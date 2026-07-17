from django.db import transaction
from django.db.models import F

from .models import CancellationLog, Evaluation, TradeOffer, UserProfile


EVALUATION_SCORE_CHANGES = {
    "good": 10,
    "bad": -10,
}

CANCELLATION_SCORE_CHANGES = {
    "cancel": -10,
    "no_show": -30,
}


@transaction.atomic
def submit_evaluation(book, evaluator, target, evaluation_type):
    if evaluation_type not in EVALUATION_SCORE_CHANGES:
        raise ValueError("evaluation_type must be 'good' or 'bad'")
    if evaluator == target:
        raise ValueError("自分自身は評価できません")

    book = book.__class__.objects.select_for_update().get(id=book.id)
    evaluation, created = Evaluation.objects.get_or_create(
        book=book,
        evaluator=evaluator,
        target=target,
        defaults={
            "evaluation_type": evaluation_type,
            "score_change": EVALUATION_SCORE_CHANGES[evaluation_type],
        },
    )
    if not created:
        return evaluation, False

    _apply_evaluations_if_both_submitted(book)
    return evaluation, True


@transaction.atomic
def apply_cancellation(book, reporter, target, kind):
    if kind not in CANCELLATION_SCORE_CHANGES:
        raise ValueError("kind must be 'cancel' or 'no_show'")

    book = book.__class__.objects.select_for_update().get(id=book.id)
    if book.status != "in_progress" or book.buyer_id is None:
        raise ValueError("取引中の出品だけがキャンセルできます")
    if reporter not in [book.seller, book.buyer] or target not in [book.seller, book.buyer]:
        raise ValueError("この取引の当事者だけが報告できます")

    score_change = CANCELLATION_SCORE_CHANGES[kind]
    log, created = CancellationLog.objects.get_or_create(
        book=book,
        reporter=reporter,
        target=target,
        kind=kind,
        defaults={"score_change": score_change},
    )
    if not created:
        return log, False

    profile, _ = UserProfile.objects.get_or_create(user=target)
    UserProfile.objects.filter(id=profile.id).update(credit_score=F("credit_score") + score_change)
    book.buyer = None
    book.status = "available"
    book.save(update_fields=["buyer", "status"])
    TradeOffer.objects.filter(book=book, status="accepted").update(status="cancelled")
    return log, True


def _apply_evaluations_if_both_submitted(book):
    if book.seller_id is None or book.buyer_id is None:
        return

    pending_evaluations = Evaluation.objects.select_for_update().filter(
        book=book,
        is_applied=False,
    )
    seller_to_buyer = pending_evaluations.filter(
        book=book,
        evaluator=book.seller,
        target=book.buyer,
    ).first()
    buyer_to_seller = pending_evaluations.filter(
        book=book,
        evaluator=book.buyer,
        target=book.seller,
    ).first()
    if not seller_to_buyer or not buyer_to_seller:
        return

    for evaluation in [seller_to_buyer, buyer_to_seller]:
        profile, _ = UserProfile.objects.get_or_create(user=evaluation.target)
        updated = Evaluation.objects.filter(id=evaluation.id, is_applied=False).update(is_applied=True)
        if updated:
            UserProfile.objects.filter(id=profile.id).update(
                credit_score=F("credit_score") + evaluation.score_change
            )

    book.status = "sold"
    book.save(update_fields=["status"])

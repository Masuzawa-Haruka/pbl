from django.db import transaction

from .models import CancellationLog, Evaluation, UserProfile


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
        return evaluation

    _apply_evaluations_if_both_submitted(book)
    return evaluation


@transaction.atomic
def apply_cancellation(book, reporter, target, kind):
    if kind not in CANCELLATION_SCORE_CHANGES:
        raise ValueError("kind must be 'cancel' or 'no_show'")

    score_change = CANCELLATION_SCORE_CHANGES[kind]
    log = CancellationLog.objects.create(
        book=book,
        reporter=reporter,
        target=target,
        kind=kind,
        score_change=score_change,
    )
    profile, _ = UserProfile.objects.get_or_create(user=target)
    profile.credit_score += score_change
    profile.save(update_fields=["credit_score"])
    return log


def _apply_evaluations_if_both_submitted(book):
    if book.seller_id is None or book.buyer_id is None:
        return

    seller_to_buyer = Evaluation.objects.filter(
        book=book,
        evaluator=book.seller,
        target=book.buyer,
        is_applied=False,
    ).first()
    buyer_to_seller = Evaluation.objects.filter(
        book=book,
        evaluator=book.buyer,
        target=book.seller,
        is_applied=False,
    ).first()
    if not seller_to_buyer or not buyer_to_seller:
        return

    for evaluation in [seller_to_buyer, buyer_to_seller]:
        profile, _ = UserProfile.objects.get_or_create(user=evaluation.target)
        profile.credit_score += evaluation.score_change
        profile.save(update_fields=["credit_score"])
        evaluation.is_applied = True
        evaluation.save(update_fields=["is_applied"])

    book.status = "sold"
    book.save(update_fields=["status"])

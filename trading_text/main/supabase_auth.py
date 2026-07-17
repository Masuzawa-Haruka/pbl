import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings


class SupabaseAuthError(Exception):
    pass


def is_configured():
    return bool(settings.SUPABASE_URL and settings.SUPABASE_ANON_KEY)


def _request(path, payload):
    if not is_configured():
        raise SupabaseAuthError("認証サービスの設定が未完了です。")

    body = json.dumps(payload).encode("utf-8")
    request = Request(
        f"{settings.SUPABASE_URL}/auth/v1/{path}",
        data=body,
        headers={
            "apikey": settings.SUPABASE_ANON_KEY,
            "Authorization": f"Bearer {settings.SUPABASE_ANON_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        try:
            detail = json.loads(error.read().decode("utf-8"))
        except json.JSONDecodeError:
            detail = {}
        message = detail.get("msg") or detail.get("message") or "メール認証に失敗しました。"
        raise SupabaseAuthError(message) from error
    except URLError as error:
        raise SupabaseAuthError("認証サービスに接続できませんでした。") from error


def sign_up(email, password, redirect_to=None, display_name=None):
    payload = {
        "email": email,
        "password": password,
    }
    options = {}
    if redirect_to:
        options["email_redirect_to"] = redirect_to
    if display_name:
        options["data"] = {"display_name": display_name}
    if options:
        payload["options"] = options
    return _request("signup", payload)


def sign_in_with_password(email, password):
    return _request("token?grant_type=password", {"email": email, "password": password})

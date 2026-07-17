import json
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.files.storage import Storage


class SupabaseStorage(Storage):
    def __init__(self):
        self.base_url = settings.SUPABASE_URL.rstrip("/")
        self.bucket = settings.SUPABASE_STORAGE_BUCKET
        self.api_key = settings.SUPABASE_STORAGE_KEY

    def _headers(self, content_type=None):
        headers = {
            "apikey": self.api_key,
            "Authorization": f"Bearer {self.api_key}",
        }
        if content_type:
            headers["Content-Type"] = content_type
        return headers

    def _object_url(self, name, public=False):
        prefix = "public/" if public else ""
        return (
            f"{self.base_url}/storage/v1/object/{prefix}"
            f"{quote(self.bucket, safe='')}/{quote(name, safe='/')}"
        )

    def _save(self, name, content):
        content.seek(0)
        request = Request(
            self._object_url(name),
            data=content.read(),
            method="POST",
            headers={
                **self._headers(getattr(content, "content_type", None) or "application/octet-stream"),
                "x-upsert": "false",
            },
        )
        self._send(request, "画像を保存できませんでした")
        return name

    def delete(self, name):
        request = Request(
            f"{self.base_url}/storage/v1/object/{quote(self.bucket, safe='')}",
            data=json.dumps({"prefixes": [name]}).encode("utf-8"),
            method="DELETE",
            headers=self._headers("application/json"),
        )
        self._send(request, "画像を削除できませんでした")

    def exists(self, name):
        request = Request(self._object_url(name), method="HEAD", headers=self._headers())
        try:
            with urlopen(request, timeout=15):
                return True
        except HTTPError as error:
            if error.code == 404:
                return False
            raise OSError(f"画像ストレージを確認できませんでした（{error.code}）") from error
        except URLError as error:
            raise OSError("画像ストレージに接続できませんでした") from error

    def url(self, name):
        return self._object_url(name, public=True)

    def _send(self, request, message):
        try:
            with urlopen(request, timeout=30):
                return
        except HTTPError as error:
            raise OSError(f"{message}（{error.code}）") from error
        except URLError as error:
            raise OSError(f"{message}。画像ストレージに接続できませんでした") from error

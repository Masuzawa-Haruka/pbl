import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


FIGMA_API_URL = "https://api.figma.com/v1/files/{file_key}"
FIGMA_TOKEN_ENV = "FIGMA_PERSONAL_ACCESS_TOKEN"


class FigmaAPIError(Exception):
    """Raised when Figma data cannot be fetched or parsed."""


def fetch_figma_document(file_key, token=None, timeout=20, opener=urlopen):
    access_token = token or os.environ.get(FIGMA_TOKEN_ENV)
    if not access_token:
        raise FigmaAPIError(f"{FIGMA_TOKEN_ENV} is required")

    if not file_key:
        raise FigmaAPIError("file_key is required")

    request = Request(
        FIGMA_API_URL.format(file_key=file_key),
        headers={"X-Figma-Token": access_token},
    )

    try:
        with opener(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        message = _read_error_message(error)
        raise FigmaAPIError(f"Figma API error: {message}") from error
    except URLError as error:
        raise FigmaAPIError(f"Figma API request failed: {error.reason}") from error
    except json.JSONDecodeError as error:
        raise FigmaAPIError("Figma API returned invalid JSON") from error

    document = payload.get("document")
    if document is None:
        raise FigmaAPIError("Figma API response did not include a document")

    return document


def _read_error_message(error):
    try:
        payload = json.loads(error.read().decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return error.reason

    return payload.get("err") or payload.get("message") or error.reason

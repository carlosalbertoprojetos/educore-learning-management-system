import json
import sys
import urllib.error
import urllib.request

from django.conf import settings



def _is_test_mode():
    return getattr(settings, "TESTING", False) or any(arg in ("test", "pytest") for arg in sys.argv)


RESPONSES_URL = "https://api.openai.com/v1/responses"
EMBEDDINGS_URL = "https://api.openai.com/v1/embeddings"


class OpenAIError(RuntimeError):
    pass


class OpenAIConfigError(OpenAIError):
    pass


def is_configured():
    if _is_test_mode():
        return False
    return bool(getattr(settings, "OPENAI_API_KEY", ""))


def _request_json(url, payload):
    api_key = getattr(settings, "OPENAI_API_KEY", "")
    if not api_key:
        raise OpenAIConfigError("OPENAI_API_KEY is not configured.")
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data, method="POST")
    request.add_header("Authorization", f"Bearer {api_key}")
    request.add_header("Content-Type", "application/json")
    timeout = int(getattr(settings, "OPENAI_TIMEOUT", 30))
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
            return json.loads(body)
    except urllib.error.HTTPError as exc:
        try:
            detail = exc.read().decode("utf-8")
        except Exception:
            detail = str(exc)
        raise OpenAIError(f"OpenAI API error: {detail}")


def extract_output_text(response_payload):
    if not response_payload:
        return ""
    output_text = response_payload.get("output_text")
    if output_text:
        return output_text.strip()
    texts = []
    for item in response_payload.get("output", []):
        if item.get("type") != "message":
            continue
        for content in item.get("content", []):
            content_type = content.get("type")
            if content_type in ("output_text", "text"):
                text = content.get("text", "")
                if text:
                    texts.append(text)
    return "\n".join(texts).strip()


def create_response(input_messages, model=None):
    payload = {
        "model": model or getattr(settings, "OPENAI_DEFAULT_MODEL", "gpt-4.1"),
        "input": input_messages,
    }
    response = _request_json(RESPONSES_URL, payload)
    return response


def create_embedding(text, model=None):
    payload = {
        "model": model or getattr(settings, "OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
        "input": text,
    }
    response = _request_json(EMBEDDINGS_URL, payload)
    return response

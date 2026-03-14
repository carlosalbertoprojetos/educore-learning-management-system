import io
import json
import urllib.error

from django.test import SimpleTestCase, override_settings
from unittest.mock import patch

from ai.services import openai_client


class OpenAIClientTests(SimpleTestCase):
    def test_is_configured_is_false_in_tests(self):
        self.assertFalse(openai_client.is_configured())

    def test_normalize_api_key_strips_prefix_and_quotes(self):
        raw = '"OPENAI_API_KEY=sk-test"'
        self.assertEqual(openai_client._normalize_api_key(raw), 'sk-test')
        raw2 = "'OPENIA_API_KEY=sk-test-2'"
        self.assertEqual(openai_client._normalize_api_key(raw2), 'sk-test-2')

    def test_extract_output_text_prefers_output_text(self):
        payload = {"output_text": "  hello  "}
        self.assertEqual(openai_client.extract_output_text(payload), "hello")

    def test_extract_output_text_from_output_messages(self):
        payload = {
            "output": [
                {
                    "type": "message",
                    "content": [
                        {"type": "output_text", "text": "A"},
                        {"type": "text", "text": "B"},
                    ],
                },
                {"type": "tool_call"},
            ]
        }
        self.assertEqual(openai_client.extract_output_text(payload), "A\nB")

    def test_request_json_requires_api_key(self):
        with self.assertRaises(openai_client.OpenAIConfigError):
            openai_client._request_json(openai_client.RESPONSES_URL, {"model": "x"})

    @override_settings(OPENAI_API_KEY="sk-test", OPENAI_TIMEOUT=1)
    @patch("urllib.request.urlopen")
    def test_request_json_success(self, urlopen):
        class FakeResponse:
            def __init__(self, payload):
                self._payload = payload

            def read(self):
                return json.dumps(self._payload).encode("utf-8")

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        urlopen.return_value = FakeResponse({"ok": True})
        data = openai_client._request_json(openai_client.RESPONSES_URL, {"model": "x"})
        self.assertEqual(data, {"ok": True})

    @override_settings(OPENAI_API_KEY="sk-test", OPENAI_TIMEOUT=1)
    @patch("urllib.request.urlopen")
    def test_request_json_http_error_includes_body(self, urlopen):
        fp = io.BytesIO(b'{"error": {"message": "bad"}}')
        err = urllib.error.HTTPError(
            openai_client.RESPONSES_URL,
            401,
            "Unauthorized",
            hdrs=None,
            fp=fp,
        )
        urlopen.side_effect = err
        with self.assertRaises(openai_client.OpenAIError) as ctx:
            openai_client.create_response([])
        self.assertIn("OpenAI API error", str(ctx.exception))
        self.assertIn("bad", str(ctx.exception))

    def test_extract_image_results(self):
        payload = {
            "output": [
                {"type": "image_generation_call", "result": {"b64_json": "..."}},
                {"type": "image_generation_call", "result": None},
                {"type": "message", "content": []},
            ]
        }
        results = openai_client.extract_image_results(payload)
        self.assertEqual(len(results), 1)
        self.assertIn("b64_json", results[0])

    def test_extract_output_text_empty_payload(self):
        self.assertEqual(openai_client.extract_output_text(None), "")

    def test_extract_image_results_empty_payload(self):
        self.assertEqual(openai_client.extract_image_results(None), [])

    @override_settings(OPENAI_API_KEY="sk-test")
    @patch("ai.services.openai_client._is_test_mode", return_value=False)
    def test_is_configured_true_when_key_present(self, _test_mode):
        self.assertTrue(openai_client.is_configured())

    @patch("ai.services.openai_client._request_json", return_value={"id": "resp"})
    def test_create_response_success(self, request_json):
        response = openai_client.create_response([{"role": "user", "content": []}], model="gpt-test")
        self.assertEqual(response["id"], "resp")
        args, kwargs = request_json.call_args
        self.assertEqual(args[0], openai_client.RESPONSES_URL)
        self.assertEqual(args[1]["model"], "gpt-test")

    @patch("ai.services.openai_client._request_json", return_value={"data": [{"embedding": [1.0]}]})
    def test_create_embedding_success(self, request_json):
        response = openai_client.create_embedding("hello", model="embed")
        self.assertIn("data", response)
        args, _kwargs = request_json.call_args
        self.assertEqual(args[0], openai_client.EMBEDDINGS_URL)
        self.assertEqual(args[1]["model"], "embed")

    @patch("ai.services.openai_client._request_json", return_value={"ok": True})
    def test_create_image_builds_tool_payload(self, request_json):
        openai_client.create_image(
            "a prompt",
            model="img-model",
            size="1024x1024",
            quality="auto",
            background="transparent",
        )
        args, _kwargs = request_json.call_args
        payload = args[1]
        self.assertEqual(payload["model"], "img-model")
        tool = payload["tools"][0]
        self.assertEqual(tool["type"], "image_generation")
        self.assertEqual(tool["size"], "1024x1024")
        self.assertEqual(tool["quality"], "auto")
        self.assertEqual(tool["background"], "transparent")

    @override_settings(OPENAI_API_KEY="sk-test", OPENAI_TIMEOUT=1)
    @patch("urllib.request.urlopen")
    def test_request_json_http_error_falls_back_to_str(self, urlopen):
        class FakeHTTPError(urllib.error.HTTPError):
            def read(self):
                raise OSError("boom")

        urlopen.side_effect = FakeHTTPError(
            openai_client.RESPONSES_URL,
            401,
            "Unauthorized",
            hdrs=None,
            fp=None,
        )
        with self.assertRaises(openai_client.OpenAIError) as ctx:
            openai_client.create_response([])
        self.assertIn("HTTP Error", str(ctx.exception))

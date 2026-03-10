import base64
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from attention.api import app
from attention.core import analyze_image_intent, generate_attention_copy, run_attention_pipeline
from attention.schemas import AnalyzeImageIntentRequest, GenerateAttentionCopyRequest


class AttentionInterfacesTest(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.intent_payload = {
            "hero_element": "蜘蛛装饰美甲",
            "hero_reason": "局部细节反差强，第一眼最容易停住",
            "supporting_elements": ["紫色针织", "库洛米发夹"],
            "mood": "怪甜、轻微暗黑感",
            "viewer_question": "这个蜘蛛装饰美甲是怎么做出来的？",
            "attention_angle": "先用怪细节把人停住，再展开整张图的气氛",
            "social_search_query": "蜘蛛美甲 紫色美甲",
            "info_needed": ["是否手作", "是否定制"],
            "relevance_score": 9,
        }

    def test_analyze_image_intent_returns_structured_error_without_key(self):
        request = AnalyzeImageIntentRequest(
            image={"path": "/tmp/does-not-exist.jpg"},
            provider="gemini",
            api_key="",
        )
        result = analyze_image_intent(request)

        self.assertEqual(result.status, "error")
        self.assertEqual(result.error.code, "missing_api_key")
        self.assertEqual(result.meta.provider_requested, "gemini")
        self.assertFalse(result.intent)

    def test_analyze_image_intent_supports_base64_input(self):
        png_bytes = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Y9erJQAAAAASUVORK5CYII="
        )
        request = AnalyzeImageIntentRequest(
            image={
                "base64": base64.b64encode(png_bytes).decode("utf-8"),
                "mime_type": "image/png",
            },
            provider="gemini",
            api_key="demo-key",
        )

        with patch("modules.photo_tagger.analyze_image_intent", return_value=self.intent_payload):
            result = analyze_image_intent(request)

        self.assertEqual(result.status, "ok")
        self.assertEqual(result.intent.hero_element, "蜘蛛装饰美甲")
        self.assertEqual(result.meta.provider_requested, "gemini")

    def test_generate_attention_copy_returns_structured_error_without_key(self):
        request = GenerateAttentionCopyRequest(
            intent=self.intent_payload,
            provider="gemini",
            api_key="",
        )
        result = generate_attention_copy(request)

        self.assertEqual(result.status, "error")
        self.assertEqual(result.error.code, "missing_api_key")
        self.assertEqual(result.copy_candidates, [])

    def test_generate_attention_copy_returns_markdown_on_success(self):
        request = GenerateAttentionCopyRequest(
            intent=self.intent_payload,
            provider="gemini",
            api_key="demo-key",
        )

        fake_notes = {
            "notes": [
                {
                    "title_a": "蜘蛛美甲｜比整套穿搭更会抢镜",
                    "title_b": "不是夸张，是这点细节太会勾人看",
                    "content": "先用怪细节把人停住，再顺着气氛看完整张图。",
                    "tags": "#蜘蛛美甲 #紫色美甲",
                }
            ],
            "total": 1,
            "passed_check": 1,
            "raw": "",
        }

        with patch("modules.copywriter.run", return_value=fake_notes):
            result = generate_attention_copy(request)

        self.assertEqual(result.status, "ok")
        self.assertEqual(result.best_copy.title_a, "蜘蛛美甲｜比整套穿搭更会抢镜")
        self.assertIn("## 最佳文案", result.markdown)
        self.assertEqual(len(result.copy_candidates), 1)

    def test_http_api_returns_same_error_contract(self):
        response = self.client.post(
            "/v1/intent/analyze",
            json={
                "schema_version": "attention.v1",
                "image": {"path": "/tmp/does-not-exist.jpg"},
                "provider": "gemini",
                "api_key": "",
            },
        )

        payload = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["schema_version"], "attention.v1")
        self.assertEqual(payload["status"], "error")
        self.assertEqual(payload["error"]["code"], "missing_api_key")

    def test_run_attention_pipeline_returns_structured_error_without_key(self):
        with tempfile.TemporaryDirectory(prefix="attention_test_") as tmpdir:
            image_path = Path(tmpdir) / "sample.jpg"
            image_path.write_bytes(b"fake-image")
            result = run_attention_pipeline(
                photos_dir=tmpdir,
                provider="gemini",
                api_key="",
                include_viral_research=False,
            )

        self.assertEqual(result.status, "error")
        self.assertEqual(result.error.code, "missing_api_key")


if __name__ == "__main__":
    unittest.main()

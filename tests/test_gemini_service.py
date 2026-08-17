from __future__ import annotations

import unittest
from atlas.gemini_service import GeminiService, GeminiServiceError, MissingApiKeyError


class FakeInteraction:
    output_text = "A concise grounded answer."

    def model_dump(self, exclude_none: bool = True):  # noqa: ARG002 - matches the SDK method shape.
        return {
            "steps": [
                {
                    "type": "model_output",
                    "content": [
                        {
                            "type": "text",
                            "text": self.output_text,
                            "annotations": [
                                {
                                    "type": "url_citation",
                                    "title": "Example video",
                                    "url": "https://www.youtube.com/watch?v=test",
                                },
                                {
                                    "type": "url_citation",
                                    "title": "Example site",
                                    "url": "https://example.com/research",
                                },
                            ],
                        }
                    ],
                }
            ]
        }


class GeminiServiceTests(unittest.TestCase):
    def test_extracts_deduplicated_grounding_citations(self) -> None:
        result = GeminiService._result(FakeInteraction())
        self.assertEqual(result.answer, "A concise grounded answer.")
        self.assertEqual(len(result.citations), 2)
        self.assertEqual(result.citations[0].kind, "Video")
        self.assertEqual(result.citations[1].kind, "Website")

    def test_key_is_required_before_creating_a_client(self) -> None:
        with self.assertRaises(MissingApiKeyError):
            GeminiService("")._client()

    def test_copyright_block_error_is_user_friendly(self) -> None:
        with self.assertRaisesRegex(GeminiServiceError, "rephrase|copyright|original"):
            GeminiService._raise_clean_error(RuntimeError("Request blocked due to copyright/citation content. Please modify your input and retry."))


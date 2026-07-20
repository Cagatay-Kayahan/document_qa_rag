import unittest
from unittest.mock import Mock, patch

from src.chunker import create_chunks
from src.cloud_llm_client import extract_response_text
from src.document_loader import clean_block_text, load_document
from src.llm_client import _extract_message_text, _post_chat_request


class DocumentLoaderTests(unittest.TestCase):
    def test_loads_utf8_txt_as_paragraph_blocks(self):
        pages = load_document(
            "ornek.txt",
            "İlk paragraf.\n\nİkinci paragraf.".encode("utf-8"),
        )

        self.assertEqual(len(pages), 1)
        self.assertEqual(len(pages[0]["blocks"]), 2)
        self.assertIn("İkinci paragraf", pages[0]["text"])

    def test_rejects_unsupported_extension(self):
        with self.assertRaises(ValueError):
            load_document("ornek.docx", b"icerik")

    def test_normalizes_split_bullet(self):
        self.assertEqual(clean_block_text("\uf0b7\nMadde"), "• Madde")


class ChunkerTests(unittest.TestCase):
    def test_keeps_sections_separate(self):
        pages = [
            {
                "page_number": 1,
                "text": "",
                "blocks": [
                    {"text": "1. Birinci Bölüm\nBirinci içerik."},
                    {"text": "2. İkinci Bölüm\nİkinci içerik."},
                ],
            }
        ]

        chunks = create_chunks(pages, chunk_size=50, chunk_overlap=10)

        self.assertEqual(len(chunks), 2)
        self.assertIn("1. Birinci Bölüm", chunks[0]["text"])
        self.assertNotIn("İkinci içerik", chunks[0]["text"])

    def test_long_heading_does_not_break_chunk_limit(self):
        heading = "1. " + " ".join(["A"] * 40)
        body = " ".join(["kelime"] * 100)
        pages = [
            {
                "page_number": 1,
                "text": "",
                "blocks": [{"text": f"{heading}\n{body}"}],
            }
        ]

        chunks = create_chunks(pages, chunk_size=50, chunk_overlap=10)

        self.assertTrue(chunks)
        self.assertTrue(all(chunk["word_count"] <= 50 for chunk in chunks))
        self.assertEqual(chunks[0]["section_title"], heading)

    def test_rejects_invalid_overlap(self):
        with self.assertRaises(ValueError):
            create_chunks([], chunk_size=20, chunk_overlap=20)


class ResponseParsingTests(unittest.TestCase):
    def test_extracts_lm_studio_final_message_only(self):
        payload = {
            "output": [
                {"type": "reasoning", "content": "gizli düşünce"},
                {"type": "message", "content": "Nihai cevap"},
            ]
        }

        self.assertEqual(_extract_message_text(payload), "Nihai cevap")

    def test_extracts_gemini_text_and_ignores_thought(self):
        thought = Mock(thought=True, text="gizli düşünce")
        answer = Mock(thought=False, text="Nihai cevap")
        candidate = Mock(content=Mock(parts=[thought, answer]))
        response = Mock(candidates=[candidate])

        self.assertEqual(extract_response_text(response), "Nihai cevap")

    @patch("src.llm_client.requests.post")
    def test_does_not_retry_unrelated_http_error(self, post):
        response = Mock(ok=False, status_code=500, text="server error")
        response.raise_for_status.side_effect = RuntimeError("500")
        post.return_value = response

        with self.assertRaises(RuntimeError):
            _post_chat_request({"reasoning": "off"})

        self.assertEqual(post.call_count, 1)


if __name__ == "__main__":
    unittest.main()

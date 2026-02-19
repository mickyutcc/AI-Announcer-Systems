import unittest

from voice_clone import chunk_text, normalize_text


class TestVoiceUtils(unittest.TestCase):
    def test_chunk_text_simple(self):
        text = "Hello world. This is a test."
        chunks = chunk_text(text, max_chars=100)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0], "Hello world. This is a test.")

    def test_chunk_text_splitting(self):
        text = "Sentence 1. " * 10
        # "Sentence 1. " is 12 chars. 10 times is 120 chars.
        # max_chars=50 should split it.
        chunks = chunk_text(text, max_chars=50)
        self.assertTrue(len(chunks) > 1)
        for c in chunks:
            self.assertTrue(len(c) <= 50)

    def test_normalize_text(self):
        text = "MuseGen AI Version 2"
        norm = normalize_text(text)
        # Check lexicon
        self.assertIn("มิวส์เจน", norm)
        self.assertIn("เอไอ", norm)
        self.assertIn("เวอร์ชัน", norm)


if __name__ == "__main__":
    unittest.main()

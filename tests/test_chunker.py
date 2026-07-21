import unittest

from src.chunker import is_heading


class HeadingDetectionTests(unittest.TestCase):
    def test_numbered_subheading_with_trailing_dot(self):
        self.assertTrue(
            is_heading("2.2. Bölgesel Yağış Değerlendirmesi")
        )

    def test_numbered_subheading_without_space(self):
        self.assertTrue(is_heading("2.4.Yağışlı Gün Sayısı"))

    def test_short_uppercase_heading(self):
        self.assertTrue(is_heading("ÖZET DEĞERLENDİRME"))

    def test_one_word_table_label_is_not_section_heading(self):
        self.assertFalse(is_heading("BÖLGELER"))

    def test_table_of_contents_line_is_not_heading(self):
        self.assertFalse(
            is_heading(
                "1.1 Genel Değerlendirme (Sıcaklık) "
                "................................ 2"
            )
        )


if __name__ == "__main__":
    unittest.main()

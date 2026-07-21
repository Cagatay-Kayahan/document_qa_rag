import unittest

from src.vector_store import _lexical_coverage


class LexicalRerankingTests(unittest.TestCase):
    def test_exact_report_terms_score_higher(self):
        question = (
            "Haziran 2025 yağış normaline göre en büyük azalma "
            "hangi bölgede görüldü?"
        )
        relevant = (
            "2025 Haziran bölgesel yağış değerlendirmesinde "
            "normaline göre en büyük azalma Marmara Bölgesi'ndedir."
        )
        unrelated = (
            "2025 Haziran ayında ortalama sıcaklıklar kıyılarda "
            "mevsim normallerinin üzerinde gerçekleşmiştir."
        )

        self.assertGreater(
            _lexical_coverage(question, relevant),
            _lexical_coverage(question, unrelated),
        )

    def test_numbers_are_matched(self):
        question = "2024 ve 2025 Haziran yağışlarını karşılaştır."
        document = "2024 Haziran yağışı 11.9 mm, 2025 yağışı 12.5 mm'dir."

        self.assertGreaterEqual(
            _lexical_coverage(question, document),
            0.7,
        )

    def test_common_turkish_suffixes_are_normalized(self):
        question = "Hangi bölgede yağış normaline göre azaldı?"
        document = "Bölgeler yağış normali ve azalma oranına göre sıralandı."

        self.assertGreaterEqual(
            _lexical_coverage(question, document),
            0.5,
        )


if __name__ == "__main__":
    unittest.main()

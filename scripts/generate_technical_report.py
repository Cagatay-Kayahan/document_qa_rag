from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "RAG_Dokuman_Soru_Cevap_Teknik_Rapor.pdf"

FONT_DIR = Path("C:/Windows/Fonts")
pdfmetrics.registerFont(TTFont("Arial", str(FONT_DIR / "arial.ttf")))
pdfmetrics.registerFont(TTFont("Arial-Bold", str(FONT_DIR / "arialbd.ttf")))

styles = getSampleStyleSheet()
styles.add(
    ParagraphStyle(
        name="ReportTitle",
        parent=styles["Title"],
        fontName="Arial-Bold",
        fontSize=17,
        leading=21,
        alignment=TA_CENTER,
        spaceAfter=10 * mm,
        textColor=colors.HexColor("#17365D"),
    )
)
styles.add(
    ParagraphStyle(
        name="Section",
        parent=styles["Heading2"],
        fontName="Arial-Bold",
        fontSize=11.5,
        leading=14,
        spaceBefore=4 * mm,
        spaceAfter=2 * mm,
        textColor=colors.HexColor("#17365D"),
    )
)
styles.add(
    ParagraphStyle(
        name="BodyTR",
        parent=styles["BodyText"],
        fontName="Arial",
        fontSize=9.3,
        leading=13.2,
        spaceAfter=2.5 * mm,
    )
)
styles.add(
    ParagraphStyle(
        name="BulletTR",
        parent=styles["BodyTR"],
        leftIndent=5 * mm,
        firstLineIndent=-3 * mm,
        bulletIndent=1.5 * mm,
        spaceAfter=1.2 * mm,
    )
)
styles.add(
    ParagraphStyle(
        name="TableTR",
        parent=styles["BodyTR"],
        fontSize=7.5,
        leading=9.5,
        spaceAfter=0,
    )
)


def p(text: str, style: str = "BodyTR") -> Paragraph:
    return Paragraph(text, styles[style])


def bullet(text: str) -> Paragraph:
    return Paragraph(f"• {text}", styles["BulletTR"])


def section(title: str, body: list) -> KeepTogether:
    return KeepTogether([p(title, "Section"), *body])


def make_table(rows: list[list[str]], widths: list[float]) -> Table:
    data = [[p(cell, "TableTR") for cell in row] for row in rows]
    table = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#D9EAF7")),
                ("FONTNAME", (0, 0), (-1, 0), "Arial-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#8A9BA8")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F6F8FA")]),
            ]
        )
    )
    return table


story = [p("RAG Doküman Soru-Cevap Sistemi<br/>Kısa Teknik Rapor", "ReportTitle")]

story += [
    section(
        "1. Amaç",
        [
            p(
                "PDF veya TXT dokümanlarının yüklenebildiği, soruyla ilgili kaynak parçalarını "
                "bulan ve yalnızca bu kaynaklara dayanarak cevap üreten bir RAG sistemi geliştirilmiştir. "
                "Uygulama, cevabın dayandığı chunk ve sayfa bilgilerini kullanıcıya gösterir."
            )
        ],
    ),
    section(
        "2. Sistem Akışı",
        [
            bullet("Doküman yüklenir; metin ve sayfa bilgisi PyMuPDF ile çıkarılır."),
            bullet("Metin başlık ve paragraf sınırları korunarak chunk'lara ayrılır."),
            bullet("Chunk'lar multilingual-e5-small ile embedding'e dönüştürülür ve ChromaDB'ye kaydedilir."),
            bullet("Semantic adaylar, soru ile ortak ayırt edici kelime ve sayılar kullanılarak yeniden sıralanır."),
            bullet("Seçilen kaynaklar Cloud Gemini veya Local Gemma'ya verilir; cevap ve kaynaklar gösterilir."),
        ],
    ),
    section(
        "3. Kullanılan Yapılar",
        [
            make_table(
                [
                    ["Bileşen", "Kullanılan yapı"],
                    ["Arayüz / PDF", "Streamlit / PyMuPDF"],
                    ["Embedding", "intfloat/multilingual-e5-small (384 boyut)"],
                    ["Vector database", "ChromaDB, cosine distance"],
                    ["Cloud LLM", "gemini-3.5-flash"],
                    ["Local LLM", "google/gemma-4-e4b, LM Studio native API"],
                ],
                [52 * mm, 116 * mm],
            )
        ],
    ),
    section(
        "4. Chunking ve Retrieval",
        [
            p(
                "Varsayılan ayarlar 120 kelimelik chunk size, 25 kelimelik overlap ve top-k 3'tür. "
                "İlk kelime tabanlı yaklaşım farklı bölümleri karıştırdığı için başlık/paragraf duyarlı "
                "chunking uygulanmıştır. Farklı alan testi sırasında içindekiler satırlarının başlık sanılması "
                "ve '2.2.' biçimindeki başlıkların tanınmaması düzeltildi. Semantic aramaya hafif Türkçe ek "
                "normalizasyonu ve anahtar kelime/sayı tabanlı yeniden sıralama eklendi."
            ),
            p(
                "İlk beş soruluk deney setinde Top-1 ve Hit@3 5/5 ölçülmüştür. Bu sonuç yalnızca o doküman "
                "ve soru setini kapsar. Farklı alan testinde cevaplanabilir altı sorunun gerekli kanıtı 6/6 "
                "oranında ilk üç kaynak içinde bulunmuştur; bazı karşılaştırmalı sorularda doğru kaynak ilk "
                "sırada değil ikinci sırada yer almıştır."
            ),
        ],
    ),
]

test_rows = [
    ["Test", "Retrieval", "Gemini", "Gemma"],
    ["Türkiye ortalama sıcaklığı", "Kanıt ilk 3'te", "Doğru, 1.28 sn", "Yanlış/çelişkili, 3.22 sn"],
    ["Türkiye uç sıcaklıkları", "Doğru chunk ilk sırada", "Doğru, 1.07 sn", "Doğru, 2.11 sn"],
    ["2024-2025 yağış karşılaştırması", "Kanıt ilk 3'te", "Doğru, 1.31 sn", "Doğru, 4.49 sn"],
    ["En büyük bölgesel azalma", "Tablo ilk 3'te", "Doğru, 1.07 sn", "Yanlış bölge, 3.25 sn"],
    ["Karadeniz-Güneydoğu karşılaştırması", "Tablo ilk sırada", "Doğru, 1.71 sn", "Doğru, 8.31 sn"],
    ["Havza ve yağışlı gün sentezi", "İki kanıt ilk 3'te", "Doğru, 1.18 sn", "Doğru, 2.43 sn"],
    ["Ekonomik kayıp (cevap yok)", "İlgili konu var, cevap yok", "Final seride kota doldu", "Uydurmadı, 1.15 sn"],
    ["Görsel ekstrem sıcaklık tablosu", "Hücreler metne çıkmadı", "Ön testte uydurmadı", "Uydurmadı, 0.95 sn"],
]

story += [
    section(
        "5. Farklı Alan Dokümanı Testi",
        [
            p(
                "Sistem, Meteoroloji Genel Müdürlüğünün 25 sayfalık 'Haziran 2025 Sıcaklık ve Yağış "
                "Değerlendirmesi' raporuyla test edildi. Doküman 40 chunk'a ayrıldı. Sekiz soru; doğrudan "
                "bilgi, çoklu kaynak sentezi, tablo karşılaştırması ve cevabı bulunmayan durumları kapsadı."
            ),
            make_table(test_rows, [58 * mm, 43 * mm, 34 * mm, 34 * mm]),
            Spacer(1, 2 * mm),
            p(
                "Cevaplanabilir altı soruda Gemini 6/6 doğru cevap verdi ve ortalama 1.27 saniye sürdü. "
                "Gemma 4/6 doğru cevap verdi ve ortalama 3.97 saniye sürdü. Gemma'nın iki hatasında doğru "
                "kaynaklar ilk üçte olmasına rağmen değerleri ters yorumlama veya tablodaki maksimumu yanlış "
                "seçme görüldü. Bu durum retrieval başarısının tek başına doğru cevap garantilemediğini gösterdi."
            ),
        ],
    ),
    section(
        "6. Negatif ve Operasyonel Testler",
        [
            bullet("Tarımsal ekonomik kayıp sorusunun cevabı dokümanda yoktu; local model bilgi uydurmadı."),
            bullet("Ekstrem sıcaklık tablosu PDF'de görsel olduğu için hücreler metne çıkarılamadı; model isim uydurmadı."),
            bullet("Final test sırasında Gemini ücretsiz günlük 20 istek kotasına ulaştı. Uygulama 429 hatasını gösterdi ve local mod çalışmaya devam etti."),
            bullet("Bir Gemini çağrısında DNS bağlantı hatası oluştu; hata kullanıcıya yansıtıldı, uygulama çökmedi."),
        ],
    ),
    section(
        "7. Sınırlamalar",
        [
            bullet("Taranmış veya görsel tablo içeren PDF'ler için OCR ve gelişmiş tablo çıkarımı yoktur."),
            bullet("Aynı kaynaklarda çelişkili veya bozuk çıkarılmış metin varsa küçük local model yanlış seçim yapabilir."),
            bullet("Cloud kullanımında seçilen chunk'lar üçüncü taraf API'ye gönderilir; kota ve ağ durumu sürekliliği etkiler."),
            bullet("Ölçülen başarı oranları yalnızca kullanılan doküman ve soru setleri için geçerlidir."),
        ],
    ),
    section(
        "8. Sonuç",
        [
            p(
                "Uygulama yükleme, metin çıkarma, yapısal chunking, embedding, vector database, hibrit "
                "retrieval, cloud/local cevap üretimi ve kaynak gösterme akışını uçtan uca tamamlamaktadır. "
                "Farklı alan testi retrieval tarafını güçlendirmiş; görsel tablo desteği ve local modelin "
                "karmaşık seçim doğruluğu sonraki geliştirme alanları olarak belirlenmiştir."
            )
        ],
    ),
]

document = SimpleDocTemplate(
    str(OUTPUT),
    pagesize=A4,
    rightMargin=20 * mm,
    leftMargin=20 * mm,
    topMargin=18 * mm,
    bottomMargin=18 * mm,
    title="RAG Doküman Soru-Cevap Sistemi - Kısa Teknik Rapor",
    author="",
)
document.build(story)

print(OUTPUT)

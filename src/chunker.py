import re


HEADING_PATTERN = re.compile(
    r"^\d+\.(?:\d+\.?)*\s*[A-ZÇĞİÖŞÜ]"
)

DOT_LEADER_PATTERN = re.compile(r"\.{4,}\s*\d*\s*$")


def is_heading(line: str) -> bool:
    """
    1. Çalışmanın Amacı
    4.2 Phi 3.5 Mini Instruct
    10. Sonuç ve Sonraki Adım

    gibi numaralı başlıkları algılar.
    """

    clean_line = line.strip()

    if not clean_line or len(clean_line) > 140:
        return False

    # İçindekiler sayfasındaki "1.1 Başlık .... 2" satırlarını
    # gerçek bölüm başlığı olarak kabul etme.
    if DOT_LEADER_PATTERN.search(clean_line):
        return False

    if HEADING_PATTERN.match(clean_line):
        return True

    # ÖNSÖZ, ÖZET DEĞERLENDİRME ve YAĞIŞ gibi kısa, tamamı
    # büyük harfli bölüm başlıklarını da algıla.
    letters = [character for character in clean_line if character.isalpha()]
    uppercase_word_count = len(clean_line.split())
    is_short_uppercase_heading = (
        4 <= len(letters)
        and uppercase_word_count <= 8
        and clean_line == clean_line.upper()
        and (
            uppercase_word_count >= 2
            or clean_line in {"ÖNSÖZ", "İÇİNDEKİLER"}
        )
    )

    return is_short_uppercase_heading


def extract_sections(
    document_pages: list[dict],
) -> list[dict]:
    """
    Metin bloklarını başlıklarına ve sayfalarına göre
    ayrı bölümlere dönüştürür.
    """

    sections = []
    current_heading = "Genel"

    for page in document_pages:
        page_number = page["page_number"]

        blocks = page.get("blocks")

        # Eski loader yapısıyla da hata vermemesi için.
        if not blocks:
            blocks = [
                {
                    "text": page["text"],
                }
            ]

        current_paragraphs = []

        for block in blocks:
            lines = [
                line.strip()
                for line in block["text"].splitlines()
                if line.strip()
            ]

            if not lines:
                continue

            body_lines = []

            for line in lines:
                if is_heading(line):
                    if body_lines:
                        current_paragraphs.append(
                            " ".join(body_lines)
                        )
                        body_lines = []

                    if current_paragraphs:
                        sections.append(
                            {
                                "heading": current_heading,
                                "page_number": page_number,
                                "paragraphs": current_paragraphs,
                            }
                        )

                        current_paragraphs = []

                    current_heading = line

                else:
                    body_lines.append(line)

            if body_lines:
                current_paragraphs.append(
                    " ".join(body_lines)
                )

        # Sayfa sonunda kalan bölümü kaydet.
        if current_paragraphs:
            sections.append(
                {
                    "heading": current_heading,
                    "page_number": page_number,
                    "paragraphs": current_paragraphs,
                }
            )

    return sections


def create_chunks(
    document_pages: list[dict],
    chunk_size: int = 120,
    chunk_overlap: int = 25,
) -> list[dict]:
    """
    Dokümanı başlık ve paragraf sınırlarını koruyarak
    chunk'lara böler.

    Kısa paragraflar ortadan bölünmez.
    Overlap yalnızca tek bir paragraf chunk boyutundan
    daha uzunsa uygulanır.
    """

    if chunk_size <= 0:
        raise ValueError(
            "Chunk size sıfırdan büyük olmalıdır."
        )

    if chunk_overlap < 0:
        raise ValueError(
            "Chunk overlap negatif olamaz."
        )

    if chunk_overlap >= chunk_size:
        raise ValueError(
            "Chunk overlap, chunk size değerinden "
            "küçük olmalıdır."
        )

    sections = extract_sections(document_pages)

    chunks = []
    chunk_id = 1

    def add_chunk(
        display_heading: str,
        section_title: str,
        page_number: int,
        body_text: str,
    ) -> None:
        nonlocal chunk_id

        chunk_text = (
            f"Bölüm: {display_heading}\n\n"
            f"{body_text.strip()}"
        )

        chunks.append(
            {
                "chunk_id": chunk_id,
                "page_number": page_number,
                "section_title": section_title,
                "text": chunk_text,
                "word_count": len(
                    chunk_text.split()
                ),
            }
        )

        chunk_id += 1

    for section in sections:
        heading = section["heading"]
        page_number = section["page_number"]

        # Çok uzun başlıkların gövde için ayrılan alanı tüketmesini önle.
        max_heading_words = max(1, chunk_size // 3)
        heading_words = heading.split()
        display_heading = " ".join(
            heading_words[:max_heading_words]
        )

        if len(heading_words) > max_heading_words:
            display_heading = f"{display_heading} ..."

        heading_word_count = len(
            f"Bölüm: {display_heading}".split()
        )

        body_word_limit = max(1, chunk_size - heading_word_count)

        current_paragraphs = []
        current_word_count = 0

        for paragraph in section["paragraphs"]:
            paragraph_words = paragraph.split()

            if not paragraph_words:
                continue

            # Tek paragraf chunk sınırından uzunsa
            # kelime bazlı ve overlap kullanarak böl.
            if len(paragraph_words) > body_word_limit:
                if current_paragraphs:
                    add_chunk(
                        display_heading=display_heading,
                        section_title=heading,
                        page_number=page_number,
                        body_text="\n\n".join(
                            current_paragraphs
                        ),
                    )

                    current_paragraphs = []
                    current_word_count = 0

                overlap = min(
                    chunk_overlap,
                    body_word_limit - 1,
                )

                start_index = 0

                while start_index < len(paragraph_words):
                    end_index = min(
                        start_index + body_word_limit,
                        len(paragraph_words),
                    )

                    paragraph_piece = " ".join(
                        paragraph_words[
                            start_index:end_index
                        ]
                    )

                    add_chunk(
                        display_heading=display_heading,
                        section_title=heading,
                        page_number=page_number,
                        body_text=paragraph_piece,
                    )

                    if end_index >= len(paragraph_words):
                        break

                    start_index = end_index - overlap

                continue

            new_word_count = (
                current_word_count
                + len(paragraph_words)
            )

            # Yeni paragraf sınırı aşacaksa önceki
            # paragrafları ayrı chunk olarak kaydet.
            if (
                current_paragraphs
                and new_word_count > body_word_limit
            ):
                add_chunk(
                    display_heading=display_heading,
                    section_title=heading,
                    page_number=page_number,
                    body_text="\n\n".join(
                        current_paragraphs
                    ),
                )

                current_paragraphs = []
                current_word_count = 0

            current_paragraphs.append(paragraph)
            current_word_count += len(paragraph_words)

        if current_paragraphs:
            add_chunk(
                display_heading=display_heading,
                section_title=heading,
                page_number=page_number,
                body_text="\n\n".join(
                    current_paragraphs
                ),
            )

    return chunks

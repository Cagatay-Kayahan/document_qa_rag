from collections import defaultdict
from pathlib import Path
import re

import fitz


def clean_block_text(text: str) -> str:
    """
    PDF'den çıkarılan blok metnindeki gereksiz
    boşlukları ve bozuk madde işaretlerini temizler.
    """

    text = text.replace("\r", "\n")
    text = text.replace("\uf0b7", "•")

    raw_lines = [
        re.sub(r"[ \t]+", " ", line).strip()
        for line in text.splitlines()
    ]

    cleaned_lines = []
    bullet_waiting = False

    for line in raw_lines:
        if not line:
            continue

        if line == "•":
            bullet_waiting = True
            continue

        if bullet_waiting:
            line = f"• {line}"
            bullet_waiting = False

        cleaned_lines.append(line)

    return "\n".join(cleaned_lines).strip()


def normalize_repeated_text(text: str) -> str:
    """
    Tekrarlanan üst ve alt bilgileri karşılaştırabilmek
    için metni sadeleştirir.
    """

    return re.sub(
        r"\s+",
        " ",
        text,
    ).strip().lower()


def extract_pdf_text(file_bytes: bytes) -> list[dict]:
    """
    PDF'yi sayfa ve metin blokları hâlinde okur.

    Aynı sayfa alt bilgisi veya üst bilgisi birden fazla
    sayfada tekrarlanıyorsa bunları kaldırır.
    """

    pdf_document = fitz.open(
        stream=file_bytes,
        filetype="pdf",
    )

    raw_pages = []
    edge_text_pages: dict[str, set[int]] = defaultdict(set)

    try:
        for page_index, page in enumerate(pdf_document):
            page_height = float(page.rect.height)
            page_blocks = []

            text_blocks = page.get_text(
                "blocks",
                sort=True,
            )

            for block in text_blocks:
                # block[6] değeri 0 ise bu bir metin bloğudur.
                if len(block) < 7 or block[6] != 0:
                    continue

                block_text = clean_block_text(block[4])

                if not block_text:
                    continue

                block_data = {
                    "text": block_text,
                    "x0": float(block[0]),
                    "y0": float(block[1]),
                    "x1": float(block[2]),
                    "y1": float(block[3]),
                }

                page_blocks.append(block_data)

                # Sayfanın üst veya alt kenarındaki metinleri
                # tekrarlanan header/footer kontrolüne alıyoruz.
                is_edge_block = (
                    block_data["y0"] < 70
                    or block_data["y1"] > page_height - 70
                )

                if is_edge_block:
                    repeated_key = normalize_repeated_text(
                        block_text
                    )

                    edge_text_pages[repeated_key].add(page_index + 1)

            raw_pages.append(
                {
                    "page_number": page_index + 1,
                    "page_height": page_height,
                    "blocks": page_blocks,
                }
            )

    finally:
        pdf_document.close()

    repeated_edge_texts = {
        text
        for text, page_numbers in edge_text_pages.items()
        if len(page_numbers) >= 2 and len(text) <= 120
    }

    document_pages = []

    for page in raw_pages:
        cleaned_blocks = []

        for block in page["blocks"]:
            is_edge_block = (
                block["y0"] < 70
                or block["y1"] > page["page_height"] - 70
            )

            repeated_key = normalize_repeated_text(
                block["text"]
            )

            is_repeated_header_or_footer = (
                is_edge_block
                and repeated_key in repeated_edge_texts
            )

            if is_repeated_header_or_footer:
                continue

            cleaned_blocks.append(block)

        page_text = "\n\n".join(
            block["text"]
            for block in cleaned_blocks
        ).strip()

        if not page_text:
            continue

        document_pages.append(
            {
                "page_number": page["page_number"],
                "text": page_text,
                "blocks": cleaned_blocks,
            }
        )

    return document_pages


def extract_txt_text(file_bytes: bytes) -> list[dict]:
    """
    TXT dosyasını paragraf bloklarına ayırarak okur.
    """

    try:
        text = file_bytes.decode("utf-8")
    except UnicodeDecodeError:
        text = file_bytes.decode("latin-1")

    text = text.strip()

    if not text:
        return []

    raw_paragraphs = re.split(
        r"\n\s*\n",
        text,
    )

    blocks = []

    for paragraph in raw_paragraphs:
        cleaned_paragraph = clean_block_text(paragraph)

        if not cleaned_paragraph:
            continue

        blocks.append(
            {
                "text": cleaned_paragraph,
                "x0": 0.0,
                "y0": 0.0,
                "x1": 0.0,
                "y1": 0.0,
            }
        )

    return [
        {
            "page_number": 1,
            "text": "\n\n".join(
                block["text"]
                for block in blocks
            ),
            "blocks": blocks,
        }
    ]


def load_document(
    file_name: str,
    file_bytes: bytes,
) -> list[dict]:
    """
    Dosya uzantısına göre uygun metin çıkarma
    fonksiyonunu çalıştırır.
    """

    file_extension = Path(file_name).suffix.lower()

    if file_extension == ".pdf":
        return extract_pdf_text(file_bytes)

    if file_extension == ".txt":
        return extract_txt_text(file_bytes)

    raise ValueError(
        "Desteklenmeyen dosya türü. "
        "Yalnızca PDF veya TXT yükleyin."
    )

from typing import Any

import hashlib
import re
import chromadb
from sentence_transformers import SentenceTransformer


EMBEDDING_MODEL_NAME = "intfloat/multilingual-e5-small"

TOKEN_PATTERN = re.compile(
    r"\d+(?:[.,]\d+)?|[^\W\d_]+",
    flags=re.UNICODE,
)

TURKISH_STOP_WORDS = {
    "acaba", "ama", "ancak", "artık", "bir", "bu", "da", "daha",
    "de", "diye", "en", "gibi", "hangi", "ile", "için", "ise",
    "kaç", "kadar", "mi", "mı", "mu", "mü", "nasıl", "ne", "neden",
    "olarak", "olan", "oldu", "ve", "veya", "ya", "yani",
}

TURKISH_SUFFIXES = (
    "larının", "lerinin", "larında", "lerinde", "lardan", "lerden",
    "ında", "inde", "unda", "ünde", "ına", "ine", "una", "üne",
    "ndan", "nden", "ları", "leri", "lar", "ler", "dan", "den",
    "nın", "nin", "nun", "nün", "da", "de", "ın", "in", "un", "ün",
    "ı", "i", "u", "ü",
)


def _normalize_token(token: str) -> str:
    """Basit Türkçe eklerini azaltarak aynı kökün eşleşmesini kolaylaştırır."""

    normalized = token.replace(",", ".").split("'", 1)[0]

    if normalized[0].isdigit():
        return normalized

    for _ in range(2):
        for suffix in TURKISH_SUFFIXES:
            if (
                normalized.endswith(suffix)
                and len(normalized) - len(suffix) >= 4
            ):
                normalized = normalized[:-len(suffix)]
                break
        else:
            break

    return normalized


def _tokenize_for_reranking(text: str) -> set[str]:
    """Metni hafif bir Türkçe/numara duyarlı anahtar kelime kümesine çevirir."""

    normalized_tokens = set()

    for token in TOKEN_PATTERN.findall(text.lower()):
        if token in TURKISH_STOP_WORDS:
            continue

        normalized = _normalize_token(token)

        if len(normalized) > 2 or normalized[0].isdigit():
            normalized_tokens.add(normalized)

    return normalized_tokens


def _lexical_coverage(question: str, document: str) -> float:
    """Sorudaki ayırt edici terimlerin chunk içinde bulunma oranını ölçer."""

    question_tokens = _tokenize_for_reranking(question)

    if not question_tokens:
        return 0.0

    document_tokens = _tokenize_for_reranking(document)
    matched_tokens = question_tokens & document_tokens

    # Tarih ve sayılar tablo/rapor sorularında özellikle ayırt edicidir.
    total_weight = sum(
        2.0 if token[0].isdigit() else 1.0
        for token in question_tokens
    )
    matched_weight = sum(
        2.0 if token[0].isdigit() else 1.0
        for token in matched_tokens
    )

    return matched_weight / total_weight


def load_embedding_model() -> SentenceTransformer:
    """
    Metinleri sayısal vektörlere dönüştürecek
    embedding modelini yükler.
    """

    model = SentenceTransformer(EMBEDDING_MODEL_NAME)

    return model


def create_vector_store(
    chunks: list[dict],
    embedding_model: SentenceTransformer,
) -> tuple[Any, int]:
    """
    Chunk embeddinglerini oluşturur ve Chroma içerisine kaydeder.

    Her doküman ve chunk ayarı için özel bir collection adı
    oluşturulur. Böylece farklı dokümanların verileri karışmaz.
    """

    if not chunks:
        raise ValueError(
            "Vector database oluşturmak için en az bir chunk gereklidir."
        )

    original_texts = [
        chunk["text"]
        for chunk in chunks
    ]

    passage_texts = [
        f"passage: {chunk['text']}"
        for chunk in chunks
    ]

    embeddings = embedding_model.encode(
        passage_texts,
        normalize_embeddings=True,
        show_progress_bar=False,
    )

    # Dokümanın içeriğine göre benzersiz bir kimlik oluşturuyoruz.
    fingerprint_text = "||".join(
        [
            f"embedding_model::{EMBEDDING_MODEL_NAME}",
            *(
            f"{chunk['page_number']}::"
            f"{chunk['chunk_id']}::"
            f"{chunk['text']}"
                for chunk in chunks
            ),
        ]
    )

    document_hash = hashlib.sha256(
        fingerprint_text.encode("utf-8")
    ).hexdigest()[:12]

    collection_name = f"document_{document_hash}"

    chroma_client = chromadb.Client()

    collection = chroma_client.get_or_create_collection(
        name=collection_name,
        configuration={
            "hnsw": {
                "space": "cosine",
            }
        },
    )

    chunk_ids = [
        f"chunk_{chunk['chunk_id']}"
        for chunk in chunks
    ]

    metadata_list = [
        {
            "chunk_id": chunk["chunk_id"],
            "page_number": chunk["page_number"],
            "word_count": chunk["word_count"],
            "section_title": chunk.get("section_title", "Genel"),
        }
        for chunk in chunks
    ]

    collection.upsert(
        ids=chunk_ids,
        embeddings=embeddings.tolist(),
        documents=original_texts,
        metadatas=metadata_list,
    )

    embedding_dimension = embeddings.shape[1]

    return collection, embedding_dimension


def retrieve_relevant_chunks(
    question: str,
    collection: Any,
    embedding_model: SentenceTransformer,
    top_k: int = 3,
) -> list[dict]:
    """
    Kullanıcının sorusunu embedding'e dönüştürür
    ve en alakalı chunk'ları Chroma'dan getirir.
    """

    clean_question = question.strip()

    if not clean_question:
        raise ValueError("Soru boş bırakılamaz.")

    query_text = f"query: {clean_question}"

    query_embedding = embedding_model.encode(
        [query_text],
        normalize_embeddings=True,
        show_progress_bar=False,
    )

    # Önce geniş bir semantic aday havuzu getir, ardından sorudaki açık
    # anahtar kelime ve sayıları da dikkate alarak yeniden sırala.
    candidate_count = min(
        max(top_k * 8, 24),
        collection.count(),
    )

    query_results = collection.query(
        query_embeddings=query_embedding.tolist(),
        n_results=candidate_count,
        include=[
            "documents",
            "metadatas",
            "distances",
        ],
    )

    documents = query_results["documents"][0]
    metadatas = query_results["metadatas"][0]
    distances = query_results["distances"][0]

    candidate_chunks = []

    for document, metadata, distance in zip(
        documents,
        metadatas,
        distances,
    ):
        semantic_similarity = 1.0 - float(distance)
        lexical_score = _lexical_coverage(
            clean_question,
            document,
        )
        retrieval_score = semantic_similarity + (0.12 * lexical_score)

        candidate_chunks.append(
            {
                "chunk_id": metadata["chunk_id"],
                "page_number": metadata["page_number"],
                "word_count": metadata["word_count"],
                "text": document,
                "distance": float(distance),
                "lexical_score": lexical_score,
                "retrieval_score": retrieval_score,
            }
        )

    candidate_chunks.sort(
        key=lambda chunk: chunk["retrieval_score"],
        reverse=True,
    )

    return candidate_chunks[:top_k]

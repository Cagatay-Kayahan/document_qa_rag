from typing import Any

import hashlib
import chromadb
from sentence_transformers import SentenceTransformer


EMBEDDING_MODEL_NAME = "intfloat/multilingual-e5-small"


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

    result_count = min(
        top_k,
        collection.count(),
    )

    query_results = collection.query(
        query_embeddings=query_embedding.tolist(),
        n_results=result_count,
        include=[
            "documents",
            "metadatas",
            "distances",
        ],
    )

    documents = query_results["documents"][0]
    metadatas = query_results["metadatas"][0]
    distances = query_results["distances"][0]

    retrieved_chunks = []

    for document, metadata, distance in zip(
        documents,
        metadatas,
        distances,
    ):
        retrieved_chunks.append(
            {
                "chunk_id": metadata["chunk_id"],
                "page_number": metadata["page_number"],
                "word_count": metadata["word_count"],
                "text": document,
                "distance": float(distance),
            }
        )

    return retrieved_chunks

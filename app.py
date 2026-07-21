import time

import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError

from src.chunker import create_chunks
from src.cloud_llm_client import (
    GEMINI_MODEL_NAME,
    generate_cloud_answer,
    has_configured_gemini_key,
)
from src.document_loader import load_document
from src.llm_client import (
    generate_answer,
    get_available_models,
)
from src.vector_store import (
    EMBEDDING_MODEL_NAME,
    create_vector_store,
    load_embedding_model,
    retrieve_relevant_chunks,
)


GEMMA_MODEL_ID = "google/gemma-4-e4b"

BLOCKED_LOCAL_MODEL_TERMS = (
    "embedding",
    "embed",
    "qwen",
)


@st.cache_resource
def get_embedding_model():
    """
    Embedding modelinin Streamlit her yenilendiğinde
    yeniden yüklenmesini engeller.
    """

    return load_embedding_model()


@st.cache_resource(show_spinner=False)
def build_document_index(
    file_name: str,
    file_bytes: bytes,
    chunk_size: int,
    chunk_overlap: int,
):
    """Aynı dokümanı Streamlit rerun'larında yeniden indekslemeyi önler."""

    document_pages = load_document(
        file_name=file_name,
        file_bytes=file_bytes,
    )

    if not document_pages:
        raise ValueError(
            "Dosyanın içerisinde okunabilir metin bulunamadı."
        )

    chunks = create_chunks(
        document_pages=document_pages,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )

    collection, embedding_dimension = create_vector_store(
        chunks=chunks,
        embedding_model=get_embedding_model(),
    )

    return document_pages, chunks, collection, embedding_dimension


def get_local_chat_models() -> list[str]:
    """
    LM Studio'daki sohbet modellerini getirir.

    Embedding modelleri ve Qwen ailesi kullanıcı
    seçim listesinden çıkarılır.
    """

    available_models = get_available_models()

    return [
        model_id
        for model_id in available_models
        if not any(
            blocked_term in model_id.lower()
            for blocked_term in BLOCKED_LOCAL_MODEL_TERMS
        )
    ]


@st.cache_data(ttl=5, show_spinner=False)
def detect_local_chat_models() -> list[str]:
    """LM Studio erişilebiliyorsa local sohbet modellerini döndürür."""

    try:
        return get_local_chat_models()
    except (ConnectionError, RuntimeError):
        return []


def get_streamlit_gemini_key() -> str | None:
    """Streamlit Cloud secrets içindeki Gemini anahtarını güvenle okur."""

    try:
        api_key = str(st.secrets.get("GEMINI_API_KEY", "")).strip()
    except (FileNotFoundError, KeyError, StreamlitSecretNotFoundError):
        return None

    return api_key or None


def show_sources(relevant_chunks: list[dict]) -> None:
    """
    Her iki cevap modeline de verilen ortak kaynakları gösterir.
    """

    st.subheader("Cevabın dayandığı kaynaklar")

    for rank, chunk in enumerate(
        relevant_chunks,
        start=1,
    ):
        source_title = (
            f"Kaynak {rank} | "
            f"Chunk {chunk['chunk_id']} | "
            f"Sayfa {chunk['page_number']} | "
            f"Cosine distance: {chunk['distance']:.4f}"
        )

        with st.expander(
            source_title,
            expanded=(rank == 1),
        ):
            st.write(chunk["text"])

            st.caption(
                f"Kelime sayısı: {chunk['word_count']}"
            )


st.set_page_config(
    page_title="Doküman Soru-Cevap Sistemi",
    page_icon="📄",
    layout="wide",
)

st.title("📄 RAG Doküman Soru-Cevap Sistemi")

st.write(
    "PDF veya TXT dokümanınızı yükleyin. Sistem dokümandan "
    "alakalı kaynakları bulup seçtiğiniz LLM ile cevap oluştursun."
)


# -------------------------------------------------
# SIDEBAR AYARLARI
# -------------------------------------------------

st.sidebar.header("Chunk ayarları")

chunk_size = st.sidebar.slider(
    "Chunk size",
    min_value=50,
    max_value=300,
    value=120,
    step=10,
)

chunk_overlap = st.sidebar.slider(
    "Chunk overlap",
    min_value=0,
    max_value=100,
    value=25,
    step=5,
)

st.sidebar.header("Retrieval ayarları")

top_k = st.sidebar.slider(
    "Getirilecek chunk sayısı",
    min_value=1,
    max_value=5,
    value=3,
    step=1,
)


# -------------------------------------------------
# DOSYA YÜKLEME
# -------------------------------------------------

uploaded_file = st.file_uploader(
    "Doküman yükleyin",
    type=["pdf", "txt"],
)

if uploaded_file is None:
    st.info("Başlamak için PDF veya TXT dosyası yükleyin.")
    st.stop()


try:
    file_bytes = uploaded_file.getvalue()

    with st.spinner(
        "Doküman işleniyor ve vector database hazırlanıyor..."
    ):
        (
            document_pages,
            chunks,
            collection,
            embedding_dimension,
        ) = build_document_index(
            file_name=uploaded_file.name,
            file_bytes=file_bytes,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

    embedding_model = get_embedding_model()

    st.success(
        "Doküman işlendi ve vector database oluşturuldu."
    )


    # -------------------------------------------------
    # DOKÜMAN BİLGİLERİ
    # -------------------------------------------------

    first_column, second_column, third_column, fourth_column = (
        st.columns(4)
    )

    first_column.metric(
        "Sayfa/Bölüm",
        len(document_pages),
    )

    second_column.metric(
        "Chunk sayısı",
        len(chunks),
    )

    third_column.metric(
        "Vector kaydı",
        collection.count(),
    )

    fourth_column.metric(
        "Embedding boyutu",
        embedding_dimension,
    )

    st.caption(
        f"Kullanılan embedding modeli: {EMBEDDING_MODEL_NAME}"
    )

    st.divider()


    # -------------------------------------------------
    # LLM SAĞLAYICI SEÇİMİ
    # -------------------------------------------------

    st.subheader("Dokümana soru sor")

    local_chat_models = detect_local_chat_models()
    provider_options = ["Cloud - Gemini"]

    if local_chat_models:
        provider_options.append("Local - LM Studio")

    if GEMMA_MODEL_ID in local_chat_models:
        provider_options.append("Karşılaştır - Gemini ve Gemma")

    provider = st.radio(
        "Cevap sağlayıcısı",
        options=provider_options,
        horizontal=True,
    )

    selected_local_model = None
    provider_ready = True
    effective_gemini_key = None

    if provider != "Local - LM Studio":
        configured_streamlit_key = get_streamlit_gemini_key()
        configured_key_exists = (
            configured_streamlit_key is not None
            or has_configured_gemini_key()
        )

        user_gemini_key = st.text_input(
            "Kendi Gemini API anahtarınız",
            type="password",
            placeholder=(
                "İsteğe bağlı" if configured_key_exists
                else "Cloud cevap için gerekli"
            ),
            help=(
                "Girilen anahtar yalnızca bu oturumdaki Gemini isteklerinde "
                "kullanılır ve proje dosyalarına kaydedilmez."
            ),
        ).strip()

        effective_gemini_key = (
            user_gemini_key
            or configured_streamlit_key
            or None
        )

        if configured_key_exists:
            st.caption(
                "Alanı boş bırakırsanız uygulamada tanımlı Gemini anahtarı "
                "kullanılır. Kota doluysa kendi anahtarınızla devam edebilirsiniz."
            )
        elif not user_gemini_key:
            st.warning(
                "Bu yayında ortak Gemini anahtarı tanımlı değil. "
                "Soru sormak için kendi API anahtarınızı girin."
            )
            provider_ready = False

    if provider == "Cloud - Gemini":
        st.info(
            f"Cloud model kullanılacak: {GEMINI_MODEL_NAME}"
        )

    elif provider == "Local - LM Studio":
        if provider_ready:
            if not local_chat_models:
                st.error(
                    "LM Studio'da kullanılabilir bir local sohbet "
                    "modeli bulunamadı."
                )
                provider_ready = False

            else:
                default_model_index = (
                    local_chat_models.index(GEMMA_MODEL_ID)
                    if GEMMA_MODEL_ID in local_chat_models
                    else 0
                )

                selected_local_model = st.selectbox(
                    "Kullanılacak local LLM",
                    options=local_chat_models,
                    index=default_model_index,
                )

    elif provider_ready:
        if GEMMA_MODEL_ID not in local_chat_models:
            st.error(
                "Karşılaştırma modu için Gemma modeli "
                "LM Studio'da yüklü ve hazır olmalıdır."
            )
            provider_ready = False

        else:
            st.info(
                "Aynı soru ve aynı kaynak chunk'lar "
                f"{GEMINI_MODEL_NAME} ile {GEMMA_MODEL_ID} "
                "modellerine gönderilecektir."
            )


    # -------------------------------------------------
    # SORU-CEVAP FORMU
    # -------------------------------------------------

    if provider_ready:
        with st.form("question_answer_form"):
            question = st.text_input(
                "Sorunuz",
                placeholder=(
                    "Örnek: Gemma neden daha güvenilir bulundu?"
                ),
            )

            ask_button = st.form_submit_button(
                "Soruyu cevapla"
            )


        if ask_button:
            if not question.strip():
                st.warning("Lütfen önce bir soru yazın.")

            else:
                # Retrieval yalnızca bir kez yapılır.
                # Karşılaştırmada iki model de aynı kaynakları kullanır.
                with st.spinner(
                    "Soruyla alakalı kaynaklar aranıyor..."
                ):
                    relevant_chunks = retrieve_relevant_chunks(
                        question=question,
                        collection=collection,
                        embedding_model=embedding_model,
                        top_k=top_k,
                    )


                # -----------------------------------------
                # YALNIZCA CLOUD GEMINI
                # -----------------------------------------

                if provider == "Cloud - Gemini":
                    answer_start_time = time.perf_counter()

                    try:
                        with st.spinner(
                            "Gemini kaynakları okuyarak "
                            "cevap oluşturuyor..."
                        ):
                            answer = generate_cloud_answer(
                                question=question,
                                relevant_chunks=relevant_chunks,
                                api_key=effective_gemini_key,
                            )

                        answer_duration = (
                            time.perf_counter() - answer_start_time
                        )

                        st.subheader("Cevap")
                        st.write(answer)

                        model_column, time_column = st.columns(2)

                        model_column.metric(
                            "Kullanılan model",
                            GEMINI_MODEL_NAME,
                        )

                        time_column.metric(
                            "Cevap üretme süresi",
                            f"{answer_duration:.2f} saniye",
                        )

                    except Exception as error:
                        st.error(f"Gemini cevap üretemedi: {error}")


                # -----------------------------------------
                # YALNIZCA LOCAL MODEL
                # -----------------------------------------

                elif provider == "Local - LM Studio":
                    answer_start_time = time.perf_counter()

                    try:
                        with st.spinner(
                            "Local LLM kaynakları okuyarak "
                            "cevap oluşturuyor..."
                        ):
                            answer = generate_answer(
                                question=question,
                                relevant_chunks=relevant_chunks,
                                model_id=selected_local_model,
                            )

                        answer_duration = (
                            time.perf_counter() - answer_start_time
                        )

                        st.subheader("Cevap")
                        st.write(answer)

                        model_column, time_column = st.columns(2)

                        model_column.metric(
                            "Kullanılan model",
                            selected_local_model,
                        )

                        time_column.metric(
                            "Cevap üretme süresi",
                            f"{answer_duration:.2f} saniye",
                        )

                    except Exception as error:
                        st.error(f"Local LLM cevap üretemedi: {error}")


                # -----------------------------------------
                # GEMINI - GEMMA KARŞILAŞTIRMASI
                # -----------------------------------------

                else:
                    cloud_answer = None
                    cloud_duration = None
                    cloud_error = None
                    cloud_start_time = time.perf_counter()

                    try:
                        with st.spinner(
                            "Gemini cevap oluşturuyor..."
                        ):
                            cloud_answer = generate_cloud_answer(
                                question=question,
                                relevant_chunks=relevant_chunks,
                                api_key=effective_gemini_key,
                            )

                        cloud_duration = (
                            time.perf_counter() - cloud_start_time
                        )

                    except Exception as error:
                        cloud_error = str(error)

                    local_answer = None
                    local_duration = None
                    local_error = None
                    local_start_time = time.perf_counter()

                    try:
                        with st.spinner(
                            "Gemma cevap oluşturuyor..."
                        ):
                            local_answer = generate_answer(
                                question=question,
                                relevant_chunks=relevant_chunks,
                                model_id=GEMMA_MODEL_ID,
                            )

                        local_duration = (
                            time.perf_counter() - local_start_time
                        )

                    except Exception as error:
                        local_error = str(error)


                    cloud_column, local_column = st.columns(2)

                    with cloud_column:
                        st.subheader("Cloud Gemini")
                        if cloud_error:
                            st.error(f"Cevap üretilemedi: {cloud_error}")
                        else:
                            st.write(cloud_answer)

                        st.metric(
                            "Kullanılan model",
                            GEMINI_MODEL_NAME,
                        )

                        if cloud_duration is not None:
                            st.metric(
                                "Cevap üretme süresi",
                                f"{cloud_duration:.2f} saniye",
                            )

                    with local_column:
                        st.subheader("Local Gemma")
                        if local_error:
                            st.error(f"Cevap üretilemedi: {local_error}")
                        else:
                            st.write(local_answer)

                        st.metric(
                            "Kullanılan model",
                            GEMMA_MODEL_ID,
                        )

                        if local_duration is not None:
                            st.metric(
                                "Cevap üretme süresi",
                                f"{local_duration:.2f} saniye",
                            )


                # İki model için de kullanılan kaynaklar ortaktır.
                show_sources(relevant_chunks)


    # -------------------------------------------------
    # BÜTÜN CHUNK'LAR
    # -------------------------------------------------

    st.divider()

    st.subheader("Dokümandaki bütün chunk'lar")

    for chunk in chunks:
        chunk_title = (
            f"Chunk {chunk['chunk_id']} | "
            f"Sayfa {chunk['page_number']} | "
            f"{chunk['word_count']} kelime"
        )

        with st.expander(chunk_title):
            st.write(chunk["text"])


except ValueError as error:
    st.error(str(error))

except Exception as error:
    st.error(
        f"Doküman işlenirken bir hata oluştu: {error}"
    )

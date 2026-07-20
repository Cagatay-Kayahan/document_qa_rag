# RAG Doküman Soru-Cevap Sistemi

PDF veya TXT dokümanlarından kaynak göstererek cevap üreten bir RAG uygulamasıdır. Sistem dokümanı işler, soruyla en ilgili parçaları ChromaDB üzerinden bulur ve aynı kaynakları Cloud Gemini, LM Studio'daki local model veya karşılaştırma modunda iki modele birden gönderir.

## Özellikler

- PDF ve TXT yükleme
- PDF sayfa bilgisini koruyan metin çıkarma
- Başlık ve paragraf duyarlı chunking
- Çok dilli E5 embedding modeliyle anlamsal arama
- ChromaDB üzerinde cosine distance tabanlı retrieval
- Cloud Gemini ve LM Studio local model desteği
- Gemini-Gemma karşılaştırma modu
- Cevabın dayandığı chunk ve sayfaların gösterilmesi

## Sistem Akışı

```text
Doküman -> metin çıkarma -> chunking -> embedding -> ChromaDB
                                                        |
Soru -> query embedding -> en ilgili chunk'lar ----------+
                                                        |
                   Cloud Gemini / Local LLM -> cevap + kaynaklar
```

## Kullanılan Yapılar

| Bileşen | Seçim |
|---|---|
| Arayüz | Streamlit |
| PDF işleme | PyMuPDF |
| Embedding | `intfloat/multilingual-e5-small` |
| Embedding boyutu | 384 |
| Vector database | ChromaDB |
| Cloud LLM | `gemini-3.5-flash` |
| Ana local LLM | `google/gemma-4-e4b` |
| Local sunucu | LM Studio native API |

Cloud modunda dokümanın tamamı değil, retrieval sonucunda seçilen chunk'lar Gemini API'ye gönderilir. Local modda kaynaklar cihaz dışına çıkmaz.

## Gereksinimler

- Windows 10/11
- Python 3.11 veya 3.12 önerilir
- Cloud modu için Gemini API anahtarı
- Local mod için LM Studio 0.4.0 veya üzeri ve yüklenmiş bir sohbet modeli
- Karşılaştırma modu için hem Gemini anahtarı hem LM Studio'da `google/gemma-4-e4b`

## Kurulum

```powershell
git clone https://github.com/Cagatay-Kayahan/document_qa_rag.git
cd document_qa_rag

py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Bilgisayarda Python 3.12 yoksa ilk komutu `py -m venv .venv` olarak çalıştırabilirsiniz.

PowerShell aktivasyon izni vermezse yalnızca açık terminal için:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

## Cloud Gemini Ayarı

Örnek ortam dosyasını kopyalayın:

```powershell
Copy-Item .env.example .env
```

`.env` dosyasını açıp kendi anahtarınızı ekleyin:

```env
GEMINI_API_KEY=KENDI_API_ANAHTARINIZ
```

Gerçek `.env` dosyası Git tarafından yok sayılır. Anahtarınızı kaynak koda, README'ye veya commit mesajına yazmayın.

## Local LM Studio Ayarı

1. LM Studio'yu kurun ve bir sohbet modeli indirin.
2. Developer bölümünden local server'ı başlatın.
3. Sunucunun `http://127.0.0.1:1234` adresinde çalıştığını doğrulayın.
4. Ana karşılaştırma için model kimliğinin `google/gemma-4-e4b` olduğundan emin olun.

Local seçim menüsünde embedding modelleri ve Qwen ailesi gösterilmez. Uygun başka LM Studio sohbet modelleri local modda seçilebilir.

## Çalıştırma

```powershell
python -m streamlit run app.py
```

Uygulama varsayılan olarak [http://localhost:8501](http://localhost:8501) adresinde açılır.

## Kullanım Modları

- **Cloud - Gemini:** Yalnız Gemini anahtarı gerekir.
- **Local - LM Studio:** Yalnız çalışan LM Studio sunucusu ve local model gerekir.
- **Karşılaştır - Gemini ve Gemma:** Aynı soru, prompt ve kaynak chunk'lar iki modele gönderilir.

## Chunking ve Retrieval

İlk kelime tabanlı yaklaşım bölüm ve paragraf sınırlarını karıştırdığı için başlık/paragraf duyarlı chunking uygulanmıştır. Deneylerde kullanılan ayarlar:

```text
Chunk size: 120 kelime
Chunk overlap: 25 kelime
Top-k: 3
```

Beş soruluk test setinde doğru kaynak her soruda ilk sırada bulunmuştur:

```text
Top-1: 5/5
Hit@3: 5/5
```

Bu oran yalnızca sağlanan deney dokümanı ve test soruları için geçerlidir; tüm dokümanlara genellenmemelidir.

## Model Karşılaştırması

Aşağıdaki süreler retrieval sonrasında yalnızca cevap üretme çağrısını ölçer:

| Soru | Cloud Gemini | Local Gemma | Sonuç |
|---|---:|---:|---|
| XZ-91 hallucination farkı | 2.13 sn | 3.84 sn | İkisi de doğru |
| Phi neden güvenilir bulunmadı? | 1.32 sn | 4.74 sn | İkisi de doğru |
| Prompta bağlam eklenince ne değişti? | 6.85 sn | 8.51 sn | İkisi de doğru |
| Local kullanımın artıları ve eksileri | 1.80 sn | 4.90 sn | İkisi de doğru |
| Hızlı modeller neden seçilmedi? | 1.82 sn | 2.28 sn | İkisi de doğru |
| **Ortalama** | **2.78 sn** | **4.85 sn** | - |

Ek gecikme testinde aynı kısa soru için Gemini süreleri 46.88, 31.02 ve 3.80 saniye ölçülmüştür; Gemma iki tekrarda 1 saniyenin altında kalmıştır. Bu gözlem cloud gecikmesinin değişken olabileceğini, local çalışmanın ise bazı kısa sorularda daha kararlı olabildiğini göstermektedir.

## Negatif Testler

İki cevap bulunmama senaryosu denenmiştir:

1. Dokümanla alakasız şirket gelir hedefi sorusu.
2. Gemma, token ve context window terimlerini içeren fakat istenen sayısal kapasitenin dokümanda bulunmadığı yüksek benzerlikli soru.

Her iki model de sayı veya bilgi uydurmak yerine cevabın dokümanda bulunmadığını belirtmiştir.

## Raporlar

- [Deneylerde kullanılan Local LLM gözlem raporu](docs/llm_rapor.pdf)
- [RAG teknik raporu](docs/RAG_Dokuman_Soru_Cevap_Teknik_Rapor.pdf)

İlk PDF aynı zamanda uygulamayı hızlıca denemek için örnek giriş dokümanı olarak kullanılabilir.

## Testler

Syntax ve çekirdek fonksiyon testleri:

```powershell
python -m compileall -q app.py src tests
python -m unittest discover -s tests -v
```

Cloud bağlantısı isteğe bağlı olarak şu komutla doğrulanabilir; bu komut Gemini kotası kullanır:

```powershell
python -c "from src.cloud_llm_client import test_cloud_connection; print(test_cloud_connection())"
```

Local model listesini doğrulamak için LM Studio açıkken:

```powershell
python -c "from src.llm_client import get_available_models; print(get_available_models())"
```

## Proje Yapısı

```text
document_qa_rag/
|-- app.py
|-- README.md
|-- requirements.txt
|-- .env.example
|-- .gitignore
|-- data/
|   `-- .gitkeep
|-- docs/
|   |-- llm_rapor.pdf
|   `-- RAG_Dokuman_Soru_Cevap_Teknik_Rapor.pdf
|-- src/
|   |-- __init__.py
|   |-- document_loader.py
|   |-- chunker.py
|   |-- vector_store.py
|   |-- llm_client.py
|   `-- cloud_llm_client.py
`-- tests/
    `-- test_core.py
```

## Sınırlamalar ve Güvenlik

- Taranmış, metin katmanı olmayan PDF'lerde OCR yoktur.
- PDF tablolarının satır-sütun ilişkisi düz metne dönüşürken bozulabilir.
- Chroma verisi uygulama süreci içinde geçici olarak tutulur.
- Cloud modunda seçilen kaynak chunk'lar üçüncü taraf API'ye gönderilir.
- Yüklenen dokümanlar güvenilmeyen içerik kabul edilse de LLM'ler prompt injection girişimlerine karşı kusursuz güvence vermez.
- Local performans donanıma, cloud gecikmesi ağ ve servis durumuna bağlıdır.

## Gelecek Geliştirmeler

- OCR ve gelişmiş tablo çıkarımı
- Reranker ve answerability katmanı
- Token tabanlı veya semantik chunking
- Çoklu doküman ve kalıcı vector database desteği
- Güvenli tool calling ile canlı API/veritabanı bağlantıları
- Daha geniş otomatik retrieval ve cevap değerlendirme seti

## Sonuç

Uygulama PDF/TXT işleme, embedding, retrieval, cloud/local cevap üretimi ve kaynak gösterme akışını uçtan uca tamamlar. Deney setinde Gemini daha akıcı ve çoğu soruda hızlı; Gemma ise doküman verisini cihazda tutan, doğru ve doğrudan bir alternatif olarak gözlemlenmiştir.

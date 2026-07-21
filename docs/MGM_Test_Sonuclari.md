# MGM Farklı Alan Testi Sonuçları

## Test Ortamı

- Doküman: `Haziran_2025_Sicaklik_Yagis_Degerlendirmesi.pdf`
- Kaynak: Meteoroloji Genel Müdürlüğü
- Sayfa: 25
- Chunk: 40
- Chunk size / overlap / top-k: 120 / 25 / 3
- Embedding: `intfloat/multilingual-e5-small`
- Cloud model: `gemini-3.5-flash`
- Local model: `google/gemma-4-e4b`

Cosine distance değerleri yalnız semantic yakınlığı gösterir. Son sıralama semantic skor ile Türkçe anahtar kelime/sayı eşleşmesinin birleşimidir; bu nedenle daha düşük distance değerine sahip bir chunk her zaman üst sırada olmayabilir.

## 1. Türkiye Ortalama Sıcaklığı

**Soru:** 2025 Haziran ayında Türkiye ortalama sıcaklığı kaç dereceydi ve 1991-2020 normalinden kaç derece yüksekti?

**Beklenen:** 23.0°C; normal 21.8°C; normalin 1.2°C üzerinde.

**Kaynaklar:** Chunk 15 / sayfa 6 / 0.0659; Chunk 11 / sayfa 5 / 0.0674; Chunk 12 / sayfa 5 / 0.0709.

- Gemini: Doğru, 1.28 sn.
- Gemma: 21.8°C ile 23.0°C değerlerini ters yorumladı, 3.22 sn.
- Sonuç: Retrieval gerekli kanıtı getirdi; local üretim modeli çelişkili çıkarılmış metni yanlış yorumladı.

## 2. Türkiye Geneli Uç Sıcaklıklar

**Soru:** Türkiye genelinde Haziran 2025'te ölçülen en düşük ve en yüksek sıcaklık hangi merkezlerde ve kaç °C idi?

**Beklenen:** Erzurum -0.2°C; Cizre 45.6°C.

**Kaynaklar:** Chunk 11 / sayfa 5 / 0.0907; Chunk 17 / sayfa 8 / 0.0779; Chunk 15 / sayfa 6 / 0.0820.

- Gemini: Doğru, 1.07 sn.
- Gemma: Doğru, 2.11 sn.
- Sonuç: Hibrit retrieval, ulusal özet chunk'ını ilk sıraya taşıdı.

## 3. 2024-2025 Yağış Karşılaştırması

**Soru:** Türkiye geneli Haziran 2025 yağışı, uzun yıllar normali ve Haziran 2024 yağışıyla karşılaştırıldığında nasıl değişti?

**Beklenen:** 12.5 mm; 33.6 mm normalin %63 altında; 2024'teki 11.9 mm'ye göre %5 artış.

**Kaynaklar:** Chunk 27 / sayfa 16 / 0.0715; Chunk 12 / sayfa 5 / 0.0895; Chunk 31 / sayfa 18 / 0.0836.

- Gemini: Doğru, 1.31 sn.
- Gemma: Doğru, 4.49 sn.
- Sonuç: Sayı duyarlı yeniden sıralama ile 2024 bilgisi ilk üç kaynağa girdi.

## 4. En Büyük Bölgesel Yağış Azalması

**Soru:** Haziran 2025'te yağış normaline göre en büyük azalma hangi coğrafi bölgede görüldü; gerçekleşen yağış, normal ve azalma oranı neydi?

**Beklenen:** Marmara; 2.4 mm; normali 41.5 mm; %94.2 azalma.

**Kaynaklar:** Chunk 27 / sayfa 16 / 0.0734; Chunk 33 / sayfa 19 / 0.0847; Chunk 12 / sayfa 5 / 0.0861.

- Gemini: Doğru, 1.07 sn.
- Gemma: Güneydoğu Anadolu ve %80.4 cevabını verdi; yanlış, 3.25 sn.
- Sonuç: Doğru tablo ilk üçte olmasına rağmen local model maksimum azalmayı seçemedi.

## 5. Karadeniz-Güneydoğu Anadolu Karşılaştırması

**Soru:** Karadeniz ve Güneydoğu Anadolu bölgelerini Haziran 2025 yağış miktarı ve normalden azalma oranı bakımından karşılaştır.

**Beklenen:** Karadeniz 27.6/58.7 mm ve %52.9 azalma; Güneydoğu Anadolu 1.7/8.7 mm ve %80.4 azalma.

**Kaynaklar:** Chunk 33 / sayfa 19 / 0.0829; Chunk 36 / sayfa 22 / 0.0739; Chunk 37 / sayfa 23 / 0.0826.

- Gemini: Doğru, 1.71 sn.
- Gemma: Doğru, 8.31 sn.
- Sonuç: Bölgesel tablo ilk sırada bulundu ve iki model de doğru sentez yaptı.

## 6. Havza ve Yağışlı Gün Sentezi

**Soru:** En büyük yağış azalması hangi havzada gerçekleşti ve Türkiye'deki ortalama yağışlı gün sayısı normaline göre ne kadar düştü?

**Beklenen:** Kuzey Ege Havzası %97 azalma; 6.5 günden 3.3 güne, yani 3.2 gün düşüş.

**Kaynaklar:** Chunk 39 / sayfa 24 / 0.1198; Chunk 38 / sayfa 23 / 0.1263; Chunk 30 / sayfa 17 / 0.1180.

- Gemini: Doğru, 1.18 sn.
- Gemma: Değerleri doğru verdi; düşüşü açıkça hesaplamadı, 2.43 sn.
- Sonuç: İki ayrı bölümden kanıt başarıyla birleştirildi.

## 7. Cevabı Bulunmayan Ekonomik Kayıp Sorusu

**Soru:** Raporda Haziran 2025 yağış azlığının tarımsal üretimde kaç milyon TL ekonomik kayba yol açtığı belirtiliyor?

**Beklenen:** Bu bilgi dokümanda bulunmuyor.

**Kaynaklar:** Chunk 27 / sayfa 16 / 0.1034; Chunk 31 / sayfa 18 / 0.1116; Chunk 33 / sayfa 19 / 0.1172.

- Gemma: Bilgi uydurmadı, 1.15 sn.
- Gemini: Ön denemede bilgi uydurmadı; final seride ücretsiz günlük kota dolduğu için 429 hatası döndü.
- Sonuç: Yüksek konu benzerliğine rağmen local model güvenli cevap verdi; cloud kota bağımlılığı gözlendi.

## 8. Görsel Tablo Sorusu

**Soru:** Haziran 2025'te yeni ekstrem maksimum sıcaklık rekoru kırılan beş istasyonun adlarını ve yeni değerlerini listele.

**PDF'deki doğru değerler:** Florya 37.2°C, Dikili 41.7°C, İzmir 41.8°C, Seferihisar 40.6°C, Sinop 33.7°C.

**Kaynaklar:** Chunk 26 / sayfa 15 / 0.0828; Chunk 18 / sayfa 9 / 0.1101; Chunk 19 / sayfa 10 / 0.1147.

- Gemma: Cevabın bulunmadığını söyledi, 0.95 sn.
- Gemini: Ön denemede cevabın bulunmadığını söyledi.
- Sonuç: Tablo hücreleri PDF'de görsel olarak yer aldığı için PyMuPDF metnine çıkmadı. Modeller isim uydurmadı; soru cevaplanamadı. OCR veya tablo çıkarımı gerekir.

## Genel Değerlendirme

- Cevaplanabilir altı soruda gerekli kanıt Hit@3 bakımından 6/6 bulundu.
- Gemini: 6/6 doğru, ortalama 1.27 sn.
- Gemma: 4/6 doğru, ortalama 3.97 sn.
- Cevabı olmayan iki durumda uydurma gözlemlenmedi.
- Retrieval başarısı, cevap modelinin kanıtı doğru yorumlayacağını tek başına garanti etmedi.
- Görsel tablo, OCR bulunmadığı için temel başarısızlık örneği oldu.

# Yazılımcıya Teslim Notu — Ölçme ve Değerlendirme Modülü

Bu paket, BCN LearnDNA ana geliştirme dokümanındaki **Bölüm 4 (Sınav Yönetimi)**,
**Bölüm 5 (El Yazısı Çözüm Analizi)** ve **Motor 1 (Yapay Zekâ Hata Muhakemesi)** kapsamının
çalışan kodudur. Maket değildir: backend, veritabanı göçü, öğretmen ekranları ve testler çalışır durumdadır.

## Paket içeriği

```
backend/    FastAPI + SQLAlchemy 2 + Alembic + SymPy + Celery
  app/services/error_reasoning.py   Hata muhakeme motoru (saf Python, DB'siz, test edilebilir)
  app/services/math_verify.py       Güvenli SymPy doğrulama (eval enjeksiyonuna karşı beyaz liste)
  app/services/item_analysis.py     Madde analizi: p, r_pbis, D, KR-20/α, SEM, çeldirici analizi
  app/services/calibration.py       Öğretmen onaylarından güven kalibrasyonu
  app/services/pipeline.py          Belge işleme iş akışı ve durum makinesi
  app/services/ai/providers.py      Sağlayıcı soyutlaması (mock + OpenAI uyumlu)
  app/api/                          REST uç noktaları (RBAC + kiracı izolasyonu)
  alembic/versions/0001_*.py        PostgreSQL göçü
  tests/                            42 test (SQLite ve PostgreSQL'de geçiyor)
frontend/   Next.js 16 + React 19 + TypeScript + Tailwind 4
  app/ogretmen/sinavlar             Sınav listesi, yeni sınav, sınav detayı (4 sekme)
  app/ogretmen/analiz/[id]          3 panelli analiz ekranı (kâğıt · adımlar · AI analizi)
  app/ogretmen/inceleme             İnceleme kuyruğu
  components/UploadModal.tsx        "Yeni Öğrenci Yükle" (tekli + toplu)
docs/       Mimari, AI motoru, veritabanı, güvenlik, kararlar, OpenAPI sözleşmesi, ekran görüntüleri
```

## Doğrulananlar (bu teslimde fiilen çalıştırıldı)
* `pytest` → **42/42** geçti (SQLite ve gerçek PostgreSQL 16).
* `alembic upgrade head → downgrade base → upgrade head` ve `alembic check` temiz.
* `npm run typecheck`, `npm test` (vitest), `npm run build` başarılı.
* Seed verisiyle uçtan uca: giriş → sınav → kâğıt yükleme → işleme → analiz → onay;
  ekran görüntüleri `docs/screenshots/` klasöründe.

## Mutlaka bilinmesi gerekenler
1. **Gerçek el yazısı tanıma henüz bağlı değil.** Varsayılan sağlayıcı *mock*'tur ve el yazısı
   okumaz; tüm cevaplar "öğretmen incelemesi gerekiyor" durumuna düşer ve arayüzde **SİMÜLASYON**
   etiketi görünür. Geliştirme ortamında taramanın yanına `*.transcript.json` yüklenerek tam akış denenebilir.
   Gerçek sağlayıcı için `.env` içinde `LEARNDNA_VISION_PROVIDER=openai_compatible` ve ilgili anahtarlar
   tanımlanmalı — **ücretli API kullanımı ve yurt dışına veri aktarımı (KVKK m.9) için önce onay alınmalı.**
2. Hata kategorisi, doğruluk ve puan **deterministik kod + SymPy** ile belirlenir; dil modeli yalnızca
   öğretmene "doğrulanmamış açıklama" metni üretir, karar vermez.
3. Güven değerleri belgelenmiş sezgisel değerlerdir; öğretmen onay/düzeltmeleri biriktikçe
   dedektör bazında otomatik kalibre olur. Psikometrik olarak doğrulanmış model iddiası yoktur.
4. Madde analizi ve kazanım raporu **gözlenen sınav istatistiğidir**, "hakimiyet (mastery)" tahmini değildir (Faz 4).
5. `[CORE]` işaretli tablolar (kurum, kullanıcı, sınıf, öğrenci, kazanım) modülün tek başına çalışması
   için asgari düzeyde eklendi; ana monorepoya alınırken Faz 1 ekibinin tablolarıyla birleştirilmeli.

## Henüz yapılmayanlar (bilerek kapsam dışı / sonraki adım)
Kitapçıktan otomatik soru çıkarımı · optik form okuma · kısmi puan rubriği · PDF üzerinde bölge
işaretleme · S3 depolama adaptörü · öğrenci/veli sonuç ekranları · PDF raporlar · hız sınırlama ·
OpenTelemetry · CI'da Playwright E2E. Ayrıntı: `docs/ASSESSMENT_MODULE.md` → "Remaining work".

## Hızlı başlangıç
`README.md` dosyasına bakın. Demo giriş: **ogretmen@demo.bcn / Demo123!** (tüm veriler sentetiktir).

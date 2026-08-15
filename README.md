# USTA — Universal Servis & Teknik Asistan

Sinyalin olmadığı sahada çalışan, **çok markalı motor sürücüsü (VFD) arıza asistanı.**
Tüm çıkarım cihaz üzerinde yapılır — çalışırken tek bir ağ isteği gönderilmez.

> Bir fabrika hattında Siemens, ABB ve Danfoss sürücüleri yan yana çalışır.
> Teknisyen üç ayrı manueli taşıyamaz; sahada çoğu zaman internet de yoktur.
> USTA bu üç manueli tek bir çevrimdışı asistanda birleştirir.

<!-- TODO: demo GIF veya ekran görüntüsü — Wi-Fi kapalıyken sorgu → cevap -->

---

## Özellikler

- **Tam çevrimdışı** — Microsoft Foundry Local ile cihaz üstü LLM çıkarımı, sıfır ağ isteği
- **Çok markalı bilgi tabanı** — Siemens SINAMICS G120, ABB ACS580, Danfoss VLT FC 302
- **Hibrit arama** — hata kodu sorgularında birebir SQL eşleşmesi, doğal dil sorgularında BM25 + vektör benzerliği
- **Kaynak atıflı cevaplar** — her cevap manuel adı ve sayfa numarası ile döner
- **Bilmediğini söyler** — bağlamda karşılığı olmayan soruda uydurmaz, reddeder
- **Güvenlik uyarıları korunur** — müdahale adımı içeren cevaplara manueldeki ilgili uyarı her zaman eklenir

---

## Mimari

```
   Kullanıcı sorgusu
          │
          ▼
   ┌──────────────────┐
   │  Retrieval katmanı│   hata kodu var mı?  ──EVET──▶  SQLite indeksli SELECT
   │   (hibrit arama)  │                       ──HAYIR─▶  FTS5 (BM25) + vektör
   └──────────────────┘                                   → skor birleştirme
          │
          ▼  top-3 chunk + sayfa no
   ┌──────────────────┐
   │  Foundry Local   │   cihaz üstü LLM — bağlamla cevap üretimi
   └──────────────────┘
          │
          ▼
   Cevap + kaynak atfı
```

| Katman | Teknoloji |
|---|---|
| Arayüz | CLI (birincil), Streamlit (opsiyonel) |
| Orkestrasyon | Python 3.12 |
| Veri | SQLite + FTS5 |
| Embedding | `qwen3-embedding-0.6b` — 1024 boyut, ~0.2 sn |
| Üretim | `qwen3-4b` — 40.960 token bağlam |

---

## Kurulum

### Gereksinimler

- macOS 14+ (Apple Silicon) veya Windows 11
- Python **3.12** — 3.13/3.14 ile paket uyumluluk sorunları çıkabilir
- ~4 GB boş disk (runtime 201 MB + modeller 3.4 GB + venv ~600 MB)

### 1. Foundry Local

```bash
# macOS
brew tap microsoft/foundrylocal
brew trust microsoft/foundrylocal   # Homebrew 6.x üçüncü taraf tap'lerde şart
brew install foundrylocal

foundry --version                   # doğrulandı: 0.10.3
```

<!-- TODO: Windows kurulum komutunu ekle (winget) -->

### 2. Modelleri indir

```bash
foundry model download qwen3-4b               # 2.9 GB — sohbet
foundry model download qwen3-embedding-0.6b   # 515 MB — embedding

foundry cache list                            # indirilenleri gör
foundry cache location                        # -> ~/.foundry/cache/models
```

`foundry model run` yerine `download` kullanılıyor; `run` etkileşimli sohbet
açar ve script içinde işe yaramaz.

### 3. Python ortamı

```bash
python3.12 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 4. Doğrula

```bash
.venv/bin/python scripts/hello_model.py
```

Her iki modelin de yüklendiğini ve cevap ürettiğini teyit eder.

---

## Bilgi tabanını hazırlama

Manuel PDF'leri depoya dahil edilmez (telif). `data/manuals/` altına kendin indir:

| Marka | Dosya adı | Kaynak |
|---|---|---|
| Siemens | `siemens_g120c_list_manual.pdf` | [cache.industry.siemens.com](https://cache.industry.siemens.com/dl/files/780/99683780/att_863315/v1/G120C_List_Manual_LH13_0414_eng.pdf) |
| ABB | `abb_acs580_firmware_manual.pdf` | [library.e.abb.com](https://library.e.abb.com/public/d03c76db17d34239a838ed3baf814028/EN_ACS580_FW_J_A5.pdf) |
| Danfoss | `danfoss_fc302_programming_guide.pdf` | [files.danfoss.com](https://files.danfoss.com/download/Drives/MG33MO02.pdf) |

Not: Siemens'in destek portalı (`support.industry.siemens.com`) oturum ister ve
403 döner; yukarıdaki CDN adresi anonim erişime açıktır.

Ardından ingestion'ı çalıştır:

```bash
.venv/bin/python -m src.ingest
```

Beklenen çıktı:

```
  Danfoss   112 chunk
  Siemens   277 chunk
  ABB       191 chunk
  580 chunk embed ediliyor (32'lik gruplar)...
  hata kodu  : {'Danfoss': 112, 'Siemens': 277, 'ABB': 191}
```

---

## Kullanım

### CLI

```bash
.venv/bin/python main.py
```

```
USTA> F30002 ne demek

F30002 — Power unit: DC link voltage overvoltage
(FAULT — sürücü durur)

Neden:
The power unit has detected an overvoltage condition in the DC link.
- motor regenerates too much energy.
- line supply voltage too high.
Çözüm:
- increase the ramp-down time (p1121).

  Kaynaklar:
    · F30002 Siemens SINAMICS G120C, s.523
  [exact | arama 0.0 sn | toplam 0.0 sn]
```

### Streamlit arayüzü

```bash
.venv/bin/streamlit run app.py
```

Tarayıcıda **http://localhost:8501** açılır.

> **Güvenlik notu:** `.streamlit/config.toml` sunucuyu `localhost`'a bağlar.
> Streamlit varsayılanda `0.0.0.0` dinler ve "Network URL" / "External URL"
> yayınlar — yani uygulama yerel ağa, NAT yapılandırmasına bağlı olarak
> internete açılır. Tesis dokümanı barındıran ve çevrimdışı çalışması gereken
> bir araçta bu kabul edilemez. Bu ayarı değiştirme.

Arayüz tasarım kararları:

- **Aciliyet ayrımı renkle SINIRLI DEĞİL.** `FAULT — sürücü durur` ve
  `ALARM — çalışmaya devam eder` rozetleri metin de taşır (WCAG
  *color-not-only*): renk körü bir teknisyen bu farkı kaçırmamalı.
- **Google Fonts kullanılmıyor.** CDN'den font çekmek çevrimdışı vaadini bozar
  ve internetsiz ortamda sayfayı bozar. Sistem font yığını kullanılıyor.
- **Yol göstergesi görünür.** Cevabın altında `indeksli eşleşme — model
  çağrılmadı` veya `hibrit arama` yazar; kullanıcı neden hızlı/yavaş olduğunu
  görür.
- **`ağ isteği 0`** her cevabın altında sabit — ürünün tek vaadi bu.

---

## Proje yapısı

```
usta/
├── main.py                CLI giriş noktası
├── app.py                 Streamlit arayüzü
├── config.py              model adları, top_k, dosya yolları
├── requirements.txt
├── .streamlit/config.toml  sunucuyu localhost'a bağlar (güvenlik)
├── src/
│   ├── ingest.py          PDF → chunk → embedding → SQLite
│   ├── parsers.py         marka bazlı fault-table ayrıştırıcıları
│   ├── db.py              şema, FTS5 tetikleyicileri, vektör saklama
│   ├── retrieval.py       hibrit arama (exact + BM25 + vektör)
│   ├── query.py           Türkçe sorgu → İngilizce çeviri + terim sözlüğü
│   ├── prompts.py         sistem prompt'u, bağlam kurma
│   ├── output.py          düşünme bloğu, tekrar temizleme, akış
│   └── assistant.py       uçtan uca akış
├── data/
│   ├── manuals/           kaynak PDF'ler (git'e girmez)
│   └── usta.db            SQLite (git'e girmez)
├── eval/
│   ├── golden_set.yaml    50 soruluk değerlendirme seti
│   └── run_eval.py
└── docs/
    ├── proje-brief.html      proje brief'i (tarayıcıda aç)
    └── demo-day-sunum.html   sunum, 10 slayt
```

---

## Makine yükünü düşük tutmak

Foundry Local modelleri **GPU'da** çalıştırır. `ps` çıktısındaki CPU yüzdesi bunu
göstermez — Apple Silicon'da GPU yükü orada görünmez. Uzun koşularda makine ısınır;
zararlı değildir (macOS termal yönetimi kendisi kısar) ama gereksizdir.

```bash
# Ölçüm: cevap üretimi olmadan (GPU'yu neredeyse hiç yormaz, ~2 dk)
.venv/bin/python eval/run_eval.py --kapsama-atla

# Ölçüm: kısmi koşu, her kategoriden orantılı örnek
.venv/bin/python eval/run_eval.py --limit 10 --cevaplarla

# İş bitince servisi durdur (arka planda çalışmaya devam eder)
foundry server stop
foundry status          # "Service: Not running" görmelisin
```

Tam koşu (`--cevaplarla`, 50 soru) yaklaşık 10-12 dakika kesintisiz GPU üretimi
demektir. Regresyon kontrolü için `--kapsama-atla` ile retrieval-only koşu yeterli;
tam koşuyu yalnızca cevap kalitesi ölçülecekse çalıştır.

---

## Değerlendirme

```bash
.venv/bin/python eval/run_eval.py --kapsama-atla     # hızlı
.venv/bin/python eval/run_eval.py --esik-tara        # eşik kalibrasyonu
.venv/bin/python eval/run_eval.py --cevaplarla       # cevap üretimi dahil
```

50 soruluk sette ölçülen (`CHAT_SEED=42` ile tekrarlanabilir):

| Metrik | Hedef | Ölçülen | |
|---|---|---|---|
| Recall@3 · kod sorguları | ≥ 0.95 | **1.00** | ✅ |
| Recall@3 · belirti | ≥ 0.80 | **0.90** | ✅ |
| Recall@3 · prosedür | — | 0.70 | ⚠ |
| Recall@3 · markalar arası | — | 0.80 | ✅ |
| Sadakat (referanslar bağlamda mı) | ≥ 0.85 | **0.96** | ✅ |
| Reddetme oranı (cevaplanamaz) | 1.00 | **1.00** | ✅ |
| Gecikme p95 · retrieval | ≤ 5 sn | **3.93 sn** | ✅ |
| Gecikme · exact yol (toplam) | ≤ 5 sn | **0.0 sn** | ✅ |
| Gecikme · hibrit yol (toplam) | ≤ 5 sn | ~12 sn | ❌ |

Prosedür kategorisinin düşük kalmasının sebebi eşik değil **kapsam**: bilgi tabanına
yalnızca arıza bölümleri alındı, parametre bölümleri alınmadı. "Rampa süresi hangi
parametreyle uzatılır" sorusunun cevabı veritabanında yok.

Hibrit yolun gecikmesi model+donanım sınırı: qwen3-4b bu makinede ~20 token/sn
üretiyor. Kod sorguları (setin %30'u) ve reddetmeler (%20'si) LLM'e hiç gitmiyor.

---

## Tasarım kararları

**Neden saf vektör araması değil?**
Embedding modelleri kısa alfanümerik kodları ayırt edemez — `F30002` ile `F30003`
string olarak neredeyse aynıdır ve vektörleri de neredeyse aynı çıkar. Kosinüs
benzerliği bu ikisini karıştırır, yani sistem tam olarak en kritik sorguda yanlış
hata kodunu getirir. Bu yüzden kod içeren sorgular vektör aramasına hiç girmiyor,
indeksli birebir SQL eşleşmesine yönlendiriliyor.

**Neden bir hata kodu = bir chunk?**
Manuellerdeki fault list'ler tablo halindedir. Sabit boyutlu bölme satırı ortadan
keser, kod bir chunk'ta kalırken çözümü diğerine düşer. Ayrıca 15 alakasız kod
içeren bir chunk'ın embedding'i bulanıklaşır ve hiçbir sorguyla iyi eşleşmez.

**Neden vektör veritabanı yok?**
~1.500 chunk × 1024 boyut × 4 byte ≈ 6 MB. NumPy ile tek matris çarpımı milisaniye
sürüyor. Bu ölçekte ayrı bir vektör veritabanı katmanı karmaşıklıktan başka bir şey
getirmezdi.

**Neden Phi değil Qwen?**
Plan dokümanı Phi-3.5 Mini öneriyor ("veya benzeri 3-5B model"). Bu projede
sorgular Türkçe, manueller İngilizce olacağı için çok dilli yeteneği belirgin
şekilde güçlü olan Qwen ailesi seçildi. Embedding modelinin de aynı aileden
olması, diller arası eşleşmede tutarlılık sağlıyor.

**Örnekleme ayarları neden bu değerlerde?**
İlk testte `temperature=0.2` ile model tekrarlama döngüsüne girdi — aynı cümleyi
altı kez üretip token limitini doldurdu, yanıt 17.7 sn sürdü. `frequency_penalty=0.9`
bunu çözdü ve aynı soru 9.3 sn'de temiz cevaba indi. Değerler `config.py`'de,
düşürmeden önce tekrarlama davranışını yeniden ölçün.

### SDK sürüm tuzağı

Microsoft Learn tutorial'ındaki ve plan dokümanındaki örnek kod **eski SDK'ya**
aittir ve `foundry-local-sdk` 1.2.x ile çalışmaz:

```python
# ESKİ — çalışmaz (ModuleNotFoundError: foundry_local)
from foundry_local import FoundryLocalManager
manager = FoundryLocalManager(alias)
client = openai.OpenAI(base_url=manager.endpoint, api_key=manager.api_key)

# GÜNCEL — 1.2.x
from foundry_local_sdk import Configuration, FoundryLocalManager
FoundryLocalManager.initialize(Configuration(
    app_name="USTA",
    model_cache_dir=str(Path.home() / ".foundry" / "cache" / "models"),
))
model = FoundryLocalManager.instance.catalog.get_model(alias)
model.load()
chat = model.get_chat_client()          # embedding: get_embedding_client()
```

`model_cache_dir` verilmezse SDK kendi uygulama dizinine bakar ve CLI ile
indirilmiş modelleri bulamaz — hata `Model path does not exist` olur.

**Neden exact yolda LLM çağrılmıyor?**
Kod sorgusunda manuelin kendi girdisi zaten cevabın kendisidir. Ölçtük: LLM
cevabının içeriği %90 manuelden birebir geliyordu. Doğrudan biçimlendirmek
15.5 sn'yi 0.0 sn'ye indirdi ve sadakati tanım gereği 1.00 yaptı.

**Neden reddetme kararı prompt'a bırakılmıyor?**
"Bilmiyorsan söyle" talimatı yetmedi — format talimatı ağır basınca model
fiyat sorusuna IGBT overload cevabı verdi. Karar artık deterministik bir
benzerlik eşiği (`ALAKA_ESIGI`); eşiğin altında model hiç çağrılmıyor.

---

## Bilinen limitler

- Bilgi tabanı yalnızca üç sürücü ailesini kapsar; kapsam dışı ekipman sorularında sistem reddeder
- OCR yok — taranmış (görüntü tabanlı) manueller işlenemez
- **Çok dilli davranış ölçüldü:** embedding modeli Türkçe sorguyla İngilizce
  dokümanı eşleştiremiyor (çevirisiz recall 0/4). Sorgular aramadan önce
  İngilizceye çevriliyor; bu +1.5-3 sn maliyet getiriyor. Daha büyük embedding
  modeli (8B) denendi ve bu sorunu çözmedi (5/8), 6 GB RAM'e karşılık kazanç yok.
- **Cevap dili karışık:** teknik terimler bilinçli olarak İngilizce bırakılıyor
  (yanlış çeviri sahada tehlikeli), iskelet Türkçe. Kod sorgularında cevap
  tamamen manuelin İngilizce metnidir.

<!-- TODO: değerlendirme sonrası tespit edilen limitleri ekle -->

---

## ⚠ Güvenlik

Bu araç bir **doküman arama aracıdır**, servis prosedürünün yerine geçmez.

Motor sürücülerinde DC bara kondansatörleri güç kesildikten sonra dakikalarca
yüksek gerilim tutar. Enerjili veya yeni enerjisi kesilmiş ekipmanda yapılacak her
müdahalede LOTO (lockout/tagout) uygulanması ve üreticinin belirttiği bekleme
süresine uyulması zorunludur.

---

## Belgeler

| Belge | Açıklama |
|---|---|
| [`docs/proje-brief.html`](docs/proje-brief.html) | Proje brief'i — kapsam, mimari, teknik kararlar, ölçülmüş sonuçlar, model deneyleri |
| [`docs/demo-day-sunum.html`](docs/demo-day-sunum.html) | Demo day sunumu, 10 slayt |

İkisi de tek dosyalık, bağımlılıksız HTML — tarayıcıda doğrudan açılır.
Ayrıntı: [`docs/README.md`](docs/README.md)

---

## Kaynaklar

- [Building Your First Local RAG Application with Foundry Local](https://techcommunity.microsoft.com/blog/azuredevcommunityblog/building-your-first-local-rag-application-with-foundry-local/4501968) — Microsoft Tech Community
- [What is Foundry Local?](https://learn.microsoft.com/azure/ai-foundry/foundry-local/) — Microsoft Learn
- [Tutorial: Build a RAG application](https://learn.microsoft.com/azure/ai-foundry/foundry-local/) — Microsoft Learn
- [SQLite FTS5](https://sqlite.org/fts5.html)

---

## Lisans

Kod [MIT](LICENSE) lisansı altındadır.

Bilgi tabanını oluşturan üretici manuelleri telif hakkı sahiplerine aittir ve
depoya **dahil edilmemiştir** — `data/manuals/` `.gitignore`'dadır. Kurulum
bölümündeki bağlantılardan kendin indirmen gerekir.

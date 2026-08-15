"""USTA yapılandırması — tüm sabitler tek yerde."""

from pathlib import Path

ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
MANUALS_DIR = DATA_DIR / "manuals"
DB_PATH = DATA_DIR / "usta.db"

# Foundry Local model alias'ları (`foundry model list` ile teyit edildi, v0.10.3).
#
# Plan dokümanı Phi-3.5 Mini öneriyor ("veya benzeri 3-5B model") ama bu proje
# için Qwen tercih edildi: sorgular Türkçe, manueller İngilizce olacak ve Qwen
# ailesi çok dilli görevlerde Phi'den belirgin şekilde güçlü. Embedding modelinin
# de aynı aileden olması, diller arası eşleşmede tutarlılık sağlıyor.
#
# Karşılaştırma için Hafta 4'te phi-3.5-mini (2.2 GB) indirilebilir.
CHAT_MODEL = "qwen3-4b"                     # 2.9 GB, GPU
EMBEDDING_MODEL = "qwen3-embedding-0.6b"    # 515 MB, GPU

# SDK varsayılan olarak uygulamaya özel bir önbellek dizinine bakar; `foundry`
# CLI ise modelleri buraya indirir. Açıkça bağlanmazsa SDK indirilmiş modelleri
# bulamaz ("Model path does not exist").
MODEL_CACHE_DIR = Path.home() / ".foundry" / "cache" / "models"

APP_NAME = "USTA"

# Örnekleme ayarları — Hafta 1'de ölçülerek belirlendi, tahmin değil.
#
# temperature=0.2 ile model tekrarlama döngüsüne giriyordu: aynı cümleyi
# ("Cihazın elektrik bağlantısını kesin.") altı kez üretip token limitini
# doldurdu ve yanıt 17.7 sn sürdü. frequency_penalty bunu çözdü — aynı soru
# 9.3 sn'ye ve temiz bir cevaba indi. Bu değerleri düşürmeden önce
# tekrarlama davranışını yeniden ölç.
CHAT_TEMPERATURE = 0.6
CHAT_TOP_P = 0.9
CHAT_FREQUENCY_PENALTY = 0.9
# Gecikme ve GPU yükü doğrudan üretilen token sayısıyla orantılı:
#     512 -> p95 40.4 sn
#     384 -> p95 28.7 sn
#     192 -> hedeflenen ~8 sn
#
# 192 seçildi. Bu bir ÜRÜN KARARI değil, proje kararı: uygulama sahada
# kullanılmayacak, dolayısıyla uzun cevabın değeri düşük; buna karşılık
# geliştirme makinesini saatlerce GPU yükü altında tutmanın maliyeti gerçek.
# Cevaplar kısalıyor (madde başına açıklama kırpılıyor), ama retrieval ve
# kaynak atfı — projenin asıl gösterdiği şeyler — hiç etkilenmiyor.
CHAT_MAX_TOKENS = 192

# Hafta 3 ölçümü: RAG bağlamıyla birlikte frequency_penalty tek başına yetmedi,
# model cümleleri tekrarlamaya devam etti. presence_penalty eklenince tekrar
# sıfırlandı (aynı soruda 4 tekrarlı satır -> 0). max_tokens 320'de cevap
# ortasından kesiliyordu, 512'ye çıkarıldı.
CHAT_PRESENCE_PENALTY = 0.6

# qwen3-4b bir reasoning modeli: cevaptan önce <think> bloğu üretir.
# Prompt'a "/no_think" eklense bile boş bir blok gelebiliyor, temizlemek şart.
THINK_PATTERN = r"<think>.*?(?:</think>|$)"
NO_THINK_PREFIX = "/no_think "

# Retrieval
TOP_K = 3

# Hata/alarm kodu desenleri — MARKA BAŞINA FARKLI.
#
# Hafta 1'de manueller incelendiğinde üç üreticinin üç ayrı kodlama şeması
# kullandığı görüldü. Tek bir global regex ile bunları yakalamak mümkün değil:
#
#   Siemens  F30002, A01009      harf + 5 hane
#   ABB      2310, A5EA, FF61    4 karakter onaltılık
#   Danfoss  ALARM 79            kelime + sayı
#
# ABB deseni tek başına tehlikeli: "2024", "0000", "FAh" gibi alakasız dizileri
# de yakalar. Bu yüzden regex'e TEK BAŞINA güvenilmiyor — ingestion sırasında
# tablolar zaten ayrıştırıldığı için var olan kodların kümesi biliniyor.
# Sorgu eşleştirmesi bu kümeye bakarak yapılır, regex yalnızca aday çıkarır.
FAULT_CODE_PATTERNS = {
    "Siemens": r"\b[FA]\d{5}\b",
    "ABB":     r"\b[0-9A-F]{4}\b",
    "Danfoss": r"\b(?:WARNING/ALARM|WARNING|ALARM)\s+(\d{1,3})\b",
}

# Bilgi tabanındaki markalar
VENDORS = ("Siemens", "ABB", "Danfoss")

# Reddetme eşiği (ham kosinüs benzerliği). Yalnızca hibrit yolu etkiler;
# exact kod eşleşmesi her zaman kabul edilir.
#
# 50 soruluk golden set ile kalibre edildi (eval/run_eval.py --esik-tara),
# 35 hibrit sorgu üzerinden:
#
#     eşik   reddetme   kaybedilen meşru sorgu
#     0.48     0.60          0
#     0.52     0.80          2
#     0.54     0.90          3
#     0.56     1.00          4      <- seçilen
#     0.60     1.00          7
#
# 0.56, reddetmeyi 1.00'e çıkaran EN DÜŞÜK eşik. Bedeli 25 hibrit sorgunun
# 4'ünü kaybetmek. Brief'in güvenlik çerçevesi bu dengeyi belirliyor: yanlış
# reddetme kullanıcıyı yorar, yanlış cevap enerjili ekipmanda tehlikelidir.
#
# Bu bedel kalıcı olmak zorunda değil. Kaybedilen sorguların çoğu prosedür
# sorusu ve asıl sebep eşik değil KAPSAM: bilgi tabanına yalnızca arıza
# bölümleri alındı, parametre bölümleri alınmadı. "Rampa süresi hangi
# parametreyle uzatılır" sorusunun cevabı veritabanında hiç yok.
ALAKA_ESIGI = 0.56

# Üretim tohumu — çıktıyı tekrarlanabilir kılar.
#
# İki gerekçe:
#  1) ÖLÇÜM: tohum olmadan çeviri adımı her koşuda farklı metin üretiyor ve
#     retrieval değişiyor. İki ardışık eval koşusunda recall B 9/10 -> 8/10,
#     C 7/10 -> 9/10 oynadı. Tekrarlanamayan ölçüm regresyon yakalayamaz.
#  2) ÜRÜN: aynı hata kodu her seferinde aynı cevabı vermeli. İki teknisyen
#     aynı arızaya bakarken farklı metin görürse araca güven kalmaz.
CHAT_SEED = 42

# Çeviri için AYRI token bütçesi.
#
# Çeviri, cevap üretimiyle aynı istemciyi kullanıyor ve aynı max_tokens'ı
# miras alıyordu. Üç kelimelik bir çeviri için 384 token bütçesi, model erken
# durmadığında 24 saniyeye kadar uzayabiliyor — ölçümde retrieval max'ının
# 23.9 sn çıkmasının sebebi buydu (retrieval'da başka LLM çağrısı yok).
#
# /no_think ile boş düşünme bloğu ~5 token, çeviri ~10 token. 64 rahat yeter.
TRANSLATE_MAX_TOKENS = 64

"""Sistem prompt'ları.

Teknik terimlerin İngilizce bırakılması bilinçli bir güvenlik kararı. Hafta 1
ölçümünde model "line supply voltage too high" ifadesini "hatasız line gerilimi"
diye çevirdi — anlam tersine döndü. Enerjili ekipmanla çalışan biri için bu
kabul edilemez. Sahada zaten "braking resistor", "ramp-down" İngilizce
kullanılıyor, yani bu hem daha güvenli hem daha doğal.
"""

CEVAP_SISTEM = """Sen USTA'sın: saha teknisyenine motor sürücüsü manuellerinden bilgi aktaran bir asistansın.

Görevin BAĞLAM'daki bilgiyi Türkçe olarak özetlemek. Yorum ekleme, tahmin yürütme.

Bağlamda sorunun cevabı yoksa TEK BİR SATIR yaz: Bu bilgi elimdeki dokümanlarda yok.

Teknik terimleri İNGİLİZCE bırak: DC link, overvoltage, undervoltage, overcurrent,
braking resistor, ramp-down, earth fault, phase loss, heatsink, short circuit.
Bunları çevirme — yanlış çeviri sahada tehlikelidir.
Parametre numaralarını (p1121, 2-15) ve hata kodlarını aynen yaz.

Cevabı şu üç başlıkla ver, her maddeyi bir kez yaz, tekrar etme:

Arıza: <tek cümle>

Nedenler:
- <bağlamdaki nedenler, en fazla 3 madde>

Yapılacaklar:
- <bağlamdaki çözüm adımları, en fazla 3 madde>

Bağlamda güvenlik uyarısı varsa sonuna "Uyarı:" satırı ekle."""


# Bağlamda chunk başına karakter sınırı.
#
# Ölçüm: tipik top-3 bağlamı ~1.500 karakter, ama en kötü durumda 13.475 —
# dokuz katı. Kuyruğu 16 uzun Siemens chunk'ı oluşturuyor ve hibrit yolun
# p95 gecikmesini 40 sn'ye çıkaran şey bu. Sınır tipik chunk'lara (Siemens
# ort. 795, diğerleri ~343) hiç dokunmuyor, yalnızca aykırıları kırpıyor.
#
# Kırpma kabul edilebilir çünkü kod sorguları artık exact yoldan tam metinle
# cevaplanıyor; hibrit yol zaten özet üretiyor.
CHUNK_SINIR = 1200


def _kirp(metin: str, sinir: int = CHUNK_SINIR) -> str:
    """Satır sınırında kırpar — cümle ortasında kesmez."""
    if len(metin) <= sinir:
        return metin
    kesik = metin[:sinir]
    son_satir = kesik.rfind("\n")
    if son_satir > sinir // 2:
        kesik = kesik[:son_satir]
    return kesik.rstrip() + "\n[...devamı manuelde]"


def baglam_kur(sonuclar) -> str:
    """Retrieval sonuçlarını prompt bağlamına dönüştürür.

    Kaynak atfı burada ekleniyor, chunk metninde değil — aynı atıf kalıbının
    580 chunk'ın embedding'inde tekrarlanması hepsini birbirine benzetirdi.
    """
    parcalar = []
    for i, s in enumerate(sonuclar, 1):
        parcalar.append(f"--- KAYNAK {i}: {s.kaynak()} ---\n{_kirp(s.content)}")
    return "\n\n".join(parcalar)


def kullanici_mesaji(baglam: str, soru: str) -> str:
    return f"BAĞLAM:\n{baglam}\n\nSORU: {soru}"

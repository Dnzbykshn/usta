"""Cevap sonrası işleme: düşünme bloğu ayıklama, tekrar temizleme, akış.

NEDEN GEREKLİ
-------------
Model kısa bağlamda tekrarlamaya giriyor. ABB chunk'ları ortalama 342 karakter
(Siemens 795); malzeme yetmeyince model aynı cümleyi beş kez yazıyor.
frequency_penalty ve presence_penalty bunu azalttı ama bitirmedi.

Aynı ilkeyi üçüncü kez uyguluyoruz: modele rica etmek yerine kodda garanti
altına al. Satır tekrarı deterministik olarak siliniyor.

Akışlı çıktı satır satır tamponlanıyor — böylece hem tekrar temizliği yapılıyor
hem de kullanıcı ilk satırı ~1 sn'de görüyor (cevabın tamamı 13-16 sn sürüyor).
"""

from __future__ import annotations

import re

_ISARET = re.compile(r"^[\s\-*•·—>#\d.)\]]+")      # madde imleri, numaralandırma
_BICIM = re.compile(r"[*_`]+")                      # markdown vurgu
_NOKTALAMA = re.compile(r"[^\w\s]+", re.UNICODE)

THINK_ACILIS = "<think>"
THINK_KAPANIS = "</think>"


# Yakın tekrar tespiti: modelin en sık ürettiği tekrar biçimi aynı cümleyi
# parantezli bir ekle uzatmak — "Toprak bağlantısını kontrol et." ardından
# "Toprak bağlantısını kontrol et (bağlantı kırık ya da yanlış)." gelir. Birebir
# karşılaştırma bunu yakalamaz, bu yüzden satırın ilk birkaç kelimesi de
# ayrı bir anahtar olarak tutuluyor.
ONEK_KELIME = 5


def _anahtar(satir: str) -> str:
    """Tekrar karşılaştırması için satırı normalleştirir.

    Model aynı cümleyi bazen madde imi veya vurgu farkıyla tekrarlıyor
    ("- Fan kırık." / "**Fan kırık**"), bu yüzden biçim atılıyor.
    """
    s = _ISARET.sub("", satir)
    s = _BICIM.sub("", s)
    s = _NOKTALAMA.sub(" ", s)
    return " ".join(s.lower().split())


def _onek(anahtar: str) -> str | None:
    """Satırın ilk ONEK_KELIME kelimesi; kısa satırlarda None (başlıklar için)."""
    kelimeler = anahtar.split()
    return " ".join(kelimeler[:ONEK_KELIME]) if len(kelimeler) >= ONEK_KELIME else None


class _Tekilleyici:
    """Birebir ve yakın tekrarları eleyen durum tutucu."""

    def __init__(self) -> None:
        self._tam: set[str] = set()
        self._onekler: set[str] = set()

    def kabul(self, anahtar: str) -> bool:
        if anahtar in self._tam:
            return False
        onek = _onek(anahtar)
        if onek and onek in self._onekler:
            return False
        self._tam.add(anahtar)
        if onek:
            self._onekler.add(onek)
        return True


def dusunmeyi_ayikla(metin: str) -> str:
    """<think> bloğunu temizler.

    Model kapanış etiketini her zaman üretmiyor ('<think>\\n\\nearth fault'
    gibi). Regex '<think>.*?(?:</think>|$)' bu durumda cevabın tamamını siler,
    çünkü non-greedy eşleşme sona kadar uzar. Kapanış var/yok ayrı ele alınıyor.
    """
    if THINK_KAPANIS in metin:
        metin = metin.split(THINK_KAPANIS, 1)[1]
    else:
        metin = metin.replace(THINK_ACILIS, "")
    return metin.strip()


def tekrarlari_temizle(metin: str) -> str:
    """Aynı satırın tekrarlarını siler, boş kalan başlıkları düşürür."""
    cikti: list[str] = []
    tekil = _Tekilleyici()

    for satir in metin.splitlines():
        a = _anahtar(satir)
        if not a:                      # boş satır — biçimi koru
            cikti.append(satir)
            continue
        if not tekil.kabul(a):
            continue
        cikti.append(satir)

    # İçeriği tamamen silinmiş başlıkları at ("Yapılacaklar:" ardından hiçbir madde yok)
    temiz: list[str] = []
    for i, satir in enumerate(cikti):
        if satir.rstrip().endswith(":"):
            sonrasi = [s for s in cikti[i + 1:] if s.strip()]
            if not sonrasi or sonrasi[0].rstrip().endswith(":"):
                continue
        temiz.append(satir)

    return re.sub(r"\n{3,}", "\n\n", "\n".join(temiz)).strip()


class CevapAkisi:
    """Akışlı çıktıyı satır satır temizleyerek yayar.

    Kullanım:
        akis = CevapAkisi()
        for parca in client.complete_streaming_chat(...):
            for satir in akis.besle(parca.choices[0].delta.content or ""):
                print(satir)
        for satir in akis.bitir():
            print(satir)
    """

    def __init__(self) -> None:
        self._tampon = ""
        self._think_bitti = False
        self._tekil = _Tekilleyici()

    def _think_kontrol(self) -> bool:
        """Düşünme bloğu geçildi mi? Geçilmediyse tamponlamaya devam."""
        if self._think_bitti:
            return True
        if THINK_KAPANIS in self._tampon:
            self._tampon = self._tampon.split(THINK_KAPANIS, 1)[1]
            self._think_bitti = True
            return True
        bas = self._tampon.lstrip()
        # Yeterince karakter geldi ve <think> ile başlamıyorsa blok yok demektir
        if len(bas) >= len(THINK_ACILIS) and not bas.startswith(THINK_ACILIS):
            self._think_bitti = True
            return True
        return False

    def _satir_ver(self, satir: str) -> str | None:
        a = _anahtar(satir)
        if not a:
            return satir
        return satir if self._tekil.kabul(a) else None

    def besle(self, parca: str) -> list[str]:
        """Yeni parçayı işler; tamamlanmış ve tekrarsız satırları döner."""
        if not parca:
            return []
        self._tampon += parca
        if not self._think_kontrol():
            return []

        *tamamlanan, self._tampon = self._tampon.split("\n")
        return [s for s in (self._satir_ver(x) for x in tamamlanan) if s is not None]

    def bitir(self) -> list[str]:
        """Tampondaki son satırı yayar."""
        self._think_kontrol()
        kalan, self._tampon = self._tampon, ""
        if not kalan.strip():
            return []
        s = self._satir_ver(kalan)
        return [s] if s is not None else []


# --- Exact eşleşmede doğrudan biçimlendirme --------------------------------
# Kod sorgusunda manuelin kendi girdisi ZATEN cevabın kendisidir. LLM'e
# göndermek üç şey maliyet: 13-16 sn gecikme, çeviri hatası riski ve
# uydurma riski. Ölçtük — F30002 cevabının içeriği zaten %90 manuelden
# birebir geliyordu. Doğrudan biçimlendirmek daha hızlı VE daha güvenli:
# sadakat tanım gereği 1.00, çünkü tek kelime değişmiyor.
#
# Türkçe olan yalnızca iskelet (alan adları). Teknik içerik İngilizce kalıyor —
# zaten sahada da İngilizce kullanılıyor ve çeviri hatası burada tehlikeli.
ALAN_ADLARI = {
    "Message class": "Mesaj sınıfı",
    "Reaction": "Tepki",
    "Acknowledge": "Onaylama",
    "Cause": "Neden",
    "Remedy": "Çözüm",
    "Fault value": "Hata değeri",
    "Alarm value": "Alarm değeri",
    "Note": "Not",
    "Notice": "Dikkat",
    "Warning": "Uyarı",
    "Troubleshooting": "Kontrol adımları",
}

# Siemens alan adlarını iki noktayla yazıyor ("Cause:"), Danfoss noktasız
# ("Troubleshooting"). İkisini de yakala.
_ALAN = re.compile(
    r"(?m)^(" + "|".join(re.escape(k) for k in ALAN_ADLARI) + r")\s*:?\s*$"
)


def bicimlendir_chunk(sonuc) -> str:
    """Bir chunk'ı LLM olmadan okunabilir cevaba dönüştürür."""
    satirlar = sonuc.content.splitlines()

    # İlk satır "KOD — Başlık", ikinci satır "[Marka Model]"
    baslik = satirlar[0] if satirlar else ""
    govde = "\n".join(satirlar[1:]).strip()
    if govde.startswith("["):
        govde = "\n".join(govde.splitlines()[1:]).strip()

    govde = _ALAN.sub(lambda m: f"{ALAN_ADLARI[m.group(1)]}:", govde)

    aciliyet = {"fault": "FAULT — sürücü durur",
                "alarm": "ALARM — sürücü çalışmaya devam eder",
                "both": "WARNING/ALARM — yapılandırmaya bağlı"}.get(sonuc.severity)

    parcalar = [baslik]
    if aciliyet:
        parcalar.append(f"({aciliyet})")
    parcalar += ["", govde]
    return "\n".join(parcalar).strip()

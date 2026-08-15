"""Marka bazlı fault-table ayrıştırıcıları.

Her üretici farklı bir kodlama şeması ve sayfa düzeni kullanıyor, bu yüzden
ortak bir ayrıştırıcı yok. Ortak olan tek şey çıktı: bir hata kodu = bir Chunk.

Kaynak atfı (manuel adı, sayfa no) bilerek chunk metnine yazılmıyor — sayfa
zaten veritabanında tutuluyor ve prompt kurulurken ekleniyor. Aynı atıf
kalıbının 1.500 chunk'ta tekrarlanması embedding'leri gereksiz yere birbirine
benzetirdi.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

import pymupdf

from .db import Chunk


def normalize(metin: str) -> str:
    """PDF ligatürlerini açar: 'deﬁned' -> 'defined', 'conﬁgurable' -> 'configurable'.

    Danfoss ve Siemens manuelleri ﬁ/ﬂ/ﬀ ligatürlerini tek karakter olarak
    gömüyor. Açılmazsa FTS5 'defined' aramasını kaçırır ve embedding'e bilinmeyen
    token girer. NFKC bunları bileşenlerine ayırır.
    """
    return unicodedata.normalize("NFKC", metin)

# --- Danfoss --------------------------------------------------------------
# Biçim:  "WARNING/ALARM 26, Brake resistor power limit"
#         "ALARM 29, Heat Sink temp"
#         "WARNING 1, 10 Volts Low"
# WARNING/ALARM alternatifte önce gelmeli, yoksa WARNING kısmı tek başına eşleşir.
DANFOSS_BASLIK = re.compile(
    r"(?m)^(WARNING/ALARM|WARNING|ALARM)\s+(\d{1,3})\s*[,.]\s*(.+?)\s*$"
)

DANFOSS_SEVERITY = {
    "WARNING": "alarm",          # sürücü çalışmaya devam eder
    "ALARM": "fault",            # sürücü durur
    "WARNING/ALARM": "both",
}

# Sayfa üstü/altı gürültüsü: yalnız sayfa numarası, üretici adı, doküman kodu
GURULTU = re.compile(
    r"(?m)^\s*(?:\d{1,3}|Danfoss\s*A/S.*|MG\d+\w*|®?\s*)\s*$"
)


def _sayfa_metinleri(pdf: Path, ilk: int, son: int) -> list[tuple[int, str]]:
    """(sayfa_no, metin) listesi. Sayfa numaraları 0-tabanlı PDF indeksidir."""
    d = pymupdf.open(pdf)
    try:
        return [(i, normalize(d[i].get_text()))
                for i in range(ilk, min(son + 1, len(d)))]
    finally:
        d.close()


def _temizle(metin: str) -> str:
    metin = GURULTU.sub("", metin)
    metin = re.sub(r"\n{3,}", "\n\n", metin)
    # Madde işaretleri kendi satırında kalıyor, sonraki satıra bağla
    metin = re.sub(r"(?m)^•\s*\n", "• ", metin)
    return metin.strip()


def parse_danfoss(pdf: Path, ilk_sayfa: int = 283, son_sayfa: int = 292,
                  model: str = "VLT AutomationDrive FC 302") -> list[Chunk]:
    """Danfoss alarm listesini bir kod = bir chunk olarak ayrıştırır."""
    sayfalar = _sayfa_metinleri(pdf, ilk_sayfa, son_sayfa)

    # Metni birleştirirken her karakterin hangi sayfadan geldiğini takip et,
    # böylece her girişe doğru sayfa numarası atanabilir.
    parcalar: list[str] = []
    sinirlar: list[tuple[int, int]] = []   # (bitis_offset, sayfa_no)
    offset = 0
    for sayfa_no, metin in sayfalar:
        parcalar.append(metin)
        offset += len(metin)
        sinirlar.append((offset, sayfa_no))
    tam = "".join(parcalar)

    def sayfa_bul(pos: int) -> int:
        for bitis, sayfa_no in sinirlar:
            if pos < bitis:
                return sayfa_no
        return sinirlar[-1][1]

    eslesmeler = list(DANFOSS_BASLIK.finditer(tam))
    chunks: list[Chunk] = []

    for i, m in enumerate(eslesmeler):
        tur, kod, baslik = m.group(1), m.group(2), m.group(3).strip()
        govde_bas = m.end()
        govde_son = eslesmeler[i + 1].start() if i + 1 < len(eslesmeler) else len(tam)
        govde = _temizle(tam[govde_bas:govde_son])

        if len(govde) < 20:          # başlık var ama içerik yok -> atla
            continue

        icerik = f"{tur} {kod} — {baslik}\n[Danfoss {model}]\n\n{govde}"
        chunks.append(Chunk(
            fault_code=kod,
            severity=DANFOSS_SEVERITY.get(tur),
            section="Warnings and alarms",
            page=sayfa_bul(m.start()),
            content=icerik,
        ))

    return chunks


# --- Siemens --------------------------------------------------------------
# Bölüm 4.2 "List of faults and alarms". Biçim:
#     F35005
#     TM54F:parallel connection not supported
#     Message class: ...
#     Reaction: ...
#     Cause: ...
#     Remedy: ...
# Kod kendi satırında, başlık bir sonraki satırda. Kodun ardından mesaj tipi
# son eki gelebiliyor — "A01009 (N)", "F01015 (A)" — bu son ek, mesajın hangi
# tiplere yeniden yapılandırılabileceğini gösterir. Yakalanmazsa 83 kod kaçıyor.
SIEMENS_BASLIK = re.compile(
    r"(?m)^([FA]\d{5})(?:[ \t]*\(([^)\n]*)\))?[ \t]*\n(.+?)[ \t]*$"
)

SIEMENS_GURULTU = re.compile(
    r"(?m)^\s*(?:SINAMICS\s+G120C"
    r"|List Manual \(LH\d+\).*"
    r"|\d+ Faults and alarms"
    r"|\d+\.\d+ List of faults and alarms"
    r"|\d{1,4})\s*$"
)


def parse_siemens(pdf: Path, ilk_sayfa: int = 462, son_sayfa: int = 545,
                  model: str = "SINAMICS G120C") -> list[Chunk]:
    """Siemens fault/alarm listesini bir kod = bir chunk olarak ayrıştırır.

    Sayfa aralığı PDF indeksidir (basılı sayfa - 1). Bölüm 4.2, basılı 463-546.
    """
    sayfalar = _sayfa_metinleri(pdf, ilk_sayfa, son_sayfa)

    parcalar: list[str] = []
    sinirlar: list[tuple[int, int]] = []
    offset = 0
    for sayfa_no, metin in sayfalar:
        temiz = SIEMENS_GURULTU.sub("", metin)
        parcalar.append(temiz)
        offset += len(temiz)
        sinirlar.append((offset, sayfa_no))
    tam = "".join(parcalar)

    def sayfa_bul(pos: int) -> int:
        for bitis, sayfa_no in sinirlar:
            if pos < bitis:
                return sayfa_no
        return sinirlar[-1][1]

    eslesmeler = list(SIEMENS_BASLIK.finditer(tam))
    chunks: list[Chunk] = []
    gorulen: set[str] = set()

    for i, m in enumerate(eslesmeler):
        kod, tip_eki, baslik = m.group(1), m.group(2), m.group(3).strip()
        if kod in gorulen:        # aynı kod ikinci kez geçerse (çapraz atıf) atla
            continue

        govde_bas = m.end()
        govde_son = eslesmeler[i + 1].start() if i + 1 < len(eslesmeler) else len(tam)
        govde = _temizle(tam[govde_bas:govde_son])

        if len(govde) < 40:
            continue

        gorulen.add(kod)
        ek = f" (yapılandırılabilir tip: {tip_eki})" if tip_eki else ""
        chunks.append(Chunk(
            fault_code=kod,
            severity="fault" if kod[0] == "F" else "alarm",
            section="List of faults and alarms",
            page=sayfa_bul(m.start()),
            content=f"{kod} — {baslik}{ek}\n[Siemens {model}]\n\n{govde}",
        ))

    return chunks


# --- ABB ------------------------------------------------------------------
# Biçim:  A2B4
#         Short circuit
#         Short-circuit in motor cable(s) or motor.        <- neden
#         Check motor and motor cable for cabling errors.  <- çözüm
#
# Zorluk: her girişin altında YARDIMCI KOD alt tabloları var (0001, 0002,
# 0004, 0008, 0010 ...) ve bunlar da dört haneli. Ayıraç: yardımcı kodlar bit
# maskesidir, yani ikinin kuvvetidir. Gerçek ABB arıza kodlarının hiçbiri
# (2310, 3130, A2B1, A5EA, FF61, 64FF ...) ikinin kuvveti değil.
ABB_KOD = re.compile(r"^([0-9A-F]{4})$")

# Metin tabanlı ayrım burada çalışmıyor: yardımcı kodlar da dört haneli ve bit
# maskesi varsayımı yetersiz kaldı (000A, 001C gibi maske olmayan yardımcı
# kodlar var). Ayrım KONUMDA: gerçek kodlar sol sütunda (x≈54), yardımcı kodlar
# girintili alt tabloda (x≈135). Bu yüzden ABB için kelime koordinatları
# kullanılıyor, düz metin değil.
ABB_SOL_SUTUN = 100.0

# DİKKAT: buraya "^\d{1,4}$" eklenmemeli. ABB kodlarının bir kısmı tamamen
# sayısal (2310, 1080, 2281) ve sayfa numarası sanılıp silinirler — arıza
# listesinin tamamı sessizce kaybolur. Sayfa numaraları zaten üç haneli,
# dört karakterlik kod deseniyle çakışmıyor.
ABB_GURULTU_SATIR = re.compile(r"^(?:Fault tracing\s+\d+|Fault messages|Warning messages)$")


def _abb_satirlar(pdf: Path, ilk: int, son: int) -> list[tuple[int, float, str]]:
    """(sayfa_no, satırın_sol_x, satır_metni) — okuma sırasında."""
    d = pymupdf.open(pdf)
    try:
        cikti: list[tuple[int, float, str]] = []
        for i in range(ilk, min(son + 1, len(d))):
            gruplar: dict[tuple[int, int], list[tuple[int, float, str]]] = {}
            for x0, _y0, _x1, _y1, kelime, blok, satir, sira in d[i].get_text("words"):
                gruplar.setdefault((blok, satir), []).append((sira, x0, kelime))
            for anahtar in sorted(gruplar):
                ws = sorted(gruplar[anahtar])
                metin = normalize(" ".join(w for _, _, w in ws)).strip()
                if metin and not ABB_GURULTU_SATIR.match(metin):
                    cikti.append((i, ws[0][1], metin))
        return cikti
    finally:
        d.close()


def parse_abb(pdf: Path, ilk_sayfa: int = 535, son_sayfa: int = 565,
              uyari_bitis: int = 547, model: str = "ACS580") -> list[Chunk]:
    """ABB uyarı ve arıza mesajlarını ayrıştırır.

    Sayfa aralıkları PDF indeksidir. Uyarılar 535-547, arızalar 548-565
    (basılı 538 ve 551; ofset +3).
    """
    satirlar = _abb_satirlar(pdf, ilk_sayfa, son_sayfa)

    # Sol sütunda duran kod satırlarının indeksleri
    basliklar = [
        i for i, (_s, x0, m) in enumerate(satirlar)
        if x0 < ABB_SOL_SUTUN and ABB_KOD.match(m)
    ]

    chunks: list[Chunk] = []
    gorulen: set[str] = set()

    for n, idx in enumerate(basliklar):
        sayfa, _x, kod = satirlar[idx]
        if kod in gorulen:
            continue

        son_idx = basliklar[n + 1] if n + 1 < len(basliklar) else len(satirlar)
        govde_satirlar = [m for _s, _x, m in satirlar[idx + 1:son_idx]]
        if not govde_satirlar:
            continue

        baslik = govde_satirlar[0]
        govde = "\n".join(govde_satirlar[1:]).strip()
        if len(govde) < 40:
            continue

        gorulen.add(kod)
        uyari = sayfa <= uyari_bitis
        chunks.append(Chunk(
            fault_code=kod,
            severity="alarm" if uyari else "fault",
            section="Warning messages" if uyari else "Fault messages",
            page=sayfa,
            content=f"{kod} — {baslik}\n[ABB {model}]\n\n{govde}",
        ))

    return chunks

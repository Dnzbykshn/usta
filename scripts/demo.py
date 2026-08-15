"""Video demosu — kendi kendine oynayan CLI gösterimi.

    .venv/bin/python scripts/demo.py

Neden var: canlı demoda yazım hatası yapmak, yanlış tuşa basmak veya
beklemek videoyu bozar. Bu script sorguları sabit tempoda yazar, cevabı
akıtır ve doğru yerlerde durur. Sen sadece kaydı başlatırsın.

Akış:
  1. Model ısıtılır (kayıt DIŞINDA — ilk sorgu ~20 sn sürer)
  2. "kaydı başlat" uyarısı, Enter beklenir
  3. Dört sorgu sırayla oynatılır (~55 sn)
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src import assistant

# ANSI — terminalde renk
R = "\033[0m"
KIRMIZI = "\033[38;5;203m"
AMBER = "\033[38;5;179m"
YESIL = "\033[38;5;79m"
GRI = "\033[38;5;245m"
BEYAZ = "\033[38;5;255m"

YAZMA_HIZI = 0.055     # karakter başına saniye — insan hızına yakın
SATIR_HIZI = 0.045     # cevap satırları arası

# (sorgu, cevap sonrası bekleme) — toplam ~55 sn, senaryodaki demo bölümü
SENARYO = [
    ("F30002 ne demek", 4.0),
    ("ALARM 28", 3.5),
    ("fren direnci arızalı", 4.5),
    ("bu sürücünün fiyatı ne kadar", 4.0),
]

BANNER = f"""{BEYAZ}
  ██  USTA — Universal Servis & Teknik Asistan
{R}{GRI}  Siemens SINAMICS G120C · ABB ACS580 · Danfoss VLT FC 302
  580 arıza kaydı · çevrimdışı · ağ isteği yok{R}
"""


def yaz(metin: str, hiz: float = YAZMA_HIZI) -> None:
    """Karakter karakter yazar — canlı yazılıyor izlenimi."""
    for k in metin:
        sys.stdout.write(k)
        sys.stdout.flush()
        time.sleep(hiz)
    print()


def sorgu_oynat(usta, soru: str, bekleme: float) -> None:
    sys.stdout.write(f"\n{YESIL}USTA>{R} ")
    sys.stdout.flush()
    yaz(soru)
    time.sleep(0.4)

    t0 = time.perf_counter()
    arama, satirlar = usta.akisli(soru, aciliyet_satiri=False)
    cevap_var = arama.alakali_mi()

    if arama.cevrildi:
        print(f"{GRI}  [arama: \"{arama.arama_sorgusu}\"]{R}")

    if cevap_var and arama.sonuclar and arama.sonuclar[0].severity:
        etiket = {"fault": (KIRMIZI, "FAULT — sürücü durur"),
                  "alarm": (AMBER, "ALARM — çalışmaya devam eder"),
                  "both": (AMBER, "WARNING/ALARM — yapılandırmaya bağlı")}
        renk, metin = etiket.get(arama.sonuclar[0].severity, (GRI, ""))
        if metin:
            print(f"  {renk}▌ {metin}{R}")

    print()
    for satir in satirlar:
        print(f"  {satir}")
        time.sleep(SATIR_HIZI)
    sure = time.perf_counter() - t0

    if cevap_var and arama.sonuclar:
        print(f"\n  {GRI}Kaynaklar{R}")
        for s in arama.sonuclar:
            kod = f"{KIRMIZI}{s.fault_code}{R} " if s.fault_code else ""
            print(f"    {GRI}·{R} {kod}{GRI}{s.kaynak()}{R}")

    yol = ("indeksli eşleşme — model çağrılmadı" if arama.yol == "exact"
           else "eşiğin altında — model çağrılmadı" if not cevap_var
           else "hibrit arama")
    print(f"\n  {GRI}[{yol} · {sure:.1f} sn · ağ isteği {YESIL}0{GRI}]{R}")
    time.sleep(bekleme)


def main() -> None:
    print(BANNER)
    print(f"{GRI}  Model ısıtılıyor — bu kısım KAYIT DIŞINDA kalmalı...{R}")
    usta = assistant.kur()
    usta.cevapla("F30002 ne demek")          # exact yolu
    usta.cevapla("soğutma fanı çalışmıyor")  # hibrit yol + çeviri modeli
    print(f"{YESIL}  Model hazır.{R}\n")

    print(f"{BEYAZ}  ┌────────────────────────────────────────────────┐")
    print(f"  │  1. Wi-Fi'yi KAPAT                             │")
    print(f"  │  2. Ekran kaydını BAŞLAT (Cmd+Shift+5)         │")
    print(f"  │  3. Bu pencereye dön ve Enter'a bas            │")
    print(f"  └────────────────────────────────────────────────┘{R}")
    try:
        input()
    except (EOFError, KeyboardInterrupt):
        return

    print("\033[2J\033[H", end="")   # ekranı temizle
    print(BANNER)
    time.sleep(1.2)

    for soru, bekleme in SENARYO:
        sorgu_oynat(usta, soru, bekleme)

    print(f"\n{GRI}  ── demo sonu ──{R}\n")
    time.sleep(2.0)


if __name__ == "__main__":
    main()

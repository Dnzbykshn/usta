"""USTA — çevrimdışı motor sürücüsü arıza asistanı. CLI giriş noktası.

    .venv/bin/python main.py
"""

import sys
import time

import config
from src import assistant

BANNER = """
  USTA — Universal Servis & Teknik Asistan
  Siemens SINAMICS G120C · ABB ACS580 · Danfoss VLT FC 302
  Çevrimdışı çalışır. Çıkmak için Ctrl-D.

  Bu araç doküman arama aracıdır, servis prosedürünün yerine geçmez.
  Enerjili ekipmanda LOTO uygulayın.
"""


def main() -> None:
    if not config.DB_PATH.exists():
        sys.exit(f"Bilgi tabanı yok: {config.DB_PATH}\n"
                 f"Önce çalıştır: .venv/bin/python -m src.ingest")

    print(BANNER)
    print("  Modeller yükleniyor...", end=" ", flush=True)
    usta = assistant.kur()
    n = usta.conn.execute("SELECT count(*) c FROM chunks").fetchone()["c"]
    print(f"hazır ({n} chunk)\n")

    while True:
        try:
            soru = input("USTA> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not soru:
            continue

        t0 = time.perf_counter()
        arama, satirlar = usta.akisli(soru)
        t_arama = time.perf_counter() - t0

        if arama.cevrildi:
            print(f'  [arama: "{arama.arama_sorgusu}"]')
        print()

        ilk_satir = None
        for satir in satirlar:
            if ilk_satir is None:
                ilk_satir = time.perf_counter() - t0
            print(satir)
        toplam = time.perf_counter() - t0

        print()
        if arama.sonuclar:
            print("  Kaynaklar:")
            for s in arama.sonuclar:
                kod = f"{s.fault_code} " if s.fault_code else ""
                print(f"    · {kod}{s.kaynak()}")
        print(f"  [{arama.yol} | arama {t_arama:.1f} sn | "
              f"ilk satır {ilk_satir or 0:.1f} sn | toplam {toplam:.1f} sn]\n")


if __name__ == "__main__":
    main()

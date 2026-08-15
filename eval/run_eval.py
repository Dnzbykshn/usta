"""USTA değerlendirme koşucusu.

    .venv/bin/python eval/run_eval.py              # retrieval metrikleri (hızlı)
    .venv/bin/python eval/run_eval.py --esik-tara  # reddetme eşiği kalibrasyonu
    .venv/bin/python eval/run_eval.py --cevaplarla # cevap üretimi dahil (~12 dk)

Varsayılan koşu cevap üretmez: 50 soru × ~14 sn = 12 dakika sürer ve
retrieval metriklerini ölçmek için gerekmez.
"""

from __future__ import annotations

import argparse
import re
import statistics
import sys
import time
from pathlib import Path

import numpy as np
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent))

import config
from src import assistant, db
from src.parsers import parse_abb, parse_danfoss, parse_siemens

# Cevapta geçen teknik referanslar bağlamda da geçmeli. Uydurulmuş bir
# parametre numarası sahada yanlış ayara yol açar — bu doğrudan güvenlik
# metriği, üslup değil.
REFERANS = re.compile(r"\b(?:[pr]\d{3,5}|\d{1,2}-\d{2}|[FA]\d{5}|[0-9A-F]{4})\b")

KATEGORI_ADI = {
    "A": "birebir kod", "B": "belirti", "C": "prosedür",
    "D": "markalar arası", "E": "cevaplanamaz",
}


# --------------------------------------------------------------- kapsama
def kapsama_testi(conn) -> bool:
    """Ayrıştırıcı sessiz veri kaybı yapıyor mu?

    Bu test Hafta 3'te iki kez hayat kurtardı: Siemens'in "(N)" son eki 277
    koddan 83'ünü sessizce düşürüyordu, ABB'nin gürültü filtresi sayısal
    kodların tamamını siliyordu. Hiçbiri hata vermedi — yalnızca bağımsız
    sayımla karşılaştırınca ortaya çıktı.
    """
    beklenen = {
        "Danfoss": (parse_danfoss, "danfoss_fc302_programming_guide.pdf"),
        "Siemens": (parse_siemens, "siemens_g120c_list_manual.pdf"),
        "ABB": (parse_abb, "abb_acs580_firmware_manual.pdf"),
    }
    print("\nKAPSAMA (ayrıştırıcı → veritabanı)")
    tamam = True
    for marka, (parser, dosya) in beklenen.items():
        yol = config.MANUALS_DIR / dosya
        if not yol.exists():
            print(f"  {marka:8s} manuel yok, atlandı")
            continue
        ayristirilan = len({c.fault_code for c in parser(yol)})
        vt = conn.execute(
            "SELECT count(DISTINCT c.fault_code) n FROM chunks c "
            "JOIN documents d ON d.id = c.doc_id WHERE d.vendor = ?", (marka,)
        ).fetchone()["n"]
        ok = ayristirilan == vt
        tamam &= ok
        print(f"  {marka:8s} ayrıştırılan {ayristirilan:3d} | veritabanı {vt:3d}  "
              f"{'OK' if ok else '!! KAYIP'}")
    return tamam


# --------------------------------------------------------------- koşu
def isindir(usta) -> None:
    """Ölçümden önce modelleri belleğe al.

    İlk sorgu model yükleme + ilk prefill maliyetini taşıyor ve tek başına
    p95'i bozuyordu (retrieval max 21.8 sn, cevap p95 39.6 sn). Bu bir
    ölçüm artefaktı, kullanıcının gördüğü sürekli rejim değil.
    """
    usta.cevapla("F30002 ne demek")          # exact yol
    usta.cevapla("soğutma fanı çalışmıyor")  # hibrit yol + çeviri


def kosu(usta, sorular: list[dict], k: int) -> list[dict]:
    sonuclar = []
    for i, s in enumerate(sorular, 1):
        t = time.perf_counter()
        arama = usta.ara(s["soru"])
        sure = time.perf_counter() - t

        kodlar = [str(x.fault_code) for x in arama.sonuclar[:k]]
        beklenen = {str(x) for x in s.get("beklenen", [])}
        sonuclar.append({
            **s,
            "kodlar": kodlar,
            "isabet": bool(beklenen & set(kodlar)),
            "benzerlik": arama.en_iyi_benzerlik,
            "yol": arama.yol,
            "alakali": arama.alakali_mi(),
            "sure": sure,
        })
        print(f"  {i:2d}/{len(sorular)} {s['id']}", end="\r", flush=True)
    print(" " * 30, end="\r")
    return sonuclar


def rapor(sonuclar: list[dict], k: int) -> None:
    print(f"\nRETRIEVAL (Recall@{k})")
    for kat in "ABCD":
        grup = [r for r in sonuclar if r["kategori"] == kat]
        if not grup:
            continue
        isabet = sum(r["isabet"] for r in grup)
        yanlis_ret = sum(1 for r in grup if not r["alakali"])
        print(f"  {kat} {KATEGORI_ADI[kat]:16s} {isabet:2d}/{len(grup):2d} = "
              f"{isabet/len(grup):.2f}   yanlış reddetme: {yanlis_ret}")

    e = [r for r in sonuclar if r["kategori"] == "E"]
    if e:
        ret = sum(1 for r in e if not r["alakali"])
        print(f"\nREDDETME (kategori E)")
        print(f"  {ret}/{len(e)} = {ret/len(e):.2f}   hedef 1.00")
        for r in e:
            if r["alakali"]:
                print(f"    KAÇAK  {r['id']} {r['soru'][:38]:38s} benzerlik {r['benzerlik']:.3f}")

    sureler = sorted(r["sure"] for r in sonuclar)
    p = lambda q: sureler[min(int(len(sureler) * q), len(sureler) - 1)]
    print(f"\nGECİKME (retrieval)")
    print(f"  ortalama {statistics.mean(sureler):.2f} sn | p50 {p(.5):.2f} | "
          f"p95 {p(.95):.2f} | max {sureler[-1]:.2f}")

    yollar = {}
    for r in sonuclar:
        yollar[r["yol"]] = yollar.get(r["yol"], 0) + 1
    print(f"  yol dağılımı: {yollar}")

    kacan = [r for r in sonuclar if r["kategori"] in "ABCD" and not r["isabet"]]
    if kacan:
        print(f"\nKAÇAN SORULAR ({len(kacan)})")
        for r in kacan:
            print(f"  {r['id']} {r['soru'][:44]:44s} benzerlik {r['benzerlik']:.3f} "
                  f"-> {r['kodlar']}")


# --------------------------------------------------------------- eşik
def esik_tara(sonuclar: list[dict]) -> None:
    """Reddetme eşiğini kalibre eder.

    Eşik yalnızca hibrit yolu etkiler; exact eşleşme her zaman kabul edilir.
    """
    hibrit = [r for r in sonuclar if r["yol"] == "hibrit"]
    cevaplanmali = [r for r in hibrit if r["kategori"] != "E"]
    reddedilmeli = [r for r in hibrit if r["kategori"] == "E"]
    if not cevaplanmali or not reddedilmeli:
        print("\nEŞİK TARAMASI: yeterli hibrit örnek yok")
        return

    print(f"\nEŞİK TARAMASI  ({len(cevaplanmali)} cevaplanmalı / "
          f"{len(reddedilmeli)} reddedilmeli, hibrit yol)")
    print("  eşik   kabul  reddet   kaçak  yanlış-ret   not")
    en_iyi = None
    for esik in [x / 100 for x in range(40, 71, 2)]:
        kacak = sum(1 for r in reddedilmeli if r["benzerlik"] >= esik)
        yanlis = sum(1 for r in cevaplanmali if r["benzerlik"] < esik)
        kabul = len(cevaplanmali) - yanlis
        not_ = ""
        if kacak == 0 and (en_iyi is None or yanlis < en_iyi[1]):
            en_iyi = (esik, yanlis)
            not_ = "<- reddetme 1.00, en az kayıp"
        print(f"  {esik:.2f}   {kabul:3d}    {len(reddedilmeli)-kacak:3d}     "
              f"{kacak:3d}      {yanlis:3d}       {not_}")

    if en_iyi:
        print(f"\n  ÖNERİLEN: ALAKA_ESIGI = {en_iyi[0]:.2f}  "
              f"(reddetme 1.00, {en_iyi[1]} meşru sorgu kaybı)")
        print(f"  şu anki : ALAKA_ESIGI = {config.ALAKA_ESIGI}")
    else:
        print("\n  Hiçbir eşik reddetmeyi 1.00 yapmıyor — bantlar tamamen örtüşüyor.")


def cevap_olc(usta, sorular: list[dict]) -> None:
    """Cevap üretimini ölçer: sadakat, gecikme, yanlış reddetme."""
    from src import prompts

    print("\nCEVAP ÜRETİMİ")
    sadakat, sureler, yollar = [], {"exact": [], "hibrit": []}, {}
    yanlis_ret, kacak = 0, 0
    for i, s in enumerate(sorular, 1):
        t = time.perf_counter()
        c = usta.cevapla(s["soru"])
        sure = time.perf_counter() - t
        yollar[c.arama.yol] = yollar.get(c.arama.yol, 0) + 1
        sureler.setdefault(c.arama.yol, []).append(sure)

        reddetti = "dokümanlarda yok" in c.metin
        if s.get("reddetmeli") and not reddetti:
            kacak += 1
        if not s.get("reddetmeli") and reddetti:
            yanlis_ret += 1

        if not reddetti and c.arama.sonuclar:
            baglam = prompts.baglam_kur(c.arama.sonuclar)
            cev = set(REFERANS.findall(c.metin))
            bag = set(REFERANS.findall(baglam))
            if cev:
                sadakat.append(len(cev & bag) / len(cev))
        print(f"  {i:2d}/{len(sorular)} {s['id']}", end="\r", flush=True)
    print(" " * 30, end="\r")

    ort = lambda L: sum(L) / len(L) if L else 0.0
    print(f"  sadakat (referanslar bağlamda mı) : {ort(sadakat):.2f}  "
          f"[{len(sadakat)} cevap]")
    print(f"  reddetme kaçağı                   : {kacak}")
    print(f"  yanlış reddetme                   : {yanlis_ret}")
    for yol, L in sureler.items():
        if L:
            L = sorted(L)
            print(f"  {yol:7s} n={len(L):2d}  ortalama {ort(L):5.1f} sn | "
                  f"p95 {L[min(int(len(L)*.95), len(L)-1)]:5.1f} sn")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", type=Path, default=Path(__file__).parent / "golden_set.yaml")
    ap.add_argument("--k", type=int, default=config.TOP_K)
    ap.add_argument("--esik-tara", action="store_true")
    ap.add_argument("--kapsama-atla", action="store_true")
    ap.add_argument("--limit", type=int, default=0,
                    help="ilk N soruyu koş (düşük GPU yükü için)")
    ap.add_argument("--cevaplarla", action="store_true",
                    help="cevap üretimi dahil (~50 soru, birkaç dakika)")
    a = ap.parse_args()

    sorular = yaml.safe_load(a.set.read_text(encoding="utf-8"))
    if a.limit:
        # her kategoriden orantılı örnek — tek kategoriye sıkışmasın
        kat = {}
        for s in sorular:
            kat.setdefault(s["kategori"], []).append(s)
        pay = max(1, a.limit // len(kat))
        sorular = [x for grup in kat.values() for x in grup[:pay]]
    print(f"USTA değerlendirme — {len(sorular)} soru, K={a.k}")

    usta = assistant.kur()
    if not a.kapsama_atla:
        kapsama_testi(usta.conn)

    print(f"\nISINMA (ölçüme dahil değil)")
    isindir(usta)

    print(f"KOŞU")
    sonuclar = kosu(usta, sorular, a.k)
    rapor(sonuclar, a.k)
    if a.esik_tara:
        esik_tara(sonuclar)
    if a.cevaplarla:
        cevap_olc(usta, sorular)


if __name__ == "__main__":
    main()

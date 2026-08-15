"""Sorgu ön işleme: Türkçe sorguyu aramadan önce İngilizceye çevirir.

NEDEN GEREKLİ
-------------
Manueller İngilizce, sorgular Türkçe. Embedding modeli (qwen3-embedding-0.6b)
bu iki dili aynı vektör uzayında hizalayamıyor. Ölçüm (Hafta 2):

    Türkçe sorgu   -> ilk 3'te doğru sonuç yok, skorlar 0.45-0.60 arası belirsiz
    İngilizce sorgu -> ilk sırada doğru sonuç, skorlar 0.63-0.71

Aynı chunk ("ALARM 56 — AMA interrupted by user") üç alakasız Türkçe sorguda
birden ilk sıraya çıkıyordu: hub vektör davranışı, yani sorgu vektörü anlamlı
bir yere değil uzayın ortasına düşüyor.

Sorgu çevirisi bunu çözüyor. Yan faydası: çeviri manuelin kendi terminolojisini
kullandığı için BM25 tarafı da güçleniyor.
"""

from __future__ import annotations

import re

import config
from src.output import dusunmeyi_ayikla

# Model "faz kaybı"nı "frequency loss" diye çevirip yanlış sonuç getirmişti.
# Sözlük, sistem prompt'una terminoloji kılavuzu olarak enjekte ediliyor —
# doğrudan string değiştirme yapılmıyor, çünkü Türkçe çekim ekleri bozulur.
SOZLUK = {
    "faz kaybı": "phase loss",
    "şebeke": "line supply (mains)",
    "aşırı gerilim": "overvoltage",
    "düşük gerilim": "undervoltage",
    "aşırı akım": "overcurrent",
    "aşırı yük": "overload",
    "fren direnci": "braking resistor",
    "ara devre": "DC link",
    "DC bara": "DC link",
    "sürücü": "drive",
    "soğutma fanı": "cooling fan",
    "aşırı ısınma": "overtemperature",
    "topraklama hatası": "earth fault",
    "kısa devre": "short circuit",
    "rampa süresi": "ramp time",
    "yalıtım": "insulation",
    "kondansatör": "capacitor",
    "hız geri beslemesi": "speed feedback",
    "enkoder": "encoder",
    "kumanda kartı": "control board",
}

_SOZLUK_METNI = "\n".join(f"  {tr} = {en}" for tr, en in SOZLUK.items())

SISTEM_PROMPT = (
    "You translate Turkish motor-drive fault descriptions into English, using "
    "the terminology of VFD manufacturer manuals (Siemens, ABB, Danfoss).\n"
    "Output ONLY the English phrase — no explanation, no quotes.\n\n"
    "Use these term mappings exactly:\n" + _SOZLUK_METNI
)

# qwen3-4b bir reasoning modeli: /no_think ile bile BOŞ bir <think> bloğu
# üretiyor ve cevap ondan sonra geliyor. max_tokens bu bloğu karşılayacak kadar
# geniş olmalı — 40'a kısıldığında bütçe bloğa gidip cevap hiç üretilmiyor.


# Türkçeye özgü karakterler.
# DİKKAT: burada re.IGNORECASE KULLANILMAMALI. Unicode katlamada U+0130 (İ)
# ASCII 'i'ye, U+0131 (ı) ASCII 'I'ya eşleşir; sonuç olarak içinde 'i' geçen
# her İngilizce sorgu Türkçe sanılır ve gereksiz yere çevrilir.
_TURKCE_HARF = re.compile(r"[çğıöşüÇĞİÖŞÜ]")
_TURKCE_KELIME = re.compile(
    r"\b(?:hatası|hata|arızalı|arıza|çalışmıyor|veriyor|var|yok|nedir|neden)\b",
    re.IGNORECASE,
)


def turkce_mi(metin: str) -> bool:
    """Sorgu Türkçe görünüyor mu? İngilizce sorgular boşuna çevrilmesin."""
    return bool(_TURKCE_HARF.search(metin) or _TURKCE_KELIME.search(metin))


def ingilizceye_cevir(chat_client, sorgu: str) -> str:
    """Türkçe sorguyu İngilizceye çevirir. Çeviri başarısızsa özgün sorgu döner.

    Token bütçesi geçici olarak düşürülüyor: cevap üretimi için gereken 384
    token, kısa bir çeviri için gereksiz ve model erken durmazsa sorguyu
    saniyelerce uzatıyor.
    """
    from foundry_local_sdk.openai import ChatClientSettings

    onceki = chat_client.settings
    chat_client.settings = ChatClientSettings(
        max_tokens=config.TRANSLATE_MAX_TOKENS,
        temperature=config.CHAT_TEMPERATURE,
        top_p=config.CHAT_TOP_P,
        frequency_penalty=config.CHAT_FREQUENCY_PENALTY,
        random_seed=config.CHAT_SEED,
    )
    try:
        yanit = chat_client.complete_chat([
            {"role": "system", "content": SISTEM_PROMPT},
            {"role": "user", "content": f"{config.NO_THINK_PREFIX}{sorgu}"},
        ])
    finally:
        chat_client.settings = onceki
    ham = yanit.choices[0].message.content or ""
    temiz = dusunmeyi_ayikla(ham).strip('"').strip()
    ilk_satir = temiz.splitlines()[0].strip() if temiz else ""
    return ilk_satir or sorgu


def hazirla(chat_client, sorgu: str) -> tuple[str, bool]:
    """(arama_sorgusu, cevrildi_mi) döner."""
    if not turkce_mi(sorgu):
        return sorgu, False
    return ingilizceye_cevir(chat_client, sorgu), True

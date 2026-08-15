"""Uçtan uca akış: sorgu → retrieval → cevap.

Sıralama önemli. Kod kontrolü ÖNCE ham sorgu üzerinde yapılıyor; ancak kod
bulunamazsa çeviri ve embedding devreye giriyor. Tersi sırada "ABB 2310 hatası"
gibi bir sorgu gereksiz yere çeviriye gidip 1.7 sn kaybettiriyordu — oysa
cevap tek bir indeks okumasıyla 0.0 sn'de bulunabiliyor.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

import numpy as np

import config
from src import db, output, prompts, query
from src.retrieval import AramaSonucu, Retriever


@dataclass
class Cevap:
    metin: str
    arama: AramaSonucu
    sure: float
    cevap_suresi: float


class Asistan:
    def __init__(self, conn, chat_client, embedding_client):
        self.conn = conn
        self.chat = chat_client
        self.emb = embedding_client
        self.retriever = Retriever(conn)

    def _vektor(self, metin: str) -> np.ndarray:
        return np.array(
            self.emb.generate_embedding(metin).data[0].embedding, dtype=np.float32
        )

    def ara(self, soru: str) -> AramaSonucu:
        # 1) Ham sorguda kod var mı? Varsa çeviri ve embedding'e hiç gerek yok.
        if self.retriever.kod_adaylari(soru):
            return self.retriever.ara(soru, None)

        # 2) Türkçeyse İngilizceye çevir (embedding modeli iki dili hizalayamıyor)
        arama, cevrildi = query.hazirla(self.chat, soru)

        # 3) Çeviri kodu ortaya çıkarmış olabilir ("aşırı gerilim F30002 hatası")
        if self.retriever.kod_adaylari(arama):
            return self.retriever.ara(arama, None, cevrildi=cevrildi)

        return self.retriever.ara(arama, self._vektor(arama), cevrildi=cevrildi)

    def cevapla(self, soru: str) -> Cevap:
        t0 = time.perf_counter()
        arama = self.ara(soru)
        t1 = time.perf_counter()

        # Alakasızsa modeli hiç çağırma: hem uydurma riski sıfırlanır hem
        # cevap anında döner (13 sn -> 0 sn).
        if not arama.sonuclar or not arama.alakali_mi():
            return Cevap("Bu bilgi elimdeki dokümanlarda yok.", arama,
                         t1 - t0, 0.0)

        # Exact eşleşmede manuelin kendi metni cevabın kendisi — LLM gereksiz.
        if arama.yol == "exact":
            metin = "\n\n".join(output.bicimlendir_chunk(s) for s in arama.sonuclar)
            return Cevap(metin, arama, t1 - t0, 0.0)

        yanit = self.chat.complete_chat(self._mesajlar(soru, arama))
        metin = output.dusunmeyi_ayikla(yanit.choices[0].message.content or "")
        metin = output.tekrarlari_temizle(metin)
        t2 = time.perf_counter()
        return Cevap(metin or "Bu bilgi elimdeki dokümanlarda yok.",
                     arama, t1 - t0, t2 - t1)

    def _mesajlar(self, soru: str, arama: AramaSonucu) -> list[dict]:
        baglam = prompts.baglam_kur(arama.sonuclar)
        return [
            {"role": "system", "content": prompts.CEVAP_SISTEM},
            {"role": "user", "content": config.NO_THINK_PREFIX
             + prompts.kullanici_mesaji(baglam, soru)},
        ]

    def akisli(self, soru: str):
        """(arama_sonucu, satır üreteci) döner.

        Cevabın tamamı 13-16 sn sürüyor; akışla ilk satır ~1 sn'de görünüyor.
        Satır satır tamponlandığı için tekrar temizliği akışta da çalışıyor.
        """
        arama = self.ara(soru)
        if not arama.sonuclar or not arama.alakali_mi():
            return arama, iter(["Bu bilgi elimdeki dokümanlarda yok."])

        if arama.yol == "exact":
            metin = "\n\n".join(output.bicimlendir_chunk(s) for s in arama.sonuclar)
            return arama, iter(metin.splitlines())

        def uret():
            akis = output.CevapAkisi()
            for parca in self.chat.complete_streaming_chat(self._mesajlar(soru, arama)):
                delta = parca.choices[0].delta.content if parca.choices else None
                yield from akis.besle(delta or "")
            yield from akis.bitir()

        return arama, uret()


def kur(db_path=None):
    """Modelleri yükleyip Asistan döner. İlk çağrıda model belleğe alınır."""
    from foundry_local_sdk import Configuration, FoundryLocalManager
    from foundry_local_sdk.openai import ChatClientSettings

    FoundryLocalManager.initialize(Configuration(
        app_name=config.APP_NAME,
        model_cache_dir=str(config.MODEL_CACHE_DIR),
    ))
    mgr = FoundryLocalManager.instance

    cm = mgr.catalog.get_model(config.CHAT_MODEL)
    em = mgr.catalog.get_model(config.EMBEDDING_MODEL)
    if cm is None or em is None:
        raise SystemExit("model bulunamadı — `foundry model list` ile alias'ları kontrol et")
    cm.load()
    em.load()

    chat = cm.get_chat_client()
    chat.settings = ChatClientSettings(
        max_tokens=config.CHAT_MAX_TOKENS,
        temperature=config.CHAT_TEMPERATURE,
        top_p=config.CHAT_TOP_P,
        frequency_penalty=config.CHAT_FREQUENCY_PENALTY,
        presence_penalty=config.CHAT_PRESENCE_PENALTY,
        random_seed=config.CHAT_SEED,
    )
    conn = db.connect(db_path or config.DB_PATH)
    return Asistan(conn, chat, em.get_embedding_client())

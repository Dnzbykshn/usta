"""Foundry Local kurulum doğrulaması — Hafta 1 milestone'u.

Sohbet modelinin ve embedding modelinin cihaz üzerinde çalıştığını teyit eder.
Çalıştırma:  .venv/bin/python scripts/hello_model.py

NOT: Bu kod foundry-local-sdk 1.2.x API'sini kullanır. Plan dokümanındaki ve
Microsoft Learn tutorial'ındaki `from foundry_local import FoundryLocalManager`
örneği eski SDK'ya aittir ve bu sürümde çalışmaz. Doğru kullanım:
    Configuration -> FoundryLocalManager.initialize -> catalog.get_model -> load
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import config


def fail(mesaj: str, ipucu: str) -> None:
    print(f"\n  BAŞARISIZ: {mesaj}")
    print(f"  İpucu: {ipucu}\n")
    sys.exit(1)


def model_yukle(manager, alias: str):
    """Alias'tan modeli bulup belleğe yükler."""
    model = manager.catalog.get_model(alias)
    if model is None:
        fail(f"model bulunamadı: {alias}",
             "`foundry model list` ile alias'ı teyit edip config.py'yi güncelle")
    model.load()
    return model


def main() -> None:
    try:
        from foundry_local_sdk import Configuration, FoundryLocalManager
        from foundry_local_sdk.openai import ChatClientSettings
    except ImportError as e:
        fail(f"paket yüklenemedi ({e.name})",
             "sanal ortamı kullan -> .venv/bin/python scripts/hello_model.py")

    FoundryLocalManager.initialize(Configuration(
        app_name=config.APP_NAME,
        model_cache_dir=str(config.MODEL_CACHE_DIR),
    ))
    manager = FoundryLocalManager.instance

    # --- 1. Sohbet modeli ---------------------------------------------------
    print(f"\n[1/2] Sohbet modeli yükleniyor: {config.CHAT_MODEL}")

    model = model_yukle(manager, config.CHAT_MODEL)
    chat = model.get_chat_client()
    chat.settings = ChatClientSettings(max_tokens=100, temperature=0.3)

    baslangic = time.perf_counter()
    yanit = chat.complete_chat([{
        "role": "user",
        "content": "Bir cümleyle kendini tanıt. Türkçe cevap ver.",
    }])
    sure = time.perf_counter() - baslangic

    print(f"      Model  : {model.id}")
    print(f"      Bağlam : {model.context_length} token")
    print(f"      Cevap  : {yanit.choices[0].message.content.strip()}")
    print(f"      Süre   : {sure:.1f} sn")

    # --- 2. Embedding modeli ------------------------------------------------
    print(f"\n[2/2] Embedding modeli yükleniyor: {config.EMBEDDING_MODEL}")

    emb_model = model_yukle(manager, config.EMBEDDING_MODEL)
    emb = emb_model.get_embedding_client()

    baslangic = time.perf_counter()
    vektor = emb.generate_embedding("DC bara aşırı gerilim").data[0].embedding
    sure = time.perf_counter() - baslangic

    print(f"      Model  : {emb_model.id}")
    print(f"      Boyut  : {len(vektor)}")
    print(f"      Süre   : {sure:.2f} sn")

    print("\n  Ortam hazır. Hafta 1 milestone'u tamam.\n")


if __name__ == "__main__":
    main()

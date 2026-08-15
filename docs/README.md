# Belgeler

Bu klasör iki HTML belgesinin **kaynağını** tutar. İkisi de tek dosyalık,
bağımlılıksız sayfalardır — tarayıcıda doğrudan açılır, sunucu gerekmez.

| Dosya | Nedir | Yayınlandığı adres |
|---|---|---|
| `proje-brief.html` | Proje brief'i v0.4 — 12 bölüm: kapsam, mimari, teknik kararlar, ölçülmüş sonuçlar, model deneyleri, riskler | [claude.ai/code/artifact/7d78d407…](https://claude.ai/code/artifact/7d78d407-c329-448d-9d22-37ca046236eb) |
| `demo-day-sunum.html` | Demo day sunumu — 10 slayt | [claude.ai/code/artifact/47506073…](https://claude.ai/code/artifact/47506073-f565-4b71-ad99-9f887aaddd29) |

| `video-senaryo.md` | 2 dakikalık tanıtım videosu için çekim planı ve anlatım metni |

## Açmak

```bash
open docs/proje-brief.html
open docs/demo-day-sunum.html
```

## Sunumu PDF'e çevirmek

Tarayıcıda aç → Yazdır → PDF olarak kaydet. Her slayt ayrı sayfaya düşer
(`@media print` içinde `page-break-after` tanımlı) ve koyu tasarım korunur
(`print-color-adjust: exact`).

## Neden dış bağımlılık yok

İkisi de tek dosya: CSS gömülü, font yok, JavaScript yok, resim yok. Sebebi
projenin kendisiyle aynı — **çevrimdışı çalışmalı.** Sunumu internetsiz bir
salonda açman gerekebilir; CDN'den font ya da kütüphane çeken bir sayfa orada
bozulur. Diyagramlar bu yüzden satır içi SVG.

## Güncelleme

Dosyayı düzenleyip aynı adrese yeniden yayınlayabilirsin — link değişmez.
Yeni bir adres oluşmasını istemiyorsan mevcut URL'yi vermen gerekir.

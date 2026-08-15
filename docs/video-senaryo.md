# 2 dakikalık video senaryosu

Toplam ~250 kelime anlatım. İki dakika sanılandan kısa: acele etmeden okunacak
metin bu kadar. Fazlası varsa demo süresinden çalar.

## Kritik teknik tuzak

Ölçülmüş süreler:

| Sorgu tipi | Süre | Videoda |
|---|---|---|
| Hata kodu (`F30002`) | **0.0 sn** | anında — vurucu |
| Reddetme (`fiyatı ne kadar`) | 1.5 sn | akıcı |
| Doğal dil (`fren direnci arızalı`) | **~12 sn** | kurguda kısaltılmalı |

İki dakikada 12 saniyelik bekleme kabul edilemez. İki çözüm:

- Doğal dil sorgusunu **kurguda 4× hızlandır** (bekleme kısmını), ya da
- Cevap belirmeye başladığı anda kes, tamamlanmasını bekleme

**Kayıttan önce mutlaka modeli ısıt.** İlk sorgu model yüklemesi yüzünden ~20
saniye sürer. Kaydı başlatmadan bir sorgu çalıştır, sonra kaydet.

---

## Çekim planı

### 0:00 – 0:12 · Problem

**Ekran:** Bir sürücü hata ekranı fotoğrafı ya da sadece `F30002` yazısı.

> "Bir fabrikada motor sürücüsü durdu. Ekranda sadece bir kod var: F30002.
> Bu kodun ne anlama geldiği, 570 sayfalık bir PDF'in içinde bir tablo
> satırında. Ve teknisyen makine dairesinde — internet yok."

### 0:12 – 0:24 · Çözüm

**Ekran:** Uygulama açılışı, sağ üstteki `ÇEVRİMDIŞI · AĞ İSTEĞİ 0` rozetine yakınlaş.

> "USTA, üç farklı markanın arıza manuellerini tek bir çevrimdışı asistanda
> birleştiriyor. Tüm model çıkarımı cihaz üzerinde — tek bir ağ isteği yok."

### 0:24 – 1:20 · Demo (videonun ağırlığı burada)

**Ekran:** Önce menü çubuğunda **Wi-Fi'yi kapat** — bu kare kanıt niteliğinde.

**1. Hata kodu** — `F30002 ne demek`

> "Kod sorgularında cevap anında geliyor, çünkü burada dil modeli hiç
> çalışmıyor. Manuelin kendi metni doğrudan geliyor — kaynak: sayfa 523."

**2. Aciliyet farkı** — `ALARM 28`

> "Danfoss'ta aynı sorgu. Rozet farklı: bu bir alarm, sürücü çalışmaya
> devam ediyor. Fault olsaydı sürücü duracaktı."

**3. Doğal dil** — `fren direnci arızalı` *(kurguda hızlandır)*

> "Kodu bilmiyorsan belirti de yazabilirsin. Türkçe soru, İngilizce
> manueller — ve üç markadan birden sonuç geliyor. Teknisyen hangi markayı
> kullandığını söylemek zorunda değil."

**4. Reddetme** — `bu sürücünün fiyatı ne kadar`

> "Cevabı bilmediğinde uyduruyor mu? Hayır. Elli soruluk testte bu oran
> yüzde yüz — çünkü karar dil modeline değil, koda bırakıldı."

### 1:20 – 1:42 · Nasıl çalışıyor

**Ekran:** Brief'teki yönlendirme diyagramı (Şekil 1).

> "İki yol var. Sorguda hata kodu varsa doğrudan veritabanı indeksine
> gidiyor. Yoksa soru İngilizceye çevrilip anahtar kelime ve anlam araması
> birlikte çalışıyor. Benzerlik eşiğin altındaysa model hiç çağrılmıyor."

### 1:42 – 2:00 · Sonuç

**Ekran:** Sonuç metrikleri (sunumun 8. slaydı).

> "Elli soruluk sette: kod sorgularında yüzde yüz isabet, reddetmede yüzde
> yüz, kaynak sadakati yüzde doksan altı. Beş yüz seksen arıza kaydı, üç
> marka, dört gigabayt disk — ve çalışırken sıfır ağ isteği."

---

## Teknik ayarlar

- **Çözünürlük:** 1080p yeter. Uygulama metin ağırlıklı, 4K gereksiz.
- **Kayıt alanı:** Tarayıcı penceresi + menü çubuğu. Wi-Fi simgesi görünmeli.
- **Yazı boyutu:** Kayıttan önce tarayıcıda `Cmd +` ile bir-iki kademe büyüt.
  YouTube'da telefondan izleyen biri okuyabilmeli.
- **Ses:** Sessiz odada, mikrofon ağza yakın. Fan sesi varsa Foundry servisini
  kayıt aralarında durdur (`foundry server stop`).
- **Kurgu:** Yazma anlarını hızlandır, bekleme anlarını kes. İzleyici tuşlara
  basılmasını izlemek istemiyor.

## Sık yapılan hata

Videonun yarısını mimari anlatmaya ayırmak. İki dakikada mimari anlatılamaz —
video **çalıştığını göstermek** için, açıklamak için değil. Demo bölümü toplam
sürenin yarısından fazlasını almalı. Ayrıntıyı merak eden brief'e bakar.

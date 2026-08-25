# 3 dakikalık video — teknik + öğrendiklerim (karma)

**Kurgu mantığı:** Teknik detay ve ders ayrı bloklar halinde anlatılmıyor,
iç içe geçiyor. Her ders somut bir teknik karara bağlı — böylece hem "ne
kullandım" hem "ne öğrendim" aynı cümlede duruyor.

Bu, üç metin arasında tek başına anlatılmaya en uygun olanı.

Bütün sayılar projeden ölçüldü. Cümleler kısa.

---

## 0:00 – 0:20 · Açılış — tek kısıt

> Merhaba. Bu projede sahada çalışan bir bakım teknisyeni için arıza
> asistanı yaptık.
>
> İşe tek bir kısıtla başladık: her şey cihaz üzerinde çalışacak. İnternet
> yok, bulut yok, API anahtarı yok.
>
> Bu kısıt sonraki bütün kararları belirledi. Şimdi o kararları ve
> yol boyunca öğrendiklerimi anlatacağım.

---

## 0:20 – 0:55 · Stack ve ilk karar

> Model çalıştırmak için **Microsoft Foundry Local** kullandık. Modelleri
> cihazın GPU'sunda çalıştırıyor.
>
> İki model var. Cevap üretimi için **qwen3-4b** — iki nokta dokuz gigabayt.
> Arama için **qwen3-embedding-0.6b** — beş yüz megabayt, bin yirmi dört
> boyutlu vektör üretiyor.
>
> Plan dokümanı Phi öneriyordu. Biz Qwen'i seçtik, çünkü sorgularımız
> Türkçe ama manueller İngilizce.
>
> Ve buradan ilk dersi aldım: **varsayılanı ölçmeden kabul etme.** Denedik,
> Türkçe sorgular Phi'de çalışmadı.

*Ekran: `config.py` — model tanımları ve altındaki gerekçe yorumu*

---

## 0:55 – 1:30 · Vektör araması yetmedi

> Klasik RAG kurulumu şudur: her şeyi vektöre çevir, benzerliğe bak.
>
> Bizde çalışmadı. Sebebi ilginç.
>
> **F-otuz-sıfır-sıfır-iki** ile **F-otuz-sıfır-sıfır-üç** string olarak
> neredeyse aynı. Vektörleri de öyle. Yani sistem, aşırı gerilim sorusuna
> düşük gerilim cevabı verebiliyordu.
>
> Çözüm: hata kodu içeren sorguları vektör aramasına hiç sokmadık. Onlar
> doğrudan **SQLite** indeksine gidiyor. Anahtar kelime araması için de
> SQLite'ın **FTS5** eklentisini kullandık, BM25 hazır geliyor.
>
> İkinci ders: **her problem aynı araçla çözülmez.** Semantik arama güçlü
> ama kodlarda işe yaramıyor.

---

## 1:30 – 2:10 · En önemli ders

> Şimdi projede en çok işime yarayan derse geliyorum.
>
> Sisteme "bilmediğin bir şey sorulursa uydurma, bilmiyorum de" demek
> istedik. Prompt'a yazdık.
>
> **Yetmedi.** Format talimatı ağır basınca, fiyat sorusuna alakasız bir
> teknik cevap uydurdu.
>
> Bunun üzerine kararı prompt'tan aldık, koda taşıdık. Artık bir benzerlik
> eşiği var. Bulunanlar yeterince ilgili değilse model hiç çağrılmıyor.
>
> Reddetme oranı o günden sonra yüzde yüz oldu ve orada kaldı.
>
> Öğrendiğim şey şu: **prompt bir rica, kod bir garanti.** Güvenlik
> gerektiren davranışı modele emanet etme.

*Ekran: reddetme örneği — "Bu bilgi elimdeki dokümanlarda yok"*

---

## 2:10 – 2:40 · Sessiz hatalar

> Bir ders daha var, belki daha da önemli.
>
> Ayrıştırıcımız Siemens kodlarının yüzde otuzunu atlıyordu. Hiç hata
> vermedi. Kod çalıştı, sonuç makul göründü.
>
> Ancak ayrıştırıcının bulduğu sayıyı bağımsız bir sayımla karşılaştırınca
> fark ettik.
>
> Şimdi bu kontrol kalıcı bir test olarak duruyor.
>
> **En tehlikeli hatalar, hata vermeyenler.** Özellikle bu tür sistemlerde,
> bilgi tabanının üçte biri eksikken her şey normal görünebiliyor.

---

## 2:40 – 3:00 · Kapanış

> Özetle: Foundry Local, iki Qwen modeli, SQLite ve NumPy. Beş yüz seksen
> arıza kaydı, tamamen çevrimdışı.
>
> Ama asıl öğrendiğim şey araçlar değil. Ölçmeden karar vermemek, ve
> önemli davranışları modelin insafına bırakmamak.
>
> Kod GitHub'da. İzlediğiniz için teşekkürler.

---

## Neden bu kurgu

Üç ders var ve üçü de somut bir teknik karara bağlı:

| Ders | Bağlı olduğu karar |
|---|---|
| Varsayılanı ölçmeden kabul etme | Phi yerine Qwen |
| Her problem aynı araçla çözülmez | Hibrit arama, FTS5 |
| Prompt bir rica, kod bir garanti | Benzerlik eşiği |
| En tehlikeli hatalar sessiz olanlar | Kapsama testi |

Soyut ders vermek kolay, ama arkasında kod olmayan ders inandırıcı olmuyor.
Bu yüzden her ders önce teknik kararla anlatılıyor, sonra çıkarımla
kapatılıyor.

## Sorulabilecekler

**"Neden Qwen, neden Phi değil?"**
Sorgular Türkçe, manueller İngilizce. Qwen çok dilli görevlerde daha güçlü.

**"Eşiği neye göre seçtiniz?"**
Tarayarak. 0.48'den 0.70'e kadar denedik. 0.56, reddetmeyi yüzde yüz yapan
en düşük değerdi. Bedeli birkaç meşru sorguyu kaybetmek — güvenlik
çerçevesi bu dengeyi belirledi.

**"Sessiz hatayı nasıl fark ettiniz?"**
Ayrıştırıcının çıkardığı kod sayısını, bölümde geçen kod sayısıyla
karşılaştırdık. Eşit olmalıydı, değildi.

## Çekimden önce

1. `.venv/bin/python scripts/demo.py` — model **kayıt dışında** ısınır
2. Wi-Fi'yi kapat
3. Arayüz kullanılacaksa `Cmd+R` ile yenile
4. Kaydı başlat

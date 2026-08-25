# 3 dakikalık video — teknik anlatım

**Odak:** Tech stack ve projeyi nasıl kurguladığımız. Hangi model, hangi
embedding modeli, neden onlar, katmanları nasıl ayırdık.

Diğer iki metinden farkı:

| | Metin 1 | Metin 2 | **Bu metin** |
|---|---|---|---|
| Odak | Sistem ve mimari | Veri ve ölçüm | **Stack ve kurgu** |
| Kime | Genel izleyici | Genel izleyici | Teknik izleyici |

Bütün sayılar ölçülmüş değerler — uydurma yok. Cümleler kısa tutuldu.

---

## 0:00 – 0:20 · Açılış — kısıt neyi belirledi

> Merhaba. Bu videoda projenin teknik tarafını anlatacağım. Hangi araçları
> seçtik ve neden.
>
> İşe tek bir kısıtla başladık: her şey cihaz üzerinde çalışacak. İnternet
> yok, bulut yok, API anahtarı yok.
>
> Bu kısıt, sonraki bütün kararları belirledi.

---

## 0:20 – 1:00 · Modeller

> Model çalıştırmak için **Microsoft Foundry Local** kullandık. Modelleri
> indirip cihazın GPU'sunda çalıştırıyor. Bulut hesabı gerekmiyor.
>
> İki model var.
>
> Cevap üretimi için **qwen3-4b**. Dört milyar parametre, iki nokta dokuz
> gigabayt.
>
> Arama için **qwen3-embedding-0.6b**. Beş yüz on beş megabayt, bin yirmi
> dört boyutlu vektör üretiyor.
>
> Plan dokümanı aslında Phi-3.5 Mini öneriyordu. Biz Qwen'i seçtik. Sebebi
> şu: bizim sorgularımız Türkçe, manueller İngilizce. Qwen ailesi çok dilli
> görevlerde belirgin şekilde güçlü. Embedding modelinin de aynı aileden
> olması diller arası tutarlılık sağlıyor.

*Ekran: `config.py` içindeki model tanımları*

---

## 1:00 – 1:40 · Veri katmanı

> Veri tarafında **SQLite** kullandık. Tek dosya, sunucu yok.
>
> İki şey saklıyor: metin parçaları ve onların vektörleri. Vektörler ikili
> blob olarak duruyor.
>
> Anahtar kelime araması için SQLite'ın **FTS5** eklentisini kullandık.
> BM25 sıralaması hazır geliyor, ek bir bağımlılık gerekmedi.
>
> Peki neden vektör veritabanı kullanmadık? Çünkü gerek yoktu.
>
> Beş yüz seksen parçamız var. Bin yirmi dört boyut, dört baytlık sayılar.
> Toplam iki nokta dört megabayt. Bunu belleğe alıp NumPy ile tek matris
> çarpımı yapıyoruz — milisaniyeler sürüyor.
>
> Ayrı bir vektör veritabanı bu ölçekte sadece karmaşıklık eklerdi.

*Ekran: SQLite şeması ya da `db.py`*

---

## 1:40 – 2:20 · Katmanları nasıl ayırdık

> Kodu sekiz modüle böldük. Her biri tek bir işten sorumlu.
>
> `parsers` — PDF'lerden arıza kayıtlarını çıkarıyor. Marka başına ayrı
> ayrıştırıcı, çünkü üçü farklı biçim kullanıyor.
>
> `db` — şema ve veri erişimi.
>
> `query` — Türkçe sorguyu İngilizceye çeviriyor.
>
> `retrieval` — hibrit arama: birebir kod eşleşmesi, BM25 ve vektör.
>
> `output` — cevabı temizliyor. Tekrarları siliyor.
>
> `assistant` — hepsini birleştiriyor.
>
> Bu ayrım işe yaradı. Arayüzü eklerken çekirdek mantığa hiç dokunmadık.
> Hem terminal hem web arayüzü aynı `assistant` modülünü çağırıyor.

*Ekran: proje klasör yapısı*

---

## 2:20 – 2:45 · Sayılar

> Birkaç rakam.
>
> Toplam disk: yaklaşık dört gigabayt. Bunun üç nokta dördü modeller.
> Veritabanı sadece üç megabayt.
>
> Donanım: M4 işlemcili bir MacBook, on altı gigabayt bellek. Modeller
> GPU'da çalışıyor.
>
> Hız: hata kodu sorgularında cevap anında geliyor, çünkü orada dil modeli
> hiç çağrılmıyor. Doğal dil sorgularında yaklaşık on iki saniye.
>
> Ve bütün ayarlar sabit bir tohumla çalışıyor. Aynı soru her zaman aynı
> cevabı veriyor.

---

## 2:45 – 3:00 · Kapanış

> Özetle: Foundry Local, iki Qwen modeli, SQLite ve NumPy. Hepsi bu.
>
> Karmaşık bir yığın kurmadık. Ölçüp gerektiği kadarını kullandık.
>
> Kod GitHub'da. İzlediğiniz için teşekkürler.

---

## Ekranda gösterilecekler

| Bölüm | Ekran |
|---|---|
| Modeller | `config.py` — model tanımları ve yorumları |
| Veri katmanı | `src/db.py` şeması ya da `foundry model list` çıktısı |
| Katmanlar | `src/` klasörü, dosya listesi |
| Sayılar | `du -sh` çıktısı ya da metrik tablosu |

## Sorulabilecekler

**"Neden Qwen, neden Phi değil?"**
Sorgular Türkçe, manueller İngilizce. Qwen çok dilli görevlerde daha güçlü.
Embedding modelinin aynı aileden olması da diller arası tutarlılık sağlıyor.

**"Neden vektör veritabanı yok?"**
580 chunk × 1024 boyut × 4 bayt = 2.4 MB. NumPy ile tek matris çarpımı
milisaniye sürüyor. Bu ölçekte ayrı bir veritabanı sadece karmaşıklık ekler.

**"Neden FTS5?"**
SQLite'ın içinde geliyor, BM25 sıralaması hazır. Ek bağımlılık gerekmedi.

**"Sabit tohum neden?"**
Hem ölçüm tekrarlanabilir olsun diye, hem de aynı hata kodu her zaman aynı
cevabı versin diye. İki teknisyen farklı metin görürse araca güven kalmaz.

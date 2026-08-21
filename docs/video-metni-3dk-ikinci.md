# 3 dakikalık video — ikinci ekip üyesi

**Neden ayrı bir metin:** İki kişi aynı projeyi aynı sırayla anlatırsa ikinci
video gereksiz görünür. Bu metin farklı bir açıdan giriyor — veri tarafı ve
ölçüm. Birinci video (`video-metni-3dk.md`) sistemi ve mimariyi anlatıyor.

| | Birinci video | Bu video |
|---|---|---|
| Odak | Sistem nasıl çalışıyor | Veriyi nasıl kurduk, nasıl ölçtük |
| Demo | Kod sorgusu + aciliyet farkı | Markalar arası + reddetme |
| Kapanış | Prompt vs kod dersi | Elediğimiz alternatifler |

Cümleler kısa tutuldu — uzun cümleler yüksek sesle okunurken nefes yetmiyor.
Ezberleme; akışı bil, kendi kelimelerinle anlat.

---

## 0:00 – 0:20 · Açılış — veri problemi

> Merhaba. Biz bu projede bir bakım teknisyeninin problemini çözmeye çalıştık.
>
> Ama ben size işin biraz farklı bir tarafından bahsedeceğim: veriden.
>
> Elimizde üç üreticinin manueli vardı. Siemens, ABB, Danfoss. Toplam bin beş
> yüz sayfa. Ve bu üç üretici hiçbir ortak standarda uymuyor.

*Ekran: üç manuelin kapağı ya da üç kod örneği yan yana*

---

## 0:20 – 0:50 · Üç marka, üç şema

> Şuna bakın. Aynı arıza, üç ayrı kod.
>
> Siemens harf ve beş hane kullanıyor: F-otuz-sıfır-sıfır-iki.
> ABB dört karakterlik onaltılık kod kullanıyor.
> Danfoss ise sadece bir sayı — "alarm yirmi sekiz".
>
> Yani tek bir ayrıştırıcı yazmak mümkün değildi. Her marka için ayrı bir
> ayrıştırıcı yazdık. ABB'de düz metin bile yetmedi; kelimelerin sayfadaki
> konumuna bakmak zorunda kaldık, çünkü gerçek kodlarla yardımcı kodlar
> metin olarak birbirinden ayırt edilemiyordu.
>
> Sonuçta beş yüz seksen arıza kaydı çıkardık. Her kod ayrı bir kayıt.

*Ekran: üç kod biçimi tablosu, sonra veritabanı sayıları*

---

## 0:50 – 1:35 · Demo

> Şimdi çalışırken göstereyim. Wi-Fi kapalı — bakın.

*Wi-Fi'yi kapat, menü çubuğu kadrajda olsun*

**Sorgu 1 — `fren direnci arızalı`**

> Türkçe bir belirti yazıyorum. Manueller İngilizce.
>
> Ve bakın, üç markadan birden sonuç geliyor. Siemens, ABB, Danfoss.
> Üçü de aynı arızayı farklı adlandırıyor ama sistem üçünü de buluyor.
>
> Teknisyenin hangi markayı kullandığını söylemesi gerekmiyor. Projenin
> asıl değeri burada.

**Sorgu 2 — `bu sürücünün fiyatı ne kadar`**

> Peki bilmediği bir şey sorulursa?
>
> Uydurmuyor. Bu bizim için en önemli davranıştı — birazdan nedenini
> söyleyeceğim.

---

## 1:35 – 2:15 · Nasıl ölçtük

> Peki bunun çalıştığını nereden biliyoruz? Ölçtük.
>
> Elli soruluk bir test seti hazırladık. Beş kategori: birebir kod sorguları,
> belirti tarifleri, prosedür soruları, markalar arası sorular, ve
> cevaplanamaz sorular.
>
> Bu seti projenin başında yazıp dondurduk. Sonradan yazsaydık, farkında
> olmadan sistemin cevaplayabildiği soruları seçerdik.
>
> Sonuçlar şöyle: kod sorgularında yüzde yüz isabet. Belirti sorgularında
> yüzde doksan. Kaynak sadakati yüzde doksan altı.
>
> Ve reddetme oranı yüzde yüz. Cevaplanamaz on sorunun hiçbirine uydurma
> cevap vermedi.

*Ekran: sonuç metrikleri tablosu*

---

## 2:15 – 2:45 · Neyi elediğimiz

> Bir de denediğimiz ama vazgeçtiğimiz şeyler var. Bence en öğretici kısım bu.
>
> Daha küçük bir model denedik. İki buçuk kat hızlıydı. Ama sadakat yüzde
> yüzden yüzde seksene düştü — Siemens bağlamı verdiğimizde cevaba bir
> Danfoss parametresi uydurdu. Sahadaki teknisyen yanlış ayara giderdi.
> Eledik.
>
> Daha büyük bir embedding modeli denedik. Beklediğimiz faydayı vermedi,
> üstelik bilgisayarı takasa itti. Onu da eledik.
>
> Yani mevcut kurulum tesadüf değil. Ölçerek savunduğumuz bir seçim.

---

## 2:45 – 3:00 · Kapanış

> Özetle: üç marka, beş yüz seksen arıza kaydı, tamamen çevrimdışı.
> Ve çalıştığını iddia etmiyoruz — ölçtük.
>
> Kod ve dokümantasyon GitHub'da. İzlediğiniz için teşekkürler.

---

## Soru-cevaba hazırlık

Bu metni anlatan kişi şu üç soruya cevap verebilmeli:

**"Neden her marka için ayrı ayrıştırıcı?"**
Üç üretici üç ayrı kodlama şeması kullanıyor. Siemens harf+5 hane, ABB
4 karakter onaltılık, Danfoss düz sayı. Sayfa düzenleri de farklı.

**"Test setini neden başta dondurdunuz?"**
Sonradan yazılan test seti, sistemin zaten cevaplayabildiği soruları seçme
eğilimi yaratır. Ölçüm anlamını kaybeder.

**"Reddetme oranı neden bu kadar önemli?"**
Yanlış cevabı emin bir tonla vermek, enerjili ekipmanla çalışan biri için
tehlikeli. Bu yüzden hedef 0.95 değil 1.00 kondu.

## Çekimden önce

1. `.venv/bin/python scripts/demo.py` — model **kayıt dışında** ısınır
2. Wi-Fi'yi kapat
3. Arayüz kullanılacaksa sayfayı yenile (`Cmd+R`)
4. Kaydı başlat
5. `fren direnci arızalı` ~12 saniye sürüyor — kurguda hızlandır

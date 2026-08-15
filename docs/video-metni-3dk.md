# 3 dakikalık video — konuşma metni

**Nasıl kullanılır:** Bunu ezberleme. Bir kez oku, akışı aklında tut, sonra
kendi kelimelerinle anlat. Ezberlenmiş metin okunduğu belli olur; doğal
konuşma tökezlese bile daha iyi durur.

Cümleler bilerek kısa. Uzun cümleler yüksek sesle okunurken nefes yetmiyor.

---

## 0:00 – 0:20 · Açılış

> Merhaba. Bu projede bir fabrikadaki bakım teknisyeninin problemini çözmeye
> çalıştım.
>
> Şöyle düşünün. Hatta bir motor sürücüsü durdu. Ekranda tek bir şey var:
> **F30002**. Bu kodun ne demek olduğu, beş yüz yetmiş sayfalık bir PDF'in
> içinde, bir tablo satırında yazıyor.
>
> Teknisyen de makine dairesinde. İnternet yok.

*Ekran: sürücü ekranı fotoğrafı ya da sadece büyük punto `F30002`*

---

## 0:20 – 0:45 · Ne yaptım

> Üstelik hatta tek marka yok. Siemens, ABB, Danfoss yan yana çalışıyor.
> Ve üçü aynı arızaya üç ayrı kod veriyor. Yani teknisyenin üç ayrı manuel
> taşıması gerekiyor.
>
> Ben de bu üç manueli tek bir asistanda birleştirdim. Model tamamen
> bilgisayarın kendi üzerinde çalışıyor — Microsoft Foundry Local ile.
> Çalışırken tek bir ağ isteği bile gitmiyor.

*Ekran: uygulamayı aç, sağ üstteki `ÇEVRİMDIŞI · AĞ İSTEĞİ 0` rozetine yakınlaş*

---

## 0:45 – 1:55 · Demo

> Göstereyim. Önce Wi-Fi'yi kapatıyorum. Bakın, kapalı.

*Menü çubuğunu kadraja al, Wi-Fi'yi kapat, bir saniye bekle*

**Sorgu 1 — `F30002 ne demek`**

> İlk olarak bir hata kodu soruyorum.
>
> Cevap anında geldi. Burada dil modeli aslında hiç çalışmıyor. Kod bir
> veritabanı indeksinde aranıyor ve manuelin kendi metni doğrudan geliyor.
> Kaynağı da yazıyor: sayfa beş yüz yirmi üç.

**Sorgu 2 — `ALARM 28`**

> Şimdi başka bir marka. Bu Danfoss'ta.
>
> Rozet farklı. Bu bir alarm — sürücü çalışmaya devam ediyor. Az önceki
> fault'tu, sürücü duruyordu. Teknisyen için bu ayrım önemli: hattı
> durduracak mı, durdurmayacak mı.

**Sorgu 3 — `fren direnci arızalı`** *(kurguda beklemeyi hızlandır)*

> Peki kodu bilmiyorsak?
>
> Türkçe yazıyorum, manueller İngilizce. Ve bakın — üç markadan birden
> sonuç geliyor. Hangi markayı kullandığımı söylemem gerekmiyor.

**Sorgu 4 — `bu sürücünün fiyatı ne kadar`**

> Son olarak şunu merak edebilirsiniz. Bilmediği bir şey sorulunca uyduruyor mu?
>
> Hayır. Elli soruluk testte bu oran yüzde yüz çıktı. Nedenini birazdan
> söyleyeceğim.

---

## 1:55 – 2:25 · Nasıl çalışıyor

> Kısaca nasıl çalıştığından bahsedeyim.
>
> İki yol var. Sorguda bir hata kodu varsa, sistem doğrudan veritabanına
> gidiyor. Dil modelini hiç çağırmıyor. Bu yüzden cevap anında geliyor.
>
> Kod yoksa, soru önce İngilizceye çevriliyor. Sonra hem anahtar kelime
> araması hem anlam araması birlikte çalışıyor.
>
> Ve eğer bulunanlar yeterince ilgili değilse, model yine çağrılmıyor.
> Sistem doğrudan "bilmiyorum" diyor.

*Ekran: brief'teki yönlendirme diyagramı (Şekil 1)*

---

## 2:25 – 2:50 · Öğrendiklerim

> Bu projede en çok şunu öğrendim: **prompt bir rica, kod bir garanti.**
>
> Başta modele "bilmiyorsan bilmiyorum de" diye yazmıştım. Yetmedi. Format
> talimatı ağır basınca, fiyat sorusuna alakasız bir cevap uydurdu.
>
> Kararı prompt'tan alıp koda taşıdım. Bir benzerlik eşiğine bağladım.
> Ondan sonra reddetme oranı yüzde yüz oldu ve orada kaldı.
>
> Bir de şunu gördüm: en tehlikeli hatalar sessiz olanlar. Ayrıştırıcım
> Siemens kodlarının yüzde otuzunu atlıyordu. Hiç hata vermedi. Ancak
> bağımsız bir sayımla karşılaştırınca fark ettim.

---

## 2:50 – 3:00 · Kapanış

> Özetle: beş yüz seksen arıza kaydı, üç marka, tamamen çevrimdışı.
>
> Kod ve dokümantasyon GitHub'da. İzlediğiniz için teşekkürler.

*Ekran: GitHub deposu ya da sonuç metrikleri*

---

## Doğal anlatım için

- **Ezberleme, akışı bil.** Altı bölüm var: problem, ne yaptım, demo, nasıl
  çalışıyor, ne öğrendim, kapanış. Bu sırayı bilmen yeterli.
- **Sayıları yazıyla söyle.** "F30002" derken "F otuz bin iki" değil,
  "F-otuz-sıfır-sıfır-iki" — ya da sadece "bu kod" de, ekranda zaten görünüyor.
- **Duraklamaktan korkma.** Kurguda kesersin. Ama "ıı", "şey" gibi dolgu
  seslerini kesmek zordur — onun yerine sus.
- **Ekrana bakarak konuş.** "Bakın", "burada", "şimdi" gibi kelimeler
  izleyiciyi ekrana yönlendirir ve doğal durur.
- **Tek seferde çek, sonra kes.** Bölüm bölüm çekip birleştirmek daha çok
  vakit alır ve ses tonu değişir.

## Zorunlu teknik adımlar

1. `.venv/bin/python scripts/demo.py` çalıştır — model **kayıt dışında** ısınır
2. Wi-Fi'yi kapat
3. Arayüz kullanacaksan sayfayı **yenile** (`Cmd+R`) — websocket yeniden kurulur
4. Kaydı başlat
5. `fren direnci arızalı` sorgusu ~12 saniye sürüyor — **kurguda hızlandır**

# Proje brifi: Hasta geçmişi ve dondurulmuş örnek analizi (yerel, Windows)

> Bu dosyayı proje klasörünün köküne `PROJE_BRIEF.md` adıyla koyun. Claude Code'u o klasörde açıp
> en alttaki "Claude Code'a ilk istem" bölümünü yapıştırın. Kod tanımlayıcıları İngilizce, arayüz
> metinleri ve kullanıcıya dönük mesajlar Türkçe olsun.

---

## 1. Amaç

Bir tüp bebek laboratuvarında, aylara göre ayrı tutulan Access (.accdb / .mdb) hasta kayıtlarını
(2017'den bugüne) okuyup birleştiren ve bir hasta hakkında şu soruları **tek ekranda, sade bir
özetle** yanıtlayan yerel bir program:

- Bu hasta (çift) bu ünitede **kaç tedavi** gördü, hangi tarihlerde?
- Her tedavide **neler yapıldı** (tedavi türü, uyarı/protokol, toplanan oosit, döllenme, embriyo
  sayısı ve kalitesi, transfer, dondurma)?
- Her tedavinin **sonucu** nedir (gebelik testi, gebelik, doğum; kayıtta ne varsa)?
- Hastanın **kullanılabilecek dondurulmuş örneği kaldı mı**? (embriyo, oosit, sperm; kaç adet,
  hangi tarihte donduruldu, hangi tedaviden kaldı, bir kısmı çözülüp kullanıldı mı?)

Kullanım senaryosu: Hasta geldi, hatırlamıyorum. Adını yazıyorum, birkaç saniyede geçmişini
okunaklı biçimde görüyorum. Örnek: hasta 2024 Mart'ta taze tedaviye gelmiş, embriyoları dondurulmuş,
sonra başka bir ay FET için gelmiş. Program bunları farklı aylık dosyalardan bulup zaman sırasına
koyar.

## 2. Değişmez kısıtlar

1. **Windows PC'de çalışacak** (işyeri bilgisayarı). Geliştirme şu an MacBook'ta başlıyor, ama
   nihai ürün Windows'ta çalışıp Windows'ta paketlenecek.
2. **Tamamen yerel ve çevrimdışı.** Hasta verisi bilgisayardan dışarı çıkmaz. Bulut yok, telemetri
   yok, otomatik güncelleme yok, dış sunucuya istek yok. Program internet olmadan çalışmalı.
3. **Access dosyalarına asla yazılmaz.** Salt okunur açılır. Orijinal dosyalara dokunulmaz.
4. **Terminal yok.** Kullanıcı hiçbir komut yazmayacak. Çift tıklayarak başlar, tepsi ikonuyla
   (system tray) kontrol edilir.
5. **Telefondan görüntüleme.** PC açık ve program çalışıyorsa, aynı Wi-Fi'deki telefon tarayıcıdan
   açabilmeli ("ana ekrana ekle" ile uygulama gibi durmalı).
6. Kolay başlatma: bkz. bölüm 6. "Telefondan başlatma" yerine **PC açılınca programın kendiliğinden
   hazır olması** hedeflenir.
7. KVKK: hasta verisi içerir. Bölüm 8'deki güvenlik maddeleri zorunlu.
8. Aylık kullanım: kullanıcı her ay sonu yeni bir Access dosyası kaydeder. Program yeni dosyayı
   kendisi bulup içeri almalı (veya tek tuşla "yeni dosyaları tara").

## 3. Önce keşif: şema raporu (Milestone 0, kod yazmadan önce yapılacak)

Access dosyalarının iç yapısını bilmeden mimari kesinleşemez. İlk iş, **veri içermeyen** bir şema
raporu üreten küçük bir keşif aracıdır:

- Klasördeki tüm .accdb/.mdb dosyalarını listeler (dosya adı, boyut, değiştirilme tarihi).
- Her dosya için tablo adları, sütun adları ve tipleri, satır sayıları, ilişkiler (varsa).
- **Yıllar arası şema farkı:** 2017'deki tablo/sütun yapısı bugünküyle aynı mı? Sütun adı değişen,
  eklenen, kaldırılan alanlar tablo halinde çıkarılır.
- Hasta ayırt edici alanlar var mı: protokol/dosya no, TC kimlik, doğum tarihi, barkod.
- Rapor `schema_report.md` dosyasına yazılır. Hasta adı vb. **yazılmaz**. İsteğe bağlı olarak her
  tablodan en fazla 3 örnek satır, kullanıcı onaylarsa ve alan değerleri maskelenmiş olarak.
- Kullanıcı bu raporu (verisiz) tekrar Claude sohbetine yapıştırıp alan eşlemesini birlikte
  yapabilir.

Bu rapor çıkmadan bölüm 5'teki veri modeli taslaktır. Sütun adlarını **tahmin etme**, rapordan al.

## 4. Mimari (önerilen, Claude Code gerekçeyle değiştirebilir)

```
Access dosyaları (salt okunur)
        │  Milestone 1: içe aktarma (artımlı)
        ▼
Yerel SQLite indeksi (yeniden üretilebilir, ProgramData altında, kısıtlı izin)
        │
        ▼
Yerel web sunucusu (Python + FastAPI, 127.0.0.1; isteğe bağlı LAN)
        │
        ├── PC tarayıcısı: tam ekran arayüz
        └── Telefon tarayıcısı: aynı arayüz (duyarlı tasarım, PWA)
        ▲
Sistem tepsisi uygulaması (pystray): başlat/durdur, "Telefonla bağlan" QR kodu,
yeni dosyaları tara, ayarlar, Windows açılışında otomatik başlat
```

- **Dil/araçlar:** Python 3.11+, FastAPI + uvicorn, SQLite, sade HTML/CSS/JS (derleme gerektiren
  framework gerekmesin; htmx veya düz JS yeterli). Tepsi için `pystray` + `Pillow`, QR için
  `qrcode`. Paketleme: **PyInstaller** (tek klasör ya da tek .exe), isteğe bağlı Inno Setup
  yükleyici. Paketleme Windows'ta yapılmalıdır (çapraz derleme güvenilir değil).
- **Access okuma, taşınabilirlik tuzağı:** Windows'ta olağan yol `pyodbc` +
  "Microsoft Access Database Engine" (ACE) sürücüsüdür. Dikkat: sürücünün 32/64 bit sürümü
  Python'un bit sürümüyle uyuşmalı, bilgisayarda kurulu Office'in bit sürümüyle çakışabilir.
  macOS'ta bu sürücü yok. Bu yüzden Access okumayı **tek bir arayüzün arkasına** koy:

  ```
  class AccessSource:   # list_tables(), read_table(name) -> iterator of dict
  ```

  Arkasında iki arka uç dene: (a) Windows için `pyodbc`+ACE, (b) Mac'te geliştirme/test için
  saf Python `access-parser` veya `mdbtools`. Aynı test dosyasında ikisinin çıktısını karşılaştır.
  Kullanıcının Windows PC'sinde hangisinin çalıştığını Milestone 0'da doğrula. Sürücü kurulumunu
  gerektiriyorsa yükleyici/ilk çalıştırma ekranı bunu Türkçe adım adım anlatsın.
- **SQLite indeksi:** Access verisini analiz için normalize eden **türetilmiş** bir kopya. Silinirse
  yeniden üretilebilir olmalı. Kaynak doğruluk her zaman Access dosyalarıdır.
- **Artımlı içe aktarma:** Her dosya için parmak izi (yol, boyut, değiştirilme zamanı, SHA-256)
  saklanır. Değişen/yeni dosya yeniden okunur, değişmeyen atlanır. Her dosya tek transaction'da
  içeri alınır, hata olursa o dosya geri alınır ve kullanıcıya hangi dosyada ne olduğu gösterilir.
  Klasör izleme (`watchdog`) veya "Yeni dosyaları tara" düğmesi.
- **Yerel ağ erişimi:** Varsayılan yalnızca `127.0.0.1`. Kullanıcı tepsi menüsünden "Telefon
  erişimini aç" derse `0.0.0.0` ve PIN zorunlu. Ekranda QR kod ve `http://BILGISAYAR-ADI:8765`
  adresi görünür. Windows Güvenlik Duvarı sorusunda yalnızca **Özel ağ** işaretlenmesi gerektiğini
  Türkçe açıkla.

## 5. Veri modeli ve analiz mantığı (şema raporundan sonra kesinleşir)

Aşağıdakiler **hipotezdir**. Gerçek tablo ve alan adları Milestone 0'dan gelir.

### 5.1 Hasta ve çift eşleştirme

- Kayıtlar aylık dosyalara dağıldığı için aynı kişi birçok dosyada görünür. Eşleştirme için,
  varsa, **sağlam bir anahtar** kullan (protokol/dosya no, TC, doğum tarihi). Yoksa ad + soyad +
  eş adı (+ doğum tarihi) birleşimi.
- Türkçe normalleştirme şart: `İ/ı, I/i, Ş, Ğ, Ü, Ö, Ç`, büyük/küçük harf, fazla boşluk,
  `\xa0` (kırılmaz boşluk), baştaki/sondaki boşluk. Arama "yilmaz" yazınca "YILMAZ" bulmalı.
- **Asla otomatik birleştirme yapma.** Aynı isimli iki farklı hasta olabilir. Belirsiz durumlarda
  adayları listele (ad, soyad, eş, doğum tarihi, ilk/son kayıt tarihi) ve kullanıcıya seçtir.
  Seçimi "birleştir/ayrı tut" kararı olarak yerel dosyada sakla (geri alınabilir).
- **Çift mantığı:** Tüp bebekte kayıt kadının, sperm kaydı erkeğin adıyla tutulabilir. Aranan
  kişinin hem kendi alanında hem **eş alanında** geçtiği kayıtlar birlikte gösterilsin.

### 5.2 Tedavi döngüsü (cycle)

Her hasta için kronolojik tedavi listesi. Her döngü için, kayıtta ne varsa:

- Tarih/ay, tedavi türü (IUI, IVF, ICSI, FET, donör, vb.), uyarı protokolü.
- OPU (toplama): toplanan oosit, MII sayısı, döllenme (2PN) sayısı.
- Embriyo gelişimi: günlük embriyo sayısı, kalite (örn. "4AA", "3BB"), blastosist sayısı.
- Transfer: tarih, gün (D3/D5), embriyo sayısı ve kalitesi.
- Dondurma: kaç embriyo/oosit/sperm, hangi cihaz/straw, tank-kanister-goblet bilgisi (varsa).
- Çözme/FET: hangi dondurmadan çözüldü, kaç tane çözüldü, sağ kalım, transfer.
- Sonuç: beta-hCG, klinik gebelik, doğum (kayıtta ne varsa, yoksa "kayıtta yok").

Eksik alanı **uydurma**. Kayıtta yoksa "bilgi yok" yaz.

### 5.3 Kalan dondurulmuş örnek hesabı (kritik)

Hasta başına, örnek türüne göre (embriyo / oosit / sperm):

```
kalan = dondurulan − (çözülen + kullanılan + atılan + başka yere devredilen)
```

Kurallar:

- Her sayıyı **kaynağına bağla**: hangi dosya, hangi ay, hangi kayıt (tıklayınca ham kayda git).
- Kayıtlar çelişiyor veya eksikse (çözülen > dondurulan, aynı örnek iki kez çözülmüş gibi, çözme
  kaydı yok) sonucu **"Doğrulanmalı"** uyarısıyla göster, kesin sayı gibi sunma.
- Çıktı dili temkinli olsun: "Kayıtlara göre 3 embriyo kalmış görünüyor" ve altında
  "Fiziksel doğrulama için tank haritasına bakın" notu. Bu araç **klinik karar vermez**, kayıtları
  derler. Her zaman son doğrulama tank haritası ve laboratuvar prosedürüyle yapılır.

### 5.4 Tank haritası ile çapraz kontrol (opsiyonel, M5)

Kullanıcının ayrıca bir Excel tank haritası var (Tank 1, 2, 4, 5, küçük tank, sperm sayfaları). Hasta
özetinde "Access'e göre kalan" ile "haritada bulunan" yan yana gösterilebilir, fark varsa
işaretlenir. Excel yapısı bu repoya ayrıca verilecek. Önce M0–M4'ü bitir.

## 6. Başlatma ve telefon

Kullanıcının isteği: terminal yok, kolay başlat, telefondan da aç. Gerçekçi tasarım:

1. **Çift tıkla başlat:** `HastaGecmisi.exe` (veya masaüstü kısayolu). İlk açılışta kurulum
   sihirbazı: Access klasörünü seç, PIN belirle, telefon erişimi isteniyor mu, Windows ile
   birlikte başlasın mı.
2. **Tepsi ikonu:** Aç (tarayıcıda), Yeni dosyaları tara, Telefonla bağlan (QR), Durdur/Çık.
3. **Windows açılışında otomatik başlat** (başlangıç klasörüne kısayol veya Görev Zamanlayıcı,
   kullanıcı onayıyla). Böylece PC açıldığında program hazırdır ve **telefondan ayrıca başlatmaya
   gerek kalmaz**; telefon yalnızca adresi açar.
4. **Telefondan başlatma (bilinçli sınır):** Kapalı/uykudaki bir bilgisayarda programı telefondan
   başlatmak için Wake-on-LAN veya uzak masaüstü gerekir. Bu internet/ağ ayarı gerektirir ve
   güvenlik riski taşır. İlk sürümde kapsam dışı. Bunun yerine: PC'nin uykuya geçmesini kapatma
   ayarı için kullanıcıya talimat ver. İleri aşama notu olarak Wake-on-LAN (aynı ağ içinde) not
   düşülebilir.
5. **Telefon arayüzü:** Duyarlı tasarım, tek sütun, büyük dokunma hedefleri, "ana ekrana ekle"
   (PWA manifest). Arama kutusu en üstte.

## 7. Arayüz (sade ve hızlı)

**Ana ekran:** tek bir arama kutusu (ad, soyad, eş adı, protokol no). Yazdıkça aday listesi.

**Hasta sayfası, yukarıdan aşağı:**

1. **Üst özet kartı (sade):** örnek metin biçimi
   - "3 tedavi · ilk kayıt 03.2021 · son kayıt 03.2024"
   - "Kayıtlara göre kullanılabilir dondurulmuş örnek: 2 embriyo (D5, 4AA ve 3BB)"
   - Varsa kırmızı/sarı uyarı: "Doğrulanmalı: çözme kaydı eksik".
2. **Tedavi zaman çizelgesi:** kronolojik kartlar, her biri tek satır özet (tarih, tür, sonuç),
   dokununca ayrıntı açılır. Kısa renk/ikon: taze, FET, dondurma, sonuç.
3. **Dondurulmuş örnek envanteri:** tablo, tür/adet/dondurma tarihi/kaynak tedavi/durum
   (kaldı, çözüldü, atıldı, belirsiz) ve kaynak bağlantısı.
4. **Kaynak kayıtlar:** hangi dosyadan hangi satır (denetim için).

İlkeler: önce sonuç, sonra ayrıntı. Türkçe, kısa cümle. Renk yalnızca anlam taşıyorsa. Kullanıcı
"istediğim sadelikte" diyor: varsayılan görünüm minimal, ayrıntı açılır panellerde.

## 8. Güvenlik ve gizlilik (zorunlu)

- Veri yalnızca bu bilgisayarda. Program hiçbir dış adrese bağlanmaz (testle doğrula: dış ağ
  engelliyken tam çalışmalı).
- **PIN/parola:** LAN erişimi açıkken zorunlu, yerel kullanımda da isteğe bağlı. Parola
  Argon2/bcrypt ile saklanır, deneme sayısı sınırlanır, oturum zaman aşımı olur.
- SQLite indeksi `C:\ProgramData\HastaGecmisi\` altında, yalnızca ilgili Windows kullanıcısına açık
  izinle. İsterseniz SQLCipher ile şifreleme seçeneği. BitLocker'ın açık olmasını kullanıcıya
  öner (ilk çalıştırma kontrol listesi).
- LAN'da düz HTTP riski: PIN dinlenebilir. Güvenilir ağda kullan, misafir Wi-Fi'den ayır uyarısı
  göster. İsteğe bağlı: yerel kendinden imzalı sertifika ile HTTPS ve telefona güven kurma
  talimatı (ileri aşama).
- Günlüklerde (log) hasta adı, TC vb. **yazılmaz**. Hata ayıklama günlüğü yalnızca teknik bilgi.
- Access dosyaları ve indeks yedeklenmez/kopyalanmaz, program kullanıcıya bunu söylemekle yetinir.
- Hata mesajları kullanıcıya hasta verisi sızdırmaz.

## 9. Test ve kabul

- **Sentetik veri üretici:** gerçek yapıya uyan, tamamen uydurma hastalardan oluşan örnek Access
  dosyaları (farklı yıllar, şema farkları dahil). Geliştirme ve testlerde yalnızca bunlar kullanılır.
  Gerçek veri yalnızca kullanıcının kendi PC'sinde, kullanıcı tarafından çalıştırılır.
- Birim testleri: Türkçe normalleştirme, eşleştirme (aynı ad farklı kişi, eş alanı), şema farklı
  dosyalar, kalan örnek hesabı (çelişkili kayıt dahil), artımlı içe aktarma.
- Kabul ölçütleri:
  1. Bilinen bir hasta için tüm yıllardan tedaviler doğru sırayla çıkıyor.
  2. Kalan dondurulmuş örnek sayısı elle hesapla aynı ya da "Doğrulanmalı" ile işaretli.
  3. İnternet kapalıyken tam çalışıyor.
  4. Telefon, aynı Wi-Fi'den PIN ile açıyor.
  5. Yeni aylık dosya klasöre konunca, taramadan sonra o aydaki yeni kayıtlar görünüyor.
  6. Hiçbir Access dosyasının değiştirilme zamanı değişmiyor (test et).

## 10. Aşamalar

| # | Aşama | Çıktı |
|---|---|---|
| M0 | Şema keşfi | `schema_report.md`, Windows'ta çalışan Access okuma yöntemi seçimi |
| M1 | İçe aktarma + arama | Artımlı içe aktarma, SQLite, ad/eş/protokol araması, aday listesi |
| M2 | Hasta zaman çizelgesi | Tedavi döngüleri, kaynak kayıt bağlantıları |
| M3 | Kalan dondurulmuş örnek | Envanter, hesap kuralları, "Doğrulanmalı" uyarıları |
| M4 | Windows paketi | PyInstaller, tepsi, kurulum sihirbazı, otomatik başlatma, QR/PIN, telefon arayüzü |
| M5 | Tank haritası çapraz kontrol (opsiyonel) | Access ile Excel haritayı karşılaştırma |

Her aşama sonunda çalışan, denenebilir bir sürüm ver ve kullanıcıdan onay al.

## 11. Kullanıcıdan gerekenler (Claude Code sorabilir)

- [ ] Access dosyalarının klasör yapısı ve adlandırma biçimi (yıl/ay, tek klasör mü, alt klasör mü).
- [ ] Windows sürümü ve işyeri PC'sinde yönetici hakkı olup olmadığı (sürücü kurulumu için).
- [ ] Kurulu Office/Access var mı, 32 mi 64 bit mi.
- [ ] Bir **anonimleştirilmiş** küçük örnek dosya veya M0 şema raporu.
- [ ] Hastayı ayırt eden alan var mı (protokol no, TC, doğum tarihi).
- [ ] Tedavi türleri ve dondurma/çözme kayıtlarının Access'te nasıl tutulduğu (hangi tablolar).
- [ ] Telefon erişimi için PC ve telefon aynı Wi-Fi'de mi.
- [ ] Çalışma ağında Windows Güvenlik Duvarı'nı değiştirme izni.

## 12. Çalışma kuralları (CLAUDE.md'ye taşınabilir)

- Hasta verisini hiçbir koşulda dış servise gönderme, günlüğe yazma, test dosyasına koyma.
- Access dosyalarını yalnızca salt okunur aç. Yazma/silme/yeniden adlandırma kodu yazma.
- Geliştirmede yalnızca sentetik veri kullan.
- Şema raporundaki gerçek sütun adlarına dayan, tahminle alan uydurma.
- Belirsiz eşleşmede otomatik karar verme, kullanıcıya sor.
- Her sayıyı kaynak kaydına bağla. Emin olunmayan sonucu "Doğrulanmalı" diye işaretle.
- Arayüz Türkçe, hataları kullanıcıya düz Türkçeyle anlat (yığın izi gösterme).
- Her milestone sonunda `README_KULLANICI.md` güncelle (kurulum ve kullanım, ekran görüntüsüz,
  kısa).

---

## Claude Code'a ilk istem (kopyala-yapıştır)

```
Bu klasördeki PROJE_BRIEF.md dosyasını baştan sona oku. Önce Milestone 0'ı yap:
Access dosyalarının şemasını çıkaran, hasta verisi içermeyen küçük bir keşif aracı yaz
(schema_report.md üretsin). Mac'te geliştiriyorum, nihai hedef Windows. Access okumayı
AccessSource arayüzü arkasında uygula, bu makinede çalışan bir arka uç seç ve neden seçtiğini
açıkla. Tahminle alan adı uydurma. Başlamadan önce brifte eksik ya da çelişkili bulduğun
noktaları kısaca listele ve bana en fazla 5 soru sor. Hasta verisini hiçbir koşulda dış servise
gönderme ve günlüklere yazma.
```

# Telefondan doğrudan Drive'dan kullanım (kurulum)

Bu yol, bilgisayar kapalıyken de çalışır: telefon Access dosyalarını **kendisi Drive'dan indirir**, okur ve
telefonda saklar. Bilgisayar gerekmez. **Önce `README_KULLANICI.md` sonundaki gizlilik uyarısını okuyun.**

## 1. Güvenlik (başlamadan)
- Hasta kayıtları Google hesabınızdan geçip telefona iner ve telefonda (tarayıcı deposunda) **şifresiz** durur.
  Telefonda ekran kilidi (PIN/parmak izi) ve cihaz şifrelemesi açık olmalı. Kurumunuzun veri sorumlusuna danışın (KVKK).
- Kurum Google hesabı kullanın; Drive klasörünü yalnızca gereken kişilerle paylaşın.
- Telefon kaybolursa: Google hesabınızdan "Üçüncü taraf erişimi"ni kaldırın ve telefonu uzaktan silin.
- Telefondaki **"Bu telefondaki verileri sil"** düğmesi tüm yerel veriyi siler (Drive'a dokunmaz).

## 2. Sayfayı yayınlayın (bir kez, sayfada hasta verisi yok)
1. GitHub'da depo → **Settings → Pages**.
2. Source: **Deploy from a branch**; Branch: `claude/new-session-qk36e1`, klasör **`/docs`** → Save.
3. Birkaç dakika sonra adres görünür: `https://onurerturk80.github.io/PatientFinder/`
   (Kendi kullanıcı/depo adınıza göre.) Not: depo özelse Pages ücretli planda çalışır.

## 3. Google'da izin tanımlayın (bir kez)
1. https://console.cloud.google.com → yeni proje ("HastaGecmisi").
2. **API'ler → Kitaplık → Google Drive API → Etkinleştir.**
3. **OAuth izin ekranı:** Kullanıcı türü *Harici* (kurum hesabıysa *Dahili*), uygulama adı yazın; **Kapsam:**
   `.../auth/drive.readonly`; **Test kullanıcıları:** kendi Google adresinizi ekleyin. (Yayınlamayın, "Test" modunda kalsın.)
4. **Kimlik bilgileri → Kimlik bilgisi oluştur → OAuth istemci kimliği → Web uygulaması.**
   **Yetkili JavaScript kaynağı** olarak yalnızca sayfa adresinin kökünü yazın: `https://onurerturk80.github.io`
5. Oluşan **İstemci Kimliği**'ni kopyalayın (`....apps.googleusercontent.com`).

## 4. Telefonda
1. Sayfa adresini açın. İlk kurulum ekranına **İstemci Kimliği**'ni ve **Drive klasör bağlantısını** yapıştırın.
2. **Drive ile eşitle** → Google girişi → izin ver. 108 dosya (~180 MB) ilk seferde iner: **Wi‑Fi'de yapın**.
3. Sonraki eşitlemelerde yalnızca yeni/değişen dosyalar iner.
4. Tarayıcı menüsünden **Ana ekrana ekle**.
Eşitlendikten sonra arama internetsiz de çalışır (sayfa açılışı için internet gerekir).

## Sınırlar
- Google "test" modundaki uygulamalarda giriş her eşitlemede yeniden onay isteyebilir; bu beklenen davranıştır.
- Python sürümündeki tüm mantık JavaScript'e taşındı; ikisi aynı örnek dosyalarda aynı sonucu verir. Gerçek 108 dosyanızda
  ilk deneme sizindir; okunamayan dosyalar ekranda ve "Okunamadı:" satırında listelenir.
- Bu yol bilgisayardaki programdan (`baslat.bat`) bağımsızdır. İkisi birlikte de kullanılabilir.

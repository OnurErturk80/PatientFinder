# Şema keşif aracı (Milestone 0)

Access dosyalarınızın **yapısını** (tablo/sütun adları, tipler, satır sayıları) çıkarır.
Hasta verisi rapora yazılmaz. Access dosyalarına yazılmaz (salt okunur).

## Windows'ta kullanım (Python kurulu)
1. Bu klasörde bir kez: `pip install -r requirements.txt` (veya `exe_olustur.bat` ile tek .exe üretin).
2. `calistir.bat` dosyasına çift tıklayın, Access dosyalarının klasörünü seçin.
3. Aynı klasörde oluşan `schema_report.md` dosyasını Claude sohbetine yapıştırın.

## Notlar
- Önce Windows'taki ACE sürücüsü (pyodbc) denenir; yoksa saf Python okuyucuya geçilir.
  Hangisinin çalıştığı rapordaki "Arka uç" sütununda görünür. İsterseniz zorlayın:
  `python -m hastagecmisi_m0 KLASOR --backend access-parser` veya `--backend pyodbc`.
- Bir dosya okunamazsa raporda "HATA" yazar; diğer dosyalar etkilenmez.

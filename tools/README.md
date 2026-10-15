# Test verisi üretici

`GenSample.java`, şema raporundaki `VERİTABANI` yapısında **tamamen uydurma** hastalardan örnek `.accdb` üretir.
Üretilmiş örnekler `tests/fixtures/sample/` altındadır.

Yeniden üretmek (Java + Jackcess gerekir):

    javac -cp "jackcess-4.0.5.jar:commons-lang3-3.14.0.jar:commons-logging-1.3.0.jar" -d cls tools/GenSample.java
    java -Dfmt=V2007 -cp "jackcess-4.0.5.jar:commons-lang3-3.14.0.jar:commons-logging-1.3.0.jar:cls" GenSample tests/fixtures/sample

(`V2010` biçimini `access-parser` 0.0.6 okuyamadığı için V2007 kullanılır.)

Telefon uygulaması uçtan uca testi: `python tests/e2e_phone.py tests/fixtures/sample` (playwright + Chromium gerekir).

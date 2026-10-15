// Şema raporundaki VERİTABANI yapısında, TAMAMEN UYDURMA hastalardan örnek .accdb üretir (test için).
// Derleme/çalıştırma: bkz. tools/README.md
import com.healthmarketscience.jackcess.*;
import java.io.File;
import java.util.*;

public class GenSample {
    static Database.FileFormat FMT = Database.FileFormat.valueOf(System.getProperty("fmt", "V2007"));
    static Table make(Database db) throws Exception {
        TableBuilder t = new TableBuilder("VERİTABANI");
        t.addColumn(new ColumnBuilder("Kimlik", DataType.LONG).setAutoNumber(true));
        t.addColumn(new ColumnBuilder("DOSYA NO", DataType.LONG));
        for (String c : new String[]{"SOYADI", "ADI", "EŞİNİN ADI", "TEDAVİ PROTOKOLÜ", "FERTİLİZASYON YÖNTEMİ",
                "EMBRİYO TRANSFER AŞAMASI", "EMBRİYO1 HÜCRE/AŞAMA", "EMBRİYO1 KALİTE", "EMBRİYO DONDURMA AŞAMASI",
                "ABORT", "MISSED", "EKTOPİK"})
            t.addColumn(new ColumnBuilder(c, DataType.TEXT));
        for (String c : new String[]{"NOTLAR", "NOTLAR CONFIDENTIAL"})
            t.addColumn(new ColumnBuilder(c, DataType.MEMO));
        for (String c : new String[]{"DOĞUM TARİHİ", "OPU TARİHİ", "TRANSFER TARİHİ"})
            t.addColumn(new ColumnBuilder(c, DataType.SHORT_DATE_TIME));
        for (String c : new String[]{"TOPLANAN OOSİT", "MATÜR (MII)", "NORMAL FERTİLİZASYON (2PN)",
                "TRANSFER EDİLEN EMBRİYO SAYISI", "DONDURULAN EMBRİYO SAYISI", "ÇÖZDÜRÜLEN EMBRİYO SAYISI",
                "İLK USG FHB KESE", "CANLI DOĞUM SAYISI"})
            t.addColumn(new ColumnBuilder(c, DataType.LONG));
        t.addColumn(new ColumnBuilder("BİRİNCİ BHCG", DataType.FLOAT));
        return t.toTable(db);
    }

    static Date d(int y, int m, int day) { return new GregorianCalendar(y, m - 1, day).getTime(); }

    static Map<String, Object> row(Object... kv) {
        Map<String, Object> m = new LinkedHashMap<>();
        for (int i = 0; i < kv.length; i += 2) m.put((String) kv[i], kv[i + 1]);
        return m;
    }

    public static void main(String[] a) throws Exception {
        String dir = a[0];
        new File(dir + "/2023").mkdirs();
        new File(dir + "/2024").mkdirs();
        // 2023 MART: taze tedavi, 3 embriyo dondurulmuş (DOSYA NO 1001)
        try (Database db = DatabaseBuilder.create(FMT, new File(dir + "/2023/MART.accdb"))) {
            Table t = make(db);
            t.addRowFromMap(row("DOSYA NO", 1001, "SOYADI", "Yılmaz", "ADI", "Ayşe", "EŞİNİN ADI", "Mehmet",
                    "TEDAVİ PROTOKOLÜ", "ANTAGONIST", "FERTİLİZASYON YÖNTEMİ", "ICSI", "EMBRİYO TRANSFER AŞAMASI", "D5",
                    "EMBRİYO1 KALİTE", "4AA", "EMBRİYO DONDURMA AŞAMASI", "D5", "NOTLAR", "2 embriyo da notta yazıyor",
                    "DOĞUM TARİHİ", d(1990, 5, 1), "OPU TARİHİ", d(2023, 3, 10), "TRANSFER TARİHİ", d(2023, 3, 15),
                    "TOPLANAN OOSİT", 10, "MATÜR (MII)", 8, "NORMAL FERTİLİZASYON (2PN)", 6,
                    "TRANSFER EDİLEN EMBRİYO SAYISI", 1, "DONDURULAN EMBRİYO SAYISI", 3, "BİRİNCİ BHCG", 250f));
            t.addRowFromMap(row("DOSYA NO", 1002, "SOYADI", "ŞAHİN", "ADI", "Işıl", "EŞİNİN ADI", "Çağrı",
                    "DOĞUM TARİHİ", d(1988, 2, 2)));
        }
        // 2024 OCAK: aynı hasta (eş adında yazım farkı), 2 embriyo çözülmüş FET
        try (Database db = DatabaseBuilder.create(FMT, new File(dir + "/2024/OCAK.accdb"))) {
            Table t = make(db);
            t.addRowFromMap(row("DOSYA NO", 1001, "SOYADI", "Yilmaz", "ADI", "Ayşe", "EŞİNİN ADI", "Mehmed",
                    "EMBRİYO TRANSFER AŞAMASI", "D5", "DOĞUM TARİHİ", d(1990, 5, 1), "TRANSFER TARİHİ", d(2024, 1, 20),
                    "TRANSFER EDİLEN EMBRİYO SAYISI", 2, "ÇÖZDÜRÜLEN EMBRİYO SAYISI", 2, "İLK USG FHB KESE", 1,
                    "BİRİNCİ BHCG", 900f));
        }
    }
}

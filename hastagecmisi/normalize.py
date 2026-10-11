"""Türkçe metin normalleştirme: arama ve eşleştirme anahtarı üretir."""
import re
import unicodedata

_MAP = str.maketrans({"İ": "i", "I": "i", "ı": "i", "Ş": "s", "ş": "s", "Ğ": "g", "ğ": "g",
                      "Ü": "u", "ü": "u", "Ö": "o", "ö": "o", "Ç": "c", "ç": "c"})


def norm(text) -> str:
    """'  YILMAZ\xa0Şükrü ' -> 'yilmaz sukru'. None -> ''."""
    if text is None:
        return ""
    s = str(text).replace("\xa0", " ").translate(_MAP)
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch)).lower()
    return re.sub(r"\s+", " ", s).strip()


def full_name(first, last) -> str:
    return norm(f"{first or ''} {last or ''}")

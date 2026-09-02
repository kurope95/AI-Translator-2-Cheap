LANGUAGE_CODES = {
    "English": "en",
    "Belarusian": "be",
    "Bulgarian": "bg",
    "Croatian": "hr",
    "Czech": "cs",
    "Danish": "da",
    "Dutch": "nl",
    "Estonian": "et",
    "Finnish": "fi",
    "French": "fr",
    "German": "de",
    "Greek": "el",
    "Russian": "ru",
    "Slovak": "sk",
    "Polish": "pl",
    "Italian": "it",
    "Arabic": "ar",
    "Hungarian": "hu",
    "Latvian": "lv",
    "Lithuanian": "lt",
    "Norwegian": "no",
    "Portuguese": "pt",
    "Romanian": "ro",
    "Serbian (Azbuka)": "sr-cyrl",
    "Serbian (Latin)": "sr-latn",
    "Slovenian": "sl",
    "Spanish": "es",
    "Swedish": "sv",
    "Turkish": "tr",
    "Ukrainian": "uk",
}

LANGUAGES = sorted(LANGUAGE_CODES.keys())

DECIMAL_COMMA_LANGUAGES = {
    "Belarusian", "Bulgarian", "Croatian", "Czech", "Danish", "Dutch",
    "Estonian", "Finnish", "French", "German", "Greek", "Hungarian",
    "Italian", "Latvian", "Lithuanian", "Norwegian", "Polish", "Portuguese",
    "Romanian", "Russian", "Serbian (Azbuka)", "Serbian (Latin)", "Slovak",
    "Slovenian", "Spanish", "Swedish", "Turkish", "Ukrainian",
}

APP_NAME = "AI Translator 2"

GEMINI_BACKEND_MODEL_MAP = {
    "gemini": "gemini-3-flash-preview",
    "gemini-pro": "gemini-3.1-pro-preview",
    "gemini-25-flash": "gemini-2.5-flash",
    "gemini-25-pro": "gemini-2.5-pro",
    # 2026-09-02: 3.1 Flash Lite retired in favour of the GA 3.5 Flash Lite;
    # 3.7 Flash added. Old backend ids are aliased in app.py's upload handler,
    # so a stale saved selection still resolves here.
    "gemini-35-flash-lite": "gemini-3.5-flash-lite",
    "gemini-37-flash": "gemini-3.7-flash",
}

GEMINI_REQUEST_CHAR_LIMIT = 24000
FINALIZATION_PROGRESS_STEPS = 1

DEEPL_LANGUAGE_CODES = {
    "Arabic": "AR",
    "Belarusian": "BE",
    "Bulgarian": "BG",
    "Croatian": "HR",
    "Czech": "CS",
    "Danish": "DA",
    "Dutch": "NL",
    "English": "EN-US",
    "Estonian": "ET",
    "Finnish": "FI",
    "French": "FR",
    "German": "DE",
    "Greek": "EL",
    "Hungarian": "HU",
    "Italian": "IT",
    "Latvian": "LV",
    "Lithuanian": "LT",
    "Norwegian": "NB",
    "Polish": "PL",
    "Portuguese": "PT-PT",
    "Romanian": "RO",
    "Russian": "RU",
    "Serbian": "SR",
    "Slovak": "SK",
    "Slovenian": "SL",
    "Spanish": "ES",
    "Swedish": "SV",
    "Turkish": "TR",
    "Ukrainian": "UK",
}

CYRILLIC_TO_LATIN_MAP = {
    "А": "A", "а": "a", "Б": "B", "б": "b", "В": "V", "в": "v", "Г": "G", "г": "g",
    "Д": "D", "д": "d", "Ђ": "Đ", "ђ": "đ", "Е": "E", "е": "e", "Ж": "Ž", "ж": "ž",
    "З": "Z", "з": "z", "И": "I", "и": "i", "Ј": "J", "ј": "j", "К": "K", "к": "k",
    "Л": "L", "л": "l", "Љ": "Lj", "љ": "lj", "М": "M", "м": "m", "Н": "N", "н": "n",
    "Њ": "Nj", "њ": "nj", "О": "O", "о": "o", "П": "P", "п": "p", "Р": "R", "р": "r",
    "С": "S", "с": "s", "Т": "T", "т": "t", "Ћ": "Ć", "ћ": "ć", "У": "U", "у": "u",
    "Ф": "F", "ф": "f", "Х": "H", "х": "h", "Ц": "C", "ц": "c", "Ч": "Č", "ч": "č",
    "Џ": "Dž", "џ": "dž", "Ш": "Š", "ш": "š",
}

LATIN_TO_CYRILLIC_DIGRAPHS = {
    "DŽ": "Џ", "Dž": "Џ", "dž": "џ",
    "LJ": "Љ", "Lj": "Љ", "lj": "љ",
    "NJ": "Њ", "Nj": "Њ", "nj": "њ",
}

LATIN_TO_CYRILLIC_MAP = {
    "A": "А", "a": "а", "B": "Б", "b": "б", "V": "В", "v": "в", "G": "Г", "g": "г",
    "D": "Д", "d": "д", "Đ": "Ђ", "đ": "ђ", "E": "Е", "e": "е", "Ž": "Ж", "ž": "ж",
    "Z": "З", "z": "з", "I": "И", "i": "и", "J": "Ј", "j": "ј", "K": "К", "k": "к",
    "L": "Л", "l": "л", "M": "М", "m": "м", "N": "Н", "n": "н", "O": "О", "o": "о",
    "P": "П", "p": "п", "R": "Р", "r": "р", "S": "С", "s": "с", "T": "Т", "t": "т",
    "Ć": "Ћ", "ć": "ћ", "U": "У", "u": "у", "F": "Ф", "f": "ф", "H": "Х", "h": "х",
    "C": "Ц", "c": "ц", "Č": "Ч", "č": "ч", "Š": "Ш", "š": "ш",
}

# Kruti Dev legacy font → Unicode Devanagari converter
# Mappings verified against April 2026.xlsx cell values

# Multi-character sequences — checked before single chars
TWO_CHAR = {
    'ks': 'ो',   # o matra
    'kS': 'ौ',   # au matra
    '.k': 'ण',   # na retroflex
    'bZ': 'ई',   # long I vowel
    ';s': 'ऐ',   # ai vowel
    'Dk': 'क्क',
    '\'k': 'शक',
}

# Single-character mappings
ONE_CHAR = {
    # Vowel matras
    'k': 'ा',   'h': 'ी',   'q': 'ु',   'w': 'ू',
    's': 'े',   'S': 'ै',   'a': 'ं',   'Z': '्र',
    'f': 'ि',   'z': 'ज्',

    # Standalone vowels
    'v': 'अ',   'b': 'इ',   'm': 'उ',   ',': 'ए',

    # Consonants — confirmed
    'd': 'क',   'e': 'म',   'g': 'ह',   'G': 'ळ',
    'H': 'भ',   'j': 'र',   'l': 'स',   'n': 'द',
    'o': 'व',   'p': 'च',   'r': 'त',   'V': 'ट',
    'B': 'ठ',   'y': 'ल',   ';': 'य',   'M': 'ड',

    # Consonants — standard Kruti Dev
    'x': 'ग',   'X': 'घ',   'u': 'न',   'i': 'प',
    'Q': 'फ',   'c': 'ब',   'F': 'थ',   't': 'ज',
    'N': 'छ',   'U': 'ण',   'I': 'ध',   'R': 'ठ',
    'W': 'श्र', 'L': 'श्र', 'T': 'ट्',

    # Special characters (Kruti Dev uses Latin-1 extended)
    'ª': '्र',   # subscript ra  e.g. राष्ट्रीय
    '®': '्र',   # alternate subscript ra
    'Ø': 'क्र',  # e.g. कार्यक्रम
    '/': 'ध्',   # dha halant  e.g. मध्यान्ह
    '¸': 'ं',   # anusvara alternate
    '·': 'ँ',   # chandrabindu

    # Punctuation / symbols
    "'": 'श',   '"': 'ष',   '~': '्',   '%': 'ः',
    '¼': '(',   '½': ')',   '|': '।',   '\\': '।',
    '&': '&',   '-': '-',   '=': '=',   '+': '+',
    '@': '@',
}


def to_marathi(text) -> str:
    """Convert a Kruti Dev encoded string to Unicode Devanagari."""
    if not isinstance(text, str):
        return str(text) if text is not None else ""

    result = []
    i = 0
    while i < len(text):
        two = text[i:i+2]
        if two in TWO_CHAR:
            result.append(TWO_CHAR[two])
            i += 2
        elif text[i] in ONE_CHAR:
            result.append(ONE_CHAR[text[i]])
            i += 1
        else:
            result.append(text[i])
            i += 1

    return "".join(result)

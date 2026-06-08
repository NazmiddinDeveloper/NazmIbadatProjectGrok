# Tajvid harflari va qoidalari

# Qalqala harflari — bosilganda "sakrash" bo'ladi
QALQALA = set('قطبجد')

# Madd harflari — cho'ziq o'qiladi  
MADD = set('اوي')

# Ghunna — burun tovushi (mim va nun)
GHUNNA = set('من')

# Shamsiy harflar — "al" dan keyin harfga qo'shiladi
SHAMSIY = set('تثدذرزسشصضطظلن')

# Qamariy harflar
QAMARIY = set('ابجحخعغفقكمهوي')

# Ikhfa harflari — nun/tanvin dan keyin
IKHFA = set('تثجدذزسشصضطظفقك')

# Izhar harflari
IZHAR = set('حخعغهء')


def classify_char(char, prev_char=None, next_char=None):
    """
    Har bir arabcha harfni tajvid qoidasiga ko'ra tasniflaydi.
    Qaytaradi: CSS klass nomi
    """
    if char in QALQALA:
        return 'tajvid-qalqala'
    if char in MADD:
        return 'tajvid-madd'
    if char in GHUNNA:
        # Shadda bilan kelsa — ghunna kuchli
        if next_char == 'ّ':
            return 'tajvid-ghunna'
        return 'tajvid-ghunna'
    return None


def colorize_arabic(text):
    """
    Arabcha matnni tajvid ranglari bilan HTML ga aylantiradi.
    """
    if not text:
        return text

    result = []
    i = 0
    while i < len(text):
        char = text[i]
        prev_char = text[i-1] if i > 0 else None
        next_char = text[i+1] if i < len(text)-1 else None

        css_class = classify_char(char, prev_char, next_char)

        if css_class:
            result.append(f'<span class="{css_class}">{char}</span>')
        else:
            result.append(char)
        i += 1

    return ''.join(result)
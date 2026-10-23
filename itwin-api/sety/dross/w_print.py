from sety.any.colors import cprint

dross_text = ''

# [Claude 2026-10-18] Очищает накопленный текст протокола дросселирования.
def w_init():
    global dross_text
    dross_text = ''

# [Claude 2026-10-18] Печатает строку (в цвете) и добавляет ее в накопленный текст протокола.
def w_print(text, color=None):
    global dross_text
    cprint(text, color=color)
    dross_text += text
    dross_text += '\n'


# [Claude 2026-10-18] Возвращает накопленный текст протокола дросселирования.
def get_text():
    global dross_text
    return dross_text
from sety.any.colors import cprint

dross_text = ''

def w_init():
    global dross_text
    dross_text = ''

def w_print(text, color=None):
    global dross_text
    cprint(text, color=color)
    dross_text += text
    dross_text += '\n'


def get_text():
    global dross_text
    return dross_text
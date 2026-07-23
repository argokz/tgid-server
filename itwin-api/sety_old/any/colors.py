import os
import sys
from enum import Enum

from sety import config



#------------------------------------------------------

#color_yes = True
color_yes = False

def nbsp(text):
    if config.args.g_color:
        return text.replace(' ', '&nbsp;')

    return text


def is_color():
    return config.args.g_color

class Color(Enum):
    RED = (255, 0, 0)
    GREEN = (0, 255, 0)
    BLUE = (0, 0, 255)
    YELLOW = (255, 255, 0)
    CYAN = (0, 255, 255)
    MAGENTA = (255, 0, 255)
    BROWN = (128, 64, 48)
    PURPLE = (106, 13, 173)
    DEFAULT = (0, 0, 0)

#------------------------------------------------------

def start_color(r, g, b):
    return f'\033[38;2;{r};{g};{b}m'

#------------------------------------------------------

def code_to_rgb(code):
    r, g, b = (code >> 16) & 0xFF, (code >> 8) & 0xFF, code & 0xFF
    return r, g, b

#------------------------------------------------------

def start_color_code(code):
    r, g, b = code_to_rgb(code)
    return start_color(r, g, b)

#------------------------------------------------------

def end_color():
    return '</span>'
#    return '\033[0m'

#------------------------------------------------------

map_color_old = {
    'red': start_color(255, 0, 0),
    'green': start_color(0, 255, 0),
#    'green1': start_color_code(0x00FF00),
    'green1': start_color(*code_to_rgb(0x00FF00)),
    'blue': start_color(0, 0, 255),
    'yellow': start_color(255, 255, 0),
    'cyan': start_color(0, 255, 255),
    'magenta': start_color(255, 0, 255),
    'brown': start_color(128, 64, 48),
    'purple': start_color(106, 13, 173),
    '-': '\033[0m',

    'b': '\033[1m',
    '/b': '\033[21m',

    'u': '\033[3m',
    '/u': '\033[23m',

    'i': '\033[4m',
    '/i': '\033[24m',
    
    'blink': '\033[5m',
    '/blink': '\033[25m',

    'reverse': '\033[7m',
    '/reverse': '\033[27m',
}

#------------------------------------------------------

map_color = {
    'red': '<span style="color:red">',
    'green': '<span style="color:green">',
    'green1': '<span style="color:green">',
    'blue': '<span style="color:blue">',
#    'yellow': '<span style="color:yellow">',
    'yellow': '<span style="color:brown">',
    'cyan': '<span style="color:cyan">',
    'magenta': '<span style="color:magenta">',
    'brown': '<span style="color:brown">',
    'purple': '<span style="color:purple">',
    '-': '</span>',

    'b': '<b>',
    '/b': '</b>',

    'u': '<u>',
    '/u': '</u>',

    'i': '<i>',
    '/i': '</i>',
    
    'blink': '\033[5m',
    '/blink': '\033[25m',

    'reverse': '\033[7m',
    '/reverse': '\033[27m',
}


def parse_colors(x):
#    x = x.replace('[-]', end_color())

    for key, value in map_color.items():
        if config.args.g_color:
            x = x.replace(f'[{key}]', value)
        else:
            x = x.replace(f'[{key}]', "")
        
    return x


def cprint(*objects, sep=' ', end='\n', file=sys.stdout, flush=False, color=None):
    objects = map(lambda x:  x if not isinstance(x, str) else parse_colors(x), objects)

    if config.args.g_color and color is not None:
        col = map_color.get(color, end_color())
        print(col, end='', file=file);


    if config.args.g_color:
        for o in objects:
#            o = o.replace(' ', '&nbsp;')
            print(o, sep=sep, end='', file=file)
        
    else:
        print(*objects, sep=sep, end='', file=file)

    if config.args.g_color and color is not None:
        print(end_color(), end='', file=file);

    print(*objects, end=end, file=file, flush=flush)


#------------------------------------------------------

if __name__ == "__main__":
    if sys.platform == 'win32':
       os.system('color')

    text = 'H[green1]e[-]l[blue]l[-]o, [red][u][i]World[/u] ertwetre[-]!'

    cprint(1, 2, text, 'ryter')
    cprint('rgtweryer', color='cyan')
    cprint('rgtweryer', color='magenta')
    cprint('rgtweryer', color='brown')
    cprint('rgtweryer', color='purple')

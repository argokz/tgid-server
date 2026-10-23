# [Claude, 2026-08-22] Общий helper для отладочной печати — показывает файл:строку
# и функцию, откуда вызван, чтобы потом не искать по коду "откуда это в выводе".
# Все вызовы dbg() помечены общим тегом [DBG — их легко найти и убрать одним
# grep -rn "\[DBG" .

import inspect


# [Claude 2026-10-18] Отладочная печать с префиксом [DBG файл:строка функция] места вызова.
def dbg(*args, **kwargs):
    f = inspect.currentframe().f_back
    print(f'[DBG {f.f_code.co_filename}:{f.f_lineno} {f.f_code.co_name}]', *args, **kwargs)

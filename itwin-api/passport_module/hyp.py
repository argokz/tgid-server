import os
# PyHyphen - optional dependency: hyphenation is disabled (see hyphen() below)
# and its only call in excel.py is commented out. Without this guard a missing
# package broke the import of the whole passport module.
try:
    from hyphen import Hyphenator
    from hyphen.dictools import is_installed
except ImportError:
    Hyphenator = None
    is_installed = None
#, install
#from hyphen.dictools import list_installed

def hyphen(sentence):
    return sentence
    # Убедимся, что нужный словарь установлен
#    if not is_installed('ru_RU'):
#        install('ru_RU')  # Установка словаря для русского языка

    dir = os.path.dirname(os.path.abspath(__file__)) + '/pyhyphen'

    # РРЅРёС†РёР°Р»РёР·РёСЂСѓРµРј Hyphenator РґР»СЏ СЂСѓСЃСЃРєРѕРіРѕ СЏР·С‹РєР°
    h = Hyphenator('ru_RU', directory=dir)

    words = sentence.split()  # Разделяем предложение на слова
    hyphenated_words = []

    for word in words:
        syllables = h.syllables(word)
        if syllables:
            hyphenated_word = '\u00AD'.join(syllables)
            hyphenated_words.append(hyphenated_word)
        else:
            hyphenated_words.append(word)  

    qq = ' '.join(hyphenated_words)
#    print('------------')
#    print(sentence)
#    print(qq)

    return ' '.join(hyphenated_words)


if __name__ == "__main__":


    qq = hyphen('Привет')
    print(qq)

#    print(list_installed())

#    run()


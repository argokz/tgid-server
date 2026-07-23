#_ = gettext.gettext

import gettext

def my_gettext(s):
    subDict = {
        'positional arguments':'позиционные аргументы',
        'optional arguments':'необязательные аргументы',
        'show this help message and exit':'показать это справочное сообщение и выйти',
        'the following arguments are required: %s': 'необходимы следующие аргументы: %s',
    }

    return subDict.get(s, s)

gettext.gettext = my_gettext
_ = gettext.gettext


import argparse
import types


#------------------------------------------------------

VERSION = '1.0'

USER = 'Lifan'
PASSWORD = 'Danil228'

if True:
#if False:
    RDBMS = 'MsSql'
    SERVER = '45.132.85.23'
    PORT = 1437
    PORT = 1433
    DB = 'Test_Baza'
    DB = 'AstanaGID'
    DB = 'AlmatyGID'

    DB = 'AstanaGID_2023_07_10'
    DB = 'test'
    PASSWORD = ''
    DB = 'AstanaGID_03_06_24_work_2'

    SERVER = 'localhost'
    SERVER = '192.168.0.37'
    PORT = 1433

    USER = 'lifan'
    PASSWORD = 'Danil228'

    
    SERVER = ''
    DB = ''
    USER = ''
    PASSWORD = ''


else:
    RDBMS = 'postgreSQL'
    SERVER = 'localhost'
    PORT = 5432
    DB = 'gis'

    USER = 'gena1967'
    PASSWORD = '12345098'

FILE = 'D:/22.tgid'


#------------------------------------------------------

#def custom_error(self, message):
#     print('Your message')

#------------------------------------------------------

def init(path, descr):

#    if path == 'import_tgid':
#        descr = _('Программа для импорта tgid-файлов')
#    elif path == 'export_tgid':
#        descr = _('Программа для экспорта tgid-файлов')


    parser = argparse.ArgumentParser(
#        prog='ProgramName',
        description=descr,
        epilog=_('https://tgid.kz'),
#        add_help=False
        )

#    parser._positionals.title = "Обязательные аргументы"
#    parser._optionals.title = "Необязательные аргументы"

#    parser.error = types.MethodType(custom_error, parser)

#    if path in ('p', 'export_tgid_2', 'import_tgid'):
#        parser.add_argument('fn', type=str, default=FILE, help='tgid-файл', metavar='Файл')

#    parser.add_argument('fn', type=str, default=FILE, help='tgid-файл', metavar='Файл', nargs='+')

    parser.add_argument('-rdbms', required=False, type=str, default=RDBMS, dest='rdbms', help='СУБД')
    parser.add_argument('-server', required=False, type=str, default=SERVER, dest='server', help='Сервер')
    parser.add_argument('-database', required=False, type=str, default=DB, dest='database', help='База данных')
    parser.add_argument('-user', required=False, type=str, default=USER, dest='user', help='Пользователь')
    parser.add_argument('-password', required=False, type=str, default=PASSWORD, dest='password', help='Пароль')
    parser.add_argument('-port', required=False, type=int, default=PORT, dest='port', help='Порт')


    parser.add_argument('-encoding', required=False, type=str, dest='encoding', help='Кодировка')

    parser.add_argument('-id', required=True, type=int, dest='id', help='Номер участка')
    parser.add_argument('-type', required=True, type=str, dest='type', help='Магистраль или распредсеть?')
    parser.add_argument('-fragments', required=False, type=str, default='', dest='fragments', help='Список фрагментов')


    parser.add_argument('-out_file', required=True, type=str, default=None, dest='out_file', help=argparse.SUPPRESS)

    parser.add_argument('-V', '--version', action='version', version=f'%(prog)s {VERSION}', help=_('Показать номер версии'))
#    parser.add_argument('-h, --help', help=_('Показать этот текст и выйти'))

#    parser.add_argument('-h', '--help', action='help', default=argparse.SUPPRESS,
#                    help='Покажите это справочное сообщение и выйдите.')

    global args
    args = parser.parse_args()

    return args

#------------------------------------------------------

if __name__ == "__main__":
    args=init()
    print(args)


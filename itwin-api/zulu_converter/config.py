import gettext

def my_gettext(s):
    subDict = {
        'options':'опции',
        'positional arguments':'обязательные аргументы',
        'optional arguments':'необязательные аргументы',
        'show this help message and exit':'показать это справочное сообщение и выйти',
        'the following arguments are required: %s': 'необходимы следующие аргументы: %s',
    }

    return subDict.get(s, s)

#_ = gettext.gettext
#gettext.gettext = my_gettext


gettext_old = gettext.gettext
_ = gettext.gettext
gettext.gettext = my_gettext

import argparse

gettext.gettext = gettext_old
_ = gettext.gettext



#------------------------------------------------------

VERSION = '1.0'

USER = ''
PASSWORD = ''


if True:
    RDBMS = 'MsSql'
    SERVER = 'localhost'
    PORT = 1433
    DB = 'piter2'
else:
    RDBMS = 'postgreSQL'
    SERVER = 'localhost'
    PORT = 5432
    DB = 'gis'


#------------------------------------------------------

def init():

    parser = argparse.ArgumentParser(
#        prog='ProgramName',
        description=_('Конвертор zulu - tgid'),
        epilog=_('https://tgid.kz'),
#        add_help=False
        )

#    parser._positionals.title = "Обязательные аргументы"
#    parser._optionals.title = "Необязательные аргументы"

    parser.add_argument('-rdbms', required=False, type=str, default=RDBMS, dest='rdbms', help='СУБД')

#    parser.add_argument('-server', required=True, type=str, default=SERVER, dest='server', help='Сервер')
#    parser.add_argument('-database', required=True, type=str, default=DB, dest='database', help='База данных')
#    parser.add_argument('-user', required=True, type=str, default=USER, dest='user', help='Пользователь')
#    parser.add_argument('-password', required=True, type=str, default=PASSWORD, dest='password', help='Пароль', metavar='ПАРОЛЬ')
#    parser.add_argument('-port', required=False, type=int, default=PORT, dest='port', help='Порт', metavar='ПОРТ')
#    parser.add_argument('-fileID', required=True, type=int, default=FILE, dest='fileID', help='Номер фрагмента')

    parser.add_argument('-V', '--version', action='version', version=f'%(prog)s {VERSION}', help=_('Показать номер версии'))
#    parser.add_argument('-h', '--help', action='help', default=argparse.SUPPRESS,
#                    help='Покажите это справочное сообщение и выйдите.')

    parser.add_argument('-central_meridian', required=False, type=float, default=0, dest='central_meridian', help='')
    parser.add_argument('-false_east', required=False, type=float, default=0, dest='false_east', help='')
    parser.add_argument('-false_north', required=False, type=float, default=0, dest='false_north', help='')

    parser.add_argument('-path_db', required=False, type=str, default='', dest='path_db', help='Каталог db')
    parser.add_argument('-path', required=True, type=str, default='', dest='path', help='Файл')
    parser.add_argument('-path_out', required=True, type=str, default='', dest='path_out', help='Каталог для itwin-файлов')

    
    parser.add_argument('-name', required=True, type=str, default='', dest='name', help='Наименование тепловой сети')
#    parser.add_argument('-db', required=True, type=str, default='', dest='db', help='Бааза данных')
    parser.add_argument('-Tn', required=True, type=float, default=-26, dest='Tn', help='Температура')

    parser.add_argument('-reset', action='store_true', default=False, dest='reset', help=argparse.SUPPRESS)
    parser.add_argument('-nogidr', action='store_true', default=False, dest='nogidr', help=argparse.SUPPRESS)

    global args
    args = parser.parse_args()

    return args

#------------------------------------------------------

if __name__ == "__main__":
    args=init()
    print(args)


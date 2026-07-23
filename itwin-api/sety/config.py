import gettext

import json

#------------------------------------------------------

def get_args_json(args):
    allowed = {

        "is_ZULU_SM",
        "is_ZULU",
        "is_ZN0",
        "is_save_po",
        "is_save_po_yes",

        "iter",
        "g_equival",

        "is_kv",
        "uf_calc",

        "g_is_avar",
        "is_dross_yes",
        "avtomat_yes",
        "is_tg",
        "tp_metod",
        "n_GWS",
        "n_GWS2",
        "n_trtp",
        "no_teplovyd",
        "no_teplopoter",
        "uf_calc",
        "is_mag_fragment",


        "is_char_sety",
        "is_no_balans",
        "is_veter",
        "is_no_current",
        "is_save_uf_new",
        "is_leto",
        "is_poteri",
        "is_dop",
        "is_fakt",
        "is_no_out",


        "Month",
        "n_nagr",
        "Tn",
        "Eps",
        "veter",
    }

    args_dict = vars(args)
    args_dict = {k: v for k, v in args_dict.items() if k in allowed}

    for k, v in args_dict.items():
        if isinstance(v, bool):
            args_dict[k] = int(v)

    json_str = json.dumps(args_dict)

    return json_str

#------------------------------------------------------

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

VERSION = '1.0.2'

USER = 'lifan'
PASSWORD = 'Danil228'


#if True:
if False:
    RDBMS = 'MsSql'
    SERVER = '45.132.85.23'
    SERVER = 'localhost'
    PORT = 1437
    PORT = 1433
    DB = 'Test_Baza'
    DB = 'AstanaGID'
    DB = 'AlmatyGID'
else:
    RDBMS = 'postgreSQL'
    SERVER = 'localhost'
    PORT = 5432
    DB = 'gis'



'''
1 Магистральные сети АлЭС (ЦЭР-ВЭР-ЗЭР-СЭР)
2 ВЭР ,3 СЭР,4 ЦЭР,5 ЮЭР,41 СВЭР Жумабаева 36Б,42 СВЭР Толстого,6б
43 СВЭР ТП Алтай,72 ЗЭР,73 CЗЭР
'''
'''
2 Автономные котельные 2017-2018г.г.,
3 Пар, 4 тм-1, 5 тм-2, 6 тм-3, 7 тм-4, 8 тм-5, 9 тм-6, 10 тм-7, 11 тм-8, 12 тм-9, 13 тм-10, 14 тм-11, 15 тм-12,
16 тм-13, 17 тм-17, 18 тм-18, 19 тм-19, 20 тм-20, 21 тм-21, 22 тм-22, 23 тм-23, 24 тм-24, 25 тм-248,1, 26 тм-25,
27 тм-26, 28 тм-27, 29 тм-28, 30 тм-29, 31 тм-30, 32 тм-31, 33 тм-32, 34 тм-33, 35 тм-34, 36 тм-36, 37 тм-37,
38 тм-38, 39 тм-39, 40 тм-43, 41 тм-44, 42 тм-45, 43 тм-46, 44 тм-47, 45 тм-48, 46 тм-50, 48 тм-52, 
49 Железнодорожный, 50 Интернациональный, 51 Мичурино, 52 Пригородный (общая схема), 54 Промышленный, 55 УПТК, 
58 Магистрали 2021-2022,
801 тм-51,
806 Энергетик_только для расчета сопел по удельным,
2149 Магистрали 2022-2023 без прироста,
3150 Магистрали 2022-2023 без прироста импортирован 14-02-2023 10:18 импортирован 10-,
3151 Магистрали 2023-2024 без прироста,
3152 Фрагмент от 23-06-2023 13:53:40
'''

FILE = 3152  # Тест
FILE = 3151  # Магистрали 2023-2024 без прироста
FILE = 4  # тм-1
FILE = 1

#------------------------------------------------------

def init():

    parser = argparse.ArgumentParser(
#        prog='ProgramName',
        description=_('Программа для расчета тепловых сетей'),
        epilog=_('https://tgid.kz'),
#        add_help=False
        )

#    parser._positionals.title = "Обязательные аргументы"
#    parser._optionals.title = "Необязательные аргументы"

    parser.add_argument('-rdbms', required=False, type=str, default=RDBMS, dest='rdbms', help='СУБД')

    parser.add_argument('-server', required=True, type=str, default=SERVER, dest='server', help='Сервер')
    parser.add_argument('-database', required=True, type=str, default=DB, dest='database', help='База данных')
    parser.add_argument('-user', required=True, type=str, default=USER, dest='user', help='Пользователь')
    parser.add_argument('-password', required=False, type=str, default=PASSWORD, dest='password', help='Пароль', metavar='ПАРОЛЬ')
    parser.add_argument('-port', required=False, type=int, default=PORT, dest='port', help='Порт', metavar='ПОРТ')
    parser.add_argument('-fileID', required=True, type=int, default=FILE, dest='fileID', help='Номер фрагмента')

    parser.add_argument('-V', '--version', action='version', version=f'%(prog)s {VERSION}', help=_('Показать номер версии'))
#    parser.add_argument('-h', '--help', action='help', default=argparse.SUPPRESS,
#                    help='Покажите это справочное сообщение и выйдите.')

    parser.add_argument('-sopr', required=False, type=int, default=0, dest='sopr', help='Формула для расчета сопротивлений')
    parser.add_argument('-roP', required=False, type=float, default=0.975, dest='roP', help=argparse.SUPPRESS)
    parser.add_argument('-roO', required=False, type=float, default=0.975, dest='roO', help=argparse.SUPPRESS)
    parser.add_argument('-ro_temp', action='store_true', default=False, dest='ro_temp', help=argparse.SUPPRESS)

    parser.add_argument('-name', required=False, type=str, default='', dest='name_calc', help='Наименование')
    parser.add_argument('-out_file', required=False, type=str, default='', dest='out_file', help='Файл для обмена данными')

    parser.add_argument('-a', action='store_true', default=False, dest='g_equival', help=argparse.SUPPRESS)
    parser.add_argument('-dross', action='store_false', default=True, dest='g_is_avar', help=argparse.SUPPRESS)
    parser.add_argument('-dross_yes', action='store_true', default=False, dest='is_dross_yes', help=argparse.SUPPRESS)
    parser.add_argument('-avtomat_yes', action='store_true', default=False, dest='avtomat_yes', help=argparse.SUPPRESS)
    parser.add_argument('-tg', action='store_true', default=False, dest='is_tg', help=_('Использовать температурный график для расчета'))
    parser.add_argument('-char_sety', action='store_true', default=False, dest='is_char_sety', help=argparse.SUPPRESS)
    parser.add_argument('-no_balans', action='store_true', default=False, dest='is_no_balans', help=argparse.SUPPRESS)
    parser.add_argument('-no_teplovyd', action='store_true', default=False, dest='no_teplovyd', help=argparse.SUPPRESS)
    parser.add_argument('-no_teplopoter', action='store_true', default=False, dest='no_teplopoter', help=argparse.SUPPRESS)
    parser.add_argument('-uf_calc', action='store_true', default=False, dest='uf_calc', help=argparse.SUPPRESS)
    parser.add_argument('-veter', action='store_true', default=False, dest='is_veter', help=argparse.SUPPRESS)
    parser.add_argument('-save_po', action='store_true', default=False, dest='is_save_po', help=argparse.SUPPRESS)




    parser.add_argument('-save_po_yes', action='store_true', default=False, dest='is_save_po_yes', help=argparse.SUPPRESS)

    parser.add_argument('-zulu_zn0', action='store_true', default=False, dest='is_ZN0', help=argparse.SUPPRESS)
    parser.add_argument('-zulu_utechki', action='store_true', default=False, dest='is_ZULU', help=argparse.SUPPRESS)

    parser.add_argument('-zulu_utechki_sm', action='store_true', default=False, dest='is_ZULU_SM', help=argparse.SUPPRESS)

    parser.add_argument('-leto', action='store_true', default=False, dest='is_leto', help=argparse.SUPPRESS)
    parser.add_argument('-no_current', action='store_true', default=False, dest='is_no_current', help=argparse.SUPPRESS)
    parser.add_argument('-save_uf_new', action='store_true', default=False, dest='is_save_uf_new', help=argparse.SUPPRESS)
    parser.add_argument('-is_dop', action='store_true', default=False, dest='is_dop', help=argparse.SUPPRESS)
    parser.add_argument('-fakt', action='store_true', default=False, dest='is_fakt', help=argparse.SUPPRESS)
    parser.add_argument('-no_out', action='store_true', default=False, dest='is_no_out', help=argparse.SUPPRESS)

    parser.add_argument('-plan', action='store_true', default=False, dest='is_plan', help=argparse.SUPPRESS)

    parser.add_argument('-no_kv', action='store_true', default=False, dest='no_kv', help='Не использовать коэффициенты вариации')

    parser.add_argument('-mag_fragment', action='store_true', default=False, dest='is_mag_fragment', help=argparse.SUPPRESS)

    parser.add_argument('-ZULU', action='store_true', default=False, dest='is_ZULU', help=argparse.SUPPRESS)
    parser.add_argument('-ZN0', action='store_true', default=False, dest='is_ZN0', help=argparse.SUPPRESS)

    parser.add_argument('-Tn', required=False, type=float, default=-30, dest='Tn', help=argparse.SUPPRESS)

    parser.add_argument('-color', action='store_true', default=False, dest='g_color', help=argparse.SUPPRESS)


    parser.add_argument('-GWS', required=False, type=int, default=1, dest='GWS', help=argparse.SUPPRESS)
    parser.add_argument('-GWS2', required=False, type=int, default=1, dest='GWS2', help=argparse.SUPPRESS)
    parser.add_argument('-trtp', required=False, type=int, default=0, dest='n_trtp', help=argparse.SUPPRESS)

    parser.add_argument('-user_gid', required=False, type=str, default='', dest='user_gid', help=argparse.SUPPRESS)


    parser.add_argument('-copy_calc', action='store_true', default=False, dest='copy_calc', help=argparse.SUPPRESS)
    parser.add_argument('-database2', type=str, default=DB, dest='database2', help='База данных для синхронизации')


# Тут нужно смотреть что за параметры

    parser.add_argument('-iter', required=False, type=int, default=20, dest='iter', help=argparse.SUPPRESS)
    parser.add_argument('-tp_metod', required=False, type=int, default=1, dest='tp_metod', help=argparse.SUPPRESS)
    parser.add_argument('-type_of_net', required=False, type=int, default=1, dest='type_of_net', help=argparse.SUPPRESS)
    parser.add_argument('-time', required=False, type=str, default='', dest='time', help=argparse.SUPPRESS)



    global args
    args = parser.parse_args()

    if args.is_leto:
        args.g_equival = True
        args.g_equival = False
        


    return args

#------------------------------------------------------

if __name__ == "__main__":
    args=init()
    print(args)


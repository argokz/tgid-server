from xml.dom import minidom

def read_d_xml(fn):
#    print(fn)
    file = minidom.parse(fn)

    database = file.getElementsByTagName('database')

    name = database[0].attributes['display-name'].value

    table = file.getElementsByTagName('table')
    tn = table[0].attributes['name'].value

    conn = file.getElementsByTagName('conn')
    typ = conn[0].attributes['type'].value
    connstr = conn[0].attributes['connstr'].value

#    print(tn, typ, connstr)
    return tn, typ, connstr

if __name__ == '__main__':
    fn = 'D:/map/piter/piter.d06'
    read_d_xml(fn)
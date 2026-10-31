import struct


def read_LOGFONT(f):
    Height = read_long(f)
    Width = read_long(f)
    Escapement = read_long(f)
    Orientation = read_long(f)
    Weight = read_long(f)
    Italic = read_char(f)
    Underline = read_char(f)
    StrikeOut = read_char(f)
    CharSet = read_char(f)
    OutPrecision = read_char(f) 
    ClipPrecision = read_char(f) 
    Quality = read_char(f) 
    PitchAndFamily = read_char(f) 
    FaceName = read_string_zero(f, 52, code='cp1251')
    return (Height,Width,Escapement,Orientation,Weight,Italic,Underline,StrikeOut,CharSet,OutPrecision,ClipPrecision,Quality,PitchAndFamily,FaceName)


def tohex(val, nbits):
  return hex((val + (1 << nbits)) % (1 << nbits))

def read_string_zero(f, size, code='cp1251'):
    s = '*'
    try:
        s = f.read(size).decode(code);
        nn = s.find('\0')
        if nn != -1: s = s[:nn]
    
    except UnicodeDecodeError:
        pass

    return s


def read_char(f):
    c1 = f.read(1)[0:1]
    if not c1: return None
    x = struct.unpack('<b', c1)[0]
    return (x+256)%256


def read_short(f):
    c1 = f.read(2)[0:2]
    if not c1: return None
    x = struct.unpack('<h', c1)[0]
    return x


def read_long(f):
    c1 = f.read(4)[0:4]
    if not c1: return None

    x = struct.unpack('<l', c1)[0]
    return x

def read_float(f):
    c1 = f.read(4)[0:4]
    if not c1: return None

    x = struct.unpack('<f', c1)[0]
    return x
    


def read_xy(f):
    c1 = f.read(8)[0:8]
    if not c1: return None
    
    (x,y) = struct.unpack('<ll', c1)

    return (x,y)


def read_xyz(f, off, loc):
#  print('---------------------')
  f.seek(off)

  coor = []
  if loc == 6:
    return read_xyz6(f, off, loc)

  if loc == 5:
      for i in range(19):
          read_char(f)

  l = read_short(f)
  l2 = read_short(f)


#  if l < 100 and l >= 0:
  if loc != 2:
    c = read_long(f)

#    print(f'< l = {l} l2 = {l2} c = {c}')
    
    if (c > 1):

        cc1 = 0
        for i in range(c-1):    
            c1 = read_long(f)
            c2 = read_long(f)
#            print(f'  {i} {c1}+{c2}+1={c1+c2+1}')
#            cc1 += c1+1
#        print(f'     ')

#    else:
#        print(c)


    for i in range(l):
          x, y = read_xy(f)
#          print(i, x, y)
          coor.append((y/100.,x/100.))
  else:
      f.seek(off)
      x, y = read_xy(f)
      coor.append((y/100, x/100))

  return coor


def read_xyz6(f, off, loc):
  f.seek(off)
  x, y = read_xy(f)

  l1_1 = 0
  l1_2 = 0
  l2 = 0

#  l1_1 = read_char(f)
#  l1_2 = read_char(f)

  l1_1 = read_short(f)/10
  l2 = read_short(f)




  lf = read_LOGFONT(f)

  text = read_string_zero(f, 40, code='cp1251')

  return (y/100, -x/100, lf, text, l1_1, l1_2, l2)


def getLastID(cursor):
    '''
    Последний номер 
    '''

    cursor.execute("SELECT last_insert_rowid()")
    row_id = cursor.fetchone()[0]

    return row_id


    LAST_INSERT_ID = "SELECT SCOPE_IDENTITY() AS id"

    cursor.execute(LAST_INSERT_ID)
    result = cursor.fetchone()

    if result != None :
#        result = result['id']
        result = result[0]
    else:
        print("Ошибка не вернулся последний ID ")

    return result



#----------------------------------



def read_xyz_debug(f, off, loc):
#  print('---------------------')
  f.seek(off)

  coor = []
  if loc == 6:
    return read_xyz6(f, off, loc)

  if loc == 5:
      for i in range(19):
          read_char(f)

  l = read_short(f)
  l2 = read_short(f)

#  print(l, l2, 'loc=', loc)
#  exit(0)

#  if l < 100 and l >= 0:
  if loc != 2:
    c = read_long(f)
    if c > 1:
        print('c=', c)
        for i in range(c-1):
            c1 = read_long(f)
            c2 = read_long(f)
#            print('<<<', i+1, c1, c2)
#    else:
#        print('c=', c)

    for i in range(l):
          x, y = read_xy(f)
#          print(i+1, '=', x, y)
          coor.append((y/100.,x/100.))
  else:
      f.seek(off)
      x, y = read_xy(f)
      coor.append((y/100, x/100))

  return coor

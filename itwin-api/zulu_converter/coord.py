import math

def coord_to_s(coor):
    s_coord = ''

    if len(coor) > 2 :
         for (xx,yy) in coor[1:-1]:
             s_coord += '{} {} '.format(xx*100, yy*100)
    return s_coord

def xy_to_s(xy):
    if xy is None:
        return 'None'

    (x, y) = xy
    return ('[{} {}]'.format(-y, x))


def xy_to_shape_1(x, y):
    return '\'POINT({} {})\''.format(x, -y)
#    return 'geometry::STGeomFromText(\'POINT({} {})\', 0)'.format(x, -y)


def xy_to_shape_2(x, y, alpha):

    l = 10

    alpha = alpha * math.pi/180

    x1 = x - l*math.cos(alpha)
    y1 = y + l*math.sin(alpha)


    x1 = x
    y1 = y


    x2 = x + l*math.cos(alpha)
    y2 = y - l*math.sin(alpha)


    return '\'LINESTRING({} {}, {} {})\''.format(x1, -y1, x2, -y2)
#    return 'geometry::STGeomFromText(\'LINESTRING({} {}, {} {})\', 0)'.format(x1, -y1, x2, -y2)




def xy_to_shape(xy):
    """ 
    Читает координаты
    """

    sc2 = ''

    n = 0
    loc = 0
    length = 0
    numParts = 0 
    numPoints = 0

    try:
        n, length, loc

        sc1 = ''
        if len(xy) == 1:
            x, y = xy
#            x, y = chXY(x, y, self.typ_mas)
            return '\'POINT({} {})\''.format(x, -y)
#            return 'geometry::STGeomFromText(\'POINT({} {})\', 0)'.format(x, -y)

        elif len(xy) > 1:
            numParts, numPoints

            ss = ''

            ss1 = ''
            x0, y0 = 0, 0

            first = True

            for c in xy:
#                print(c)
                x, y = c

                if first:
                    x0, y0 = c
                    first = False


                if (x, y) != (0,0):

  #                if k == 0: x0, y0 = x,y
                  if ss1 != '' : ss1 += ','
                  ss1 += '{} {}'.format(x, -y)

            if ss1 != '' : ss1 += ','
            ss1 += '{} {}'.format(x0, -y0)

            if ss != '' : ss += ','
            ss += '('+ss1+')'

            if ss == '' : return ''

#            return 'geometry::STGeomFromText(\'POLYGON({})\', 0).MakeValid()'.format(ss)
            return '\'POLYGON({})\''.format(ss)


    except Exception as e:
        print('-----------')
        print(e)
        print('-----------')

    return ''




def find3(coor, p_x, p_y):
  Result = False

  first = True

  for it in coor:
    if first:
      (x0, y0) = it
      (x1, y1) = it
      first = False
    else:
      x2, y2 = it

      if (p_y > y1 or p_y > y2) and (p_y <= y1 or p_y <= y2):
        if p_x-x1 < (p_y-y1)*(x2-x1)/(y2-y1):
          Result = not Result

      (x1, y1) = (x2, y2)

  if (p_y > y1 or p_y > y0) and (p_y <= y1 or p_y <= y0):
    if p_x-x1 < (p_y-y1)*(x0-x1)/(y0-y1):
      Result = not Result

  return Result

if __name__ == '__main__':
    coor = [(1,1), (1,2), (2,2), (2,1)]

    f = find3(coor, 1, 1.99)
    print(f)


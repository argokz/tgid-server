from sety import read_gid
from sety.any import colors

eps = 0.00000000001

#-----------------------------------------------

#G_main = None

def setG(G):
    global G_main
    G_main = G

#------------------------------------------------------

def print_b(txt, b):
    print(txt, end=': ', flush=True)
    for n in b:
        print(f'{n:.3f}', end=' ', flush=True)
    print()

#------------------------------------------------------

def make_link(s):
    if colors.is_color():
        s = f'<a href=\'{s}\'>{s}</a>'
        return s
    return s
    


#def print_matrix(matrix, beta, x):
def print_matrix(matrix, beta):
    row, col = matrix.shape

    for j in range(col):
        print('-', end='', flush=True)
    print('', flush=True)

    for i in range(row):
        for j in range(col):
            if matrix[i, j] == eps:
                print('.', end='', flush=True)
            elif matrix[i, j] == 1:
                print('1', end='', flush=True)
            elif matrix[i, j] == -1:
                print('n', end='', flush=True)
            elif matrix[i, j] > 0:
                print('+', end='', flush=True)
            elif matrix[i, j] < 0:
                print('-', end='', flush=True)
            else:
                print(' ', end='', flush=True)

#        print('|', beta[i], x[i], flush=True)
        print('|', beta[i], flush=True)

    for j in range(col):
        print('-', end='', flush=True)
    print('+', flush=True)

#------------------------------------------------------

def print_matrix2(matrix, beta):
    row, col = matrix.shape

    for j in range(col):
        print('-------', end='', flush=True)
    print('+', flush=True)

    for i in range(row):
        for j in range(col):
            if matrix[i, j] == eps:
                print(f'   eps', end=' ', flush=True)
            else:
                print(f'{matrix[i, j]:6.2f}', end=' ', flush=True)

        print('|', beta[i], flush=True)

    for j in range(col):
        print('-------', end='', flush=True)
    print('+', flush=True)

#-----------------------------------------------

def node_fragment(G, n):
    nn = G.nodes.get(n, None)
    if nn is None: return f'???? {n}'
    
    fileID = nn.get('fileID', None)
    s = read_gid.map_fragments.get(fileID, fileID)

    return s

#-----------------------------------------------

def node_names(G, n):

    if 'G_main' in globals():
        global G_main
        G = G_main

    nn = G.nodes.get(n, None)
    
    if nn is None: 
        return '???', '???', '???', f'???? {n}', '?'

    id = nn.get('id', None)
    fileID = nn.get('fileID', None)
    kod = nn.get('externalCodeID', None)
    internalNodeID = nn.get('internalNodeID', None)
    po = nn.get('po', None)

    fragment = read_gid.map_fragments.get(fileID, fileID)

    parent = ''

    if not internalNodeID is None:
       fragment1, parent1, pkod, pname, ppo = node_names(G, (internalNodeID, 1))
       parent = pkod + ' ' + pname


    kod = str(read_gid.map_kod.get(kod, kod))
    name = str(nn.get('name', 'Без названия'))
    po = 'П' if po == 1 else 'О'

    return fragment, parent, kod, name, po

#-----------------------------------------------

def node_name(G, n, fileID_on, link=True):
    fragment, parent, kod, name, po = node_names(G, n)

#    print(fragment, parent, kod, name, po)

    s = ''

    if fileID_on and not fragment is None:
        s += fragment
        s += ' '

    if parent != '':
        s += f'[({parent}) {kod} {name} {po}]'
    else:
        s += f'[{kod} {name} {po}]'

    if link:
        s = make_link(s)

#    s += kod + ' ' + name + ' ' + po

    return s

#-----------------------------------------------

def line_name_n1_n2(G, n1, n2):
    '''
    s1 = node_name(G, n1, False)
    s2 = node_name(G, n2, False)

    return s1 + ' - ' + s2

    '''

    fragment1, parent1, kod1, name1, po1 = node_names(G, n1)
    fragment2, parent2, kod2, name2, po2 = node_names(G, n2)

    if parent1 == parent2 and parent1 != '':
       s = f'[({parent1}) {kod1} {name1} {po1} - {kod2} {name2} {po2}]'
    elif parent1 == parent2 and parent1 == '':
       s = f'[{kod1} {name1} {po1} - {kod2} {name2} {po2}]'
    else:
       s = f'[({parent1}) {kod1} {name1} {po1} - ({parent2}) {kod2} {name2} {po2}]'

    s = make_link(s)

    return s

#-----------------------------------------------

def line_name(G, nodeID1, nodeID2, externalSignLineID):
    p1 = 1 if externalSignLineID in {1, 2, 4} else 2
    p2 = 1 if externalSignLineID in {1, 2, 5} else 2 

    s1 = node_name(G, (nodeID1, p1), False)
    s2 = node_name(G, (nodeID2, p2), False)

    return make_link(s1 + ' - ' + s2)

#-----------------------------------------------

if __name__ == "__main__":
    pass

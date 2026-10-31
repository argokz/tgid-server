import math
import csv

import connect
#from z import Zulu

#---------------------------------------------------------------------------

def Appr( H, Q, k):
    n10 = 10

    Q = [q*k for q in Q]

    b1 = 0
    b2 = 0
    b3 = 0
    am11 = 10
    am12 = 0
    am13 = 0
    am21 = 0
    am22 = 0
    am23 = 0

    am31 = 0
    am32 = 0
    am33 = 0
    av11 = 0
    av12 = 0
    av13 = 0
    av21 = 0
    av22 = 0
    av23 = 0
    av31 = 0
    av32 = 0
    av33 = 0
    d = 0

    for i in range(n10):
        b1 += H[i]
        b2 += H[i]*Q[i]
        b3 += H[i]*math.pow( Q[i], 2 )
        am12 += Q[i]
        am13 += math.pow( Q[i], 2 )
        am23 += math.pow( Q[i], 3 )
        am33 += math.pow( Q[i], 4 )

    am21 = am12  
    am22 = am13
    am31 = am13  
    am32 = am23

    av11 = am22*am33-am32*am23    
    av12 =- (am21*am33-am31*am23) 
    av13 = am21*am32-am31*am22
    av21 =- (am12*am33-am32*am13) 
    av22 = am11*am33-am31*am13    
    av23 =- (am11*am32-am31*am12)
    av31 = am12*am23-am22*am13    
    av32 =- (am11*am23-am21*am13) 
    av33 = am11*am22-am21*am12

    d = am11*am22*am33+am12*am23*am31+am21*am32*am13-am13*am22*am31-am12*am21*am33-am11*am23*am32

    if d == 0:
        print("В базе данных не полная информация по характеристикам насоса")
#        error_nasos = true
        return None

    r0 = (av11*b1+av12*b2+av13*b3)/d
    r1 = (av21*b1+av22*b2+av23*b3)/d
    r2 = (av31*b1+av32*b2+av33*b3)/d
    d = 0.0

    for i in range(n10): 
        if H[i] > d:
            d = H[i]

    b3 = 200.0

    for i in range(n10):
        b1 = r0 + r1*Q[i] + r2*math.pow( Q[i], 2 )
        b2 = (b1 - H[i]) * 100 / d

        if b2 < 0.0:
            b2 =- b2
        if b3 > b2: 
            b3 = b2

    pog = b3

    return r0, r1, r2, pog


#arr1 = 260,300,320,350,380,400,420,440,450,460
#arr2 = 0,37,53,65,74,78,84,86,84,79
#arr2 = 280,300,320,350,380,400,420,440,450,460

#arr1 = h
#arr2 = q

#---------------------------------------------------------------------------

def open_nasos_std1(zulu):

    std_nas = {}
    
    cursor = zulu.cursor

    q = 'select id, tip_nas, h1, h2, h3, h4, h5, h6, h7, h8, h9, h10, q1, q2, q3, q4, q5, q6, q7, q8, q9, q10 from standardPumps'

    cursor.execute(q)

    while True:
        row = cursor.fetchone()
        if not row: break

        id = row[0]
        tip = row[1]
        H = row[2:12]
        Q = row[12:22]
    #    print(H)
    #    print(Q)

        qq = Appr(H, Q, 2)

        std_nas[tip] = (id, H,Q)

    #    print(qq)

    return std_nas

#---------------------------------------------------------------------------

def open_nasos_std():

    std_nas = {}

    with open(f'standardpumps.csv', mode='r', encoding='utf-8') as file:
        reader = csv.reader(file, delimiter=',')
        cols = next(reader)
        
        for row in reader:
            id = row[0]
            tip = row[1]

            H = [float(x) for x in row[2:12]]
            Q = [float(x) for x in row[12:22]]

            qq = Appr(H, Q, 2)

            std_nas[tip] = (id, H,Q)

    return std_nas


#---------------------------------------------------------------------------

if __name__ == '__main__':

#    zulu = Zulu()
#    baza = 'piter'
#    zulu.connect('localhost', '', '', baza)

#    H = 82,80,79,75,71,69,65,60,56,45
#    Q = 0,480,800,1120,1440,1600,2080,2500,2760,3200


    std_nas = open_nasos_std()

    print(std_nas)
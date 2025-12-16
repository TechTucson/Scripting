import sys
from collections import defaultdict, Counter
#This will take your STDIN, easiest thing is to pipe it in with a command CAT INPUT.TXT | python AOCD12025.PY
D = sys.stdin.read()
#
pos = 50
print(pos)
p1 = 0
p2 = 0
for line in D.splitlines():
#This splits the first item of each line, which is used below if L or Else. If L is negative else +.
    d = line[0]
#amt is the amount we are either moving up or down. 
    amt = int(line[1:])
    for _ in range(amt):
        if d=='L':
#If this is negative, then we'll take the current position I think multiply it by -1 add 
            print("---------START---------------")
            print("We are going")
            print(d)            
            print("Position before artihmetic")
            print(pos)
            print ("RANGE/AMT")
            print(amt)
            pos = (pos-1+100)%100
            pos2 = (pos-1+100)
            print("Position2 Withouth %100")
            print(pos2)
            print("Position2 With %100")
            print(pos)
            print("---------END---------------")
        else:
            pos = (pos+1)%100
#            print(pos)
        if pos==0:
            p2 += 1
#            print("P2")
#            print(p2)
    if pos==0:
        p1 += 1
#        print("P1")
#        print(p1)
print("P1, This is all of the times it stops at Zero")
print(p1)
print("P2, This is all of the times it stops at Zero and goes through Zero")
print(p2)
print("I ended up In POsition")
print(pos)

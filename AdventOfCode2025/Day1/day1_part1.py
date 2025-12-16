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
    print(d)
#amt is the amount we are either moving up or down. 
    amt = int(line[1:])
    for _ in range(amt):
        if d=='L':
#If this is negative, then we'll take the current position I think multiply it by -1 add 
            pos = (pos-1+100)%100
            print(pos)
        else:
            pos = (pos+1)%100
            print(pos)
        if pos==0:
            p2 += 1
            print("P2")
            print(p2)
    if pos==0:
        p1 += 1
        print("P1")
        print(p1)
print("P1")
print(p1)
print("P2")
print(p2)

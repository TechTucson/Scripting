import sys
from collections import defaultdict, Counter
D = sys.stdin.read()
pos = 50
print(pos)
p1 = 0
p2 = 0
for line in D.splitlines():
    d = line[0]
	print(d)
    amt = int(line[1:])
    for _ in range(amt):
        if d=='L':
            pos = (pos-1+100)%100
        else:
            pos = (pos+1)%100
        if pos==0:
            p2 += 1
    if pos==0:
        p1 += 1
print(p1)
print(p2)

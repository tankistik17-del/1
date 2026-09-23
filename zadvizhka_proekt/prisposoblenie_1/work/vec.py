import pymupdf, pickle, sys
d=pymupdf.open('/root/.claude/uploads/86fac385-3f3e-5e76-a6d4-4fcfb153bd6d/959ac31e-___________.pdf')
p=d[5]
print(p.rect, p.rotation)
dr=p.get_drawings()
S=200/72
items=[]
for di in dr:
    w=di.get('width') or 0
    for it in di['items']:
        k=it[0]
        if k=='l':
            a,b=it[1],it[2]; items.append(('l',[(a.x*S,a.y*S),(b.x*S,b.y*S)],w))
        elif k=='c':
            pts=[it[i] for i in range(1,5)]; items.append(('c',[(q.x*S,q.y*S) for q in pts],w))
        elif k=='re':
            r=it[1]; items.append(('re',[(r.x0*S,r.y0*S),(r.x1*S,r.y1*S)],w))
        elif k=='qu':
            q=it[1]; items.append(('qu',[(q.ul.x*S,q.ul.y*S),(q.ur.x*S,q.ur.y*S),(q.lr.x*S,q.lr.y*S),(q.ll.x*S,q.ll.y*S)],w))
print(len(items))
from collections import Counter
print(Counter(i[0] for i in items)); print(Counter(round(i[2],2) for i in items))
pickle.dump(items,open('vec6.pkl','wb'))

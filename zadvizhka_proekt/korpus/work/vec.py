import pymupdf, json, math
doc=pymupdf.open('/root/.claude/uploads/86fac385-3f3e-5e76-a6d4-4fcfb153bd6d/959ac31e-___________.pdf')
page=doc[1]
print(page.rect)
dr=page.get_drawings()
print(len(dr))
segs=[]
for d in dr:
    w=d.get('width') or 0
    for it in d['items']:
        if it[0]=='l':
            p1,p2=it[1],it[2]
            segs.append(('l',p1.x,p1.y,p2.x,p2.y,w))
        elif it[0]=='c':
            p=[it[1],it[2],it[3],it[4]]
            segs.append(('c',)+tuple(v for q in p for v in (q.x,q.y))+(w,))
        elif it[0]=='re':
            r=it[1]; segs.append(('re',r.x0,r.y0,r.x1,r.y1,w))
        elif it[0]=='qu':
            q=it[1]; segs.append(('qu',q.ul.x,q.ul.y,q.lr.x,q.lr.y,w))
json.dump(segs,open('segs2.json','w'))
from collections import Counter
print(Counter(s[0] for s in segs))
print(Counter(round(s[-1],2) for s in segs))

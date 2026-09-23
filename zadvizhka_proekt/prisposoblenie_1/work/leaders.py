import pickle, math
items=pickle.load(open('vec6.pkl','rb'))
PX=200/25.4
# markers: clusters of tiny 0.48 segments (len<0.6mm)
tiny=[p for k,p,w in items if abs(w-0.48)<0.01 and math.dist(p[0],p[1])/PX<1.0]
pts=[((p[0][0]+p[1][0])/2,(p[0][1]+p[1][1])/2) for p in tiny]
clusters=[]
for q in pts:
    for c in clusters:
        if math.dist(c[0],q)<8: c[1].append(q); break
    else: clusters.append([q,[q]])
markers=[]
for c,l in clusters:
    if len(l)>=8:
        x=sum(a for a,b in l)/len(l); y=sum(b for a,b in l)/len(l); markers.append((x,y))
print(len(markers),'markers')
# long thin lines
lines=[p for k,p,w in items if abs(w-0.48)<0.01 and math.dist(p[0],p[1])/PX>10]
words=[l.split('\t') for l in open('/tmp/claude-0/-home-user-1/86fac385-3f3e-5e76-a6d4-4fcfb153bd6d/scratchpad/dwg/hi/sheet6_words.txt').read().strip().split('\n')]
labels=[(w[0],(float(w[1])+float(w[3]))/2,float(w[4])) for w in words if w[0].isdigit() and int(w[0])<=27]
for m in markers:
    # find line with endpoint near marker
    best=None
    for p in lines:
        for i in (0,1):
            d=math.dist(p[i],m)
            if d<15 and (best is None or d<best[0]): best=(d,p,i)
    if best is None: print('marker',m,'no line'); continue
    d,p,i=best; other=p[1-i]
    # follow chain: find shelf line connected at 'other'
    lab=min(labels,key=lambda L: math.dist((L[1],L[2]),other))
    # also check connected horizontal shelf
    print(f'marker px({m[0]:.0f},{m[1]:.0f}) mainmm({(m[0]-1930)/PX:.1f},{-(m[1]-2545.3)/PX:.1f}) other end px({other[0]:.0f},{other[1]:.0f}) nearest label {lab[0]} at ({lab[1]:.0f},{lab[2]:.0f}) dist {math.dist((lab[1],lab[2]),other):.0f}')

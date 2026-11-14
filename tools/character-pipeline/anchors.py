# Is a spring chain's ANCHOR buried inside a collider?
#
# The guard never moves joint 0, which is correct -- the game's spring job takes
# joints[i] as a head and joints[i+1] as a tail and moves only the tail. But an
# anchor buried deep in a sphere leaves its CHILD sitting on that sphere's
# surface, and the child IS simulated, so it gets ejected radially from a centre
# far away. That reads as a symmetric outward flare, not as a whip.
import json, math, os, struct, sys
def mul(a,b): return [[sum(a[i][k]*b[k][j] for k in range(4)) for j in range(4)] for i in range(4)]
def trs(t,r,s):
    x,y,z,w=r
    m=[[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w),0],[2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w),0],[2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y),0],[0,0,0,1]]
    for i in range(3):
        for j in range(3): m[i][j]*=s[j]
        m[i][3]=t[i]
    return m
def xf(m,p): return tuple(m[i][0]*p[0]+m[i][1]*p[1]+m[i][2]*p[2]+m[i][3] for i in range(3))
def run(p):
    d=open(p,'rb').read(); off=12; g=None
    while off<len(d):
        ln,ty=struct.unpack_from('<II',d,off)
        if ty==0x4E4F534A: g=json.loads(d[off+8:off+8+ln].decode('utf-8'))
        off+=8+ln+((4-ln%4)%4)
    nodes=g['nodes']; W={}
    I=[[1 if i==j else 0 for j in range(4)] for i in range(4)]
    def walk(i,par):
        n=nodes[i]
        w=mul(par,trs(n.get('translation',[0,0,0]),n.get('rotation',[0,0,0,1]),n.get('scale',[1,1,1]))); W[i]=w
        for c in n.get('children',[]): walk(c,w)
    for sc in g.get('scenes',[]):
        for r in sc.get('nodes',[]): walk(r,I)
    sb=g.get('extensions',{}).get('VRMC_springBone',{}) or {}
    ys=[W[v['node']][1][3] for v in (g['extensions']['VRMC_vrm']['humanoid']['humanBones']).values()
        if isinstance(v,dict) and v.get('node') in W]
    H=max(ys) if ys else 1.0
    cols=[]
    for c in sb.get('colliders',[]):
        n=c['node']; shp=c['shape']; m=W[n]
        sc_=math.sqrt(sum(m[i][0]**2 for i in range(3))) or 1.0
        if 'sphere' in shp: cols.append(('sphere',nodes[n].get('name','?'),xf(m,shp['sphere'].get('offset',[0,0,0])),None,shp['sphere']['radius']*sc_))
        else:
            cp=shp['capsule']; cols.append(('capsule',nodes[n].get('name','?'),xf(m,cp.get('offset',[0,0,0])),xf(m,cp.get('tail',[0,0,0])),cp['radius']*sc_))
    def dist(pt,c):
        kind,_nm,a,b,r=c
        if kind=='sphere': return math.dist(pt,a)-r
        ab=[b[k]-a[k] for k in range(3)]; ap=[pt[k]-a[k] for k in range(3)]
        L2=sum(x*x for x in ab) or 1e-12
        t=max(0.0,min(1.0,sum(ap[k]*ab[k] for k in range(3))/L2))
        return math.dist(pt,[a[k]+ab[k]*t for k in range(3)])-r
    worst=[]
    for s in sb.get('springs',[]):
        js=s.get('joints',[])
        if not js: continue
        n=js[0]['node']; m=W.get(n)
        if m is None: continue
        P=(m[0][3],m[1][3],m[2][3])
        dd=min((dist(P,c) for c in cols), default=1e9)
        if dd<0: worst.append((-dd/H, s.get('name','?'), -dd))
    worst.sort(reverse=True)
    print("%-30s height %.2f  %2d chains, %d anchor(s) inside a collider%s"
          % (os.path.basename(p)[:30], H, len(sb.get('springs',[])), len(worst),
             ("  deepest %.1f%% of height (%s)" % (100*worst[0][0], worst[0][1][:22])) if worst else ""))
for p in sys.argv[1:]: run(p)

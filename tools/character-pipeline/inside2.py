# Which SIMULATED spring joints sit inside a collider?
#
# World positions are composed from full TRS matrices. Adding translations down
# the tree -- which the first version of this did -- ignores every node's
# rotation and scale, and it reported Peach with 7 violations and Batman with 4
# when both were verified clean. Controls are the only reason that was caught.
#
# joints[0] is an anchor: the game's spring job takes joints[i] as a head and
# joints[i+1] as a tail and moves only the tail, so no collider can move joint 0.
import json, math, os, struct, sys

def mul(a, b):
    return [[sum(a[i][k]*b[k][j] for k in range(4)) for j in range(4)] for i in range(4)]

def trs(t, r, s):
    x, y, z, w = r
    rot = [[1-2*(y*y+z*z), 2*(x*y-z*w),   2*(x*z+y*w),   0],
           [2*(x*y+z*w),   1-2*(x*x+z*z), 2*(y*z-x*w),   0],
           [2*(x*z-y*w),   2*(y*z+x*w),   1-2*(x*x+y*y), 0],
           [0, 0, 0, 1]]
    for i in range(3):
        for j in range(3): rot[i][j] *= s[j]
        rot[i][3] = t[i]
    return rot

def xform(m, p):
    return tuple(m[i][0]*p[0] + m[i][1]*p[1] + m[i][2]*p[2] + m[i][3] for i in range(3))

def run(p):
    d = open(p, 'rb').read(); off = 12; g = None
    while off < len(d):
        ln, ty = struct.unpack_from('<II', d, off)
        if ty == 0x4E4F534A: g = json.loads(d[off+8:off+8+ln].decode('utf-8'))
        off += 8 + ln + ((4 - ln % 4) % 4)
    nodes = g['nodes']; W = {}
    I = [[1 if i == j else 0 for j in range(4)] for i in range(4)]
    def walk(i, par):
        n = nodes[i]
        if 'matrix' in n:
            m = n['matrix']; local = [[m[c*4+r] for c in range(4)] for r in range(4)]
        else:
            local = trs(n.get('translation', [0,0,0]), n.get('rotation', [0,0,0,1]), n.get('scale', [1,1,1]))
        w = mul(par, local); W[i] = w
        for c in n.get('children', []): walk(c, w)
    for sc in g.get('scenes', []):
        for r in sc.get('nodes', []): walk(r, I)
    sb = g.get('extensions', {}).get('VRMC_springBone', {}) or {}
    cols = []
    for c in sb.get('colliders', []):
        n = c.get('node'); shp = c.get('shape', {}); m = W.get(n, I)
        sc_ = math.sqrt(sum(m[i][0]**2 for i in range(3))) or 1.0
        if 'sphere' in shp:
            cols.append(('sphere', nodes[n].get('name','?'), xform(m, shp['sphere'].get('offset',[0,0,0])), None, shp['sphere'].get('radius',0)*sc_))
        elif 'capsule' in shp:
            cp = shp['capsule']
            cols.append(('capsule', nodes[n].get('name','?'), xform(m, cp.get('offset',[0,0,0])), xform(m, cp.get('tail',[0,0,0])), cp.get('radius',0)*sc_))
    def dist(pt, c):
        kind, _nm, a, bb, r = c
        if kind == 'sphere': return math.dist(pt, a) - r
        ab = [bb[k]-a[k] for k in range(3)]; ap = [pt[k]-a[k] for k in range(3)]
        L2 = sum(x*x for x in ab) or 1e-12
        t = max(0.0, min(1.0, sum(ap[k]*ab[k] for k in range(3))/L2))
        return math.dist(pt, [a[k]+ab[k]*t for k in range(3)]) - r
    bad = []; sims = 0
    for s in sb.get('springs', []):
        for idx, j in enumerate(s.get('joints', [])):
            if idx == 0: continue
            n = j.get('node'); m = W.get(n)
            if m is None: continue
            P = (m[0][3], m[1][3], m[2][3]); sims += 1
            hr = j.get('hitRadius', 0.0)
            worst = min(((dist(P, c) - hr, c[1]) for c in cols), default=(1e9, '-'))
            if worst[0] < 0: bad.append((nodes[n].get('name','?'), idx, -worst[0], worst[1]))
    print("%-34s %2d colliders, %3d simulated joints, %d INSIDE"
          % (os.path.basename(p)[:34], len(cols), sims, len(bad)))
    for n, i, dd, c in bad: print("      %-28s joint %d  %.4f m inside %s" % (n, i, dd, c))
for p in sys.argv[1:]: run(p)

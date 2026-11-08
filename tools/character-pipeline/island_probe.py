"""Break a mesh into connected islands and describe each one, so a part with no
name of its own (a hood inside a single body mesh) can still be identified."""
import sys
from collections import deque

import bpy
from mathutils import Vector

SRC = sys.argv[sys.argv.index("--") + 1]
if SRC.lower().endswith(".blend"):
    bpy.ops.wm.open_mainfile(filepath=SRC)
else:
    bpy.ops.wm.read_homefile(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=SRC)

arm = next((o for o in bpy.data.objects if o.type == "ARMATURE"), None)
for o in bpy.data.objects:
    if o.type != "MESH":
        continue
    me = o.data
    n = len(me.vertices)
    adj = [[] for _ in range(n)]
    for e in me.edges:
        a, b = e.vertices
        adj[a].append(b)
        adj[b].append(a)
    seen = [False] * n
    islands = []
    for s in range(n):
        if seen[s]:
            continue
        q = deque([s])
        seen[s] = True
        comp = []
        while q:
            v = q.popleft()
            comp.append(v)
            for w in adj[v]:
                if not seen[w]:
                    seen[w] = True
                    q.append(w)
        islands.append(comp)
    islands.sort(key=len, reverse=True)
    g2n = {g.index: g.name for g in o.vertex_groups}
    print("MESH %s: %d verts, %d islands" % (o.name, n, len(islands)))
    for isl in islands[:14]:
        lo = Vector((1e18,) * 3)
        hi = Vector((-1e18,) * 3)
        tally = {}
        for vi in isl:
            co = o.matrix_world @ me.vertices[vi].co
            for i in range(3):
                lo[i] = min(lo[i], co[i])
                hi[i] = max(hi[i], co[i])
            for g in me.vertices[vi].groups:
                if g.weight > 0.3:
                    tally[g2n.get(g.group, "?")] = tally.get(g2n.get(g.group, "?"), 0) + 1
        top = sorted(tally.items(), key=lambda kv: -kv[1])[:3]
        print("   island %6d verts  z=%.3f..%.3f  y=%.3f..%.3f  x=%.3f..%.3f  bones=%s"
              % (len(isl), lo.z, hi.z, lo.y, hi.y, lo.x, hi.x,
                 [t[0] for t in top]))
print("DONE")

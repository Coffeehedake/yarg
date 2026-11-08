"""Rank every connected island across ALL meshes by size, the way the
builder's island:N selector does, so a part can be addressed by number."""
import sys
from collections import deque
import bpy
from mathutils import Vector
SRC = sys.argv[sys.argv.index("--")+1]
bpy.ops.wm.read_homefile(use_empty=True)
low = SRC.lower()
if low.endswith(".blend"): bpy.ops.wm.open_mainfile(filepath=SRC)
elif low.endswith((".glb",".gltf")): bpy.ops.import_scene.gltf(filepath=SRC)
elif low.endswith((".usd",".usdc",".usda",".usdz")): bpy.ops.wm.usd_import(filepath=SRC)
else: bpy.ops.import_scene.fbx(filepath=SRC)
ranked = []
for o in [x for x in bpy.data.objects if x.type == "MESH"]:
    me = o.data
    adj = [[] for _ in range(len(me.vertices))]
    for e in me.edges:
        a, b = e.vertices
        adj[a].append(b); adj[b].append(a)
    seen = [False]*len(me.vertices)
    for st in range(len(me.vertices)):
        if seen[st]: continue
        q = deque([st]); seen[st] = True; comp = []
        while q:
            v = q.popleft(); comp.append(v)
            for w in adj[v]:
                if not seen[w]:
                    seen[w] = True; q.append(w)
        ranked.append((len(comp), o, comp))
ranked.sort(key=lambda t: -t[0])
for i, (n, o, comp) in enumerate(ranked[:14]):
    ws = [o.matrix_world @ o.data.vertices[v].co for v in comp]
    print("  island %-3d verts=%-6d mesh=%-34s x %.2f..%.2f y %.2f..%.2f z %.2f..%.2f"
          % (i, n, o.name[:34],
             min(w.x for w in ws), max(w.x for w in ws),
             min(w.y for w in ws), max(w.y for w in ws),
             min(w.z for w in ws), max(w.z for w in ws)))
print("DONE")

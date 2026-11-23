"""Render a character with ONE piece painted, so a verdict can be looked at.

    blender --background --python piece_render.py -- <file.vrm> <faces> <zlo> <zhi> <out.png> [res]

A signed-volume verdict names a piece by face count and height and nothing else. That is enough
to find it and not enough to know what it IS -- Scott Hall's flagged piece turned out to be his
MOUTH, which is inside-out by design, and no number in the verdict said so. This paints the
piece and renders the character so the question "what is this" can be answered by looking.

The piece is matched the same way `facing_check.py` builds pieces: connected across edges shared
by exactly two faces, vertices welded at 0.1 mm. The match is by face count and z range, and if
more than one piece matches, ALL of them are painted and the count is reported -- a render that
silently picked one of two would be worse than no render.

Everything else is flattened to a neutral grey so the painted piece is the only thing with a
colour, and the camera is framed from the model's own bounding box rather than a fixed position,
because these characters run from 0.9 m to 2.9 m.
"""
import collections
import sys

import bpy
from mathutils import Vector

args = sys.argv[sys.argv.index("--") + 1:]
SRC, WANT_N, WANT_ZLO, WANT_ZHI, OUT = args[0], int(args[1]), float(args[2]), float(args[3]), args[4]
RES = int(args[5]) if len(args) > 5 else 640
# SOLO deletes everything that is not the flagged piece, BACK looks from behind. A piece that
# does not appear in a front render has either not been painted or is hidden, and those are
# completely different findings -- solo separates them.
SOLO = "solo" in args[6:]
BACK = "back" in args[6:]
LEFT = "left" in args[6:]
RIGHT = "right" in args[6:]
TOP = "top" in args[6:]

bpy.ops.wm.read_homefile(use_empty=True)
bpy.ops.import_scene.gltf(filepath=SRC)

grey = bpy.data.materials.new("flat_grey")
grey.use_nodes = False
grey.diffuse_color = (0.55, 0.55, 0.55, 1.0)
red = bpy.data.materials.new("flagged")
red.use_nodes = False
red.diffuse_color = (1.0, 0.05, 0.05, 1.0)

matched = 0
for o in [x for x in bpy.data.objects if x.type == "MESH"]:
    me = o.data
    mw = o.matrix_world
    polys = list(me.polygons)
    if len(polys) < 100:
        for i in range(max(1, len(me.materials))):
            pass
        me.materials.clear()
        me.materials.append(grey)
        continue

    wid, weld = {}, {}
    for p in polys:
        for vi in p.vertices:
            if vi not in weld:
                co = me.vertices[vi].co
                weld[vi] = wid.setdefault(
                    (round(co.x * 1e4), round(co.y * 1e4), round(co.z * 1e4)), len(wid))
    edges = collections.defaultdict(list)
    for p in polys:
        vs = [weld[v] for v in p.vertices]
        for i in range(len(vs)):
            a, b = vs[i], vs[(i + 1) % len(vs)]
            if a != b:
                edges[(min(a, b), max(a, b))].append(p.index)
    adj = collections.defaultdict(list)
    for fl in edges.values():
        if len(fl) == 2:
            adj[fl[0]].append(fl[1])
            adj[fl[1]].append(fl[0])
    comp, nc = {}, 0
    for p in polys:
        if p.index in comp:
            continue
        comp[p.index] = nc
        stack = [p.index]
        while stack:
            f = stack.pop()
            for g in adj[f]:
                if g not in comp:
                    comp[g] = nc
                    stack.append(g)
        nc += 1
    byc = collections.defaultdict(list)
    for p in polys:
        byc[comp[p.index]].append(p)

    me.materials.clear()
    me.materials.append(grey)
    me.materials.append(red)
    for p in polys:
        p.material_index = 0
    for cid, ps in byc.items():
        if len(ps) != WANT_N:
            continue
        zs = [(mw @ p.center).z for p in ps]
        if abs(min(zs) - WANT_ZLO) > 0.01 or abs(max(zs) - WANT_ZHI) > 0.01:
            continue
        matched += 1
        for p in ps:
            p.material_index = 1

print("PIECES MATCHED: %d (face count %d, z %.3f..%.3f)" % (matched, WANT_N, WANT_ZLO, WANT_ZHI))
if matched == 0:
    print("NOTHING PAINTED -- this render would show a character with no answer on it.")
    sys.exit(1)
if matched > 1:
    print("MORE THAN ONE PIECE MATCHED: all are painted. Read the image accordingly.")

if SOLO:
    import bmesh
    for o in [x for x in bpy.data.objects if x.type == "MESH"]:
        me = o.data
        bm = bmesh.new()
        bm.from_mesh(me)
        bm.faces.ensure_lookup_table()
        doomed = [f for f in bm.faces if f.material_index != 1]
        if len(doomed) == len(bm.faces):
            bm.free()
            bpy.data.objects.remove(o, do_unlink=True)
            continue
        bmesh.ops.delete(bm, geom=doomed, context="FACES")
        bm.to_mesh(me)
        bm.free()
    print("SOLO: everything but the flagged piece removed")

lo = Vector((1e9, 1e9, 1e9))
hi = Vector((-1e9, -1e9, -1e9))
for o in [x for x in bpy.data.objects if x.type == "MESH"]:
    for c in o.bound_box:
        w = o.matrix_world @ Vector(c)
        lo = Vector((min(lo.x, w.x), min(lo.y, w.y), min(lo.z, w.z)))
        hi = Vector((max(hi.x, w.x), max(hi.y, w.y), max(hi.z, w.z)))
mid = (lo + hi) / 2
height = max(hi.z - lo.z, 0.1)

cam_data = bpy.data.cameras.new("cam")
cam_data.type = "ORTHO"
cam_data.ortho_scale = height * 1.15
cam = bpy.data.objects.new("cam", cam_data)
bpy.context.collection.objects.link(cam)
# "Never visible" is a claim about every direction, so front and back alone cannot carry it.
if BACK:
    cam.location = (mid.x, hi.y + height * 2.0, mid.z)
    cam.rotation_euler = (1.5707963, 0, 3.14159265)
elif LEFT:
    cam.location = (lo.x - height * 2.0, mid.y, mid.z)
    cam.rotation_euler = (1.5707963, 0, -1.5707963)
elif RIGHT:
    cam.location = (hi.x + height * 2.0, mid.y, mid.z)
    cam.rotation_euler = (1.5707963, 0, 1.5707963)
elif TOP:
    cam.location = (mid.x, mid.y, hi.z + height * 2.0)
    cam.rotation_euler = (0, 0, 0)
else:
    cam.location = (mid.x, lo.y - height * 2.0, mid.z)
    cam.rotation_euler = (1.5707963, 0, 0)
bpy.context.scene.camera = cam

light_data = bpy.data.lights.new("key", type="SUN")
light_data.energy = 3.0
light = bpy.data.objects.new("key", light_data)
bpy.context.collection.objects.link(light)
light.rotation_euler = (1.0, 0.2, 0.4)

sc = bpy.context.scene
sc.render.engine = "BLENDER_WORKBENCH"
sc.display.shading.light = "STUDIO"
sc.display.shading.color_type = "MATERIAL"
sc.render.film_transparent = False
sc.world = bpy.data.worlds.new("w")
sc.world.color = (0.04, 0.04, 0.05)
sc.render.resolution_x = RES
sc.render.resolution_y = RES
sc.render.filepath = OUT
bpy.ops.render.render(write_still=True)
print("WROTE %s" % OUT)

"""Frame the camera on one MATERIAL's centroid, and report where it sits.

Framing on a BONE cannot compare a Rigify source against its build: the source
carries a metarig and a rig with different bone names, and the metarig is not
posed, so a camera framed on it looks at empty space. A material centroid is
present in both files under the same name and needs no skeleton at all.

Argv: <file> <material-substring> <out.png> [span] [azimuth-deg]
"""
import math
import os
import sys

import bpy
from mathutils import Vector

a = sys.argv[sys.argv.index("--") + 1:]
SRC, MAT, OUT = a[0], a[1], a[2]
SPAN = float(a[3]) if len(a) > 3 else 0.22
AZ = float(a[4]) if len(a) > 4 else 0.0
# Elevation matters for a hand. A T-posed character holds its palms down, so a
# camera level with the hand sees it edge-on and the fingers read as thin
# spikes whatever shape they really are -- which is a fault that is not there.
EL = float(a[5]) if len(a) > 5 else 0.0

low = SRC.lower()
if low.endswith(".vrm"):
    bpy.ops.wm.read_homefile(use_empty=True)
    if bpy.ops.import_scene.vrm(filepath=SRC) != {"FINISHED"}:
        raise SystemExit("ABORT: vrm import failed")
elif low.endswith(".blend"):
    bpy.ops.wm.open_mainfile(filepath=SRC)
    for o in [x for x in bpy.data.objects if x.type in {"CAMERA", "LIGHT"}]:
        bpy.data.objects.remove(o, do_unlink=True)
else:
    raise SystemExit("ABORT: want a .blend or a .vrm")

# FACECAM_REST=1 clears the pose before rendering.
#
# A source file is usually POSED and a build is at rest, so a side-by-side of
# the two answers "does the build match the author's pose", which is rarely the
# question. "Does the build match the model's REST shape" is a different one and
# it is the one that says whether the build is faithful -- and a glTF/VRM has no
# pose at all, so the build can only ever be compared with a source at rest.
if os.environ.get("FACECAM_REST") == "1":
    for _o in bpy.data.objects:
        if _o.type == "ARMATURE":
            for _pb in _o.pose.bones:
                _pb.matrix_basis.identity()
    bpy.context.view_layer.update()
    print("POSE CLEARED: rendering the rest shape")

# Hide the rig widgets: they are geometry and they would be in the shot.
for o in bpy.data.objects:
    if o.name.startswith("WGT-") or o.name == "smd_bone_vis":
        o.hide_render = True

bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get()


def centroid(sub):
    """Centre of a material's geometry, or of a vertex GROUP's.

    `group:NAME` frames on everything weighted to vertex groups matching NAME,
    which is how to look at a hand: a hand is not a material, and framing on the
    BONE instead fails on exactly the files worth comparing -- a Rigify source
    carries a metarig as well as the rig, the metarig is not posed, and a camera
    aimed at it looks at empty space beside the character.
    """
    if sub.lower().startswith("group:"):
        want = sub.split(":", 1)[1].lower()
        acc, n = Vector((0.0, 0.0, 0.0)), 0
        for ob in bpy.data.objects:
            if ob.type != "MESH" or ob.hide_render:
                continue
            gi = {g.index for g in ob.vertex_groups if want in g.name.lower()}
            if not gi:
                continue
            # Vertex groups live on the BASE mesh and the character may be
            # POSED, so read the indices from the base and the POSITIONS from
            # the evaluated mesh. Framing on base coordinates aims the camera
            # at where the hand would be at rest; on a posed source that is
            # empty space, and the render comes back blank -- which looks
            # exactly like "the hand is missing".
            idx = [v.index for v in ob.data.vertices
                   if any(g.group in gi and g.weight > 0.3 for g in v.groups)]
            if not idx:
                continue
            saved = [(m, m.show_viewport) for m in ob.modifiers]
            for m, _ in saved:
                if m.type != "ARMATURE":
                    m.show_viewport = False
            ev = ob.evaluated_get(bpy.context.evaluated_depsgraph_get())
            me = ev.to_mesh()
            src, mw = ((me.vertices, ev.matrix_world)
                       if len(me.vertices) == len(ob.data.vertices)
                       else (ob.data.vertices, ob.matrix_world))
            for i in idx:
                acc += mw @ src[i].co
                n += 1
            ev.to_mesh_clear()
            for m, flag in saved:
                m.show_viewport = flag
            bpy.context.view_layer.update()
        return (acc / n, n) if n else (None, 0)
    acc, n = Vector((0.0, 0.0, 0.0)), 0
    for ob in bpy.data.objects:
        if ob.type != "MESH" or ob.hide_render:
            continue
        idx = [i for i, sl in enumerate(ob.material_slots)
               if sl.material and sub.lower() in sl.material.name.lower()]
        if not idx:
            continue
        ev = ob.evaluated_get(dg)
        me = ev.to_mesh()
        vs = set()
        for p in me.polygons:
            if p.material_index in idx:
                vs.update(p.vertices)
        for i in vs:
            acc += ev.matrix_world @ me.vertices[i].co
            n += 1
        ev.to_mesh_clear()
    return (acc / n, n) if n else (None, 0)


# SPAN is a FRACTION OF THE CHARACTER'S HEIGHT, not metres.
#
# The source and its build are not the same size -- this source is 2.9 times
# the build, since the build scales to a 1.30 m target -- so a fixed world-space
# span frames the two at different magnifications and the smaller one's teeth
# look enormous. That artefact read as "the teeth were not scaled with the
# head", which is a real-sounding fault that the file does not contain. Framing
# on a fraction of each character's own height makes the two pictures
# comparable, which is the whole point of putting them side by side.
_hz = []
for _ob in bpy.data.objects:
    if _ob.type == "MESH" and not _ob.hide_render:
        _hz += [(_ob.matrix_world @ Vector(c)).z for c in _ob.bound_box]
HEIGHT = (max(_hz) - min(_hz)) if _hz else 1.0
SPAN = SPAN * HEIGHT
print("CHARACTER height %.4f, framing %.4f wide" % (HEIGHT, SPAN))

tgt, nt = centroid(MAT)
if tgt is None:
    raise SystemExit("ABORT: no material matching %r" % MAT)
print("CENTRE %-10s verts=%-6d at (%.4f,%.4f,%.4f)" % (MAT, nt, tgt.x, tgt.y, tgt.z))
for other in (() if MAT.lower().startswith("group:")
              else ("body", "eye", "hair", "teeth")):
    c, n = centroid(other)
    if c is not None and other != MAT.lower():
        d = c - tgt
        print("  vs %-6s (%6d verts) = (%+.4f,%+.4f,%+.4f) |d|=%.4f"
              % (other, n, d.x, d.y, d.z, d.length))

cam_d = bpy.data.cameras.new("cam")
cam = bpy.data.objects.new("cam", cam_d)
bpy.context.scene.collection.objects.link(cam)
cam_d.sensor_fit = "AUTO"
dist = SPAN * 2.4
ang = math.radians(AZ)
cam.location = tgt + Vector((math.sin(ang) * dist, -math.cos(ang) * dist, 0.02))
cam.rotation_mode = "XYZ"
elev = math.radians(EL)
cam.rotation_euler = (math.radians(90.0) - elev, 0.0, ang)
cam_d.lens = 50.0
cam_d.sensor_width = 36.0
# 50mm on a 36mm sensor: the frame is SPAN wide at `dist` when dist = SPAN*lens/sensor
_dir = Vector((math.sin(ang) * math.cos(elev),
               -math.cos(ang) * math.cos(elev),
               math.sin(elev)))
cam.location = tgt + _dir * (SPAN * 50.0 / 36.0)
bpy.context.scene.camera = cam

for i, (vec, e) in enumerate((((-1.0, -1.0, 0.6), 60.0), ((1.0, -0.8, 0.3), 30.0),
                              ((0.0, 1.0, 0.4), 20.0))):
    ld = bpy.data.lights.new("l%d" % i, type="AREA")
    ld.energy, ld.size = e, 0.6
    lo = bpy.data.objects.new("l%d" % i, ld)
    bpy.context.scene.collection.objects.link(lo)
    v = Vector(vec)
    lo.location = tgt + v.normalized() * 0.6
    lo.rotation_euler = (-v).to_track_quat("Z", "Y").to_euler()

sc = bpy.context.scene
sc.render.resolution_x = sc.render.resolution_y = 700
sc.render.film_transparent = False
# WORKBENCH, not EEVEE. A VRM imports with MToon materials, which EEVEE
# renders black without the addon's own shading setup -- and a black frame and
# "the teeth are not where I am looking" are the same picture. Workbench shades
# the raw geometry and cannot go black, so the shot is about POSITION, which is
# the question, and a per-material colour makes the teeth findable in it.
try:
    sc.render.engine = "BLENDER_WORKBENCH"
    sc.display.shading.light = "STUDIO"
    sc.display.shading.color_type = "MATERIAL"
except TypeError as exc:
    print("engine:", exc)
for m in bpy.data.materials:
    n = m.name.lower()
    m.diffuse_color = ((1.0, 1.0, 1.0, 1.0) if "teeth" in n
                       else (0.85, 0.2, 0.2, 1.0) if "eye" in n
                       else (0.55, 0.45, 0.40, 1.0))
sc.render.image_settings.file_format = "PNG"
sc.render.filepath = OUT
bpy.ops.render.render(write_still=True)
print("WROTE", OUT)

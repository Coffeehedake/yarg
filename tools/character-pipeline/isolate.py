# The decisive test for a material that was flipped but changed nothing on screen.
#
#   blender --background --python isolate.py -- <in.vrm> <outstem> <material>
#
# Delete every face that does not use this material, then render it alone with
# culling on and off. Two outcomes, and they mean opposite things:
#
#   THE PAIR DIFFERS   the geometry really does have back faces a viewer can
#                      see, so it is a genuine sheet and the full-figure render
#                      showed nothing only because something is in front of it
#                      or it faces away. The flip is right.
#   THE PAIR IS EQUAL  nothing is behind any face from any angle: the piece is
#                      closed. Drawing it double-sided buys nothing and costs
#                      fill rate, which is the exact objection this whole change
#                      started from -- so a flip like that is a false positive.
#
# It also prints the material's own geometry so the verdict can be read against
# something: face count, and how much of the frame it fills.
import os, sys
import bmesh, bpy, mathutils

argv = sys.argv[sys.argv.index("--") + 1:]
src, stem, want = argv[0], argv[1], argv[2].strip()
bpy.ops.wm.read_homefile(use_empty=True)
if bpy.ops.import_scene.vrm(filepath=src) != {"FINISHED"}:
    raise SystemExit("ABORT: vrm import failed")

kept = 0
for o in [o for o in bpy.data.objects if o.type == "MESH"]:
    idx = [i for i, sl in enumerate(o.material_slots) if sl.material and sl.material.name == want]
    if not idx:
        bpy.data.objects.remove(o, do_unlink=True); continue
    me = o.data
    bm = bmesh.new(); bm.from_mesh(me)
    doomed = [f for f in bm.faces if f.material_index not in idx]
    bmesh.ops.delete(bm, geom=doomed, context="FACES")
    bm.to_mesh(me); n = len(me.polygons); bm.free()
    if n == 0:
        bpy.data.objects.remove(o, do_unlink=True)
    else:
        kept += n
if kept == 0:
    raise SystemExit("ABORT: no faces use material %r" % want)
print("  ISOLATED %s: %d face(s)" % (want, kept))

# Replace the material with a plain matte grey. The question here is whether
# the GEOMETRY has back faces a viewer can see, and the source shader can defeat
# that test outright: Vegeta's Material_46 is Metallic 1.0 / Roughness 0.0, a
# perfect mirror, which renders BLACK under sun lamps with no environment to
# reflect. Six black frames read as "no verdict" when the geometry was fine all
# along. Culling is a property of the material slot, so the stand-in carries it.
neutral = bpy.data.materials.new("isolate_neutral")
neutral.use_nodes = True
bsdf = next(n for n in neutral.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
bsdf.inputs["Base Color"].default_value = (0.62, 0.62, 0.62, 1.0)
bsdf.inputs["Metallic"].default_value = 0.0
bsdf.inputs["Roughness"].default_value = 0.6
neutral.blend_method = "OPAQUE"
for o in [x for x in bpy.data.objects if x.type == "MESH"]:
    o.data.materials.clear()
    o.data.materials.append(neutral)
    for pz in o.data.polygons:
        pz.material_index = 0

objs = [o for o in bpy.data.objects if o.type == "MESH"]
lo = [1e18]*3; hi = [-1e18]*3
for o in objs:
    for v in o.data.vertices:
        p = o.matrix_world @ v.co
        for i in range(3):
            lo[i] = min(lo[i], p[i]); hi[i] = max(hi[i], p[i])
cx = (lo[0]+hi[0])/2; cy = (lo[1]+hi[1])/2; cz = (lo[2]+hi[2])/2
span = max(max(hi[i]-lo[i] for i in range(3)), 1e-4)
print("  extent %.4f x %.4f x %.4f m" % tuple(hi[i]-lo[i] for i in range(3)))

sc = bpy.context.scene
sc.render.resolution_x = 460; sc.render.resolution_y = 460
try: sc.render.engine = "BLENDER_EEVEE_NEXT"
except TypeError: pass
sc.render.film_transparent = False
cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
sc.collection.objects.link(cam); sc.camera = cam
cam.data.type = "ORTHO"; cam.data.ortho_scale = span * 1.25
# Blender's default near clip is 0.1 m. Sayuri's moles span 1.5 cm, which put
# the camera 4.6 cm away -- INSIDE that plane -- so the first run rendered an
# empty frame and the culled/unculled pair diffed to 0.00%, which read as
# "closed geometry, the flip buys nothing". A zero from a camera that saw
# nothing is indistinguishable from a zero from geometry with no back faces,
# so the clip planes are scaled to the subject and the frame is checked below.
cam.data.clip_start = max(span * 0.001, 1e-5)
cam.data.clip_end = span * 100
for pos, e in (((cx, cy - span*3, cz + span), 4.0), ((cx + span*3, cy, cz), 3.0),
               ((cx, cy + span*3, cz), 3.0), ((cx - span*3, cy, cz), 3.0)):
    lt = bpy.data.objects.new("L", bpy.data.lights.new("L", "SUN"))
    sc.collection.objects.link(lt); lt.location = pos; lt.data.energy = e
    lt.rotation_euler = (mathutils.Vector((cx, cy, cz)) - mathutils.Vector(pos)).to_track_quat('-Z','Y').to_euler()

VIEWS = {"f": ((cx, cy - span*3, cz), (1.5708, 0, 0)),
         "b": ((cx, cy + span*3, cz), (1.5708, 0, 3.14159)),
         "s": ((cx + span*3, cy, cz), (1.5708, 0, 1.5708))}
for tag, cull in (("cull", True), ("nocull", False)):
    neutral.use_backface_culling = cull
    for vn, (loc, rot) in VIEWS.items():
        cam.location = loc; cam.rotation_euler = rot
        sc.render.filepath = "%s-%s-%s.png" % (stem, vn, tag)
        bpy.ops.render.render(write_still=True)
# Prove the camera actually saw the geometry, rather than reporting a zero
# from an empty frame.
import struct, zlib
def nonblack(path):
    import subprocess
    return None
for vn in VIEWS:
    f = "%s-%s-cull.png" % (stem, vn)
    try:
        from PIL import Image
        im = Image.open(f).convert("L")
        lo, hi = im.getextrema()
        print("  FRAME %s: luminance %d..%d  %s" % (vn, lo, hi, "EMPTY -- camera saw nothing" if hi <= 8 else "ok"))
    except Exception as e:
        print("  FRAME %s: could not check (%s)" % (vn, e))
print("  wrote %s-{f,b,s}-{cull,nocull}.png" % stem)

# Render a character TWICE: as the old bundle drew it and as the new one does.
#
#   blender --background --python cullpair.py -- <in.vrm> <outstem> <mat;mat;...>
#
# A plain render of a .vrm shows NEITHER, because Blender honours the file's
# own `doubleSided` and draws no gaps at all. The bundle does not: every
# material carried `_Cull 2` before this change, and 34 of them now carry 0.
# So BEFORE forces culling on everything, AFTER turns it off for exactly the
# materials the exporter measured as sheets, and the difference between the two
# images is precisely what the change does -- nothing else moves.
#
# EEVEE_NEXT honours use_backface_culling; Cycles would ignore it and report
# no difference at all, which would read as "the change did nothing".
import os, sys
import bpy, mathutils

argv = sys.argv[sys.argv.index("--") + 1:]
src, stem = argv[0], argv[1]
named = [m.strip() for m in (argv[2].split(";") if len(argv) > 2 else []) if m.strip()]

bpy.ops.wm.read_homefile(use_empty=True)
if bpy.ops.import_scene.vrm(filepath=src) != {"FINISHED"}:
    raise SystemExit("ABORT: vrm import failed")

have = {m.name for m in bpy.data.materials}
missing = [m for m in named if m not in have]
if missing:
    # Say so rather than rendering an identical pair and calling it "no change".
    print("  WARNING unmatched material name(s): %s" % missing[:4])
    print("  materials present: %s" % sorted(have)[:12])
print("  will uncull %d of %d material(s)" % (len(set(named) & have), len(have)))

objs = [o for o in bpy.data.objects if o.type == "MESH"]
lo = [1e18] * 3; hi = [-1e18] * 3
for o in objs:
    for c in o.bound_box:
        p = o.matrix_world @ mathutils.Vector(c)
        for i in range(3):
            lo[i] = min(lo[i], p[i]); hi[i] = max(hi[i], p[i])
cx = (lo[0] + hi[0]) / 2; cz = (lo[2] + hi[2]) / 2
h = hi[2] - lo[2]
# Frame the HEAD: every material named here is a lash, brow, iris, tooth or
# hair card, and a whole-body shot at 500 px draws them a few pixels tall.
headz = lo[2] + h * 0.88
hh = h * 0.22

sc = bpy.context.scene
sc.render.resolution_x = 520; sc.render.resolution_y = 620
sc.render.film_transparent = False
try: sc.render.engine = "BLENDER_EEVEE_NEXT"
except TypeError: pass
sc.display_settings.display_device = "sRGB"

cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
sc.collection.objects.link(cam); sc.camera = cam
cam.data.type = "ORTHO"

for pos, e in (((cx, lo[1] - h, cz + h), 3.0), ((cx + h, lo[1] - h, cz), 2.0),
               ((cx - h, lo[1] - h, cz), 2.0), ((cx, hi[1] + h, cz), 1.2)):
    lt = bpy.data.objects.new("L", bpy.data.lights.new("L", "SUN"))
    sc.collection.objects.link(lt); lt.location = pos
    lt.data.energy = e
    lt.rotation_euler = (mathutils.Vector((cx, 0, cz)) - mathutils.Vector(pos)).to_track_quat('-Z', 'Y').to_euler()

# A head-framed shot cannot show a material that is not on the head. Scott
# Hall's flipped material is his VEST, Spider-Man PS's is a webshooter on his
# WRIST, and The Rock's is an unnamed body part -- all of which fell outside
# the head crop and read as "no difference". FRAME=body renders the whole
# figure instead, so a zero means the change is invisible rather than merely
# off-camera.
if os.environ.get("FRAME") == "body":
    VIEWS = {
        "bodyfront": ((cx, lo[1] - h * 3, cz), (1.5708, 0, 0), h * 1.1),
        "bodyside":  ((cx + h * 3, 0, cz), (1.5708, 0, 1.5708), h * 1.1),
    }
else:
    VIEWS = {
        "front": ((cx, lo[1] - h * 2, headz), (1.5708, 0, 0), hh * 2.2),
        "side":  ((cx + h * 2, 0, headz), (1.5708, 0, 1.5708), hh * 2.2),
    }

def shoot(tag, uncull):
    for m in bpy.data.materials:
        try: m.use_backface_culling = not (uncull and m.name in named)
        except Exception: pass
    for vn, (loc, rot, scale) in VIEWS.items():
        cam.location = loc; cam.rotation_euler = rot; cam.data.ortho_scale = scale
        sc.render.filepath = "%s-%s-%s.png" % (stem, vn, tag)
        bpy.ops.render.render(write_still=True)

shoot("before", False)   # every material culled, as the installed bundles were
shoot("after", True)     # the measured sheets drawn double-sided
print("  wrote %s-{front,side}-{before,after}.png" % stem)

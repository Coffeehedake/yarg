import sys, bpy
from mathutils import Matrix, Vector
SRC = sys.argv[sys.argv.index("--")+1]
KEEP = sys.argv[sys.argv.index("--")+2]
bpy.ops.wm.read_homefile(use_empty=True)
bpy.ops.import_scene.fbx(filepath=SRC)
arm = next(o for o in bpy.data.objects if o.type=="ARMATURE")
me  = next(o for o in bpy.data.objects if o.type=="MESH")
if me.data.shape_keys:
    me.shape_key_clear()
# refit
V=[me.matrix_world @ v.co for v in me.data.vertices]
hz=[(arm.matrix_world @ b.head_local).z for b in arm.data.bones]
mlo=min(v.z for v in V); k=(max(v.z for v in V)-mlo)/(max(hz)-min(hz))
arm.matrix_world = Matrix.Translation((0,0,mlo-min(hz)*k)) @ Matrix.Diagonal((k,k,k,1.0)) @ arm.matrix_world
bpy.context.view_layer.update()
import re
pat = re.compile(KEEP, re.I)
n=0
for b in arm.data.bones:
    b.use_deform = bool(pat.search(b.name))
    n += b.use_deform
print("deform bones kept:", n, sorted(b.name for b in arm.data.bones if b.use_deform))
me.parent=None; me.matrix_parent_inverse.identity()
bpy.ops.object.select_all(action="DESELECT")
me.select_set(True); arm.select_set(True)
bpy.context.view_layer.objects.active = arm
bpy.ops.object.parent_set(type="ARMATURE_AUTO")
nz=sum(1 for v in me.data.vertices if any(g.weight>0.01 for g in v.groups))
print("RESULT weighted %d/%d" % (nz, len(me.data.vertices)))
print("DONE")

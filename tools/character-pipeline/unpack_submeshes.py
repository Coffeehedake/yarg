"""Unpack a .yargchar into one OBJ per SUBMESH, with the texture each one uses.

Exporting a Unity mesh whole throws away the material split: Yui Suzukaze's
skin, uniform, skirt and boots came out as one object, so only one of their
textures could be applied and she rendered half undressed. The bundle knows the
answer -- a renderer lists one material per submesh, in order, and each material
names its own _MainTex.

UnityPy will not hand over a decoded vertex array on a modern bundle, but it
will write the whole mesh as OBJ. Faces come out in index-buffer order, so the
submeshes' index counts slice that face list directly, with no buffer decoding.
"""
import os
import sys

import UnityPy

SRC, OUT = sys.argv[1:3]
os.makedirs(OUT, exist_ok=True)
TEX = os.path.join(OUT, "textures")
os.makedirs(TEX, exist_ok=True)
env = UnityPy.load(SRC)


def clean(n):
    return "".join(c if c.isalnum() or c in "._- " else "_" for c in n)


texes, mats = {}, {}
for obj in env.objects:
    if obj.type.name == "Texture2D":
        d = obj.read()
        n = clean(d.m_Name) + ".png"
        try:
            d.image.save(os.path.join(TEX, n))
            texes[obj.path_id] = n
        except Exception as e:
            print("  texture %s failed: %s" % (d.m_Name, e))
for obj in env.objects:
    if obj.type.name != "Material":
        continue
    d = obj.read()
    t = None
    # m_TexEnvs is a LIST of (name, UnityTexEnv) pairs here, not a dict.
    try:
        te = d.m_SavedProperties.m_TexEnvs
        pairs = te.items() if hasattr(te, "items") else te
        for k, v in pairs:
            if k in ("_MainTex", "_BaseMap", "_BaseColorMap") and v.m_Texture.m_PathID:
                t = texes.get(v.m_Texture.m_PathID)
                break
    except Exception as e:
        print("  material %s: texture lookup failed: %s" % (d.m_Name, e))
    mats[obj.path_id] = (d.m_Name, t)

rend = {}
for obj in env.objects:
    if obj.type.name not in ("SkinnedMeshRenderer", "MeshRenderer"):
        continue
    d = obj.read()
    try:
        mid = d.m_Mesh.path_id
    except Exception:
        continue
    rend[mid] = [mats.get(m.path_id, ("?", None)) for m in d.m_Materials]

written = 0
for obj in env.objects:
    if obj.type.name != "Mesh":
        continue
    d = obj.read()
    try:
        text = d.export()
    except Exception as e:
        print("  %s: export failed: %s" % (d.m_Name, e))
        continue
    head, faces = [], []
    for line in text.splitlines():
        (faces if line.startswith("f ") else head).append(line)
    subs = getattr(d, "m_SubMeshes", None) or []
    per = rend.get(obj.path_id, [])
    stem = clean(d.m_Name)
    print("MESH %-28s faces=%-6d submeshes=%d materials=%d"
          % (d.m_Name, len(faces), len(subs), len(per)))
    at = 0
    for si, sm in enumerate(subs):
        n = sm.indexCount // 3
        chunk = faces[at:at + n]
        at += n
        if not chunk:
            continue
        mname, tname = per[si] if si < len(per) else ("?", None)
        path = os.path.join(OUT, "%s__%02d__%s.obj" % (stem, si, clean(mname or "mat")))
        with open(path, "w", encoding="utf-8") as f:
            f.write("# material %s  texture %s\n" % (mname, tname))
            f.write("\n".join(head) + "\n" + "\n".join(chunk) + "\n")
        written += 1
        print("   sub %-2d %-30s faces=%-6d tex=%s" % (si, mname, n, tname))
    if at != len(faces):
        print("   NOTE: %d faces not covered by any submesh" % (len(faces) - at))
print("DONE: %d submesh objs" % written)

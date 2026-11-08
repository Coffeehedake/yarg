"""Pull the meshes and textures back out of a .yargchar (a Unity AssetBundle).

A character that was only ever delivered as a built bundle still has its
geometry inside it. Exporting that geometry gives something Mixamo can rig,
which is the only route back for a model whose source archive is gone.
"""
import os
import sys

import UnityPy

SRC, OUT = sys.argv[1:3]
os.makedirs(OUT, exist_ok=True)
os.makedirs(os.path.join(OUT, "textures"), exist_ok=True)
env = UnityPy.load(SRC)
meshes, texes = [], []
for obj in env.objects:
    if obj.type.name == "Mesh":
        try:
            d = obj.read()
            meshes.append((d.m_Name, d))
        except Exception as e:
            print("  mesh read failed:", e)
    elif obj.type.name == "Texture2D":
        try:
            d = obj.read()
            texes.append((d.m_Name, d))
        except Exception as e:
            print("  texture read failed:", e)
for name, d in meshes:
    try:
        txt = d.export()
    except Exception as e:
        print("  %s: export failed: %s" % (name, e))
        continue
    safe = "".join(c if c.isalnum() or c in "._- " else "_" for c in name)
    path = os.path.join(OUT, safe + ".obj")
    with open(path, "w", encoding="utf-8") as f:
        f.write(txt)
    print("  mesh %-34s verts=%-7s -> %s" % (name, getattr(d, "m_VertexCount", "?"), os.path.basename(path)))
for name, d in texes:
    safe = "".join(c if c.isalnum() or c in "._- " else "_" for c in name)
    try:
        d.image.save(os.path.join(OUT, "textures", safe + ".png"))
        print("  texture %-30s %sx%s" % (name, d.m_Width, d.m_Height))
    except Exception as e:
        print("  texture %s failed: %s" % (name, e))
print("DONE: %d meshes, %d textures" % (len(meshes), len(texes)))

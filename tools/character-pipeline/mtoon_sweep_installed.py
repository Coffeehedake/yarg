# MToon materials carry distinctive PROPERTY names (_ShadeColor, _MToonVersion, _RimColor...).
# This sweep reads PROPERTY names, and that is still the right thing for it to do. But the
# reason given here for not reading the shader object was WRONG, and it is corrected below
# rather than deleted, because it sent a later reader (me) down the wrong road for an hour.
#
# WHAT THIS HEADER USED TO SAY: "The shader OBJECT cannot be read -- a bundle references
# shaders it does not contain, so m_Shader.read() throws, and a try/except around it returns
# a confident zero." The first half of that is false and the inference from it is worse.
#
# MEASURED 2026-11-18, three bundles, with a type histogram as the control: EVERY .yargchar
# CONTAINS its shaders, and every material's shader PPtr resolves inside the bundle --
# 23 of 23 in Hatsune Miku (Retry Now ver.), 14 of 14 in her Dark variant, 3 of 3 in our Aiko.
# What actually fails is reading m_Name on a bundled Shader: it comes back EMPTY. The real
# name is in m_ParsedForm.m_Name, and with that:
#
#     Hatsune Miku (Retry Now ver.)  carries  VRM10/Universal Render Pipeline/MToon10
#     Aiko (ours)                    carries  Universal Render Pipeline/Lit
#
# An empty string is not a failed read, and "the object is not here" is not the only thing a
# blank name can mean. That mistake mattered: believing the shader lived outside the bundle
# made "could we ship MToon ourselves?" look like it depended on the GAME BUILD carrying
# MToon (it does not -- the character carries it), and MToon is absent from
# m_AlwaysIncludedShaders, so the wrong answer was the discouraging one.
import os, sys, collections
import UnityPy
MARK = ("_mtoonversion", "_shadecolor", "_shadetexture", "_rimcolor", "_outlinewidth",
        "_shadingshifttexture", "_mattexture")
rows=[]; propcount=collections.Counter()
for path in sorted(sys.argv[1:]):
    try: env=UnityPy.load(path)
    except Exception: rows.append((os.path.basename(path),-1,-1)); continue
    tot=0; mt=0
    for obj in env.objects:
        if str(obj.type.name)!="Material": continue
        try: t=obj.read_typetree()
        except Exception: continue
        tot+=1
        props=set()
        sp=(t.get("m_SavedProperties") or {})
        for key in ("m_Colors","m_Floats","m_TexEnvs"):
            for e in (sp.get(key) or []):
                n=None
                if isinstance(e,dict): n=e.get("first")
                elif isinstance(e,(list,tuple)) and e: n=e[0]
                if isinstance(n,dict): n=n.get("name")
                if isinstance(n,str): props.add(n.lower())
        for p in props: propcount[p]+=1
        if any(m in props for m in MARK): mt+=1
    rows.append((os.path.splitext(os.path.basename(path))[0], tot, mt))
ok=[r for r in rows if r[1]>0]
aff=[r for r in rows if r[2]>0]
print("%d bundles, %d with readable materials, %d carrying MToon properties" % (len(rows), len(ok), len(aff)))
print("CONTROL: %d distinct material property names seen -- a zero here would mean the read failed" % len(propcount))
print("")
if aff:
    print("%-34s %6s %7s" % ("character","mats","MToon"))
    for r in sorted(aff,key=lambda r:-r[2]): print("%-34s %6d %7d" % (r[0][:34], r[1], r[2]))
else:
    print("No installed bundle carries MToon material properties.")
print("")
print("most common property names (the non-zero beside the zero):")
for n,c in propcount.most_common(6): print("   %-28s %d" % (n, c))

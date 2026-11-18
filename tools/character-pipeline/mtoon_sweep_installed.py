# MToon materials carry distinctive PROPERTY names (_ShadeColor, _MToonVersion, _RimColor...).
# The shader OBJECT cannot be read -- a bundle references shaders it does not contain, so
# m_Shader.read() throws, and a try/except around it returns a confident zero. That is how the
# first version of this sweep reported "0 of 65 carry MToon" having read no shader at all.
# Its own control caught it: zero distinct shader names is impossible if the read worked.
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

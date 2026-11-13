# Did this rebuild change ANYTHING except back-face culling?
#
# The exporter's only deliberate change is `_Cull` per material. Everything else
# a rebuild touches would be a silent regression -- the shape of the Gordon
# Freeman fault, where a rebuild from the documented recipe dropped all 32 of
# his shape keys while every count a census checks stayed identical.
#
# So compare the new bundle against the INSTALLED one on everything UnityPy can
# read, with _Cull removed from the material state:
#
#   TYPE COUNTS    how many of each object type
#   MATERIALS      names, and each one's floats/colours/keywords/queue/tags/
#                  texture slots, with _Cull taken out
#   TEXTURES       names
#   RIG            every Transform's bone name, local position length and
#                  rotation magnitude
#
# Mesh data is deliberately absent: UnityPy reports verts=0 for a .yargchar
# because the mesh is not readable that way, and that zero looks like an answer.
# The rig is what stands in for it, as identify_build.py already established.
import collections, json, math, os, sys

# Usage:
#   python verify_rebuild.py <triples.txt>
# each line "<name>|<rebuilt.yargchar>|<installed-or-backup.yargchar>";
# writes the cull-only names to clean.txt beside that file.
import UnityPy

def read(path):
    env = UnityPy.load(path)
    types = collections.Counter()
    mats, texs, pos, rot = {}, set(), {}, {}
    objs = {}
    for o in env.objects:
        types[o.type.name] += 1
        if o.type.name == "Material":
            tt = o.read_typetree()
            sp = tt.get("m_SavedProperties", {}) or {}
            cull = None; fl = []
            for a, b in sp.get("m_Floats", []):
                if a == "_Cull": cull = float(b); continue
                fl.append((a, round(float(b), 6)))
            mats[tt.get("m_Name", "?")] = (json.dumps({
                "floats": sorted(fl),
                "kw": sorted(tt.get("m_ValidKeywords") or []),
                "q": tt.get("m_CustomRenderQueue"),
                "tags": str(tt.get("stringTagMap")),
                "cols": sorted((a, str(b)) for a, b in sp.get("m_Colors", [])),
                "texn": sorted(a for a, _ in sp.get("m_TexEnvs", [])),
            }, sort_keys=True), cull)
        elif o.type.name == "Texture2D":
            try: texs.add(o.read().m_Name)
            except Exception: pass
        try: objs[o.path_id] = (o.type.name, o.read())
        except Exception: pass
    for _pid, (ty, d) in objs.items():
        if ty != "Transform": continue
        go = getattr(d, "m_GameObject", None)
        try: nm = go.read().m_Name if go is not None else None
        except Exception: nm = None
        if nm is None: continue
        lp = getattr(d, "m_LocalPosition", None); lr = getattr(d, "m_LocalRotation", None)
        if lp is not None: pos[nm] = round(math.sqrt(lp.x**2 + lp.y**2 + lp.z**2), 4)
        if lr is not None:
            w = min(1.0, max(-1.0, abs(getattr(lr, "w", 1.0))))
            rot[nm] = math.degrees(2 * math.acos(w))
    return types, mats, texs, pos, rot

rows = [l.rstrip("\r\n").split("|") for l in open(sys.argv[1], encoding="utf-8") if l.strip()]
clean, dirty, missing = [], [], []
for name, newp, oldp in rows:
    if not os.path.exists(newp): missing.append((name, "not built")); continue
    tn, mn, xn, pn, rn = read(newp)
    to, mo, xo, po, ro = read(oldp)
    issues = []
    if tn != to:
        d = {k: (to.get(k, 0), tn.get(k, 0)) for k in set(tn) | set(to) if tn.get(k, 0) != to.get(k, 0)}
        issues.append("object counts " + ", ".join("%s %d->%d" % (k, v[0], v[1]) for k, v in sorted(d.items())))
    if set(mn) != set(mo): issues.append("material names differ")
    beyond = [n for n in set(mn) & set(mo) if mn[n][0] != mo[n][0]]
    if beyond: issues.append("%d material(s) differ beyond cull: %s" % (len(beyond), ", ".join(sorted(beyond)[:4])))
    if xn != xo:
        issues.append("textures %d->%d (%s)" % (len(xo), len(xn), ", ".join(sorted(xo ^ xn))[:70]))
    if set(pn) != set(po): issues.append("rig names %d->%d" % (len(po), len(pn)))
    bad = [n for n in set(pn) & set(po) if abs(pn[n] - po[n]) > 0.0005 or abs(rn.get(n, 0) - ro.get(n, 0)) > 1.0]
    if bad: issues.append("%d bone(s) moved: %s" % (len(bad), ", ".join(sorted(bad)[:4])))
    flips = sorted(n for n in set(mn) & set(mo) if mn[n][1] != mo[n][1])
    ds_new = sum(1 for n in mn if mn[n][1] == 0.0)
    ds_old = sum(1 for n in mo if mo[n][1] == 0.0)
    if issues:
        dirty.append((name, issues, ds_old, ds_new))
        print("%-24s *** %s" % (name, "; ".join(issues)))
    else:
        clean.append((name, flips, ds_old, ds_new))
        print("%-24s cull-only   double-sided %d -> %d   %s"
              % (name, ds_old, ds_new, (", ".join(flips[:6]) + (" +%d" % (len(flips) - 6) if len(flips) > 6 else "")) if flips else "(no change)"))
print("\nCULL-ONLY %d   DIFFERS BEYOND CULL %d   NOT BUILT %d" % (len(clean), len(dirty), len(missing)))
for n, w in missing: print("   %-24s %s" % (n, w))
with open(os.path.join(os.path.dirname(sys.argv[1]), "clean.txt"), "w", encoding="utf-8") as f:
    for n, _fl, _a, _b in clean: f.write(n + "\n")

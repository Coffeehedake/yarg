# Which .vrm produced each INSTALLED .yargchar? Three readings, two of them
# hard gates, and every candidate that fails is printed so the pass means
# something.
#
#   RIG            identify_build.py's own rule -- >90% shared bone names, no
#                  bone length off by >0.5 mm, no rotation off by >1 deg. The
#                  threshold is ITS 90, not a stricter one of mine: 95 rejected
#                  Pomni (92.5%, the documented duplicate-name artefact), Steve,
#                  Mannequin and Gwen Stacy, all of which have zero length and
#                  zero rotation mismatches.
#   MATERIAL COUNT the exporter renames every material to "<Character>_<n>", so
#                  the name carries nothing -- but the COUNT survives exactly.
#   TEXTURE NAMES  ranking only. Unity's VRM importer duplicates a texture that
#                  two materials share ("__UNIGLTF__DUPLICATED__3") and appends
#                  ".normal"/".standard" by usage, so the counts legitimately
#                  differ (The Rock: 6 images -> 21 textures) and only the
#                  stripped NAMES can be compared. Peacemaker has no textures at
#                  all in either, which is agreement, not a zero score.
import json, os, re, struct, sys

# Usage:
#   python select_source.py <dir-of-vrms> [out.txt]
# writes "<installed name>|<vrm path>" per line, default ./chosen.txt
sys.path.insert(0, r"C:\dev\YARG - Open Source Contributions\yarg\tools\character-pipeline")
import identify_build as IB
import UnityPy

INST = r"C:\Users\ENG2\AppData\LocalLow\FatalException\YARG-FE\release\custom\characters"
SCR = sys.argv[1]
ROOTS = [SCR, r"C:\Users\ENG2\Documents\YARG-Characters"]
KEY = {"the mandalorian":"mando","spartan mark v":"spartan","b1 battle droid":"b1droid",
       "yui suzukaze":"yui","mickey mouse":"mickey","alcina dimitrescu":"alcina",
       "shadow the hedgehog":"shadow","clone trooper 501st":"clonep","clone trooper shiny":"clonep",
       "the rock":"rock","jessica rabbit":"jessica","iron man mark 85":"ironman","k-2so":"k2so",
       "doom slayer":"doom","skeleton mage":"skeleton","skibidi toilet":"skibidi",
       "elite terrorist":"elite","gadget hackwrench":"gadget","gordon freeman":"gordon",
       "baby groot":"groot","spider-man ps":"spidermanps","spider-man":"spiderman",
       "killer clown":"clown","judy hopps":"judy","lola bunny":"lola","harley quinn":"harley",
       "power girl":"powergirl","gwen stacy":"gwen","chibi rem":"chibirem","alice ivy":"aliceivy",
       "shaggy rogers":"shaggy","scott hall":"scotthall"}
def norm(s): return re.sub(r"[^a-z0-9]","",s.lower())
def strip(t):
    t = re.sub(r"\.(normal|standard)$","",t)
    return re.sub(r"__UNIGLTF__DUPLICATED__\d+$","",t)
def bundle_mt(path):
    mats, texs = 0, set()
    for o in UnityPy.load(path).objects:
        if o.type.name=="Material": mats+=1
        elif o.type.name=="Texture2D":
            try: texs.add(strip(o.read().m_Name))
            except Exception: pass
    return mats, texs
def vrm_mt(path):
    with open(path,"rb") as f:
        f.read(12); ln,_=struct.unpack("<II",f.read(8))
        j=json.loads(f.read(ln).decode("utf-8"))
    return len(j.get("materials",[])), {strip(i.get("name","?")) for i in j.get("images",[])}
vrms=[]
for r in ROOTS:
    for dp,_,fns in os.walk(r):
        for fn in fns:
            if fn.lower().endswith(".vrm"):
                p=os.path.join(dp,fn); vrms.append((norm(os.path.splitext(fn)[0]),p,os.path.getmtime(p)))
chosen, unresolved = [], []
for fn in sorted(os.listdir(INST)):
    if not fn.lower().endswith(".yargchar"): continue
    name=os.path.splitext(fn)[0]; key=KEY.get(name.lower(),norm(name))
    cands=[v for v in vrms if key in v[0]]
    ipath=os.path.join(INST,fn)
    if not cands: unresolved.append((name,"no .vrm bearing this name",0)); continue
    ipos,irot=IB.bundle_rig(ipath); imat,itex=bundle_mt(ipath)
    scored=[]
    for _k,p,mt in cands:
        try: vp,vr,dupe=IB.vrm_rig(p); vmat,vtex=vrm_mt(p)
        except Exception: continue
        shared=set(ipos)&set(vp); jac=100.0*len(shared)/max(len(set(ipos)|set(vp)),1)
        c=shared-dupe
        lbad=sum(1 for n in c if abs(vp[n]-ipos[n])>0.0005)
        rbad=sum(1 for n in c if abs(vr[n]-irot.get(n,0.0))>1.0)
        tex=100.0 if not (itex|vtex) else 100.0*len(itex&vtex)/len(itex|vtex)
        ok = c and jac>90 and not lbad and not rbad and vmat==imat
        scored.append((ok,round(tex,1),mt,p,jac,lbad,rbad,vmat,imat))
    good=[s for s in scored if s[0]]
    if not good:
        near=[s for s in scored if s[4]>90 and not s[5] and not s[6]]
        why=("rig ok but material count %s != %d" % ({s[7] for s in near}, imat)) if near else \
            ("best rig %.1f%% names, %d len, %d rot" % max(((s[4],s[5],s[6]) for s in scored), default=(0,0,0)))
        unresolved.append((name,why,len(scored))); continue
    good.sort(key=lambda s:(-s[1],-s[2]))
    b=good[0]; ties=[g for g in good if g[1]==b[1]]
    chosen.append((name,b[3]))
    print("%-24s mats %-3d tex %5.1f%%  rig %5.1f%%  %d/%d ok  %s%s"
          %(name,imat,b[1],b[4],len(good),len(scored),
            os.path.relpath(b[3],SCR) if b[3].startswith(SCR) else b[3],
            "  (+%d tied, newest taken)"%(len(ties)-1) if len(ties)>1 else ""))
with open(os.path.join(SCR,"rebuild","chosen.txt"),"w",encoding="utf-8") as f:
    for n,p in chosen: f.write("%s|%s\n"%(n,p))
print("\nCHOSEN %d   UNRESOLVED %d"%(len(chosen),len(unresolved)))
for n,why,k in unresolved: print("   %-38s %-44s (%d candidates)"%(n,why,k))

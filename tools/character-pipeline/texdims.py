# Four Iron Man .vrm files all pass the rig and material-count gates and all
# score 100% on texture NAMES, so neither can separate them -- but -full,
# -tex1k and -trim differ by what is IN the textures. Dimensions can tell them
# apart, and the bundle carries them.
import io, json, os, struct, sys
import UnityPy
def bundle(p):
    out={}
    for o in UnityPy.load(p).objects:
        if o.type.name!="Texture2D": continue
        try:
            d=o.read(); out[d.m_Name]=(d.m_Width,d.m_Height)
        except Exception: pass
    return out
def vrm(p):
    d=open(p,"rb").read(); off=12; g=None; bin_=None
    while off<len(d):
        ln,ty=struct.unpack_from("<II",d,off)
        if ty==0x4E4F534A: g=json.loads(d[off+8:off+8+ln].decode("utf-8"))
        elif ty==0x004E4942: bin_=d[off+8:off+8+ln]
        off+=8+ln+((4-ln%4)%4)
    out={}
    for im in g.get("images",[]):
        bv=g["bufferViews"][im["bufferView"]]
        blob=bin_[bv.get("byteOffset",0):bv.get("byteOffset",0)+bv["byteLength"]]
        w=h=None
        if blob[:8]==b"\x89PNG\r\n\x1a\n":
            w,h=struct.unpack(">II",blob[16:24])
        elif blob[:2]==b"\xff\xd8":
            i=2
            while i<len(blob)-9:
                if blob[i]!=0xFF: i+=1; continue
                m=blob[i+1]
                if m in (0xC0,0xC1,0xC2):
                    h,w=struct.unpack(">HH",blob[i+5:i+9]); break
                i+=2+struct.unpack(">H",blob[i+2:i+4])[0]
        out[im.get("name","?")]=(w,h)
    return out
inst=bundle(sys.argv[1])
print("installed: %d textures  %s" % (len(inst), sorted(set(inst.values()))))
for n,(w,h) in sorted(inst.items()): print("   %-46s %sx%s" % (n[:46],w,h))
for p in sys.argv[2:]:
    v=vrm(p)
    shared=set(n for n in v if n in inst)
    same=sum(1 for n in shared if v[n]==inst[n])
    print("\n%-34s images=%-3d dims agree %d/%d   %s"
          % (os.path.basename(p),len(v),same,len(shared),sorted(set(v.values()))))

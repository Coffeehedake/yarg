# -*- coding: utf-8 -*-
"""Give a character's spring chains a CENTER transform, which our conversions never set.

    python set_spring_center.py <file.yargchar> [--center NAME] [--chain NAME ...] [--write]

WHY. Four attempts at Batman's cape failed on collision geometry, and the fifth picture showed
why: the cape was not hanging and clipping, it was FLYING -- spread wide and level, like a flag.
No collider shape can fix a cape that is being thrown outwards.

THE SPRING DEFINITION HAS A `Center` FIELD AND OURS IS NULL. In
`UpdateFastSpringBoneJob.Execute`:

```csharp
var currentTail = centerTransform.HasValue
    ? MathHelper.MultiplyPoint3x4(centerTransform.Value.localToWorldMatrix, CurrentTail[logicIndex])
    : CurrentTail[logicIndex];
```

With a Center, a joint's tail is stored in THAT transform's space and converted to world each
frame, so the character's own movement carries the cloth with it. Without one the tails are
world positions, so every time the character moves the cloth is left behind and then yanked --
which on a rotating character-select turntable is a permanent outward fling. Batman's cape also
has `m_gravityPower = 0.0` (as does every chain on the roster), so nothing pulls it back down
afterwards.

THE CONTROL IS THE ROSTER ITSELF, and it is unanimous. Of 432 springs across 30 installed
characters, 237 have a Center -- and they are the ones that arrived as real VRMs:

    Hatsune Miku (Retry Now ver.)   54 springs, 54 with a Center -> `Root`
    Inforder Trogen                 78 springs, 78 with a Center -> `Root`
    Kaiser Aufhanger                42 springs, 42 with a Center -> `Root`

Every one points at a transform named `Root`, 174 for 174. Every character our own pipeline
built -- Batman, Jessica, Miku, Peach, Link, Prix, Tenna, Yoda and the rest -- has it null.
Batman HAS a `Root` transform at y 0.000, exactly where Miku's is. The value was always
available and we never wrote it.

So this is not a new idea, it is the convention the working characters already follow. Nothing
is invented here: `--center` defaults to `Root` and the tool refuses if no such transform
exists rather than picking something that looks close.

It backs the file up, keeps the bundle a `UnityFS` bundle, and verifies on the bytes in hand.
"""
import hashlib
import io as _io
import os
import shutil
import sys

import cloth_collide_installed as cci
import UnityPy

BACKUP_DIR = r"C:\dev\YARG - Open Source Contributions\character-backups"


def die(msg):
    print("REFUSED: %s" % msg)
    sys.exit(1)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    path = sys.argv[1]
    center_name = (sys.argv[sys.argv.index("--center") + 1]
                   if "--center" in sys.argv else "Root")
    chains = [sys.argv[i + 1] for i, a in enumerate(sys.argv) if a == "--chain"]
    write = "--write" in sys.argv

    human, tf, go_tf, springs, joints, colliders, groups, world = cci.read(path)
    hits = [pid for pid, rec in tf.items() if (rec.get("name") or "") == center_name]
    if not hits:
        die("no transform called %r in this file. The working characters on this roster all "
            "use `Root`; nothing is guessed here, so pass --center with a name that exists."
            % center_name)
    if len(hits) > 1:
        die("%d transforms are called %r, so the target is ambiguous" % (len(hits), center_name))
    center_tpid = hits[0]
    cwp, _q, _s = world(center_tpid)
    print("center %r is transform %s at y %.3f" % (center_name, center_tpid, cwp[1]))

    by_name = {s[0]: s for s in springs}
    if chains:
        missing = [c for c in chains if c not in by_name]
        if missing:
            die("no chain(s) %s; this file has %s" % (missing, sorted(by_name)))
    targets = chains or sorted(by_name)
    print("%d spring chain(s) in this file, %d named" % (len(springs), len(targets)))

    env = UnityPy.load(path)
    inst_obj = inst_tree = None
    for o in env.objects:
        if o.type.name != "MonoBehaviour":
            continue
        try:
            cn = o.read().m_Script.read().m_ClassName
        except Exception:                                            # noqa: BLE001
            continue
        if cn == "Vrm10Instance":
            inst_obj, inst_tree = o, o.read_typetree()
    if inst_obj is None:
        die("this file has no Vrm10Instance, so it carries no spring definitions")

    already, todo = [], []
    for s in inst_tree["SpringBone"]["Springs"]:
        nm = s.get("Name")
        if nm not in targets:
            continue
        cur = (s.get("Center") or {}).get("m_PathID", 0)
        (already if cur else todo).append(nm)
    print("%d already have a Center, %d to set" % (len(already), len(todo)))
    if already:
        print("  already set: %s" % ", ".join(already[:6]))
    if not todo:
        print("nothing to do.")
        return 0

    if not write:
        print()
        print("would set Center -> %r on: %s" % (center_name, ", ".join(todo)))
        print("DRY RUN -- nothing written. Re-run with --write to apply.")
        return 0

    if not os.path.isdir(BACKUP_DIR):
        die("the backup directory %s does not exist" % BACKUP_DIR)
    src = open(path, "rb").read()
    src_md5 = hashlib.md5(src).hexdigest()
    found = None
    for f in os.listdir(BACKUP_DIR):
        fp = os.path.join(BACKUP_DIR, f)
        if os.path.isfile(fp) and os.path.getsize(fp) == len(src):
            if hashlib.md5(open(fp, "rb").read()).hexdigest() == src_md5:
                found = f
                break
    if found:
        print("backup present: %s" % found)
    else:
        dest = os.path.join(BACKUP_DIR, "%s.%s.bak" % (os.path.basename(path), src_md5[:8]))
        shutil.copy2(path, dest)
        print("backed up to %s" % dest)

    touched = 0
    for s in inst_tree["SpringBone"]["Springs"]:
        if s.get("Name") in todo:
            s["Center"] = {"m_FileID": 0, "m_PathID": center_tpid}
            touched += 1
    if touched != len(todo):
        die("expected to touch %d chain(s), touched %d" % (len(todo), touched))
    inst_obj.save_typetree(inst_tree)

    # SAVE THE BUNDLE, NOT THE ASSETS FILE -- af.save() produces a bare SerializedFile that
    # UnityPy reads happily and AssetBundle.LoadFromFile cannot open. It cost two characters.
    data = env.file.save(packer="original")
    if not data.startswith(b"UnityFS"):
        die("the written bytes do not start with 'UnityFS', so this is no longer an "
            "AssetBundle and the game cannot load it. Nothing written.")
    if not (0.5 * len(src) <= len(data) <= 2.0 * len(src)):
        die("the written bytes are %d against %d in -- a factor of %.1f. Setting one field "
            "cannot do that. Nothing written."
            % (len(data), len(src), float(len(data)) / max(1, len(src))))
    print("container: UnityFS kept, %d bytes against %d in (%+d)"
          % (len(data), len(src), len(data) - len(src)))

    # verify on the BYTES, and in the direction that can fail: read every spring back
    env2 = UnityPy.load(_io.BytesIO(data))
    problems = []
    seen = 0
    for o in env2.objects:
        if o.type.name != "MonoBehaviour":
            continue
        try:
            cn = o.read().m_Script.read().m_ClassName
        except Exception:                                            # noqa: BLE001
            continue
        if cn != "Vrm10Instance":
            continue
        for s in ((o.read_typetree().get("SpringBone") or {}).get("Springs") or []):
            nm = s.get("Name")
            got = (s.get("Center") or {}).get("m_PathID", 0)
            if nm in todo:
                seen += 1
                if got != center_tpid:
                    problems.append("%s: Center is %s, expected %s" % (nm, got, center_tpid))
            elif nm not in already and got != 0:
                problems.append("%s was not named and gained a Center of %s" % (nm, got))
    if seen != len(todo):
        problems.append("read back %d of the %d chains that were set" % (seen, len(todo)))
    if problems:
        die("the patch verified wrong and was NOT written:\n  - " + "\n  - ".join(problems))

    open(path, "wb").write(data)
    print("WRITTEN. Center -> %r on %d chain(s): %s"
          % (center_name, touched, ", ".join(todo)))
    return 0


if __name__ == "__main__":
    sys.exit(main())

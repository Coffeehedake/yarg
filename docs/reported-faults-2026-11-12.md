# Thirteen faults reported from the game, 2026-11-12

Jay looked at the installed characters and listed thirteen visible faults. **Every one of them
passed every check this project has**: collider groups, unguarded chains, heights, alpha modes,
visemes, eye shells, the census, `identify_build`. That is the first thing to say about this
list, and the most important.

The faults are mostly RIGGING and WEIGHTING — where geometry sits relative to the bones that move
it — and nothing here measures that. The tools built so far read material state, bone *counts*,
spring-bone structure and file-level census. A dress that is not weighted to the body, a hair
mesh parked beside the head, a leg bone mirrored wrongly: all of those files are perfectly
well-formed.

| # | character | reported fault | first guess at the class | touched 2026-11-12? |
|---|---|---|---|---|
| 1 | **Alice Ivy** | hair is detached, floating off a bald scalp | hair rig / spring chain — **and I added her hair chains today** | **YES** |
| 2 | **Heels** | eyes have no irises | the `Std_Cornea_L/R` pair left opaque on purpose — may be the wrong call | no |
| 3 | **Thanos** | armour discoloured, whole body too dark | texture or colour space | no |
| 4 | **Spartan Mark V** | right leg detached and asymmetrical | rig / weighting | no |
| 5 | **The Rock** | arms are squiggly | weighting or a bad fit — he had a shoulder fit applied | no |
| 6 | **Gadget Hackwrench** | mesh not rigged properly at all | weighting — **and I re-collidered her today** | **YES** |
| 7 | **Miku** | hair missing pieces | geometry dropped, or a cutout eating it | no |
| 8 | **Peach** | dress clips through legs, moves as one solid piece | dress not weighted / rigid-bound | no |
| 9 | **Killer Clown** | hair clips through her hat | layering / weighting | no |
| 10 | **Shadow the Hedgehog** | eyes closed | the documented wrong eye-atlas frame — **and I rebuilt him today** | **YES** |
| 11 | **Pomni** | hair clips through face and head | layering / weighting | no |
| 12 | **Jessica Rabbit** | dress not rigged to her body | weighting — **and I rebuilt her today** | **YES** |
| 13 | **Alcina Dimitrescu** | textures discoloured and mapped wrongly | the known noise-texture archive problem, plus UVs — **and I gave her hair chains today** | **YES** |

**Five of the thirteen are characters changed today**, which has to be the first thing
investigated rather than the last: a fault I introduced this morning and a fault that has been
there for weeks look identical in a screenshot.

The backups of all five are hash-verified in `C:\dev\_tmp\yarg-char-backup\2026-11-12-prehair`,
so reverting any of them is a file copy.


## First pass, 2026-11-12 evening

### Four reverted, because I could not tell cause from coincidence

Five of the thirteen are on characters I changed today. Four of those four
complaints touch exactly what I changed, so they went back to their backups —
my versions kept in `C:\dev\_tmp\yarg-char-backup6-11-12-mine-reverted`,
so nothing is lost and a fix-forward is a file copy:

| character | what I had changed | why reverted |
|---|---|---|
| **Alice Ivy** | added 4 hair spring chains | the complaint IS the hair. Her eye fix is in the backup, so that is kept |
| **Alcina** | added 4 hair spring chains | built by the same tool the same way; dropped pre-emptively |
| **Jessica Rabbit** | added hair + skirt chains | the complaint IS the dress |
| **Gadget Hackwrench** | round-tripped her mesh for colliders | the complaint IS the mesh |

**Shadow is not reverted.** His complaint — eyes closed — is documented and
pre-existing, and colliders and a finger map cannot cause it.

Worth recording: Gadget's hair chains turned out to be **original**, not mine.
Her `HairSpring_0_0`..`3_3` are in her backup too.

### Heels: the fault was mine, and the render found it in one shot

Her eyes close up, before and after today's alpha rebuild:

* **Before** — the character's LEFT eye has a clean blue iris and pupil; the
  right is a blank white film.
* **After** — **both** are blank white. The good eye was changed to match the
  bad one.

The materials say why. Before: `Std_Eye_Occlusion_L` was `MASK` and `_R` was
`BLEND`; after, the alpha work made **both** `BLEND`. So the documented
asymmetry was real and had been read backwards — **`_R` being a blend was the
fault, not `_L` being a cutout.**

And neither mode is the real answer. Hiding the `CC_Base_EyeOcclusion` mesh
entirely gives **both** eyes perfect irises, which is better than either. The
occlusion mesh is a subtle eye-socket shadow; losing it costs far less than
losing both irises. Rebuilt with `^CC_Base_EyeOcclusion$` excluded:

* rig **MATCH** against her installed bundle, 127 bones, 0 length and 0
  rotation mismatches
* the exclusion costs exactly that mesh — 288 triangles, 1 mesh, 2 materials,
  2 images, 1 node, and nothing else
* colliders 10, all grouped; height 1.7000 m

**Sayuri was checked the same way and is clean** — her `Eye_Shadows` was
blended by the same change and her irises are unaffected, before and after.
"Not reported" is not "checked".

### Thanos is NOT the metalness trap, which is what it looked like

Every one of his five materials carries `_Metallic 1.0`, which is the exact
signature of the documented fault that shipped Link's face gold — a leftover
metalness with no map turning a surface into a mirror. **It is not that.** All
five also carry a `_MetallicGlossMap`, so the 1.0 is a multiplier on a real
map, which is the correct setup. A sweep of all 65 for metallic > 0.2 with no
metal map returns **zero characters**. His darkness is something else and he
needs a render; he has no `.vrm`, so that means extracting his archive.


## One root cause under several of them: the bundle draws single-sided geometry

Every `.vrm` this pipeline writes marks its materials **`doubleSided: true`**. Measured on the
twelve reported characters that still have one: Alice Ivy 22 of 22, Heels 21 of 21, Thanos 5 of
5, The Rock 21 of 21, Gadget 6 of 6, Miku 1 of 1, Peach 16 of 16, Killer Clown 4 of 4, Shadow 5
of 5, Pomni 13 of 13, Jessica Rabbit 10 of 10, Alcina 13 of 13. **Not one false.**

None of it survives the export, and `YargCharExporter.cs` says why in its own comment:

> `// A fresh URP/Lit culls back faces. The source materials are Standard, which has no cull`
> `// property to read, so the glTF doubleSided flag is [lost].`
> `// YARG_CULL_OFF_MATERIALS draws just those materials double-sided; everything else stays culled.`

The escape hatch has to be named per material, per build, and almost nobody ever did. Across the
65 installed characters when this was measured: **398 materials at `_Cull 2` and exactly ONE at
0.**

Thin, single-layer geometry — hair ribbons, skirt panels, capes, lashes — has no back face to
fall back on. From the wrong side it is simply not drawn. That reads as **"missing pieces"**, or
as hair **"clipping through"** a hat when what is actually happening is the near surface being
culled away so you see what is behind it.

### And it is exactly why no render here ever caught it

Blender honours `doubleSided`, so a render of the `.vrm` shows a character that is whole. **The
bundle the game loads is a different object from the one I have been looking at all day.**

Miku is the clean proof, because her whole character is one material. Rendered from her `.vrm`
her twintails are continuous ribbons. Rendered with backface culling forced on — which is what
the bundle does — they break into pieces, exactly as reported.

`cullrender.py` in the scratchpad is that comparison, and `patch_cull_off.py` is the repair:
`_Cull 2 → 0` in the installed bundle, the same in-place UnityPy route as the alpha patchers,
with a read-back that proves only the named materials changed.

**`--all` is defensible here and not a shortcut.** The source declares every one of these
materials double-sided, so turning culling off restores what the model asked for rather than
inventing something. On a closed solid mesh it changes nothing visible, because the back faces
are hidden by the front ones anyway.

### Done, and what is left

**Twelve characters patched and installed** — all of the reported ones that have a `.vrm` to
confirm the source intent, plus Miku. Backups in
`C:\dev\_tmp\yarg-char-backup6-11-13-precull`.

**262 materials across 48 other characters are still single-sided.** They carry exactly the same
latent fault and nobody has complained about them yet. Flipping them is one command and fully
reversible, but it touches most of the roster, so it is left as a decision rather than taken.

**The real fix is in the exporter**, which should read `doubleSided` out of the `.vrm` and set
`_Cull` from it instead of needing a hand-written list. Every character built from now on will
otherwise arrive single-sided again.

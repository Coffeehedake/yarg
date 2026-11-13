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


## RETRACTED: "one root cause under several of them: single-sided geometry"

**This section claimed back-face culling explained several of the thirteen faults, and it is
wrong. The twelve characters it was applied to are reverted, hash-verified, and the roster is
back to 398 materials culled and the one deliberate exception (Alastor's `Eyes.001`). Jay called
it before any of the checks below were run.**

The claim was: every `.vrm` the pipeline writes declares `doubleSided: true` — twelve characters,
not one false — while the installed bundles are almost all culled, so the exporter must be losing
a deliberate signal, and restoring it is the fix. `patch_cull_off.py` was given an `--all` flag
and run across twelve characters. Four measurements take it apart.

**1. The pipeline does not lose the flag.** Batman's source GLB omits `doubleSided`, which glTF
defaults to false, and `Batman.vrm` omits it too — 2 materials, 0 true. `BatmanNoT.vrm` and
`bat-regress.vrm` likewise. So "every `.vrm` this pipeline writes is double-sided" was simply
untrue. It was true of the twelve characters that were looked at, and generalised from there.
The twelve were not a sample; they were the ones with a reported fault.

**2. The sources are not declaring anything.** Across the third-party sources on hand:
**60 materials true, 0 false, 5 absent.** A Blender glTF export writes
`doubleSided = not use_backface_culling`, and Blender defaults that off, so anything exported by
someone who never touched the setting arrives `true`. An unbroken run of one value is the
signature of a default upstream, not of authorship — and a control is the only thing that tells
those apart, which is what Batman is.

**3. The geometry says culling cannot cause the reported faults.** `facing_check.py` has been in
this repo the whole time and answers this directly. Alice Ivy, whose hair is reported detached:
all four hair materials **100% outward, 0% winding conflicts, 0 inside-out pieces**. Culling
cannot detach correctly-wound outward geometry. Killer Clown: 0 inside-out. Miku: 78% outward,
0% winding conflicts, 0 inside-out, and her twintails measure as **closed solids**, not sheets.

**4. The one positive result does not reproduce.** The Miku comparison that was offered as proof
— continuous from the `.vrm`, broken into pieces with culling forced on — was re-run with the
same script on the same file. The two renders differ by **0.3% of pixels**, scattered edge
slivers, with the twintails continuous in both. Whatever was shown before, this does not show it.

### What is actually true, and the rule that follows

Culling does break thin single-layer geometry, because a sheet has no back face. But a material
that renders wrong under culling has two possible causes and they want **opposite** fixes:

| What it is | How to tell | Fix |
|---|---|---|
| An open sheet — hair card, cape, skirt panel, lash | boundary edges > 0; no signed volume | `YARG_CULL_OFF_MATERIALS`, named |
| A closed piece wound inside-out | boundary edges 0; **negative** signed volume | `VRM_ORIENT_CONSISTENT` at build time |

Double-siding the second kind **hides** the bug instead of fixing it, and that has already
happened once here: Alastor's eyes were inverted, 0% facing the front, and the note on him records
them as *"hidden by the double-sided material"*. So run `facing_check.py` first and name what it
finds.

`YargCharExporter.cs` had already written the conclusion, in the comment right above the escape
hatch, before any of this started:

> `// Double-sided everywhere tints the lighting, so name them, do not blanket.`

The `--all` flag is gone from `patch_cull_off.py`; it refuses to run without `--materials`, and
`--on` is the inverse so a named flip is reversible without a backup. **No exporter change is
warranted** — reading `doubleSided` out of the `.vrm` would propagate an upstream default to the
whole roster, which is the thing that was nearly shipped.

### The fix: the exporter measures it

`YargCharExporter.cs` now decides sidedness **per material, from the geometry**, and reads the
file's `doubleSided` flag not at all. Two scale-invariant numbers per connected piece of surface
— openness (`boundary/sqrt(area)`) and solidity (`|V|/area^1.5`) — and a piece is a sheet when it
is both open and encloses nothing. A material is drawn double-sided when at least 20% of its area
sits in sheet pieces. `YARG_CULL_OFF_MATERIALS` and the new `YARG_CULL_ON_MATERIALS` override it
either way. The full reasoning, the thresholds and the sensitivity data are in
`tools/character-pipeline/README.md` under "Single- and double-sided, measured rather than
flagged".

It names **20 of 265 materials (7.5%)** across the 37 characters that have a `.vrm` — eyelashes,
brows, hair cards, eye planes — and reproduces Alastor's hand-made answer (`Eyes.001`
double-sided, `Head.001` not) **with no environment variable set**.

Verified rather than assumed:

- The same rule is implemented twice — `sidedness.py` in Blender and the exporter in C# — and the
  two were compared on four characters: **68 materials, all 68 agreeing.** That check earned its
  place immediately. The first C# version built connected pieces per SUBMESH rather than per
  mesh, so a material border counted as a boundary and Ariel's ears, irises and lips — patches of
  a closed head — came out double-sided. Seven disagreements, now none.
- The exported bundles carry it: Alastor 1 of 4 materials double-sided, Alice Ivy 3 of 22,
  Ariel 5 of 26, Peach 6 of 16. Exactly the predicted counts.

**This changes what is BUILT from now on. The 65 installed characters were not rebuilt**, so they
still carry whatever `_Cull` their original export gave them — 398 culled and Alastor's one
exception. Rebuilding the roster is a separate decision and would pull in every other pipeline
change since each character was last built.

### What this costs, which is why it is not free to "just turn it on"

Double-sided doubles the fragments rasterised for that material, lights back faces with normals
pointing the wrong way, and makes a blended material show its own interior. YARG draws four
characters and a crowd at a frame rate a rhythm game has to hold. A blanket flip also removes the
signal that finds real winding bugs: every inside-out piece on the roster would start looking
correct, and the next one would be undiagnosable.

### Where this leaves the thirteen

Unchanged. The culling story explained none of them, so Alice Ivy's hair, Miku's hair, Killer
Clown's and Pomni's hair, Peach's dress, Jessica's dress, The Rock's arms, the Spartan's leg,
Gadget's rigging, Shadow's eyes, Thanos's darkness and Alcina's textures are all still open, and
most of them look like weighting or spring-bone faults rather than material state. One genuine
lead did come out of the geometry pass: **Pomni has one inside-out piece**, 168 faces of
`PomniFace` at z 1.16–1.20, which is head height and is where her hair is reported to clip
through. That is a `VRM_ORIENT_CONSISTENT` candidate, and it is the kind of thing a blanket
double-side would have buried.

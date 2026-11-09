# YARG character build tooling

Tooling for turning a third-party model into a `.yargchar`.

The **tooling** is published here; the **characters it produces are not**. They are personal-use
conversions of third-party models, so no `.yargchar`, `.vrm`, texture or source archive belongs
in this repository — only the scripts that make them.

The reasoning behind almost every line is written up in `docs/character-models.md`. Read that
first; this file is only how to *run* it.

## The two steps

**1. Model → VRM** (Blender 4.5, with the VRM add-on installed in the user profile — do **not**
pass `--factory-startup`, the add-on will not load):

```
blender --background --python build_vrm.py -- <model> <texdir> <height_m> <rig> <name> <out.vrm> <texmax> [exclude] [spring] [hairrig]
```

- `model` — `.fbx`, `.blend`, `.glb`/`.gltf`, or `.usd*`
- `height_m` — final height in metres; the builder scales to it and asserts on the result
- `rig` — one of the families below
- `texmax` — texture edge limit; **1024** is the house setting (2048 roughly triples bundle size)
- `exclude` — regex over MESH names to drop (scenery, props, spare variants). Python `re`, so a
  negative lookahead works: `'^(?!Body$).*'` keeps only `Body`
- `spring` — regex for spring-bone chains; **omit it** and hair/skirt/tail/cape chains are found
  automatically, which is almost always what you want
- `hairrig` — regex over MESH *or* MATERIAL names to build hair chains for a model that has none;
  `island:N` addresses the Nth-largest connected island for a part with no name of its own

Environment switches: `VRM_TEX="Mat=file.png[:kind]"` forces a texture onto a named material when
the archive's names carry no information (Alcina's fourteen `Material.NNN`); `VRM_RIGID="island:N=Bone"`
binds a connected mesh island wholly to one bone, for a part an auto-rigger has no business bending
(Sonic's back quills); `VRM_DROP_ISLAND="<mesh-pattern>=<bone>[+<bone>]"` drops the islands of a
mesh that one bone CARRIES, which is how a weapon comes out of a hand when the same mesh also
holds gear that belongs on the character (the mesh pattern is not optional — a hand is itself
weighted to the hand bone); `VRM_BREASTRIG=1` builds chest bones for a rig that has none and weights the bust onto
them (`check` measures and prints without changing anything, which is how it was written);
`VRM_BREAST_SPRING=0` stops chest bones being sprung and `VRM_BREAST_PARAMS="stiffness,drag,gravity"`
changes the feel; `VRM_SAVE_BLEND=<path>` saves the pre-export scene (the single most useful
debugging aid — renders of it tell you whether a fault is yours or the exporter's),
`VRM_NO_TPOSE=1`, `VRM_DROP_SOLIDIFY=1` (inverted-hull outlines), `HAIR_ANCHOR` / `HAIR_SEGS` /
`HAIR_STRANDS` for the hair rigger.

**2. VRM → .yargchar** (Unity 6000.3.5f2). Copy `YargCharExporter.cs` from this folder into
`<fork>/Assets/__TempExport/Editor/`, run it, then delete that folder. It lives here, not under
`Assets/`, so that Unity does not compile it into every build — and an `Assets/__TempExport/`
left lying around is one `git add -A` away from entering the fork:

```
Unity.exe -batchmode -nographics -quit -projectPath <fork> -logFile <log> \
  -executeMethod YargCharExporter.ExportAll \
  -vrmList "<a.vrm>|<Name A>;<b.vrm>|<Name B>" -outDir <dir>
```

Two ways to lose an hour here, both measured:

- `Unity.exe` **detaches on Windows** — the launcher returns 0 immediately. Wait on the editor
  process, not the launcher. And `Get-Process Unity` matches Unity **Hub**'s background helper
  (`unity.exe serve`), not the editor, so a "wait until Unity exits" loop on that name never
  finishes. Use `Start-Process -PassThru` and poll `$p.HasExited`.
- PowerShell's `Start-Process -ArgumentList` with an **array** joins on spaces **without quoting**,
  so a project path containing a space arrives as several arguments and Unity exits 1 with
  `Couldn't set project path`. Build one argument string with embedded quotes.

Install to `%USERPROFILE%\AppData\LocalLow\FatalException\YARG-FE\release\custom\characters\`.
**YARG reads these at startup**, so it must be restarted to see a change.

## What the first in-game playtest found

Everything below was invisible to the build logs, the renders and every count the pipeline
produces. Eleven characters, found in about twenty minutes of actually looking at them in YARG.
**The lesson is the list itself**: a pipeline that verifies its own output against its own
measurements will keep producing confident, broken characters.

Two of these are regressions from the chest-rig work; the other nine were already installed and
had simply never been looked at.

| character | what is wrong | what it is |
|---|---|---|
| The Rock | limbs stretched into metre-long spikes | his humanoid skeleton is sized for a ~3.5 m figure against a 1.96 m mesh: head bone at 2.77 m, hand bone 1.94 m out. Spider-Man and Chibi Rem measure 1.00 and 1.02 on the same head-to-mesh ratio; he is 1.41 |
| Power Girl, Judy Hopps | legs cross over each other when posed | **left and right are swapped.** Measured across all 66: 258 of 264 limb pairs agree on which side is which, and these two supply all six disagreements |
| Prix, Pomni | eyes render as solid white; hair reads as a cap | every material in every character exports `alphaMode: OPAQUE` — see below |
| Ariel, Heels | lower hair hangs in space while the body moves | the hair rigger leaves part of the hair behind. Chains are correctly parented and every vertex is weighted, so it is neither of the obvious two |
| Mando | cape folded in on itself, static | the documented cloak case: he needs the hair rigger with `HAIR_BONE=Spine1` and was never built with it |
| Jessica Rabbit | dress static while the body moves; sequin texture on her skin | cloth unrigged, and her `rskin` material took the dress's sequin map |
| Alcina | chest drifts like a balloon | **chest spring parameters do not scale.** 0.85 stiffness and 0.60 drag were set looking at Prix at 1.70 m; Alcina is 2.9 m and VRM spring stiffness is scale-dependent |
| Yui | looks out of proportion | not yet measured |
| Kasane Teto | does not animate at all, stands in her T-pose | **her bundle has no AnimatorController and no AnimationClip.** 1 of 66; every other character has both. She has an Animator and an Avatar, 20 skinned renderers and a complete humanoid map, so nothing else distinguishes her |
| Lola Bunny | head floats detached above the neck | a part following a bone that does not follow the body — the same shape as Judy's belt and the static hair |
| Judy Hopps | belt detached, arms and legs crossed | the crossing is the mirrored rig above; the belt is the detached-part case |
| Gordon Freeman | every texture misplaced except his head | one material taking another's map, at the scale of a whole character |
| Miku | dress does not move with her | loose cloth with no chains |
| Alastor | no eyes; something wrong with the hair | eye meshes, so either the orphan-bone case or the cutout |
| Elite Terrorist | right hand's fingers crunched | one hand posed, the other not -- the asymmetry the finger-relax check looks for |
| Batman | every texture misplaced | the same whole-character mapping failure as Gordon Freeman |
| Gadget Hackwrench | eyeballs and teeth do not move; some hair static | measured: her eyes are 100% weighted to a bone nothing drives |
| Joker | a pistol orbiting him; parts of the suit unrigged | a prop that was never excluded, plus the detached-part case |
| Peach | eyes missing; dress springs so reactive her legs clip through it | the eye atlas again, and the other end of the cloth problem: hers IS rigged and is too lively. Cloth needs its own parameters, gentler than hair and separate from chest |
| Link | eye textures misplaced; still holding the master sword and shield | needs an exclude and a texture pin |
| Shadow | eyes use the blink/closed frame of the atlas; fingers do not move | an eye atlas with the wrong frame pinned, and finger bones that are mapped but not weighted |
| Skibidi Toilet | is a man, with no toilet | the exclude that drops the toilet shell (it swamped the model) drops the character's defining feature and leaves the body that was inside it |

### One cause under six of the reports: a bone nothing drives

VRM moves the 52 humanoid bones and the spring chains, and nothing else. Every other bone
follows only if it is a **descendant** of one of those. A deform bone parented outside that
hierarchy therefore never moves at all, and the vertices on it hold their bind position while
the character walks away from them.

Nothing counts it. The mesh is present, the skin is present, every vertex carries full weight,
the humanoid map is complete, the renders look right because at rest a dead bone and a live one
are identical. Measured:

| character | what hangs off a bone nothing drives |
|---|---|
| Lola Bunny | **31% of her body mesh** — `fml_un_C_TopHead`, `fml_un_C_BotHead`, eyelid, tooth and brow joints. Her head floats above her neck |
| Gadget Hackwrench | `Eye_L` and `Eye_L.001` at **100%**, plus 3.8% of her body (the teeth) |
| Judy Hopps | her belt |
| Joker | panels of his suit |
| Ariel, Heels | the lower hair that stays in space |

Two sub-cases, and they need different answers. A real bone outside the hierarchy is
**re-parented to the nearest humanoid bone**, keeping its world position. Weight on the glTF
exporter's `neutral_bone` means something else entirely: that bone is invented at export time
for geometry that had **no vertex groups at all**, so Gadget's eyes were never bound to
anything — the unrigged-mesh rescue stands down as soon as any mesh in the file is bound, and
hers were.

`VRM_KEEP_ORPHANS=1` leaves them where they are.

**The check is three lines and should have existed from the first character**: take every bone
that deforms geometry, walk up its parents, and assert it reaches a humanoid or spring bone.

### Two of these were predicted before they were reported

Both came out of sweeps run over the installed set rather than out of looking at characters,
which is the only reason they are not still unknown:

- **Judy Hopps' crossed limbs.** The left/right sweep named her and Power Girl, and nobody had
  reported her yet. She was reported an hour later, in exactly those terms.
- **Kasane Teto's missing animator.** She was reported as "still doesn't animate"; a sweep for
  bundles with no AnimatorController returned her and nobody else.

The pattern worth keeping: **when a defect is reported, sweep the whole set for the same
signature before fixing the one character.** Every sweep run that way today found between one
and two more characters with the same fault, and each took one command.

### alphaMode: a setting on a disabled extension

`mtoon1.enabled` defaults to **false**, and the exporter only writes that extension's
`alpha_mode` when it is on. The builder had been setting `alpha_mode` and nothing else, so the
setting was inert and **every material in every character exported `OPAQUE`**. Hair cards,
eyelashes, eye whites and lace all depend on that cutout; without it they render as solid
slabs.

It is turned on now, for the materials that need a cutout only — enabling MToon across a whole
character swaps its shading model, which is a far larger change than this defect warrants.

Heels is where it surfaced: her installed build carries ten textures that UniGLTF merged from a
diffuse and an opacity map, which it only does for a material that is not opaque, and her
rebuild had none. **That comparison is also the cheapest detector for it** — a character whose
installed version has merged textures and whose rebuild has none has lost its transparency.

## Runlist

What is left, in the order it is worth doing. Kept here rather than in a conversation,
because every entry below has already been rediscovered at least once.

1. **Tune the chest rig** once it has been seen in game. The feel is
   `VRM_BREAST_PARAMS="stiffness,drag,gravity"` (default `0.85,0.6,0.0` — stiffer and draggier
   than the hair chains, which swing and keep swinging). Detection has three knobs:
   `VRM_BREASTRIG_MIN` (0.06, how far the apex must stand proud of the surface),
   `VRM_BREASTRIG_MIN_OUT` (0.12, how far from the midline a peak must be before it counts as
   a bust rather than a sternum), `VRM_BREASTRIG_R` (0.25 of the shoulder span, the radius of
   the weighted patch), and the two mesh-detail floors `VRM_BREASTRIG_MIN_VERTS` (120 front
   vertices a side to measure from) and `VRM_BREASTRIG_MIN_PATCH` (40 in the patch itself).
   A character under those is refused as a **limitation of the model, not a failure** — the
   build finishes normally and the log says which floor it was under. Run `VRM_BREASTRIG=check` to see what a change does to a character
   without rebuilding it.
2. **Sweep the installed set for the floating-prop height bug** — the Peacemaker failure mode,
   where the tallest mesh in the file is not part of the character and the whole figure scales
   down to fit it. Nothing looks wrong until the character stands next to another one.
3. ~~Re-check Lola Bunny against the split-channel metallicRoughness fix.~~ **Settled: it
   never applied to her.** Her `.glb` carries its own packed ORM, so every map on her one
   material arrives wired from the import (`base=packed:C038_Base_C, metal=packed:C038_Base_ORM,
   rough=packed:C038_Base_ORM, normal=packed`) and the picker is never asked. The
   `C038_Base_ORM_1@channels=R/G/B.png` files beside her model are extracted channels nothing
   reads.
4. **Finish the chest-rig rollout.** Nineteen rebuilt, ten installed — Alcina, Prix, Chibi
   Rem, Sayuri, Alice Ivy, Tenna, Gadget, Lola, Ariel and Killer Clown. The installed set now
   has **13** characters with sprung chest bones where it had 3, 7 carrying bones nothing
   moves, and 46 with none.

   All seven of those are accounted for, and only two are open work: **Batman** and **Peach**
   carry chest bones that deform nothing and are skipped deliberately; **Heels** and **Jessica
   Rabbit** have working chest chains in a build held back for the reasons below; **Harq
   Alkahana**, **Kaiser Aufhänger** and **Kasane Teto** have no source located.

   Two of those 9 will never move and should stop being counted as work: **Batman** and
   **Peach** carry chest bones that deform no geometry — Batman's from the shared MultiVersus
   female base, Peach's from whatever her rip inherited — and the deform test skips both
   deliberately. That leaves **seven** genuinely pending, split by whether a source exists:

   - ~~Source on hand, arguments not written down.~~ **All four recovered and in the table
     below** — read out of their own installed bundles, where the bone names give the rig
     family and the mesh bounds give the height, checked first against four characters whose
     heights are documented. Ariel and Killer Clown rebuild clean and are installed. Two are
     not:
     - **Heels loses her transparency.** Her installed character carries ten textures that
       UniGLTF merged from a diffuse and an opacity map, which it only does for a material that
       is not opaque. The rebuild assigns nine alpha maps and still exports **every one of its
       21 materials as `OPAQUE`**, so her hair, eyelashes and tear line would render as solid
       cards. Her base textures arrive PACKED in the `.blend`, so the alpha the installed
       version uses never came from the picker — and two of the alpha maps the picker does
       choose are wrong anyway (`front_hair_Transparency` gets its own *bump* map, and
       `Std_Eye_L` gets the eyelash opacity). Transparency, not jiggle, is what to fix first.
     - **Jessica Rabbit rebuilds 6% heavier** than the installed character, so an exclude was
       used and never recorded.
   - **No source located**: Harq Alkahana, Kaiser Aufhänger, Kasane Teto.
   What stopped the rest, in the order it is worth picking up:

   - **Compare the bundle SIZE as well.** Geometry and texture names can both match while the
     rebuild is twice the size: Prix came out at 39 MB against the 18 MB already installed,
     because she was rebuilt at `texmax` 2048 rather than the house 1024. Nothing in the log
     says so — the counts are identical and only the bytes differ. Rebuilt at 1024 she is
     8.2 MB of VRM again.
   - **A rebuild that loses a texture is worse than no jiggle**, so compare before installing
     — but compare the right thing. A Unity texture count and a glTF image count are not the
     same number: the UniVRM import copies an image per material slot
     (`__UniGLTF__Duplicated__2`) and renames by slot (`<image>Normal`, `<image>Standard`).
     Compare names, with all of that stripped, and repeatedly — Unity appends `Normal` to a
     file already called `Bikini_Normal`.
   - **Alcina is installed**; the rebuild that looked like it had lost two maps had lost
     nothing, and the comparison script was at fault. **Gwen Stacy is not**: her textures are
     fixed, but she is under the mesh-detail floor, so a rebuild gains her nothing.
   - **Gwen Stacy's loss was real and is fixed.** Her files are `GwenStacyDifuselMap`,
     `NormalMap`, `MetallnessMap`; the map-token regex spelled out a trailing `map` only after
     `normal`, so her base stem kept `difuselmap` whole, the texture SET derived from it
     contained one file — itself — and the rule "take only from this set" quietly meant "take
     nothing". A set of one carries no information and now falls back to the ordinary pick.
   - **Judy Hopps** rebuilt 132% heavier than the installed one, so the installed character did
     not come from `judy-hopps-not-game-ready.zip`. Find out which source it did come from
     before replacing her.
   - ~~Lola Bunny and Peach produced no model file.~~ **Both archives hold another archive**:
     Lola's `source/` is a `.rar` containing her `.glb`, Peach's is a `model.zip` containing
     four spellings of her (`.dae`, `.fbx`, `.mtl`, `.obj`). Lola rebuilds identically and
     gains a chest chain — her `fml_un_C_breast` does deform geometry, unlike Batman's copy of
     the same bone from the same shared rig — so she is installed. Peach rebuilds identically
     and gains nothing: 94 front vertices a side, under the detail floor, so she is left as
     she is.
   - **Jinx and Miku** rebuild cleanly and gain nothing: both decline the chest rig (Jinx's two
     sides disagree, Miku has 93 torso vertices). Leave them installed as they are.
   - These carry chest bones but have no recoverable arguments or no locatable source —
     Harq Alkahana, Kaiser Aufhänger, Kasane Teto, Adachi Rei, Ariel, Heels, Killer Clown.
     Jessica Rabbit's row in the table below records her `VRM_TEX` value truncated.
5. **Anakin** is still unconverted; Mixamo's auto-rigger has refused him five times.
6. **`T-800_Run.usdz`** is unconverted — 33 bones on a numbered rig rooted at `n14`, and a
   2.0 x 2.0 x 3.7 m bounding box that says it is posed mid-run, so it needs `VRM_STANDUP=1`
   like Anakin. The older `terminator-t-800-endo-skeleton-damaged` archive is abandoned.
7. **`junio-sonic-legacy`** looks unconverted: the installed Sonic carries Mixamo's
   `HeadTop_End`, so it is the HD one.
8. **Power Girl** is deliberately not rebuilt until her issues are confirmed in game.

**Record the arguments when you build.** Entry 4 exists only because they were not: every
build prints `ARGV:` and `ENV:` before it can fail, and that line belongs in the table below
rather than in a log that goes away with the session.

## Rig families

`mixamo` (auto-detects a prefix) · `cc_base` · `rigify_def` · `rigify_plain` · `ue4` · `rp`
(Renderpeople) · `daz` · `bip` · `valvebiped` · `maxbiped` (auto-detects `Bip001`/`Bip01`) ·
`advskel` · `arp` · `multiversus` · `mayajnt` · `xeno` · `pomni` · `steve` · `b1` · `sonic` ·
`sonicforces` · `linkoot` · `mariojnt` · `smash` · `anakin` · `simple`

Mapped names are resolved case-insensitively and tolerate a trailing `_NN` index, so a Source rig
shipped as `ValveBiped.Bip01_L_Forearm_41` still maps (it mapped 0 of 52 without that).

The last six are hand-written for one model each, mapped by reading the hierarchy because their
bones are called `Bone.0NN`. `classify.py <model> <tag>` guesses the family for a new download.

## Checking the result

Never trust the build log alone — several characters have shipped broken while every count was
right.

- `render_vrm.py <vrm|blend> <out.png>` — `RENDER_LIGHT=0.2` matters: the default lighting
  over-exposes bright textures and has twice made a correct model look wrong
- `render_closeup.py <model> <bone> <out.png> [span]` — `RENDER_EL` / `RENDER_AZ` orbit. Look at a
  hand from **above**, not edge-on
- `pose_test.py <blend> <bone-pattern> <out.png> [deg]` — bends spring chains. A rest render proves
  nothing about weights; at rest every weighting is the identity
- `weight_check.py <vrm> <pattern>` — do those bones actually drive vertices?
- `skin_check.py <vrm>` — any mesh node without a skin can never animate
- `armpose2.py <model>` — arm straightness in REST **and** POSE for any rig, finding the arm
  chain by name. This is what showed Mixamo's rest pose to be the arms-down original
- `fingerpose.py <model>` — per-chain finger curl, REST vs POSE, both hands. The left/right
  comparison is the measurement: one relaxed hand is the control that says whether the other is
  really clenched
- `meshbb.py <blend>` — per-mesh vertex count, world size and materials; how to tell which
  numbered mesh is the eyes before pinning a texture to its material
- `alpha_check.py` / `mat_check.py` / `spring_scan.py` / `uv_test.py` / `tex_stats.py` — material,
  alpha, spring and texture inspection straight out of the exported file

## Chest bones, and the three groups of characters

Unity's humanoid rig has no slot for a chest bone, so VRM leaves one rigid unless a spring chain
names it. Across the 66 characters installed here that splits three ways, and each wants something
different:

| | what it needs |
|---|---|
| **3** arrive with their own chains (the VRoid models) | nothing |
| **16** carry chest bones nothing moves | the spring section: name them, give a lone bone a tip |
| **47** have no chest bones at all | `VRM_BREASTRIG=1`, which builds them |

A lone bone cannot spring: a VRM chain moves every joint but the last, so a one-bone chain moves
nothing. Alcina, Jessica Rabbit and Killer Clown have exactly one a side, and they get a
weightless tip — the same trick the hair rigger uses.

**A bone in the rig is not a bone in the model.** Batman carries `fml_un_C_breast` because
MultiVersus skins its whole cast onto one shared female base; on him it deforms nothing. The test
is whether the bone drives vertices, so his is skipped. Springing it would have been invisible,
which is worse than wrong — it would have sat in the file looking like it worked.

`VRM_BREASTRIG` refuses to run on a rig that already has weighted chest bones. Rigging Alcina
anyway gave her four chains, hers and a generated pair 20 cm inboard, weighted to the same
geometry and pulling against each other.

## An authored T-pose beats one you compute

A Mixamo auto-rig download carries its T-pose in an **animation**, not in the rest skeleton. The
rest skeleton is whatever the uploader supplied, and that is usually arms-down: Sonic HD measures
57.9 degrees off X at rest, Yoda 93.4. The builder used to drop every attached action on sight,
which threw away the only T-pose in the file and then rebuilt one out of its own rotations.

Those rotations get the arm **on to** the X axis and still look wrong, because an arm has more
than a direction. The synthesized rotation carries no information about the limb's axial ROLL or
the orientation of the hand, so the arm arrives twisted along its own length. That is what Jay
saw and called "squiggly arms", and what webbed Yoda's sleeves to his robe.

So measure both poses and keep the better one:

- the animated pose's arms must be within 10 degrees of X, and the rest pose's must not be
- the animated pose's **legs** must be within 20 degrees of straight down

The leg test is what tells a T-pose from a frame of motion. Do **not** test the root bone's
translation instead -- Mixamo's own T-pose clip moves the hips 11 units of a 57-unit rig, so a
drift test rejects the very pose the check exists to keep. The arms-only test is not enough on its
own either: a jump or ragdoll frame can have one arm out.

The test is deliberately narrow because most clips in these archives -- jumps, ragdolls, walk
cycles, `IDLE003`, `Confession` -- **must** still be dropped. Of 80-odd builds only the ones whose
clip is genuinely a T-pose pass it.

## Measure limb direction in WORLD space

An FBX import leaves the armature object rotated 90 degrees about X, so the source's Y-up becomes
Blender's Z-up. Bone heads are in the armature's **own** space, where that rotation has not been
applied: measured there Sonic stands 57 units tall along **+Y**, and a perfectly straight pair of
legs reads 87.9 degrees away from -Z. A T-pose then looks like a frame of motion and the check
above rejects it.

X survives the rotation unchanged, which is exactly why an arms-only test passes anyway and hides
the bug. Multiply by `armature.matrix_world` before taking any angle against an axis.

## The texture pool must contain only images

`os.listdir(TEXDIR)` returns the extracted archive, and an extracted archive also holds the
`.fbx`, the `.blend`, `readme.txt` and a `.mtl`. Left in the pool those are candidates like any
other -- and since the last-resort rule is "largest file first", the **model** is the strongest
candidate in the folder.

Yoda's eye material was assigned `yoda_rigged.fbx`; his eyes rendered magenta, which reads as a
missing texture rather than as a texture that is a 3D model. Blender says only `failed to load
image buffer`, one line among a hundred packing warnings, so nothing in the build output looks
wrong. Filter the listing to image extensions and print what was ignored.

It only bites a material that has **no other candidate**. Sonic and Peach load the same way --
`sonic_rigged.fbx`, and `model.obj`/`.fbx`/`.dae`/`.mtl` -- and both came out correct, because
every one of their materials had a packed image to win with. Yoda's eyes had none. So the
failed-load line is worth grepping for across old logs, but finding it does not by itself mean
that build is wrong: check whether any material actually took it.

## A build log must say what it was built FROM

Every env switch changes the result, so a log that records only side effects cannot be reproduced
from. Reconstructing Yoda's arguments meant inferring them from the island numbers and vertex
counts his log happened to mention. `build_vrm.py` now prints `ARGV:` and `ENV:` before anything
can fail; re-running a build and matching those side effects is how you confirm you got it right.

## A hand posed around a prop that is no longer there

Alcina Dimitrescu holds a cigarette holder. The holder is excluded from the build (`^NurbsPath`)
because it skewers her hand, but her left fingers stayed clamped around the hole where it was, and
Jay reported them as mangled.

The model supplies its own control, and that is what makes this safe to automate. Her **right**
hand's pose is identical to rest on all five finger chains, to 0.0 degrees; her left thumb is
125.7 degrees further curled than rest and her middle finger 112.9, while her index stays straight
-- a holder gripped between thumb and middle finger. So the rest pose **is** the modeller's own
neutral hand, and relaxing the left one to rest reproduces the hand the model already has on the
other side rather than inventing one.

The builder fires only on that asymmetry: one hand at rest, the other 20+ degrees from it. A
character posed with BOTH hands gripping shows no asymmetry and is left alone -- which is the case
this must not break, since YARG puts a microphone in the hand and a deliberate two-handed grip is a
real thing to ship. `VRM_KEEP_GRIP=1` disables it. Only finger bones are touched: the blanket
reset-to-rest is what destroyed Alcina's 9'6" proportions once already, and this is not that.

**Measure the SHAPE of the hand, never the direction its bones point.** A direction test also sees
the whole arm's rotation: Alcina's right hand first measured 65.9 degrees "off rest" purely because
her static pose lifts that arm, and the asymmetry the check depends on vanished. Compare **curl** --
the angle between consecutive bones, summed down each finger -- which a rotation of the whole hand
does not change. `fingerpose.py <model>` prints it per chain for both hands.

## A posed sculpt: Anakin, and the switches he needs

Some archives are not a character plus a rig, they are a **scene** -- one figure frozen in an
action pose, most of it unrigged, props and a second character in the same file. The pipeline now
converts one, but it has to be told to.

```
VRM_REBIND_STALE=1 VRM_STANDUP=1 blender --background --python build_vrm.py --   "<src>/anakin pose.fbx" "<src>/textures" 1.85 anakin "Anakin" Anakin.vrm 1024   '^(Luke_Saber|obiwan\.002|Circle\.00[23]|Cylinder)$'
```

- `VRM_STANDUP=1` -- his spine lies 102 degrees off vertical, so he must be stood up before a
  T-pose means anything. **Opt-in on purpose:** measured automatically it fires on characters that
  are already standing (Sonic reads 115.4 degrees "off vertical" while perfectly upright).
- `VRM_REBIND_STALE=1` -- his head, eyes, hair and tabards are bound to four bones between them,
  against a rest pose this build replaces. Dropping those and re-binding everything in one pass is
  what stops them floating half a metre above the body. **Opt-in:** it claimed Yoda's eyes and
  eyelashes and moved his scale factor from 0.6471 to 0.1022.
- `VRM_REBIND_MAX_GROUPS` (default 4) -- how few bones a binding must use to count as a rigid
  attachment rather than real authored weights.
- The exclude list is doing real work: `Luke_Saber` is a prop, `obiwan.002` is a **different
  character** in the same file, `Cylinder` is the lightsaber blade (match it exactly, or it also
  catches `Cylinder.004`, which is part of him), and the two `Circle` meshes have zero size.

**Always check both arms AND legs after.** His bones all finish at 0.0 degrees and one leg's
geometry still smears, which is the limit described in `docs/character-models.md` under *Where
automatic weighting actually gives out*.

## Mixamo's auto-rigger: what it needs, and how it fails

The route for a model whose own rig cannot be used. Prepare the upload with
`strip_for_mixamo.py`, which now does four things that each turned out to be necessary:

- **Bakes any existing skinning into the geometry first.** A partly-rigged model keeps its skinned
  meshes at bind position while its unrigged ones sit where they were sculpted. Anakin uploaded as
  a headless body with his head floating beside it, because his head was the one mesh the file had
  skinned.
- **Joins everything into ONE mesh.** Every model that has rigged successfully here went up as one.
- **Stands a posed sculpt up** (`MIXAMO_UP="<hipsBone>,<headBone>"`). Mixamo will not make sense of
  a character lying at 102 degrees off vertical, and a rigid rotation deforms nothing.
- **Can drop embedded textures** (`MIXAMO_NO_TEX=1`). The browser upload is capped at 10 MB and
  Mando's embedded export was 12.6 MB; the rigger only needs geometry, and `build_vrm.py` re-applies
  textures from the archive's own folder afterwards.

**It fails SILENTLY, and that is the thing to know.** There is no error anywhere on screen: the
page simply returns to the marker step with the markers still in place. What actually happens is
visible only in the network and console:

```
PUT  /api/v1/characters/<id>/rig        -> 202
GET  /api/v1/characters/<id>/monitor    -> 202, 202, 200
console:  app:autorigger inputs: ...
console:  app:viewer  .../assets/UNRIGGED/verold.json     <- it reloaded the unrigged asset
```

Seeing `assets/unrigged/` after the monitor returns 200 is the failure signature. Each attempt
costs about 25 seconds, so a human watching it just sees the dialog bounce.

**What it rejects: limbs against the body.** Measured across attempts on one afternoon:

| Model | pose | result |
|---|---|---|
| Mandalorian | upright, arms clear of the torso | **rigged** |
| Anakin | mid-lunge, one arm up, legs crossed | rejected, 4 attempts |
| Judy Hopps | upright but arms straight down against her sides | rejected, 2 attempts |

Mixamo's own orient screen says it: *"have your character in T-pose and fingers spread apart"*.
Joining the mesh, standing it up and placing the markers carefully do not substitute for limbs
that are actually apart.

Working the dialog: **turn off Use Symmetry** for any asymmetric pose, or the mirrored marker lands
in mid-air. The orient step's up-arrow is "Rotate On X-Axis" and moves in 90-degree steps.

## Regression-test before committing a builder change

Three of these changes passed their own model and broke others. Sonic, Yoda and Alcina are the
cheap regression set, because between them they cover a kept T-pose clip, a hair rigger, a static
pose that is the model's shape, and a relaxed hand. Re-run all three and compare the numbers --
not the renders, the numbers, which are in their build logs:

| Model | height | scale factor | humanoid | other |
|---|---|---|---|---|
| Sonic | 1.00 | `x0.9968` | 28/52 | keeps the authored T-pose clip |
| Yoda | 0.66 | `x0.6471` | 28/52 | 1 spring chain |
| Alcina | 2.90 | `x0.7388` | 52/52 | relaxes the left hand, 61.3 vs 0.0 deg |

A scale factor that moves is the loudest signal available: it says the geometry being measured
changed size, which means something upstream moved it.

**Two of the three cannot be re-run from their archives.** Sonic and Yoda both arrive unrigged and
go through Mixamo, so the thing the table's numbers describe is the auto-rigged intermediate, not
the download. Keep those intermediates somewhere durable — a build that only exists in a session's
scratchpad takes two thirds of the regression set with it when the session ends. Alcina is the one
that rebuilds from her own archive, and she is also the one that covers the texture picker.

## Known per-model arguments

| Character | rig | height | notes |
|---|---|---|---|
| Prix | mixamo | 1.70 | shape keys must be dropped, else she builds at 0.42 m |
| Pomni | pomni | 1.70 | exclude `^Circle` |
| Sayuri / Aiko | cc_base / mixamo | 1.70 | hairrig `^Hair$` — no hair bones of their own |
| Aiko | mixamo | 1.70 | exclude `^Girl2\.[0-9]` — one girl, 15 Mixamo clips |
| Batman | multiversus | 1.88 | run `prep_batman.py` first: two half-characters on two armatures |
| Chibi Rem | rigify_def | 1.55 | exclude `'^(?!GME_Rem$).*'` |
| Gwen Stacy | mixamo | 1.70 | hairrig `island:1`, `HAIR_ANCHOR=0.70 HAIR_SEGS=2 HAIR_STRANDS=3` |
| Junio Sonic | sonic | 1.00 | `VRM_DROP_SOLIDIFY=1`, exclude `^Dots` |
| B1 Battle Droid | b1 | 1.93 | four of five meshes are empty placeholders |
| Thanos | advskel | 2.40 | source is a kneeling pose; head emission must be zeroed |
| Alastor | mixamo | 1.95 | exclude `^(Cube\|Microph)` — detached mic inflates the bounds |
| Jessica Rabbit | rigify_plain | 1.80 | exclude `^(BezierCurve\|Cylinder\|Cube)` |
| Clone troopers | mixamo | 1.83 | |
| Jinx | ue4 | 1.68 | braids and bangs already in the rig |
| Shrek | mayajnt | 2.10 | |
| Gordon Freeman | valvebiped | 1.80 | |
| Joker / Miku | maxbiped | 1.85 / 1.58 | |
| Tenna | rigify_def | 1.80 | exclude `^(Floor\|Lights\|Sign)` |
| Sophia | rp | 1.70 | |
| Steve | steve | 1.80 | |
| Shadow | sonicforces | 1.05 | |
| Pepsiman | arp | 1.85 | |
| Vegeta / Spider-Man PS | mixamo | 1.64 / 1.75 | |
| Mannequin | simple | 1.75 | |
| Sonic (HD) | mixamo | 1.00 | model arrives UNRIGGED — auto-rig it on mixamo.com first, then `VRM_RIGID="island:0=Head"`. Its T-pose is in the clip, not the rest skeleton |
| Alcina Dimitrescu | rigify_plain | 2.90 | 9'6" is correct and her static pose is her SHAPE — never reset it to rest. exclude `^NurbsPath` (the cigarette holder skewers her hand), `VRM_TEX="Material.005=CABELOO_preto_1.png,Material.019=(null)_Base_Color.png"`. The floating hat was the unrigged-mesh rescue resizing her whole rig by 0.5568 to fit one stray dress train; it is fixed |
| Yui Suzukaze | mixamo | 1.60 | recovered from her own .yargchar, re-rigged; needs the VRM_TEX map from the submesh headers |
| Lola Bunny | multiversus | 1.75 | exclude `^Icosphere` |
| Mickey Mouse | mixamo | 1.10 | archive is called `talking.zip` |
| Elite Terrorist | mixamo | 1.83 | |
| Jessica Rabbit | rigify_plain | 1.80 | hairrig `^hair`, `VRM_TEX="rskin=Skin_makup_0003_Body_multires_sculpt.001_m.jpg"` (the row used to record this truncated). A straight rebuild comes out 6% heavier than the installed character — 320,562 triangles against 340,638 — so something was excluded that nobody wrote down |
| Alice Ivy | cc_base | 1.70 | exclude `^COLLIDER` |
| Ariel | daz | 1.70 | hairrig `Hair`. Recovered from her own `.yargchar`: `lPectoral` and `abdomenUpper` are DAZ names, and the mesh bounds give the height |
| Killer Clown | mixamo | 1.80 | hairrig `hair`. Her bones are Mixamo's with the prefix stripped (`Hips`, `LeftHandIndex1`, `HeadTop_End`), which the family auto-detects |
| Heels | cc_base | 1.70 | hairrig `Hair`; the archive holds `source/untitled.zip` with the `.blend` inside. **Do not reinstall yet** — see the runlist: a rebuild loses her transparency |
| The Rock | mixamo | 1.96 | |
| Mario | mariojnt | 1.55 | |
| Link (OoT) | linkoot | 1.65 | `VRM_TEX="Hair=Link_Link_BaseColor.png"` |
| Gadget Hackwrench | rigify_def | 1.30 | exclude `^(WGT-\|smd_bone_vis)`, hairrig `^Hair$` |
| Peach | smash | 1.70 | her forearms are stretched in the SOURCE rip, not by the build |
| Harley Quinn | mixamo | 1.70 | build from the USDZ (names transferred from the .fbx) — the .zip has no colour map and the two have different UVs |
| The Mandalorian | mixamo | 1.83 | glTF; BOTH its skeletons are collapsed, so re-rig via Mixamo. Exclude `^(grogu\|.*CRADLE\|.*JetPack\|.*RIFLE\|Icosphere)` — the pack also contains Grogu, his cradle and a rifle |
| Power Girl | mixamo | 1.80 | Injustice 2 rip, 417 bones, builds clean. Materials are called `mesh0`/`mesh1`, so pin them: `VRM_TEX="mesh0=Supergirl_A_Body_Color.png,mesh0.001=Supergirl_A_FACE_30hz_Color.png,mesh0.002=Supergirl_A_Cape_Color.png,mesh1=Supergirl_A__EyesMouth_Color.png,mesh2=Supergirl_A_Hair_Color.png"`. Her hair alpha has to be pinned too, for the same reason — add `,mesh2=Supergirl_A_Hair_Alpha.png:alpha`. She is the ONLY model of the 109 archives here whose opacity map does not name its own material, so she is the only one the narrowed alpha pick leaves without one |
| Peacemaker | dcseries | 1.85 | exclude `^Peacemaker_obj_(BlueDeep\|RedGlow\|Silver_003)_0$` — a SECOND figure's helmet on a second skeleton, floating above his head. Left in, it is the tallest thing in the file and he scales to 1.51 m. Flat-colour model: its USDZ holds no images at all, so every material reading `-> NONE` is correct |
| Vigilante | dcseries | 1.88 | same rig as Peacemaker, based at `n8` instead of `n115`. He arrives armed, and the two weapons CANNOT be excluded by mesh name: they share `Vigilante_obj_001_Pewter_002_0` with the sheath on his back and the holster on his hip. `VRM_DROP_ISLAND="Vigilante_obj_001_(Pewter_002\|Silver_003)=n17+n50"` takes the 540 vertices the two hand bones carry and leaves the 204 the spine and hips carry. Height, width and humanoid count are unchanged by it (`x1.0552`, 0.7075 m, 47/47) — the weapons never affected his proportions, which is why they survived the first build |
| Shaggy Rogers | shaggyusd | 1.83 | USDZ, 52/52 — the whole humanoid including toes and three-bone thumbs, and already in a T-pose. One 1.5 KB palette texture does the entire character |
| Scott Hall | mixamo | 2.01 | the `.blend` in `source/`, not the fbx: a plain 65-bone Mixamo rig. exclude `^(Plane\|Scott Hall OGscale\|M_Jacket)$` — a joined duplicate of the whole body, a duplicate jacket and a backdrop. hairrig `Hall_Hair$`. His own file points the RIGHT elbow pad at the kneepad texture, so `VRM_TEX="Hall_Elbow-R=Hall_r_elbowpad_color.png,Hall_Elbow-R=Hall_r_elbowpad_roughness.png:rough"` |
| Anakin Skywalker | anakin | 1.85 | a posed SCULPT — see the section above; needs `VRM_STANDUP=1 VRM_REBIND_STALE=1`. One leg's mesh still smears |
| Judy Hopps | rigify_plain | 1.05 | exclude `^NurbsPath` (whiskers). Arms bind straight down at 86.6 deg off X and web to the torso when straightened — needs a Mixamo re-rig |
| Yoda | mixamo | 0.66 | USDZ, no skeleton at all — auto-rigged; `VRM_RIGID="island:0=Head"`, robe on `island:1` with `HAIR_BONE=Spine1 HAIR_STRANDS=1`. The USDZ has **no** eye map: merge `CHA_yodaEye_C.png` from the original zip and pin it with `VRM_TEX="yoda_mesh_RoninShader7=CHA_yodaEye_C.png"` |
| Miku | maxbiped | 1.58 | `VRM_FINGER_FILL=1`, hairrig `island:7+8` for the twintails, exclude `^ts_bot` (a detached guitar) |
| Skibidi Toilet | valvebiped | 1.60 | exclude `^(Icosphere\|Object_2$)` — the toilet shell swamps the model |

### Recovering a character from its own .yargchar

A `.yargchar` is a Unity AssetBundle, so a character whose source archive is
gone is not lost. `unpack_submeshes.py <file.yargchar> <outdir>` writes one OBJ
per SUBMESH plus every texture, and — the part that matters — reads the
renderer's material list to say which texture each submesh uses.

Do NOT use the whole-mesh export for this. A Unity mesh holds several materials
as submeshes of one object, and exporting it whole throws that away: Yui
Suzukaze's skin, uniform, skirt and boots came out as a single object, so only
one of their eleven textures could be applied and she rendered half undressed.
UnityPy will not hand over a decoded vertex array on a modern bundle, but it
will write the mesh as OBJ, and faces come out in index-buffer order — so the
submeshes' index counts slice that face list with no buffer decoding at all.

Then: `assemble_objs.py` to put the parts back together (Unity is left-handed,
so it mirrors X and flips the normals), `strip_for_mixamo.py` to export, rig on
mixamo.com, and build with `rig=mixamo` and a `VRM_TEX` map built from the
`# material ... texture ...` header each OBJ carries.

`contact_sheet.py <texdir> <out.png>` puts every texture in one labelled image,
which is much cheaper than opening thirty files when an archive names them
`_01` ... `_27`.

### A USD export with its bone names stripped

USDZ routinely renames every bone to an ordinal -- Harley Quinn's
`mixamorig:Hips` arrives as `n7` -- which makes the rig unmappable even though
it is bone-for-bone the rig the `.fbx` of the same model carries. The `.fbx` and
the `.usdz` of one model can also have DIFFERENT UV layouts, so the right move
is to keep the USDZ's geometry and borrow only the names:

```
blender -b -P name_from_donor.py -- <nameless.usdz> <named.fbx> <out.blend>
```

It walks the two trees together and pairs siblings by subtree size first,
position second. Flat nearest-neighbour matching across all 65 bones at once is
an assignment problem a greedy pass gets wrong; the hierarchy makes it trivial.
Check the result with `checknames.py` before building: the head should be the
highest bone and `LeftUpLeg` should be at +x.

### When a part ends up in the wrong place, TRACE it

`VRM_TRACE=<mesh-name-substring>` prints that mesh's evaluated world box at
every stage of the build: after import, after the constraint conversion, after
the realign, after the pose bake, after the scale, before export. Three wrong
fixes were written for Alcina Dimitrescu's floating hat by reasoning about
matrices; the trace found the real cause in one run, and it was not where any
of them were aimed. Reach for it first.

What it found, and what each is worth knowing:

- **The unrigged-mesh rescue was resizing a working rig.** The refit exists for
  a model with NO rig (the HD Sonic). Alcina has one stray 49,091-vertex dress
  train with no weights, and fitting the skeleton to it shrank her whole rig by
  0.5568 -- hat above her head, cigarette holder through the floor. The rescue
  now stands down whenever any mesh is already bound.
- **Constraint-driven parts must be converted FIRST**, before anything asks
  what is rigged, or the rescue claims them.
- **A static pose can be the model's SHAPE.** Alcina is 9'6" because her pose
  says so, with no action attached. Resetting every bone to rest -- right for a
  stray Mixamo clip -- compressed her head and torso to 59%. The reset now only
  runs when an animation was actually attached.
- **A PBR set can put one map type's word in several filenames.** Yoda ships
  `..._metallicRoughness_metal_scale0.jpg` and `..._metallicRoughness_rough.jpg`;
  the metal one (a 1x1 black image) became his ROUGHNESS, so his robe shipped
  as a mirror. The short code at the END of the name breaks the tie.

### Straighten an arm JOINT BY JOINT

The T-pose correction used to rotate only the upper arm until the HAND sat on
the X axis. That leaves whatever bend the elbow had, and the sleeve pinches
into a crimp at the joint. Alcina Dimitrescu's static pose holds her left elbow
at 119.3 degrees -- her REST pose is already a near-T, 5.4 degrees -- so
correcting the arm as one segment swung the forearm round the shoulder and
crimped her sleeve. It now puts the upper arm along X first, then the forearm,
using `<side>_lower_arm` from the rig map. A rig with no forearm mapped falls
back to the old single-segment behaviour and says so in the log.

### A cloak is hair, as far as the rigger is concerned

An auto-rigger skins a loose outer garment to the arms as if it were skin, and
it then webs between arm and body the moment the character T-poses. Give it the
hair rigger instead: `HAIR_BONE=Spine1` hangs the new chains off the chest
rather than the head. Use `HAIR_STRANDS=1` for a garment -- splitting a
continuous robe into four strands tears it into shards when the chains diverge,
because neighbouring vertices end up on different chains.

### Things that are not the pipeline's fault, and how to tell

The Blender **VRM importer** re-poses a skin on import and can draw a perfectly good character
with arms stretched metres wide. Before believing a bad render of a `.vrm`, check the two things
that cannot lie: render the `VRM_SAVE_BLEND` scene, and read the POSITION accessor min/max out of
the `.glb` chunk. The Rock measured 5.13 m wide on re-import while both of those said 1.96 m.

A model can also arrive broken. Render the SOURCE as a control (`render_vrm.py` reads .fbx/.glb/
.blend/.usd as well as .vrm) before changing anything: Peach's forearms are flat blades in the rip
itself, and Harley Quinn's archive contains a normal map and nothing else.

### An unrigged model: send it to Mixamo

A mesh with no weights at all cannot be rescued by bone heat — it refuses to solve on a mesh of
loose shells and returns FINISHED having bound nothing. `mixamo.com`'s auto-rigger does the job
properly: export the geometry alone with `strip_for_mixamo.py`, upload it, place the five markers
(put the elbow at the MIDDLE of the arm — too close to the shoulder and the T-pose straightening
kinks it), apply the **T-Pose** animation, and download FBX Binary *with skin*. Build the result
with `rig=mixamo`.

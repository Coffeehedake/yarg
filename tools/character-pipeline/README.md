# YARG character build tooling

Tooling for turning a third-party model into a `.yargchar`.

The **tooling** is published here; the **characters it produces are not**. They are personal-use
conversions of third-party models, so no `.yargchar`, `.vrm`, texture or source archive belongs
in this repository — only the scripts that make them.

The reasoning behind almost every line is written up in `docs/character-models.md`. Read that
first; this file is only how to *run* it.

> **The installed set is 65, and was 66 until 2026-11-11.** Kasane Teto was removed: she stands
> in her T-pose and never animates, she is a downloaded bundle with no source so there is nothing
> to re-export, and her cause is still not known — see her row below. Both documents carry
> measurements taken while she was installed, and those say **66** on purpose. A count of 66 is a
> statement about when it was measured, not a stale 65; anything measured after that date says 65.

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
  `island:N` addresses the Nth-largest connected island for a part with no name of its own, and
  the build prints where each island sits so a recipe can be written from its own output

**More than one group.** The positional `hairrig` is the hair, and `VRM_RIG_MORE` adds further
groups — a dress as well as hair, a cape as well as a tail:

```
VRM_RIG_MORE="pattern@bone#segs,strands,anchor,lo,hi;pattern2@bone2"
```

`;` separates groups, `@` names the bone the group hangs from, `#` sets that group's own numbers,
and everything after the pattern is optional. `lo`/`hi` clip the group to a band of the
**character's height** (0 at the feet, 1 at the crown) for cloth that has no name, no material
and no island of its own. Fractions rather than coordinates because the build moves and rescales
the figure before the rigger runs.

A group anchored anywhere other than the head gets its chains named `ClothSpring` instead of
`HairSpring`, which is what puts it on the gentler cloth spring parameters below — a cape and a
ponytail want different numbers, and the chain's name is what the spring section judges by.

**Which end is attached is measured, not assumed.** Chains are built outward from the anchor
bone, by comparing the two ends of the group against the MIDDLE of that bone in three
dimensions. Do not assume the top: Mando's cape anchors at his chest and his build scene has z
running the other way.

Environment switches: `VRM_TEX="Mat=file.png[:kind]"` forces a texture onto a named material when
the archive's names carry no information (Alcina's fourteen `Material.NNN`); `VRM_RIGID="island:N=Bone"`
binds a connected mesh island wholly to one bone, for a part an auto-rigger has no business bending
(Sonic's back quills); `VRM_DROP_ISLAND="<mesh-pattern>=<bone>[+<bone>]"` drops the islands of a
mesh that one bone CARRIES, which is how a weapon comes out of a hand when the same mesh also
holds gear that belongs on the character (the mesh pattern is not optional — a hand is itself
weighted to the hand bone); `VRM_BREASTRIG=1` builds chest bones for a rig that has none and weights the bust onto
them (`check` measures and prints without changing anything, which is how it was written);
`VRM_BREAST_SPRING=0` stops chest bones being sprung and `VRM_BREAST_PARAMS="stiffness,drag,gravity"`
changes the feel; `VRM_CUTOUT_INFER=1` infers a cutout from a base map's own alpha and
`VRM_CUTOUT_MATERIALS="a;b;c"` does the same for named materials only, when the inference is right
about some of a character's materials and wrong about others; `VRM_BLEND_MATERIALS="a;b"` is the third state, for a
material whose alpha has no extremes at all and that therefore no cutoff can express — Gordon
Freeman's glasses lenses; `VRM_MTOON_ALL=1` puts every material
on the MToon shading model, which is what a character needs when a cutout shares a continuous
surface with an opaque material (otherwise only the cutouts are MToon and the seam shows);
`VRM_LIMB_COLLIDERS=0` goes back to a head sphere and a torso capsule alone;
`VRM_SAVE_BLEND=<path>` saves the pre-export scene (the single most useful
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
| The Rock | limbs stretched into metre-long spikes | **FIXED 2026-11-11.** His skeleton spanned 4.47 m against a 1.96 m mesh, bones 1.7 m below the floor. Two stages: scale the rest skeleton about the hips (already correct at 0.573 of height) anchored on feet-on-floor, then `fit_joints.py` to place each limb joint at the boundary of the flesh it separates — needed because legs and arms were wrong by different factors (0.387 vs 0.557), which no single scale expresses. `FINGERFIT` 30/30 at 135.3 cm → **0/30 at 4.1 cm**; posed displacement 2.36 m → 0.93 m; geometry unchanged. Rebuilt, installed and podium-verified |
| Power Girl, Judy Hopps | legs cross over each other when posed | **left and right are swapped.** Measured across all 66: 258 of 264 limb pairs agree on which side is which, and these two supply all six disagreements |
| Prix, Pomni | eyes render as solid white; hair reads as a cap | every material in every character exports `alphaMode: OPAQUE` — see below. **Pomni's eyes are fixed** (her own row, further down). **Prix's are not, and her hair must be left alone**: the only hair map in her folder is a DIFFERENT model's atlas reached by the loose fallback, so honouring its alpha leaves her bald. Her eye textures are still open |
| Ariel, Heels | lower hair hangs in space while the body moves | the hair rigger leaves part of the hair behind. Chains are correctly parented and every vertex is weighted, so it is neither of the obvious two |
| Mando | cape folded in on itself, static | the documented cloak case, and the recipe alone was not enough: built with `HAIR_BONE=Spine1` the rigger took the HEM as the attached end, pinned it to his thighs and left the swinging tip at his collar |
| Jessica Rabbit | dress static while the body moves; sequin texture on her skin | the rigger took one group per build, so her hair and her dress could not both be rigged. `rskin` had already been given its own map |
| Alcina | chest drifts like a balloon | **chest spring parameters do not scale.** 0.85 stiffness and 0.60 drag were set looking at Prix at 1.70 m; Alcina is 2.9 m and VRM spring stiffness is scale-dependent |
| Yui | looks out of proportion | not yet measured |

### Round of 2026-11-09, after the undriven-weight batch went in

Four more in-game reports, four separate causes. All four are written up in
`docs/character-models.md`; the short version:

| character | what is wrong | what it is |
|---|---|---|
| Batman | his chest jiggles | the shared MultiVersus rig ships `fml_un_C_breast` on **every** character, and on his export it carries enough weight to be sprung. Rebuilt with `VRM_BREAST_SPRING=0`. The pipeline cannot know he should not jiggle, so this stays a per-character knob |
| Pomni | black marks above and below the iris | **two faults on one eye.** `EyeDetails` is authored `blend_method=BLEND` with `Eyes.png` in its Alpha and exported `alphaMode=OPAQUE`, so the 69.2%-clear sheet rendered its clear pixels black; and `PomniEyes`, the sclera, has **no texture at all** in the source but took `Eyes.png` on a substring match — measured against its own UVs that map is 67% transparent. It also held a *hair* normal map |
| Lola Bunny | ponytail detached and floating beside her head | the hair spring chain was anchored on `fml_un_C_hair_att`, which is **0.260 long carrying 51.9% of the hair** against 0.100 and 48.1% for the rest of the chain. A VRM chain rotates joint 0 to move joint 1, so the sim swung the bulk of her hair on a lever 2.5× the hair's own length, with zero colliders to catch it |
| Jessica Rabbit | turned to the side, rubber legs, dress clipping | facing was read off the feet, and her feet are crossed in heels pointing **within 2° of her own shoulder line**. The build turned her 89° to face the feet forward and shipped her in profile; the per-arm straightening then put the arms along X anyway, so nothing downstream noticed |
| Ariel | blank white eyes, and a pale band across the forehead | **one fault, two symptoms.** glTF has no opacity map — alpha is `baseColorTexture`'s own alpha channel and nothing else — and the builder was wiring `X_Opacity.png` into a second image node that `mtoon1` has nowhere to put. It was dropped on export, so `Cornea_BaseColor.png` shipped **RGB**, alpha fell back to 1.0, and a pure-white shell (its opacity map is 100% below 10%) was drawn over her iris. `Hair Cap` failed identically and painted the forehead band. Now baked into the base map's alpha by `_bake_opacity_into_base`; verify by checking the exported PNG's colour type is RGBA |
| Ariel | purple eyebrows, pink eyelashes, navy scalp cap | the guard that lets an authored colour refuse a loosely-named texture assumed the colour means something. **All 26** of her materials carry a different saturated pastel — a pure green cornea, teal teeth — a palette the exporter generated. Measured per file: a real palette is ≥79% neutral-or-hue-pure (Pomni 100%, Peacemaker 50%), Ariel is **4%** and Power Girl **0%**. Below 25% the colours cannot veto a texture |
| Ariel | iris glowed white (`emissiveFactor [1,1,1]`) | Daz ships an emission-**colour** map per surface whether or not it glows, gated by a strength no FBX carries. Mean brightness looked decisive on a sample of two and collapsed on the full set — it would have stripped **Thanos's gauntlet**. The real split is how much of the map is **lit**: every genuine mask lights ≤9.1% of its area (Master Chief 0.01%, Thanos 4.06%, K-2SO `DROID_Misc` 9.10%), while `Irises_Emissive.png` lights **100%** and holds not one black pixel. Refused above 50%. Note this was **not** why her eyes were white: killing it changed the render not at all |
| Alice Ivy, Heels, Power Girl | the same missing-alpha fault | found by sweeping every built `.vrm` for a non-opaque material whose base texture has no alpha channel: **Alice Ivy 8, Heels 2, Power Girl 1**. Rebuilt 2026-11-11. Alice keeps 6 of 7 (`Cap_Transparency` has no base texture at all — a separate sub-case); Heels goes to 7 with alpha and resolves her "a rebuild loses her transparency" warning; Power Girl's hair cards stop being slabs |
| Heels | **her shoes vanished** on the first attempt at the fix | `High_Heels_Diffuse-High_Heels_Opacity.png` is a *merged* UniGLTF texture — RGB diffuse, mask in the alpha — that arrived as plain RGB, so its alpha was already gone. Baking its colour as alpha put the shoes at 0.25, under the 0.5 MASK cutoff. Triangle count was identical and every automated check passed; only the render caught it. The channel is now chosen by `img.depth`, and a merged RGB file with no alpha is declined |

### The character test stage

A `.yargchar` is only shown if the VENUE supplies a slot for it.
`BackgroundManager.LoadCharacter` bails on its first line unless the venue root
has a `VenueCharacter` of type `Vocals`, then instantiates the custom character
into the **parent** of that placeholder and destroys the placeholder; lipsync
additionally needs a `CharacterManager` under the root. Measured against a
known-good control, the community venues on Nexus have neither:

| venue | `CharacterManager` | vocalist slot |
|---|---|---|
| Character Test Stage (ours) | yes | `VocalistAnchor` + `VocalistPlaceholder` |
| Moe's Tavern | no, only `Light Manager` | none |
| GH2 Arena | no, only `Light Manager` | none |

So a character can be installed, correct, and still never appear.
`YargVenueExporter.cs` builds a deliberately plain stage — floor, two cameras,
one light, the managers, the vocalist slot — so that anything that looks wrong
on it belongs to the character rather than the venue:

```
Unity.exe -batchmode -nographics -quit -projectPath <fork>   -executeMethod YargVenueExporter.ExportTestStage -outDir <dir>
```

The podium browser in **Content Browser -> Character Select** already renders a
`.yargchar` and runs the spring simulation, so it covers colliders, hair,
textures and proportions. This stage is for what it cannot show: a character
PERFORMING -- lipsync, blink, the animation controller.

Two faults found by running it, both mine, both worth knowing before building
any venue:

- **The vocalist showed his back.** Cameras on -Z, character facing +Z.
  `LoadCharacter` does `Instantiate(character, existingParent)`, which keeps the
  prefab's own world transform rather than adopting the anchor's, so rotating
  `VocalistAnchor` cannot be relied on to turn him round. The cameras moved to
  the side he already faces instead, which works whatever his rotation is.

- **A NullReferenceException on chart load.** `CameraManager._profile` is a
  `[SerializeField] VolumeProfile` the VENUE must supply, and a null one throws
  in `InitializePostProcessing` (`PostProcessing.cs:76`, reached from
  `CameraManager.cs:229`). That matters more than it looks: the throw aborts the
  rest of `OnChartLoaded`, so `InitializeVolume` and the camera-cut setup below
  it never run, and the venue silently loses its camera behaviour. Assign
  `Assets/Authoring/Venue/Unique/VenueProfile.asset`. Note `CameraManager.cs:131`
  computes `_volumeSet = _profile != null` immediately above, so null IS
  anticipated -- line 229 just doesn't check. Arguably an upstream bug.

A character playing only its idle animation is NOT one of these. `ProcessVocals`
is driven entirely by `_vocalEvents` and `_vocalMaps`, built from the song's
vocals chart (`if (vocalsId.Notes.Count > 0)`), so a song without a charted
vocals part leaves the singer idle by design -- and lipsync and blink have
nothing to exercise either.

Venue facts worth not rediscovering, from <https://wiki.yarg.in/wiki/Venue_Creation>
and the source: the root must be named `Venue`; `BundleBackgroundManager`'s
camera field is a lowercase `mainCamera` carrying a "DO NOT CHANGE the name of
this!" comment; `CharacterManager` and `CameraManager` each need a
back-reference to the venue root; venue cameras must have their `AudioListener`
removed and be culled to the `Venue` layer. `LightManager` and `VenueLight` are
in namespace `YARG.Venue`, NOT `YARG.Venue.Lights`, and the class `VenueCamera`
sits in a namespace whose last segment is also `VenueCamera`, so it has to be
fully qualified.

### Lipsync and visemes

Measured across all 28 built characters: **none had a single viseme bound**, so lipsync could
not work on any of them. The shape-key pass drops everything except blink by default -- right
for size (Prix: 8.6 MB -> 28.3 MB with all of hers) -- and visemes were never on the spared
list, so the shapes were being deleted before they could be bound.

It now spares and binds only the keys it actually uses. Character Creator sources carry the
full set:

| character | before | after | cost |
|---|---|---|---|
| Heels | 2 keys, blink only | 5/5 visemes + blink | 10.70 -> 12.21 MB |
| Alice Ivy | 2 keys, blink only | 5/5 visemes + blink | triangles unchanged |

`VRM_NO_VISEMES=1` opts out per character.

Two things to know before trusting it:

- **The mapping is phoneme-group to phoneme-group.** Character Creator has no separate IH, so
  `ih` and `ee` both take `V_Wide`. That is the source set's limit, not a guess a different key
  would improve.
- **Name matching is anchored on purpose.** A loose `mouth` match catches the seventy-odd
  `Mouth_Smile` / `Mouth_Pucker` / `Mouth_Blow` shapes that sit directly beside the visemes on a
  CC body, and would bind a vowel to a smirk.

**A character with no morph targets cannot lipsync and nothing here can change that.** Batman
and Jessica Rabbit both export zero. Every VRM declares all 18 preset expressions regardless, so
a file always *looks* lipsync-capable -- the distinction is declared versus bound. Check the
morph-target count before suspecting the venue, the `VRMCharacter` component or the chart.

### Exaggerate the mouth, or nobody sees it

Pomni's visemes worked first time -- her mouth tracked the words -- and were **"barely
noticeable"**. A mouth modelled for a close-up is far too subtle at the distance YARG draws a
vocalist, and the bind WEIGHT cannot fix it: `aa` is already at 1.0, which is the ceiling.

`VRM_VISEME_GAIN=2.2` scales the shape key's own displacement, so weight 1.0 then means a
bigger mouth. Viseme keys only -- amplifying a blink drives the eyelids through the eye.

Check the result at full open before shipping it: doubling a shape key can tear geometry.
Pomni at 2.2x opens wide with teeth and tongue visible and holds together.

**Measured 2026-11-10 -- 4.4x is too much for Pomni.** At 4.4x her upper lip peels back over her
nose and forehead and the open mouth shows straight into her head (front and side renders at
weight 1.0). At 3.0x the lips stay on the face and teeth and tongue read clearly; her lower lip
droops onto the collar but nothing is see-through. She now ships at **3.0**. Render the mouth at
weight 1.0 from the side as well as the front: the front view hid the lip flip.

`ih` is the preset most models have no shape for -- Alastor has `a`, `e`, `o`, `U` and no `i` at
all. It falls back to `ee` at 0.7, because an unbound viseme is a mouth that stalls mid-word.

### Who can lipsync at all

Measured with `viseme_fit.py` over all 44 sources still on this machine. Only **9** have mouth
shape keys:

| character | what the source has | bound |
|---|---|---|
| Chibi Rem | `vrc.v_aa/ih/ou/e/oh` -- a complete VRChat set | 5/5 |
| Heels, Alice Ivy | the Character Creator `V_*` set | 5/5 |
| Alastor | `a`, `e`, `o`, `U` -- no `i` | 5/5 (ih mirrors ee) |
| Gordon Freeman | FACS action units: `AU26` jaw, `AU12` lip corners, `AU18` pucker | 5/5 |
| Pomni | `A`, `ClosedTeeth`, `ClosedTeethVariation`, `OpenNoTeeth` -- named for an artist | 5/5, but only from **2026-11-12**: this table claimed 5/5 while she shipped at 1/5 for weeks, because only `A` is guessable and nothing had checked the built file. Mapped by hand; see below |
| Doom Slayer | `JawDrop` (`CheekPuff`/`CheekSuck` deliberately NOT used -- puffed cheeks are not a wide mouth) | 5/5, all from `JawDrop` at five weights |
| Prix | `M_kiss` only, so `ee`/`ih` alone | **skipped on purpose** -- her README row warns her shape keys must be dropped or she builds at 0.42 m |
| Jessica Rabbit | a DIFFERENT source blend has keys; the GLB she was built from has none | not attempted |

The other 35 have **no mouth shape keys at all**, Batman among them. No pipeline change can give
them one.

### What is actually INSTALLED, measured 2026-11-12

That table is about sources. `viseme_audit.py` reads the bundles the game loads, which is the only
version that can be wrong, and the two disagree:

> **65 installed: 13 with all five visemes, 0 partial, 52 with none; 10 can blink.**
>
> *(It was 11/1/53 when first measured, with Gordon Freeman broken and Pomni at 1/5. Both are
> fixed below.)*

| | |
|---|---|
| **11 at 5/5** | Alastor, Alice Ivy, Chibi Rem, Doom Slayer, Gordon Freeman, Heels — and the five downloaded bundles (Adachi Rei, Harq Alkahana, Inforder Trogen, both Hatsune Mikus), which carry 70-odd expressions each including a full `*_hi`/`*_lo` phoneme set |
| ~~1 partial~~ | **Pomni was 1/5 and is now 5/5** — mapped by hand on 2026-11-12, see below. The table above claimed 5/5 all along and was wrong until then |
| **53 with none** | 35 have no mouth shape keys and never can; the rest are characters whose source has them but whose installed build predates the viseme work |
| **Alastor and Doom Slayer** | 5/5 bound but `blink=NO` — they have a mouth and no eyelids |

**Run this audit after rebuilding any character.** It is how a regression introduced on 2026-11-12
was caught: Gordon Freeman was rebuilt for his glasses, and the rebuild silently shipped **zero**
morph targets where his installed bundle had twelve. The cause is the next section.

### A hand-written viseme map that is not in the recipe row will be lost on the next rebuild

Gordon Freeman's shape keys are FACS action units — `AU26ZR+AU26ZL` (jaw), `AU12R+AU12L` (lip
corners), `AU18R+AU18L.001` (pucker). **None of them matches any of the anchored viseme patterns**,
and the patterns are the only automatic path, so his 5/5 came from an explicit `VRM_VISEME=`
mapping written by hand — which his recipe row did not record. Rebuilding him from the documented
recipe therefore dropped all 32 of his shape keys and bound nothing, and the build log said so in
passing while every count a census checks stayed identical: 7,169 triangles, 4 meshes, 7 materials,
6 images.

The map was recovered from the bundle that still had it rather than guessed, by reading its
`morphTargetBinds` back — node, target index and weight — and it is now in his row. The general
rule: **an env var that a character cannot be rebuilt without belongs in the recipe table the
moment it is used**, and `viseme_audit.py` is the check that catches it when it is not.

### Pomni, mapped by hand: 1/5 to 5/5

Her face carries `A`, `ClosedTeeth`, `ClosedTeethVariation` and `OpenNoTeeth` — real mouth shapes
named for an artist, and only `A` is guessable, which is why she sat at one viseme. Rendering each
at weight 1.0 is the only way to choose between them, and it settles it immediately:

| shape | what it actually is | mapped to |
|---|---|---|
| `A` | wide open, upper teeth and tongue | `aa` @1.0 |
| `ClosedTeeth` | lips retracted over a full row of teeth — a grin | `ee` @1.0, `ih` @0.7 |
| `OpenNoTeeth` | a rounded oval, no teeth | `oh` @1.0, `ou` @0.6 |

```
VRM_VISEME="aa=Face/A,ee=Face/ClosedTeeth,ih=Face/ClosedTeeth@0.7,oh=Face/OpenNoTeeth,ou=Face/OpenNoTeeth@0.6"
```

Her `VRM_VISEME_GAIN=3.0` now applies to two shapes that had never been exaggerated, so both were
checked at weight 1.0 **front and side** as the gain note above insists: no tearing, lips stay on
the face, nothing shows through into her head. 32,764 triangles, 16 meshes and 6 spring chains
unchanged; morph targets 21 → 27; she also picks up the eight limb colliders she had been excluded
from, so 2 → 10.

**`RENDER_KEY="Face/A=1.0"` in `render_closeup.py` is what made that possible**, and it exists
because four attempts at framing a camera on her mouth from the shape key's own displacement all
landed on her eyes — her mouth keys move the eye region more than they move her lips. Framing on
the head BONE, which that script already did, works first time.

### `identify_build.py` was wrong about Pomni, and it cost her two rounds

Her rebuild reported `rotation-mismatch=5` against her installed bundle, at `Arm.L`, `Arm.R`,
`Eye.L`, `Leg.L` and `Leg.R`, and on that basis she was excluded from the collider rollout twice
as "the `.vrm` is not what is installed". **It was an artefact.** A glTF node name is not unique
and a VRM routinely reuses one: those five are the names of her MESHES as well as her bones. The
mesh node sits at the origin with an identity rotation, the bone carries the real transform, and
whichever was written last won the dictionary. Every real bone matched to four decimal places.

The comparison now drops a name that identifies more than one node — from the value comparison
only, because dropping it from the name overlap as well pushed her score from 92.5% to 87.1% and
under the threshold, turning one wrong verdict into a different wrong verdict. Verified in four
directions: Pomni now MATCHes, Jinx still MATCHes, Gadget Hackwrench still differs at 57 rotations
(hers is a real re-pose, not a naming artefact, so excluding her was correct), and a deliberately
wrong pairing still reports nothing in common.

### viseme_fit.py -- proposing a mapping for a model that does not follow a convention

```
blender --background --python viseme_fit.py -- <source>
```

Prints a table of every shape key that moves geometry -- how many vertices, how high up the
face, how far the jaw drops (`open`) and how far the mouth widens (`wide`) -- and then a
`VRM_VISEME=` string to check and edit.

It uses names AND measurement, because neither is sufficient alone:

- **Names win where they exist.** Measured on Pomni, the biggest jaw-opener is `Expression2`,
  some startled face, which beats her shape literally called `A`. The widest opening is not the
  phoneme.
- **Measurement fills the gaps**, and is the only thing that works on a model named for an
  artist rather than a phoneme set.

**It was wrong three times before it was right, and each failure is worth knowing:**

| what it proposed | why | the fix |
|---|---|---|
| `aa = Lashes.R/Closed` | a closing eyelid travels downward exactly as a jaw does | exclude eye meshes; measure, then exclude, never select on eye-ness |
| nothing at all, on Pomni | her face read as 27% of model height -- her `.blend` carries rig widgets that stretch the bounding box | normalise within the **shape keys' own** height range, never the model's |
| nothing at all, on Heels | a bounding-box-relative threshold rejected all 420 of her keys; her source sits at a different scale | rank relatively, never threshold absolutely |
| `aa = Eye_Wide_R` on Heels | name matching ran only inside the measured mouth band, and CC puts eyes and mouth on one `CC_Base_Body` | match names over **every** key -- a name does not need the band to be right |

`--validate` is the point: it reproduces Heels and Alice Ivy exactly (`aa=V_Open`, `ee`/`ih`=`V_Wide`,
`oh=V_Tight_O`, `ou=V_Tight`) and gets Pomni's one name-derivable preset right. **A change that
breaks those three is wrong however reasonable it looks** -- that is this project's
`validate-a-heuristic-on-solved-cases` lesson, and it caught every one of the four failures above.

What it cannot do: invent lip rounding a model has no geometry for. Where no rounding shape
exists, `oh` and `ou` are driven from the opener at reduced weight, which reads as "open less"
rather than as rounded lips. The report says which of the two you got. That is honest talking,
not accurate phonetics.

### When the Unity batch export "fails"

`unity exit 1` with a log that stops around `Begin MonoManager ReloadAssembly` usually does not
mean the project is broken. It means **another Unity instance already holds it**. Unity refuses
the project and exits immediately.

Two ways that happened in one session:

- A **zombie Unity** survived a killed export and kept `Temp\UnityLockfile`. `pgrep -f Unity.exe`
  from Git Bash did NOT see it; `Get-Process | Where ProcessName -match '^Unity'` did, with 97
  seconds of CPU.
- Deleting that lockfile and `Assets\__TempExport` triggered a **full shader and library
  rebuild** -- 22 `UnityShaderCompiler` processes, several minutes -- and every export launched
  during it exited 1 on arrival.

The fix both times was to wait, not to kill: once the running instance finished, the identical
command succeeded first try. Check for a live Unity before concluding anything, and prefer
waiting over killing, because killing restarts the rebuild that is causing the problem.

**Do not judge an install by its timestamp.** `Copy-Item` preserves `LastWriteTime`, so an
installed `.yargchar` carries the time it was BUILT, not the time it was copied. Gadget's read
`11-09 21:57` after being installed on 11-10, and her hash matched the fresh build exactly.
Compare size or hash instead. And an export reporting `exit 1` has sometimes still produced and
installed its file -- Yoda did. Verify the artefact, not the exit code.

### Colliders

Every character shipped with **zero spring-bone colliders**, so every sprung chain passed
through the body. Two measured colliders now go on each: a sphere fitted to the head geometry
(excluding anything a spring drives) and a capsule down the torso whose axis comes from the
spine bones but whose ends come from the vertices.

- `vrm_colliders.py` — the measuring, shared so it cannot drift
- `build_vrm.py` — calls it during a build; `VRM_COLLIDERS=0` opts out
- `add_colliders.py` — retro-fits a built `.vrm` (import, fit, re-export) for the characters
  whose source files are gone, and prints a before/after census so a lossy round trip is visible
- `VRM_COLLIDER_SCALE` — multiplies both radii, for tuning from in-game feedback

Radii are **median** distances, erring small on purpose: hair sinking slightly into a body reads
far better than hair held visibly off the head.

**Reach is bounded by what still exists -- but by MORE than the scratchpad.** A correction to an
earlier claim here that 35 characters had "neither source nor VRM": there is a durable store at
`%USERPROFILE%\Documents\YARG-Characters\` holding **25 `.vrm` files** alongside the installed
bundles, which the scratchpad-only survey never saw. Counting both locations there are **51**
VRMs for 66 installed characters. Names differ between the two (`DoomSlayer.vrm` against
`Doom Slayer.yargchar`), so coverage has to be matched case by case rather than by a filename
join -- the naive join is what produced the wrong 35.

The census caught two of the 23 round trips, which is the whole reason it prints:

- **Pomni** lost 14 triangles and gained 4 materials. She has a source file, so she was rebuilt
  from it instead -- back to the full 32,764 triangles with the colliders built in.
- **Link** gained a material, `Link` -> `Link` + `Link.001`, and the two copies point at
  *different* base textures, which looks alarming. Checked per primitive: all 8 keep exactly the
  image they had. The importer split one material across meshes that already used different maps,
  so it is bookkeeping, not a visual change. Shipped.

Four characters were skipped because they have no spring chains at all, so a collider would have
nothing to collide with: **Alastor, Elite Terrorist, Gordon Freeman, Joker**. Alastor is worth
noting — "his hair is still not right" has a simpler cause than any collider: it was never sprung.

The Lola and Jessica fixes are general and apply to every rebuild; Pomni's two are general to
material handling. Batman's is a per-character flag. None of them touches a character that is
not rebuilt, so the other installed builds are unaffected.
| Kasane Teto | does not animate at all, stands in her T-pose | **her bundle has no AnimatorController and no AnimationClip.** 1 of 66; every other character has both. **But that is not established as the CAUSE (2026-11-11):** the game's `LoadAnimationDefaults` already loads `Animations/Vocals/Default/DefaultController` when the animator has none, and that controller has the `Idle` and `Playing` states she is configured for. Ruled out: missing component (she has `VRMCharacter`), `UseCustomAnimations` (0), mismatched state names, failed Resources path. She is a DOWNLOADED bundle with no source, so there is nothing to re-export either. Needs the game rebuilt with logging to settle |
| Lola Bunny | head floats detached above the neck | a part following a bone that does not follow the body — the same shape as Judy's belt and the static hair |
| Judy Hopps | belt detached, arms and legs crossed | the crossing is the mirrored rig above; the belt is the detached-part case |
| Gordon Freeman | every texture misplaced except his head | **measured and fixed by a rebuild.** His installed bundle carries `gordon_d` — his FACE map — duplicated five times, on his eyes, his HEV suit and his suit mesh, with no `onefreeman` and no eye texture in the bundle at all. His head was right because `gordon_d` is the one place that map belongs |
| Miku | dress does not move with her | **ALREADY FIXED, re-measured 2026-11-11.** It was 23.7% of her body, 985 vertices including the skirt, on `Bip01 Pelvis` -- a bone above the humanoid root, which nothing drives. The undriven-weight batch moved that weight down onto `Bip01 Spine`, which IS her mapped `hips`, and the installed bundle was exported from the fixed VRM two minutes later. The control is the old build: `drivers.py` reports 24.0% undriven on `Miku.vrm` of 11-08 and 0% on every build from 11-09 19:54 on, so the zero is a real zero. `pose_check.py` moves all 3,958 of her vertices with no static region, and the posed render shows the skirt following the hips. Nothing to do |
| Alastor | no eyes; something wrong with the hair | **neither, and not fixable from here.** His materials and textures are correct and the maps are in the built file: `aleyes.png` plainly contains a pink iris with a black pupil. His eye geometry's UVs do not land on it — the eyes render as flat pink ovals and the pupil sits as a stray mark BESIDE the left eye. A source-model UV fault; it needs hand UV work, not a pipeline rule |
| Elite Terrorist | right hand's fingers crunched | one hand posed, the other not -- the asymmetry the finger-relax check looks for |
| Batman | every texture misplaced | **does not reproduce.** He has exactly one base colour map, so no pairing can be wrong; his rebuild is identical to the installed build to the triangle (18,818) and renders correctly — grey suit, black cowl and cape, bat symbol, gold belt. His metal/rough both take the ORM atlas, which is what glTF wants (G rough, B metal). Needs re-checking in game before more is spent on it |
| Gadget Hackwrench | eyeballs and teeth do not move; some hair static | measured: her eyes are bone-parented to `MCH-eye.L/R`, which the export drops because they do not deform, so the weight landed on an invented bone at the root |
| Joker | a pistol orbiting him; parts of the suit unrigged | **both fixed.** The pistol is 262 verts on a bone called `Gun_joker`, inside his one mesh with his one material: `VRM_DROP_ISLAND="Joker=Gun_joker"`. The suit was the orphan-bone case |
| Peach | eyes missing; dress springs so reactive her legs clip through it | **BOTH FIXED 2026-11-11, and neither was what the report implied.** The eyes are the alpha fault: her eye is a STACK of meshes from a Smash rip -- `Peach_eye` is a blank white sclera with no iris, `Peach_Blink_Ottotto` is the iris and `Peach_Blink_VoiceA` is the eyelid-and-lash plate that fills a rectangular hole in `Peach_faceN` -- and all three shipped `OPAQUE`, so the top layer drew as a solid plate. The skirt is NOT too reactive: her skirt chains are stiffer and more damped than her hair's (0.85/0.80 against 0.60/0.45). They are UNGUARDED -- eight of her nine chains hang around her thighs and she had two colliders, both on her torso. See below |
| Link | eye textures misplaced; still holding the master sword and shield | **both fixed.** His rig has bones named `Sword` and `Shield`, so `VRM_DROP_ISLAND="LinkEquipment=Sword+Shield"` takes 41 islands and leaves `Fourreau`, his scabbard, on his back. His eye material `Material.003` was taking the body atlas while `Eye.png` sat unused beside it |
| Shadow | eyes use the blink/closed frame of the atlas; fingers do not move | an eye atlas with the wrong frame pinned, and ~~finger bones that are mapped but not weighted~~ **corrected 2026-11-11 by `bundle_audit.py`: he has ZERO finger bones in his humanoid map**, and 21 humanoid bones in total against a typical 52. The symptom was right, the stated cause was wrong |
| Skibidi Toilet | is a man, with no toilet | the exclude that drops the toilet shell (it swamped the model) drops the character's defining feature and leaves the body that was inside it |

### Two colliders was never enough, and nothing counted

Peach's "dress so reactive her legs clip through it" is not a spring-parameter fault. A VRM spring
joint is deflected by one thing: a collider attached to its own chain. **The body's geometry is
invisible to the simulation.** `vrm_colliders.fit` placed a head sphere and a torso capsule and
nothing else, so a skirt hanging around the thighs had nothing to push it aside and the legs
walked straight through it. Her skirt chains are *stiffer* than her hair's.

`cloth_collide_installed.py` counts it across all 65. Before this round:

> **107 of 422 spring chains, across 18 characters, sat nearest a body part carrying no collider.**

The reference is in the same folder and is not ours. The downloaded VRoid bundles —
**Harq Alkahana, Inforder Trogen and both Hatsune Mikus — each carry 28 colliders** across arms,
legs and torso, and all four come back with zero unguarded chains. Adachi Rei carries 16. Two was
never a reasonable number; it only looked like one because nothing counted.

`vrm_colliders.fit` now adds a capsule per arm and leg bone — upper arm, forearm, thigh, shin,
eight more, ten in all. Three things made it safe to do:

- **The axis is the BONE, not the geometry.** Capsules drawn between bone heads meet at the elbow
  and the knee with no gap. Two independently geometry-clipped capsules would leave one, and a gap
  at the knee is exactly where a hem slips through.
- **The radius is the median distance of the flesh that bone carries**, the same rule the torso
  capsule already used, so it works from Yoda to Alcina without a hardcoded number.
- **The existing clearance guard does the rest.** A collider that CONTAINS a spring joint ejects it
  on frame one — the fault that ballooned Gadget's hair. Measured before writing any code: on
  Peach, Power Girl, Chibi Rem and Batman every limb had room (her thigh wants 0.061 and her
  nearest skirt joint sits at 0.114), and only Jinx clashed, her braids at 0.061 against an 0.083
  thigh. The guard shrinks that capsule to clear them. After the rollout, **no joint on any of the
  nine rebuilt characters is inside any collider**.

**`fit` did not do what its own docstring said.** It claimed "safe to call twice: an existing group
made by this function is replaced rather than added to". There was no removal code at all, so a
second call would have doubled every collider. Nothing had ever called it twice, so the claim was
never tested and read as a guarantee. Re-fitting is the first thing that needed it; it now clears
its own previous group, and `add_colliders.py VRM_RECOLLIDE=1` re-fits a built VRM in place.

Nine characters fixed and installed — Peach, Batman, Chibi Rem, Gwen Stacy, Jinx, Link, Power Girl,
Prix, Sayuri — each verified three ways: the round trip lost nothing (triangles, meshes, materials,
images and springs all unchanged), the installed bundle is identical to its backup on every counted
object type except three collider gizmo transforms, and five were podium-rendered. **97 → 58
unguarded chains.**

What is left, and why each is left:

| character | chains | why not fixed |
|---|---|---|
| Kaiser Aufhänger (36), Adachi Rei (2) | 38 | downloaded bundles, not built here. Kaiser's own author covered his arms and torso and not his legs |
| Aiko, Scott Hall, Shadow | 11 | **zero colliders** — the original collider rollout never reached them, and no `.vrm` for any of them survives on this machine |
| Gadget Hackwrench, Pomni | 4 | they have a `.vrm`, but `identify_build.py` says it is **not what is installed** (57 and 5 rotation mismatches). Installing it would swap the character, which is the trap this project has already been caught by twice |
| ~~Xenomorph~~ | ~~5~~ | **DONE 2026-11-12** — his source FBX survived. See below |

Installed total after that: **53 of 391 across 7 characters**, and every one of the seven is in
one of the three rows above.

### The Xenomorph: his tail is on his spine, so he had no torso collider

Rebuilt from `xeno/source/Xenomorph Default.fbx` at `2.40 xeno`, which reproduces the installed
bundle exactly — **171 bones matching to zero length and zero rotation mismatches**, 51,548
triangles, 1 mesh, humanoid 46/46 — and he had no `rollout/out` reference, so that rig comparison
is what stands in for the triangle gate. Two things had to be recovered rather than guessed:

- **His spring regex.** The default finds his tail and nothing else; his four dorsal tubes need
  `BackTube` appending to it, or he comes back with 1 chain against the installed 5. And
  `(BackTube|TailRoot)` is *not* enough — the regex has to match a chain's whole run of bones, not
  just its root, so `TailRoot` alone produced the four tubes and **lost the tail**.
- **A real defect in the collider guard**, which is the part worth keeping.

The guard refuses to let a collider contain a spring joint. His tail is rooted on his spine, so
`XenosBiped_TailRoot_SHJnt` sits at **exactly 0.0000 m from the torso capsule's axis** — and the
guard dutifully shrank the capsule to 0.000, `add` dropped it as degenerate, and he ended up with
eight limb colliders and **nothing at all on his torso**, which is where his lower back tubes hang.

The anchor is now excluded from the guard, and this is checked rather than assumed. From the code
the game actually runs — `UpdateFastSpringBoneJob` and `FastSpringBoneBuffer` in
`com.vrmc.gltf` — a spring is built as `joints.Length - 1` logic elements, each taking `joints[i]`
as its head and `joints[i+1]` as its tail, and collision moves `nextTail` only. **`joints[0]` is a
head and never a tail, so no collider can move it.** Guarding against it protected nothing and cost
the collider; a joint sitting exactly on the axis has no outward direction to be ejected along
either.

With it excluded his torso capsule comes back at 0.041 (shrunk from 0.122 to clear his next tail
joint at 0.043), all five chains are guarded, and the nearest **simulated** joint to any collider
surface is +0.002 m.

Both cloth checks now skip the anchor when measuring that distance, for the same reason: a tail
rooted on a spine is inside the torso capsule by design, and reporting it would bury the case the
number exists to catch — a *simulated* joint inside a collider, which is ejected on frame one.

### The second pass, and the clear that still was not clearing

Every character fitted before that change is carrying colliders that its own cloth had crushed,
so all ten were re-fitted. **The clearest case is Batman**: twelve cape chains are anchored on his
pelvis, every one of those anchors sits on the pelvis capsule's axis, and between them they had
shrunk it from 0.112 to **0.048** — his cape is the one thing that needs a pelvis to collide with,
and his cape is what deleted it.

| character | biggest gain | |
|---|---|---|
| Batman | `fml_un_C_pelvis_att` | **+63.7 mm**, 0.048 → 0.112 |
| Peach | `_03_-_HipN` | **+48.2 mm**, 0.055 → 0.103 |
| Link | `Pelvis` | +22.0 mm, 0.106 → 0.128 |
| Sayuri | `CC_Base_Head` | +20.0 mm, 0.081 → 0.101 |
| Chibi Rem | `DEF-spine` | +11.3 mm |
| Alcina | `spine` | +8.0 mm — but her only chains are chest chains, so her colliders attach to nothing and reinstalling her changes nothing observable. Left alone |
| Gwen Stacy | `Hips` | +3.1 mm |
| Jinx, Power Girl, Prix | — | **unchanged** (under 2 mm): nothing that constrained them was an anchor |

Six reinstalled, each verified: triangles identical, round trip lost nothing, **no simulated joint
inside any collider** anywhere in the set, closest approach +0.001 m, and four podium-rendered.

**The re-fit found one more defect in the clear, and only the SECOND re-fit could have.** The
first version removed colliders by matching the group's stored `collider_uuid`. A round trip
through the exporter and back does not preserve every uuid: on Peach, six of her ten were named by
her group and four were not, so four survived, ten fresh ones were added, and the file came out
with **fourteen colliders** — the doubling this clear exists to prevent, wearing a different hat.
Nothing in the first pass could have shown it, because nothing had been fitted twice.

It now sweeps up any collider that no *remaining* group still references, which does not care how
the uuid bookkeeping came out and keeps anything an author's own group still points at. All ten
then cleared 10 and produced 10.

### Chest chains are unguarded on purpose

Chest springs sit ON the torso, so handing them the torso capsule would push them out of the body
they belong to. `vrm_colliders.CHEST` skips them and both cloth checks now skip them too — without
that, the sweep reported Alcina Dimitrescu's `breast.L` and `breast.R` as faults, which is true and
is not a defect. A check that flags a decision as a fault teaches the reader to skim its output.

### The alpha gate refused the one provenance nobody could argue with

`VRM_CUTOUT_INFER=1` infers a cutout from a base map's own alpha, but only for a map the material
can claim — authored in the file, matched by mesh stem, or matched by name. Peach printed *nothing*
under it. Every one of her maps is packed inside the `.fbx`, and when the source material already
has an image wired into Base Color, `already_good` keeps it and sets `_base_authored` — but never
sets `base_from`, which stays `None`. So the strongest provenance there is, the author's own
wiring, was the one case the gate excluded. Her iris and eyelash layers shipped opaque over her
eyes because of it.

Fixed, and then immediately shown to need a narrower lever. With the gate repaired, the global
inference took seven of Peach's materials, and two of them were wrong: her crown's alpha is an
**outline**, so masking it carved the jewel out of its setting and left a wire ring. "77.4% solid"
says nothing about *which* 77.4%. `VRM_CUTOUT_MATERIALS="a;b;c"` asks for the same inference on
named materials only, which is what a character needs when the sweep is right about some of its
materials and wrong about others.

### A cutout changes the SHADING MODEL, and on a big surface that shows

MToon is enabled only for materials that need a cutout, deliberately — swapping a whole character's
shading model is a much larger change than the defect warrants. The cost is that the character ends
up with two shading models, MToon on its cutouts and standard PBR on everything else. On hair
cards, eyelashes and tear lines nobody notices.

On Peach it landed on half her face. `Peach_faceN` carries a rectangular hole that
`Peach_Blink_VoiceA` fills, and the moment the filling plate became a cutout it turned unlit while
the face around it stayed lit — a tan plate on a cream face with a hard polygon seam across her
brow. The eyes were fixed and the face was worse, and **only a render showed it**; every count said
the build was identical.

`VRM_MTOON_ALL=1` puts the whole character on one shading model, which is the answer when a cutout
shares a continuous surface with an opaque material. It is opt-in, because for most characters the
swap is the larger change. Peach is built with it, and her podium render has irises, an even face,
her crown jewel and a scalloped lace hem.

`RENDER_HIDE=<substring>` and `RENDER_ONLY=<substring>` in `render_closeup.py` are what named the
plate. Hiding a mesh tells you what was *behind* it; rendering it alone tells you what it *draws*,
and only the second answered the question — her face is six overlapping expression meshes from a
Smash rip and reasoning about the stack produced two wrong answers before the renders settled it.

### Sayuri: the sweep found her, then under-reported her by a factor of five

**FIXED and installed 2026-11-11.** Nobody had reported Sayuri. `alpha_sweep.py` named her for one
material, `Lace`, and the lace *was* solid — but a render of the installed build showed something
far worse that the sweep had said nothing about: **both of her eyes were buried under solid black
slabs**, and a pink rectangle sat on her cheek.

Her source has **eight dedicated `*_Opacity.png` maps** — hair, lace, cloth, eyelashes, moles,
bikini, clock, scrunchie — and her build predates the alpha fix, so every one of them was dropped.
Thirteen materials, all `OPAQUE`. The eyelash and eye-shadow quads therefore drew as opaque black
rectangles over her eyes; the Moles decal, which is two soft dots on a transparent map, drew as a
patch of pink.

Rebuilt with the recovered command plus two additions:

```
build_vrm.py -- "Sayuri dans.fbx" <textures> 1.70 cc_base Sayuri <out.vrm> 1024 '' '' '^Hair$'
VRM_BREASTRIG=1 VRM_TEX="Eye_Shadows=Eyelashes_Opacity.png:alpha"
```

`VRM_BREASTRIG=1` because the recovered ARGV is the ORIGINAL build and the installed one has her
chest rig — without it the rebuild came back with 4 spring chains against her 6, which is the sort
of silent loss a triangle count cannot see. The `VRM_TEX` pin is because `Eye_Shadows` shares
`Eyelashes_Diffuse` with `Eyelashes` but the opacity picker gave the single `Eyelashes_Opacity.png`
to the material whose name matched, leaving the other one opaque — half a fix, and the half that
still covers an eye.

Nine opacity maps baked, 91,632 triangles unchanged, 0 unguarded chains, no undriven weight, and
the podium render has eyes, lashes, hair that reads as strands and a sheer lace skirt. Her chest
springs come out at 1.00/0.90 where the installed build had 0.85/0.60 — that is the current code's
scale-aware value, not a loss.

**The lesson is about the instrument.** The sweep's single hit was the least important of her five
faults. Its gate was `build_vrm`'s rule for deciding a *mask* — mostly two-valued, neither almost
all clear nor almost all solid — and an eyelash alpha is **feathered** (46.7% clear, 0.3% solid),
so it failed the test. So did her hair, and so did the mole decal at 95.0% clear. "Is this a clean
mask?" and "does this material ignore real transparency?" are different questions, and only the
second one is the defect. `alpha_sweep.py` now reports both tiers, which takes it from 12 materials
across 6 characters to **24 across 10**. Verified both ways on her: the pre-fix build flags all
seven of her materials, the rebuild comes back clean.

Ignore `[VRM Add-on:ERROR] Unexpected alpha clip input node type` on this character — fifteen of
them, all emitted during the FBX import before the builder touches a material, from alpha-clip
inputs the Character Creator export left wired to nothing. Peach and Heels produce none.

### Alcina: the lashes were real, and they are the least of what is wrong with her

**Her eyelashes and hair are cutouts as of 2026-11-12, and she is still a white statue.** Both
halves of that matter.

The sweep's two hits were right. `CILIOS` is Portuguese for eyelashes and `CABELOO_preto_1` is a
hair-card atlas, and both shipped OPAQUE: her lashes drew as **two thick black slabs over her
eyes**. Rebuilt with `VRM_CUTOUT_MATERIALS="Material.005;Material.006"` they are lash strands and
her eyes are visible. 350,162 triangles unchanged, same 12 meshes, 13 materials and 2 chains.

Getting there needed **two more holes in the cutout gate** closed, both the same shape as the
`_base_authored` one above — the gate kept refusing the provenances that are hardest to argue with:

- **A `VRM_TEX` override set neither `base_from` nor `_base_authored`.** An operator naming the map
  by hand is the strongest signal there is, and it was invisible. Alcina's hair is pinned that way.
- **The probe measured a BLURRED COPY of the alpha.** It did `image.copy()`, `scale(96, 96)` and
  read that — and Blender's scale is a *filtered* resize, so it averages. Averaging is the one
  operation guaranteed to destroy the property being tested: a two-valued mask blurred to 96×96
  stops being two-valued, and the finer and sparser the mask the worse it gets. Eyelashes and hair
  cards are exactly that. Measured on `CILIOS`: **0.875 at full resolution, which passes, and 0.790
  after the resize, which fails.** Her hair atlas survived only because it is denser (0.930 against
  0.830). The probe now reads the full-resolution alpha through numpy.

  This is also why `alpha_sweep.py` and the builder could disagree: the sweep samples with NEAREST,
  which preserves extremes, and the builder averaged. Two instruments, the same written rule,
  different answers.

**Now the part the alpha fix does not touch.** Alcina renders as an untextured white figure, and
that is her archive rather than the build: **every colour map in it is a grey noise field.**
`(null)_Base_Color`, `Material.014_Base_Color` and `None_Base_Color` are all noise, and they are
what her body, dress, hat and train use. The only real images in the folder are
`CABELOO_preto_1`, `CILIOS` and `smoke.png`. The crosshatch relief across her cheek and jaw is
`(null)_Normal_OpenGL`, another noise field, used as her face's normal map. Her appearance in
`Alcina102.blend` must come from material node setups that no glTF export can carry; recovering it
means baking those to textures in Blender, which is a different job from anything the pipeline
does today.

**And at 2.9 m her head is above the character-select camera.** `YargSceneShot` uses
`Camera.main` — the scene's own camera, not a fitted one — so the podium shot crops her at the
shoulders, and that is the game's framing rather than the harness's. Her height is canon and must
not be changed, so the lash fix is correct and invisible where players pick her. Worth knowing
before spending anything more on her face.

One change in the rebuild that is **not** from this work: `Material` (her neck, `Body1.002`) now
takes `Material.014_Base_Color` where the installed build took `Material`. Both are grey noise and
the renders are identical, and the control build made before today's two edits already shows it —
so it came from a pipeline change between her 11-09 build and now, not from these.

### The eye hits: one real defect, five that would have done damage

Six of the sweep's hits were eye-adjacent, on The Rock and Gordon Freeman. **One was real.** The
others are the case this whole section keeps circling, and this time there are numbers for it.

**Gordon Freeman's glasses were two solid white panes over his eyes.** `lens` carries a base map
whose alpha has **no extremes at all** — 0.0% fully clear, 0.0% fully solid, median 63/255 — which
is to say a uniformly semi-transparent pane. That is what a lens is, and *no cutoff expresses it*:
masking at 0.5 would punch a mottled hole, and leaving it opaque is what shipped.

So there is now a third lever, `VRM_BLEND_MATERIALS="a;b"`, the sibling of
`VRM_CUTOUT_MATERIALS`. Opaque, cutout and blended are three different things and only two of them
could be asked for. Rebuilt with it: 7,169 triangles unchanged, 4 meshes, 7 materials, and his eyes
are visible through his glasses on the podium.

**The Rock's `eye_ov` is a false positive.** His eyes render correctly as installed — brown irises,
clean sclera, no grey disc. Rendering him before touching anything is the only reason nothing was
changed.

**And three of Gordon's hits would have broken him**, which is worth being exact about because the
sweep cannot tell and the numbers can:

| map | alpha | what honouring it would do |
|---|---|---|
| `lens` | median 63/255, no extremes | **the fix.** A 25%-opaque pane |
| `eye-iris-green.tga` | median 113/255, black **exactly on the iris disc** | make his irises invisible. The alpha is a specular mask, not opacity |
| `onefreeman` (two materials) | mean **0.1/255** | erase his entire HEV suit |

The rule that comes out of it: **in a game rip an alpha channel is as likely to be a specular mask
as an opacity map.** Source engine stores an environment-map mask there as a matter of course, and
Gordon is a Half-Life 2 model carrying all three kinds at once. The way to tell is not the
histogram — it is to ask what the texture is FOR and whether honouring its alpha would erase that.
An alpha that is black precisely where the subject is, is not an opacity map.

Still open on him, and not touched: his irises render pale, which looks like his eye UVs not
landing on the iris disc in `eye-iris-green.tga` — the same family as Alastor's UV fault, and not
fixable from the pipeline.

### The rest of the list was false positives, and fixing that is the useful part

Six characters were left after the eyes. **A render of each, as installed, showed every one of them
to be correct.** Killer Clown's red and blue eyes, Yoda's eyes and his fine white hair strands,
Doom Slayer's helmet — all fine. Nothing was changed on any of them.

The reason they were flagged is worth having, because it is a property of the instrument rather
than of the characters: **an atlas is mostly empty space between its UV islands, and that empty
space is usually transparent.** Measured over the whole image, a perfectly ordinary body atlas
looks exactly like a cutout. That is what put Gadget Hackwrench's `Body` map on the list three
times, and Jinx's merged diffuse, and Killer Clown's sheet of eye decals.

`alpha_sweep.py` now rasterises each material's own UV triangles and measures the alpha **only
where that material's geometry actually lands.** Two materials sharing one atlas get different
numbers, which is the point of an atlas.

| | whole image | under its own UVs |
|---|---|---|
| Killer Clown | 1 material | **clean** |
| Doom Slayer | 2 materials | **clean** |
| The Rock | 1 material | **clean** |
| Gadget Hackwrench | 4 materials | 1 material |
| Jinx's merged diffuse | 24.4% clear | 6.6% clear |
| **Sayuri, pre-fix (control)** | 7 materials | **7 materials** |

Across the set that is **24 materials on 10 characters down to 13 on 6**, with the control
unmoved — and the three it dropped to clean are the three a render had already cleared, which is
the agreement worth having between an instrument and an eye. It also dropped The Rock's `eye_ov`
on its own, independently of the render that had already acquitted it.

What is left is now all known: Gordon's specular masks and his suit (100.0% clear under its own
UVs — the suit's geometry lands entirely on transparent alpha, so honouring it would erase him),
Peach's crown and hair, Prix's wrong-atlas trap, Yoda's two, and Gadget's goggles, whose `.vrm` is
not the build that is installed. **The sweep has been run to ground; there is no untried candidate
left on it.**

### `alpha_sweep.py`'s other hits, and which of them to believe

With both tiers, **24 materials across 10 characters**. Sayuri is done; the rest, with what the
numbers are worth — and none of these has been rendered yet, so each row is a candidate and not a
finding:

| character | material ← map | alpha | reading |
|---|---|---|---|
| ~~Alcina~~ | `Material.006` ← `CILIOS`, `Material.005` ← `CABELOO_preto_1` | 87.1% / 88.7% clear | **DONE 2026-11-12.** Both real; see above |
| ~~The Rock~~ | `Material #30` ← `eye_ov` | 1.2% clear, 84.8% solid | **CHECKED 2026-11-12: false positive.** His eyes render correctly as installed |
| ~~Gordon Freeman~~ | `lens` | 0.0% clear, 0.0% solid | **DONE 2026-11-12.** His lenses were solid white panes; now blended at 25%. See above |
| Gordon Freeman | `eye_r`, `eye_l` ← `eye-iris-green.tga` | 7.5% clear | **do not touch.** The alpha is black exactly on the iris disc — a specular mask. Honouring it makes his irises invisible |
| Killer Clown | `eyes` ← `eyes_base_color` | 95.3% clear | over the cap; a mask would erase them |
| Gordon Freeman | `HEV`, `HEV_Mesh` ← `onefreeman` | **99.9% clear** | do not touch. An alpha that is essentially all transparent erases the mesh |
| Yoda | two materials | 0.0% and 65.9% clear | unexamined |
| Peach | `_`, `_.017` ← `1_model0.png` | 4.4% clear, 64.1% solid | her hair, a vertical gradient. Deliberately left opaque in the shipped build |
| Peach | `_6`, `_6.002` ← `0_model46.png` | 67.3% clear | the crown. **Tried and rejected** — its alpha is an outline and masking it carved the jewel out |
| Gadget | `Body` on three materials, `Jumpsuit` | 31.5% / 52.1% clear | a body atlas. Masking a body map punches holes in a body |
| Jinx | `12_meshes_Merge_Diffuse` | 24.4% clear | a merged diffuse; the clear region is likely unused atlas space |
| Doom Slayer | `doomslayer_hair` ×2 | 88.9% clear, **0.0% solid** | no fully-opaque pixel at all |
| **Prix** | `Hair`, `lambert8` ← `CN_F_HAIR_110_hair` | 58.6% clear | **a trap this project has already sprung.** That is a DIFFERENT hair model's atlas, reached by the loose global-pool fallback; its alpha "cut away the wrong regions and left her bald". The fault is the texture's provenance, not its channel |

Pomni is the other reason this prints instead of acting: her eyes carry a two-valued alpha that is
not a cutout at all, and inferring one made them see-through in game while every render and count
said she was fine.

### One cause under six of the reports: a bone nothing drives

VRM moves the 52 humanoid bones and the spring chains, and nothing else. Every other bone
follows only if it is a **descendant** of one of those. A deform bone parented outside that
hierarchy therefore never moves at all, and the vertices on it hold their bind position while
the character walks away from them.

Nothing counts it. The mesh is present, the skin is present, every vertex carries full weight,
the humanoid map is complete, the renders look right because at rest a dead bone and a live one
are identical. Measured:

> **Re-measured 2026-11-11 with `pose_check.py`, and this table is now STALE.** Posing the
> humanoid bones and measuring per-vertex displacement, every character below comes back
> clean — every mesh moves and no mesh has a static region above 1 mm. The detector is
> verified in both directions (`POSE_CONTROL` unbinds a mesh and it is flagged;
> `POSE_STATIC_EPS=0.05` makes the partial branch fire on Judy's hip vertices), so the zero
> is a real zero and not a probe that never ran. Two caveats: the Gadget VRM tested is newer
> than his installed bundle, and Sonic cannot be tied to an installed bundle at all — all
> five of his candidate VRMs carry identical geometry, since his failure was the rig.
> See *Posing is the only check that can see a detached part* in `docs/character-models.md`.

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

### Weight on a bone nothing drives, in four flavours

Eight of the twenty-four reports above are one fault wearing four hats, and a sweep over
every `.vrm` built here found **six more characters nobody has reported yet**: Gwen Stacy,
both Clone Troopers, Yoda, Anakin and Junio Sonic.

The test is three lines and should have existed from the first character: take every bone that
deforms geometry, walk up its parents, and assert it reaches a humanoid or spring bone.
`scratchpad/drivers.py` does exactly that against the exported file and prints the percentage.

| flavour | what it looks like | what fixes it |
|---|---|---|
| **Orphan bone** — a deform bone parented outside the humanoid hierarchy | Lola Bunny: 31% of her body, including her whole head | re-parent to the nearest humanoid bone, keeping world position |
| **No weight at all** — the glTF exporter invents `neutral_bone` at the root for unweighted geometry | Gadget's teeth; four cape vertices on Mando | bind to the nearest humanoid bone |
| **Non-deform bone** — the VRM export writes only bones with `use_deform`, and Rigify's ORG- and MCH- control bones have it off | Gadget's eyes, bone-parented to `MCH-eye.L`; 152 face groups on Jessica | move the weight to the nearest ancestor that will be written, or failing that the nearest humanoid bone |
| **Above the humanoid root** — hips is the root, so a bone *above* it is never driven either | Miku's `Bip01 Pelvis`, 985 vertices | move the weight **down** to the root. It cannot be re-parented: every candidate is its own descendant |

The fourth one is the one to be careful of. The first version of the orphan fix adopted Miku's
pelvis to `Bip01 R Thigh`, one of its own grandchildren; Blender will not build that cycle, so
the re-parent silently did nothing while the log announced the fix. **The measurement did not
move, and that is the only reason it was caught.**

None of this is visible to any count. The mesh is present, the skin is present, every vertex
carries full weight, the humanoid map is complete, and at rest a dead bone and a live one draw
identically.

### The rest of the list is not blocked, and the claim that it was is the same mistake twice

This section first said the remaining twelve characters could not be rebuilt, because only 23 of
the 66 had a build command recoverable from a **log** in this workspace. That was true about logs
and false about the characters: **the rig-family table below already records a recipe for every
one of them.** Family, height and exclusions, written down at the time.

It is the Jessica Rabbit error again, in the same document, three hours later — reaching for
the place the answer was last found instead of the place it is kept, and then writing down the
absence as a property of the world. Two tables in one file, and the one that was searched is the
one that did not have it.

What the recovery pass is actually worth is **cross-checking** the table rather than replacing
it. Reading height and rig family back out of each installed `.yargchar` agrees with the written
recipe on all twelve, to the centimetre:

| character | recovered | table | character | recovered | table |
|---|---|---|---|---|---|
| Joker | 1.85, maxbiped | 1.85 maxbiped | Peach | 1.70, smash | 1.70 smash |
| Alastor | 1.95 | 1.95 mixamo | The Rock | 1.96 | 1.96 mixamo |
| Gordon Freeman | 1.80, valvebiped | 1.80 valvebiped | Yui Suzukaze | 1.60 | 1.60 mixamo |
| Batman | 1.88, multiversus | 1.88 multiversus | Skibidi Toilet | 1.60, valvebiped | 1.60 valvebiped |
| Link | 1.65 | 1.65 linkoot | Elite Terrorist | 1.83 | 1.83 mixamo |
| Shadow | 1.05 | 1.05 sonicforces | Pomni | 1.70 | 1.70 pomni |

Where the recovery says "unknown" — Alastor, Elite Terrorist, The Rock — the bones are Mixamo's
with the prefix stripped (`Hips`, `LeftArm`, `LeftHandIndex1`), which the family auto-detects and
the table already names. Source archives for all twelve are present, extracted, and named in the
table.

Joker is worth keeping in view: he measures **undriven weight** on the sweep above, so he is in
the family this round fixed, and nothing was ever stopping him being rebuilt to collect it.

Measured while they were in front of me: **all twelve are fully opaque**, every material. Several
of the reports are eye faults — Alastor has no eyes, Pomni's are mismapped, Peach's are missing,
Shadow's are stuck on the blink frame — and eyelashes, eye occlusion and tearlines are exactly
the cards a cutout is for. Expect the inference below to change several on the first rebuild.

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

**Re-swept on 2026-11-12 with `audit_all.py`, and the order changed.** Three classes turned out
to be closed, one turned out to be far larger than anyone had counted, and the ordering that
falls out of that is by *characters fixed per change made* rather than by severity:

| # | class | scope | state |
|---|---|---|---|
| 1 | a soft alpha shipped as a hard cutout | **20 materials, 6 characters** | one exporter change, below. Heels' eyelashes are **99.6% clipped away** |
| 2 | Kaiser Aufhänger has no leg colliders | 36 chains, 1 character | **70% of every unguarded chain left in the set** is this one character |
| 3 | zero colliders, no `.vrm` | 11 chains, 3 characters | **blocked, and not by effort.** Editing a loaded bundle works; writing it back does not — `BackgroundHelper.Export` exits 0 and produces a 2,552-byte shell with no meshes in it. See `docs/character-models.md` |
| 4 | opacity in an opaque material (`UNUSED`) | 45 materials, 17 characters | needs a render each; roughly half will be specular masks |
| 5 | no bound visemes | 52 of 65 | mostly blocked on a source file that does not exist |
| 6 | Jessica Rabbit is 3.7% too tall | 1 character | cosmetic |
| — | floating prop setting the height | **0 of 65** | **CLOSED** — item 2 below |
| — | bent or asymmetric limbs | **0 new** | **CLOSED** — every flag is already explained in `docs/character-models.md` |
| — | missing animation / finger mapping | **0 new** | **CLOSED** — same |

The reasoning behind each is in `docs/character-models.md`; what follows is the older list,
which items 1-3 above now sit in front of.

0. **Rebuild the six characters whose soft alpha ships as a hard cutout.** Still open, and the
   reason it was briefly closed is worth keeping: this entry said "NOT POSSIBLE — none of the six
   can be rebuilt", which was **wrong**. Every source archive is in `%USERPROFILE%\Downloads\`,
   named after the model listing rather than the character — `sayuri-dans.zip`,
   `alice-ivy-animated-by-jungle-jim.zip`, `valve-gordon-freeman-model.zip`,
   `topless-sexy-girl-with-heels.zip`, `alcina-dimitrescu-resident-evil-village.zip`. The search
   that "proved" they were gone looked for the file *inside* each archive, which is what the
   recipe rows name, and a file inside a zip matches no `find`.

   **Search for the CONTAINER, not the content**, and sort by modification time: the whole set
   was downloaded within a few hours of 2026-11-07, so one known archive's timestamp finds the
   rest. Ariel is the only one with no archive, and her row already says she was recovered from
   her own `.yargchar`.

   What IS true: the three surviving `.vrm` files (Heels, Ariel, Alcina) are OLDER than what is
   installed — 0 length and 0 rotation mismatches against a sub-90% name overlap, the same rig
   *minus* the spring bones the 11-11 chest rig added — so re-exporting a `.vrm` is not a route.
   A rebuild from the archive is.

   Until then, four of the six carry the lowered-cutoff stopgap below. **That is not the fix** —
   a rebuild with the corrected exporter gives them real alpha blending.

   Two consolation routes were then measured, and only one of them works. **Patching the
   installed bundle's material to a real blend does NOT work**: every number comes back right and
   Gordon's lens renders as a solid white pane, worse than the 79%-clipped cutout it replaced.
   **Lowering `_Cutoff` does work**, because it changes no shader variant — see
   `patch_alpha_blend.py` and the write-up in `docs/character-models.md`. It cannot give a
   feathered edge, and it needs a render and a per-material `--keep` each, because one value does
   not suit both an eyelash and a hair atlas.

   **Four of the six are installed, as of 2026-11-12**, by lowering `_Cutoff` to 0.16 on the
   materials the threshold was destroying, each one rendered before and after on the podium:

   | character | materials changed | result | backup |
   |---|---|---|---|
   | Alice Ivy | `AliceIvy_5` | solid black bars over both eyes become real lashes — the biggest visible gain in the set | `.precutblend` |
   | Heels | `Heels_5`, `_18`, `_19`, `_13` | lashes appear, hair fuller, tear line kept by the cap (0.042) | `.precutblend` |
   | Sayuri | `Sayuri_8`, `_9`, `_10`, `_11` | modestly heavier lashes, slightly fuller hair | `.precutblend` |
   | Ariel | `Ariel_20`, `Ariel_25` **only** | lashes fuller. Her `EyeMoisture` and `Cornea` are deliberately excluded — at 0.16 they draw an opaque white film and **erase her irises** | `.precutblend` |
   | Alcina Dimitrescu | — | not installed: no visible change, her head is above the select camera at 2.9 m | — |
   | Gordon Freeman | — | not installed: a lens is a pane, and no cutoff expresses one. Needs the blend, so needs a rebuild | — |

   **Do not rank this work by the clipped-ink number.** Alice Ivy was last of eleven by that
   measure and produced the most visible improvement; Alcina was second and produced nothing.
   How much of a texture a threshold destroys says nothing about how much of the *character* it
   destroys — that depends on where the material sits and whether the camera can see it.

   Per material, the share of the texture the 0.5 threshold threw away before this:

   | character | material | texture | clipped |
   |---|---|---|---|
   | Heels | `Heels_5` | `Std_Eyelash_Diffuse_OPA` | **99.6%** |
   | Alcina Dimitrescu | `AlcinaDimitrescu_11` | `CILIOS.png` | 96% |
   | Ariel | `Ariel_10` | `EyeMoisture_BaseColor` | 95% |
   | Ariel | `Ariel_20` | `Ariel_Eyelash-Brow_…` | 86% |
   | Sayuri | `Sayuri_8`, `Sayuri_11` | `Eyelashes_Diffuse_OPA` | 85% |
   | Gordon Freeman | `GordonFreeman_4` | `lens.png` | 79% |
   | Heels | `Heels_18`, `Heels_19` | `front_hair`, `tail` | 56% |
   | Alice Ivy | `AliceIvy_5` | `Std_Eyelash_Diffuse_OPA` | 45% |
   | Sayuri | `Sayuri_10` | `Hair_Diffuse_OPA` | 40% |
   | Sayuri | `Sayuri_1` | `Lace_Diffuse_OPA` | 32% |
   | Ariel | `Ariel_25` | `Ariel_Hair_Cap_…` | 25% |

   Back up each installed `.yargchar` first, and look at each one before and after — a material
   that goes from cutout to blend changes sort order as well as edges, and hair that sorts wrongly
   against itself is its own defect.

0b. **Triage the 45 `UNUSED` candidates, strongest first.** These are opaque materials whose base
   map carries alpha, and roughly half of such hits have historically been specular masks, atlas
   padding, or already correct — so this is a list to *look at*, in this order, not a list to fix.
   The ranking is by two things the sweep can see: whether the alpha is two-valued (`mask`, which
   is what an opacity map looks like) and whether the filename admits what it is.

   | strength | character / material | why it ranks there |
   |---|---|---|
   | **strong** | Shrek `t_Shrek_alpha_c` | the filename says `alpha`, and it is a clean mask: 43.7% clear, 56.3% solid, 0.0% between |
   | **strong** | Gadget Hackwrench `Body` ×4 + `Jumpsuit` | mask, 31.6% clear; five of her six materials. She also has 2 unguarded chains, so she is worth one visit |
   | **strong** | Killer Clown `eyes_base_color` | mask, 95.3% clear — an eye plane on a mostly-empty atlas is the Peach shape exactly |
   | **strong** | Steve `Diffuse` | mask, 17.1% clear. Minecraft skins use alpha for the **hat/overlay layer**; this is the one hit where the format itself predicts real opacity |
   | **strong** | Doom Slayer `doomslayer_hair` ×2 | `soft`, 88.8% clear — a hair card with a feathered edge, which also means it wants BLEND and not a cutout |
   | **medium** | Jinx `12_meshes_Merge_Diffuse` | mask, 23.9% clear, but it is her ONE material for the whole character — masking it wrongly costs everything |
   | **medium** | Yoda `CHA_yodaEye_C`, Aiko `pf2001_C01`, Yui Suzukaze ×9 | masks on the right kind of part, no filename signal either way |
   | **weak** | Scott Hall `Hall_body_color` ×4 | 97.9% solid, 1.7% clear. A body atlas that is almost entirely opaque is what a specular mask looks like |
   | **weak** | Spider-Man PS `SMAdvanced_Gloves_D` | 95.5% solid, same shape |
   | **weak** | Shadow the Hedgehog ×4, Xenomorph `headcap` | Shadow's are `_d` diffuses from a Sonic-series rip; the Xenomorph's is **uniform** alpha (100% between the extremes), which no opacity map is and every gloss mask is |
   | **leave** | The Rock `eye_ov` | already investigated and retracted once. Do not re-open without new evidence |
   | **leave** | Prix `CN_F_HAIR_110_hair` ×2 | the only hair map in her folder belongs to a **different model**, reached by the loose fallback. Honouring its alpha leaves her bald |
   | **leave** | Gordon Freeman `eye-iris-green.tga`, `onefreeman` ×2 | measured specular masks. Honouring them hides his irises and erases his suit |
   | **care** | Peach ×4 | her five real cutouts are already in her recipe. The crown is deliberately NOT among them — its alpha is an outline, and masking it carves the jewel out |

   Nineteen of the 45 are in the `leave` or `weak` rows, which is the useful half of this exercise:
   the shortlist that is actually worth a render is about ten materials, not forty-five.

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
2. ~~Sweep the installed set for the floating-prop height bug.~~ **Done 2026-11-12, and the
   class is closed.** `height_check_installed.py` over all 65: **no character carries a mesh
   detached from its body**, and 51 of the 52 with a documented target height measure it to
   within 0.8%. The one exception is **Jessica Rabbit at 1.867 m against a documented 1.80**
   (+3.7%) — small, carried in from whatever exclude shipped her, and the only height finding
   in the set. Peacemaker himself now measures 1.850 exactly.
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
   - **Judy Hopps: the source in this workspace is not her, and the rebuild is not usable.**
     Settled by measurement rather than by size. Her geometry matches the installed character
     to 0.6% — 38,268 triangles against 38,044 — which looks like the same model, but her
     textures are a different set entirely: the installed build carries `Judy_A_01_Cloth_baseColor`
     and `Judy_A_01_Face_baseColor` at 512², the rebuild carries `Material_ColorMap` and
     `Material_NormalMap` at 1024². **Rendered, the rebuild is almost entirely white**: the
     maps are present and are not reaching the surface.
     She also exports 13 glTF texture ENTRIES for 2 images, so UniGLTF materialises seven
     copies of the same colour map and she lands at 14.2 MB against 2.3 MB installed.
     Her rebuild does fix two real things — the sides check reports "all 4 limb pairs are on
     the side their names claim", so this source has no mirrored rig, and the belt is attached
     — which makes her tempting and makes the white render the only thing standing in the way.
     **She is held back**; the installed build stays until a source is found that textures.
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
- `proportion_check_installed.py <yargchar|dir>` — are a character's limb SEGMENTS the right
  length relative to each other? Nothing measured this, which is how The Rock shipped with
  **gorilla arms** while passing every check here: `limb_check_installed.py` measures joint
  ANGLES (he reads `worst=0.38`, perfectly symmetric) and `height_check_installed.py` measures
  the TOTAL (1.960 against a documented 1.96). Both are right and neither looks at segment
  length. This reports each segment as a fraction of stature — foot bone to head bone, so it is
  rig-intrinsic — against the population median with a robust sigma, because half this set is not
  human and a deviation from anatomy is not a defect. Population, measured over 65: upperarm
  0.181, forearm 0.174, thigh 0.292, shin 0.286, shoulders 0.249, reach 0.938
- `scale_rig.py <in.blend> <out.blend>` — scales a rest skeleton onto its own mesh, about the
  hips, feet on the floor. **This step was documented for a year and existed in no script**: The
  Rock's row describes it precisely and then says "`fit_joints.py` does both", which it does not.
  It had been done by hand once, so rebuilding him from source reproduced the original defect
  verbatim — a 4.4726 m skeleton for a 1.96 m mesh with the feet 1.7011 m below the floor. The
  hips are the anchor because they sit at about 0.573 of height on every rig here even when the
  skeleton is the wrong size, and feet-on-floor gives the factor (0.3978 for him). Run it
  **before** `fit_joints.py`, never instead of it. `RIG_HIPS_RATIO`, `RIG_HIPS_BONE` override
- `fit_joints.py` — places each limb joint at the midpoint of the weighted-vertex centroids of
  the two bones meeting there, and carries untouched descendants by their nearest fitted
  ancestor's displacement. For a rig that is wrong by a **different factor in each limb**, which
  no single scale expresses. The Rock is the case: legs wanted 0.387 and arms 0.557. Disconnect
  bones before writing positions, and remember that disconnecting stops children following —
  the first version left all thirty finger bones behind and `FINGERFIT` came back byte-identical
- `drivers.py <vrm> [name]` — weight on bones nothing drives, per mesh, as a percentage. Also
  reports a mesh that is **not skinned at all**, which is worse and was previously passed over in
  silence
- `pose_check.py <vrm> <out.png>` — poses eight humanoid bones and measures per-vertex
  displacement, so a detached part shows up as a static cluster inside a mesh that moved.
  `POSE_CONTROL=<mesh>` unbinds a mesh as a positive control; `POSE_STATIC_EPS` raises the
  threshold
- `limb_check.py <vrm>` / `limb_check_installed.py <yargchar|dir>` — joint-to-joint limb angles
  from bone HEADS. Do not use bone-axis angles on a VRM: the importer synthesises a tail wherever
  the hierarchy does not pin one, and an angle measured against a synthetic tail is meaningless —
  it produced both a phantom 86.8° elbow and a suspiciously exact 90.00° wrist before that was
  understood
- `identify_build.py <yargchar> <vrm> [...]` — which `.vrm` produced an installed bundle, by
  skeleton names, then bone lengths, then rotation angles. The two ruled-out ends are the point:
  a comparison where nothing fails is not a comparison. Names shared by a mesh and a bone are
  excluded from the value comparison and reported
- `bundle_audit.py <yargchar|dir>` — clips, controller, humanoid-bone and finger coverage per
  bundle. What the game has to work with, as opposed to what the model looks like
- `bone_fit.py <vrm>` — how far each bone sits from the mesh it carries, in the written file.
  Expect centimetres. A finger bone 20-30 cm out is a mesh left in the A-pose while the skeleton went
  to T, and it throws the fingers out as long strips when the animation plays. It prints
  `FINGERFIT: n of m finger bones more than 5 cm from their mesh` -- expect 0
- `facing_check.py <vrm> [min_faces]` — also prints VOLUME lines: the exact signed-volume test for closed pieces (negative = the whole piece is inside-out) and a winding-conflict share per material. Which way each mesh/material's faces point, measured away from the nearest point of the bone that drives them. Textured clothing far under 50% is inside-out; thin sheets, hair cards and teeth read 45-60% and are fine; a rig where one bone drives everything (Sonic) cannot be judged
- `YargSceneShot.cs` — renders a `.yargchar` on the game's REAL character-select podium with the game's own camera and High render profile, the only render that has shown what the game shows (purple tint, inside-out clothing). **Copy it into a scratch copy of the project only, never into the real one**; run hidden with `-batchmode` and `-executeMethod YargSceneShot.Run -yargchars "<file>|<Name>" -shotDir <out>`. See `docs/character-models.md`
- `bind_check.py <vrm>` — pose versus rest for every bone, rotation AND position. Reads clean when
  pose and rest agree even if both are wrong against the mesh, so it does not replace `bone_fit.py`
- `YargCharHandRender.cs` — renders both hands INSIDE Unity, at rest and in the animated pose
  (`-renderDir`, with `export_one`-style `-vrmList`; run WITHOUT `-nographics`). Only the animated
  pose shows a skinning fault, and only because it bakes each skinned mesh first
- `meshbb.py <blend>` — per-mesh vertex count, world size and materials; how to tell which
  numbered mesh is the eyes before pinning a texture to its material
- `cloth_collide.py <vrm|dir>` / `cloth_collide_installed.py <yargchar|dir>` — for every spring
  chain, which humanoid part its joints hug and whether that part carries any collider. A chain
  whose part has none is **UNGUARDED**: the limb passes through the cloth, because a VRM spring
  joint is deflected by a collider and by nothing else. `CLOTH_VERBOSE=1` prints the clean chains
  too, `CLOTH_CONTROL=1` empties the collider list so every chain must flag. The installed version
  reads `Vrm10Instance.SpringBone.Springs`, `VRM10SpringBoneJoint` and `VRM10SpringBoneCollider`
  out of the bundle, which is the only way to cover the 35 characters with no `.vrm` left here —
  and the two agree to the millimetre on all nine of Peach's chains
- `viseme_audit.py <yargchar|dir>` — which INSTALLED characters can actually lipsync, read out of
  the bundle. Every VRM declares all 18 preset expressions whether or not anything is wired to
  them, so a file always *looks* capable; this reports the ones with real `MorphTargetBindings`,
  visemes and blink separately. Run it after rebuilding any character — it is what caught a
  rebuild shipping zero morph targets while every other count stayed identical
- `alpha_sweep.py <vrm|dir>` — materials shipping `alphaMode: OPAQUE` over a base map that carries
  real transparency, in **two tiers**: `mask` passes the same test `build_vrm.py` uses to decide a
  cutout, and `soft` is a feathered alpha that wants BLEND, or a cutoff chosen for it, rather than
  nothing at all. The second tier exists because the first version reported only `mask` and
  therefore missed Sayuri's eyelashes. The alpha is measured **only under each material's own UV
  triangles**, because the empty space between an atlas's islands is transparent and would
  otherwise make every ordinary body atlas look like a cutout. Both refinements are written up
  below. It prints candidates and fixes nothing on purpose: an alpha that looks like a mask is not
  always meant as one, and roughly half of its hits have turned out to be specular masks, atlas
  padding, or already correct
- `alpha_sweep_installed.py <yargchar|dir>` — the same question asked of the **installed bundle**,
  which is the only way to cover the forty-odd characters with no `.vrm` (25 `.vrm` files survive,
  covering about 22 of the 65, and four of those are Iron Man variants). Reads `_Surface`, `_AlphaClip`
  and `_Cutoff` off each URP/Lit material and decodes its `_BaseMap`, and reports three different
  defects: `UNUSED` (opaque material, base map carries alpha — the Peach/Alcina class), `HARDCUT`
  (a **cutout** whose alpha is a smooth gradient, so the 0.5 threshold butchers it rather than
  softening it) and `NOALPHA` (a cutout whose map has no alpha at all). `ALPHA_CONTROL=1` forces
  every material opaque, so every alpha-carrying one must flag — it takes UNUSED from 45 to 75 and
  HARDCUT to 0, which is what says the tiers are live rather than vacuous. MToon materials are
  listed and **not judged**: the six downloaded bundles carry their transparency in MToon's own
  properties, not URP's, and scoring them on a property they do not have would invent findings.
  It is **not** UV-masked, unlike `alpha_sweep.py` — a material sharing an atlas can read as
  alpha-carrying because of a region it never samples, so treat a hit on a shared atlas as the
  weaker evidence
- `height_check_installed.py <yargchar|dir>` — how tall each installed character is, against
  `height_targets.tsv` (transcribed from the per-model table below, and a committed data file
  because a mapping that lives in a session is lost), plus the floating-prop check that runlist
  item 2 asked for: a mesh whose whole vertical span is clear of the body's, and how much of the
  figure's height it is adding. That is Peacemaker's defect — scaling the FILE to 1.85 m scaled a
  second figure's helmet to 1.85 m and left him 1.51 m. `--strict` re-derives every bound from
  the raw vertex buffer and aborts if it disagrees with `m_LocalAABB` by a millimetre;
  `--selftest` runs the decision over Peacemaker's real geometry **and** the three shapes that
  made the first version flag a body mesh, and must get all four right
- `patch_alpha_blend.py <yargchar> --auto --out <new>` — the only repair in this folder that
  changes an **installed** bundle. UnityPy rewrites the serialized file directly, which is a
  different operation from Unity's bundle builder and does not have its problem: nothing needs an
  asset path, because nothing is rebuilt. Two modes, and only one works:
  - **`--mode cutoff` (the default) works.** It lowers `_Cutoff` on a cutout whose threshold is
    destroying its own opacity, so the same compiled `_ALPHATEST_ON` path keeps running and only
    the float it compares against moves. `--keep 0.45` picks the value from the ink; `--cutoff-to
    0.16` sets it outright, which travels better between materials once a good value is known.
    Any cutoff is capped at 90% of the material's own peak alpha, because a patch that can reduce
    a material to nothing is not a repair — Heels' tear line peaks near 0.05 and a flat 0.16
    would erase it, which the tool caught on its first real run.
  - **`--mode blend` is measured NOT to work** on an already-built bundle and is kept only so the
    measurement can be repeated. Every property comes back correct and Gordon Freeman's lens
    renders as a solid white pane, worse than the 79%-clipped cutout it replaced.

  It re-reads what it wrote and refuses to keep a file unless the targeted materials changed, the
  untargeted ones provably did not, and the object counts match. **It cannot tell you whether the
  result looks right** — that needs `YargSceneShot.cs`, and the podium harness jitters ~0.6% of
  pixels run to run, so compare by looking rather than by diffing
- `audit_all.py` — runs every installed-side check in one command and writes a dated report. See
  the next section
- `alpha_check.py` / `mat_check.py` / `spring_scan.py` / `uv_test.py` / `tex_stats.py` — material,
  alpha, spring and texture inspection straight out of the exported file

### One command for the whole set

```
python audit_all.py
```

`audit_all.py` finds the character folder, finds an interpreter that can import UnityPy, runs
every installed-side check over all 65 characters and writes `audit-<date>.md` next to itself —
each check's full output, and at the top a table of what each one said.

It exists because the list of checks was the thing that kept going missing. Seven of them read
the installed bundles, each with its own argument shape, and knowing which ones exist lived in a
conversation: that is how the floating-prop sweep sat unwritten in the runlist for days, and how
one character was excluded from the collider rollout twice. `--only cloth,alpha` runs a subset,
`--chars <dir>` points it elsewhere, `--out <dir>` moves the report.

Two details that are load-bearing rather than tidy:

- **It resolves the interpreter by IMPORTING UnityPy**, not by picking a version. `python` on
  this machine's PATH is 3.13 and has no UnityPy; the one that has it is 3.12. The obvious
  command fails with `ModuleNotFoundError: No module named 'UnityPy'`, which reads as "the
  tooling is not installed" rather than "you have two Pythons", and that is a five-minute
  detour every time.
- **When it cannot read a check's own summary line it says so** instead of printing a zero. The
  priority table is parsed out of each tool's last line with a per-tool regex; a regex that
  silently stops matching after an output change would turn a real count into a clean bill of
  health, which is the single most expensive shape of wrong answer this project has met.

It fixes nothing, by design, and it cannot see what only a render can see — a two-toned face, a
slab over an eye, an inside-out mesh. The alpha rows in particular are candidates: in a game rip
an alpha channel is as likely to be a specular mask as an opacity map.

The thirty-odd scripts in this folder that are **not** listed above — `bonecounts.py`,
`matcol.py`, `meshz.py`, `island_probe.py` and the rest — are one-off probes written to answer a
single question about a single character, kept because re-deriving one costs more than reading
it. They are not maintained and none is a check anything depends on. The list above is the set
worth reaching for; treat anything else here as a worked example.

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
| Mandalorian | upright, arms clear of the torso | **rigged**; cape needs `HAIR_BONE=Spine1 HAIR_ANCHOR=0.15` with hairrig `^CAPE$` |
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
| Sonic | 1.00 | `x0.9968` | 28/52 | keeps the authored T-pose clip. **Installed build identified 2026-11-11** with `identify_build.py`: it is `rollout/out/Sonic.vrm` = `reg-Sonic.vrm` = `SonicHD_fix.vrm` (34/34 bones agree in length and rotation). `SonicHD`/`SonicHD_nt` differ on bone length, and the `withcols` copy is the wrong-rig rebuild that was reverted. **His wrists are NOT off** — an earlier entry here said they were, from mirrored local rest rotations (69° at the hand, 127° at the finger), and that was wrong: local rotation is relative to the parent and left/right bone rolls need not match. A second attempt using bone AXES read "exactly 90.00°" and was also wrong, because the VRM importer synthesises bone tails. Measured joint-to-joint with `limb_check.py` his elbows and wrists are 0.00° on both sides, mirrored bone heads agree to 2–7 mm, and close-up renders show two correct mirror-image gloves. Nothing to fix |
| Yoda | 0.66 | `x0.6471` | 28/52 | 1 spring chain |
| Alcina | 2.90 | `x0.7388` | 52/52 | relaxes the left hand, 61.3 vs 0.0 deg |

A scale factor that moves is the loudest signal available: it says the geometry being measured
changed size, which means something upstream moved it.

**Two of the three cannot be re-run from their archives.** Sonic and Yoda both arrive unrigged and
go through Mixamo, so the thing the table's numbers describe is the auto-rigged intermediate, not
the download. Keep those intermediates somewhere durable — a build that only exists in a session's
scratchpad takes two thirds of the regression set with it when the session ends. Alcina is the one
that rebuilds from her own archive, and she is also the one that covers the texture picker.

## Material and face switches

Set in the environment of the step named. All are off unless set, so no other character changes.

| Switch | Step | Does |
|---|---|---|
| `VRM_DROP_MATERIAL_FACES="Mat1;Mat2"` | build | deletes every face using a named material and the vertices only they used. A material is not always just what its name suggests: Alastor's black `Material.001` is the outline hull AND half his clothes. Measure before dropping, and expect `-Force` on the install |
| `VRM_FLIP_FACES="Mesh:z<0.9;Mesh2:z<0.15"` | build | reverses the winding and the split normals of every face of the named mesh below that height (metres). For clothing modelled inside-out behind an outline hull. Check with the share of faces pointing away from the local body axis |
| `VRM_ORIENT_OUTWARD="Body.001@0.25"` | build | for each mesh, named material and driving bone, flips the WHOLE group (winding and split normals) when fewer than that share of its faces point away from the bone. Whole groups only, so mixed groups (a double-layered coat) are left alone. Runs after `VRM_FLIP_FACES`. Measure first with `facing_check.py` |
| `VRM_ORIENT_CONSISTENT="Body.001;Head.001;Eyes.001"` | build | the better one. Orients whole CONNECTED PIECES (faces joined by shared edges, vertices welded by position): propagates one winding through each piece, then decides it as a whole, by SIGNED VOLUME for a closed piece (exact, needs no bone) and by the driving-bone vote only for an open sheet. Replaces `VRM_ORIENT_OUTWARD`, whose group flips cut across pieces and left 3% winding conflicts (patches missing from gloves and cuffs). Judges pieces of any size, joined across every material of the mesh (nearest-neighbour weld, 0.1 mm); `VRM_ORIENT_DEBUG=1` prints each small piece's decision. Known miss: a closed 3 cm solid beside Alastor's eyes stays inside-out |
| `YARG_CULL_OFF_MATERIALS="Head.001;Eyes.001"` | export | draws the named materials double-sided. The source `Standard` material has no cull property, so the glTF `doubleSided` flag is lost on import and single-sided sheets (hair fringe, ears, eye planes) vanish from behind |
| `YARG_NO_SHINE_MATERIALS="Body.001;..."` or `*` | export | smoothness, metallic, specular and environment reflections off. Partly overridden for materials with a metallic map (the exporter sets `_Metallic` 1 afterwards) |
| `YARG_SHELL_NO_SHADOW=1` | export | an untextured near-black material stops casting shadows. Made no visible difference on Alastor |
| `YARG_SHADOWS=1` | hand render | soft shadows on the render light |

## Known per-model arguments

| Character | rig | height | notes |
|---|---|---|---|
| Prix | mixamo | 1.70 | shape keys must be dropped, else she builds at 0.42 m |
| Pomni | pomni | 1.70 | exclude `^Circle`; `VRM_VISEME_GAIN=3.0` (4.4 turns her upper lip inside out); `VRM_BLINK_BAKE="EyelidSup.L=1,0.55,0,0;EyelidInf.L=1,-0.5,0,0;EyelidSup.R=1,0.5,0,0;EyelidInf.R=1,-0.5,0,0"` and `VRM_BLINK_LASH="^Lashes"` (lash ticks lie on the closed seam, 4 mm in front of the lid, keeping 40% of their height) -- her blink is four eyelid BONES (peak at frame 30 of `Animation`), not a shape key; her `Lashes/Closed` key only moves two lash ticks and leaves the eyes open. The bake applies Solidify+Subsurf to the lid meshes, writes the closed pose as a `Blink` key and binds it. Rendered at weight 1.0: dark lids with a slit, matching her Sketchfab blink. Her iris `Big`/`Small` keys ride on YARG's own facial events: `VRM_EXPR="Wide_eyed=Eye.L/Big;Squint=Eye.L/Small"` makes them custom expressions named for lipsync event types, which `VRMCharacter.TryGetExpressionKey(string)` sets by name -- `Big` fills the eye with iris, `Small` shrinks it to a pinpoint (rendered, both eyes). The chart generator emits `Squint` but not `Wide_eyed`. **Added 2026-11-12, and she cannot be rebuilt without it:** `VRM_VISEME="aa=Face/A,ee=Face/ClosedTeeth,ih=Face/ClosedTeeth@0.7,oh=Face/OpenNoTeeth,ou=Face/OpenNoTeeth@0.6"` — her mouth shapes are named for an artist and only `A` is guessable, so without this she builds at 1/5 visemes. 32,764 triangles, 16 meshes, 27 morph targets, 5/5 bound |
| Sayuri / Aiko | cc_base / mixamo | 1.70 | hairrig `^Hair$` — no hair bones of their own. **Sayuri as installed 2026-11-11:** add `VRM_BREASTRIG=1` (the recovered ARGV is the original build and omits it — without it the rebuild comes back with 4 spring chains against her 6) and `VRM_TEX="Eye_Shadows=Eyelashes_Opacity.png:alpha"` (she has one `Eyelashes_Opacity.png` and two materials that need it; the picker gives it to the one whose name matches). Her model is `source/Sayuri dans.fbx`, its texture paths point at `C:\Temp\CharacterCreator4Temp\` on someone else's machine and the builder relocates all 8 of them. 91,632 triangles |
| Aiko | mixamo | 1.70 | exclude `^Girl2\.[0-9]` — one girl, 15 Mixamo clips |
| Batman | multiversus | 1.88 | run `prep_batman.py` first: two half-characters on two armatures |
| Chibi Rem | rigify_def | 1.55 | exclude `'^(?!GME_Rem$).*'` |
| Gwen Stacy | mixamo | 1.70 | hairrig `island:1`, `HAIR_ANCHOR=0.70 HAIR_SEGS=2 HAIR_STRANDS=3` |
| Junio Sonic | sonic | 1.00 | `VRM_DROP_SOLIDIFY=1`, exclude `^Dots` |
| B1 Battle Droid | b1 | 1.93 | four of five meshes are empty placeholders |
| Thanos | advskel | 2.40 | source is a kneeling pose; head emission must be zeroed |
| Alastor | mixamo | 1.95 | exclude `^(Cube\|Microph)` — detached mic inflates the bounds **As installed 2026-11-11 (in-game result pending):** build with `VRM_VISEME_GAIN=2.2 VRM_DROP_MATERIAL_FACES="Material.001" VRM_ORIENT_CONSISTENT="Body.001;Head.001;Eyes.001"`, export with `YARG_CULL_OFF_MATERIALS="Eyes.001" YARG_NO_SHINE_MATERIALS="Body.001;Head.001;Eyes.001"` and `-Force` (21,415 triangles against 40,124 on purpose). `Head.001` is single-sided on purpose, as a test of whether the mask-through-fringe fault was winding. `Eyes.001` is oriented too (they were inverted: 0% facing the front, hidden by the double-sided material) and the small pieces are judged. One closed 3 cm head solid at z 1.55 stays inside-out and is not understood. He has no outline. See `docs/character-models.md` |
| Jessica Rabbit | rigify_plain | 1.80 | exclude `^(BezierCurve\|Cylinder\|Cube)` |
| Clone troopers | mixamo | 1.83 | |
| Jinx | ue4 | 1.68 | braids and bangs already in the rig |
| Shrek | mayajnt | 2.10 | |
| Gordon Freeman | valvebiped | 1.80 | **As installed 2026-11-12:** build from `m2/source/Valve_Gordon_Freeman.fbx`, textures `m2/textures`, with BOTH of these or he loses something — `VRM_BLEND_MATERIALS="lens"` (his glasses lenses shipped opaque and drew as two solid white panes over his eyes) and `VRM_VISEME="aa=gordon_freeman/AU26ZR+AU26ZL,ee=gordon_freeman/AU12R+AU12L,ih=gordon_freeman/AU12R+AU12L@0.7,oh=gordon_freeman/AU18R+AU18L.001,ou=gordon_freeman/AU18R+AU18L.001@0.75"`. **His shape keys are FACS action units and match none of the automatic patterns**, so without that map a rebuild drops all 32 of them and binds nothing — which is exactly what happened on the first rebuild, silently, with every census count unchanged. 7,169 triangles, 4 meshes, 7 materials, 12 morph targets, 5/5 bound. Do NOT add `eye-iris-green.tga` or `onefreeman` to the blend list: both alphas are specular masks, and honouring them hides his irises and erases his suit |
| Joker / Miku | maxbiped | 1.85 / 1.58 | |
| Tenna | rigify_def | 1.80 | exclude `^(Floor\|Lights\|Sign)` |
| Sophia | rp | 1.70 | |
| Steve | steve | 1.80 | |
| Shadow | sonicforces | 1.05 | |
| Pepsiman | arp | 1.85 | |
| Vegeta / Spider-Man PS | mixamo | 1.64 / 1.75 | |
| Mannequin | simple | 1.75 | |
| Sonic (HD) | mixamo | 1.00 | model arrives UNRIGGED — auto-rig it on mixamo.com first, then `VRM_RIGID="island:0=Head"`. Its T-pose is in the clip, not the rest skeleton |
| Alcina Dimitrescu | rigify_plain | 2.90 | 9'6" is correct and her static pose is her SHAPE — never reset it to rest. exclude `^NurbsPath` (the cigarette holder skewers her hand), `VRM_TEX="Material.005=CABELOO_preto_1.png,Material.019=(null)_Base_Color.png"`. The floating hat was the unrigged-mesh rescue resizing her whole rig by 0.5568 to fit one stray dress train; it is fixed. **As installed 2026-11-12:** add `VRM_BREASTRIG=1` and `VRM_CUTOUT_MATERIALS="Material.005;Material.006"` — her hair and eyelashes, which shipped opaque and put two black slabs over her eyes. Build from `Alcina102.blend`, 350,162 triangles. Her colour maps are all noise fields and she renders white; that is the archive, not the build, and at 2.9 m her head is above the character-select camera |
| Yui Suzukaze | mixamo | 1.60 | recovered from her own .yargchar, re-rigged; needs the VRM_TEX map from the submesh headers |
| Lola Bunny | multiversus | 1.75 | exclude `^Icosphere` |
| Mickey Mouse | mixamo | 1.10 | archive is called `talking.zip` |
| Elite Terrorist | mixamo | 1.83 | |
| Jessica Rabbit | rigify_plain | 1.80 | exclude `^(BezierCurve\|Cylinder\|Cube)`, hairrig `^hair`, `VRM_RIG_MORE='^glitter-transprnt$@spine#4,4,0.2'` for the skirt, `VRM_TEX="rskin=Skin_makup_0003_Body_multires_sculpt.001_m.jpg"`. **The exclude was not lost** — this row said "something was excluded that nobody wrote down" while the rig-family table above recorded it all along. With it the rebuild matches the installed character exactly: 320,562 triangles, 10 meshes |
| Alice Ivy | cc_base | 1.70 | exclude `^COLLIDER` |
| Ariel | daz | 1.70 | hairrig `Hair`. Recovered from her own `.yargchar`: `lPectoral` and `abdomenUpper` are DAZ names, and the mesh bounds give the height |
| Killer Clown | mixamo | 1.80 | hairrig `hair`. Her bones are Mixamo's with the prefix stripped (`Hips`, `LeftHandIndex1`, `HeadTop_End`), which the family auto-detects |
| Heels | cc_base | 1.70 | hairrig `Hair`; the archive holds `source/untitled.zip` with the `.blend` inside. ~~Do not reinstall yet — a rebuild loses her transparency~~ **Resolved 2026-11-11**: that was the missing-alpha bug. A rebuild now keeps all five of her transparent materials and adds two more (`Std_Eye_Occlusion_R`, `Std_Tearline_R`). `High_Heels` and `Underwear_Bottoms` stay opaque, as installed — their "opacity" files are merged diffuses with no alpha channel left |
| The Rock | mixamo | 1.96 | Archive `the-rock.zip` -> `source/The_Rock.7z` -> `Rock.fbx`, textures beside it. **SCALE ONLY — do not run `fit_joints.py` on him.** His source skeleton spans 4.4726 m against a 1.96 m mesh with bones 1.7011 m below the floor; `scale_rig.py` fixes that about the hips (factor 0.3978) and that is the whole correction. Measured after: shoulders 0.276, reach 0.931, upperarm 0.160 — all on the population median — and the render has proper deltoids, biceps and fingers. ~~Needs two corrections and `fit_joints.py` does both~~: it does not do the scale, the scale was never in a script, and the joint fit makes him WORSE both ways — fitting the shoulder doubled his span to 0.548 (the gorilla arms), and even with the shoulder excluded it smears his arms into thin tubes (upperarm 0.344 against a median of 0.181). Check with `proportion_check_installed.py`, not `bone_fit.py`, which rewards exactly what the fit does |
| Mario | mariojnt | 1.55 | |
| Link (OoT) | linkoot | 1.65 | `VRM_TEX="Hair=Link_Link_BaseColor.png"` |
| Gadget Hackwrench | rigify_def | 1.30 | exclude `^(WGT-\|smd_bone_vis)`, hairrig `^Hair$` |
| Peach | smash | 1.70 | her forearms are stretched in the SOURCE rip, not by the build. **As installed 2026-11-11:** build from `source/model.fbx` with `VRM_CUTOUT_MATERIALS="_1.004;_4.003;_5.008;_5.012;_5.013" VRM_MTOON_ALL=1` — the iris, eyelash-plate and dress-lace materials, and one shading model so the plate does not read as a patch on her face. NOT `_6`/`_6.002`: the crown's alpha is an outline and masking it carves the jewel out. Reproduces the installed character exactly at 11,602 triangles, 16 meshes, 16 materials, 10 images, 9 springs, 173 nodes |
| Harley Quinn | mixamo | 1.70 | build from the USDZ (names transferred from the .fbx) — the .zip has no colour map and the two have different UVs |
| The Mandalorian | mixamo | 1.83 | glTF; BOTH its skeletons are collapsed, so re-rig via Mixamo. Exclude `^(grogu\|.*CRADLE\|.*JetPack\|.*RIFLE\|Icosphere)` — the pack also contains Grogu, his cradle and a rifle |
| Power Girl | mixamo | 1.80 | Injustice 2 rip, 417 bones, builds clean. Materials are called `mesh0`/`mesh1`, so pin them: `VRM_TEX="mesh0=Supergirl_A_Body_Color.png,mesh0.001=Supergirl_A_FACE_30hz_Color.png,mesh0.002=Supergirl_A_Cape_Color.png,mesh1=Supergirl_A__EyesMouth_Color.png,mesh2=Supergirl_A_Hair_Color.png"`. Her hair alpha has to be pinned too, for the same reason — add `,mesh2=Supergirl_A_Hair_Alpha.png:alpha`. She is the ONLY model of the 109 archives here whose opacity map does not name its own material, so she is the only one the narrowed alpha pick leaves without one |
| Peacemaker | dcseries | 1.85 | exclude `^Peacemaker_obj_(BlueDeep\|RedGlow\|Silver_003)_0$` — a SECOND figure's helmet on a second skeleton, floating above his head. Left in, it is the tallest thing in the file and he scales to 1.51 m. Flat-colour model: its USDZ holds no images at all, so every material reading `-> NONE` is correct |
| Vigilante | dcseries | 1.88 | same rig as Peacemaker, based at `n8` instead of `n115`. He arrives armed, and the two weapons CANNOT be excluded by mesh name: they share `Vigilante_obj_001_Pewter_002_0` with the sheath on his back and the holster on his hip. `VRM_DROP_ISLAND="Vigilante_obj_001_(Pewter_002\|Silver_003)=n17+n50"` takes the 540 vertices the two hand bones carry and leaves the 204 the spine and hips carry. Height, width and humanoid count are unchanged by it (`x1.0552`, 0.7075 m, 47/47) — the weapons never affected his proportions, which is why they survived the first build |
| Shaggy Rogers | shaggyusd | 1.83 | USDZ, 52/52 — the whole humanoid including toes and three-bone thumbs, and already in a T-pose. One 1.5 KB palette texture does the entire character |
| Scott Hall | mixamo | 2.01 | the `.blend` in `source/`, not the fbx: a plain 65-bone Mixamo rig. exclude `^(Plane\|Scott Hall OGscale\|M_Jacket)$` — a joined duplicate of the whole body, a duplicate jacket and a backdrop. hairrig `Hall_Hair$`. His own file points the RIGHT elbow pad at the kneepad texture, so `VRM_TEX="Hall_Elbow-R=Hall_r_elbowpad_color.png,Hall_Elbow-R=Hall_r_elbowpad_roughness.png:rough"` |
| Anakin Skywalker | anakin | 1.85 | a posed SCULPT — see the section above; needs `VRM_STANDUP=1 VRM_REBIND_STALE=1`. One leg's mesh still smears |
| Judy Hopps | **judyusd** | 1.05 | `Judy-hopps-zootopia.usdz`, textures `new/judy2/textures`, hairrig `^n(29\|3[0-8])$`, `VRM_KEEP_SIDES=1`. **Her hands stood UP out of the cuffs until 2026-11-10**: the stub-finger step laid the missing finger chains along her hand bone, which points straight down (2.5 cm, tail at -Z), and the exported hand came out turned 100 degrees against the pose the mesh is bound in. The stubs now go along the FOREARM. Check any rebuild with `bind_check.py`. Her real hands are closed fists, thumb out -- that is how she was modelled -- and her finger bones are not mapped to the humanoid fingers, so they do not animate. **The installed Judy is this USDZ build, NOT the rigify_plain FBX** -- that row used to say `rigify_plain` + the FBX, which is the abandoned attempt that renders white. Rebuilding from it produced a 38,268-triangle stranger where she has 16,521, and it was installed over her before anyone checked. Identify a character by its MESH NAMES, not its recipe row: hers are `Judy_Judy_A_01_Cloth_0` / `_Eyelash_0` / `_Face_0` with hips on `n15`; the FBX build has `Cube.001` / `Low` with hips on `spine` |
| Yoda | mixamo | 0.66 | USDZ, no skeleton at all — auto-rigged; `VRM_RIGID="island:0=Head"`, robe on `island:1` with `HAIR_BONE=Spine1 HAIR_STRANDS=1`. The USDZ has **no** eye map: merge `CHA_yodaEye_C.png` from the original zip and pin it with `VRM_TEX="yoda_mesh_RoninShader7=CHA_yodaEye_C.png"` |
| Miku | maxbiped | 1.58 | `VRM_FINGER_FILL=1`, exclude `^ts_bot` (a detached guitar), spring regex `$^` and `VRM_CLEAR_SPRINGS=1`. **The hairrig was removed**: `island:7+8` reached 198 of her ~493 hair verts and weighted 59, which sheared the ribbons apart. Her hair is ~250 strips and is splayed outward in the ORIGINAL download, not by us |
| Skibidi Toilet | valvebiped | 1.60 | exclude `^(Icosphere\|Object_2$)` — the toilet shell swamps the model |
| Xenomorph | xeno | 2.40 | `xeno/source/Xenomorph Default.fbx`, 51,548 triangles, 1 mesh, humanoid 46/46. The spring argument must be the DEFAULT regex with `\|BackTube` appended — the default alone finds only his tail and loses his four dorsal tubes, and `(BackTube\|TailRoot)` loses the tail, because the regex has to match a chain's whole run of bones rather than just its root. No `rollout/out` reference exists for him, so verify a rebuild with `identify_build.py` against the installed bundle instead: expect 171 bones, 0 length and 0 rotation mismatches |

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
the `.glb` chunk.

**That check cleared The Rock, and The Rock is broken.** He measured 5.13 m wide on re-import
while the mesh bounds said 1.96 m, and this section recorded the importer as the liar. In game
his limbs stretch into metre-long spikes. The mesh bounds were right and were never the
question: his **skeleton** is sized for a figure about 3.5 m tall — head bone at 2.77 m, hand
bone 1.94 m out from the centre — and the skin is being dragged onto it. Spider-Man and Chibi
Rem measure 1.00 and 1.02 on head-bone against mesh height; he is 1.41.

So the importer may well also re-pose a skin, but it was not what the 5.13 m was showing, and
the check that dismissed it only ever measured the MESH. **A check that clears a defect is a
claim, and it is only as good as the thing it measured.** Measure the skeleton against the mesh
as well, which is two more lines and would have caught him the first time.

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

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
  the build prints where each island sits so a recipe can be written from its own output.
  **Two things it refuses, both added 2026-11-15 and both printed when they fire.** A mesh taken
  only because it SHARES a matching material is declined when its own name says it is not hair
  (`lash`, `brow`, `eye`, `teeth`, `tongue`, `mouth`, `lip`…) — a material is shared by whatever
  the author chose, and on an anime-styled model that is routinely the lashes and brows; a mesh
  the pattern NAMES is still taken, so `hairrig lashes` still rigs the lashes
  (`VRM_HAIRRIG_FACE=1` to disable). And a strand that is ≥50% SEALED inside a mesh rigidly
  parented to the head — a hat, helmet, hood or crown — is not rigged at all, because hair that
  cannot be seen cannot be seen to swing and can only be seen to clip (`VRM_HAIR_SEALED`).
  Killer Clown hit both at once; see "Killer Clown's hat, 2026-11-15"

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
Freeman's glasses lenses — and for a **feathered** one a cutout would destroy, such as an
eyelash. **It overrides a cutout an opacity map has already established**, deliberately: "a
dedicated opacity map is the stronger signal" answers OPAQUE vs not, and says nothing about MASK
vs BLEND, which is a question about the shape of the alpha rather than its provenance. While it
was guarded the other way it was a no-op on every material that needed it, and Heels' eyelashes
shipped 99.6% clipped away; `VRM_MTOON_ALL=1` puts every material
on the MToon shading model, which is what a character needs when a cutout shares a continuous
surface with an opaque material (otherwise only the cutouts are MToon and the seam shows);
`VRM_LIMB_COLLIDERS=0` goes back to a head sphere and a torso capsule alone;
`VRM_SAVE_BLEND=<path>` saves the pre-export scene (the single most useful
debugging aid — renders of it tell you whether a fault is yours or the exporter's),
`VRM_NO_TPOSE=1`, `VRM_DROP_SOLIDIFY=1` (inverted-hull outlines), `HAIR_ANCHOR` / `HAIR_SEGS` /
`HAIR_STRANDS` for the hair rigger;
**`VRM_EXPORT_POSE=rest`** stops the VRM add-on applying a T-pose estimate of its own on the way
out — which re-aims every humanoid chain including the FINGERS, and is what flattened Gadget
Hackwrench's hands (29.9/45.3/29.0/28.3 degrees of knuckle bend in, 0.0 out). It is opt-in on
purpose: on a rig whose own T-pose step never ran the add-on's estimate is the only thing
T-posing the character, so the build measures the rest pose and warns when it is not a T-pose.
See "The VRM add-on applies a T-pose of its OWN" below.

**2. VRM → .yargchar** (Unity 6000.3.5f2). Copy `YargCharExporter.cs` **and
`YargCharHandRender.cs`** from this folder into `<fork>/Assets/__TempExport/Editor/`, run it,
then delete that folder. Both: the exporter calls into the hand renderer, and copying only the
exporter fails the whole batch with `error CS0103: The name 'YargCharHandRender' does not exist`
— a compile error, so nothing is written and the Unity exit code is the only sign. It lives here, not under
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

**Measured 2026-11-12, and the "18 whose source has them" was a subtraction that does not survive
contact with the files.** `viseme_fit.py` over all 30 surviving `.vrm` files splits them with
nothing in between: **22 carry zero shape keys** and 8 are mappable — and seven of those eight
are the characters already installed at 5/5. The four extracted source archives agree: Sayuri,
Alcina, Ariel and Jessica Rabbit's GLB have zero shape keys each, and all four were inside
that 18. The control that makes the zeroes readable is that the same importer reports 16 keys
for Chibi Rem, 13 for Pomni, 10 for Heels and 5 for Sonic.

The eighth is **Sonic**, whose `.vrm` binds all five visemes while his bundle binds none — but
`identify_build.py` puts that `.vrm` at **4.3% of names** against his installed bundle, 6 bones
compared. It is the other Sonic model, not his. Installing it would replace the character
rather than give him a mouth, so it is left alone.

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
| Gadget Hackwrench | head and hair dragged off the body | **FIXED 2026-11-13, and the cause was none of the three things it was blamed on.** Her `hips` was mapped to a bone literally called `root` at **0.6% of her height**, because her thighs hang off the armature root rather than her pelvis, so the root is the only bone satisfying "the junction of a spine and two legs". Unity then pivots the whole body about a floor-level hips, whipping the head, and her hair springs turn that into a spike. Also true, and separate: her eyes are bone-parented to `MCH-eye.L/R`, which the export drops because they do not deform |
| Joker | a pistol orbiting him; parts of the suit unrigged | **both fixed.** The pistol is 262 verts on a bone called `Gun_joker`, inside his one mesh with his one material: `VRM_DROP_ISLAND="Joker=Gun_joker"`. The suit was the orphan-bone case |
| Peach | eyes missing; dress springs so reactive her legs clip through it | **BOTH FIXED 2026-11-11, and neither was what the report implied.** The eyes are the alpha fault: her eye is a STACK of meshes from a Smash rip -- `Peach_eye` is a blank white sclera with no iris, `Peach_Blink_Ottotto` is the iris and `Peach_Blink_VoiceA` is the eyelid-and-lash plate that fills a rectangular hole in `Peach_faceN` -- and all three shipped `OPAQUE`, so the top layer drew as a solid plate. The skirt is NOT too reactive: her skirt chains are stiffer and more damped than her hair's (0.85/0.80 against 0.60/0.45). They are UNGUARDED -- eight of her nine chains hang around her thighs and she had two colliders, both on her torso. See below. **~~BOTH FIXED~~ — REOPENED 2026-11-15 and fixed again, and "BOTH FIXED" is what let it happen.** Reported a second time, for clipping legs AND a dress moving as one piece. Two causes: her skirt was damped to near-rigidity by the 0.85/0.80 cloth default, which had itself been set in answer to the *first* Peach report before that report's cause was withdrawn; and the limb capsules fitted on 2026-11-11 use the MEDIAN flesh radius, so half of every limb sits outside its own collider and her calf reaches 24 mm past the only thing her hem can feel. See "Peach's dress, 2026-11-15" |
| Link | eye textures misplaced; still holding the master sword and shield | **both fixed.** His rig has bones named `Sword` and `Shield`, so `VRM_DROP_ISLAND="LinkEquipment=Sword+Shield"` takes 41 islands and leaves `Fourreau`, his scabbard, on his back. His eye material `Material.003` was taking the body atlas while `Eye.png` sat unused beside it |
| Shadow | eyes use the blink/closed frame of the atlas; fingers do not move | an eye atlas with the wrong frame pinned, and ~~finger bones that are mapped but not weighted~~ **corrected 2026-11-11 by `bundle_audit.py`: he has ZERO finger bones in his humanoid map**, and 21 humanoid bones in total against a typical 52. The symptom was right, the stated cause was wrong |
| Sophia | shiny | **FIXED 2026-11-15, and it was never her defect.** One material, URP/Lit, one base map and nothing else — no normal map, no metallic/gloss map, because her RenderPeople source ships diffuse only. `_Smoothness` 0.50 with specular highlights and sky reflections on is **URP/Lit's own default**, and **63 of the 65 installed characters sit there; 27 of those have no normal or gloss map either**, so the specular is completely uniform. Ruled out by measurement: her albedo is not blown (12.7% above 0.80 luminance against Gwen Stacy's 79.1%), her base map is sRGB like all 57, and she has no emission. She is simply the character on whom a plastic specular over photoscanned skin shows. `YARG_NO_SHINE_MATERIALS` was already the project's answer to this for Alastor. Applied to her alone and put to Jay as a question, since an appearance change across a third of the roster is his call; he said **"yes, all 26"**, so the other 26 were flattened too — **132 materials across 26 characters**, each hash-backed up and verified five ways. See "Sophia's shine, 2026-11-15" |
| Spartan Mark V | asymmetric right leg | **FIXED 2026-11-15.** His whole right leg hung off one bad `thigh.R` offset, sitting **29.7 mm clear of a hip socket his left leg sits 4.7 mm inside** — and after the fix it reads 4.6 mm, his left leg's own figure. (An earlier version of this row said "92.12 mm from the mirror of his `thigh.L`"; that number came from a tool that was withdrawn the same day for comparing local offsets under a rotated shared parent. The fault was real, the number was not — the evidence is the socket gap, his provably symmetric source, and his lower torso's self-mirror error going to 0.00 mm when the bone moved.) No ANGLE check could see it: the leg moved rigidly, so his knee and ankle match his left side to four decimals. His source `.blend` is an exact mirror in both bones and flesh, and a rebuild from it today is 0.000 mm out, so this came from a build that no longer exists. Patched in the four structures that hold that offset. See "Spartan Mark V's right leg, 2026-11-15" |
| Killer Clown | hair clipping through her hat | **FIXED 2026-11-15, and the hat was the smaller half of it.** Her lashes, brows and hair are one material, and the hair rigger's material fallback takes every mesh that shares the hair material — so her **eyebrows are 146 of 146 vertices on hair spring chains** and her **eyelashes 2,357 of 4,640**, swinging on hair physics across her face. They are 2,503 of the 2,890 vertices those four chains move; the hair itself is 387. Of those 387, **371 sit inside her jester hat**, up to 51.8 mm deep, while 95% of the hair the rigger left rigid is outside it — the physics went on the hair nobody can see and the visible hair stayed rigid. Both are selection faults, so no parameter fixes either: the four chains were removed. See "Killer Clown's hat, 2026-11-15" |
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
| ~~Gadget Hackwrench, Pomni~~ | ~~4~~ | **BOTH VERDICTS WERE STALE.** Pomni's 5 mismatches were the duplicate-name artefact, fixed above. Gadget's 57 were real -- of the `rollout/out` and `withcols` files. **Four newer `.vrm` files match her installed rig at 0 length and 0 rotation mismatches**, and two already carry the limb colliders. Rebuilt and installed 2026-11-13; see below |
| ~~Xenomorph~~ | ~~5~~ | **DONE 2026-11-12** — his source FBX survived. See below |

Installed total after that: **53 of 391 across 7 characters**, and every one of the seven is in
one of the three rows above.

### Peach's dress, 2026-11-15: both halves were a remedy that outlived its reason

She was reported again, four days after being closed. The report this time was **clipping through
her legs AND moving as one piece** — and "one piece" is the opposite of the symptom the first
report described. Both halves turned out to be pipeline defaults still in place after the
reasoning behind them had been withdrawn, and one of them was put there *by* the first Peach
report.

**Fault A — the skirt barely moves.** `build_vrm.py` gives a cloth-named chain 0.85 stiffness and
0.80 drag against hair's 0.60/0.45, uniform across all five joints. The comment on that line said
why: *"Peach's dress is rigged and reported as so reactive that her legs pass through it"*. On
2026-11-11 that reactivity was measured and was not the cause at all — her skirt chains had **no
collider on any leg**, so the legs passed through cloth that was barely moving. The colliders were
fixed, the entry in the table above was marked **BOTH FIXED**, and the stiffening stayed. Same
character, four days, opposite symptom.

The replacement is not a better guess. The six downloaded VRoid bundles in the installed folder
were parameterised by their own authors and are not ours, so they are a control:

| whose | kind | stiffness | drag |
|---|---|---|---|
| Harq Alkahana, both Hatsune Mikus, Inforder Trogen | skirt | **0.50** | **0.05** |
| Adachi Rei | skirt | 2.00–4.00 | 0.40 |
| all six | hair | 0.26–0.40 | 0.40–0.50 |
| ours | hair | 0.60 | 0.45 |
| **ours** | **cloth** | **0.85** | **0.80** |

Drag 0.80 is **above every authored value in the set**, for cloth or hair, and sixteen times what
four independent authors give a skirt. And the direction is wrong, not just the magnitude: the
authors damp a skirt *less* than hair, because a hanging panel is restrained by its restoring
force and damping is what stops it moving at all. Stiffness 0.85 is unremarkable by comparison and
was never the outlier. `VRM_CLOTH_PARAMS` now defaults to `0.5,0.05,0.0`.

**One false lead, recorded because it was convincing.** Collapsing each authored chain to its set
of distinct settings showed *two* per skirt, which read as a graded chain — stiff at the waist,
loose at the hem — and would have been a much more interesting finding. Printing them in chain
order killed it: the second setting is `1.00/0.50` on the **last** joint of every chain, hair and
cloth alike. A VRM joint rotates the bone *before* it, so the final joint only marks the tip and
its parameters are never simulated. The authored chains are uniform, like ours. A set is not a
sequence, and the question was entirely about order.

**Fault B — the legs pass through the hem anyway.** `vrm_colliders.fit` sizes a collider at the
**median** distance of the flesh its bone carries. That rule is right where it was written —
a hair collider on a scalp, where a sphere enclosing the nose and chin holds the hair visibly off
the head — and the limb capsules added on 2026-11-11 inherited it. On a limb the requirement is
the opposite. A VRM spring joint is deflected by a collider and by nothing else, so **the capsule
IS the leg** as far as a skirt is concerned, and a median radius leaves half the leg outside it by
construction.

Measured off her shipped bundle, by decoding the vertex buffers and attributing each vertex to the
bone that dominates it. Her radius equals the 50th percentile to three decimals on **all eight
limbs** — the rule, read back out of the file it built:

| limb | capsule | p50 | p90 | max | outside the capsule |
|---|---|---|---|---|---|
| upper leg | 0.061 | 0.061 | 0.081 | 0.085 | 49%, worst by 24 mm |
| lower leg | 0.039 | 0.039 | 0.064 | 0.080 | 50%, worst by **41 mm** |
| upper arm | 0.053 | 0.053 | 0.095 | 0.109 | 50%, worst by **57 mm** |
| forearm | 0.032 | 0.034 | 0.040 | 0.042 | 75%, worst by 10 mm |

Her calf reaches 0.080 from the bone axis and its capsule stops at 0.039, so a hem resting on that
capsule sits 20 mm inside the skin. No spring parameter can fix that.

`VRM_LIMB_PCT` now defaults to **0.90** for the limbs; the head and torso keep the median. p90
rather than the maximum, and the first reason is weaker than it looked. A spring joint is a sphere
of `hit_radius` 0.02, so the capsule only has to come within 0.02 of the furthest vertex — and
swept over all 65 installed bundles, p90 + 0.02 does that on **314 of 469 limbs**, Peach's eight
among them. Not on all of them: **155 fall short**, so this is an improvement on the median and
not a guarantee.

The second reason is why the shortfall is tolerable and why chasing the maximum would be worse.
The vertices attributed to a leg bone are not all flesh — a gown skinned to the legs counts too.
**Alcina Dimitrescu's lower leg has its furthest vertex at 0.401 against a 0.123 p90, because that
vertex is her dress.** A capsule drawn to enclose it would wrap the very cloth the capsule exists
to deflect, and eject it. A fixed percentile cannot chase that; a max-seeking one would.

The clearance guard is unchanged and still has the final word. On the installed set it would newly
fire on 14 limbs across five of our own characters — Chibi Rem, Jinx, Power Girl, Sayuri and Yoda
— which is the guard working, not a regression. Peach is not among them: her nearest skirt joint
is 0.114 from the thigh axis against an 0.081 p90.

**She was PATCHED, not rebuilt, and the reason is a measurement.** Her recorded recipe does not
reproduce her. The rebuild from `source/model.fbx`, 1.70 m, `smash`, with her cutout materials,
matches the installed bundle on 173 bones with **63 rotation mismatches**, and adding
`VRM_EXPORT_POSE=rest` makes it worse at 71. So rebuilding her would have shipped a pose change
nobody asked for alongside the spring fix — which is exactly the mistake Miku's rebuild made
earlier the same day. Her real arguments are still unknown and she joins the characters with
drifted recipes.

`patch_springs.py` does both fixes to an installed bundle instead, which also reaches the 35
characters with no source file left on this machine. What it changed in her:

```
cloth: 8 chain(s), 40 joint(s) -> stiffness 0.50, drag 0.05, gravity 0.00  (from 0.85/0.80)
limbs: LeftUpperArm   _15_-_LShoulderJ   0.053 -> 0.095 (+42.1 mm)
       LeftUpperLeg   _04_-_LLegJ        0.061 -> 0.081 (+19.8 mm)
       LeftLowerLeg   _05_-_LKneeJ       0.039 -> 0.064 (+25.2 mm)
       LeftLowerArm   _16_-_LArmJ        0.032 -> 0.040 ( +7.4 mm)   (and the four mirrors)
       2 collider(s) left alone -- the head sphere and the hip capsule
read-back: 545 object(s) readable, 48 changed (expected 48), 0 gone, 0 added
```

Verified four ways. The patcher's own read-back fingerprints **every** object's full typetree
before and after, and a Mesh's typetree carries its vertex buffer bytes, so the geometry is
byte-compared and identical: 48 of 545 objects differ and they are the 40 joints and 8 colliders.
`verify_rebuild.py` against the installed file: **CULL-ONLY, DIFFERS BEYOND CULL 0** — type counts,
material state, texture names and the whole rig unchanged. `texdims.py` the same 10 textures at the
same dimensions, `bundle_audit.py` the same 6 clips / 51 humanoid / 30 fingers / 16 meshes,
`viseme_audit.py` the same (none, as before — she has never had any). The file is **68 KB smaller**,
entirely from re-deflating the container; nothing any of those tools can read differs.

The limb radii are also a genuine cross-check, because two independent implementations produced
them. The Blender fit wrote 0.081 / 0.064 / 0.095 / 0.038 and the bundle patcher 0.081 / 0.064 /
0.095 / 0.040 — three identical and the fourth 2 mm apart, because the build attributes vertices by
bone *subtree* and the patcher by *dominant weight*.

**What is still wrong.** Five other characters carry the old 0.85/0.80 cloth — **Batman, Chibi
Rem, Link, Power Girl and Yoda** — and every character built before today carries median limb
capsules. `patch_springs.py --cloth --limbs` is the tool for all of them and none of them has been
done. And nothing here has been seen in game: Peach is verified file-side only.

### Killer Clown's hat, 2026-11-15: the hat was the smaller half

Reported as hair clipping through her jester hat. Measuring it turned up a second fault that was
not reported and is worse, and both come from the same place: not the hair rigger's PARAMETERS,
which is where the last two rounds of spring work went, but its **SELECTION** — which vertices it
decided were loose hair. No stiffness, drag or collider fixes a chain that is on the wrong
geometry.

**Fault A — her eyebrows and eyelashes are on hair springs.** The rigger takes a group by mesh
name, and failing that by MATERIAL name, and the material fallback takes every mesh that shares
the material. Her hair, lashes and brows are one material, so `hairrig hair` took all three:

| mesh | vertices on a hair spring chain |
|---|---|
| `brows` | **146 of 146** |
| `lashes` | **2,357 of 4,640** (and all 4,640 carry some spring weight) |
| `hair` | 387 of 731 |

So 2,503 of the 2,890 vertices her four chains move are facial features, swinging on hair physics
across her face, and her own mesh names say `brows` and `lashes`. Nothing asked them. A material
is shared by whatever the author chose to share it with, and on an anime-styled model that is
routinely the lashes and brows, drawn with the hair's own texture — a mesh-name match is a
deliberate instruction and a shared material is an inference, and the two were treated as the same
evidence. The name is now consulted when the evidence is only a shared material; a mesh the
pattern names directly is still taken, so `hairrig lashes` still rigs the lashes.
`VRM_HAIRRIG_FACE=1` restores the old behaviour.

**Fault B — the hair it did rig is sealed inside the hat.** Of the 387 hair vertices on the
chains, **371 (96%) are inside the hat shell**, up to 51.8 mm deep, while **95% of the 344 the
rigger left rigid are outside it**. The physics went on the hair nobody can see and the visible
hair stayed rigid. The only observable effect those chains have is the reported fault.

The shell test is the sign of the dot product between a point and the nearest surface's normal.
Its control is the head's own flesh: a scalp vertex must read inside the hat and a nose vertex
outside it, and they do — scalp −26 to −12 mm, nose +68 to +72 mm.

**Why not an inside collider.** UniVRM does implement `SphereInside` and `CapsuleInside`
(`SpringBoneCollision.TryResolveSphereCollisionInside`), and confining the hair under the hat is
the physically right description, so this was the first candidate. Her own numbers rule it out. A
collider constrains a JOINT — a sphere of `hit_radius`, 20 mm, at the bone's tail — and what
breaches the hat is the MESH, hanging up to 64 mm past that joint. Dividing each vertex's
clearance by its lever arm gives the angle at which it comes through:

| | breach angle |
|---|---|
| 16 of the 387 | already outside the shell at rest |
| p10 of the rest | **2.9°** |
| median | 9.3° |
| max | 62.7° |

Nothing that confines the joints saves geometry with 3 mm of room at 60 mm of radius, and
shrinking the sphere until it did would pull her hair into her scalp at rest. So the chains were
removed, not re-parameterised — and for the same reason stiffening them is not a fix either: a
stiffer spring still moves, and these have 2.9° of room.

**The attachment test was not the bug, and the margin says why.** The rigger measures which end of
a hair group is attached by comparing the two ends against the MIDDLE of the anchor bone, and runs
the chain away from the nearer one. On her hair it chose the BOTTOM — chains running *upward* —
over the TOP by **13.4 mm out of 135, a 9.9% margin**. That test asks which end is attached and
assumes the other one swings. On a cap of hair both ends sit on the scalp, so it is deciding
between two nearly equal numbers. The answer is not that it picked the wrong end; it is that
neither end is loose, which is what the new rule measures directly.

**Two sweeps, and the first one was wrong.** The sweep written to ask whether any other character
has sprung hair sealed inside a rigid head mesh pooled EVERY spring-driven vertex and tested it
against any rigid head mesh with no bound on distance. A nearest-vertex normal describes the
surface it belongs to and nothing further away, so at range it returned confident nonsense:
**Peach's SKIRT as 1,583 mm "inside" her crown**, and Heels' hem 447 mm inside a mesh called
`CC_Base_TearLine`, which was only in the shell list because `ear` is a substring of `TearLine`.
It also diluted Killer Clown's own 96% to 8%, by averaging her hair in with the 4,200 vertices her
CHEST springs drive. Corrected — hair chains only, reported per chain, and a point outside the
shell's bounding box or more than 50 mm from its surface gets NO answer rather than a wrong one —
it reproduces her 371 and reports zero elsewhere. Both tools now carry that bound.

Swept over all 65 installed bundles with the corrected test, **Killer Clown is the only character
with a facial feature on a spring chain**, and the only one with hair sealed in a shell. The tool
itself was then run as a dry run over all 65 as its own control, and flags her four chains and
nothing else: 29 characters with spring chains report nothing to remove, and 36 have no spring
chains at all. The sweep's limit is worth stating: it can only see a mesh whose NAME says what it
is, and a dozen characters have theirs on `Plane`, `Mesh.001` or `default`, where no name test can
look.

**Patched, and the rebuild is the control.** `patch_springs.py --unrig-hair` removes a chain from
the `Vrm10Instance.SpringBone.Springs` array, which is the single source of truth — the runtime
builds its simulation buffers from it and never looks for joint components on its own, so an
orphaned `VRM10SpringBoneJoint` is inert. Her BONES stay, all 16 of them, so every vertex keeps the
position the model gives it and only the motion stops. Her four chains went, both chest chains
stayed at 1.00/0.90, and her two colliders were untouched.

Her source does still exist (`killer-clown-v2-balatro-style.zip`, `source/Catwalk Walking.fbx` —
a Mixamo export, which is where her stripped-prefix bone names come from), so she was also rebuilt
with the fixed rigger. That is not what was installed; it is the control, and it is two independent
implementations of the same two rules agreeing:

```
hair rig: 'brows' shares a material matching /hair/, but its own name says it is not hair -- NOT rigged
hair rig: 'lashes' shares a material matching /hair/, but its own name says it is not hair -- NOT rigged
hair rig: 'jester hat' is rigid on 'Head' -- treating it as a shell the hair must stay out of
hair rig: strand 0 is 74% sealed inside 'jester hat' (deepest 28 mm) -- NOT rigged
hair rig: strand 1 is 86% sealed inside 'jester hat' (deepest 50 mm) -- NOT rigged
hair rig: strand 2 is 71% sealed inside 'jester hat' (deepest 50 mm) -- NOT rigged
hair rig: strand 3 is 82% sealed inside 'jester hat' (deepest 19 mm) -- NOT rigged
spring bone chains added: 0        breast spring chains added: 2
```

Blender uses `closest_point_on_mesh`, an exact FACE normal; the patcher has only nearest-vertex
normals on the exported geometry. The deepest depths agree to about 2 mm — 28/29.0, 50/47.2,
50/47.6, 19/19.7 — and the rebuild lands on the same outcome the patch did, 0 hair chains and 2
chest chains. The sealed FRACTIONS differ (71–86% against 93–97%) because the denominators are
different populations: Blender's is the strand's loose vertices, the patcher's is what the chain
dominates in the exported mesh. Both are far above the 50% the rule needs.

**Verified four ways**, as with Peach. The patcher's read-back fingerprints every object's full
typetree: **1 of 325 objects changed, 0 gone, 0 added** — the one `Vrm10Instance`. `verify_rebuild.py`
against the installed file: **CULL-ONLY, DIFFERS BEYOND CULL 0**. `texdims.py`: the same 10
textures at 1024×1024. `bundle_audit.py`: the same 6 clips / 1 controller / 52 humanoid / 30
fingers / 14 meshes. A second `--unrig-hair` run on the result reports "nothing to do", so it is
idempotent and at target. Backup `character-backups/Killer Clown.prehairrig-2026-11-15.yargchar`,
md5 `2521f356…`, matched against the live file before it was replaced; installed md5
`ca62c1fd…`, 7,880,410 bytes against 8,133,085.

**What is still wrong.** The orphaned collider group is still in her file, referenced by nothing —
harmless, and left rather than add a second kind of edit to verify. Her hair is now entirely rigid
on her head, which is what 344 of its 731 vertices already were and what the hat requires; if she
is ever reported as having stiff hair, the fringe below the hat brim is the part that could
legitimately swing and it has never been rigged. And none of this has been seen in game.


### Spartan Mark V's right leg, 2026-11-15: a limb in the wrong PLACE, which no angle can see

Reported as an asymmetric right leg. It is one number: his `thigh.R` sits **92.12 mm** from the
mirror of his `thigh.L`, and every other bone in his rig is an exact mirror — rotations to six
decimal places, and `shin`, `foot`, `toe` and `heel.02` to 0.000 mm. His whole right leg hangs off
that one bad offset.

**Why nothing caught it.** `limb_check_installed.py` measures joint ANGLES and their left/right
asymmetry, and its own calibration is right that asymmetry is the signal to trust — elbow and knee
asymmetry is exactly 0.0 across all 66 characters. But an angle is blind to a limb that is
RIGIDLY displaced: his knee and ankle angles match his left side to four decimals, because the
whole leg moved together. That is why the sweep for "bent or asymmetric limbs" closed at **0 new**
while his right leg stood 30 mm clear of its own hip socket.

**The seam is what proves which side is wrong.** Mirror arithmetic alone cannot say whether the
right leg is misplaced or the left one is, so the question was asked without reference to either:
how far is each thigh's flesh from the TORSO it hangs off?

| | nearest torso vertex, over the top fifth of the thigh |
|---|---|
| `thigh.L` | min **4.6** mm, p10 10.4, median 33.9 |
| `thigh.R`, as shipped | min **29.7** mm, p10 39.8, median 58.7 |
| `thigh.R`, after the fix | min **4.6** mm, p10 10.4, median 33.9 |

Identical to the left on every statistic. And the torso it joins is symmetric on its own account:
every spine bone's flesh mirrors ITSELF in its own frame, `spine.001` — the hips, 2,509 vertices,
1,168 a side — to a maximum of 0.00 mm. So the socket was in the right place and the leg was not.

Two more measurements say the leg itself is intact rather than deformed. In each thigh's own frame
his two legs are **identical to 0.0 mm** on all three joints, with the same vertex counts
(665/1066/695 a side). And `spine` and `spine.001` went from a 6.85 mm self-mirror error to
**0.00 mm** when the bone moved, because the displaced thigh had been dragging the blend-weighted
vertices around his right hip out of symmetry with it.

**His source is not like this.** `halo-mk-v-model.zip` → `source/MkVSKETCHFAB.blend` — which means
the README's list of characters "whose source archive was never located" is stale for him. Its
armature is an exact mirror, 0.000 mm on head and tail for every leg bone, and its FLESH is an
exact mirror too, 0.00000 units, measured in armature space. His bundle is ours — `_Character`
root, `SpartanMarkV_0..5` materials, the `MKV_*_Metallic.png-MKV_*_Roughness.png.standard` merge
names — so the displacement was introduced between the `.blend` and the bundle.

It is not introduced by today's pipeline. Rebuilt from that source at `rigify_plain` / 2.146 m,
the resulting `.vrm` is **0.000 mm out of mirror on every leg pair**, so there is no builder bug to
fix and nothing to sweep for. His `.blend` does carry an action with a pose, and both thighs have
pose TRANSLATIONS in it that are not mirrors of each other (0.121 against 0.078 units), so a build
that baked that pose would produce something like this; the installed bundle differs from today's
build in more than the one bone (his `thigh.L` is at a different offset entirely, with its X sign
flipped), so it was built with arguments or a pipeline that no longer exist. **He was patched, not
rebuilt**, for the Peach reason: the rebuild is a different character build and shipping it would
ship unasked-for changes alongside the fix.

**Four structures hold that one offset**, all parent-relative and all in the same representation:

```
Transform.m_LocalPosition
Avatar.m_Avatar.m_AvatarSkeletonPose.data.m_X[67].t
Avatar.m_Avatar.m_DefaultPose.data.m_X[67].t
Avatar.m_HumanDescription.m_Skeleton[thigh.R].m_Position
```

The Avatar's arrays are nested under a `data` key, and a first probe read them one level too
shallow: `m_AvatarSkeleton.m_ID` and all three pose arrays came back as **empty lists rather than
an error**, which reads as "the Avatar carries no skeleton, so the Transform is the only place to
patch". It carries one in triplicate, and Unity retargets humanoid animation through it. An empty
container and an absent one look identical from a `.get()`.

**The check that was missing, and ~~two~~ THREE versions of it that were wrong.**
~~`mirror_check_installed.py`~~ — **deleted the same day; `limb_socket_check_installed.py` replaces
it, and the correction below says why.** It compared each limb bone's LOCAL offset from its parent,
X negated, against its partner's. Three decisions, the first two of which a first attempt got
backwards and the third of which was itself wrong:

- **Local, not world.** World folds in every ancestor's rotation, so it measures the rest POSE as
  much as the skeleton. On him the world comparison flags **29 of 29** pairs — his fingers
  included, at 190 mm — because his authored stance is twisted. The local comparison flags one.
- **The humanoid map, not bone names.** Pairing `.L`/`.R` by pattern drags in every finger, hair
  strand, IK target and spring helper, and a flat 2 mm threshold over all of them "found" **39 of
  65** characters: Adachi Rei's IK leg target at 2,850 mm, Harley Quinn's little finger at 167 mm,
  Mario at 458 mm. Those are the test breaking, not the rigs. The eight humanoid limb pairs are
  the ones the game animates a limb through.
- **The character is its own control.** A local offset lives in its PARENT's frame, so negating X
  is the true mirror only where the parent frames are themselves mirrored. Where that fails it
  fails for nearly every pair at once, so a character is judged only when two thirds of its pairs
  mirror and a rig that fails wholesale is reported as NOT MEASURABLE by count. **This was the
  version that was wrong**, and the sentence above contains the reason without drawing it: it is
  not enough that the two parents be mirrors of each other, because when they are THE SAME BONE
  its own roll corrupts the comparison, and the wholesale-failure guard cannot see a fault that
  afflicts one pair. The three slots whose left and right share a parent — UpperLeg, Shoulder,
  UpperArm — are the only ones it ever flagged.

Swept over all 65: ~~**41 clean, 17 not measurable, and 9 displaced limb bones across 7
characters.**~~ **WITHDRAWN the same day — the tool was unsound and none of these nine numbers is a
mirror discrepancy. See the correction below.**

| character | limb | ~~out of mirror~~ **not a measurement** |
|---|---|---|
| ~~Kronk~~ | ~~UpperLeg~~ | ~~226.04 mm~~ — 30.48 mm in world, and his mesh was never mirrored |
| ~~Sayuri~~ | ~~UpperLeg~~ | ~~220.59 mm~~ — **0.05 mm in world. Nothing was ever wrong** |
| ~~Kronk~~ | ~~Shoulder~~ | ~~144.56 mm~~ |
| **Spartan Mark V** | **UpperLeg** | ~~92.12 mm~~ — real fault, wrong number; see the correction |
| ~~Jessica Rabbit~~ | ~~UpperArm~~ | ~~30.58 mm~~ |
| ~~Alastor~~ | ~~UpperLeg~~ | ~~27.93 mm~~ |
| ~~Jessica Rabbit~~ | ~~Shoulder~~ | ~~11.36 mm~~ |
| ~~Elite Terrorist~~ | ~~UpperLeg~~ | ~~7.26 mm~~ |
| ~~The Mandalorian~~ | ~~UpperLeg~~ | ~~6.42 mm~~ |

The check finds CANDIDATES, not faults, and that distinction is load-bearing. Alastor, Elite
Terrorist and the Mandalorian are pure `dz` offsets — one thigh further forward than the other in
the parent's frame — which is what an authored stance looks like, and only the seam test can tell
that from a displacement. Spartan Mark V earned the fix because his source is provably symmetric
AND his socket had a 25 mm gap in it. None of the other six has been looked at.

**Verified.** `patch_mirror.py` refuses unless the named bone is the sole outlier in a rig that
otherwise mirrors, so it cannot be pointed at a rig where negating X is not the mirror. On him:
**2 of 225 objects changed** — one Transform and the Avatar — 0 gone, 0 added.
`verify_rebuild.py` names the change exactly: `*** 1 bone(s) moved: thigh.R`, with every type
count, material, texture and other bone identical. `bundle_audit.py` the same 6 clips / 1
controller / 52 humanoid / 30 fingers / 6 meshes; `texdims.py` the same 23 textures at the same
dimensions. A second run reports "every limb pair mirrors", so it is idempotent. Backup
`character-backups/Spartan Mark V.preleg-2026-11-15.yargchar`, md5 `7a652564…`, matched against
the live file before replacing; installed md5 `cd31325a…`, 20,002,228 bytes against 20,421,828.

**What is still wrong.** His rest pose is still the authored twisted stance — `spine` carries a
rotation, so his limbs are mirrored in the SKELETON and still not mirrored in world space, his
arms worst at 198 mm. That is his whole upper body, not his leg, and nobody has reported it. The
six other candidate characters above are untouched. And none of this has been seen in game.


#### CORRECTION, later the same day: `mirror_check_installed.py` was unsound and its nine findings were not

Sent to look at the two worst candidates it had reported, **Kronk at 226.04 mm and Sayuri at
220.59 mm**, and neither is a fault. The tool was wrong, and it was wrong in a way that explains
every one of its findings.

**What it did.** It compared each limb bone's LOCAL offset from its parent with X negated.
Negating X is the mirror only when the parent's own axes put X along the body's left-right line —
and that is the rig's intrinsic axis convention, not something readable back out of the file.

**Sayuri is the proof.** Her `CC_Base_Pelvis` is rolled **90.2°** and both thighs hang off it, so
the comparison in its frame means nothing. Her leg bones' WORLD positions tell the truth:

| | left | right | out of mirror |
|---|---|---|---|
| `CC_Base_L/R_Thigh` | (−0.0948, 0.9202, 0.1016) | (+0.0947, 0.9202, 0.1016) | **0.05 mm** |
| `CC_Base_L/R_Calf` | | | 0.05 mm |
| `CC_Base_L/R_Foot` | | | 0.05 mm |
| `CC_Base_L/R_ToeBase` | | | 0.05 mm |

Every one of her eight limb pairs is 0.05 mm. **There was never anything wrong with her legs.**

**And it explains the pattern.** All nine findings were `UpperLeg`, `Shoulder` or `UpperArm` —
precisely the three slots whose left and right hang off ONE bone. Where the parents are each
other's MIRROR the local offsets carry the mirror themselves and read 0.00 correctly, which is why
nothing else ever flagged. The one case the tool could get wrong is the only case it reported.

**Kronk is the same artefact with a second reason to leave him alone.** 226.04 mm by that measure,
**30.48 mm** in world. And his mesh was never mirrored at all: his thighs carry **54 and 45
vertices**, and all eight of his limbs differ in their own bones' frames by 18 to 80 mm. Nothing
about his two sides is comparable. His source is `Kronk_Doing_the_Hokey_Pokey.usdz` and the README
already records that "he LOOKS T-posed and is not". Both his legs join his body — 25.2 mm against
29.0 — so there is no fault to fix.

**Spartan Mark V's fix stands, but one number reported for him does not.** "92.12 mm out of
mirror" was that same corrupted reading; his `spine` is rotated 24.6° with a real Y component, and
the true mirror of his left thigh's offset differs from the naive one by **84.8 mm**. What the fix
rested on was never the mirror arithmetic:

- his SOURCE armature and flesh are exact mirrors, 0.000 mm and 0.00000 units;
- a rebuild from it today is 0.000 mm out on every leg pair;
- his right thigh's flesh sat **29.7 mm** clear of a socket his left thigh sat **4.7 mm** inside,
  and after the fix reads **4.6 mm** — his left leg's own figure;
- his lower torso's self-mirror error went from 6.85 mm to **0.00 mm** when the bone moved.

All four are independent of any axis convention. The new check, run against his pre-fix backup and
his shipped file, flags the first and clears the second, which is the cleanest confirmation
available that the fix landed where it should.

**The replacement measures THE JOIN.** `limb_socket_check_installed.py` asks, for each limb that
attaches to the torso, how far the nearest part of its flesh is from the nearest torso vertex. That
needs no reference to the other side and no axis convention; the other side becomes a control
rather than the measurement. Two calibration decisions, both from the installed set rather than
guessed: a limb flags only when the two sides' gaps differ by **≥ 10 mm AND ≥ 2×** (Spartan 25.1 mm
at 6.4×, Kronk 3.8 mm at 1.15× — they separate with room), and a pair whose two sides carry
materially different vertex counts is **declined rather than judged**, because then nothing about
them is comparable.

Two details that cost a measurement each. The limb's flesh is its bone's whole SUBTREE down to the
next mapped humanoid bone, because a Character Creator rig deforms through `*_Twist` bones —
Sayuri's `CC_Base_L_Thigh` dominates zero vertices while her `ThighTwist01/02` dominate thousands.
But the TORSO reference is the mapped spine chain ONLY, deliberately not its subtree: expanding it
was tried and it destroyed the measurement, because Spartan Mark V's `pelvis.R` is an unmapped
child of his hips whose flesh sits right beside his displaced thigh, and counting it as torso
closed his 29.7 mm gap to 5.4 mm and made the fault disappear.


#### Scott Hall, and the fourth version of this measurement

Sent to look at the socket check's worst finding — his right leg at 14.0 mm against his left at
1.1, a 13× reading. **He is sound, and the check was wrong again.** This is the fourth version of
this measurement and the third to over-report, which is the most useful thing on this page.

**He is sound, three ways.** His thighs carry **1,326 and 1,325 vertices** and sit **2.69 mm**
apart in their own bones' frames. His thigh bones mirror to 3.15 mm — and **his SOURCE armature
carries the same 3.07 mm**, measured in `Scott-Hall_2K20.blend` at 0.3074 units against an armature
scale of 0.01, so the build introduced nothing; a Mixamo auto-rig is simply a little asymmetric,
and his worst pair there is a finger at 13 mm. And the two sides' distances to his torso are the
same distribution:

| | min | p10 | median |
|---|---|---|---|
| `LeftUpLeg` | **1.1** | 17.8 | 49.1 |
| `RightUpLeg` | **14.0** | 20.7 | 46.0 |

Only the single closest vertex differs. **The check read the MINIMUM** — the most noise-sensitive
statistic available, where one vertex that happens to land near one torso vertex sets the answer.
It now reads the **p10** of the near region, which says the same thing about a real displacement
(Spartan Mark V: 11.6 against 39.8) without being hostage to one vertex. On p10 Scott Hall reads
2.9 mm at 1.2×, and so does Yui Suzukaze, the other finding that evaporated — her minima were
22.2 against 7.4 and her p10s are 37.1 against 27.4.

**Changing the statistic changed WHICH characters were named, not just how many**, and that is
worth more than either list. On minima the sweep found Scott Hall, Vegeta and Yui Suzukaze. On the
p10 it found **Vegeta and Peacemaker** — Scott Hall and Yui dropped out, and Peacemaker appeared,
whose two minima are *identical* at 8.4 mm while his p10s are 10.5 against 32.1. A finding set that
reshuffles under a change of summary statistic is a weak signal being read as a strong one, and the
only entry that survived every version is the one real fault.

**And a vertex count is not enough to say two limbs are the same object.** Vegeta has upper arms of
**818 and 827 vertices** — within 5%, so the count gate passed them — that differ by **45.2 mm in
their own frames**. Every limb he has differs in frame, by 4.9 to 45.2 mm, and so does every limb
Kronk has. Both are hand-modelled characters whose meshes were never mirrored. The check now
declines a pair that differs by more than 10 mm in frame whatever its counts say, because that is
the question of whether the two limbs are the same object at all and it has to be answered before
any comparison between them is worth making.

**The same two corrections went into the patcher**, and they matter more there. Its guard was
measuring minima, so on `RightUpLeg` it would have read Scott Hall at 1.1 against 14.0, accepted
him, and moved a leg that was already attached. It now refuses him in those words — *"moving a bone
that is already attached would detach it"* — and refuses Kronk and Sayuri for want of comparable
flesh, while still accepting Spartan Mark V's pre-fix backup and reproducing his shipped file byte
for byte.

**What this cost and what it bought.**

| version | measures | found |
|---|---|---|
| 1 | local offsets, `.L`/`.R` names, flat 2 mm | **39 of 65** — mostly fingers and IK targets |
| 2 | local offsets, humanoid limbs | **9** — every one the case a rolled shared parent corrupts |
| 3 | the join, on MINIMA | **3** — Scott Hall, Vegeta, Yui Suzukaze |
| 4 | the join, on a p10 | **2** — Vegeta and Peacemaker; Scott Hall and Yui gone |
| 5 | the join, p10 + in-frame gate | **1** — Peacemaker |

Every version was plausible, every version printed confident millimetres to one decimal place, and
the only thing that separated them was going and measuring the characters they named. Spartan Mark
V's leg is the one fault any of them found, and it was found by version 2 — whose arithmetic was
wrong, and which named him for a number that meant nothing.

**One candidate is left and is NOT examined: Peacemaker's right leg**, p10 10.5 mm against 32.1 at
3.1×. His two minima are *identical* at 8.4 mm, so his leg touches the body at a point and is
generally further from it — which is the shape of a limb ROTATED in its socket rather than
translated out of it, and a different thing from Spartan Mark V's fault. He also already appears
in this file for a leg that reads 27.9° off vertical. Nobody has looked.


#### Peacemaker, and the end of the summary statistic

The last candidate, and he is sound too. His seven limb bone offsets mirror to **0.00 mm**, every
one of them. What flagged him was the p10, and this is why it was wrong — the two sides' whole
distance distributions, decile by decile:

| | q0 | q10 | q20 | q30 | q40 | q50 | q60 | q70 | q80 | q90 |
|---|---|---|---|---|---|---|---|---|---|---|
| left `n187` | 8.4 | 10.5 | 19.3 | 49.1 | 52.6 | 57.7 | 61.2 | 83.2 | 92.2 | 97.0 |
| right `n191` | 8.4 | 32.1 | 46.1 | 49.8 | 49.9 | 56.9 | 59.1 | 87.9 | 94.4 | 95.3 |
| difference | **+0.1** | +21.7 | +26.8 | **+0.7** | **−2.8** | **−0.8** | **−2.1** | +4.8 | +2.3 | **−1.8** |

**Two deciles out of eleven differ.** They agree at the closest point, agree from q30 on, and
reverse sign four times. Against Spartan Mark V's displaced leg, which is the shape a rigid
displacement actually makes:

| | q0 | q10 | q20 | q30 | q40 | q50 |
|---|---|---|---|---|---|---|
| Spartan, right − left | **+25.1** | **+28.1** | **+26.7** | **+27.8** | **+26.8** | **+24.8** |

About 25 mm at every quantile, because the whole leg moved as one piece. That is the difference
between a limb out of its socket and two sides whose topology differs slightly — and Peacemaker's
does: his thighs carry 414 and 402 vertices and sit 7.03 mm apart in their own frames, and six of
his seven limbs differ in frame at all.

**And that asymmetry is his, not ours.** His source `Peacemaker_John_Cena_-_Rigged.usdz` holds
8,449 vertices of which **3,929 sit right of centre and 4,520 left** — a difference of 591 — and
each sampled right vertex is a median **4.74 mm** from its nearest mirrored left one, p90 7.32 mm.
His model was never mirrored, the scatter in the source is the same size as the 7.03 mm in his
bundle, and the build carried it through unchanged. Same conclusion as Scott Hall, reached the same
three ways.

**So the criterion is no longer a summary statistic.** A limb flags only when it is further from
the body at EVERY decile from q0 to q50 — distributional dominance over the near half — by at least
10 mm at the weakest of them. That is what "this limb is further from the body" means, it was
derivable before any of this, and it is the thing three earlier versions each approximated with one
number that happened to move. Spartan Mark V's weakest decile is +24.8 mm; Peacemaker's profile
changes sign, so his is 0.

Yui Suzukaze is the useful near-miss: her left upper arm IS consistently further out, −15 −10 −10
−7 −10 −8, so the sign never changes — and the weakest is 7.2 mm, under the threshold. A mild
genuine asymmetry, correctly not called a fault.

**The decision now lives in ONE function**, `decide()`, called by both the check and the patcher.
It had lived in two, and the duplication bit twice: each time the criterion was sharpened the check
got it and the patcher kept the old one, so the tool that MOVES A BONE was briefly willing to
accept characters the tool that only reports had already cleared. Pointed at Peacemaker's `n191`
the patcher now refuses him, and the only reason it did no harm before the fix is that his bone was
already at the target.

**Six versions, one fault.**

| version | measures | found across 65 |
|---|---|---|
| 1 | local offsets, `.L`/`.R` names, flat 2 mm | 39 |
| 2 | local offsets, humanoid limbs | 9 |
| 3 | the join, on minima | 3 |
| 4 | the join, on a p10 | 2 |
| 5 | + an in-frame gate | 1 |
| 6 | the join, dominant across q0..q50 | **0 installed — and it still flags the real fault** |

**A check that ends up reporting zero after six versions has to answer for itself**, so: three
things say this is not a threshold tuned until the complaints stopped.

1. **It still flags the fault.** Run against Spartan Mark V's pre-fix backup it reports his right
   leg at +24.8 mm on the weakest decile. That fault was verified three ways that have nothing to
   do with this check — a provably symmetric source, a rebuild 0.000 mm out, and a socket gap that
   closed to his left leg's own figure when the bone moved. The installed set reads zero because
   he is fixed and he was the only one.
2. **The criterion was derivable before any of this.** A rigid displacement moves the whole near
   region; that is what rigid means. Versions 3, 4 and 5 each approximated it with one number, and
   the sharpening was towards the thing that was always correct rather than away from an answer.
3. **It is not blind.** Yui Suzukaze's left upper arm is consistently further out at every decile
   — −15 −10 −10 −7 −10 −8, sign never changing — and comes out at 7.2 mm on the weakest, under
   the 10 mm threshold. The check reports that profile rather than hiding it; a genuine mild
   asymmetry is visible in the output and simply not called a fault.

64 of the 65 report "every limb joins the body"; the one that does not has too little torso flesh
to measure a join against and says so.


### Sophia's shine, 2026-11-15: not her defect, the pipeline's default

Reported as shiny, and explicitly not the Thanos fault — there is no glossiness map to invert
because there is no second map at all. Her whole material state is five lines:

```
Sophia_0   Universal Render Pipeline/Lit
  _Smoothness 0.50   _Metallic 0.00   _SpecularHighlights 1.00   _EnvironmentReflections 1.00
  keywords: (none)
  tex _BaseMap / _MainTex  rp_sophia_animated_003_dif
```

One material for the entire character, one base map, and nothing else — no normal map, no
metallic/gloss map, no occlusion map. Her source archive holds exactly two files,
`source/rp_sophia_animated_003_idling.fbx` and `textures/rp_sophia_animated_003_dif.jpeg`, so the
build dropped nothing: a RenderPeople scan at this tier ships diffuse only.

**That 0.50 is URP/Lit's own default, and it is not hers.** The exporter builds a fresh URP/Lit
material and lowers nothing unless `YARG_NO_SHINE_MATERIALS` names it or it is an untextured
near-black outline shell. So she inherits the shader's defaults, and so does most of the roster:

| | |
|---|---|
| installed characters on URP/Lit at `_Smoothness` 0.50, specular and reflections ON | **63 of 65** |
| of those, with NO normal map AND NO metallic/gloss map — a completely uniform specular | **27** |
| with the no-shine switch actually applied | **1** — Alastor |

**Three things ruled out, each measured rather than assumed.** Her albedo is not an outlier: 12.7%
of it is above 0.80 luminance against Gwen Stacy's 79.1%, and its p99 is 0.859, so it is not a
blown-out photograph. Her base map is sRGB (`m_ColorSpace` 1), like all 57 installed base maps, so
this is not a colour-space fault. And her material carries no emission map and a black
`_EmissionColor`, so nothing is glowing.

What is left is the mechanism, and it is sufficient: a 0.5 specular lobe and a full sky reflection
applied at one uniform value to photoscanned skin, denim and shoes alike, with no roughness map to
vary it and no normal map to break up the reflection. Nothing else in her file can produce a
highlight.

**So this is a judgement about appearance, not a defect, and the project had already made it.**
`docs/character-models.md` records it for Alastor: *"URP/Lit's default smoothness and environment
reflections read as a sky tint on a flat toon character"*, fixed with `YARG_NO_SHINE_MATERIALS`,
and *"the editor shows the difference much less than the game does, so the editor is not a guide to
how bad the shine looks."* She is the character on whom it shows, because a uniform plastic
specular over a photoscan of a real person reads as wrong in a way it does not on Shrek or Mickey
Mouse.

**It was applied to her alone, not swept — and then Jay said to sweep it, so it was.** Both halves
of that matter. The recommendation was to stop at her: smoothness 0 is fully matte, the editor is
on record as a poor guide to how the shine reads in game, and 27 characters is a roster-wide
appearance change made on the strength of a tool default — the mistake a previous session nearly
made with `doubleSided`, where every file reported `true` because Blender defaults it. An
appearance judgement across a third of the roster is the owner's to make, not a measurement's,
which is why it was put as a question rather than done. **Jay answered "yes, all 26"**, so the
other 26 are flattened too; the sweep is below. `patch_shine.py` takes `--smoothness S` if matte
turns out to look dead on any of them, and every one has a hash-verified backup, so reverting any
single character is a file copy.

**That documentation was also stale, and the files are the record.** The same passage says Heels,
Gwen Stacy and Ariel *"were also installed no-shine (`*`) to compare"*. They are not: all three
read `_Smoothness 0.50`, specular 1, reflections 1 in the installed bundles. Those comparison
builds were never what shipped, or were replaced. Alastor is the only one.

**A documented known bug, fixed while here.** The same passage records: *"the exporter sets
`_Metallic` to 1 for any material with a metallic map AFTER this switch runs, so for those
materials the switch is only partly applied."* It was still true — the no-shine block zeroed four
floats and three statements later `if (mr != null)` bound the gloss map, re-enabled
`_METALLICSPECGLOSSMAP` and set `_Metallic` back to 1, which also routes smoothness through the
map's alpha. Flattening now happens LAST and declines the map outright, because a material asked
to have no shine does not want a gloss map either, and it logs what it did. Of the installed set
this would have affected Alcina (6 materials with a metallic map), Ariel (22), Scott Hall (13) and
the others that carry one — nobody had asked them to be flat, so nothing shipped wrong, but the
switch would not have worked if they had.

**The keywords are the part that matters.** URP/Lit branches on `_SPECULARHIGHLIGHTS_OFF` and
`_ENVIRONMENTREFLECTIONS_OFF`; the floats are what the material inspector uses to set them. A
patch that wrote only the floats would look correct in a dump and change nothing in the game, so
`patch_shine.py` writes both.

**Alastor is the control, and he is a strong one.** He is the one character built with the switch
on, so his material is the target state rather than a state I derived. Run against him the tool
reports **"already flat, nothing to do"** on all three of his materials — the patcher and the
exporter agree exactly. Sophia's patched material now matches his line for line: the same two
keywords and the same seven shine values.

**Verified.** 1 of 225 objects changed — the single Material — 0 gone, 0 added.
`verify_rebuild.py` names it: `*** 1 material(s) differ beyond cull: Sophia_0`, with the rig,
texture names and type counts identical. `bundle_audit.py` the same 6 clips / 1 controller / 52
humanoid / 30 fingers / 1 mesh; `texdims.py` the same single texture at 2048×2048. A second run
reports "already flat". Backup `character-backups/Sophia.preshine-2026-11-15.yargchar`, md5
`74925073…`, matched against the live file before replacing; installed md5 `990bb92a…`, 6,159,657
bytes against 6,357,467.

**What is still wrong.** Her base map is 2048×2048 against the house setting of 1024, which is
hers alone among the one-material characters and was left alone. And none of this has been seen in
game — which matters more here than anywhere else today, because the project's own note says the
editor understates the shine. (The other 26 with a uniform default specular were untouched when
this was written and are not any more; the sweep is below.)


#### The sweep across the other 26, on Jay's decision

Asked whether to extend it, he said **"yes, all 26"**, so it was done in full. The set was
re-derived from the bundles rather than from the earlier sweep's output, and it is exactly the
characters whose **every** material is URP/Lit at the shader's own defaults — `_Smoothness` 0.50,
`_SpecularHighlights` 1, `_EnvironmentReflections` 1 — with **no** normal map and **no**
metallic/gloss map on any of them. That matters for scope: because no material in any of them has
either map, a wildcard flatten is coherent for the whole character and there is no material whose
shine was ever varying.

26 in, 39 out, 65 total. The 39 excluded, with the reason printed per character, are the MToon
VRoid models (different shader, no such properties), the characters with a normal or gloss map
somewhere, and the ones already carrying a non-default value — Alastor, who already had the switch,
and Sophia, who got it earlier the same day.

| character | materials flattened | | character | materials flattened |
|---|---|---|---|---|
| Aiko | 3 | | Power Girl | 5 |
| B1 Battle Droid | 2 | | Shaggy Rogers | 1 |
| Chibi Rem | 1 | | Shrek | 3 |
| Doom Slayer | 12 | | Skeleton Mage | 1 |
| Elite Terrorist | 2 | | Skibidi Toilet | 7 |
| Gadget Hackwrench | 6 | | Sonic | 4 |
| Joker | 1 | | Steve | 1 |
| Judy Hopps | 3 | | Tenna | 2 |
| Kronk | 1 | | The Rock | 21 |
| Mario | 13 | | Vegeta | 9 |
| Mickey Mouse | 1 | | Vigilante | 6 |
| Miku | 1 | | Xenomorph | 2 |
| Peacemaker | 8 | | | |
| Peach | 16 | | **total** | **132** |

**Backed up first, and verified by hash, not by exit code.** Each of the 26 was copied to
`character-backups/<Name>.preshine-2026-11-15.yargchar` and the copy's md5 compared against the
source before anything was patched; the script refuses to overwrite a backup that already exists,
so a second run cannot destroy the pre-change state. The installer then refuses any character
whose live file no longer matches its backup, because if those disagree something else has changed
the file since and it must not run blind over it.

**The backup loop failed first, loudly, and the failure is worth recording.** The name list was
written by Python with its default newline, so on Windows every line ends CRLF, and bash read each
name with a trailing `\r`: every path became `Aiko\r.yargchar` and all 26 reported MISSING. It is
the same one-bad-byte fault as piping a value into a Unix `read`, and the only reason it was
obvious is that it failed on all 26 at once rather than on some.

**Verification, per character, five ways and none of them sampled.**

1. `patch_shine.py`'s own read-back fingerprints every object's full typetree before and after:
   **26 of 26 report the changed count equal to that character's material count, 0 gone, 0
   added.** Peach's 545 objects with 16 changed also confirms her dress fix from earlier the same
   day is intact underneath.
2. `verify_rebuild.py` against each character's BACKUP — not against a file this sweep had already
   touched — reports **material state as the only difference on all 26**: no object-count change,
   no texture-name change, no bone moved.
3. **Uncompressed payload delta = 60 × materials, exactly, on all 26.** Not approximately: Chibi
   Rem +60 for one material, The Rock +1,260 for twenty-one, and every one in between on the
   line. Object, texture and material counts unchanged throughout.
4. Texture pixels decoded and hashed on the two biggest size drops and two controls: **identical,
   every texture**.
5. The installer refuses any character whose live file no longer matches its backup, so **26
   installed and 0 skipped** also says nothing else had touched those files in the meantime.

And the set was re-derived from the installed bundles afterwards, which is the check that nothing
was missed: **0 in, 65 out**. No character is left at URP's defaults with no normal or gloss map.

**The Rock's file fell from 26.0 MB to 7.9 MB, and the sweep stopped until that was explained.**
A 70% drop from editing 21 materials' floats is not a recompression difference, and none of the
checks above would have caught a loss: `patch_shine.py`'s fingerprint compares each object's
typetree, and a Texture2D's bytes are in the typetree **only when they are inline** — a bundle
that streams them (`m_StreamData` with a path and offset) would fingerprint identically with the
pixels gone. `verify_rebuild.py` compares texture NAMES. `texdims.py` reads dimensions out of the
header. All three would have passed an empty file.

Four measurements settled it, and nothing was installed until they had:

| | The Rock, before → after |
|---|---|
| textures, streamed vs inline | 0 streamed, **21 inline** both sides — so the fingerprint did cover them |
| texture pixels, md5 of the decoded image | **21 of 21 identical** |
| objects, and the cab | **273 → 273**, same `CAB-2680e4bb…` |
| UNCOMPRESSED object data | **100,644,790 → 100,646,050 bytes** |
| compression flags | identical (`BlocksAndDirectoryInfoCombined ǀ BlockInfoNeedPaddingAtStart ǀ 3`) |

100.6 MB of payload in, 100.6 MB out, differing by **1,260 bytes** — and that number is the
explanation. Flattening a material adds two keyword strings and four float entries, about 60
uncompressed bytes, and 21 × 60 = 1,260. The same law holds on every character checked: Elite
Terrorist +120 for 2 materials, Shrek +180 for 3, Skeleton Mage +60 for 1. **A size that had
fallen for any other reason would not land on that line**, so the delta was checked against
60 × materials for all 26 rather than for a sample.

Why the container shrinks so much is his own shape: 15 of his 21 textures are
`all_color__UNIGLTF__DUPLICATED__N`, identical inline copies of one 1024×1024 image. The
exporter's original block layout could not dedupe across them; repacking the same bytes in one
pass can. It is also why the drop tracks duplication rather than size — Elite Terrorist −35%, The
Rock −70%, Shrek −203 bytes on an 8.6 MB payload.

**Where the whole roster now stands**, swept again after installing:

| | characters |
|---|---|
| fully flat — specular and reflections off | **28** (Alastor already was, Sophia, and the 26) |
| still at URP's default | **27** — every one of them carries a normal or a gloss map |
| MToon, so no such properties exist | **5** (the VRoid models) |
| mixed, some materials flat and some not | **5** — Alcina, Alice Ivy, Jessica Rabbit, Pomni, Spider-Man PS |
| | **65** |

**What was deliberately NOT done.** The 27 still at the default are untouched: their specular
already varies per pixel through a normal or gloss map, so they are not the uniform-plastic case
and flattening them is a different question. The 5 mixed ones are untouched for a stronger reason
— somebody's build already made a per-material decision on them, and overriding that blind would
be exactly the kind of blanket change this sweep was careful about.

No per-material judgement was attempted within the 26, because it cannot be made from the bundle:
the exporter renames every material to `<Character>_N`, so `Xenomorph_0` and `SkibidiToilet_3`
carry no authoring meaning. Refining a hard-surface character to keep some shine on one part needs
the source material names, which means a rebuild rather than a patch.

**The two most likely to want it back** are the hard surfaces, where a specular highlight is part
of what the thing is: **Xenomorph**'s carapace and **Skibidi Toilet**'s porcelain. Both were
flattened with the rest. **Seen in game on 2026-11-15, Jay asked for Xenomorph's shine back and it
was restored** from `character-backups/Xenomorph.preshine-2026-11-15.yargchar` -- `verify_rebuild`
first confirmed that backup differs from the flattened file in its 2 materials and nothing else,
so the revert is exactly the shine and touches no geometry. He is back at smoothness 0.50 with
specular and reflections on, md5 `7fe424b4`. Skibidi Toilet was not mentioned and is left matte. `patch_shine.py --smoothness S` softens one without reverting it, and the hash-verified
backup makes a full revert a file copy. Nothing here has been seen in game, and the project's own
note is that the editor understates the difference.


### FOUND, exactly: the POSE RESET, and her authored pose is her shape

`VRM_TRACE_OFFSET="teeth,eye"` plus three temporary probes put the jump before the trace at
"actions settled" -- which is BEFORE the CHILD_OF conversion, before the bone-parent conversion,
before the T-pose step, before the pose bake and before the shape-key drop. All five had been
suspected and all five run later.

It is this, at the top of the file:

```python
if _had_anim and not _keep_anim_pose:
    for pb in arm.pose.bones:
        pb.matrix_basis.identity()
```

Her eyes are bone-parented to `MCH-eye.L/R`, so clearing the pose returns those bones to rest and
takes her eyes with them, while her face follows the armature modifier and her unweighted teeth
follow nothing at all. **Her authored pose is her SHAPE** -- the same case as Alcina Dimitrescu,
whose static pose is why she is 9 feet 6 inches. The difference is that Alcina has no action
attached, so the automatic test already spares her; Gadget has one, so it does not.

**Proved by forcing the pose to be kept.** The teeth-to-eye offset then holds at the source value
through every later stage instead of jumping:

| stage | pose reset (shipping) | pose KEPT |
|---|---|---|
| after import | -0.0123 | -0.0123 |
| after CHILD_OF | **-0.1211** | -0.0085 |
| after realign | -0.1211 | **-0.0123** |
| after pose bake | -0.1211 | **-0.0123** |

**But keeping the pose is not a one-line fix.** With it set the build ABORTS: *"mesh DATA measures
1.2844 m but the target is 1.3000 m. A scale is still hiding in an object transform."* A kept pose
has to be baked into rest and then scaled, and that path does not currently handle it. So the flag
is NOT in the tree -- the cause is settled and the fix is not.

**Why the obvious fix aborts, and what it would really take.** With the pose kept the build stops
at the height gate -- mesh DATA 1.2844 m against a 1.3000 m target -- and the abort blames "a
scale hiding in an object transform", which is not what is happening. The built-in `VRM_DEBUG`
report says plainly:

```
DBG armature world_scale=(1.0,1.0,1.0)  bone[0]=root rest_len=1.0568  pose==rest: False
```

Every object scale is 1.0. The pose simply was not baked -- and `bake_pose_to_rest` cannot bake
it, because it decides there is something to bake by testing each bone's `matrix_basis` against
identity. A Rigify DEF bone has an IDENTITY basis and is deformed by CONSTRAINTS, so the test
sees nothing while the rig is bent.

**That residual is always there.** Built normally, with the pose reset, `pose==rest` is `False`
too -- the data lands at 1.2987 against 1.3000, 0.1% out, comfortably inside the 1% gate. Keeping
the pose makes the same residual twelve times bigger, 1.2% out, and the gate fires. The gate is
right; the bake is what is incomplete.

So the fix is to bake when the EVALUATED pose differs from rest rather than when a basis is
non-identity -- a small change to one test, and one that would alter the build of **every
character with a constraint-driven rig**, which is most of the roster. That wants its own session
with the blast radius measured first, the way the hips threshold and the decal rule were. It is
not a patch to tack onto the end of an evening.

**Five wrong stages, each costing a rebuild**, before a relative trace with a few extra probes
found it in two. The probes are the cheap part. Add them FIRST.



`VRM_TRACE_OFFSET="a,b"` tracks one material group RELATIVE to another at every stage, which a
whole-mesh box cannot do -- her teeth and her face are the same mesh, so its box moves with the
face and says nothing about the teeth inside it. One run found what three rebuilds could not:

```
OFFSET after import     teeth - eye = (+0.000,-0.012,-0.116)  |d|=0.117   <- matches the source
OFFSET after CHILD_OF   teeth - eye = (+0.021,-0.121,-0.158)  |d|=0.200   <- JUMPED
OFFSET after realign    (unchanged)
OFFSET after pose bake  (unchanged)
OFFSET after scale      (unchanged)
```

**Nothing after CHILD_OF touches it**, which is exactly why binding strays before the pose bake
and before the T-pose step both changed nothing: by then the damage was three stages old.

Traced against the body, which is neither constraint-driven nor unweighted, both parts move and
the EYES move most:

| at CHILD_OF | y (forward) | z (up) |
|---|---|---|
| **eyes** vs body | -0.129 -> **-0.050**, back 0.079 | +0.383 -> **+0.415**, up 0.032 |
| teeth vs body | -0.141 -> -0.171, forward 0.030 | +0.267 -> +0.257, down 0.009 |

So her eyes recede into her head and ride up by nearly three times what the teeth move. Her eyes
are bone-parented to `MCH-eye.L/R` -- the row above has said so all along -- and the conversion
that turns bone-parenting and CHILD_OF into skinned weights is placing them wrongly. The teeth
ride along because they are unweighted and in the same mesh.

What this does NOT yet say is which part of that conversion is wrong. That is the next question,
and it is now a question about forty lines of code rather than about a whole build.

**Three stages were ruled out the expensive way first** -- the T-pose step, subdivision (her Body
carries Subsurf 2; the source EVALUATED with it reads 0.012, the same as its base mesh) and the
pose bake -- each costing a full rebuild. Reach for a relative trace BEFORE guessing at stages.



Measured against her EYES, which is the comparison that works -- it needs no shared origin and no
assumption about scale or facing:

| | teeth below eyes | teeth IN FRONT of eyes |
|---|---|---|
| source, base mesh | 0.116 | **-0.011** (tucked inside the head) |
| source, **Subsurf 2 evaluated** | 0.116 | **-0.012** |
| every build of her | 0.160 | **-0.124**, eleven times further out |

Her 188 teeth vertices are unweighted in the source, so the natural reading is that something
moves the face while they stay put. **Three candidates were tested and all three are disproved:**

| mechanism | test | result |
|---|---|---|
| the T-pose step | moved the stray binding to run before it | gap unchanged at -0.124 |
| SUBDIVISION (her Body carries Subsurf level 2, 4,648 -> 90,000 verts) | measured the source with modifiers EVALUATED | -0.012, the same as the base mesh. Not the cause |
| the pose bake | bound strays to their nearest weighted neighbour BEFORE `bake_pose_to_rest` | gap unchanged at -0.124 |

None of those changes is in the tree. The displacement is somewhere else, and finding it wants
`VRM_TRACE` or a per-stage measurement of this same eye-to-teeth offset through the build rather
than another guess -- each of these three cost a full rebuild to disprove.

**What IS fixed:** her teeth are driven by her mouth (`DEF-lip.T.L`, under `DEF-spine.006`)
instead of by her left shoulder, so they no longer swing when her arms move. That was a real
fault and it is gone. Where they SIT is a second fault that has not been found.

**Compare against the eyes, not the floor.** Teeth-to-eye offset normalised nothing and needed no
origin; the first measurement of this used absolute z against model height and read as a 9.09% ->
12.42% vertical drop, which sent the search after the pose bake. The real signal is horizontal.



Binding them to the mouth instead of the shoulder (below) fixed what MOVES them. It did not move
them: isolating the `teeth` material and rendering it shows a plate hanging below her chin,
outside her mouth, with her actual mouth a small smile above it. The same band is in the REST
pose, so no animation is involved, and it is in builds that predate all of this.

**A measurement that looked like the answer and was not.** The teeth-to-eye gap is 9.09% of her
height in the source `.blend` and 12.42% in every build, so her eyes rise 0.061 during the build
while her teeth rise 0.017. Unweighted geometry does not follow a pose bake, so the obvious
reading is that the teeth were left behind -- and the obvious fix is to bind stray geometry
BEFORE the T-pose step rather than after it.

**That was tried and the gap did not move: still 12.42%.** Whatever displaces them happens earlier
than the T-pose section, and the change was reverted since it bought nothing. Two possibilities
remain and neither is settled:

- something earlier in the build moves the face relative to the teeth (the first pose bake is at
  the very top of the file, long before the humanoid map exists, so the binding cannot simply be
  moved there), or
- **the source model is simply like that** and the gap difference is her head straightening out of
  an authored pose, which would be correct rather than a fault.

The control that would separate them is a render of the SOURCE's teeth in isolation. Three
attempts at it framed the back and top of her head instead of her face -- her source faces the
opposite way and its proportions differ -- and it is still owed. **Do that first next time**: if
the source shows the same plate under her chin, the pipeline never moved them and this whole line
of enquiry is closed.

### Teeth at the collar: stray geometry must ask its NEIGHBOURS

Gadget Hackwrench's teeth hung at her throat. The cause was in her build log all along:

```
stray geometry: ... bound to the nearest humanoid bone: Body 188 verts -> DEF-shoulder.L
```

188 unweighted vertices -- her teeth -- were bound to her LEFT SHOULDER. A shoulder bone's head
sits at the base of the neck, which really is closer to a mouth than a head bone whose head sits
up inside the skull, so "nearest humanoid bone" was not wrong in its arithmetic. It was the wrong
question.

Stray geometry is almost always part of something that IS weighted -- teeth inside a mouth, a
tongue, an eye -- so it now takes the weight of the nearest vertex in the SAME MESH that already
has some, and falls back to the nearest humanoid bone only when a mesh has no weighted vertex at
all. Local, needs no anatomy, and gets teeth onto whatever the mouth around them uses:

```
Body 188 verts -> DEF-lip.T.L, Hair 4 verts -> HairSpring_0_0_3
```

`DEF-lip.T.L` ships, sits at z 0.819 against her head bone at 0.800, and is parented under
`DEF-spine.006`. Her teeth ride with her mouth.

**This is the same misjudgement as her ears**, in a different code path: an anatomical question
answered with a distance between bone heads. The ear case is still open -- see above -- but it is
worth noting the two together, because "nearest humanoid bone" appears in three places in this
file and is suspect in all of them.

### RETRACTED: "a head sphere that swallowed the hair roots"

The head-sphere change below was made, shipped and then REVERTED. It did not fix the splaying,
and shrinking her sphere 0.1997 -> 0.1187 is the likely cause of hair then clipping through her
head. The real cause of the splaying was not the hair at all -- see the next section. Kept here
because the measurement in it is sound and the conclusion drawn from it was not.

### Her EARS are rigged to her FOREARMS, and the pipeline does it

What looked like hair splaying into wings is her EARS being dragged out sideways. Four bones
drive 1,459 vertices of ear at head height (z 1.03-1.08) and are parented to her FOREARMS:

| bone | verts | geometry centre | parent |
|---|---|---|---|
| `DEF-ear.L.003` / `.R.003` | 543 / 552 | z +1.078 | **DEF-forearm.L / .R** |
| `DEF-ear.L.004` / `.R.004` | 182 / 182 | z +1.029 | **DEF-forearm.L / .R** |
| the other six `DEF-ear.*` | 1,915-2,558 | z 1.08-1.23 | `DEF-spine.006` (head) |

**The pipeline creates this.** They are orphans in her source, and the orphan repair adopts each
to the humanoid bone whose HEAD is nearest the orphan's own head. Her ear chain's bone heads sit
nearer her forearm than her skull, because at rest her arms are out in the T-pose. It passes
every static check for the same reason.

**Four fixes were tried and all four failed. None is in the tree.** Recorded so they are not
tried again:

| attempt | why it failed |
|---|---|
| distance RATIO, centroid-to-parent against centroid-to-nearest-bone | flags ordinary face bones on every character -- 13 on Gadget, 14 on Jinx -- and misses the two that are wrong, because a small bone always has another small bone near it |
| NEAREST-HUMANOID classifier on the geometry centroid | same noise: broad regions have centroids near limb bones. Flagged capes, skirts and chest bones everywhere |
| NAME-FAMILY majority vote | correct on the built file (flags exactly the four, clean on six other characters) but useless where it has to run: before export the siblings hang off Rigify CONTROL bones like `ear.L`, which have `use_deform` off and are not written. Voting for them put the ears on `root` |
| adopt by WEIGHTED CENTROID instead of bone head | made things worse -- moved `DEF-chin` onto `DEF-shoulder.L`. The humanoid bone HEADS are poor reference points for "which part is this" |

The family vote is still the most promising: it discriminates perfectly on the exported file. It
needs the sibling's first ancestor that SURVIVES export, resolved through the Rigify control
bones rather than stopping at them.

### A head sphere that swallowed the hair roots

With the hips fixed her head stayed on her neck -- and her hair then splayed into two wings out
to the sides. A second, separate fault, and the shape of it was the clue: symmetric and static
rather than whipped, which is a chain resting against something too big, not one being flung.

Her head sphere was **0.1997 on a character 0.80 tall**, centred 0.26 ABOVE her head bone,
because the sphere is fitted to head geometry and her EARS are part of her head. That buried
`HairSpring_0_3_0` 0.101 m inside it and left the chain's first SIMULATED joint with 0.0136 m of
clearance, so any motion pushed it back in and ejected it outward.

The guard skips chain anchors, and that is correct for a CAPSULE -- the Xenomorph's tail is rooted
on his spine, and guarding anchors shrank his torso capsule to zero. **A head sphere is the
opposite case.** An anchor buried in it means the sphere has swallowed the roots, and the first
joint that CAN move is then sitting on the surface. So the head sphere now clears the anchors too,
and says why:

```
head sphere 0.1997 -> 0.1187: a spring ANCHOR sits 0.1187 from the head centre, and a sphere
that swallows the roots leaves the first simulated joint on its surface
```

Blast radius measured over eleven built characters before the change, with the same `CHEST`
exclusion the guard already applies: **Gadget to 59% of her radius, Peach 92%, Sayuri 93%, and the
other eight unchanged.** Shrinking is the direction this file already argues for -- a small
collider still stops hair driving through the face, while an ejecting one is a visible
catastrophe.

After: her deepest buried anchor goes from 10.1% of height (a hair chain) to 3.1%, and that one is
`DEF-breast.R`, a chest chain which is unguarded on purpose. No hair anchor is buried, and no
simulated joint is inside anything.

**Two faults, one screenshot.** The hips put her head on the floor's pivot; the head sphere threw
her hair outward. Fixing either alone still looked broken, which is why the first three attempts
read as failures of the fix rather than as a second cause.

### A hips on the floor: three wrong diagnoses before a controlled one

Her head and hair were being dragged off her body in game. It took three attempts, and the two
failures are worth more than the fix.

**Blamed first on her colliders.** She genuinely had only 2 and 2 of 4 chains unguarded, so that
was a real defect -- it was just not THIS defect. Fixed, installed, no change in game.

**Then on a collider CONTAINING a spring joint**, the fault her own row already named. A probe
said `HairSpring_0_3_1` sat 5.4 cm inside her head sphere. It was wrong: the probe built world
positions by ADDING translations down the node tree, which ignores every rotation and scale. The
only reason that did not get reported as fact is that the same probe put Peach at 7 violations and
Batman at 4, and both had been verified clean -- **a control is what caught it.** With proper TRS
composition: Batman 0, Gadget 0, Peach 1 at 3.4 mm.

**And it was not weighting either**: 0.0% undriven weight on every mesh.

What it was, measured against 147 built rigs: her `hips` is a bone called `root` at **0.6% of her
height**, where the healthy band is **0.405 to 1.072** and the nearest healthy rig is 0.405. Her
thighs hang off that root rather than off her pelvis, so the root is the only bone that satisfies
"the junction of a spine and two legs", and it sits on the floor.

**It passes every static check**, which is why it survived so long: the bind pose never consults
the humanoid map, so she renders perfectly. Only in game does Unity pivot her whole body about a
floor-level hips.

`build_vrm.py` now promotes the parent of the mapped spine -- the pelvis by construction -- when
the chosen hips sits below 25% of height, and only when that candidate is itself a descendant of
the old hips, since otherwise re-parenting the legs would lift them out of the skeleton. The
existing repair already re-parents legs onto whatever `hips` becomes. Where no better candidate
exists it prints a warning instead of shipping a floor-level hips in silence. She now reports:

```
hips 'root' sits at 0.0% of height, which is the floor -- promoting 'DEF-spine' at 54.1%
```

Only two of 147 built files trip the threshold: Gadget, and `withcols/Sonic.vrm` at 0.063 -- an
abandoned variant. The Sonic that is installed comes from `rollout/out` at 0.818, so nothing else
on the roster changes.

**`cloth_collide.py` does not check containment.** It counts chains with no collider NEAR them,
which is the opposite failure, so its "0 UNGUARDED" was never a statement about joints inside
colliders. `inside2.py` is the one that answers that question.

### Gadget Hackwrench was excluded on a verdict that had gone stale

Reported in game as a mess: her head and hair dragged off the body. She was not broken by anything
recent -- her installed file was byte-identical to its backup -- she had simply never received the
limb-collider rollout, because `identify_build.py` said her `.vrm` was not what is installed.

That was true of the two files it was run on and false of the set. Measured against all seven
candidates:

| | names | length | rotation | |
|---|---|---|---|---|
| `rollout/out`, `withcols` | 98.9%, 95.7% | 0 | **57** | the files the old verdict judged |
| `alpha3/Gadget-all`, `alpha3/Gadget-hair` | 95.7% | 0 | **0** | MATCH |
| `gadget/rt-Gadget`, `guardtest/Gadget Hackwrench` | 94.1% | 0 | **0** | MATCH, and already collider-fitted |

Her installed bundle carried **2 colliders and 2 of 4 chains unguarded** -- both hair chains, out
by her arms with nothing to catch them -- against 10 and 0 for every character the rollout did
reach. Rebuilt from `guardtest/Gadget Hackwrench.vrm`: **10 colliders, 0 unguarded**, and humanoid
coverage 44 -> 50 bones because the installed build was missing her entire LITTLE FINGER chain
(fingers 24 -> 30).

**Re-run a stale verdict before building on it.** A row saying "this file is not what is
installed" is a measurement of the files that existed when it was written.

One difference needed adjudicating rather than waving through, and it is the Gordon Freeman
pattern again: the installed bundle put the `Body` skin map on her TEETH, which no source `.vrm`
asks for -- all three candidates give that material no base-colour texture and an authored grey of
0.8. The loose fallback had reached for the only other map in the folder. The rebuild drops it.

With her in, the only unguarded chains left on the roster are **38 across 2 characters**, Kaiser
Aufhanger and Adachi Rei, both downloaded bundles that were never built here.

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
| — | a soft alpha shipped as a hard cutout | was 20 materials, 6 characters | **CLOSED 2026-11-12** — all six rebuilt, `HARDCUT` 20 → 1 across the set, blended materials 1 → 20. Item 0 below |
| — | colliders in a group that do not resolve | was 12 orphans, 3 characters | **CLOSED 2026-11-12** — a stale Blender reference; found while doing the above. Item 0a |
| 2 | Kaiser Aufhänger has no leg colliders | 36 chains, 1 character | **70% of every unguarded chain left in the set** is this one character |
| 3 | zero colliders, no `.vrm` | 11 chains, 3 characters | **blocked, and not by effort.** Editing a loaded bundle works; writing it back does not — `BackgroundHelper.Export` exits 0 and produces a 2,552-byte shell with no meshes in it. See `docs/character-models.md` |
| 4 | opacity in an opaque material (`UNUSED`) | 45 materials, 17 characters | needs a render each; roughly half will be specular masks |
| 5 | no bound visemes | 52 of 65 | mostly blocked on a source file that does not exist |
| 6 | Jessica Rabbit is 3.7% too tall | 1 character | cosmetic |
| — | floating prop setting the height | **0 of 65** | **CLOSED** — item 2 below |
| — | bent or asymmetric limbs | **0 new** | ~~**CLOSED**~~ — **NOT closed, as of 2026-11-15.** Every flag was explained, and the sweep could only ever flag a limb that is BENT. Spartan Mark V's right leg sat 25 mm out of its socket with its knee and ankle angles matching his left to four decimals, so it was never a candidate. `limb_socket_check_installed.py` measures whether a limb JOINS the body. It took THREE more corrections after that — a minimum is not robust, a vertex count does not establish that two limbs are the same object, and no single quantile does either — and the sixth version requires the gap to dominate across q0..q50. It finds **0 across the installed 65** while still flagging Spartan Mark V's pre-fix backup at +24.8 mm, which is the only fault any version of it found. See "Spartan Mark V's right leg, 2026-11-15" and the correction under it |
| — | missing animation / finger mapping | **0 new** | **CLOSED** — same |

The reasoning behind each is in `docs/character-models.md`; what follows is the older list,
which items 1-3 above now sit in front of.

0. ~~**Rebuild the six characters whose soft alpha ships as a hard cutout.**~~ **DONE, all six,
   2026-11-12.** Across the installed set `HARDCUT` went **20 → 1**, and the one left is
   deliberate (Ariel's `EyeMoisture`, below). Blended materials in the 65 went from **1 to 20**,
   and the one that was there before belongs to Adachi Rei, a downloaded bundle we did not build.

   **The entry was wrong twice, in opposite directions, and both are worth keeping.**

   First it said "NOT POSSIBLE — none of the six can be rebuilt". Every source archive is in
   `%USERPROFILE%\Downloads\`, named after the model listing rather than the character —
   `sayuri-dans.zip`, `alice-ivy-animated-by-jungle-jim.zip`, `valve-gordon-freeman-model.zip`,
   `topless-sexy-girl-with-heels.zip`, `alcina-dimitrescu-resident-evil-village.zip`. The search
   that "proved" they were gone looked for the file *inside* each archive, which is what the
   recipe rows name, and a file inside a zip matches no `find`. **Search for the CONTAINER, not
   the content**, and sort by modification time: the whole set was downloaded within a few hours
   of 2026-11-07, so one known archive's timestamp finds the rest.

   Then it said "Ariel is the only one with no archive". **Also wrong.** Her recipe row says her
   arguments were *recovered from her own `.yargchar`*, which is a statement about how the
   ARGUMENTS were reconstructed and says nothing about whether the model exists. It does:
   `base-female-character.zip`, as `source/Ariel For Sketchfab.fbx`. A row explaining how a
   recipe was derived is not evidence about what is on disk — go and look.

   **The builder had no lever for this, and that was the real blocker.** The exporter fix landed
   on 2026-11-12 and carried a blend across correctly; what it could not do is *decide* to make
   one. Only 3 of the 20 flagged materials were `alphaMode: BLEND` in their `.vrm` at all — the
   other 17 were `MASK`, chosen by `build_vrm.py`'s opacity-map path — so a plain re-export would
   have reproduced every cutout exactly. `VRM_BLEND_MATERIALS` existed but was guarded on
   `not cut`, which made it a no-op on precisely the materials that needed it. **An explicitly
   named material now outranks an inferred cutout**; see the switch's description above.

   Only Gordon needed no Blender rebuild — his lens was already `BLEND` and his fault was purely
   the exporter — which is also why re-exporting his existing `.vrm` was the right move: it put
   his 32 FACS shape keys out of reach of a rebuild that has dropped them before.

   | character | blended | verdict from the podium render | installed |
   |---|---|---|---|
   | Gordon Freeman | `lens` | **a speckled hard mask over both eyes becomes glass you can see his eyes through.** The clearest single win | re-export only |
   | Sayuri | 2 eyelash, `Lace`, `Moles`, `Hair` | **hair stops being dotted and reads as hair.** The cutout was chewing the feathered strand edges into speckle | + hair |
   | Heels | eyelash, both tear lines, both eye occlusions, 2 hair | lashes present, hair continuous instead of speckled | + hair |
   | Alice Ivy | `Std_Eyelash` | lashes already fixed by the stopgap; the blend keeps them without a threshold | lashes only |
   | Ariel | `Eyelashes`, `Hair Cap` | hair edge and lash softer, **irises intact** | lashes only |
   | Alcina Dimitrescu | `Material.006` (`CILIOS`) | **no verdict possible** — at 2.9 m her head is above the podium camera and the render shows her dress | yes, on the numbers |

   **Hair was built both ways and decided by a render, not by preference.** A blended card has no
   z-write, so overlapping hair sorts by draw order rather than by depth, which a cutout does not
   — that cost cannot be predicted from an alpha channel. Two builds each for the three
   characters with hair in the flagged set, rendered side by side: blending it is clearly better
   for Sayuri and Heels, whose hair loses ~25% of its ink to the threshold. **Alice Ivy's hair
   stayed a cutout**, because it loses **1%** — there is nothing to recover, and a cutout sorts
   more robustly. Rule: blend the hair only where the sweep flags it.

   **Ariel's `EyeMoisture` and `Cornea` are deliberately still cutouts**, and that is the one
   remaining `HARDCUT` plus the one `INVISIBLE` in the whole set. At a lowered cutoff
   `EyeMoisture` drew an opaque white film and erased her irises; a blend is a different
   operation on the same suspect alpha, and upgrading the two materials already proven safe costs
   nothing while adding these two re-opens a measured regression.

   Backups are `<Name>.prerebuild.yargchar` in `character-backups/`.

   The earlier stopgap (lowering `_Cutoff` to 0.16 on the installed bundle) is superseded by all
   of the above and its tooling is kept only for what it measured: **patching an installed
   bundle's material to a real blend does NOT work** — every number comes back right and Gordon's
   lens renders as a solid white pane — while **lowering `_Cutoff` does**, because it changes no
   shader variant. See `patch_alpha_blend.py` and `docs/character-models.md`.

   **Do not rank this work by the clipped-ink number.** Alice Ivy was last of eleven by that
   measure and produced the most visible improvement from the stopgap; Alcina was second and
   produced nothing. How much of a texture a threshold destroys says nothing about how much of
   the *character* it destroys — that depends on where the material sits and whether the camera
   can see it. The same number then mis-ranked the rebuild in the other direction: Gordon's lens
   was sixth of eleven at 79% and is the most improved thing in the set.

   Per material, the share of the texture the 0.5 threshold threw away before any of this:

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

0a. **Four colliders per character were guarding nothing, in three installed characters.**
   Found while rebuilding the six, and it is the more serious of the two faults.
   `vrm_colliders.py` built its collider group by holding the element `.add()` handed back and
   reading `.uuid` off it later. `sb.colliders` is a Blender `CollectionProperty`, and `.add()`
   may reallocate, so those references go stale; the add-on then drops every group reference
   whose uuid does not resolve.

   **The builder's own log said "colliders: 10 in one group" while the file held six.** Sayuri's
   exported group was `[4, 5, 6, 7, 8, 9]` — her head, hip and left arm were measured, fitted,
   written into the file and guarded nothing. It is not even stable: the same character built
   twice in one batch came out `[4..9]` once and `[8, 9]` the next. **A count printed from the
   builder's own list is not a measurement of what reached the file**, and this is the second
   time that distinction has cost something here.

   Fixed by keeping the uuid string rather than the element, plus a warning that compares the
   group's references against the colliders actually in the file. `collider_group_check.py` over all 30 `.vrm` files
   behind an installed character found exactly three affected — **Alcina, Pomni, the Xenomorph,
   4 orphans each, always the head/spine and the left arm**. All three are rebuilt and installed;
   Pomni and the Xenomorph carry no other change, and their backups are `.precolgroup`.

   Only Sayuri of the rebuilt six goes through `add_colliders.py`, and it matters: that script is
   a **round trip**, so the installed Sayuri carries 19 named collider nodes the importer makes
   and a bone-roll convention that differs from a direct build on 25 bones by exactly 90° or
   180°. Her rebuild was put through the same round trip, which takes her from `differs` back to
   a clean `MATCH` against the installed bundle. Check `identify_build.py` before assuming a
   recipe reproduces what is installed — a recipe row records the *build*, not the steps after
   it.

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
- `vrm_alpha_modes.py <vrm...>` — what alpha mode each material actually CARRIES. Run it before
  rebuilding for an alpha fault: a material that is `MASK` in the `.vrm` comes out a cutout no
  matter what the exporter can express, and the rebuild will report success doing it
- `value_alpha_scan.py <source>` (via `blender --background --python`) — which materials state a
  transparency as a VALUE with no map to carry it? Those are what the builder flattens to opaque
  unless `VRM_VALUE_ALPHA=1`, and a dark one in front of an eye is a black disc. Run it on the
  ARCHIVE, not the bundle: no alpha sweep can see a material with no base map. A hit is a
  candidate, not a defect — read the base colour and what sits behind it
- `collider_group_check.py <dir|vrm...>` — does every collider reach the group that guards the
  chains? The builder's log is not an answer: it said "10 in one group" for three characters
  whose exported group held six. Exits non-zero on an orphan, so it works in a pre-commit check
- `patch_alpha_cutout.py <yargchar> --materials "Name"` — turn an OPAQUE material into a
  cutout IN THE INSTALLED BUNDLE, the sibling of `patch_alpha_blend.py`. For when the
  material is right and a rebuild is not: Shrek's torn hem needed this because the Blender
  round trip that produces the `.vrm` changes 60 bone orientations on a character whose rig
  matches his bundle exactly. The state is COPIED from a real cutout (Heels' `Heels_17`),
  not invented, and it reads the file back to prove only the named material changed
- `patch_shine.py <yargchar> [mat;mat|*] [--smoothness S] [--out X] [--dry-run]` — turns URP's
  default shine off IN THE INSTALLED BUNDLE, the same change `YARG_NO_SHINE_MATERIALS` makes at
  export: `_Smoothness`, `_Metallic`, `_SpecularHighlights` and `_EnvironmentReflections` to zero
  plus the keywords `_SPECULARHIGHLIGHTS_OFF` and `_ENVIRONMENTREFLECTIONS_OFF`. **The keywords
  are the part that matters** — URP/Lit branches on them and the floats are what the inspector
  uses to set them, so writing only the floats would look right in a dump and change nothing in
  the game. Alastor is the control, the one character of 65 built with the switch on: run against
  him it reports "already flat, nothing to do" on all three materials, which is the patcher and
  the exporter agreeing. `--smoothness S` writes S instead of 0 if matte looks dead
- `limb_socket_check_installed.py <dir|yargchar...>` — is a LIMB out of its socket? The companion
  to `limb_check_installed.py`, which measures how a limb is BENT and is blind to one that has
  moved rigidly: Spartan Mark V's right leg sat 25 mm out of place with its knee and ankle angles
  matching his left to four decimals. For each limb that attaches to the torso it measures THE
  JOIN — how far the nearest part of its flesh is from the nearest torso vertex — which needs no
  reference to the other side and **no assumption about anybody's axis convention**. That last
  part is the whole reason it exists: it replaces `mirror_check_installed.py`, deleted the same
  day, which compared local bone offsets with X negated and was wrong wherever a shared parent is
  rolled. The other side is a control, not the measurement: a limb flags only when the two sides'
  gaps differ by ≥ 10 mm AND ≥ 2× (Spartan 25.1 mm at 6.4×, Kronk 3.8 mm at 1.15×), and a pair
  whose sides carry materially different vertex counts is DECLINED rather than judged, because
  then nothing about them is comparable — Kronk's thighs carry 54 and 45. A limb's flesh is its
  bone's whole subtree down to the next mapped humanoid bone, so a Character Creator `*_Twist`
  bone counts as part of its limb; the torso reference is the mapped spine chain ONLY, because
  expanding that to its subtree pulled in Spartan's `pelvis.R` and closed his 29.7 mm gap to 5.4.
  A limb flags only when it is further from the body at EVERY decile from q0 to q50 —
  distributional dominance over the near half — by at least 10 mm at the weakest of them.
  NOT one summary statistic: three earlier versions were each fooled by a single quantile
  that happened to move, and the profiles are what separate the cases. Spartan Mark V's
  displaced leg reads +25 +28 +27 +28 +27 +25 and Peacemaker's sound one +0 +22 +27 +1 -3
  -1. It also declines a pair differing by more than 10 mm IN ITS OWN FRAME whatever its
  vertex counts say, because Vegeta's upper arms are 818 and 827 vertices and 45.2 mm apart
  in frame. The decision lives in ONE function, `decide()`, shared with `patch_mirror.py`
- `patch_mirror.py <yargchar> <bone> [--out X] [--dry-run]` — moves a displaced bone onto the
  mirror of its partner, in all FOUR structures that hold its offset: the `Transform`, the
  Avatar's `m_AvatarSkeletonPose` and `m_DefaultPose` (both nested under a `data` key — read one
  level too shallow they come back as empty lists rather than an error, which reads as "the Avatar
  carries no skeleton"), and `m_HumanDescription.m_Skeleton`. The bone's children keep their own
  offsets and the mesh keeps its bind pose, so the limb travels rigidly and its geometry is
  untouched. **It refuses on evidence and then checks its own work**: it will not run unless the
  named bone's side is measurably out of its socket and the other side is in, and after the edit
  it RE-MEASURES the join on the patched bytes and writes nothing unless the gap has come down to
  its partner's — because the naive mirror of a local offset is an assumption about the parent's
  axes that the file cannot confirm. On Spartan Mark V: 29.7 mm → 4.6, against a left leg at 4.7
- `patch_springs.py <yargchar> [--cloth] [--limbs] [--unrig-hair] [--out X] [--dry-run]` — fixes
  the spring simulation IN THE INSTALLED BUNDLE, three independent defects, any or all. `--cloth`
  re-parameterises every cloth-named chain to the authored reference 0.50/0.05/0.00 (the old
  0.85/0.80 damps a skirt into near-rigidity and is above every value in any author-made bundle
  here); `--limbs` re-radiuses the arm and leg capsules from the median flesh distance to the
  90th percentile, because a median leaves half of every limb outside its own collider and a
  VRM spring joint is deflected by a collider and by nothing else. Both carry the clearance
  guard — a collider that CONTAINS a joint ejects it, which is what ballooned Gadget's hair —
  and both skip the chain's anchor joint, as `vrm_colliders.fit` does. `--unrig-hair` is the
  third and it REMOVES chains rather than tuning them: a hair chain that drives a facial feature
  (Killer Clown's eyebrows were 146 of 146 vertices on hers) or whose hair is sealed inside a
  rigid head-mounted mesh (371 of her 387 were inside her jester hat) is a selection fault that
  no parameter fixes. It drops the chain from `Vrm10Instance.SpringBone.Springs`, which is the
  single source of truth the runtime builds its buffers from, and leaves the bones, joints and
  meshes alone — so every vertex keeps the position the model gives it and only the motion
  stops. Its read-back
  fingerprints every object's full typetree, so an unintended change cannot hide and a failed
  check writes nothing at all. For the 35 characters with no source left, and for the ones like
  Peach whose recorded recipe no longer reproduces them
- `uv_alpha.py <vrm...>` — what would ACTUALLY disappear if a material honoured its
  texture's alpha? Samples the alpha at the material's own vertex UVs, not across the
  whole atlas, because an atlas's unused regions are clear and lie outside every UV island
- `honour_alpha.py <in.vrm> <out.vrm>` (via `blender --background --python`, with
  `HONOUR="Material"`) — wire a base texture's existing alpha into Alpha and switch the
  material off OPAQUE. Exists to be TRIED AND REJECTED in five minutes: on 2026-11-12 it
  was, on all three reachable UNUSED candidates — two catastrophic, one a no-op
- `eye_shell_sweep.py <dir|yargchar|vrm ...>` — is an opaque shell parked in front of
  anybody's eyes? Three characters shipped that way and all three were found by accident.
  Reads BOTH forms and needs to: a bundle renames every material to `<Character>_<n>`, so
  a shell that lives as a MATERIAL inside an ordinarily-named mesh (Alice Ivy's
  `EyeMoisture_*` inside `Custom_Eye`) is invisible on that side. Every hit is a
  CANDIDATE — a solid eye is ordinary on a stylised character
- `set_material_alpha.py <in.vrm> <out.vrm>` (via `blender --background --python`, with
  `SETALPHA="Material=0.08"`) — make one material transparent in a built `.vrm`. For the
  eye-shell fault on a character with no source: Alice Ivy, Ariel and Prix have all had a
  flat lens shipped opaque over perfect eyes. REFUSES a material with a MAP wired into
  Alpha, because overriding a real opacity map is a different decision — the one time this
  project did that by accident it washed Heels' iris out
- `add_visemes.py <in.vrm> <out.vrm>` (via `blender --background --python`, with
  `VRM_VISEME=` in the environment) — retro-fit viseme bindings onto a built `.vrm` whose
  source is gone. Consumes the line `viseme_fit.py` emits, so the measuring is not
  duplicated. REFUSES to write a file when the mapping names a mesh or key the file has not
  got, which the VRM add-on otherwise writes silently and which moves nothing in game
- `collider_group_check_installed.py <dir|yargchar...>` — the same question asked of the
  **installed bundle**, which is the only form 35 of the 65 characters still exist in. Separates
  an orphaned collider from a dangling group reference and from a group no chain uses, and knows
  that a chest-only character's unused group is by design. `CGC_CONTROL=1` empties every group,
  so a clean character must come back orphaned
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
  pose shows a skinning fault, and only because it bakes each skinned mesh first.
  **`-renderDir` renders INSTEAD of exporting** — the block ends in a `continue`, so a run that
  passes it produces pictures and no `.yargchar` at all, and says nothing about it beyond
  `ALL DONE, failures=0`. Build the bundle in a second run without it.
  `HandIsolate` is the part worth reaching for: per-finger `FINGERGAP` measurements and renders of
  the hand **with every other renderer switched off**, framed on the hand's own axes. Both exist
  because the plain views could not answer the question — the camera aims at the hand BONE and
  photographs whatever is in front of it, which on a posed character is a thigh or a sleeve
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
| `YARG_CULL_OFF_MATERIALS="Head.001;Eyes.001"` | export | **override**: forces the named materials double-sided. The exporter now MEASURES sidedness per material (see "Single- and double-sided" below), so this is only for a judgement the measurement gets wrong |
| `YARG_CULL_ON_MATERIALS="Hair"` | export | **override** the other way: forces the named materials back-face culled |
| `YARG_NO_SHINE_MATERIALS="Body.001;..."` or `*` | export | smoothness, metallic, specular and environment reflections off, plus the two keywords URP/Lit actually branches on. ~~Partly overridden for materials with a metallic map (the exporter sets `_Metallic` 1 afterwards)~~ — **fixed 2026-11-15**: flattening now runs LAST and declines the metallic map outright, so the switch is whole. For a bundle that will not be rebuilt, `patch_shine.py` makes the same change in place |
| `YARG_SHELL_NO_SHADOW=1` | export | an untextured near-black material stops casting shadows. Made no visible difference on Alastor |
| `YARG_SHADOWS=1` | hand render | soft shadows on the render light |

## Single- and double-sided, measured rather than flagged

A fresh URP/Lit culls back faces. The Standard material the `.vrm` is imported as has no cull
property, so nothing carries the source's intent across, and a single-layer sheet — a hair
fringe, an ear, an eye plane — vanishes from the side its normals face away from. That is how
Alastor's mask showed through his fringe.

**The exporter decides this per material by measuring the triangles.** Two scale-invariant
numbers per connected piece of surface, vertices welded by position so a UV seam does not split
a piece:

| | | |
|---|---|---|
| **openness** | `boundary_length / sqrt(area)` | an edge used by one triangle is a boundary. A solid with a wrist hole scores near zero; a single-layer sheet is boundary all the way round. A flat disc is `2*sqrt(pi)` = 3.5 |
| **solidity** | `abs(signed volume) / area^1.5` about the piece's own centroid | a sphere is 0.094, a limb-shaped cylinder 0.058, anything enclosing nothing about 0 |

A piece is a sheet when `openness > 1.5` **and** `solidity < 0.02`, and a material is drawn
double-sided when at least 20% of its area sits in sheet pieces.

**Both tests are needed, which is not obvious and was measured.** Openness alone names 93–147 of
265 materials — a blanket by another road — and gets Alastor's `Head.001` wrong, which is
single-sided on purpose. What solidity rejects is the piece that is *open but still voluminous*:
a hollow head shell with eye and mouth openings, which openness alone calls a sheet.

**The glTF `doubleSided` flag is NOT read, in either direction.** Across the third-party sources
here it is 60 true, 0 false, 5 absent, because a Blender glTF export writes
`doubleSided = not use_backface_culling` and Blender defaults that off. A field that is true
because of an upstream default is not a declaration. An absent one is equally just a different
tool's default (the MultiVersus rips), so it is no good as a veto either. Reading it as intent
is what nearly put the whole roster double-sided on 2026-11-13; see
`docs/reported-faults-2026-11-12.md`.

### How the thresholds were chosen

Measured over **3,971 connected pieces across the 37 characters that have a `.vrm`**, then
sensitivity-tested rather than picked at one point:

- **openness is the robust knob.** It is strongly bimodal — 822 pieces below 0.1, a large mass
  above 3, a sparse valley between — and *any* value in 1.0–2.0 gives the identical set of
  material verdicts. 1.5 sits mid-plateau.
- **solidity is the sensitive one.** It is not bimodal, so the cut is a judgement: 0.02 names 20
  materials, 0.025 names 31, 0.03 names 48. **Err low.** Culled is the status quo that ships 52
  characters with no reported fault, and a wrongly double-sided material *hides* inverted winding
  instead of showing it — Alastor's eyes were inverted and the note on him records them as
  "hidden by the double-sided material".
- **the area share is mild**: 10% names 33, 20% names 20, 30% names 18, 50% names 15.

**The test is Alastor**, the only character whose sidedness was decided by hand and shipped:
`Eyes.001` must come out double-sided and `Head.001` must not. The chosen values reproduce that,
and name **20 of 265 materials (7.5%)** across the roster — eyelashes, brows, hair cards and eye
planes, which is what the category is supposed to contain.

### Checking it

`sidedness.py` is the same rule in Blender (`blender --background --python sidedness.py --
file.vrm`). It exists so the exporter's C# can be cross-checked against an independent
implementation on the same characters: a transcription slip in the welding, the edge keys or the
union-find would not crash, it would just quietly shift which materials come out double-sided.
`openness.py` prints the raw open/closed split per piece. The exporter logs
`sidedness <material> sheet-area N% -> DOUBLE-SIDED|culled (why)` for every material, so the
decision is readable in the build log and an override says so.

### Rolling it onto the installed roster, 2026-11-13

**56 of 65 rebuilt and installed. 1 double-sided material on the roster became 34, across 17
characters.** `{None: 141, 2.0: 398, 0.0: 1}` -> `{None: 141, 2.0: 365, 0.0: 34}`. Alastor, Alcina
Dimitrescu, Alice Ivy, Ariel, Heels, Iron Man Mark 85, Jessica Rabbit, Judy Hopps, Peach,
Power Girl, Sayuri, Scott Hall, Spider-Man, Spider-Man PS, The Rock, Vegeta and Yui Suzukaze each
gained between one and six. The 141 with no `_Cull` at all are MToon materials, which carry
sidedness inside the VRM extension instead.

**Alastor is the control and he passed with nothing set.** His is the only hand-made cull decision
on this roster -- `Eyes.001` double-sided, `Head.001` single-sided on purpose -- and his rebuild
ran with no `YARG_CULL_OFF_MATERIALS` at all: `Eyes.001` measured 100.0% sheet area and came back
double-sided, `Head.001` measured 0.0% and stayed culled. His bundle is identical to his backup.

#### The newest file bearing a character's name is NOT its source

This is the part that cost the most and generalises furthest. Picking each `.yargchar`'s source
`.vrm` by modification date is wrong, and wrong in a way that silently swaps a character:

| character | newest by name | what it scored | what actually built it |
|---|---|---|---|
| Alice Ivy | `hair/out/Alice Ivy.vrm` | **89.2%** rig overlap | seven others at 98.7% |
| Power Girl | `pass2/Power Girl.vrm` | 450 nodes against 431 | `withcols/Power Girl.vrm`, 99.5% |
| The Rock | `withcols/The Rock.vrm` | bone lengths wrong | `rockbuild/rock-final.vrm`, 0 and 0 |
| Prix | `pass2/Prix.vrm` | 2 rotations wrong | `prix/Prix-lens.vrm` |
| Sayuri, Scott Hall, Jessica Rabbit, Alcina, Ariel, Jinx, Heels | newest | — | an older file in every case |

Three readings settle it, two of them hard gates, and `select_source.py`'s losers are printed so
the pass means something:

- **RIG** -- `identify_build.py`'s own rule, >90% shared bone names with no length off by more than
  0.5 mm and no rotation off by more than 1 degree. **Use its 90, not a stricter number.** A 95%
  threshold rejected Pomni at 92.5% -- the duplicate-name artefact that file already documents and
  that had already cost her two rounds -- along with Steve, Mannequin and Gwen Stacy, every one of
  them with zero length and zero rotation mismatches.
- **MATERIAL COUNT** -- the exporter renames every material to `<Character>_<n>`, so the bundle
  keeps no trace of the source's names, but the count survives exactly. Measured over the whole
  roster this gate changed exactly one pick -- Thanos, `ThanosT.vrm` to `Thanos.vrm` -- and
  narrowed the field everywhere else (Heels 9 surviving candidates to 1). A gate that rejects
  without changing an answer is still doing its job; it is the reason the answer can be trusted.
- **TEXTURE NAMES**, for ranking only. Unity's VRM importer duplicates a texture two materials
  share (`__UNIGLTF__DUPLICATED__3`) and appends `.normal` / `.standard` by usage, so the counts
  legitimately differ -- The Rock's 6 images become 21 textures -- and only the stripped names
  compare. Peacemaker has none in either, which is agreement and not a zero.

**The Clone Troopers are crossed.** `CloneP2` builds the 501st and `CloneP1` builds Shiny, each
MATCHing its own and failing the other at 30 bone lengths. The names invite the opposite guess.

#### The gate that made the rollout safe

The exporter's only intended change is `_Cull`, so every rebuild was compared against the
hash-verified backup on everything UnityPy can read -- object type counts, each material's floats,
colours, keywords, render queue, tags and texture slots with `_Cull` removed, texture names, and
every Transform's bone name, position and rotation (`verify_rebuild.py`). Cull-only differences
installed; anything else did not. Mesh data is deliberately absent: UnityPy reports verts=0 for a
`.yargchar`, and that zero looks like an answer.

#### The six held back, and what happened to them

| character | installed -> rebuild | the difference |
|---|---|---|
| Shrek | 0 -> 0 double-sided | rebuild loses a cutout (`TransparentCutout` -> `Opaque`). The only rig-matching source has no MASK material; the four `alpha3` files that do differ at **60 rotations** |
| Skeleton Mage | 0 -> 0 | rebuild makes a material transparent that ships opaque, and only one source exists |
| Gadget Hackwrench | 0 -> 0 | 179 -> 185 nodes and a texture lost. Her `.vrm` is not what is installed, as her row above already says |
| Iron Man Mark 85 | 0 -> **2** | his installed materials are named `Arc Reactor_urp`, `Glass_urp` -- an **older exporter**, before the `<Character>_<n>` rename. No source choice fixes that |
| Jessica Rabbit | 0 -> **1** | rebuild applies `_SpecularHighlights 0` / `_EnvironmentReflections 0` that the installed build never had |
| Spider-Man PS | 0 -> **1** | the same no-shine change |

The first three cost nothing: their rebuild produces exactly the sidedness they already carry, so
skipping them is correct rather than a compromise, and they stay on their installed builds.
**Measure that before calling a skip harmless** -- the other three forgo real double-sided
materials, and they are the same shape of problem: the exporter has moved on since those
characters were built, so sidedness cannot be applied without applying those changes too. On
Jay's call the last three WERE installed, once each had been shown to differ in nothing beyond
`_Cull` and those named changes.

#### What the change actually LOOKS like: one clear win, and eight that show nothing

Rendered before and after for all 17, from four angles -- head front, head side, whole-body front,
whole-body side -- with `cullpair.py`. A plain render of a `.vrm` shows neither state, because
Blender honours the file's own `doubleSided` and draws no gaps at all, so BEFORE forces culling on
every material and AFTER releases exactly the 34 the exporter measured. EEVEE_NEXT honours
`use_backface_culling`; **Cycles ignores it**, and would have reported no difference anywhere.

| | characters | largest change |
|---|---|---|
| clearly improved | **Alcina Dimitrescu** | **2.230%** -- the hair at the back of her head goes from sparse see-through wisps to a solid mass |
| visibly improved | Ariel, Judy Hopps, Peach | 0.542% (her brows and hair curls), 0.037% (eyelash arc), 0.030% |
| a few pixels | Alice Ivy, Heels, Iron Man Mark 85, Spider-Man PS, Yui Suzukaze | 0.006% or less -- a lash line, an eye slit, a webshooter |
| **nothing in any of the four views** | Jessica Rabbit, Power Girl, Sayuri, Scott Hall, Spider-Man, The Rock, Vegeta | 0.0000% |

**Half the flips make no visible difference from a static camera, and that is not evidence they
are wrong.** A sheet only shows its missing back face when that face is turned toward the viewer;
Scott Hall's flipped material is his vest and The Rock's is an unnamed body part, either of which
may only present a back face once the character leans or turns. What the renders do settle is that
the *measured* benefit is concentrated in a handful of characters rather than spread across the
roster, which is worth knowing before anyone spends more on sidedness.

**Alastor is the control and came back 0.0000% on all four views**, as he must -- his eyes already
shipped double-sided, so there was nothing to release. That zero is only trustworthy because the
same code released 33 other materials and nine of those characters moved.

Two things the check got wrong first, both of which produced a convincing zero:

- **A trailing `
` silently disabled it.** The material list was written with Windows newline
  translation, so `read` left a carriage return on the LAST name of every line. Ten characters
  have exactly one named material, so for those **nothing at all was released** and the pair was
  identical by construction -- including Alastor, whose 0.000% would have read as the control
  passing. Only the script's own "unmatched material name" warning caught it. It now strips
  whitespace, and the released count is asserted against the roster: 34 of 34, no mismatches.
- **A head-framed camera cannot show a material that is not on a head.** Spider-Man PS's
  webshooter is on his wrist and showed only once a whole-body view was added, so a view that
  finds nothing is reported per view rather than per character.

#### The eight that showed nothing were OCCLUDED, not wrong -- and the cross-check is not roster-wide

Chasing the zeros found something worth more than the renders did. `isolate.py` deletes every face
that does not use the flipped material and renders what is left from front, back and side with
culling on and off. If that pair differs, the geometry really does have back faces a viewer can
see and the full-figure zero was something standing in front of it.

| material | culled vs not, isolated | reading |
|---|---|---|
| Power Girl `mesh1` | **23.10%** from behind | a genuine sheet, hidden by her body |
| Scott Hall `Hall_Vest` | 10.00% from the front | ditto |
| Scott Hall `..._Hall_Teeth` | 9.72% from behind | teeth, inside a closed mouth |
| The Rock `Object015` | 8.18% from behind | |
| Sayuri `Moles` | **vanishes entirely when culled** (luminance 0-1 against 0-108) | |
| Spider-Man `Model001_Material003.001` | 1.62% | |
| Jessica Rabbit `Material.007` | 1.49% | |
| Vegeta `Material_46` | no verdict -- all six frames rendered black | **unresolved, see below** |

**So the measurement was right and the renders were the thing that was misleading.** A static
camera in front of a dressed figure cannot see a vest lining, the inside of a mouth, or a mole
decal's back face; culling would still lose all of them the moment the character turns.

**`sidedness.py` and the exporter do NOT agree across the roster.** Of the 34 flips, two are flat
contradictions -- not rounding:

| | exporter | `sidedness.py` |
|---|---|---|
| Sayuri `Moles` | 100.0% | **0.0%** |
| Vegeta `Material_46` | 100.0% | **0.0%** |

The earlier "68 of 68 materials agree" was measured on **four characters** and does not generalise;
treat it as evidence about those four. The cause is that the exporter builds connected pieces
within a MESH while `sidedness.py` builds them across the whole scene, so a decal lying on a body
and sharing its vertex positions welds into the body in one and stays a small patch in the other --
Sayuri's 12-face mole patch against a 25,648-face body piece. **On Sayuri the exporter is right**:
culled, her moles disappear completely.

#### SETTLED: all 34 flips are correct, and neither static cross-check is trustworthy

Vegeta's `Material_46` is a sheet. Three things had to be fixed before that could be seen, and
each had produced a confident wrong answer:

- **The isolated render was defeated by the material itself.** `Material_46` is `Metallic 1.0,
  Roughness 0.0` -- a perfect mirror -- which renders BLACK under sun lamps with no environment to
  reflect. Six black frames read as "no verdict" while the geometry was fine throughout.
  `isolate.py` now replaces every material with a matte grey stand-in and carries the culling flag
  on that, so the render tests GEOMETRY and a shader cannot defeat it. Vegeta then comes back at
  **12.79% from behind**, against Sayuri's `Moles` at 20.15% as the control.
- **`matgeom.py` was lumping disconnected faces into one piece.** `Material_46` is a symmetric
  left/right PAIR of 380-triangle pieces; measured as one set their signed volumes partly cancel
  about a shared centroid and solidity came out **0.0648**, three times the threshold. Split per
  connected piece -- which is what the exporter and `sidedness.py` both do -- each piece is
  open 5.74 / solid 0.0191 and open 5.28 / solid 0.0189, both sheets, **100.0% sheet area, the
  exporter's number exactly**.
- **`sidedness.py`'s two disagreements have two different causes**, and neither is the exporter's.
  On Sayuri the glTF importer merges every mesh into a single 91,632-face object, so
  `remove_doubles` welds her 12-face mole decal into a **25,648-face body piece** -- a closed body,
  hence "not a sheet". On Vegeta the pieces are found correctly (2 x 190 quads) but the metrics
  land on the far side of `SOLID_MIN`: 0.0268 against 0.0191.

**Checked across all 34 flips rather than four characters this time**, `matgeom.py` agrees with the
exporter on **30 of 34** -- including Sayuri and Vegeta, now both 100.0%. The four it disagrees on
are different ones, and the render settles every one of them in the EXPORTER's favour:

| material | exporter | `matgeom.py` | isolated render |
|---|---|---|---|
| Alice Ivy `Teeth` | 100.0% | 0.0% | **4.86% from behind -- sheet** |
| Ariel `Brows01` | 30.4% | 18.6% | **2.65%, all three views -- sheet** |
| Ariel `Brows02` | 37.5% | 17.7% | **2.37% -- sheet** |
| Ariel `Brows03` | 36.4% | 18.1% | **2.37% -- sheet** |

Ariel's three brows sit just under the 20% threshold on `matgeom`'s attribution and just over it on
the exporter's, which is the same sensitivity the threshold work already found in solidity. Her
brows were visibly affected in the whole-figure render too -- they are the two red arcs in the
contact sheet -- so the exporter's side of that line is the correct one.

**So: 34 of 34 flips are right, and the two Blender implementations each undercount in their own
way** -- `sidedness.py` by 2, `matgeom.py` by 4. Neither is a reliable arbiter on its own. The
shader-independent isolated render is, because it asks the only question that matters: does
culling this material's own faces lose geometry a viewer could see? Use `isolate.py` for anything
disputed, and treat a static sheet-area figure as a proposal.

#### Three zeros in a row, each of which looked like an answer

Worth listing together, because the same shape kept recurring in one afternoon:

1. **A trailing `
`** meant the last-named material of every character was never released, so the
   ten characters with one material had identical pairs -- including the control.
2. **Blender's default 0.1 m near clip** swallowed Sayuri's 1.5 cm mole patch whole: the camera sat
   4.6 cm away, the frame came out empty, and the pair diffed to 0.00%, which read as "closed
   geometry, the flip buys nothing" -- the exact opposite of the truth. Clip planes are now scaled
   to the subject.
3. **The guard against that** printed nothing, because Blender's bundled Python has no PIL and the
   runner's grep filtered its line out anyway. `grep -c EMPTY` returning 0 meant the check had not
   run, not that no frame was empty.

A zero is only worth something next to a non-zero produced by the same code. Every table above has
one.

#### The exporter undercounted too, and only a both-directions check found it

Comparing all 227 materials rather than the 34 the exporter flipped turned up two it was
CULLING that an isolated render says are sheets: Alcina's `Material.007` (1.42% of its silhouette
lost from behind) and `Material.013` (2.05%). Nothing that inspects only what a rule FIRED on can
find what it missed.

The cause is the same decal case that `sidedness.py` had: `Material.007` is 2,792 triangles in
**482 separate 8-triangle flakes** which weld into a larger non-sheet piece, so by piece it
measured 0.0%. `SheetShareByMaterial` now also measures each material's OWN faces as connected
pieces and takes the better of the two, gated on the same decal-vs-patch test -- a piece counts
only when its rim is still free in the WHOLE mesh, or Ariel's `Ears`, `Irises` and `Lips` come
back as sheets and the per-submesh bug returns by another road.

One thing the measurement forced: the 12-triangle floor had to move from per-piece to per-material
TOTAL. These pieces are small by nature, and a per-piece minimum would have discarded all 482 of
Alcina's flakes and rescued nothing.

Verified by rebuilding four characters, three of them controls that had to not move:

| | before | after | |
|---|---|---|---|
| Alcina `Material.007` | 0.0% | **79.0%** | fixed (`matgeom.py` predicted 78.7%) |
| Alcina `Material.013` | 0.0% | **64.9%** | fixed (predicted 64.9%) |
| Sayuri `Eyelashes` | 0.0% | 0.0% | control against over-reach -- 4 pieces at openness 0.00, fully closed, and the render loses nothing |
| Ariel `Ears` / `Irises` / `Lips` | 0.0% | 0.0% | control: patches of a closed head, the per-submesh signature |
| Alastor `Eyes.001` / `Head.001` | 100% / 0.0% | 100% / 0.0% | the hand-made answer, preserved |

Alcina goes from 3 double-sided materials to 5, cull-only against her installed build, and the
roster to 36 across 17 characters.

#### Pair materials by what they USE, not by name and not by order

Verifying those three needed a pairing that survives the rename, and the obvious two both fail:

- **ORDER fails silently.** UnityPy enumerates objects in file order, which is not material index
  order. Pairing by position matched `JessicaRabbit_2` against `JessicaRabbit_5` and reported
  sixteen differences on a character that has one. A pairing that invents differences is worse
  than none, because every one reads as a regression.
- **TEXTURE KEYS fail where textures are duplicated.** Jessica has 11 materials and only 6
  distinct texture-assignment keys, so five were lost and her double-sided count came back 0 -> 0
  instead of 0 -> 1.

So each is used only where it is valid: texture keys for Iron Man, whose names were rewritten;
names for the other two, whose names already agree. With that, all three differ in nothing but
`_Cull` and the no-shine set.

#### Iron Man had four candidate sources and only texture SIZE could separate them

`IronManMark85.vrm`, `-full`, `-tex1k` and `-trim` all pass the rig and material-count gates and
all score 100% on texture names, because the names are identical in every one. The bundle carries
each texture's dimensions, and that settles it: the installed build is thirteen textures at
**1024x1024**, which `-tex1k` and `-trim` match while `.vrm` is 2048 and `-full` is 4096. Choosing
either of those would have doubled or quadrupled his texture memory with nothing to show for it.

`-trim` is then ruled out on geometry -- 173,451 triangles against `-tex1k`'s 639,859, a 3.7x
difference -- and the rebuild from `-tex1k` lands within **0.113%** of the installed bundle's size,
where several megabytes of index and vertex data would otherwise be missing. **Check texture
dimensions whenever a model has resolution variants**; nothing else in the selection sees them.

#### A stale output file fails a build and reads as a model fault

Gadget Hackwrench failed the first batch with `IOException: Cannot create a file when that file
already exists`, from `File.Move` in `BackgroundHelper.Export`. **Nothing to do with her model** --
her six materials had already measured 0.0% sheet area and been culled before the throw.
`BackgroundHelper` builds a MacOS metal shader bundle into the temp cache and moves it to
`Assets\<name>_metal.bytes`, and a stale one from three days earlier was sitting there; `File.Move`
will not overwrite. Delete `Assets\<name>.yargchar_metal.bytes` (and its `.meta`) in the SCRATCH
project and the export succeeds. The `_metal_*.mat` clones the exporter normally deletes itself
leak too, because the throw happens first.

The batch reported **exit 1** for this one failure out of 58. Verify the artefact, not the exit
code -- the other 57 were written and correct.

## Known per-model arguments

| Character | rig | height | notes |
|---|---|---|---|
| Prix | mixamo | 1.70 | shape keys must be dropped, else she builds at 0.42 m. **As installed 2026-11-12:** `aiStandardSurface4` (the lens on `L_iris`/`R_iris`) is set to alpha 0.08 with `set_material_alpha.py` — it shipped OPAQUE, wearing her SKIN atlas, parked in front of perfect blue eyes. She has no source here, so this is an edit to the built `.vrm`, not a rebuild; census identical and only the two collider helper nodes differ in rotation. **Her hair stays untouched** |
| Pomni | pomni | 1.70 | exclude `^Circle`; `VRM_VISEME_GAIN=3.0` (4.4 turns her upper lip inside out); `VRM_BLINK_BAKE="EyelidSup.L=1,0.55,0,0;EyelidInf.L=1,-0.5,0,0;EyelidSup.R=1,0.5,0,0;EyelidInf.R=1,-0.5,0,0"` and `VRM_BLINK_LASH="^Lashes"` (lash ticks lie on the closed seam, 4 mm in front of the lid, keeping 40% of their height) -- her blink is four eyelid BONES (peak at frame 30 of `Animation`), not a shape key; her `Lashes/Closed` key only moves two lash ticks and leaves the eyes open. The bake applies Solidify+Subsurf to the lid meshes, writes the closed pose as a `Blink` key and binds it. Rendered at weight 1.0: dark lids with a slit, matching her Sketchfab blink. Her iris `Big`/`Small` keys ride on YARG's own facial events: `VRM_EXPR="Wide_eyed=Eye.L/Big;Squint=Eye.L/Small"` makes them custom expressions named for lipsync event types, which `VRMCharacter.TryGetExpressionKey(string)` sets by name -- `Big` fills the eye with iris, `Small` shrinks it to a pinpoint (rendered, both eyes). The chart generator emits `Squint` but not `Wide_eyed`. **Added 2026-11-12, and she cannot be rebuilt without it:** `VRM_VISEME="aa=Face/A,ee=Face/ClosedTeeth,ih=Face/ClosedTeeth@0.7,oh=Face/OpenNoTeeth,ou=Face/OpenNoTeeth@0.6"` — her mouth shapes are named for an artist and only `A` is guessable, so without this she builds at 1/5 visemes. 32,764 triangles, 16 meshes, 27 morph targets, 5/5 bound. **Rebuilt and reinstalled 2026-11-12 for the collider-group fix alone** (item 0a) — no alpha change; backup `.precolgroup` |
| Sayuri / Aiko | cc_base / mixamo | 1.70 | hairrig `^Hair$` — no hair bones of their own. **Sayuri as installed 2026-11-11:** add `VRM_BREASTRIG=1` (the recovered ARGV is the original build and omits it — without it the rebuild comes back with 4 spring chains against her 6) and `VRM_TEX="Eye_Shadows=Eyelashes_Opacity.png:alpha"` (she has one `Eyelashes_Opacity.png` and two materials that need it; the picker gives it to the one whose name matches). Her model is `source/Sayuri dans.fbx`, its texture paths point at `C:\Temp\CharacterCreator4Temp\` on someone else's machine and the builder relocates all 8 of them. 91,632 triangles. **As installed 2026-11-12:** add `VRM_BLEND_MATERIALS="Eyelashes;Eye_Shadows;Lace;Moles;Hair"`, then run the result through `add_colliders.py` with `VRM_RECOLLIDE=1`. **That last step is not optional and is not in the ARGV**: what is installed went through that round trip, which adds 19 named collider nodes and normalises bone rolls, so a direct build reads as `differs` against the installed bundle (25 bones off by exactly 90° or 180°) until it has been round-tripped too |
| Aiko | mixamo | 1.70 | exclude `^Girl2\.[0-9]` — one girl, 15 Mixamo clips |
| Batman | multiversus | 1.88 | run `prep_batman.py` first: two half-characters on two armatures |
| Chibi Rem | rigify_def | 1.55 | exclude `'^(?!GME_Rem$).*'` |
| Gwen Stacy | mixamo | 1.70 | hairrig `island:1`, `HAIR_ANCHOR=0.70 HAIR_SEGS=2 HAIR_STRANDS=3` |
| Junio Sonic | sonic | 1.00 | `VRM_DROP_SOLIDIFY=1`, exclude `^Dots` |
| B1 Battle Droid | b1 | 1.93 | four of five meshes are empty placeholders |
| Thanos | advskel | 2.40 | source is a kneeling pose; head emission must be zeroed |
| Alastor | mixamo | 1.95 | exclude `^(Cube\|Microph)` — detached mic inflates the bounds **As installed 2026-11-11 (in-game result pending):** build with `VRM_VISEME_GAIN=2.2 VRM_DROP_MATERIAL_FACES="Material.001" VRM_ORIENT_CONSISTENT="Body.001;Head.001;Eyes.001"`, export with `YARG_CULL_OFF_MATERIALS="Eyes.001" YARG_NO_SHINE_MATERIALS="Body.001;Head.001;Eyes.001"` and `-Force` (21,415 triangles against 40,124 on purpose). `Head.001` is single-sided on purpose, as a test of whether the mask-through-fringe fault was winding. `Eyes.001` is oriented too (they were inverted: 0% facing the front, hidden by the double-sided material) and the small pieces are judged. One closed 3 cm head solid at z 1.55 stays inside-out and is not understood. He has no outline. See `docs/character-models.md` |
| Jessica Rabbit | rigify_plain | 1.80 | exclude `^(Icosphere\|Object_12\|Object_13\|Object_15\|Object_17\|Object_19\|Object_21)$` — see her row in the recipe table below. The blend-era `^(BezierCurve\|Cylinder\|Cube)` recorded here until 2026-11-12 matches nothing in the GLB she is actually built from |
| Clone troopers | mixamo | 1.83 | |
| Jinx | ue4 | 1.68 | braids and bangs already in the rig |
| Shrek | mayajnt | 2.10 | **As installed 2026-11-12:** `t_Shrek_alpha_c` (material `Shrek_1` in the bundle) is a CUTOUT, applied with `patch_alpha_cutout.py` rather than by rebuilding — it is a real opacity map, 40.8% clear and 0.0% mid under its own UVs on a 238-vertex card, and honouring it gives his tunic the ragged hem it should have. **Do not ship this by rebuilding**: the Blender round trip changes 60 bone orientations at arbitrary angles, and his `.vrm` and bundle otherwise agree exactly |
| Gordon Freeman | valvebiped | 1.80 | **As installed 2026-11-12:** build from `m2/source/Valve_Gordon_Freeman.fbx`, textures `m2/textures`, with BOTH of these or he loses something — `VRM_BLEND_MATERIALS="lens"` (his glasses lenses shipped opaque and drew as two solid white panes over his eyes) and `VRM_VISEME="aa=gordon_freeman/AU26ZR+AU26ZL,ee=gordon_freeman/AU12R+AU12L,ih=gordon_freeman/AU12R+AU12L@0.7,oh=gordon_freeman/AU18R+AU18L.001,ou=gordon_freeman/AU18R+AU18L.001@0.75"`. **His shape keys are FACS action units and match none of the automatic patterns**, so without that map a rebuild drops all 32 of them and binds nothing — which is exactly what happened on the first rebuild, silently, with every census count unchanged. 7,169 triangles, 4 meshes, 7 materials, 12 morph targets, 5/5 bound. Do NOT add `eye-iris-green.tga` or `onefreeman` to the blend list: both alphas are specular masks, and honouring them hides his irises and erases his suit. **2026-11-12, second pass: he needed no rebuild at all** — his `.vrm` already carried `alphaMode: BLEND` on `lens` and the fault was entirely the exporter's, so his installed bundle is a straight re-export of that same `.vrm`. That was also the safer route: a rebuild is what dropped his 32 FACS keys the first time. His lens now renders as glass you can see his eyes through, where it had been a speckled hard mask |
| Joker / Miku | maxbiped | 1.85 / 1.58 | **Miku, as installed 2026-11-15:** build from `miku-final.blend`, textures `miku_orig/textures`, exclude `^ts_bot`, **spring argument EMPTY** and `VRM_CLEAR_SPRINGS=1 VRM_FINGER_FILL=1`. Her intermediate carries the `HairSpring_1_*`/`HairSpring_2_*` twintail chains an earlier session built, so `VRM_CLEAR_SPRINGS` wipes those and `DEFAULT_SPRING` rebuilds exactly one chain per twintail — 2 chains, 4 joints each, 10 colliders, `MonoBehaviour` 22 -> 41. **Do NOT pass `$^` as the spring argument** (see below), and do not pass `VRM_EXPORT_POSE=rest`: her recipe has never had it and adding it moves 18 bones, 45 deg on the fused thumb metacarpals. Her skirt still does not swing and cannot be rigged by the current interface — one mesh, one material, no skirt bones, so no pattern can isolate it |
| Tenna | rigify_def | 1.80 | exclude `^(Floor\|Lights\|Sign)` |
| Sophia | rp | 1.70 | |
| Steve | steve | 1.80 | |
| Shadow | sonicforces | 1.05 | |
| Pepsiman | arp | 1.85 | |
| Vegeta / Spider-Man PS | mixamo | 1.64 / 1.75 | |
| Mannequin | simple | 1.75 | |
| Sonic (HD) | mixamo | 1.00 | model arrives UNRIGGED — auto-rig it on mixamo.com first, then `VRM_RIGID="island:0=Head"`. Its T-pose is in the clip, not the rest skeleton |
| Alcina Dimitrescu | rigify_plain | 2.90 | 9'6" is correct and her static pose is her SHAPE — never reset it to rest. exclude `^NurbsPath` (the cigarette holder skewers her hand), `VRM_TEX="Material.005=CABELOO_preto_1.png,Material.019=(null)_Base_Color.png"`. The floating hat was the unrigged-mesh rescue resizing her whole rig by 0.5568 to fit one stray dress train; it is fixed. **As installed 2026-11-12:** add `VRM_BREASTRIG=1` and `VRM_CUTOUT_MATERIALS="Material.005;Material.006"` — her hair and eyelashes, which shipped opaque and put two black slabs over her eyes. Build from `Alcina102.blend`, 350,162 triangles. Her colour maps are all noise fields and she renders white; that is the archive, not the build, and at 2.9 m her head is above the character-select camera — which also means **no podium render can verify a change to her face**; hers was accepted on the numbers alone. **Updated 2026-11-12:** `Material.006` (`CILIOS`, the lashes) moves from the cutout list to `VRM_BLEND_MATERIALS="Material.006"`; keep `VRM_CUTOUT_MATERIALS="Material.005;Material.006"` as it is, since an explicit blend now outranks it. Her rebuild also clears the four orphaned colliders in item 0a. **Updated 2026-11-12:** add hairrig `Material.005` (positional 10). Her hair is its own 160,985-vert mesh with **no vertex groups at all**, so the rigger builds its weights from nothing; it comes out with four 4-joint `HairSpring` chains and 125,849 vertices weighted, and `identify_build.py` compares 80 bones with **0 length and 0 rotation mismatches**. Before this her one collider group was referenced by no chain — the note in the collider table about her colliders "attaching to nothing" was that, and it is now resolved |
| Yui Suzukaze | mixamo | 1.60 | recovered from her own .yargchar, re-rigged; needs the VRM_TEX map from the submesh headers |
| Lola Bunny | multiversus | 1.75 | exclude `^Icosphere` |
| Mickey Mouse | mixamo | 1.10 | archive is called `talking.zip` |
| Elite Terrorist | mixamo | 1.83 | |
| Jessica Rabbit | rigify_plain | 1.80 | **Corrected 2026-11-12 — the values that were here described a build that was never installed.** Source is `jessica_rabbit.glb`, proven by the installed bundle's own node names (`GLTF_created_0_rootJoint` and sixteen `Object_NN` meshes, which exist only in the GLB). Exclude `^(Icosphere|Object_12|Object_13|Object_15|Object_17|Object_19|Object_21)$` — the stray sphere and the six `metal` mic-stand parts, the same seven objects the old blend-era `^(BezierCurve|Cylinder|Cube)` dropped under `.blend` names. **Without it the build refuses to run**: those unrigged meshes inflate the scene's Z by 3.33x and it aborts *implausibly narrow, 0.1397 m wide for 1.8000 m tall*. **Pass NO `VRM_TEX` and an EMPTY texture directory** — the recorded `rskin=Skin_makup_0003_Body_multires_sculpt.001_m.jpg` is an atlas for the `.blend`'s UV layout on a black background, and on the GLB's UVs it paints half her face and the inside of her mouth solid black; the installed bundle carries the GLB's own `Image_5` and none of the zip's `Body_resculpt1*` maps. Keep `VRM_RIG_MORE='^glitter-transprnt$@spine#4,4,0.2'` for the skirt, hairrig `^hair`, then **round-trip through `add_colliders.py` with `VRM_RECOLLIDE=1`** — that is where her colliders come from and it normalises bone rolls; without it 31 bones disagree on rotation, with it zero. Result against the original bundle: 178 of 178 names, 0 rotation mismatches, 177 of 178 lengths within 0.5 mm, 15,706,041 bytes against 15,590,635. The one residual is `GLTF_created_0_rootJoint`, 13.4 mm longer in the original. Her 1.867 m is NOT a height: her REST mesh data spans 1.8672 m while her POSED model measures 1.8000 m, and the sweep reads rest bounds. The same 1.8672 is in the `.vrm` behind the original build. She is the only one of 52 characters with a documented target that misses it, so it is hers alone and not an exporter fault |
| Alice Ivy | cc_base | 1.70 | exclude `^COLLIDER`. **As installed 2026-11-12:** `VRM_BREASTRIG=1 VRM_VISEME_GAIN=2.2 VRM_VALUE_ALPHA=1` and `VRM_BLEND_MATERIALS="Std_Eyelash"`. **`VRM_VALUE_ALPHA=1` is not optional for her**: her `Custom_Eye` mesh carries `EyeMoisture_Left`/`_Right`, a wet-film shell in front of the eyeballs that is black at **alpha 0.051, `blend_method=HASHED`, no texture**, and without the switch it ships `baseColorFactor [0,0,0,1]` — **a solid black disc over each eye**, with her correctly-textured eyes intact underneath. Checked before turning it on: on her it changes those two materials and nothing else (every other material either has an image in Alpha or sits at 1.0) — the lash only. **Her four hair materials stay cutouts on purpose**: they lose 1% of their ink to the 0.5 threshold, so a blend recovers nothing and gives up a cutout's sorting. Built both ways and compared on the podium before deciding. **Updated 2026-11-12:** add hairrig `Hair` (positional 10). She shipped with two chest chains and no hair chain; `Hair` matches her mesh `HS_SBH_Hair_G9_Shape`, 30,717 verts hanging to z=1.394 under a head bone at 1.533, and gives her four 4-joint `HairSpring` chains with 25,713 vertices weighted onto them. Adding it changes nothing else: `identify_build.py` compares 149 bones with **0 length and 0 rotation mismatches**, the names falling to 89.2% purely because of the 18 new bones |
| Ariel | daz | 1.70 | hairrig `Hair`. The ARGV was recovered from her own `.yargchar` — `lPectoral` and `abdomenUpper` are DAZ names, and the mesh bounds give the height — but **she is not sourceless, and this row was read that way twice**: her model is `base-female-character.zip`, `source/Ariel For Sketchfab.fbx`. **As installed 2026-11-12:** `VRM_BREASTRIG=1` and `VRM_BLEND_MATERIALS="Eyelashes;Hair Cap"`. `EyeMoisture` and `Cornea` are deliberately left as cutouts and are the only `HARDCUT` and `INVISIBLE` left in the installed set: at a lowered cutoff `EyeMoisture` drew an opaque white film and erased her irises, and a blend is a different operation on the same suspect alpha |
| Killer Clown | mixamo | 1.80 | hairrig `hair`. Her bones are Mixamo's with the prefix stripped (`Hips`, `LeftHandIndex1`, `HeadTop_End`), which the family auto-detects. **Source confirmed 2026-11-15:** `killer-clown-v2-balatro-style.zip`, model `source/Catwalk Walking.fbx` (a Mixamo animation export, which is where those bone names come from) with `textures/`, no exclude and no spring pattern. Rebuilt from exactly that on 2026-11-15 and it is **NOT what is installed** — the rebuild was the control for the hair-rigger fix, and she was patched with `patch_springs.py --unrig-hair` instead. The rebuild agrees with the patch on the outcome (0 hair chains, 2 chest chains) but was never exported to a bundle, so nothing here claims her recipe reproduces her |
| Heels | cc_base | 1.70 | hairrig `Hair`; the archive holds `source/untitled.zip` with the `.blend` inside. ~~Do not reinstall yet — a rebuild loses her transparency~~ **Resolved 2026-11-11**: that was the missing-alpha bug. A rebuild now keeps all five of her transparent materials and adds two more (`Std_Eye_Occlusion_R`, `Std_Tearline_R`). `High_Heels` and `Underwear_Bottoms` stay opaque, as installed — their "opacity" files are merged diffuses with no alpha channel left. **As installed 2026-11-12:** add `VRM_BREASTRIG=1 VRM_VISEME_GAIN=2.2` and `VRM_BLEND_MATERIALS="Std_Eyelash;Std_Tearline_R;Std_Tearline_L;Std_Eye_Occlusion_R;Std_Eye_Occlusion_L;front_hair_Transparency;tail_Transparency"` — seven blended, two cutouts left. Her hair IS in the blend list, unlike Alice Ivy's: hers loses 25.5% of its ink to the threshold and renders as speckle without it. Naming both the `_R` and `_L` of each pair is not redundant — the archive's merged texture is `Std_Eye_Occlusion_L_Diffuse-Std_Eye_Occlusion_R_Opacity.png`, so the opacity picker matched `_R` by name and left `_L` a cutout |
| The Rock | mixamo | 1.96 | Archive `the-rock.zip` -> `source/The_Rock.7z` -> `Rock.fbx`, textures beside it. Two stages and **both are needed**: `scale_rig.py` (his skeleton spans 4.4726 m against a 1.96 m mesh with bones 1.7011 m below the floor; factor 0.3978 about the hips), then `fit_joints.py`. ~~SCALE ONLY, do not run fit_joints~~ — that was written off a REST-pose render, and on the podium the scale-only build's fingers stretch into strips past his knees. Only the posed render shows it. What IS removed from the fit is the **shoulder** joint, which doubled his span to 0.548 and is the gorilla-arm defect. Check with `proportion_check_installed.py` (expect shoulders near 0.249, reach near 0.938) AND a podium render of the hands — `bone_fit.py` alone rewards exactly what the fit does. **Installed 2026-11-12** with scale + fit-minus-shoulder: shoulders 0.548 -> 0.295, hands intact, wrist 24.9/25.1 -> 1.9/0.9, everything else identical (6 clips, 52 humanoid, 30 fingers, 21 meshes, 1.960 m). Backup `The Rock.pregorilla.yargchar` |
| Mario | mariojnt | 1.55 | |
| Link (OoT) | linkoot | 1.65 | `VRM_TEX="Hair=Link_Link_BaseColor.png"` |
| Gadget Hackwrench | rigify_def | 1.30 | exclude `^(WGT-\|smd_bone_vis)`, hairrig `^Hair$` |
| Peach | smash | 1.70 | her forearms are stretched in the SOURCE rip, not by the build. **As installed 2026-11-11:** build from `source/model.fbx` with `VRM_CUTOUT_MATERIALS="_1.004;_4.003;_5.008;_5.012;_5.013" VRM_MTOON_ALL=1` — the iris, eyelash-plate and dress-lace materials, and one shading model so the plate does not read as a patch on her face. NOT `_6`/`_6.002`: the crown's alpha is an outline and masking it carves the jewel out. Reproduces the installed character exactly at 11,602 triangles, 16 meshes, 16 materials, 10 images, 9 springs, 173 nodes. **~~Reproduces exactly~~ — NOT TRUE as of 2026-11-15.** Rebuilt from these arguments, `identify_build.py` puts it at 89.2% name match over 173 bones with **63 rotation mismatches** against the installed bundle (and 71 with `VRM_EXPORT_POSE=rest`, so that is not the missing flag either). The counts in this row may well all match — they did for Gordon Freeman while a rebuild silently dropped all 32 of his shape keys. Her real arguments are unknown; she was fixed with `patch_springs.py` rather than rebuilt |
| Harley Quinn | mixamo | 1.70 | build from the USDZ (names transferred from the .fbx) — the .zip has no colour map and the two have different UVs |
| The Mandalorian | mixamo | 1.83 | glTF; BOTH its skeletons are collapsed, so re-rig via Mixamo. Exclude `^(grogu\|.*CRADLE\|.*JetPack\|.*RIFLE\|Icosphere)` — the pack also contains Grogu, his cradle and a rifle |
| Power Girl | mixamo | 1.80 | Injustice 2 rip, 417 bones, builds clean. Materials are called `mesh0`/`mesh1`, so pin them: `VRM_TEX="mesh0=Supergirl_A_Body_Color.png,mesh0.001=Supergirl_A_FACE_30hz_Color.png,mesh0.002=Supergirl_A_Cape_Color.png,mesh1=Supergirl_A__EyesMouth_Color.png,mesh2=Supergirl_A_Hair_Color.png"`. Her hair alpha has to be pinned too, for the same reason — add `,mesh2=Supergirl_A_Hair_Alpha.png:alpha`. She is the ONLY model of the 109 archives here whose opacity map does not name its own material, so she is the only one the narrowed alpha pick leaves without one |
| Peacemaker | dcseries | 1.85 | exclude `^Peacemaker_obj_(BlueDeep\|RedGlow\|Silver_003)_0$` — a SECOND figure's helmet on a second skeleton, floating above his head. Left in, it is the tallest thing in the file and he scales to 1.51 m. Flat-colour model: its USDZ holds no images at all, so every material reading `-> NONE` is correct |
| Vigilante | dcseries | 1.88 | same rig as Peacemaker, based at `n8` instead of `n115`. He arrives armed, and the two weapons CANNOT be excluded by mesh name: they share `Vigilante_obj_001_Pewter_002_0` with the sheath on his back and the holster on his hip. `VRM_DROP_ISLAND="Vigilante_obj_001_(Pewter_002\|Silver_003)=n17+n50"` takes the 540 vertices the two hand bones carry and leaves the 204 the spine and hips carry. Height, width and humanoid count are unchanged by it (`x1.0552`, 0.7075 m, 47/47) — the weapons never affected his proportions, which is why they survived the first build |
| Kronk | **kronkusd** | 1.95 | `Kronk_Doing_the_Hokey_Pokey.usdz`, textures `extract/0`, exclude `^$` and spring `^$` — one mesh, one material, one 512x512 map, and nothing on him that should swing. **Do NOT pass `VRM_NO_TPOSE=1`**: he LOOKS T-posed and is not, and skipping it takes `bind_check.py` from 16 bones over threshold to 52, arms off by 62 deg and up to 962 mm. No shape keys at all, so he can never lipsync or blink. `n7` sits above the humanoid root carrying 171 vertices and its weight moves to the hips; `n8`/`n9`, probably his tunic flap, are re-parented there and are rigid by design |
| Shaggy Rogers | shaggyusd | 1.83 | USDZ, 52/52 — the whole humanoid including toes and three-bone thumbs, and already in a T-pose. One 1.5 KB palette texture does the entire character |
| Spartan Mark V | rigify_plain | — | **Source located 2026-11-15** and newly recorded here: `halo-mk-v-model.zip` → `source/MkVSKETCHFAB.blend` with `textures/`, no exclude, no spring pattern, no hairrig. Proven his by the bundle's own names — its six meshes are the `.blend`'s six (`MKVHELMET`, `MKVLEGS`, `MKVLIMBS`, `MKVPOUCHES`, `MKVTORSO`, `MKVUNDERSUIT`) and its 65 bones are the `.blend`'s Rigify set. **No height is given on purpose**: he is installed at 2.146 m and nothing records that as a chosen target, so `height_targets.tsv` still has no row for him. **This recipe does NOT reproduce the installed bundle** — built at 2.146 it comes out with `thigh.L` at a different offset with its X sign flipped, so the installed character was built with arguments or a pipeline that no longer exist. What the rebuild DOES establish is that today's builder produces a perfectly mirrored rig from this source, 0.000 mm on every leg pair, which is why his right leg was patched rather than rebuilt |
| Scott Hall | mixamo | 2.01 | the `.blend` in `source/`, not the fbx: a plain 65-bone Mixamo rig. exclude `^(Plane\|Scott Hall OGscale\|M_Jacket)$` — a joined duplicate of the whole body, a duplicate jacket and a backdrop. hairrig `Hall_Hair$`. His own file points the RIGHT elbow pad at the kneepad texture, so `VRM_TEX="Hall_Elbow-R=Hall_r_elbowpad_color.png,Hall_Elbow-R=Hall_r_elbowpad_roughness.png:rough"` |
| Anakin Skywalker | anakin | 1.85 | a posed SCULPT — see the section above; needs `VRM_STANDUP=1 VRM_REBIND_STALE=1`. One leg's mesh still smears |
| Judy Hopps | **judyusd** | 1.05 | `Judy-hopps-zootopia.usdz`, textures `new/judy2/textures`, hairrig `^n(29\|3[0-8])$`, `VRM_KEEP_SIDES=1`. **Her hands stood UP out of the cuffs until 2026-11-10**: the stub-finger step laid the missing finger chains along her hand bone, which points straight down (2.5 cm, tail at -Z), and the exported hand came out turned 100 degrees against the pose the mesh is bound in. The stubs now go along the FOREARM. Check any rebuild with `bind_check.py`. Her real hands are closed fists, thumb out -- that is how she was modelled -- and her finger bones are not mapped to the humanoid fingers, so they do not animate. **The installed Judy is this USDZ build, NOT the rigify_plain FBX** -- that row used to say `rigify_plain` + the FBX, which is the abandoned attempt that renders white. Rebuilding from it produced a 38,268-triangle stranger where she has 16,521, and it was installed over her before anyone checked. Identify a character by its MESH NAMES, not its recipe row: hers are `Judy_Judy_A_01_Cloth_0` / `_Eyelash_0` / `_Face_0` with hips on `n15`; the FBX build has `Cube.001` / `Low` with hips on `spine` |
| Yoda | mixamo | 0.66 | USDZ, no skeleton at all — auto-rigged; `VRM_RIGID="island:0=Head"`, robe on `island:1` with `HAIR_BONE=Spine1 HAIR_STRANDS=1`. The USDZ has **no** eye map: merge `CHA_yodaEye_C.png` from the original zip and pin it with `VRM_TEX="yoda_mesh_RoninShader7=CHA_yodaEye_C.png"` |
| Miku | maxbiped | 1.58 | `VRM_FINGER_FILL=1`, exclude `^ts_bot` (a detached guitar), spring regex `$^` and `VRM_CLEAR_SPRINGS=1`. **The hairrig was removed**: `island:7+8` reached 198 of her ~493 hair verts and weighted 59, which sheared the ribbons apart. Her hair is ~250 strips and is splayed outward in the ORIGINAL download, not by us |
| Skibidi Toilet | valvebiped | 1.60 | exclude `^(Icosphere\|Object_2$)` — the toilet shell swamps the model |
| Xenomorph | xeno | 2.40 | `xeno/source/Xenomorph Default.fbx`, 51,548 triangles, 1 mesh, humanoid 46/46. The spring argument must be the DEFAULT regex with `\|BackTube` appended — the default alone finds only his tail and loses his four dorsal tubes, and `(BackTube\|TailRoot)` loses the tail, because the regex has to match a chain's whole run of bones rather than just its root. No `rollout/out` reference exists for him, so verify a rebuild with `identify_build.py` against the installed bundle instead: expect 171 bones, 0 length and 0 rotation mismatches. **Rebuilt and reinstalled 2026-11-12 for the collider-group fix alone** (item 0a) — four of his nine capsules were guarding nothing; no alpha change, backup `.precolgroup` |

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

### When there is no donor: reading a numbered rig off its own geometry

`name_from_donor.py` needs a named `.fbx` of the same model, and Kronk's USDZ came with none. The
numbered-rig families cannot help either -- `dcseries`/`shaggyusd` find the hips as "the parentless
`nNNN` bone with three or more children", and Kronk's root `n6` has exactly ONE child, with his
hips two levels below it.

So his family is read off the geometry, and three measurements had to come first:

- **THE FRAME WAS INVERTED.** His import maps USD +Y onto world -Z, so he hangs upside down in
  world space: feet at z=+0.05, head at z=-2.70, HEIGHT is -z. Taken the other way up, the bone
  nearest the "top" is the pelvis and every name after it is wrong.
- **29 of his 87 bones are stubs**, zero-length tips parked on the root's own position. He has 58
  vertex groups for 87 bones, and the 29 without one are exactly those. Weight mass per bone is
  what separates a joint from a stub.
- **SIDES ARE MEASURED.** His toes sit at greater world Y than his ankles on both legs, so he
  faces +Y, and with up at -Z his LEFT is +X. That is the check that was missing when Judy shipped
  criss-crossed, and `build_vrm.py` confirms it: "all 4 limb pairs are on the side their names
  claim".

The result maps hips `n11`, spine `n22`, chest `n23`, head `n24` (no neck -- the chest runs
straight into it), and four bones per limb, giving humanoid 38/38 with zero readback mismatches.

**`bind_check.py` needs a control to read.** Kronk comes back with 16 bones over threshold, which
looks alarming until it is measured against anything else: Peach and Batman score **0**, and Judy
Hopps -- installed, and the character whose stub fingers were explicitly fixed -- scores **34**,
with the same `*_thumb_*_fused` bones at 43.3 deg that Kronk has at 45. That artefact belongs to
the stub-finger step, which fires for any model whose fingers are two-bone chains; a model with
real three-bone fingers scores zero. Kronk is better than the shipped baseline, not worse.

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

### Gadget Hackwrench's teeth, and three fixes that measured as nothing

2026-11-14. No fix shipped. What shipped is a knob, three probes, and the
retraction of a conclusion this file carried for a day. Written up at length
because the wrong readings here were expensive and each of them looked right.

**The symptom.** Her whole set of teeth hangs below her lip like a collar
instead of sitting inside her mouth. `facecam.py` puts the source and the build
side by side, framed on the same material at the same fraction of each
character's own height:

```
blender --background --python facecam.py -- <source.blend> teeth src.png 0.16
blender --background --python facecam.py -- <built.vrm>    teeth bld.png 0.16
```

**What is actually wrong, in numbers.** `partsize.py` reports each material's
box as a percentage of character height, which is free of the build's rescale:

| | teeth box (% of height) | teeth centre z | eye centre z |
|---|---|---|---|
| source | 8.10 / 8.94 / 5.35 | 59.1% | 68.3% |
| build | 7.91 / 8.74 / 5.23 | 59.6% | 71.8% |

So the teeth are **not oversized** and **not at the wrong height** -- both within
half a percent. What moves is the gap between the teeth and the eyes, and it
moves FORWARD: `-0.99%` of height in the source against `-9.55%` in the build.
Eleven centimetres of it. In the source only a sliver of tooth shows between
her lips and the rest is inside her head; in the build the whole band has come
out through her face. Same geometry, same place vertically, pushed forward.

`VRM_TRACE_OFFSET="teeth,eye"` puts the move between `after import` and
`after CHILD_OF`, and nothing later touches it.

**Three fixes, and what each measured.**

1. **Bind the unweighted teeth before the pose moves.** In her source, 188 of
   the Body mesh's 4,648 vertices carry no weight at all, and they are exactly
   the 188 vertices of the `teeth` material. Everything that moves geometry in
   this build does it by evaluating the armature modifier, and that never moves
   an unweighted vertex -- so the reasoning was that her face travelled and her
   teeth stayed. Binding them to the nearest weighted neighbour a thousand lines
   earlier left the teeth **exactly where they already were**: same box, same
   centre, same driving bones, same trace to four decimals. The .vrm is not
   byte-identical -- it also reaches four stray vertices in her hair -- but on
   the thing it was written for it measured as nothing. Reverted.

   Worth knowing anyway: the pass near the END of the build already binds those
   188 vertices, and `partbind.py` confirms all 3,522 of them come out weighted,
   spread over `DEF-lip.T.L`, `DEF-nose.002/003`, `DEF-lip.T.R`, `DEF-lip.B.R`
   and `DEF-chin.L`. They are rigged. They are in the wrong place.

2. **Make `bake_pose_to_rest` test the EVALUATED pose.** It decides whether
   there is a pose to bake by testing each bone's `matrix_basis` against
   identity. A Rigify DEF bone has an identity basis and is bent by a Copy
   Transforms constraint, so the test sees a rig at rest while the character is
   in a full pose -- which is why asking to keep her pose aborted on the height
   gate with a message about "a scale hiding in an object transform" when every
   object scale in her file is 1.0. Comparing `pose_bone.matrix` against
   `bone.matrix_local` does see it: 73 bones on the normal path, 628 with the
   pose kept. The build it produced on the normal path was **again identical**,
   and with the pose kept it **still aborted** -- because the constraints are
   still live, so every bake is undone the moment the depsgraph re-evaluates.
   Baking has to happen after the constraint bake-and-remove, which is 1,400
   lines further down. Reverted; it changes the default build of every
   constraint-driven rig in the roster, which is most of it, for no measured
   gain.

3. **Keep her pose.** `VRM_KEEP_POSE=1` is now wired, and this is the one thing
   that shipped. It had been used as a probe before and had never been
   connected, so a run that passed it **silently took the normal path** and its
   result was read as "keeping the pose changes nothing". With it connected the
   teeth-to-eye gap closes from `-0.1211` to `-0.0973`, about a fifth of the
   way back to the source's `-0.0123`, and the build still aborts on the height
   gate for the reason in (2). Opt-in, and the default is unchanged **by
   measurement**, not by inspection: with the knob unset her build comes out
   byte-identical to the one from before the change.

**The retraction.** This file said the pose reset displaced her teeth. It does
not displace them: they end up within half a percent of their source height and
at their source size, and binding them before the reset changes nothing. What
the reset does is move everything ELSE -- including her eyes, which are
bone-parented to `MCH-eye.L/R` and so follow a control bone whose basis is
cleared. A teeth-to-eye measurement cannot tell those two apart, and that is
how a reference chosen for being rigidly related to the teeth turned out not to
be.

**Three traps worth not falling into again**, all of them hit in one session:

- **A centroid of one material against a centroid of another is not a
  measurement** when the two files have different topology. The build subdivides
  -- 188 teeth vertices become 3,522 and 642 lip vertices become 14,030 -- and a
  centroid of a non-uniform cluster moves when you subdivide it. Three
  comparisons built on this each said something different, and one of them said
  the build was BETTER than the source. Use a box, not a centroid: a box shifts
  by a few percent under subdivision, not by a factor.
- **A fixed world-space camera span is not a like-for-like picture.** Framing
  both files 0.20 m wide made the build's teeth look three times too big, which
  is a specific and plausible fault -- geometry left out of the rescale -- and
  the file does not contain it. `facecam.py` now frames on a fraction of each
  character's own measured height.
- **A VRM renders black in EEVEE.** MToon materials need the addon's own shading
  setup, and a black frame and "the part is not where I am looking" are the same
  picture. `facecam.py` renders with Workbench, which shades raw geometry and
  cannot go black; the question is position, not shading.

**The probes.** `facecam.py <file> <material> <out.png> [span-as-fraction-of-height]
[azimuth]` frames a render on a material and prints its centre; `partsize.py
<file> [material ...]` gives each material's box as a percentage of height;
`partbind.py <file.vrm> [material]` says which bones actually drive it and how
many of its vertices carry no weight at all.

**Answered, the same day, by `VRM_TRACE_PART`.** The teeth never move. Their
mesh DATA sits `(+0.0012,-0.0589,+0.0024)` from its own neighbouring vertices at
import and `(+0.0012,-0.0598,+0.0024)` before export -- nine tenths of a
millimetre apart, which is the 1.7% rescale and nothing else. Flat at every
stage.

What changes is the POSE. Evaluated with the armature modifier alone, the same
comparison reads `(-0.0199,+0.0281,+0.0571)` at import and
`(+0.0012,-0.0589,+0.0024)` from the next stage onward. So:

> **Her model is only correct POSED.** In the file's own pose her teeth sit 2.8 cm
> BEHIND the mouth skin around them, where teeth belong. In the rest shape they
> sit 5.9 cm in FRONT of it -- out through her lip. The rest pose of that mesh is
> not a shape anyone sculpted, and the build ships it because an action is
> attached and the reset fires.

This is the case already written up for Alcina Dimitrescu -- "a static pose can
be the model's SHAPE" -- with the one difference that hid it: hers has no action
attached, so the reset never ran. Gadget's does, so it does.

**`VRM_TRACE_PART="<material>"` is what answers this**, and it is worth reaching
for before any theory. It anchors the part to its OWN neighbours -- the nearest
400 vertices of the same mesh that are not part of it, fixed by index at the
first stage -- rather than to a second material, which is what let a measurement
of her TEETH actually be reporting her EYES. And it prints the part twice at
every stage: DATA, the base mesh through the object transform, which is what
ships, and EVAL, after the armature. A stage that changes EVAL alone moved the
POSE; one that changes DATA rewrote the geometry. That one distinction is the
whole answer here, and five fixes were written without it.

Two things it needs to be honest about, both of which it prints:

- It evaluates with **only the armature modifier on**. With a Subdivision in the
  way the vertex count changes, the same indices are not the same vertices, and
  the first run of this said "nothing to compare" six times over -- correctly,
  and uselessly.
- Comparing centroids **stage to stage within one run** is sound in a way that
  comparing them across two FILES is not: the topology is fixed, so the same
  vertices are averaged every time. When that stops being true the vertex count
  changes, and it re-anchors and says so rather than quietly averaging a
  different set.

**Why the bake did not stick, and the fix.** `armature_apply` writes the
evaluated pose into rest and leaves the constraints in place, so the depsgraph
drives the bones straight back off the new rest and the geometry just written
back no longer matches them. That is why keeping her pose baked 628 bones, still
failed the height gate by 1.25%, baked another 326, and still failed: each pass
undid the one before it. `bake_pose_to_rest` now settles the constraints --
visual transform applied, constraints removed -- immediately before
`armature_apply`. The build already does exactly this further down, on the
grounds that a driven bone cannot be posed and the exported skeleton has no use
for a control rig; doing it at the bake as well costs nothing where no bake
happens.

With that in, `VRM_KEEP_POSE=1` on Gadget **no longer aborts** -- 1.3069 m
against a 1.3000 m target, inside the gate -- and her teeth move from
`(+0.0012,-0.0589,+0.0024)` to `(+0.0214,-0.0302,+0.0614)` against a target of
`(-0.0199,+0.0281,+0.0571)`. The vertical is now right (0.0614 against 0.0571),
the forward error is halved, and the sideways error doubles. Not an install: it
also leaves her bind pose arms-down, 0.64 m wide against 0.91 m T-posed.

**The fix, and it is three lines of arithmetic.** For a vertex that HAS weights
the armature computes a skinning matrix M and draws it at `M*v`. A stray vertex
has no M, so it sits at `v` in both the posed file and the rest shape while
everything around it moves. Give it its neighbour's weights and set its rest
coordinate to `M^-1*v`, and the same M puts it back exactly where the author
had it -- so when the reset returns the face to rest, the teeth travel with it.

Runs immediately before the pose reset, and only when that reset is about to
fire. Measured against their own neighbours, her teeth now land at
`(-0.0199,+0.0351,+0.0461)` against the authored `(-0.0199,+0.0281,+0.0571)`:
sideways exact, and the error down from 10.4 cm to 1.3 cm. The sign is right on
every axis -- the teeth are BEHIND the mouth skin now, not in front of it. The
residue is the realign and the rescale moving her head a little afterwards.

**The arithmetic is checked, not trusted.** Hand-rolling the armature deform is
what moved Anakin Skywalker's head half a metre, so the pass records where each
stray sat, evaluates the mesh afterwards with only the armature modifier on, and
prints the worst disagreement. On Gadget the worst vertex lands **0.000000** from
where it started. If that number ever comes back large, or a modifier changes the
vertex count so it cannot be computed, the pass says so in the log instead of
reporting success.

**Two things it is NOT**, both tried first and both measured as nothing:

- *Binding the strays earlier than the pass at the end of the build.* Weights
  alone change nothing, because in the default path no stage rewrites the mesh
  data at all -- the reset changes the POSE and the data stays as imported. The
  .vrm came out with the teeth in exactly the same place.
- *Keeping the pose instead.* It moves the teeth two thirds of the way home and
  wrecks everything else: the facing detector reads her feet as 180 degrees off
  and turns her around, the humanoid map swaps her arms, and 85 orphan bones
  adopt the wrong parents -- her brow bones end up on `DEF-upper_arm.L`. The
  render is a balloon head on spindly spikes. The pose heuristics downstream all
  assume a rig near rest, and keeping an action pose breaks every one of them at
  once.

**Blast radius, measured.** The constraint settle only runs inside
`bake_pose_to_rest`, and the stray rebind only where an animation is attached AND
a mesh skinned to the rig has vertices with no weight:

| | bakes | settle fires | rebind fires | result |
|---|---|---|---|---|
| Gadget | no | no | yes, 188 verts | **fixed** -- teeth in her mouth |
| Alcina | 12 bones | no | no | 2.9000 m, byte-identical |
| Anakin | 49 bones | no | no | 1.8500 m, byte-identical |
| Prix | no | no | no | 1.7000 m, byte-identical |

Across every build log on this machine, 16 of 40 characters show unweighted
geometry SOMEWHERE -- but that count comes from the late pass, which looks at
every mesh including the bone-parented and unskinned ones. The rebind only
touches a mesh skinned to the rig, which is why it did not fire on three
characters that the late pass does report. Nothing else was rebuilt, so nothing
else changed; a character that is rebuilt later and does trip it has the
self-check above standing in front of it.

### The VRM add-on applies a T-pose of its OWN, and it is what made her hands a mess

2026-11-14, on "her hands are a mess" **in game**. The section below this one
records that nothing in the build touches Gadget Hackwrench's fingers, and that
is still true -- `VRM_TRACE_BONE` follows her middle fingertip from import to
the last line before export and it moves by the 1.7% rescale and nothing else.
**The trace stopped one step too early.** The add-on moves it afterwards.

`vrm1.humanoid.pose` defaults to `autoPose`, which runs the add-on's
`set_estimated_humanoid_t_pose`, whose core helper is called
`_set_bone_direction_to_align_child_bone`. It re-aims every humanoid chain,
**the fingers included**, and this script had never set the property, so every
character it has ever built went out through it.

| | pre-export scene | written .vrm |
|---|---|---|
| index knuckle | 29.9 deg | **0.0 deg** |
| middle knuckle | 45.3 deg | **0.0 deg** |
| ring knuckle | 29.0 deg | **0.0 deg** |
| thumb knuckle | 28.3 deg | **0.0 deg** |
| hand bounding box | -- | 122 x 31 x 85 mm, flattened |

Both numbers come from the same build: `VRM_SAVE_BLEND` saves the scene eight
lines above the export call, and nothing of ours runs in between. Her middle
fingertip moves 22 mm in the hand's own frame.

**It is not a broken bind, which is why no still render ever showed it.** The
skin is carried along with the bones: bone-head to skin-centroid stays 13.36 mm
before and 13.39 mm after, on every finger. The exported hand is simply a
different hand from the one the artist sculpted -- flattened and splayed.

**What that does in game.** YARG's vocalist clips rotate her finger bones
55-78 degrees, and `ANIMDELTA` shows the values are identical to Alcina's, bone
for bone, because it is the same clip retargeted. Yet half a second in, the
shipped build's fingers are still splayed and straight while a rest-pose build
of the same character closes into a grip. Identical muscle values, opposite
results, because the add-on re-aimed each bone and gave it a fresh roll: Unity
derives the muscle axes from the avatar's bind, so "curl" now turns about an
axis that is no longer the knuckle's hinge. The renders are
`measurements/gadget-hand-ingame-SHIPPED` and `-FIXED`.

It is not one character. Over the 105 `.vrm` files on this machine: **85 have a
knuckle bend of exactly 0.0, two do not** (Pomni, 3.4-5.2 deg) **and 18 carry no
finger map at all.**

**`VRM_EXPORT_POSE=rest` turns it off, and it is OPT-IN, because the add-on's
estimate is load-bearing on rigs whose own T-pose step did not run.** Built both
ways and compared in the written file:

| character | effect of `rest` | why |
|---|---|---|
| Gadget | fingers keep 29.9 / 45.3 / 29.0 / 28.3; every other joint within 0.1 deg | her T-pose step ran: arms 0.0 deg off X |
| Alcina | 3 deg at the hip, nothing else | her T-pose step ran |
| Anakin | **hip 93.9 -> 26.2 deg** | built `VRM_STANDUP_LEGS=0` |
| Prix | **elbow 0.0 -> 14.6 deg**, shoulder 1.2 -> 7.6 | a Mixamo rig: the T-pose step prints *nothing* for him, so the add-on was the only thing T-posing him |

Prix is the one to remember. Unity builds the humanoid avatar on the bind pose,
so shipping him bent would have mis-aimed every muscle axis he has -- the same
fault as the hands, applied to the whole body.

So the build **measures the rest pose whenever `rest` is asked for** and says
plainly whether it is a T-pose, joint to joint: upper arm and forearm along X,
thigh and shin vertical. It passes Gadget and Alcina and fires on Prix
(`forearm 21.2 deg`) and Anakin (`thigh 77.3 deg, shin 43.6 deg`) -- the same two
the rebuild flagged, which is what makes it a check rather than a hope.

**The guard got that wrong once first, in the way this file keeps warning
about.** Its first version asked which way each *bone points* and reported
Prix's arms as 90.0 degrees off X and his legs as 180.0 off vertical, both
sides, upper and lower, to the decimal. Numbers that round are not a pose. A
bone's tail is synthesised wherever the rig does not pin one, so a bone's axis
is a fact about the importer; the **head of the next joint down** is a fact
about the model. Measuring joint to joint turned those into 21.2 and 77.3 --
numbers that match an independent measurement of the same two rigs.

### Two reasons the hand pictures could not answer the question

Both were in the tooling, not the model, and both produced a picture that
looked like evidence:

- **`YargCharHandRender` frames on the hand BONE and renders the whole
  character.** Anything between camera and hand is what you photograph: Alcina's
  animated hand came back as a close-up of her own dress, and Gadget's as her
  face. `HandIsolate` keeps only the triangles all of whose vertices are weighted
  to that hand and switches every other renderer off, so nothing can be in the
  way.
- **`RecalculateBounds` measures the whole VERTEX ARRAY.** Filtering the
  triangles does not shrink it, so the first "isolated hand" renders framed a
  1049 x 1200 x 492 mm box -- her entire body -- and the hand was four pixels
  across. Bound the kept triangles by hand. The corrected box reads 122 x 31 x 85
  mm, which is also the measurement that showed the flattening.

`STRIPV` had a third form of the same disease: it looks for finger bones by
NAME, matching `_L_` plus `Index`/`Mid`/`Pinky`. A Rigify rig calls them
`DEF-f_index.01.L` and matches none of it, so for every Rigify character that
check has been reporting nothing wrong **by never looking**. `HandIsolate` asks
the Animator's humanoid map instead, which is what the game drives and is the
same question in every naming convention.

Measured, and NOT a defect, each with the control that settled it:

| looked like | control |
|---|---|
| `SKINDEV` 300 bone/renderer pairs off, fingers worst at 917 mm | Alcina reads 600 pairs and 2957 mm and is fine |
| fingers nearly touching: 0.7-0.9 mm between neighbours | Alcina reads 0.3-0.8 mm; the minimum is taken at the web where fingers join, so it is ~0 for everyone |
| her bind fingers curl 32.5 deg against Alcina's 15.0 | both read 0.0 from the file; the curl came from `fingerpose.py`, which sums bone AXES |
| a balloon head on thin spikes in the body render | that is her hair, from the front |

### A .vrm read back into Blender INVENTS half of what you measure

2026-11-14, chasing "her hands are a mess". Three faults were measured in
Gadget Hackwrench's hands, each specific and alarming, and **all three were
artefacts of the comparison**. Nothing in the build touches her hands. Written
up because the measurements looked clean and the numbers were real; it was the
frame of reference that was invented.

**What a glTF actually stores is a node's TRANSLATION.** It has no notion of a
bone length and no notion of a bone roll. Both are reconstructed by the importer
on the way back in, and a reconstruction is not a measurement:

| claim | measured | actually |
|---|---|---|
| "the fingertip bones were halved" | `DEF-f_index.03` 1.841% of height in the source, 0.890% in the build | a leaf bone has no child to point at, so the importer gives it half its parent |
| "the palm bones were flattened to one length" | source 2.620 / 3.201 / 3.083%, build 1.353 / 1.353 / 1.353% | the same invention, on three bones that each lost their `ORG-` child |
| "the fingers were straightened" | in the hand's rest frame the source's joints curl in +x and the build's run dead straight | the hand's rest FRAME is itself rebuilt from an invented roll, so the two sets of components are quoted in different axes |

**What is real in both files is a joint's POSITION.** Measured as a distance from
the wrist, every finger joint survives the build to within 0.1% of character
height, and the worst in the hand is 0.66%. `VRM_TRACE_BONE` settles it from the
other end: `DEF-f_middle.03.L` in the hand's frame reads
`(+0.0183,+0.0858,-0.0063)` at import and `(+0.0186,+0.0872,-0.0064)` before
export -- the 1.7% rescale and nothing else, at every stage in between. **The
build does not touch her fingers.**

> That conclusion is correct and it is not the whole answer. The trace ends at
> the last line before export, and the **VRM add-on re-poses the hand after
> it**: the same joint is written to the file at `(-0.0101,+0.0995,-0.0026)`.
> See "The VRM add-on applies a T-pose of its OWN" above. A trace that stops
> where our code stops cannot see a tool we call.

### The roster, 2026-11-14: the add-on had flattened 25 of 35 hands, and only 8 could be rebuilt

Gadget was not special. Every one of the 35 characters whose source and recipe
both survive was rebuilt with `VRM_EXPORT_POSE=rest` and again with `auto`, and
**every single auto build reads a knuckle bend of exactly 0.0 degrees** -- all
35 but Pomni, who reads 5.2 either way. 25 of them carry authored bend the
add-on was destroying, and it is not subtle: Vigilante 87.0 degrees, Peacemaker
74.5, The Rock 36.2, Scott Hall 34.8, Doom Slayer and Shaggy Rogers 34.3, The
Mandalorian 28.4, Batman 27.9, Gordon Freeman 25.2.

That also closes the open question about Pomni. She was one of only two built
files on this machine whose fingers were not flat, and the cause was recorded
as unknown. The cause is that the knob is a no-op for her: 5.2 degrees both
ways. The add-on's estimate agrees with her rest pose, so she was never a
counter-example to anything.

Ten characters changed nothing and were not touched. Seven of those have only
4 of 8 finger chains mapped -- mitten hands, with nothing to recover.

#### The rest pose has to be a T-pose, and for four of them it was not

The guard added with the knob fired on exactly four: The Mandalorian (thighs
179.6 degrees off vertical, knees above hips), Yoda (28-34), Jessica Rabbit
(left leg only, 28.0) and Peacemaker (right leg only, 27.9). Three are the same
fault, and `VRM_STRAIGHTEN_LEGS=1` -- which already existed, and whose comment
names Jessica Rabbit -- fixes them. Measured joint to joint in the FILE, her
legs and Peacemaker's come out at 0.0 degrees from vertical either way: our
straightening lands exactly where the add-on's did.

Yoda needs nothing. He passes the guard with that knob, but his fingers are
identical both ways, so there is nothing to win.

The Mandalorian is a different fault: his legs are not authored bent, his REST
pose is wrong while his ANIMATED pose is right (5.5 degrees off vertical). The
build's own test for that keeps an animated pose when it is the better T-pose,
and it declined him because **it gates on the arms** -- `_p < 10.0 <= _r`, and
his animated and rest arms are both 17.1 degrees off X, so "the clip is a T and
the rest pose is not" reads false. The legs are what differ and the test never
looks at them for that decision. `VRM_KEEP_POSE=1 VRM_STRAIGHTEN_LEGS=1`
produces a clean T-pose from the same recipe. He still did not ship, for the
reason below.

#### A ratio is not a tear, and a camera framed on the subject is not a measurement

`VRM_STRAIGHTEN_LEGS` is a DEFORMATION, so it was checked three ways, and the
first two each gave a confident wrong answer.

**Edge-length RATIO** found Jessica at 21.8x, Yoda at 13.2x and the Mandalorian
at 30.8x. A ratio decides nothing on its own: a seam edge 0.01 mm long
stretched twentyfold has grown 0.2 mm. Ranked by ABSOLUTE growth instead, with
the bone carrying each edge named, Jessica's worst is 14 mm in `thigh.L` and
Peacemaker's 27 mm in his right leg -- while the Mandalorian's is **234 mm**,
and his render is a character with no head, stub legs and the cape standing up
as a flat sheet.

**A render framed on the leg joints** then reported Jessica and Peacemaker as
pixel-identical to the shipped build, mean 0.00 of 255. That framing is derived
from the very joints being compared, so the camera moves with the subject.
Pinned in world space the same pair reads 12.6 and 7.2. Neither number is about
legs: the first hides a global vertical offset, the second is the offset coming
back.

**The angle, joint to joint, in each file's own frame** is the measurement --
no camera, and immune to offset and scale. Jessica and Peacemaker: 0.0 degrees
of change. Its first run returned exactly 90.0 for all eight of their leg
joints in both builds, which is a vertical leg measured against the wrong axis:
**glTF is Y-up**, and these positions come out of the FILE, not out of a
Blender import, unlike the build's own guard which measures in Blender where up
is +Z.

#### What stopped 16 of the 24: the recipe, not the knob

The recipes here are harvested from the `ARGV:`/`ENV:` lines builds print, so a
log IS the recipe that produced its .vrm. The most recent log per character is
NOT the recipe that produced what is installed. Rebuilt and verified against
the installed bundle, 15 of 24 differ in ways no pose knob can cause:

| Character | What a rebuild would have destroyed |
|---|---|
| Gwen Stacy | 94 -> 72 transforms; 22 bones and their spring chains |
| Sayuri | 143 -> 124 transforms |
| Link | Material 6 -> 5, Texture2D 14 -> 11; three textures |
| Chibi Rem | 180 -> 158 transforms |
| Batman | Texture2D 3 -> 6, Material 1 -> 2, names differ |
| Vigilante | an extra Mesh and SkinnedMeshRenderer, 3 materials |
| Alcina, Alice Ivy | MonoBehaviour 37 -> 53: 16 spring/collider components |

This is the Gordon Freeman fault again: exit 0, a plausible file, work quietly
gone. **Comparing the rebuild against the installed bundle cannot tell the two
causes apart.** The control that does is building the SAME recipe with `auto` --
the pipeline exactly as it ships -- and verifying THAT. Nine reproduced their
installed character; The Rock's auto build moves `LeftArm`, `LeftForeArm`,
`LeftFoot` and `LeftHand`, so his recipe is stale too and only eight shipped:
Ariel, Doom Slayer, Gordon Freeman, Heels, Joker, Scott Hall, Shaggy Rogers,
Xenomorph.

Their legs do shift by 2.4 to 12.3 degrees, which is the add-on's own leg
straightening going away, within the guard's tolerance and the same effect
Gadget shipped with.

#### Scott Hall grew 36% and nothing was wrong

35.4 MB installed against 48.1 MB rebuilt looks like a regression and is not.
His textures are identical -- 37 of them, same dimensions, same format, and
306,538,952 image bytes in both files to the byte. Summed per object type the
two bundles differ by **32 bytes**, in a TextAsset. The 13 MB is the container's
compression and nothing else, and the comparison is the strongest confirmation
in this batch that his recipe reproduces him exactly. `verify_rebuild.py`
deliberately does not read mesh data, so a file-size check is worth running
beside it -- but read it against the auto build before believing it.

#### What is still open

15 characters hold a stale recipe. The logs carry **87 distinct candidates**
between them -- Jessica Rabbit 13, Alice Ivy 11, Alcina and Sayuri 7 each -- and
a candidate can be eliminated in Blender time alone, because almost everything
`verify_rebuild.py` compares is visible in the .vrm before Unity is involved:
node count is GameObject/Transform, images are Texture2D, materials are
Material, and the spring bones and colliders in the VRM extension are the
MonoBehaviours. Calibrate the node-count-to-Transform offset on the eight pairs
now known to be correct before trusting it.

`VRM_TRACE_BONE="<bone>,<reference bone>"` follows one joint in another bone's
REST frame at every stage. Rest and not pose on purpose: `bone.matrix_local` is
what a bind is expressed against, so a stage that rewrites it moves every vertex
bound to that bone, and a pose-space reading hides exactly that. Use it on a rig
the way `VRM_TRACE_PART` is used on geometry.

### Recovering a stale recipe, 2026-11-15: the arguments are not the recipe

Fifteen of the roster could not be rebuilt on 2026-11-14 because the recipe
harvested from their build logs no longer reproduced the installed character at
all -- Gwen Stacy lost 22 bones and their spring chains, Link three textures,
Batman and Vigilante their materials. The logs hold many more candidate recipes
than the one `recipes.py` picked, so the question was whether the right one was
still in there. **Two of the fifteen were. The other thirteen fail for a reason
no argument search can fix.**

#### A cheap predicate, and what it cost to make it trustworthy

Searching by building is expensive, so the search runs on the `.vrm` instead:
nearly everything `verify_rebuild.py` checks apart from the rig is visible in
the glb before Unity is involved. The first version of that predicate compared
counts and was **wrong on every count but one**, which the nine already-proven
pairs said immediately:

| glb -> bundle | delta across the nine | usable? |
|---|---|---|
| `nodes` -> `Transform` | +1, +2 | no |
| `images` -> `Texture2D` | 0, +1, +3, +6, +7, +15 | no |
| `materials` -> `Material` | 0 | **yes** |
| springbone pieces -> `MonoBehaviour` | +16, +17, +18, +22 | no |

Images are unpredictable because Unity's VRM importer **duplicates an image per
sampler usage** and suffixes it by colorspace, so one glb image becomes `name`,
`name__UNIGLTF__DUPLICATED__2`, `name.normal`, `name.standard`. Strip those two
artefacts and the base-name SET is exact. Node names survive verbatim as
GameObject names. And `MonoBehaviour` decomposes exactly:

    MonoBehaviour == 22 + joints + colliders + (1 if any spring else 0)

22 on the nose for the four characters with no spring bones at all, and the extra
1 is the manager component. Without that fourth leg the predicate passed Lola
Bunny and Tenna, whose ONLY difference from their installed bundle is spring-bone
count, 34 to 42 and 33 to 40. **The negative control caught two false positives
before the search ran** -- run a predicate over cases already known to be stale,
not only over cases known to be good.

Validated: 9/9 on the proven pairs, 0/15 on the known-stale, 6/6 on deliberately
mismatched pairs. Then a sweep of all 397 `.vrm` files on the machine, 5,925
comparisons, found an exact match for ten of the fifteen. The predicate is
pose-blind by construction -- export pose moves node transforms and touches none
of material count, texture names, node names or spring count -- so a `.vrm` built
under either pose identifies its recipe equally well.

#### The arguments are not the recipe: the pipeline version is part of it

Fourteen candidate recipes were then built under `auto` and exported, which is
the control that decides. **Two came back cull-only:** Alcina Dimitrescu and
Alice Ivy, each on one of three recipes the cheap predicate could not separate,
because they differ only in `VRM_BLEND_MATERIALS` / `VRM_VALUE_ALPHA` and those
change material PROPERTIES, which the glb-side check does not read.

The other eight failed, and six failed because the recipe was never theirs:
`findrecipe.py` fell back to matching the output BASENAME when no log named the
exact path, and **nine different Batman logs all write a file called `Batman.vrm`**
into nine directories, one of them a different source model at a different
texture size. Require the exact path.

But Alastor and Lola Bunny came off exact logs and still failed -- Alastor's
material count 3 to 4, Lola Bunny's `MonoBehaviour` 34 to 42. Their matching
`.vrm` on disk reproduces the installed bundle; replaying that `.vrm`'s own
recorded command today does not. **So the recipe is the arguments PLUS the
version of `build_vrm.py` that ran them,** and for thirteen of the fifteen this
script has since drifted in some way that shows: an extra material, extra spring
chains, colliders fitted in a different place. No archaeology on arguments
recovers those. Rebuilding them means accepting the current pipeline's output as
the new baseline, which is a decision about the character, not about the recipe.

#### The collider round trip, and why four of them are near-misses

Batman, Chibi Rem, Gwen Stacy, Jinx and Link had no matching `.vrm` at all, and
four failed the same leg: their installed bundle holds two or three GameObjects
named `Head-Head Collider`, `Hips Collider-Hips Collider End` and
`Hips Collider1` that no `.vrm` contains. That naming is the tell. The build
writes colliders into the **VRM extension**, and it is Blender's VRM importer
that materialises them as empties called `<bone> Collider` -- so a node called
`Pelvis Collider-Pelvis Collider End` has already been round-tripped through
`add_colliders.py` once, and Unity then makes its own GameObject per collider,
named after the node it hangs off. `_Character` and `secondary` are Unity's, in
every bundle.

Round-tripping a fresh build once takes the unexplained extras from 24 to zero
for Chibi Rem and Gwen Stacy on the cheap predicate -- but the full verify still
puts them three GameObjects short, **and reports their `Head Collider` and
`Hips Collider` empties as moved**: `vrm_colliders.fit` no longer places them
where it did. The same drift, one layer down. Jinx overshoots instead: the round
trip gives him 16 collider nodes his installed bundle has never had, because that
bundle predates the limb-capsule change `add_colliders.py`'s own docstring
describes.

Two things worth keeping from that detour. `add_colliders.py` exits **2** with
"left alone" rather than re-fitting colliders the build has already written;
`VRM_RECOLLIDE=1` is what makes the round trip happen at all. And the round trip
is **pose-safe, measured**: Gwen Stacy's rest build goes in at 14.3 / 15.4 / 13.6
/ 12.1 degrees of knuckle bend and comes out at 14.3 / 15.4 / 13.6 / 12.1, to the
decimal, even though `add_colliders.py` sets no export pose and therefore runs
the add-on's `autoPose`. It is safe for a reason rather than by luck: the VRM
importer synthesises every bone tail to point at its child, so the thing
`autoPose` does -- aim each bone at its child -- has nothing left to do. The pose
setting is not written to the file at all; checking the glb for it finds nothing.

#### What shipped

Alcina Dimitrescu and Alice Ivy, rebuilt under `VRM_EXPORT_POSE=rest` from their
confirmed recipes, verify against installed as **bones only, with no position
change anywhere** -- the bind is untouched to four decimal places. Alcina's 18
moved bones are all in the hands, and the left/right asymmetry the add-on had
introduced is gone: `f_pinky.01` was 52.2 degrees on the left and 20.7 on the
right, and is now 4.2 on both. Alice Ivy moves 8 hand bones plus four leg bones
at 1.4 and 1.2 degrees, which is the add-on's leg straightening going away and
the same effect the eight shipped with on 2026-11-14.

That is **eleven of the roster on a rest-pose build** -- Gadget Hackwrench, the
eight of 2026-11-14, and these two -- and thirteen still held: the eleven whose
pipeline has drifted, plus The Rock and The Mandalorian. The eleven with a
`.preexportpose` backup in `character-backups/` are exactly the eleven that
ship one, which is the cheapest way to ask.

### Gadget Hackwrench's ears hung off her elbows, 2026-11-15: nearness is a property of the pose

Her ears were reported wrong three times before anything measured them. The
answer was not in the ear geometry, which is correct in the shipped file to
within a per-cent of its source, and not in her weights. It was one line of
this script choosing the wrong parent.

Her DEF-ear chain hangs off rigify CONTROL bones, which do not deform, so all
five ear joints per side are orphans by the test above: deform bones outside
the humanoid hierarchy that nothing would ever move. The orphan rescue adopts
each to the nearest humanoid bone --

    _near = min(_cand, key=lambda t: (t[1] - _eb.head).length)

-- and for the two outer joints it chose `DEF-forearm.L/R`. In game her ears
followed her elbows.

**It chose the elbow because it was asked after the T-pose bake.** The log
ordering is the whole finding:

    1364  T-pose: left upper arm 0.0 deg off X, forearm 0.0 deg
    1366  T-pose bake: 'Body' has 152 groups, 4648/4648 verts weighted
    1378  orphan bones: 85 deform bone(s) ... re-parented 85

By line 1378 her arms have been swung out horizontal to shoulder height and
written into the rest pose, so her forearm sits up beside her head -- and for
the two ear joints that point up and OUT, it is genuinely the closest humanoid
bone there is. The rule did exactly what it says. It measured in a pose this
pipeline had put her into, not the one she was modelled in. The three inner
joints are far enough inboard that the head still wins, which is why only
`.003` and `.004` went astray and why the fault looked like a geometry problem
rather than a parenting one.

**The wrong reasoning that nearly closed this off.** The proximity hypothesis
was raised and then dismissed, on a measurement: in her SOURCE rest pose the
head bone is 0.447 away from `DEF-ear.L.003` and the forearm 0.525, so the rule
"could not" have picked the forearm. The measurement was right and the
conclusion was wrong, because **nearness between two body parts is not a
property of the character -- it is a property of the pose.** Measuring it in
the authored pose says nothing about what the rule saw.

The fix is to measure in the authored pose on purpose. `_REST_HEADS` snapshots
`head_local` for every bone at the top of the T-pose section, before anything
in it moves a bone, and the rescue uses those positions for both the orphan and
the humanoid candidates. Re-parenting is deformation-neutral and the bone keeps
its position either way, so this changes only the CHOICE of parent.

Measured against the build that reproduced the shipped fault, same arguments,
one line different:

| | shipped build | fixed build | her source |
|---|---|---|---|
| `DEF-ear.L.003` parent | `DEF-forearm.L` | `DEF-spine.006` | -- |
| `DEF-ear.L.003` world x | **-0.416** | **+0.284** | +0.279 |
| `DEF-ear.L.004` world x | -0.284 | +0.261 | +0.257 |
| ear.L chain steps, % of hips->head | 31.78 / 32.09 / **178.02** / 35.18 | 31.78 / 32.09 / **20.56** / 35.18 | even |

Four of 183 nodes changed parent, the same four moved, and nothing else in the
file did: 6 materials, 3 texture names, 183 node names, 20 spring joints, 10
colliders and 18 expressions are identical either side. The 178% step -- a gap
five times longer than any other joint in the chain -- is what an ear stretched
to an elbow looks like in one number, and it is the measurement to reach for
when an appendage is reported "wrong" with no further detail.

`VRM_KEEP_ORPHANS=1` is **not** the fix, though it is a good control: it
collapses the gap to 20.56% too, because it leaves the ear bones parented to
`root` where nothing moves them at all. That is the problem the rescue exists to
solve, traded for a different one.

#### The rule now reports when the pose changed its answer

One build per character is enough to tell whether this moved anybody who was
already right, because the rescue computes both choices and logs the
disagreements:

    orphan bones: 4 of them would have been adopted by a DIFFERENT bone had this
    measured the baked pose instead of the authored one -- DEF-ear.L.003
    (DEF-forearm.L not DEF-spine.006), ...

Every line it prints is a bone the old rule got wrong. It is the line to read
first when a part comes out attached to the wrong body part, and it makes the
control and the treatment come out of the same run instead of two.

`VRM_TRACE_ORPHANS=1` prints all of the assignments rather than the first eight;
85 of them is a wall of text in the normal log, but eight cannot show a choice.

Run over the other characters the orphan rescue actually does work on, that line
says the change is surgical:

| character | orphan bones | adopted | choices the pose changed |
|---|---|---|---|
| Gadget Hackwrench | 85 | 85 | **4** |
| Lola Bunny | 120 | 118 | 0 |
| Judy Hopps | 2 | 1 | 0 |
| Ariel / Heels / Joker | 0 | 0 | -- |

**119 adoption decisions on other characters, none of them changed.** Ariel,
Heels and Joker have no orphans left at all, so they are null controls and say
nothing either way -- which is worth stating, because the first run of this
sweep reported "nothing changed" for four of the five and every one of those
four had **failed to build**: `blender -b <model>` opens its argument as a
`.blend`, and `build_vrm.py` imports the model itself off the extension, so
every `.fbx`/`.glb`/`.usdz` died at "File format is not supported" before a line
of the build ran. A sweep must assert that the work happened, not just that the
count came back zero.

#### Two things worth knowing about her source, and about what is still wrong

Her rig is damaged independently of anything here. `ear.L.001` is **missing from
the `rig` armature**, and rigify's Damped Track and Stretch To constraints on
`DEF-ear.L` that reference it fail to resolve on load:

    Could not find op_from: OperationKey(type: BONE, component name: 'ear.L.001', ...)

That is why the DEF-ear chain is orphaned rather than self-parenting, and it is
in the file as downloaded.

And this file still has **two other proximity searches that measure in the baked
pose** -- the non-deform weight rebind, and the stray-mesh bind. Neither fires
on Gadget, so neither was changed here and neither is measured. They are the
first place to look if another part lands on the wrong bone.

### Thanos, 2026-11-15: a glossiness map is not a roughness map, and a decoder that agreed with itself

Reported three times as "his textures are wrong". Two faults, both measured in
his **glb** rather than in his bundle, which matters for a reason given below.

#### Specular-glossiness is the other PBR workflow, and `gloss` was wired raw

His set is Diffuse / Specular / Glossiness, not BaseColor / Metallic /
Roughness. `TOKENS["rough"]` matches `gloss`, which is right -- the glossiness
map IS the file that belongs in that slot -- but **glossiness = 1 - roughness**,
and nothing in this file inverted it. glTF packs roughness in G, and his came
out of the build at exactly his source maps' values:

| map | glb G | source .jpg mean |
|---|---|---|
| Body_Glossiness | 0.460 | 0.460 |
| Head_Glossiness | 0.474 | -- |
| Helmet_Glossiness | 0.431 | -- |

Equal to three decimals, so the values went in untouched. His matte skin read
as polished and his polished armour as matte, per pixel, across the whole
dynamic range.

**The inversion has to be in the PIXELS, not in a node.** The first fix put a
`ShaderNodeInvert` between the image and Roughness. Blender's glTF exporter
accepts that link and then silently ignores it. Probed with two materials, one
direct and one through an invert:

    probe_direct     -> texture 0 -> image 0
    probe_inverted   -> texture 1 -> image 0
    image 0   R1.000 G0.460 B1.000        <- the raw glossiness, shared

One image, both materials pointing at it. The node-based fix would have changed
nothing while printing a log line claiming it had worked. Inverting the pixel
buffer instead gives a second image at G 0.540 with the standard deviation
unchanged at 37.6 -- a true complement rather than a shift -- and packing makes
no difference either way. `_INVERTED` guards against flipping twice, because
`images.load(check_existing=True)` hands two materials the same datablock and a
second inversion is the identity.

The datablock rename that was meant to make the artefact self-describing does
**not** work: the exporter names the glb image from the image's FILEPATH, so the
rebuilt Thanos still ships a texture called `..._Glossiness` that now contains
roughness. Read a bundle's texture suffix as the SOURCE map's kind, not the
slot's.

#### The second fault was already fixed, and the rebuild proves it

| material | metallicFactor before | after | roughness G before -> after |
|---|---|---|---|
| Body | **absent** | 0 | 0.460 -> 0.540 |
| Head | **absent** | 0 | 0.474 -> 0.526 |
| Helmet | **absent** | 0 | 0.431 -> 0.569 |
| Gauntlet | **absent** | 0 | 0.643 -> 0.357 |

**A missing `metallicFactor` is 1.0 in glTF, not 0.** With the texture's B
channel at 1.000 as well, his skin, head, helmet and gauntlet were fully
metallic -- which in URP/Lit throws the diffuse away and turns a dark base map
into a dark mirror. That is the larger of the two faults visually, and the
metallic guard already in this file (`metallic %.2f with no map -> 0`) fixes it
with no change from us: his build is dated 2026-11-07 and the guard is not in
it. Nothing but a rebuild was needed.

#### The decoder that agreed with itself

The first version of this investigation read the BUNDLE with UnityPy and found
his metallic/gloss map to be 5,592,404 bytes of a single byte value, `0xcd` --
no content at all. `0xCD` is also MSVC's uninitialised-heap fill, which was the
clue. The control settled it: **18 of 22 characters' metallic-slot textures read
the same flat 0xcd**, Yoda, Link, Iron Man, Batman and both Clone Troopers among
them, none of which anyone has complained about, while their base maps in the
same bundles read 250-odd distinct values. Flatness tracked the DECODER, not the
characters. One step further and "Thanos ships as chrome" would have been
reported on an artefact of a library.

The glb is readable with any JPEG/PNG decoder and needs no library that
understands Unity's serialised textures, so it is the surface to measure on.

#### What is still wrong with him

- **`EyeBall` has no base colour at all**, in the glb as `baseTex=NO`. There is
  no `Thanos_EyeBall_Diffuse` on disk -- the set ships only Specular and
  Glossiness. That is a gap in the download, not in the build, and it cannot be
  fixed without a map.
- `EyeBall`'s rough slot now takes `Thanos_EyeBall_Specular` where the old
  build took `..._Glossiness`, so it is not inverted. In a spec-gloss set a
  `*_Specular` map is an RGB specular COLOUR, not a roughness map, and it should
  not win that slot over a glossiness map. Left alone deliberately: the material
  is wrong either way until it has a diffuse, and reordering `TOKENS["rough"]`
  would change the pick for every character that has both.
- **His humanoid map is questionable and was not touched.** `rightLowerLeg:
  HipPart1_R`, `rightFoot: HipPart2_R`, with `spine`, both arms and `head` on
  bare `joint6`-`joint14` from an Advanced Skeleton rig whose deformation
  system holds 131 bones. The log says "assigned 52/52, readback mismatches 0",
  which is a count of filled slots and not a statement that they are the right
  bones. The rebuild reproduces that map exactly, so it is no worse -- but 52/52
  is not evidence of a correct rig.

#### He had no recorded recipe

No log anywhere records an `ARGV:` line for him: that echo was added after
2026-11-07, which is the gap "A build log must say what it was built FROM"
exists for. His arguments were reconstructed from the evidence --
`m10/source/Kneeling Idle.fbx` (which carries `Thanos_Rig`, `joint9` and
`Shoulder_L` and no `mixamorig`, so it is the model despite the name),
`m10/textures`, 2.40 m from the log's own VERIFIED height, `advskel`, 1024 --
and confirmed by the rebuild reproducing his humanoid map bone for bone.

### Miku's twintails, 2026-11-15: a diagnostic switch shipped as a recipe

Reported twice as "her twintails are broken". Nothing in the pipeline was
wrong. **Her recipe disabled her springs twice over, and one of the two
switches was a diagnostic that was never meant to ship.**

Her recorded arguments ended `1024 '^ts_bot' '$^' ''`. The eighth argument is
`SPRING`, the pattern that decides which bones get spring chains -- and `$^` is
a regex that can never match anything. Her environment then also carried
`VRM_CLEAR_SPRINGS=1`. Belt and braces on the same trousers, and the result was
measurable in the shipped bundle:

| | installed | after |
|---|---|---|
| `HairSpring_*` GameObjects | **8** | 8 |
| `MonoBehaviour` | **22** | **41** |
| spring chains | **0** | 2 |
| colliders | **0** | 10 |

22 is the bare count for a character with no springs at all, so all eight
twintail bones were in the file with nothing whatever to move them. They were
rigid because they were bones, not hair.

`VRM_CLEAR_SPRINGS` exists *because of her*. The comment on it says so: her
intermediate `.blend` carries the `HairSpring` chains an earlier session built,
so rebuilding her with the hair rigger switched off still shipped them, and the
switch was added to prove the chains were inherited rather than made by that
run. It did its job. Then it stayed in her recipe, with `$^` beside it, and a
measurement aid became the shipped configuration.

**The fix keeps the clear and drops the `$^`.** `DEFAULT_SPRING` contains
`hair`, which matches `HairSpring_1_0` and `HairSpring_2_0`, so with the eighth
argument empty the build wipes the two inherited chains and makes two fresh
ones -- 4 joints each, stiffness 0.60, drag 0.45, gravity 0, hitRadius 0.02,
identical to Gadget Hackwrench's four working hair chains. Clearing first is
deliberate: it is what stops an inherited chain and a new one claiming the same
bones.

#### One variable, and the first attempt was not

The first rebuild also set `VRM_EXPORT_POSE=rest`, which her recipe has never
had. It produced the right springs AND moved 18 of 90 bones -- 45.04 deg on
`left_thumb_metacarpal_fused` and its mirror, 5.47 at both thighs -- so the
spring fix could not be told apart from a pose change nobody asked for. Built
again with her environment exactly as recorded:

    MonoBehaviour 22 -> 41, textures same, materials same, meshes 1 -> 1,
    bones moved: 0 of 90

That is the build that shipped. A fix whose diff contains one thing is worth a
second build, particularly when the first one's own script comment claimed
"ONE change" while making two.

#### Her skirt is a different problem and is not fixed

The hair-rig interface finds a group by **material**, and she is one mesh with
one material, `tsx_bot205`, covering her whole body. There is no pattern that
isolates her skirt, and no skirt bones to spring either -- her 70-bone rig is
`Bip01 *` plus the eight `HairSpring` bones and nothing else. So the twintails
swing and the skirt does not. Note this is a different fault from "her dress
does not move with her", which was undriven WEIGHT above the humanoid root and
was fixed on 2026-11-11; the skirt follows her hips correctly and simply has
nothing to make it swing.

### A build log carries the VRM add-on's own guesses, and they are not ours

The same session nearly reported a catastrophe. Gadget's build log contains:

```
[VRM Add-on:WARNING] Generated mappings:
  hips: root
  leftHand: DEF-shin.L
  rightHand: DEF-shin.R
  leftUpperLeg: torso
```

Hands mapped to shins, a leg mapped to a control bone. That is the ADD-ON's
structure search guessing at a rig it does not understand, printed at WARNING
level in the middle of our own output. It has nothing to do with the humanoid
this build assigns -- and grepping the log for `leftHand:` finds it rather than
ours.

`vrmhuman.py <file.vrm>` reads the humanoid out of the FILE, which is the only
thing that settles it. Gadget's is correct: 50 bones, `leftHand` on `DEF-hand.L`,
every limb where it belongs.

The general rule, and it has now cost time twice in one day: **a log line is
evidence about whoever printed it.** Ours are indented two spaces and say what
was done; the add-on's carry its own prefix. When a grep returns something
shocking, read the ten lines above it before believing it.

### Framing a render on a vertex GROUP, and three ways that renders nothing

`facecam.py` grew what a hand needs: `group:DEF-hand.L` frames on everything
weighted to matching vertex groups, an elevation argument, and `FACECAM_REST=1`
to clear the pose first. Each exists because its absence produced an empty or a
misleading frame:

- **A hand is not a material**, so it cannot be framed the way the teeth were.
  Framing on the BONE instead fails on exactly the files worth comparing: a
  Rigify source carries a metarig as well as a rig, `render_closeup.py` picks the
  metarig, the metarig is not posed, and the camera is aimed at empty space.
- **Vertex groups live on the base mesh and the character may be POSED.** Taking
  the group's indices and then the base COORDINATES aims the camera where the
  hand would be at rest. On a posed source that is empty space, and a blank frame
  looks exactly like "the hand is missing". Read indices from the base, positions
  from the evaluated mesh.
- **A T-posed character holds its palms down**, so a camera level with the hand
  sees it edge-on and the fingers read as thin spikes whatever shape they are.
  That alone made the build's hand look deformed beside a source photographed
  from above.

Still open: `FACECAM_REST=1` renders an empty frame on this source while the
probe that places the camera reports a sensible centre. Clearing `matrix_basis`
on a constraint-driven rig does not put the geometry where the depsgraph is asked
for it one line later. Not chased, and NOT to be read as a finding about the
model until it is.

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

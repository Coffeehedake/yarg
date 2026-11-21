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

## Where it stands — open items, last reconciled 2026-11-20 (Jessica Rabbit closed)

The runlist further down is the full history. This is only what is OPEN, so a
session picking this up does not have to reconstruct it.

> **The date on this heading is the last time the list was CHECKED, not the last
> time anything was done.** It read `2026-11-17` until 2026-11-20 while already
> carrying three 11-18 outcomes (Aiko installed, Miku resolved, Jessica Rabbit
> re-opened), so a reader could date the whole section three days earlier than
> its newest row and treat a closed item as open. On 2026-11-20 that is exactly
> what happened from the other end: a handoff three generations stale sent work
> at the podium render and Prix, both finished on 11-16. **Re-date this heading
> whenever you touch a row, even to close one.**

**The podium render is FIXED, 2026-11-16: drop `-nographics`.** It had been
writing **identical 12,477-byte blank frames** for every character, good and
broken alike. The cause was not the shot code and not the subject: with
`-nographics` Unity has no graphics device, so `cam.Render()` draws nothing
and `ReadPixels` hands back the clear colour — a uniform grey frame that
looks like a render of an empty scene. Run as `-batchmode` WITHOUT
`-nographics` the same command writes a real 171,663-byte shot.

The `VRMCharacter init skipped: NullReferenceException` logged alongside it is
a RED HERRING: it is caught, the code continues, and it appears on characters
that render perfectly.

This is the project's own standard for accepting a change, and it had been
unavailable. **Every Unity call in these notes that RENDERS must omit
`-nographics`**; the ones that only load, measure or export should keep it,
since it is faster and opens no window. Hide the window with
`Win32_ProcessStartup.ShowWindow = 0` either way — the WMI launch is still
needed for the job-object breakaway.

| open | state |
|---|---|
| ~~**Prix**~~ | **DONE 2026-11-16.** All four reported faults closed, three confirmed by eye on the podium; chest chains restored (5c/15j). What remains is a **31.9 mm arm depth asymmetry** that is her authored pose and hair that reads auburn under the podium light — neither reported, neither a fault |
| ~~**The Mandalorian**~~ | **DONE — STRAIGHTENED AND INSTALLED 2026-11-17.** Reported as armour off-centre; it was a **3.3° spine lean**, not the "two half-skeletons" this file first recorded, and the lean was inherited. Skeleton **37.2 → 6.0 mm** read back off the installed file with Spartan at 0.0 as the control, geometry untouched (armour planes −8.00→−7.70, −8.60→−8.80), load test identical, renders indistinguishable. It does not SHOW — the fault was the rig, not the look. Baking the body with the bones, the other sense of "straighten", throws his helmet 50 mm off; that build is kept beside the installed one in `character-backups/mando-straighten-2026-11-17/` |
| ~~**Jessica Rabbit**~~ | **CLOSED 2026-11-20 — leave her, and this time the cost of every alternative is measured.** Re-opened 2026-11-18 on the interior-fault probe ranking her worst; that result was separately downgraded, but the 92.4 mm **was real** — her whole left shoe, measured on geometry against two controls at 0.0 mm. Three corrections exist and each costs more than the fault: patching the bundle is **impossible** (`Hips` is humanoid-mapped, the Animator retargets from the Avatar); **dropping the static pose** fixes the shoe to 0.0 mm and stretches her skirt **30.35×** across the widening gap between her legs, besides losing the stance that is the character; **levelling the hips** (`straighten_spine.py --level`, new) fixes it to 0.0 mm with no streaks and swings her skirt from **+24 mm** of drift to **−155 mm**, because her skirt is weighted to `spine`, which IS her Hips. That last one is the 2026-11-16 sentence in millimetres: *the buried shoe for a twisted pelvis*. **DO NOT RE-OPEN** without a re-modelled skirt; the measurements are recorded so nobody repeats the three attempts. See "ANSWERED, 2026-11-20" |
| ~~**Kronk**~~ | **DONE — STRAIGHTENED AND INSTALLED 2026-11-17.** Not a half-body step: a **57.0 mm lean**, and unlike The Mandalorian his GEOMETRY leans with it (37.2 mm of it), because his source is `Kronk_Doing_the_Hokey_Pokey.usdz` and the T-pose step squares the limbs but never touches the spine. Rebuilt from source, straightened BAKED and re-centred: skeleton **57.0 → 13.4 mm**, geometry **37.2 → 9.6 mm**, and the podium render is visibly straighter. Never reported by anyone |
| ~~**Aiko**~~ | **DONE — INSTALLED 2026-11-18.** Not a lean but a **YAW**; the sheet over her face was an **alphaMode draw-order artefact**, a builder regression (e921bf62) against her 2026-11-07 intermediate, NOT a recipe gap. Installed `aiko-RECIPE-OPAQUE-v2-colliders`: **yaw −29.95° → +0.03°** (spread 0.15), height 1.700 m, **10 colliders, 0 of 4 chains unguarded** (was 9), face clear in all 10 frames. Backup `character-backups/aiko-2026-11-18/`. A latent chain inversion remains — real in the file, invisible in this idle |
| ~~**Limb capsules**~~ | **DONE — SWEPT AND INSTALLED 2026-11-17**, and the scope was far smaller than this line implied: of 65 bundles **35 have no spring chains at all**, so their capsules are inert, and 9 more were already right. **194 resizes across 21 characters**, median +11.7 mm; **20 installed, Alcina held** because p90 on her legs is her gown. Still run: 0 worse, 1 better (Inforder Trogen 33.15 → 8.34 mm), 20 unchanged. Load test identical on every pair. (That run measures instantiate-pose to settled-pose, NOT ejection — see "Miku's 1748 mm") |
| **Alcina Dimitrescu** | **HELD out of the limb sweep on purpose**, not a regression: p90 on her legs is her GOWN (thigh 0.111 → 0.207, shin 0.091 → 0.199), and for her the median is the closer approximation of a leg. Her still run is 0.10 mm either way, so nothing is lost. Re-open only with a flesh-only percentile |
| ~~**Hatsune Miku (Retry Now ver.)**~~ | **DONE — NOTHING IS WRONG WITH HER, checked twice.** (1) The 283 mm is a modest, correct settle, not an ejection — rendered rest and sprung with  as control; her rest pose is already tidy, which is why she settles 283 where Miku settles 1748. (2) Re-opened 2026-11-18 because she carries **23 of 23 MToon materials** and I had claimed this path ignores MToon — **that claim was WRONG and she disproved it**: she renders flat and cel-shaded against our Miku’s gradient, and 7 of her materials carry real shade colours (hair delta 1.000). MToon draws her as authored. She also has 5 joints inside their own colliders with no visible damage. Nothing installed, nothing changed |
| ~~**Arbiter**~~ | **CLEARED for this project 2026-11-20.** 12 handoffs remain open estate-wide and **none of them is yarg's** — the chain RHBDK4 → UR3U3Z → UJFAX7 → LR4GZ6 is all claimed. Each link was superseded by the next, so three of them were live invitations into work that was already finished, and on 2026-11-20 one of them was acted on: `UR3U3Z` was picked up and its `next_action` ("fix the podium render first, then Prix") had been done on 11-16. **A superseded handoff still reads like an instruction** — the hub's own `warning` field is the only thing that says otherwise, so pull the chain to its end before working from one |

**Settled on 2026-11-17**, each with its own section below. Two characters
STRAIGHTENED and installed, and they are the two halves of one lesson: The
Mandalorian's bones leaned inside a plumb body, so his correction must NOT bake
the mesh; Kronk's body leans with his bones, so his must. The wrong choice on
Mando throws his helmet 50 mm off, and `straighten_spine.py` therefore refuses
to choose. The **limb-capsule sweep** closed at 194 resizes across 20
characters, with 35 of the 65 turning out to have no spring chains at all and
Alcina held on purpose.

**Four instruments were wrong and all four are fixed**, which is most of what
the day actually cost:

* `half_body_check_installed.py` cannot tell a step from a lean, and had
  reported one on two characters who have neither — `plumb_check_installed.py`
  is the replacement;
* `patch_springs.py` reported a MISSING FILE as "has no spring chains";
* `YargSpringProbe -still` blew a 14 m/s wind while printing that any
  displacement was a collider ejecting a joint;
* and that same still run does not measure ejection at all — it measures
  instantiate-pose to settled-pose, which is why Miku's 1748 mm is her springs
  working rather than a fault.

**Settled on 2026-11-16**, each with its own section below: the clearance
guard cleared a joint's CENTRE rather than its sphere, in two separate copies
of the rule — fixed in both, and `--reclear` applied to the 14 characters of
ours, taking Power Girl and Jinx from 78 and 76 mm of permanently displaced
hair to under 1 mm. Chest chains with no collider group turned out to be
**deliberate**, and five characters patched on that mistaken basis were
reverted. Four new checks were added and swept across all 65:
`joint_inside_check_installed.py`, `pair_offset_check_installed.py`,
`half_body_check_installed.py` and `centreline_check_installed.py`. Between
them they closed the long-standing "seven characters whose yaw lines disagree"
item, naming the limb and the millimetres for each.

**Also settled 2026-11-16, from the source Jay supplied for Prix** — four
builder defects, each found by rebuilding her and each general rather than
hers: the `mixamo` preset never stripped a name PREFIX, so her head mapped to
her neck and both left leg joints to her buttock bones; enabling MToon threw
away the base texture, because MToon's own base-colour slot starts empty;
the base colour FACTOR was forced to white, which ships a greyscale map grey;
and a character could sit off its own root with nothing to notice. Plus
`glb_bake_joint_scale.py`, a new tool: Blender's glTF importer cannot hold a
joint scale on a rest bone and drops it silently, so the scale is baked into
the file instead — verified to 1.388e-16 m.

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
- PowerShell's `Start-Process -ArgumentList` with an **array** joins on spaces **without quoting**.
  Build one argument string with embedded quotes, or bind parameters normally.

  **THE MECHANISM IS THE WARNING; THE SYMPTOM IS NOT.** This entry used to say only "a project
  path containing a space arrives as several arguments and Unity exits 1 with
  `Couldn't set project path`" -- and on 2026-11-18 a session that had READ this line walked
  straight into it anyway, because its spaces were in a 65-entry CHARACTER LIST
  (`"Adachi Rei.yargchar"`), not in a project path. The list split and `Rei.yargchar|Adachi` was
  bound to `-Step`, a double. Nothing about "project path" matched what it was doing, so the
  warning did not fire in its head.

  ANY argument with a space is affected, and the symptom depends entirely on where the stray
  token lands. It was cheap that time only because `-Step` is a **double** and the type
  conversion failed loudly with no Unity log at all. **Had the stray token landed in a string
  parameter, the run would have completed and produced a tidy wrong answer.**

  Write the mechanism into the warning. A hazard indexed by its example is invisible to anyone
  meeting it in a different costume.

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
| Jessica Rabbit | ~~dress static while the body moves~~ **SUPERSEDED — FIXED 2026-11-16, and the fix is INSTALLED** (verified in the shipped bundle 2026-11-18: her 24,035-vert bodice is on 9 bones including breast.L and breast.R). Sequin texture on her skin still stands | the rigger took one group per build, so her hair and her dress could not both be rigged. `rskin` had already been given its own map |
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

## The runlist

Everything reported, and what became of it. **This table had no header row and
no blank line before it until 2026-11-16, so every row of it rendered as
literal pipe-separated text rather than a table** -- which is why it reads as
a wall in any Markdown viewer. The rows themselves were always fine.

| character | what was reported | what it is |
|---|---|---|
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
| The Rock | arms are squiggly | **FIXED 2026-11-16 BY A REBUILD.** His upper arm is **61% over** the population norm and his forearm 13% under — upper/forearm ratio **2.37** where his own source `Rock.fbx` has **0.96**. Every existing check passes him because nothing is BENT (elbow 0.0/0.0) and nothing is DISPLACED; the segments are the wrong LENGTHS, which nothing measured. Reproduced exactly: `fit_joints.py` places a joint at the midpoint of two flesh centroids, and his upper-arm group keeps dominant weight 209 mm past his elbow, so it lands at 70% of the arm where it belongs at 49% — the shipped bundle is 70.3%. ~~His legs go the same way~~ and ~~three fixes tried and all three measured wrong~~ — **all of that was an artefact of a broken staging** that applied the armature's transform and its 21 parented meshes' together, counting it twice and reading a 1.9638 m model as 3.2915 m. The real cause is `scale_rig.py` sizing the skeleton from `Object.bound_box`, which is a CACHE and goes stale (and survives `evaluated_get(depsgraph)`): it scaled him by **0.6668** where his recipe records **0.3978**, and the midpoint rule then landed the elbow at 69.5% of a wrongly scaled arm against the shipped 70.3%. `fit_joints.py` was innocent — on a correctly scaled rig it puts the elbow at 50.7% against the rig's own 48.9%. scale_rig now reads vertices. Rebuilt: upper arm 0.344 → **0.176** (human 0.186), reach 1.272 → **0.932** (documented 0.938). See "The Rock's arms, 2026-11-16" |
| Spartan Mark V | asymmetric right leg | **FIXED 2026-11-15.** His whole right leg hung off one bad `thigh.R` offset, sitting **29.7 mm clear of a hip socket his left leg sits 4.7 mm inside** — and after the fix it reads 4.6 mm, his left leg's own figure. (An earlier version of this row said "92.12 mm from the mirror of his `thigh.L`"; that number came from a tool that was withdrawn the same day for comparing local offsets under a rotated shared parent. The fault was real, the number was not — the evidence is the socket gap, his provably symmetric source, and his lower torso's self-mirror error going to 0.00 mm when the bone moved.) No ANGLE check could see it: the leg moved rigidly, so his knee and ankle match his left side to four decimals. His source `.blend` is an exact mirror in both bones and flesh, and a rebuild from it today is 0.000 mm out, so this came from a build that no longer exists. Patched in the four structures that hold that offset. See "Spartan Mark V's right leg, 2026-11-15" — **but see the correction below: the patch is correct and the GAME DISCARDS IT** |
| Jessica Rabbit | dress clips through the body, not rigged to it, and the sprung parts of the body and the dress move separately | **DRESS FIXED 2026-11-16; a SEPARATE rig fault found the same day and NOT fixed.** Her whole right leg sits **92.4 mm higher** than her left and her whole right arm 29.0 mm higher and 74.1 mm further back, while her shoulder bones are symmetric to a tenth of a millimetre and each limb's flesh is symmetric about its own bone to 0.1 mm — so whole limbs are displaced, correctly skinned to bones in the wrong place. Her 92.4 mm is the worst limb-height fault on the roster, double the next. It is identical in all four of her snapshots that day, so it predates every patch and our builder reproduces it faithfully from her source. Settled: not a pose — her left shoe hangs 67 mm below her own skirt hem and 92 mm below the plane her right foot stands on, where three symmetric characters put both feet at the identical height. Traced to her Hips bone's X axis sitting **25.71° out of horizontal**, inherited from a source posed leaning on a microphone; her thighs are mirrored to seven decimal places and entirely innocent. **DECIDED: leave her**, because every available correction trades the buried shoe for a twisted pelvis. See "Jessica Rabbit's right leg is 92 mm higher than her left, 2026-11-16". Dress note follows: **FIXED 2026-11-16, both halves.** Her dress is two meshes and **every vertex of both was weighted to ONE bone** — `spine`, her humanoid hips — at one influence: bodice 24,035 verts, skirt 13,275. It followed her hips and nothing else, so the one part of her that moved (`breast.L`/`breast.R`) swung inside cloth that did not. *(Those two chains having no collider group was separately called a fault and "fixed" on five characters; that was wrong -- the builder skips chest chains deliberately -- and all five were reverted.)* Shaken in the spring runtime the installed character's only moving bones were the two breast tips at 90.6 mm. Rebuilt from her documented recipe: skirt now **17 bones, 1-3 influences**, chains 2 → **10**, colliders 2 (referenced by none) → **10 (referenced by 8 of 10)**, skirt peak deflection **1024 mm**; clips, meshes, textures and materials all identical. ~~The bodice is still 24,035 verts on `spine`~~ — **also fixed**, by a new step in `build_vrm.py` that re-weights a mesh once the build has CARRIED it into place: the bodice is now on **9 bones** including `breast.L`/`breast.R`, so the cloth over her chest deforms with the sprung chest instead of being a shell it swings through, and the skirt on **21** including both thighs. Geometry moved 0.0000 mm. The step is gated on a mesh this script auto-weighted itself landing ≥90% on a bone ABOVE the humanoid root, and the control proves it inert: Spartan Mark V rebuilt before and after is **byte-identical**, md5 `b68ce9e4…`. See "Jessica Rabbit's dress, 2026-11-16" |
| Aiko | *(not reported — found by the yaw sweep)* | **MEASURED 2026-11-16, NOT FIXED, nothing installed.** She stands **29.95° off**, the worst on the roster. Today's builder detects and corrects it unprompted (`facing: feet point (-0.5, -0.87, 0.0), 30 deg off forward`) and the rebuild reads **+0.03°, spread 0.15** — but it puts her hair as a flat sheet over her face, with AND without the hair rigger, -- **CORRECTED 2026-11-18: the recipe IS right; the BUILDER changed under it (e921bf62, 2026-11-09) and her 2026-11-07 intermediate predates it. The sheet is an alphaMode draw-order artefact, now fixed and rendered.**. The turn has never been reported and the hair would be, so she keeps the 30°. See "Aiko, 2026-11-16" |
| Spartan Mark V | ~~asymmetric right leg~~ **leg still sticking out at the right hip** | **FIXED 2026-11-16 BY A REBUILD, and the earlier patch provably did nothing in game.** Two separate findings. (1) The patch IS in the file and IS right — his hip offsets read L 161.8 mm / R 161.8 mm at instantiate, against 161.8 / 244.5 before. (2) **Unity's humanoid Animator re-poses the skeleton from the AVATAR, and the four rest structures are not what the Avatar retargets from.** After `Animator.Rebind()` the patched bundle reads L 161.8 / R **244.5** — byte-for-byte the unpatched figure. (3) Separately, the whole character is **turned 20.00°**: hips, shoulders, knees and feet all agree to two decimals, because his source is a perfect mirror about a plane 20° off the x axis and nothing straightens him. His left hip faces the camera, which is the hip reported. **No bundle patch can fix either** — the Avatar has to be regenerated, so he was REBUILT and installed. Today's `build_vrm.py` already carries a facing stage that detects and corrects the 20° itself, so his plain recorded recipe was enough and now reproduces him. Verified through the Animator, which is where the patch failed: hips L/R 143.3 / 143.3 mm after `Rebind()` against 161.8 / 244.5, and post-`Rebind` yaw 4.56° / −7.96° against Doom Slayer's control 4.20° / −7.89°. Both hips were wrong in the old build, not only the right one. See "Spartan Mark V, 2026-11-16: the Animator does not read what we patch" |
| Killer Clown | hair clipping through her hat | **FIXED 2026-11-15, and the hat was the smaller half of it.** Her lashes, brows and hair are one material, and the hair rigger's material fallback takes every mesh that shares the hair material — so her **eyebrows are 146 of 146 vertices on hair spring chains** and her **eyelashes 2,357 of 4,640**, swinging on hair physics across her face. They are 2,503 of the 2,890 vertices those four chains move; the hair itself is 387. Of those 387, **371 sit inside her jester hat**, up to 51.8 mm deep, while 95% of the hair the rigger left rigid is outside it — the physics went on the hair nobody can see and the visible hair stayed rigid. Both are selection faults, so no parameter fixes either: the four chains were removed. See "Killer Clown's hat, 2026-11-15" |
| Miku | necktie sticking straight out | **FIXED 2026-11-15, and it is not ours.** Her `Bip01 Spine1` → `Bone01` → `Bone02` → `Bone03` tie chain runs **71° off vertical** — 89 mm of drop for 255 mm of reach, geometry out to z +0.545 against a chest surface at z +0.08. Her source `Miku.fbx` has the same chain at 69.1° and 72.4°, the same story as her hair being "splayed outward in the ORIGINAL download": an MMD rig whose tie was meant to be settled by rigid-body physics a VRM export does not carry. Re-aimed with `patch_bone_aim.py` to 15° from vertical — straight down puts 14 of its 20 vertices inside her chest. See "Miku's necktie, 2026-11-15" |
| Miku | twintails only move where they were repaired; the tie could be sprung too | ~~FIXED 2026-11-15 (evening)~~ — **RE-REPORTED UNCHANGED, FIXED AGAIN 2026-11-16.** Two faults. (1) `patch_add_springs.py` set each new joint's `m_GameObject` and never added it to that GameObject's `m_Component`, so **21 of 29 joints were orphans** — and both the tool's own read-back and the Unity load test missed it because they follow the Springs array's pointers, the one direction the patch had written. (2) `Bone06` and its mirror, **158 vertices** and a third of the twintails, were left rigid on an unmeasured assumption; the project's own `_trim_anchor` rule clears them (0.133 m against 0.774 m for the rest of the chain), so they are now sprung. **462 of 462 twintail vertices are on a chain**, against 304 and 38. **VERIFIED IN THE SPRING RUNTIME** with `YargSpringProbe.cs`: every twintail bone now peaks between 143 and 422 mm under a linear shake, the two sides within 10%, where `Bone07` and `Bone11` read **0.001 mm** yesterday. The necktie swings 161 and 359 mm. **The orphans were NOT the cause** — yesterday's build peaks at 706 mm with all 21 orphaned, because Unity attaches them at instantiate; what was rigid was the TOP (the crown plus the two chain-root pivots, ~187 vertices), which is exactly what "only the middle" described. See "Miku's twintails, 2026-11-16". Original note follows: Both right. Her two `HairSpring_*` chains run on eight bones an earlier hair-rigger run INVENTED, which dominate **38** vertices; her own twintail bones `Bone06`..`Bone15` and their `(mirrored)` twins dominate **462** and were on no chain, as were the three tie bones. Nothing found it because every rigger here selects by bone NAME and her rig has no bone whose name contains hair, tail, bang or tie — while `HairSpring_1_0` does. `patch_add_springs.py` put 7 new chains on her own bones: **324 vertices now move against 38**. `Bone06` stays rigid on purpose (it is the bun, 158 vertices, at the crown). The tie chain is given NO collider group — all three of its bones start 44.4/30.5/7.4 mm INSIDE the torso capsule, and attaching it would have thrown the knot forward and undone that morning's re-aim. See "Miku's twintails and necktie, 2026-11-15 (evening)" |
| The Mandalorian | armour is not centred on his chest | **RE-MEASURED 2026-11-16 and the first answer was WRONG — see "The Mandalorian is NOT two half-skeletons".** He has no step: his spine LEANS 37.2 mm from feet to head, about 3.3°, every gap 4.5–11.2 mm, and `plumb_check_installed.py` reads 0.0 at all eleven heights for the Spartan control. The lean is INHERITED — 25 islands matched between `Mando_for_mixamo.fbx` and the bundle fit a line to 2.06 mm median residual and the chest plate's residual is +4.6 mm, so our pipeline moved nothing. His armour is coherent with itself: helmet plane −8.6 mm, chest plate plane −8.0 mm, two independent fits agreeing to 0.6 mm. A fix means straightening his spine (a deformation, and `VRM_STANDUP`'s 25° gate exists so it does NOT fire for 3.3°) and it cannot be patched into the bundle because every spine bone is a mapped humanoid bone — and his Mixamo rig is not on this machine. Put to Jay. ~~Original diagnosis follows and is superseded:~~ It is not the armour: his skeleton is **two half-skeletons 37.2 mm apart**. Every lower pair (hips, knees, feet) centres at -18.5 mm and every upper pair (shoulders, elbows, hands) at +18.7 mm, to a tenth of a millimetre, with no gradient between them, while his limb segments are near perfect (arms 0.2453/0.2456 vs 0.2453/0.2457). His source glTF has two collapsed skeletons and he was re-rigged through Mixamo, which is where a step like that comes from. Nothing shows at rest — raw and skinned vertices agree to four decimals — so the bones are simply in the wrong place INSIDE the geometry, and his chest pivots about an axis 18.7 mm off the centreline his legs define. The Animator is NOT the mechanism: Spartan Mark V, square in his own bundle, also goes 0.00/0.00 to 4.56/-7.96 after `Rebind()`, so that shift is the controller's, not his. Fixing it means moving bones while compensating their bind poses so the rest pose does not move, and that needs his mesh's true centreline first. See "The Mandalorian is two half-skeletons, 2026-11-16". Original note follows: **reported 2026-11-16, not yet measured.** Two existing measurements probably bear on it and should be read before anything is rebuilt. His body-yaw lines **disagree** (+2.50 deg mean, spread **11.10**), which `body_yaw_check_installed.py` reads as a displaced part rather than a turned body — he is one of seven on that list. And the edge-length ratio sweep puts his worst stretched edge at **234 mm**, the largest on the roster by a wide margin (Peacemaker's is 27 mm). His source is a glTF whose **both skeletons are collapsed**, so he was re-rigged through Mixamo; a chest plate that is a separate island riding one bone, or weighted to a bone the re-rig moved, would produce exactly this. Check first whether the armour is its own mesh/island and which bones dominate it — if it is one rigid island on one bone, this is the Joker's-pistol and Judy's-belt shape, not a weighting fault |
| Prix | no hair, no pupils, eyelashes have no alpha — "a mess, she needs a lot of work" | **REBUILT AND INSTALLED 2026-11-16**, md5 `8ee48d5`, backup `Prix.prerebuild-2026-11-16.yargchar` (sha256 `0124c722d881`). She had **no source** until Jay supplied `prix.glb`; she now has one and a recipe. **HAIR FIXED:** 10,741 verts go from a 14 x 22 x 13 mm pellet at her ankles to **372.6 x 465.6 x 423.3 mm** spanning her crown to her chest, with three driven physics chains, BLEND, textured, and near-black (0.0782, 0.0182, 0.0182) instead of white. **EYEBROWS FIXED:** back as their own 834-vert MASK mesh instead of merged into the body. **LENS:** excluded — its map is 100% clear in the source, so it was never meant to draw, which retires the 2026-11-12 alpha-0.08 hand-fix. **Centred** to 6.6 mm from 63.5. One import defect explained all of it: every node scale was dropped (`hairAll` 22.085905 -> 1.0). **STILL OPEN:** her two `BreastSpring` chains (5 -> 3; her source has no chest bones, so `patch_add_springs.py` must restore them), a 31.9 mm arm depth asymmetry that is her authored pose, and whether `eyes1` alone gives her the blue irises of her source render — **not established, needs a render**. See "Prix: her hair is at her ankles" |
| Skibidi Toilet | is a man, with no toilet | the exclude that drops the toilet shell (it swamped the model) drops the character's defining feature and leaves the body that was inside it |

### Prix: her hair is at her ankles, 2026-11-16 (first pass)

Four faults reported at once -- no hair, no pupils, eyelashes with no alpha,
"a mess". **She has no source on this machine**, which her recipe row already
records, so every fix here is an edit to the built bundle and no rebuild is
available.

#### The hair, which is the big one

`Mesh.009` is **10,741 vertices** on bones called `hairAll`, `headUpper` and
`backHair_03`. It sits in a box **14 x 22 x 13 mm at y 0.135** -- ankle height
-- while her head bone is at y 1.5496. Her hair is a crushed pellet by her
feet, which is exactly "no hair".

The arithmetic is one line:

```
FemaleBody_Head  world rotation (w -0.0, x -0.0, y 0.0, z 1.0)   <- 180 deg about Z
hairAll          local position (0.0000, +1.4111, +0.0259)
                 world position (0.0000, +0.1385, -0.0034)
```

Her head bone is rotated **180 degrees about Z**, so `hairAll`'s local **+1.411
m** becomes **-1.411 m** in world: 1.5496 - 1.4111 = 0.1385, the measured
value. The meshes bound to the head are unaffected because their bind poses
compensate the rotation; a CHILD BONE's offset is not compensated, and
`hairAll` was authored as though the head were upright.

**And it is tiny as well as displaced, with no scale factor anywhere to
explain it.** Every bone from `FemaleBody_Head` down through `hairAll` to
`LefthairA_02` has local scale exactly `(1.000 1.000 1.000)` and world scale
1.0000. The rig is simply built small:

| | |
|---|---|
| hair segment `LefthairA_00` -> `_01` | **3.38 mm** |
| `_01` -> `_02` | 3.27 mm |
| `_02` -> `_03` | 3.81 mm |
| body segment `FemaleBody_Neck` -> `FemaleBody_Head` | **101.37 mm** |

**There is a correctly-sized reference in the same file.** `Mesh.006`, 847
verts, wears the duplicate of the same hair material and sits properly on her
head at **148 x 156 x 173 mm**. Against `Mesh.009`'s 14 mm width that puts the
scale error at roughly **10x** -- measured against her own other hair piece
rather than guessed.

`hairAll` is **not a humanoid-mapped bone**, which matters: the Animator
retargets mapped bones from the Avatar and discards rest-pose edits to them
(Master Chief, Jessica), but leaves unmapped bones alone (Miku's `Bone01`). So
unlike Jessica's hips, this one **can** be fixed in the installed bundle.

#### The hair would still be wrong once moved

Both hair materials are **opaque over a texture that is 58.7% clear**:

```
Prix_0  opaque  soft  clear=0.587 solid=0.125 mid=0.287  UNUSED  CN_F_HAIR_110_hair
Prix_5  opaque  soft  clear=0.587 solid=0.125 mid=0.287  UNUSED  ..._DUPLICATED__2
```

They are the only two materials of the nine with a meaningful alpha channel.
Hair cards rendered opaque are solid rectangles, so moving the mesh without
also fixing the mode would trade no hair for a block of hair.

#### The pupils are NOT the lens, and that fix is still intact

Her recipe records a fix applied 2026-11-12: a lens over `L_iris`/`R_iris`
that *"shipped OPAQUE, wearing her SKIN atlas, parked in front of perfect blue
eyes"*, set to alpha 0.08. **It is still there and still correct** --
`Prix_7`, render queue **3000**, `_Color a=0.080`, `_ALPHAPREMULTIPLY_ON`, on
`Mesh.003` and `Mesh.005`. So the re-reported "no pupils" is something else,
and **the cause is not yet found**. Her irises are `Mesh.002`/`Mesh.004` on
`Prix_6` with the proper `eyes_lambert2SG_BaseColor`; its emissive map is
assigned but `_EMISSION` is not among its keywords, so a blown-out emissive is
ruled out too.

#### The eyelashes have no mesh of their own

There is no lash mesh in the file. The ten meshes are the body (22,693), the
underwear (2,684), two hair (10,741 and 847), four eye parts (402-422 each),
and two untextured grey meshes at mouth height -- `Mesh` (11,220 verts, 100%
on `FemaleBody_Jaw_02`) and `Mesh.001` (12,240, 100% on `FemaleBody_Head`),
both on materials with **no texture at all** and `_Color (0.735 0.735 0.735)`.
Whatever those are, they are not lashes at eye height. **Where her lashes
actually live is unresolved**, and the only materials carrying a real alpha
channel are the two hair ones.

#### Confirmed by eye, from a render that already existed

`scratchpad/prix/full.png`, made 2026-11-12 during the lens work, shows it
without any new measurement: she is **completely bald**, her eyes read blank,
and there is a **small white speck between her ankles** -- the hair pellet,
visible in the render, exactly where the arithmetic puts it.

#### The scale factor CANNOT be derived from the file

The hair has to be scaled as well as moved, and the factor has no answer in
the bundle. Her raw mesh data really is 14 x 22 x 13 mm -- RAW and SKINNED
extents agree exactly on all three meshes checked, so nothing is being shrunk
by a bind pose. Four independent ways of fitting it disagree:

| basis | factor |
|---|---|
| hair box against the scalp box (183.4 / 14.0 etc.) | 8.2 - 15.4 per axis |
| hair box against her OTHER, correctly-placed hair piece | 7.0 - 12.9 per axis |
| per-bone sub-boxes against the scalp | 13 - 69 |
| cap vertices fitted to the scalp ellipsoid, median r = 1 | ~28.6 |

They disagree because a hair mesh is not head-shaped: `Mesh.009`'s aspect is
1 : 1.6 : 0.96 against the scalp's 1 : 1.01 : 1.12, so no pair of boxes has a
common quantity to match. The ellipsoid fit is the only principled one of the
four and it lands at 28.6, which would make the hair **400 mm wide** against a
183 mm head -- so it is wrong too, and its own r-distribution says why: the
cap's vertices sit 3.2 mm from their centroid where the scalp's sit 92 mm.

**Picking one of these by eye is exactly the move this file keeps recording as
a mistake**, so the hair is not being moved until there is a picture to fit
against.

#### And the podium render is broken for EVERYBODY

Which is the actual blocker, and it is not about Prix. Run against Jinx and
Prix together, the tool logs `VRMCharacter init skipped:
NullReferenceException` for **both** and writes two **identical 12,477-byte**
blank frames. A known-good character renders exactly as blank as she does, so
this is the shot path, not the subject -- and it means no visual verification
of anything is available on this project right now. The 2026-11-12 renders
came from a different route (flat grey, T-pose, not the podium).

#### SOLVED by the source: the importer DROPPED EVERY NODE SCALE

Jay supplied `prix.glb` (53,038,136 bytes, sha256 `7b3d7836af17a1e4`,
Sketchfab-16.56.0, 159 nodes / 13 meshes / 9 materials / 1 skin of 130 joints)
and a `.usdz`. The GLB answers everything, and the scale was never a thing to
fit -- **it is written in the file**:

| node | scale in the GLB | scale in the bundle | |
|---|---|---|---|
| `hairAll` | **22.085905** | 1.000000 | DROPPED |
| `R_eye`, `L_eye` | 0.849676 | 1.000000 | DROPPED |
| `R_iris`, `L_iris` | 0.849676 | 1.000000 | DROPPED |
| `HairCalp` | 1.011477 | 1.000000 | DROPPED |

**All six.** One import defect accounts for the lot, and it predicts each
symptom rather than being fitted to them:

* The hair strands are **22.0859x** too small — not 7, not 10.6, not the 28.6
  the ellipsoid fit produced. Four attempts to derive this from geometry were
  four attempts to re-measure a number the source states.
* `HairCalp` lost only **1.1%**, which is why the cap alone looks correctly
  placed and she reads as having a painted-on skullcap rather than nothing.
* Both eye meshes and both iris meshes grew **17.7%** inside a socket modelled
  for the smaller ones — which is what a blank white almond with no iris looks
  like from the front.

**The material modes were flattened too**, and the GLB names the right ones:

| material | GLB | installed |
|---|---|---|
| `Hair` | **BLEND** | OPAQUE — the washed-out grey cap |
| `aiStandardSurface4` (the iris lens) | **MASK** | queue 3000, alpha 0.08, a hand-fix approximating a cutout |
| `cejas1` (eyebrows) | **MASK** | gone — see below |

**And the eyebrows were MERGED INTO THE BODY.** The GLB has them as their own
834-vertex mesh on `cejas1`; the bundle's body mesh `Mesh.007` is **22,693**
verts, and 21,859 + 834 = 22,693 exactly. They now wear the body's opaque skin
material instead of their own cut-out one, which is why her brows are missing.

**`Mesh` and `Mesh.001` are her TEETH, not her eyelashes.** Correcting an
earlier reading in this section: the GLB has `Dteeths_phong2_0` + `Dteeths_phong1_0`
= 5,904 + 5,316 = **11,220**, which is `Mesh` exactly, on her jaw bone; `Uteeths`
is the pair behind `Mesh.001`. `phong1` and `phong2` have **no base texture in
the source either**, so the flat grey 0.735 is correct for teeth and is not a
fault. She appears to have **no separate eyelash geometry at all** — there is no
lash material among the nine.

#### The rebuild, 2026-11-16: a builder bug found, the hair not yet fixed

**It is Blender's glTF importer that drops the scale, and it is worse than a
scale.** Importing `prix.glb` and measuring before any build step runs, the
hair mesh comes in at **3.9 x 3.8 x 6.3 mm sitting at the origin**, while the
head bone is at z 0.3977. A Blender REST bone has head, tail and roll and no
scale at all, so a glTF joint carrying 22.0859 cannot be represented directly
— and this import loses the placement with it. **A straight rebuild therefore
reproduces the fault exactly**, which it did: the rebuilt `.vrm`'s hair mesh
measures **14.0 x 22.4 x 13.4 mm**, the same three numbers as the installed
bundle.

**But the rebuild found a real builder bug, and this one is fixed.** The
`mixamo` preset strips a `mixamorig:` prefix and a trailing `_NNN`, then maps
by name. Prix's joints are named `FemaleBody_<MixamoName>_<NNN>`, so stripping
`_093` gives `FemaleBody_Head` — not a name Mixamo is expected to have, so
nothing was renamed and the matcher downstream took whatever looked closest:

```
head:         FemaleBody_Neck_092        <- her NECK
rightHand:    FemaleBody_RightForeArm_073 <- her FOREARM
leftUpperLeg: FemaleBody_L_but_01_02     <- her BUTTOCK helper bone
leftFoot:     FemaleBody_L_but_02_03_0   <- also a buttock bone
```

The preset now drops leading `<token>_` segments until an expected name
appears, under the guard that was already there — a rename happens only when
the result is a name Mixamo is expected to have AND that name is still free,
so it cannot invent a mapping that was not already there. `FemaleBody_L_but_01`
tries `01`, `but_01` and `L_but_01`, matches none, and is left alone, which is
exactly what stops the buttock bones competing. **52 bones now rename**, the
map comes out correct, and the build reports *"all 4 limb pairs are on the
side their names claim"* and *"feet point (0.0, -1.0, 0.0) — already
forward"*.

**What the rebuild fixes, measured off the written `.vrm`:**

| | |
|---|---|
| height | **1700.0 mm** — not the 0.42 m her recipe warns of, because shape keys drop by default |
| the eyebrows | **separate again**: 834 verts on their own `cejas1` material, no longer merged into the body |
| `cejas1` alphaMode | **MASK**, as the source declares |
| all 13 meshes | preserved, none merged |

**What it does NOT fix, and both are measured rather than assumed:**

* **The hair is still 14.0 x 22.4 x 13.4 mm.** The importer drops the scale
  before any of our code sees the file, so re-applying it needs a builder step
  that reads the source GLB's node scales and restores them to the bone
  subtree and its mesh. The number is not in question — 22.085905 — only the
  mechanism.
* **`Hair` exports BLEND but LOSES ITS BASE TEXTURE** (`baseTex` 13 → None),
  and `aiStandardSurface4` stays OPAQUE despite being named in
  `VRM_CUTOUT_MATERIALS`. The exporter logs `Unexpected alpha clip input node
  type: NoneType` throughout. So the alpha path takes one of the three
  materials the source declares and mishandles the other two.

#### FIXED: the hair, by baking the scale into the GLB

**Two independent losses, not one**, and each needed its own fix. Both are
verified by measurement.

**1. The scale.** `glb_bake_joint_scale.py` rewrites the file so no joint
carries a scale at all: it drops the scale from the joint, multiplies every
descendant's local translation by it, and corrects the inverse bind matrices
by `IBM' = inverse(world') * world * IBM` so that `world' * IBM'` equals
`world * IBM` and **no vertex moves**. It checks its own arithmetic before
writing — *"rewrote 130 inverse bind matrix/matrices; worst joint-matrix
disagreement **1.388e-16 m**"* — and refuses above a micrometre.

**2. The placement, which was a separate fault entirely.** Even baked, the
hair still imported at the world origin. Blender's importer derives bone
positions from the INVERSE BIND MATRICES, and this file's IBMs and its node
tree disagree: the node tree puts `hairAll` on her head, the IBMs put it at
the origin, 1.4 m away. The renderer is unaffected either way — a skinned
vertex is `world(joint) * IBM * v` and both halves move together — which is
exactly why the file looks right everywhere except in Blender's bones.
`VRM_GLTF_BIND_POSE=node` passes `guess_original_bind_pose=False`.

Measured on import, which separates them cleanly:

| | hair mesh on import |
|---|---|
| as supplied | 3.9 x 3.8 x 6.3 mm, at the origin |
| baked only | 87.1 x 83.4 x 138.9 mm, **still at the origin** |
| `bind_pose=node` only | 4.8 x 5.5 x 6.1 mm, **correctly on the head** |
| **both** | **107.0 x 121.6 x 133.7 mm, on the head** |

And in the built `.vrm`, against the installed bundle's 14.0 x 22.4 x 13.4 mm:

```
CN_F_HAIR_111_Hair_0   10741 verts   372.6 x 465.6 x 423.3 mm
```

Long hair falling past the shoulders, which is what her source render shows.

**The after-import repair was tried first and withdrawn.** It learned the
GLB->Blender mapping from the bones the importer placed correctly and applied
it to the ones it had not — which rests on that mapping being a similarity,
and it is not. Fitted over 115 control joints it left **124 mm** of residual,
with `FemaleBody_L_eye_J_0104` **421.9 mm** out and a finger joint 188.0 mm
out on a 434 mm span. Blender does not place bones from the node hierarchy
alone, so there is no single transform to recover. The module was deleted
rather than left as a dead path.

#### Still blocking: the Hair material loses its texture

`cejas1` exports **MASK** correctly, so the eyebrows are fixed. The other two
are not:

* **`Hair` exports BLEND but with `baseTex` NULL.** Built without
  `VRM_BLEND_MATERIALS` it keeps its texture and exports OPAQUE; asking for
  BLEND is what drops it. So the hair would now be the right shape in the
  right place and untextured.
* **`aiStandardSurface4` stays OPAQUE** despite being named in
  `VRM_CUTOUT_MATERIALS`.

#### FIXED: enabling MToon was throwing the base texture away

The cause was one unfilled slot, and it is not in the alpha code at all.
`mt.enabled = True` switches a material to MToon, and from then on the
exporter reads **MToon's own** base-colour slot —
`mtoon1.pbr_metallic_roughness.base_color_texture.index.source` — which
starts EMPTY. The block that turns MToon on sets the base colour FACTOR and
never the TEXTURE.

Everything upstream looks right, which is what made it hard to see. The
Principled node still holds the image, Blender still shows it, and the build
log still prints `material Hair ... TEX -> base=packed:Image_12`. Only the
written file is missing it. So the symptom reads as *"asking for BLEND drops
the map"*, which points squarely at the alpha code — and the alpha code is
innocent.

```
before   Hair   alphaMode=BLEND  baseTex=None
after    Hair   alphaMode=BLEND  baseTex=12
```

**The blast radius is nil**, which was worth measuring rather than assuming,
since this silently removes a texture and six characters were rebuilt through
the cutout path on 2026-11-12. Swept all 65 installed bundles for a non-opaque
material with no base map: **2 carry one**, and neither is this. Adachi Rei's
`Glass` is a downloaded bundle, and Alice Ivy's three were already recorded
here as a separate sub-case in the 2026-11-11 rebuild note. A CUTOUT survives
the empty slot — `cejas1` kept its map throughout — and it was a BLEND that
did not, with `VRM_BLEND_MATERIALS` used on exactly one other character.

#### Where she stands

| | |
|---|---|
| hair geometry | **372.6 x 465.6 x 423.3 mm**, from 14.0 x 22.4 x 13.4 |
| hair material | **BLEND with its texture** |
| eyebrows | separate mesh, **MASK**, 834 verts |
| height | 1700.0 mm |
| humanoid map | correct; all 4 limb pairs on the side their names claim |

#### The lens: it is meant to be INVISIBLE, and is now dropped

`aiStandardSurface4` is the layer over her irises, and the gate was right to
refuse it. Its base map is a 4096x4096 **grey+alpha** PNG whose alpha is
**100.0% clear** — every pixel fully transparent. With `alphaMode=MASK` the
source discards the entire mesh, so the lens contributes nothing to her
appearance by design.

The builder's own guard says it declines an alpha that is *"almost entirely
transparent, which would erase the mesh"* — and here erasing the mesh is the
author's intent. Rather than loosen a guard that is right in general, the two
meshes are simply excluded: `^(Icosphere|[LR]_iris_.*)$`. Same result, 804
fewer vertices, and no alpha subtlety to get wrong later.

That also retires the 2026-11-12 hand-fix. The installed bundle carries the
lens at alpha 0.08 with her SKIN atlas on it; the source says it should not be
drawn at all.

**So her eyes are now whatever `eyes1` gives**, which is a 4096x4096 RGB map
with emissive (0.2286, 0.2286, 0.2286) — the glow in her character-select
screenshot. Whether that alone produces the blue irises of her source render
is **not yet established**; it needs a look at her.

#### Still wrong: her hair ships GREY

The last known defect, and the numbers are exact. glTF multiplies
`baseColorTexture` by `baseColorFactor`, and her hair map
`CN_F_HAIR_110_hair` is a 512x512 **grey+alpha** image — 13.3% clear, 59.5%
solid — carrying no colour of its own. The colour is entirely in the factor:

| | baseColorFactor |
|---|---|
| source GLB | **(0.0782, 0.0182, 0.0182)** — near-black |
| our build | (1.0, 1.0, 1.0) — white |

So the hair comes out **grey**, which is exactly the washed-out skullcap in
her installed bundle next to the near-black hair of her source render. The
builder forces white whenever a base texture exists, on the assumption that
the map carries the colour.

Blender's importer brings the factor in as a **Mix node** between the texture
and Base Color — colour input B holds it, A takes the image, read off the
graph directly.

**FIXED, and the first attempt failed for a reason worth keeping.** That
attempt read the Mix node *after* `mt.enabled = True`, printed nothing and
changed nothing, and was removed rather than left as a step that silently
does nothing. A debug print at the line is what finally said why:

```
DEBUG Hair: bsdf=True base_tex=True bc_linked=None from=None
DEBUG lambert11: bsdf=True base_tex=True bc_linked=True from=TEX_IMAGE
```

`bc_linked=None` means `bsdf.inputs.get("Base Color")` returned **None** —
on the one material being fixed, and not on its neighbour. **Enabling MToon
REBUILDS the material's node tree**, so by the time the old code looked, the
Principled graph it wanted to read no longer existed. The tint is now read
BEFORE MToon is enabled, and the build says so:

```
Hair: carrying the source's base colour factor (0.0782, 0.0182, 0.0182)
      rather than shipping its map at white
```

| | baseColorFactor |
|---|---|
| source GLB | (0.0782, 0.0182, 0.0182) |
| **our build** | **(0.0782, 0.0182, 0.0182)** |

#### She builds clean

| | |
|---|---|
| hair geometry | **372.6 x 465.6 x 423.3 mm**, from 14.0 x 22.4 x 13.4 |
| hair material | BLEND, with its texture, **near-black** |
| eyebrows | separate mesh, MASK, 834 verts |
| iris lens | excluded — 100% clear in the source |
| height | 1700.0 mm |
| humanoid map | correct; all 4 limb pairs on the side their names claim |
| meshes / materials | 11 / 8, skin intact |

**Her recipe, which she has never had:**

```
glb_bake_joint_scale.py prix.glb prix_baked.glb
VRM_BREASTRIG=1 VRM_GLTF_BIND_POSE=node VRM_BLEND_MATERIALS="Hair" VRM_CUTOUT_MATERIALS="cejas1" build_vrm.py prix_baked.glb <emptytexdir> 1.70 mixamo "Prix" prix.vrm 1024     '^(Icosphere|[LR]_iris_.*)$' '' ''
```

`VRM_BREASTRIG=1` is not optional for her. Without it she builds with **3**
spring chains where the bundle she replaced had **5**: her source carries no
chest bones at all, so the rigger has to BUILD them. With it:

```
chest rig: built BreastSpring_L, BreastSpring_R and weighted 341 vertices onto them
breast spring chain 'BreastSpring_L': 2 joints, stiffness 1.00, drag 0.90
breast spring chains added: 2
colliders: 10 in one group, attached to 3 of 5 spring chain(s)
```

That last line is the day's other lesson holding: **3 of 5**, because a chest
chain is deliberately given no collider group, and the two it skips are
exactly the two just built.

Then flatten the shine on the exported bundle — `patch_shine.py <bundle> '*'`
— which is confirmed by render rather than assumed.

#### FINAL, installed 2026-11-16

Rebuilt with the rigger, exported (7,575,706 bytes, `failures=0`), shine
flattened (7 of 8 materials changed, 0 gone, 0 added), load-tested against the
bundle it replaces — **134 bones against 130 and 5c/15j against 3c/11j, the
+4 bones being the two chains and their tips, 0 failed** — and installed as
md5 `dff90f9`, 7,500,450 bytes, backup `Prix.prechestchains-2026-11-16.yargchar`
(sha256 `406381dd5d63`).

Read back off the installed file:

```
5 chains:
   backHair_00_physics_8_13_15_0107   4 joints  collider group
   LefthairA_00_physics_8_13_15_0114  4 joints  collider group
   RefthairA_00_physics_8_13_15_0118  3 joints  collider group
   BreastSpring_L                     2 joints  NO group (chest, by design)
   BreastSpring_R                     2 joints  NO group (chest, by design)
```

5c/15j, matching the bundle she had before the rebuild exactly; centred to
-6.6/+7.0 mm; height 1.700 m.

**All four reported faults are closed**, three of them confirmed by eye on the
podium. What remains on her is a **31.9 mm arm depth asymmetry**, which is her
authored pose and would need deforming to square, and **hair that reads auburn
rather than near-black**, which is not specular — the tint in the bundle is
exactly right — and is most likely blended hair cards accumulating under the
podium light. Neither was reported and neither is a fault.

#### INSTALLED 2026-11-16, with one regression that must be named

Exported at **7,563,587 bytes** (`ALL DONE, failures=0`), load-tested against
the bundle it replaces — both load, 0 failed — and installed over a verified
backup, `Prix.prerebuild-2026-11-16.yargchar`, sha256 `0124c722d881`,
13,770,126 bytes. The installed file is byte-identical to the built one,
md5 `0e4bdd0...`.

Read back off the INSTALLED bundle, her hair is where it belongs:

```
CN_F_HAIR_111_Hair_0   10741 verts   x -0.202..+0.170  y +1.220..+1.686  z -0.190..+0.233
```

From the top of her head down to her chest, 372 x 466 x 423 mm, against the
14 x 22 x 13 mm pellet at her ankles. Height 1.700 m. And her three HAIR
PHYSICS chains now exist and are driven — `backHair_00`, `LefthairA_00`,
`RefthairA_00`, 11 joints — so it moves.

**THE REGRESSION — CENTRING FIXED 2026-11-16, asymmetry still open.** The
first rebuild was **63.5 mm off-centre** and carried **31.9 mm** of
left/right depth asymmetry in the arms, where the bundle it replaced was
**perfectly centred and symmetric** — `pair_offset` worst 0.0 mm, no
half-body step at a 1 mm threshold:

| | old bundle | rebuilt |
|---|---|---|
| pair-offset worst | **0.0 mm** | 31.9 mm (arms, dz) |
| hip-pair centre | 0.0 mm | **-63.5 mm** |
| shoulder-pair centre | 0.0 mm | -49.9 mm |

The cause is `VRM_GLTF_BIND_POSE=node` itself. It is what puts the hair on her
head, and it does that by using her AUTHORED rest pose instead of the
symmetric one her inverse bind matrices describe — and her authored pose is
neither centred nor symmetric. The two cannot both be had from that one flag.

**The centring half is fixed by a new builder step** that translates the rig
and its meshes onto the character's own root, measured as the midpoint of the
pairs the Avatar itself calls left and right. Rebuilt, re-exported
(7,566,950 bytes, `failures=0`), load-tested — identical to the bundle it
replaces on every count, 11 renderers / 8 materials / 130 bones / 11 skinned
meshes / 3 chains / 11 joints, 0 failed — and installed, md5 `8ee48d5...`,
over the same backup.

| | first rebuild | **installed now** |
|---|---|---|
| hip-pair centre | -63.5 mm | **-6.6 mm** |
| shoulder-pair centre | -49.9 mm | **+7.0 mm** |
| arm depth asymmetry | 31.9 mm | 31.9 mm — **unchanged** |
| height | 1.700 m | 1.700 m |
| hair | 372.6 x 465.6 x 423.3 mm | unchanged |

The residual +-7 mm is her LEAN: the step centres the mean of the pairs and
her halves still disagree by 11.4 mm, so neither half can sit at exactly
zero.

**On a character who leans HARD that limitation bites, and it can move him
further from the axis than it found him.** Rebuilding Kronk 2026-11-17 the
step reported *"the humanoid pairs centre +16.9 mm off X=0 (spread 116.7 mm
across 5 pair(s)) ... now +0.00 mm"* -- truthfully -- and his LEGS went from
-3.0 mm in the shipped bundle to **+13.9 mm** in the rebuild, his arms from
+27.9 to +44.8. Centring a mean whose members span 116.7 mm is an average of
things that disagree, and no individual pair lands near zero. It is not a bug
and the printed spread says so; it is a reason to **straighten a leaning
character before centring him**, which is the order `straighten_spine.py
--recentre` now uses. **And the 31.9 mm arm asymmetry is untouched on purpose** — a pure X
translation cannot change a depth difference, and a step that appeared to fix
one would be doing something other than translating. It is her authored pose,
and squaring it is a deformation, which is a different decision from moving
where she stands.

**She also loses her two `BreastSpring` chains**, 5 chains to 3. The rigger
refuses them honestly: *"breast spring chains added: 0 (no weighted chest
bones in this rig)"*. Her source has no chest bones, so the old bundle's pair
were added to it after the fact, and `patch_add_springs.py` can put them back
on the rebuilt file the same way.

#### Looked at her, 2026-11-16: her eyes are FIXED

With the podium render working, the comparison is direct. **Before** — bald
but for a grey skullcap, **glowing white eyes with no iris at all**, standing
visibly off the centre of the podium, with the hair pellet a speck by her
ankle. **After** — long hair past her shoulders, **blue irises with pupils**,
eyebrows, and centred on the disc.

So removing the lens was the answer to "no pupils": it was the only thing in
front of her irises, and `eyes1` alone gives her exactly the eyes her source
render shows. **That is three of the four reported faults closed by looking**
— hair, pupils and the brows — and the fourth, the eyelashes, turns out to
have no separate geometry at all: what reads as lashes is the dark liner in
`eyes1` itself, visible in the close-up.

#### And she was shiny, which was never reported

Her skin came out bronze and glossy, the Sophia class exactly. Flattened with
`patch_shine.py '*'` and **confirmed by a before/after render** rather than
assumed: matte skin, and her eyes and liner read properly where the specular
had been washing them out. Installed, md5 `5e86fa7`, 7,482,953 bytes, backup
`Prix.preshine-2026-11-16.yargchar` (sha256 `3b6309563dd2`). Add
`YARG_NO_SHINE_MATERIALS` to her recipe so a rebuild keeps it.

**Her hair is still auburn where the source is near-black**, and the shine
pass did NOT change that, so it is not specular. The tint is correct in the
bundle — `_Color (0.310, 0.144, 0.144)` is exactly the sRGB encoding of the
linear `(0.0782, 0.0182, 0.0182)` the GLB declares — so the likely cause is
many alpha-blended hair cards accumulating under a bright podium light. Not
chased; it is a refinement rather than a fault, and she reads as a brunette
either way.

Nothing has been installed. Her bundle is untouched and the rebuilt file is a
scratch artefact.

### Her 25.71° is a POSE, not her rest pose — and the pose is in her OWN GLB, 2026-11-20

**The section below concludes "leave her, every correction trades the buried shoe for a twisted
pelvis". Its premise is false: the 25.71° is a clearable POSE, and her rest pose is level and
symmetric.** Put at the head of the old claim rather than after it, because a reader who stops
at the first relevant section is the reason she was closed twice.

> **CORRECTION, same day, to the first version of this section.** It said the unlock was the
> author's `.blend` in `~\Downloads\jessica-rabbit.zip`, "sitting there the whole time". **That
> is wrong and the `.blend` is a red herring.** `source_pose_check.py` on `jessica_rabbit.glb` —
> the source she was ACTUALLY built from — reports the same thing to the same numbers: 43 posed
> bones against the `.blend`'s 41, the identical rotations (`shin.L` 61.64°, `upper_arm.R`
> 52.75°, `thigh.L` 42.89°, `spine.001` 37.24°), rest dz **0.00 on all six L/R pairs**, and
> posed dz −597.41 / −277.55 / +5.32 / +79.03 / −0.87 / −187.78 matching the `.blend` exactly.
> Mirror deltas are 8e-3 rather than the `.blend`'s 1e-8, which is glTF float precision at 8 µm.
>
> So no new source is needed and no new recipe is needed. **The pose was always separable in the
> file the build already reads.** I reached for the exotic source first because I found it first;
> the cheap check on the ordinary one would have settled it in a single run.
>
> *(That check only worked after a fix: `import_scene.gltf` suffixes every bone with its index,
> so `shin.L` arrives as `shin.L_165` and a side matcher testing the end of the string finds no
> pairs on any glTF rig. The first GLB run reported "no L/R pair identified" on a perfectly
> regular 160-bone rig. It was caught only because the tool prints WHY it found none instead of
> printing zeros.)*

**Her REST pose is level and symmetric.** Measured in the `metarig` (Rigify, 159 bones):

**Every L/R pair is EXACTLY zero at rest**, from `source_pose_check.py`:

| pair | rest dz | posed dz | local mirror delta |
|---|---|---|---|
| `thigh` | **0.00** | −597.41 | 1.49e-08 |
| `shin` | **0.00** | −277.56 | 0.00e+00 |
| `foot` | **−0.00** | +5.31 | 0.00e+00 |
| `toe` | **−0.00** | +79.03 | 0.00e+00 |
| `shoulder` | **0.00** | −0.87 | 1.86e-09 |
| `upper_arm` | **0.00** | −187.78 | 1.49e-08 |

> **Those dz figures are in the SCENE'S OWN UNITS, not metres** — this armature carries a
> `matrix_world` scale of about 5.58 and her spine sits at Z ≈ 6.9, so a 1.7 m character does not
> read in metres here. The load-bearing numbers are the ones that do not depend on the unit: the
> rest column is **exactly zero** on all six pairs, and the mirror deltas are 1e-8. Do not quote
> −597 as millimetres of anything.

And the limb angles, which are unit-free:

| | rest L / R | posed L / R |
|---|---|---|
| thigh off vertical | **6.2° / 6.2°** | 28.0° / 6.2° |
| shin off vertical | **0.7° / 0.7°** | 28.4° / 0.7° |
| upper arm off vertical | **16.3° / 16.3°** | 31.2° / 36.5° |

**The 25.71° lives in `spine`'s `matrix_basis`** — a pose, on top of that rest pose, one of 41
posed bones — and it is the *same number* this file records as her installed Hips roll.

**And the source is SELF-CONSISTENT, which is the part that reframes the fault.** Under the
author's pose only her LEFT leg moves (thigh 28.0° against the right's 6.2°), and her feet come
out level: posed `dz` is +0.0010. So the author rolled the hips and compensated down the leg.
**Our build kept the roll and lost the compensation** — that is where the buried foot comes from.
It is not "a fault inherited from a posed source"; it is a self-consistent pose, half-applied.

**Clearing the pose is safe, and the unbound geometry says why.** Of 16 meshes, 10 are bound and
100% weighted (`Jessica` 28,860 verts, `hair1.001` 50,440, `gloves`, `shoes`, both eyes, three
`NurbsPath` hair strands, `BezierCurve`). Six do not follow the rig, and none of them is her:

| mesh | verts | weighted | modifier | centre (x, y, z) |
|---|---|---|---|---|
| `Body_resculpt1.001` | 9,308 | 9,308 | **NO** | +0.002 +0.222 +6.275 |
| `Cube` | 2,426 | 0 | NO | −0.207 **+3.080** +10.191 |
| `Cube.004` | 12 | 0 | NO | −0.207 **+3.100** +9.746 |
| `Cylinder` | 64 | 0 | NO | −0.206 **+3.098** +9.579 |
| `Cylinder.002` | 64 | 0 | NO | −0.209 **+3.440** +5.141 |
| `Cylinder.003` | 160 | 0 | NO | −0.211 **+3.790** +0.610 |

Those five props sit a metre in front of a body centred at y ≈ +0.3, and descend 10.19 → 9.75 →
9.58 → 5.14 → 0.61. **That is the microphone and its stand** — the thing this file has described
her as leaning on since 2026-11-16, present as geometry. They must be excluded from a build, not
carried. `Body_resculpt1.001` is fully weighted with its armature modifier missing, so it is a
sculpt duplicate rather than her body.

**This is NOT a deliberate exclusion being re-opened.** The builder's machinery around her —
facing cross-checked against shoulder roots because her feet are posed, `VRM_STRAIGHTEN_LEGS`
opt-in because "straightening a leg is a DEFORMATION… it is the deformation that tears" — is
correct reasoning about **the GLB**, where the pose IS the rest shape. The `.blend` is a
different artefact layer. This file already knew it existed: the viseme table says *"a DIFFERENT
source blend has keys; the GLB she was built from has none — not attempted"*. It was passed over
for its shape keys, and nobody checked its rest pose.

#### So why does the shipped character carry the roll? A PREDICTION, written before the run

`build_vrm.py`'s default is to **discard** a source pose. It keeps one in two cases, and the
second is the suspect: the *"Anakin"* path, which keeps the pose when the skeleton lies inside
the **unrigged** geometry posed and outside it at rest, because then the model was sculpted in
that pose and it is the only configuration worth binding in.

That test builds its population as meshes with no armature modifier, **no vertex groups at all**,
and ≥50 vertices. On her GLB that is:

| mesh | verts | in `_loose`? |
|---|---|---|
| `Object_10` | 13,275 | **YES** — and this is her SKIRT (the dress note records the skirt at 13,275) |
| `Object_12` / `_13` / `_17` / `_19` / `_21` | 9,728 / 2,880 / 192 / 192 / 576 | yes, but her recipe EXCLUDES them (the mic) |
| `Object_15`, `Cube`, `Icosphere` | 34 / 8 / 42 | no, under the 50-vertex floor |

**Her recipe excludes the six mic parts and does NOT exclude `Object_10`.** So after exclusion the
heuristic measures her rig against her own unweighted skirt — which hangs on her posed body, so
the skeleton is inside it posed and out of it at rest. **Prediction: the build log says
`rig fit against 1 unrigged mesh(es)` and then `KEEPING the animated pose`, and the bake is what
buries her foot.**

#### THE PREDICTION FAILED, and the real rule is a third one

Built with her recipe unchanged (exit 0, 14,798,080 bytes). **Neither predicted line appears.**
Both heuristics are gated on `if _had_anim …` and **her GLB has no animation attached**, so a
third rule applies, at `build_vrm.py` line 905:

```
keeping a static pose on 41 bones (no animation was attached, so this is the
  model's shape, not a stray frame)
...
baked a non-identity rest pose (31 bones) into the rest pose
```

The `_loose` reasoning was wrong twice over: the log also shows `auto-weighted unrigged mesh
'Object_10' (13275 verts)` and `'Object_9' (24035 verts)`, so by the time any unrigged-geometry
test could run there was no unrigged geometry left. I had read two heuristics carefully and
missed that the one that fires is the `else` branch of the gate on both.

**The control, which is the part that makes this usable.** Source against the build it produces:

| pair | source GLB rest dz | built VRM rest dz | recorded in the shipped bundle |
|---|---|---|---|
| `thigh` | **0.00** | **−92.38 mm** | **92.4 mm** |
| `upper_arm` | **0.00** | **−29.04 mm** | **29.0 mm** |
| `shin` | 0.00 | −42.92 | — |
| `foot` | 0.00 | +0.82 | — |

**Reproduced to 0.02 mm on a number recorded four days earlier from a different artefact.** The
source's *posed* thigh angles (28.0° L / 6.2° R) are the output's *rest* angles, with the T-pose
laid on top (`upper_arm` 90.0° off −Z, i.e. along X). So the chain is settled: her source is
clean, the builder keeps her static pose, bakes it into rest, and that is the buried foot.

#### The rule is DELIBERATE, and it is still wrong for her — the discriminator is already here

Line 905 carries its own counter-example, and it is a good one:

> *"A static pose in `matrix_basis` is not a stray animation frame — it can be the model's SHAPE.
> Alcina Dimitrescu is 9 feet 6 inches because her pose says so, with no action attached at all;
> resetting her to rest compressed her head and torso to 59% and left her hat and hair floating
> above them."*

So this is not an oversight to delete, and there is no flag to decline a static pose:
`VRM_KEEP_POSE=1` only forces keeping. **But the signal that separates Alcina from Jessica is
already computed in this file, and already acted on — for hands only.** Two lines after the bake:

```
fingers: relaxed the L hand's 15 finger bones to rest -- it is posed 21.2 deg
  off rest while the other hand sits AT rest, so it is gripping a prop this
  build has removed (VRM_KEEP_GRIP=1 keeps it)
```

**The builder detects that she is holding a prop the build removed, and relaxes her hand for it —
then keeps the body pose that was holding her against the same removed microphone.** The hand
rule is right. It simply is not asked about the body.

The discriminator that follows: *a static pose is the model's shape unless it poses the character
against geometry THIS BUILD EXCLUDES.* Alcina has no removed prop, so she is untouched; Jessica's
mic is in her own `EXCLUDE` argument, known at line 183 and so available 700 lines before the
decision. **Alcina is the control and must come out unchanged** — ideally byte-identical, the way
Spartan Mark V was for the bodice re-weighting step.

#### That rule is WRONG, and its own control is what says so — 2026-11-20

**Do not implement the paragraph above.** It was proposed, approved, and then disproved before a
line of it was written, by the control it had itself nominated. The claim *"Alcina has no removed
prop"* is false. This file says so 5,700 lines further down, under *"A hand posed around a prop
that is no longer there"*:

> *"Alcina Dimitrescu holds a cigarette holder. The holder is excluded from the build
> (`^NurbsPath`) because it skewers her hand"*

So Alcina has an `EXCLUDE`, the excluded geometry is **a prop she is holding**, and her static
pose is the one that MUST be kept — it is her 9'6". The proposed rule fires on exactly the
character it was supposed to protect, drops her pose, and compresses her head and torso to 59%.
**It is not a near miss; she is the worst case for it on the roster.**

And the reason the error was easy to make is worth keeping: the hand-relax rule two lines below
the bake *was written for Alcina*, from her case, and it works because **the model supplies its
own control** — her right hand matches rest to 0.0° on all five chains while her left thumb is
125.7° further curled. That is an asymmetry between two things that should agree, not a
proximity-to-prop test. I generalised the wrong half of it: the part about a removed prop, rather
than the part about an internal disagreement.

**So props cannot be the discriminator**, because keeping a pose and relaxing a prop hand is
exactly the right combination and Alcina already gets it. What Jessica needs on top is her BODY
pose dropped. **Nothing was implemented, and the rule above stays struck rather than deleted so
the next session does not re-derive it.**

#### THE LEGS separate them, measured on both with one instrument — 2026-11-20

`source_pose_check.py` on each author source, `%` of each rig's **own** span so two differently
scaled files are comparable (Alcina's span 3.4507 units, Jessica's GLB 43.3899):

| pair | **Alcina** — pose must be KEPT | **Jessica** — pose must be DROPPED |
|---|---|---|
| `thigh` | **0.00%** | **−1.38%** |
| `shin` | **0.00%** | −0.64% |
| `foot` | **0.00%** | +0.01% |
| `toe` | **0.00%** | +0.18% |
| `shoulder` | 0.10% | −0.00% |
| `upper_arm` | **1.67%** | −0.43% |

Alcina's 23 posed bones are **all arms, hands and fingers** — `forearm.L` 135.97°, `thumb.02.L`
102.20°, `hand.L` 61.63° — holding the cigarette holder, with **no spine and no leg bone touched
at all**. Jessica's pose reaches `spine.001` 37.24°, `spine.002` 36.67°, `thigh.L` 42.89° and
`shin.L` 61.64°.

**And the ARMS invert.** Alcina's arms are posed roughly four times harder than Jessica's
(1.67% against 0.43%), so a threshold on overall pose magnitude, or on the arms, gets this
exactly backwards. Only the legs work, and on them the gap is 0.00% against 1.38% — so the
cutoff would not be doing the work, which is the property this project asks of a threshold.

> **Jay's objection, and it is half right: "Alcina is bigger than other characters, are we sure
> we want to use her as a base to compare?"**
>
> **Her size does not corrupt the measurement.** The `%` columns exist for that, and her legs
> read **exactly 0.0000 in raw units** with mirror deltas at 4.47e-08. A zero is scale-free; no
> normalisation turns it into a non-zero, so "her legs carry no pose" holds at 2.9 m or at 1.7.
>
> **But she is NOT a sufficient control, and that is the real objection.** She is necessary —
> she is the character the existing rule was written to protect, so she is the one who must not
> regress — and she is also **n = 1 and atypical**: upper-body-only pose, 2.9 m, holding a prop.
> A rule validated on her alone is validated at one point. The rule would change behaviour for
> *every* character whose source has a static pose and no action attached, and that population
> was unmeasured when the rule was proposed. **Sized before implementing, not after** — the same
> order that the shader-default sweep got wrong, where a "defect" turned out to be shared by 63
> of 65 characters.

#### The population, swept over the 26 sources on disk

| outcome | count | who |
|---|---|---|
| **the rule would fire** | **1** | `jessica_rabbit.glb`, **1.38%** |
| keeps a static pose, legs **0.00%** | **18** | Alastor, Alice Ivy, Doom Slayer, Fortnite Mando/Baby Yoda, `Jessica_Rabbit.usdz`, Judy Hopps, Killer Clown, **Kronk** (86 posed bones, legs clean — his lean was spinal), Peacemaker, Pomni, Rebecca, Shaggy, **T-800_Run**, Thanos, Heels, Vigilante, Xenomorph, Harley Quinn |
| already reset — an action is attached | 6 | Baby Groot, Mando-for-mixamo, Batman, Lola Bunny, Prix, Heavy Metal girl |
| **unreadable — UNKNOWN, not clean** | 1 | `Yoda.usdz` (no armature found) |

**So Alcina is not an exotic control: 18 of 18 characters on that branch read exactly 0.00%**,
including two whose filenames promise a pose (`Kronk_Doing_the_Hokey_Pokey`, `T-800_Run`). And
the zeros are trustworthy because the same instrument reads **2.14% on Prix**, 0.23% and 0.22% on
two others — all in the already-reset branch, so a non-zero sits beside the zeros.

Not a census: 107 zips may hold further `source/*.blend` files, and the roster's downloaded
bundles have no source here at all.

#### Implemented as `VRM_DROP_LEG_POSE=1` — opt-in, and the build then ABORTS

`build_vrm.py` now measures what the static pose ADDS to the leg roots' height difference
(posed minus rest, so an authored rest asymmetry is left alone) as a % of the rig's own span.
Its own reading agrees with the tool's: **1.38%, `thigh.L` / `thigh.R`, limit 0.50%.**

**It is opt-in because on its own it does not produce a shippable character.** With the flag set,
the pose is correctly dropped and the build then refuses:

```
ABORT: re-weighting 'Object_10' left it on 1 bone(s) with 0 unweighted vertices.
  That is no better than what it had, and shipping it would hide the fault rather than fix it.
```

`Object_10` is her **skirt** — 13,275 vertices, unweighted in the GLB, authored around the POSED
body. Drop the pose and bone heat binds it to whatever is now near, so the whole garment lands
on one bone. **The guard caught it instead of shipping it**, which is the guard working. Turning
the rule on by default would convert a build that produces a wrong character into one that
produces no character, which nobody asked for — the same reasoning that made `YARG_KEEP_MTOON`
opt-in.

**THE DEFAULT PATH IS PROVEN INERT, on the one character the rule targets.** Rebuilt with the
flag off: **14,798,080 bytes, sha256 `86767e6ff48531f3`, byte-identical to the pre-change
build**, zero occurrences of the new log lines, and the original `keeping a static pose on 41
bones` intact. That is a stronger control than Alcina, because it is the subject rather than a
bystander.

#### ANSWERED, 2026-11-20: leave her. Three corrections, three costs, all measured

The re-opening was **justified** — the shoe is real, 92.4 mm, measured on geometry against two
controls at 0.0 (below). And the answer is still the 2026-11-16 one, now with the cost of every
available correction measured rather than argued:

| correction | does it fix the shoe? | what it costs |
|---|---|---|
| patch the installed bundle | — | **impossible**: `Hips` is humanoid-mapped and the Animator retargets from the Avatar |
| **drop the static pose** (`VRM_DROP_LEG_POSE=1`) | **yes — 0.0 mm** | her skirt stretches across the widening gap between her legs: **max edge stretch 30.35x**, and her stance, which is the character |
| **level the hips** (`straighten_spine.py --level`) | **yes — 0.0 mm** | her skirt **swings sideways**, drift +24 mm → **−155 mm**, the garment 200–390 mm off |

**The hips route is the surgical one and it still fails.** One bone rotated, 25.71° → 0.000°,
thighs and torso keeping their orientation, `thigh.L vs thigh.R` −92.38 mm → **−0.00 mm**, and
the shoe measured on the exported bundle at **0.0 mm** with no streaks anywhere. Then the skirt:

| skirt centroid X, by height band | shipped | hips levelled |
|---|---|---|
| y 0.45–0.60 | +72.3 mm | **−143.0 mm** |
| y 0.30–0.45 | +82.6 mm | **−204.5 mm** |
| y 0.15–0.30 | +90.5 mm | **−269.3 mm** |
| y 0.00–0.15 | +96.4 mm | **−298.3 mm** |

The shipped skirt drifts **+24 mm** over its whole drop — it hangs straight. The levelled one
drifts **−155 mm** and sits 200–390 mm across, fanning wider the lower it goes: a garment
rotated with the pelvis. **Her skirt is weighted to `spine`, which IS her Hips**, so rotating
that bone rotates her dress with it.

**That is the 2026-11-16 sentence, measured: "every available correction trades the buried shoe
for a twisted pelvis."** A skirt swinging 155 mm is what a twisted pelvis looks like from the
outside. The closure was right, it was right for the stated reason, and three independent
attempts now agree with it.

**What is genuinely new, and worth keeping:** her 25.71° is a clearable pose rather than a rest
pose; the skeleton CAN be levelled exactly, two ways; `--level` exists now for a roll, which the
aim sweep cannot express and which Kronk and Mando never needed; and the cost is her dress rather
than her pelvis. **Nothing is installed. She stays as she is.**

#### THE BURIED SHOE IS REAL — measured on GEOMETRY, with controls, 2026-11-20

I doubted it, on the grounds that the figure came from `YargFootProbe`, which reports
**upper-leg bone** heights under the label *"foot height difference"*, and that in a build of her
the foot BONES differ by only 0.82 mm. **That doubt was wrong.** `foot_plane_check_installed.py`
(new) skins the installed bundle and reads the lowest vertex of the geometry each foot actually
dominates:

| character | L min | L p1 | R min | R p1 | **L − R** | foot verts |
|---|---|---|---|---|---|---|
| **Jessica Rabbit** | −0.0917 | −0.0915 | +0.0007 | +0.0009 | **−92.4 mm** | 2,770 / 2,778 |
| Spartan Mark V | −0.0240 | −0.0204 | −0.0240 | −0.0204 | **−0.0 mm** | 695 / 695 |
| Jinx | −0.0003 | +0.0003 | −0.0003 | +0.0004 | **−0.0 mm** | 4,345 / 4,312 |

**Her whole left shoe is 92.4 mm below her right**, and the 1st percentile sits within 0.2 mm of
the minimum, so it is the shoe and not one stray vertex. Two controls read **0.0 mm**, which is
what makes the reading mean anything.

**Why my build disagreed with the installed bundle, which is the part worth keeping.** In the
build I made today the thigh ROOTS differ by 92.38 mm while the foot BONES differ by 0.82 — the
pose compensates down the leg. In the SHIPPED bundle the whole left leg chain is low, so the
compensation is absent and the shoe goes through the floor. Those are two different artefacts and
I compared across them; the bundle is the one a player sees.

**One sub-claim does NOT reproduce.** *"67 mm below her own hem"* measures **7.7 mm** here. Her
dress is weighted to the leg, so the hem follows the sunken foot down and the shoe barely clears
it. (The hem column is not comparable between characters — Spartan's and Jinx's lowest non-foot
geometry is armour that never reaches the floor, which is why theirs read −97.4 and −19.5 mm.)

**So the 2026-11-18 re-opening was justified on the measurement**, even though the probe result
that triggered it was separately downgraded, and even though the stance itself is the character.
A stylised silhouette is not the same claim as a shoe through the floor, and the controls are
what separate them.

#### THE RENDER CAUGHT WHAT FIVE NUMERIC CHECKS MISSED — 2026-11-20

**The section below is correct about the legs and WRONG that she is fixed.** Rendered on the
podium — `measurements/jessica-posedrop-REHOMED-streaks-2026-11-20.png`, against
`-CONTROL-` — her legs are straight and both feet are on the podium, **and a spray of streaks
fans out across the figure.**

> **I read the cause off the picture and the picture misled me.** I wrote here, and in a commit
> message, that skirt vertices had borrowed weights from her FOREARM. **Measured, they had not.**
> The bones carried by the vertices of the 200 most-stretched edges are:
>
> ```
> thigh.R 163, thigh.L 52, shin.L 33, palm.04.R 27, foot.R 19, shin.R 16
> ```
>
> **Her THIGHS dominate**; the one arm bone, `palm.04.R`, is fourth at a sixth of the weight.
> These are not wrong-limb borrows at all — they are skirt panels spanning BETWEEN her legs. Her
> skirt is a tube modelled around legs that are CROSSED in the source, and dropping the pose puts
> them side by side (6.2° / 6.2°, feet 0.216 apart). The panels bridging the gap have to stretch,
> and linear blend skinning across a widening gap is exactly what produces these streaks.
>
> So the donor restriction I set out to build would not have helped: the donors were already
> right. One grep over the actual weights settled what three renders and an inference did not.

**Every numeric check passed.** That is the finding. In order:

| check | reading | verdict |
|---|---|---|
| L/R pair asymmetry | 0.00% on all six | passed, and it was RIGHT — the legs are fixed |
| height / feet | 1.8000 m, z = 0.0000 | passed |
| median distance to body | 352.7 → 286.2 mm (0.81x) | passed, and it is BLIND here |
| p99 distance to body | 1723.2 → 1723.2 mm (1.00x) | passed, and it is blind too |
| **edge stretch (added after the render)** | **median 1.00x, p99 7.19x, max 118.69x** | **CAUGHT IT** |

**Why distance-to-body could not see it, at either percentile.** The far end of a streak lands
*on the body* — her hand IS the body — so the stray vertex is 0 mm away. What explodes is the
EDGE between the skirt and the vertex, not any vertex's distance to anything. The metric has to
be the artefact: stretched geometry means measure stretch.

**And why the median was worthless.** Median edge stretch is **1.00x** — the bulk of the rehoming
is exact — beside a max of **118.69x**. A median cannot see a tail, and a tail of a few hundred
vertices is what a viewer sees first.

`VRM_DROP_LEG_POSE=1` now **refuses to write the file**, naming the percentile, the max and the
bones to blame. Smoothing the borrowed weights over the garment's own edges (`VRM_REHOME_SMOOTH`,
6 passes) took the max from **118.69x to 30.35x** and the p99 from 7.19x to 4.85x — a real
improvement, and not enough, because the stray region is CONTIGUOUS: its neighbours borrowed the
same thighs, so averaging arm-with-arm, or thigh-with-thigh, changes nothing about the gap.

#### And the residue is the 2026-11-16 trade, re-derived from the other end

**This is not an implementation defect left to polish.** Her skirt is cut around crossed legs.
Straighten the legs and the panels bridging them must stretch; no choice of donor, smoothing or
threshold removes a geometric conflict between a garment's cut and the limbs' position. The only
repairs are re-modelling the skirt or accepting the stretch.

Which is the closure this file made on 2026-11-16 — *"every available correction trades the
buried shoe for a twisted pelvis"* — arrived at from a different direction and with a different
cost in the second half of the sentence. **That closure was better founded than I credited when
I re-opened the question.** What is genuinely new is that the skeleton CAN be fixed, cleanly and
measurably, and that what it costs is her skirt rather than her pelvis.

**She is NOT fixed, nothing is installed, and the numbers below stand only for the skeleton.**

#### The legs, which the render confirms: symmetric to 0.00%

`VRM_DROP_LEG_POSE=1` now builds her, and the fault is gone from the output:

| pair | default build | rehomed build |
|---|---|---|
| `thigh` rest dz | **−0.0924 m (−5.32%)** | **0.0000 (0.00%)** |
| `shin` | −2.47% | **0.00%** |
| `foot` posed | −5.32% | **0.00%** |
| `upper_arm` | −1.67% | **0.00%** |
| mirror deltas | 6–10 × 10⁻² | **4 × 10⁻⁴ – 2.7 × 10⁻³** |

That **−0.0924 m is the recorded 92.4 mm**, read off a build rather than off the installed
bundle. Every pair is now zero.

**How, and it is not what the three previous attempts assumed.** Bone heat cannot weight her
skirt or bodice at all — loose shells, and it puts both 100% on the glTF root whether the pose is
applied or not, before and after re-weighting in place. So the orphans are rehomed from the
**body** instead: for each orphan vertex, take the weights of the nearest vertex of a mesh that
IS rigged, evaluated DEFORMED so the match happens in the posed world the garment was authored
in, then store the vertex at `M⁻¹·v` for that blend. The skirt lands on **27 bones** and the
bodice on **25**, against bone heat's one. The builder's own carried-mesh repair then never fires,
because nothing is root-dumped any more.

It has to happen at the pose decision and nowhere later: the pose is baked into the rest pose at
line ~1128 and the carried-mesh repair does not run until ~4057, so by then there is no pose left
to drop — and that repair succeeds on the default path only *because* the bake has made the
skeleton's rest shape the posed shape its garments were cut around.

**A check that can fail, and did.** The guard compares each garment's median distance to the body
before and after, and aborts on the RATIO:

```
'Object_10': median distance to the body 352.69 mm before -> 286.17 mm after (ratio 0.81)
'Object_9':  median distance to the body  57.10 mm before ->  56.33 mm after (ratio 0.99)
```

The bodice at **0.99** is the strong evidence: a garment that sits on the body stayed on it. The
first version of this guard used an ABSOLUTE 50 mm and aborted at 286 mm — but her skirt's median
standoff was already 352 mm untouched, because a skirt flares away from the legs. An absolute
distance measures the garment's cut, not the rehoming; the ratio measures the rehoming.

**Height holds: 1.8000 m verified, feet at z = 0.0000, in both builds.** Her WIDTH moves from
0.5172 m to 1.0083 m, which reads as a consequence rather than a regression — with the lean no
longer baked in she reaches a real T-pose, and this file records her failing the other way when
things go wrong, *"implausibly narrow, 0.1397 m wide for 1.8000 m tall"*.

**NOT INSTALLED, and not yet SEEN.** Numbers are not the project's standard for accepting a
character — a podium render is, and none has been taken of this build. Her installed character is
untouched and her backup discipline applies before anything replaces it.

#### WHY the repair fails, settled — and the deferral point was simply in the wrong place

The builder already contains the repair. Its **carried mesh** step detects a mesh that came out
of weighting on an undrivable bone — *"it was weighted while it stood away from the skeleton"* —
strips the weights and re-runs `ARMATURE_AUTO`. The same step, the same mesh, two paths:

| | default (pose kept) | `VRM_DROP_LEG_POSE=1` |
|---|---|---|
| after bone heat | 100% on `GLTF_created_0_rootJoint` | 100% on `GLTF_created_0_rootJoint` |
| after re-weighting in place | **`Object_10` → 13 bones, `Object_9` → 10 bones** | **1 bone** → ABORT |
| geometry moved | 0.0000 mm | 0.0000 mm |

Ruled out on the way: the *"put 2 deformed mesh(es) into the armature's own space"* step runs on
**both** paths, so it is not the difference.

**The difference is that on the default path the body is still in the pose her skirt was authored
for.** Bone heat always dumps these loose shells on the root — it does so identically on both
paths — and the recovery works only because, when it re-weights, there is a body under the
garment. Clear the pose first and the skirt is stranded in mid-air, so the re-weight finds
nothing near it and returns the root again.

**So the pose must be dropped AFTER the carried-mesh step (~line 4100), not before it.** My
deferral moved it to ~1948, which is past bone heat but still 2,000 lines short of the step that
actually produces usable weights. With that step's 13 and 10 bones in hand, `M` is meaningful and
the `M⁻¹·v` move is the correct final act; with bone heat's root dump it was meaningless, which
is exactly what went wrong below.

#### The deferred reset: implemented, self-verified, REMOVED — and the check could not fail

The reset is now **deferred** until after automatic weighting, because resetting at line 905
strands anything not yet weighted — `UNRIGGED` is not even built until ~1724 and bone heat does
not run until ~1858. With `VRM_DROP_LEG_POSE=1` the sequence now reads:

```
leg roots: the static pose adds 1.38% of rig span to their height difference (thigh.L / thigh.R, limit 0.50%)
DROPPING the static pose: ... the reset is DEFERRED until after automatic weighting
  auto-weighted unrigged mesh 'Object_10' (13275 verts) to the skeleton
  auto-weighted unrigged mesh 'Object_9' (24035 verts) to the skeleton
  deferred reset: 'Object_10' 13275 of 13275 vertices moved to M^-1*v (0 had no usable weight)
  deferred reset: 'Object_9' 24035 of 24035 vertices moved to M^-1*v (0 had no usable weight)
  deferred reset: 37310 vertices moved, 0 left alone, worst round-trip 0.000000
  deferred reset: the static pose is now cleared
```

**37,310 vertices moved and the round-trip is 0.000000**, so the arithmetic inverts the deform
exactly — the self-check is in the code and it is the thing that would catch a wrong `M`.

**And the build still ABORTED**, so the code was **REMOVED on the same day**. Two things were
wrong with it, and the second is the one worth carrying:

**It inverted a matrix that meant nothing.** Bone heat had put both meshes 100% on
`GLTF_created_0_rootJoint`, so the `M` being inverted was the root's, and the move relocated
37,310 vertices by a transform with no relation to the body. It corrupted the input to the very
step that was about to repair them.

**And the self-check COULD NOT FAIL.** It asserted that `M @ (M⁻¹ @ v) == v` — true for *any*
invertible matrix. It verified the algebra and never the premise, so it printed `0.000000` on
weights that were garbage and read as a pass. **A check that holds for every possible input is
not a check**, and this one was written by someone (me) who had recorded that same lesson twice
in this repo the previous week.

What the move needs is the weights from the carried-mesh step above — 13 bones and 10, not one
root — which means the drop belongs after that step, as the section above now says.

#### A BYTE-IDENTICAL REBUILD IS NOT A SOUND CONTROL HERE — this builder is non-deterministic

Found while trying to re-prove the default path inert. Four default-path builds of Jessica, all
**14,798,080 bytes**:

| run | code | sha256 (16) |
|---|---|---|
| 1 | before any change | `86767e6ff48531f3` |
| 2 | after the opt-in rule | `86767e6ff48531f3` |
| 3 | after the deferred reset | **`bd06fa0c2dd3507e`** |
| 4 | **identical code to run 3** | `86767e6ff48531f3` |

Run 4 reproduces run 1 on the very code that produced run 3, so **the change is inert and the
builder varies between runs** — roughly one in four, at a constant length, which is the signature
of something written in a varying order rather than of different content.

**The consequence is methodological and it reaches backwards.** This file cites a byte-identical
rebuild as proof that a step is inert — the bodice re-weighting step's control is *"Spartan Mark V
rebuilt before and after is byte-identical, md5 `b68ce9e4…`"*. At a 1-in-4 variance rate, **a
single byte-identical rebuild is roughly a 75% coin-flip, not a proof**, and a single
byte-DIFFERENT rebuild is not evidence of a change either. Repeat it, or compare on the quantity
you actually care about rather than on bytes. *(Reverting a file to its backup is a different
claim and stays sound: that is a copy, not a rebuild.)*

The cause is not chased here. The same class of bug is already written up in the sibling repo —
`yarg-song-server`'s rule *"Packing is DETERMINISTIC. Never make `PackFS` depend on anything but
the files it is given"*, after a random archive mask gave two clients 16 different files out of 22.

**What is left:** the bind, above. Nothing installed, and her installed character is untouched.

Not built, not installed, and the proposed change is to the BUILDER rather than to a recipe —
which is a correction to the first version of this section, where I called it "a change of INPUT,
not of builder". Her backup discipline applies when anything is installed.

### Jessica Rabbit's right leg is 92 mm higher than her left, 2026-11-16

Chased because `half_body_check_installed.py` put her at **-86.5 mm**, the
largest half-body step on the roster, and because she had been rebuilt that
same day -- so it was either inherited or made by our own builder.

**It predates everything done to her that day.** All four of her snapshots --
`predress` (the original conversion), `prebodice`, `prechestcollide` and the
installed file -- report the identical -86.5 mm step, with identical hip and
shoulder positions to four decimals. The rebuild from her documented recipe
reproduced it exactly, so our builder is carrying it faithfully out of her
source rather than creating it.

#### Three ways of finding her centreline, and why they all failed

Her X positions cannot be compared without knowing where her middle is, and
her middle is exactly what will not be established:

* the **midpoint of a slice's extremes** is a measurement of her outliers;
* a **median over a height band** lands on whichever leg carries more
  geometry -- her band medians spread **169.6 mm**, and the quartiles say why
  (one band runs q25 -0.0197, median +0.1233, q75 +0.1568: not a symmetric
  body, a cluster);
* **flesh centroid against its driving bone** gave +8, +33, -11, -73, -63 and
  -53 mm on six torso bones, flipping sign with no trend.

`centreline_check_installed.py` is kept for the median approach because it is
the right instrument on a symmetric character, and because its quartile
columns are what show when it is not.

#### The measurement that works needs no centreline at all

**Height and depth need no middle.** For a pair the rig itself calls left and
right, `dy` and `dz` should both be zero, and a difference is measured against
nothing but the pair. `pair_offset_check_installed.py`:

```
UpperLeg   dy  +92.4  dz   +3.0     thigh.L / thigh.R
LowerLeg   dy  +92.4  dz   +3.0     shin.L  / shin.R
Foot       dy  +92.4  dz   +3.0     foot.L  / foot.R
Shoulder   dy   +0.1  dz   -2.7     shoulder.L / shoulder.R
UpperArm   dy  +29.0  dz  -74.1     upper_arm.L / upper_arm.R
LowerArm   dy  +29.0  dz  -74.1     forearm.L / forearm.R
Hand       dy  +29.0  dz  -74.1     hand.L / hand.R
```

Her whole right leg sits **92.4 mm higher** than her left and her whole right
arm **29.0 mm higher and 74.1 mm further back**, while her **shoulder bones
are symmetric to a tenth of a millimetre**. Each limb is internally consistent
-- all three joints displaced by the identical amount -- so whole limbs are
displaced rather than deformed, the same signature as Mando's half-skeleton
step. And her arm flesh is symmetric about each arm bone to 0.1 mm
(`forearm.L` -121.4 against `forearm.R` +121.3, `upper_arm.L` -169.4 against
+169.4), so each limb is correctly skinned to a bone that is in the wrong
place.

**Spartan Mark V reads 0.0 mm on every pair and every axis**, and 32 of the 65
bundles are symmetric to within 0.1 mm. That is what makes a reading here mean
something: the instrument demonstrably can return zero.

#### dy and dz are not the same finding

The first version of this sweep reported one number per character and would
have claimed 14 new faults. Several are a fault this file already records. A
pure `dz` difference with `dy` at zero is the body being **turned**: Aiko reads
`dz` -100.2 mm on her legs with `dy` -0.0, and 190 mm of leg separation rotated
by the **29.95 deg** `body_yaw_check_installed.py` already measures for her
gives 94.9 mm. Same fault, second instrument. A `dy` difference cannot come
from a yaw at all.

| classification | characters |
|---|---|
| **a TURN (yaw)** -- already measured elsewhere | Aiko 136, Alastor 28, Vegeta 11, Elite Terrorist 7, Shaggy Rogers 7 |
| **MIXED** -- height and depth both | **Jessica Rabbit 92 (dy 92.4)**, Vigilante 77, Peacemaker 66, Kronk 66 (dy 44.4), Alcina 56 (dy 42.6), Steve 54 (dy 18.4), The Mandalorian 44 (dy 20.2), B1 Battle Droid 32, Thanos 13 |
| symmetric to 0.1 mm | **32 of 65** |

**This closes an open roster item.** The seven characters whose yaw lines
disagreed -- Steve, Jessica Rabbit, The Mandalorian, Alastor, Peacemaker,
Vigilante, Alcina -- were recorded as "a displaced limb each, not a turn".
All seven are flagged here, with the limb named and the displacement in
millimetres, and the split above says which of them are turns after all
(Alastor) and which are genuinely displaced (the rest).

#### SETTLED: it is not a pose. Her left foot is 92 mm under the floor

The pose question was the one thing that mattered, since this file has twice
recorded reading a deliberate choice as a defect. It is answered by asking the
floor. The lowest skinned vertex on each side:

```
LeftToes    1037 verts   lowest y  -0.0917
RightToes   1040 verts   lowest y  +0.0007
```

And the control, on three characters whose bones are symmetric to 0.1 mm:

| character | left foot lowest | right foot lowest | difference |
|---|---|---|---|
| Spartan Mark V | -0.0240 | -0.0240 | **0.0 mm** |
| Power Girl | -0.0115 | -0.0115 | **0.0 mm** |
| Jinx | -0.0003 | -0.0003 | **0.0 mm** |
| **Jessica Rabbit** | **-0.0917** | **+0.0007** | **92.4 mm** |

A correct character puts both feet at the identical height with the lowest
vertex at y ~ 0, so **y = 0 is the floor**. Jessica's right foot is at +0.0007,
exactly where Jinx's is. Her **left foot is 92 mm below the floor** -- she is
buried to the ankle on one side. No authored pose does that.

Her mesh is also symmetric in topology, which is the other half of the answer:
LeftFoot 1733 against RightFoot 1738, LeftToes 1037 against 1040, LowerLeg 676
against 677, LowerArm 1113 against 1114, Hand 445 against 449. A symmetric mesh
whose right half is translated is a displacement; an authored asymmetry would
show in the counts. *(An earlier reading here called her geometry asymmetric,
from the extents rather than the counts. Wrong -- the extents were moving
because the geometry was displaced, not because it differed.)*

~~So the fix direction is known for her legs: her LEFT leg chain is the one in
the wrong place, and it goes up by 92.4 mm.~~ **WRONG, and corrected below.
Her legs are innocent; the fix is one bone's ORIENTATION.**

**Her arms stay open.** Right arm 29.0 mm higher and 74.1 mm further back than
left, with symmetric shoulder bones -- so the displacement is below the
shoulder, but there is no floor for an arm and nothing yet says which side is
right. Her hands' geometry differs by 33.6 mm, and for comparison Jinx's
differs by 14.8 mm on a rig whose bones are symmetric to 0.1 mm, so some
hand-geometry asymmetry is normal and authored.

#### Her legs are innocent. Her HIPS bone is rolled 25.7 degrees

Going to move the left leg, the first thing to check was its local offset
against its mirror. They are the same bone, mirrored:

```
thigh.L local (-0.10646030 -0.02430527 +0.03878002)
thigh.R local (+0.10646027 -0.02430554 +0.03877869)
```

Mirrored to **seven decimal places** in x, and identical in y and z to within
1.3 micrometres. Both hang off the same parent, `spine`, which is her humanoid
**Hips**, at the same scale. Mirrored offsets under a shared parent cannot
produce different world heights -- unless the parent's orientation maps them
there. It does:

```
thigh.L local -> through the parent's rotation -> world (-0.0461 +0.9200 -0.1996)
                                        actual world (-0.0461 +0.9200 -0.1996)
thigh.R local -> through the parent's rotation -> world (+0.1457 +1.0123 -0.1966)
                                        actual world (+0.1457 +1.0123 -0.1966)
agreement 0.0000 mm on both
```

The two local offsets differ by `(+0.21292057, -0.00000027, -0.00000133)`.
After her Hips' rotation they differ by `(+0.1918, +0.0924, +0.0030)`. **The
92.4 mm is produced entirely by the parent's orientation**, and the arithmetic
closes to zero.

The number that says it plainly: **her Hips' local X axis points
`(+0.9009, +0.4339, +0.0142)` in world.** Its sideways axis is tilted
**25.7 degrees out of horizontal**, so a mirrored +-106 mm offset along it
becomes +-46 mm of height -- one leg up, one leg down.

One rolled bone accounts for all of it: the 92.4 mm leg difference, the
-86.5 mm half-body step, her arms' 29.0 mm and 74.1 mm, and
`patch_body_yaw.py` refusing her because her hip and shoulder lines disagree.
**Nothing is wrong with any limb.** The earlier plan in this section -- lift
the left leg 92.4 mm -- would have broken a pair mirrored to seven decimals in
order to compensate for its parent, and left the arms and the half-body step
untouched.

#### And a bundle patch will not fix it

`YargFootProbe` reports each leg bone's world height at instantiate and after
`Rebind()` + `Update()`:

| bone | Jessica before | after | Jinx before | after |
|---|---|---|---|---|
| LeftUpperLeg | 0.9200 | 0.9071 | 0.9787 | 0.9601 |
| RightUpperLeg | 1.0123 | 0.9920 | 0.9787 | 0.9562 |
| **foot height difference** | **92.4 mm** | **94.05 mm** | 0.0 mm | **1.75 mm** |

Two things, and the control supplies both. **The Animator does NOT preserve
positions** -- it re-poses every bone by 2 to 45 mm from the Avatar, on both
characters. And **the fault survives it**: 92.4 mm becomes 94.05 mm. Jinx,
symmetric in her bundle, comes out at 1.75 mm, which is the Animator's own
asymmetry and the noise floor for this measurement.

So the rest pose in the bundle is not what the game draws, and the four-
structure rest-pose patch is the one Master Chief already proved gets discarded
for a MAPPED humanoid bone -- and Hips is as mapped as a bone gets. **This
needs a build-time correction to her Hips orientation and a rebuild**, not a
patch. Her source carries the same roll, so a rebuild from her recipe as it
stands reproduces it; that is why all four of her snapshots agree.

#### Attempted 2026-11-16, and stopped before deforming her

The builder corrects FACING (yaw) and can STAND a character up
(`VRM_STANDUP`), so the first question was whether either reaches this. Neither
does, and the measurements say why.

**There are two different tilts, not one.**

```
Hips -> Head is (-0.0823 +0.5126 +0.0362),  9.95 deg off vertical
the hip line L->R is (+0.1918 +0.0924 +0.0030), 25.71 deg out of horizontal
```

`VRM_STANDUP` aligns hips->head to vertical and then straightens each leg onto
-Z. It would address the 9.95 and **not the 25.71**: straightening a leg makes
it vertical *from its own socket*, and the sockets are what is 92.4 mm apart.
Her feet would stay exactly as unlevel as they are. (Its gate is 25 deg of
SPINE tilt and she reads 9.95, so it never fires for her either -- which this
file already recorded, for her, by name.)

**Her legs are the same length**, thigh to toe 0.997 m on both sides, so
nothing can be blamed on one being short.

So a new step would be needed, and every form of it deforms her:

* **Rotate the hips bone to level the socket line.** Its children are both the
  thighs AND the spine chain, so a 25.71 deg rotation carries her whole torso
  with it. Counter-rotating the spine child by the inverse puts the torso back
  and leaves 25.71 deg of twist concentrated in the pelvis -- her most visible
  silhouette.
* **Translate the left leg chain up 92.4 mm.** Rigid for the leg, but it tears
  the hip join, and it breaks a pair mirrored to seven decimal places.
* **Shorten one leg to reach the floor.** 92 mm on a 997 mm leg is 9%.

This project's own note on the stand-up path says the same thing in advance:
*"straightening a leg is a DEFORMATION and on weights taken from a contorted
pose it is the deformation that tears"*.

#### Is it even visible? Yes -- 67 mm of it

Worth asking before deforming anything, because she wears a floor-length gown.
The lowest vertex of each mesh:

| mesh | what | lowest y |
|---|---|---|
| `Object_2` | the skirt | **-0.0245** |
| `Object_21` | shoe | -0.0917 |
| `mesh_11` | her body | -0.0908 |

Her **right** foot at +0.0007 sits 26 mm *above* the hem and is covered. Her
**left** foot reaches -0.0917, **67 mm below the hem** and 92 mm below the
plane her right foot stands on. So it is not hidden: one shoe hangs out under
the dress and into the podium.

*(A podium render was attempted as a second opinion and produced a blank frame
-- `VRMCharacter init skipped: NullReferenceException` in batch mode. Not
chased; the geometry answers the question quantitatively and the render would
only have illustrated it.)*

**Stopped here deliberately.** The fault is real, visible and precisely
located, but every correction available trades a buried shoe for a distorted
pelvis, and that is a judgement about how she should look rather than a
measurement. Her reported fault -- the dress -- is fixed, and nobody has
reported her leg.

**DECIDED 2026-11-16: leave her.** Put to Jay with the trade-off stated --
a buried shoe against a twisted pelvis -- and the answer was to leave her as
she is. **Do not re-open this and deform her**; the measurements above are
recorded so the next reader does not have to redo them, not as a work item.
If her leg is ever reported, the thing to reach for is a corrected bind pose
in the SOURCE, not any of the three operations ruled out above.

### Miku's 1748 mm is her springs WORKING, 2026-11-17

The limb sweep's still run listed eight characters with a large displacement
and this file called them *"eight characters eject a spring joint at rest"*.
**That was wrong, and the biggest of them is the proof.**

Hatsune Miku (`Miku`) reads **1748 mm** on `Bone10(mirrored)`, growing down
the chain -- 247, 717, 1234, 1748 -- on a chain only 907 mm long. Everything
that would explain an ejection checks out clean:

| | |
|---|---|
| joints starting inside a collider | **0** (`joint_inside_check` subtracts the joint sphere, so this is the real test) |
| gravity | **0.0** on all 9 chains, direction (0,-1,0) |
| wind, root motion | zero, in a corrected still run |
| chain structure | every joint a child of the one before, 133-270 mm segments, no gaps |
| bone scales | all unit, no mirrored negatives |
| colliders | symmetric left to right; nearest surfaces 0.027 vs 0.030 m |
| parameters | 0.60 / 0.45 / 0.020 -- **identical to Jinx**, who reads 0.61 mm |

**So it was rendered twice: once with `-rebind 0`, so the springs never run,
and once normally.** The REST render is the one that looks wrong. Her
twintails are authored **splayed out past her elbows and down to her knees**;
the springs pull them in and up, which is how she should look. The 1748 mm is
the distance from a splayed authored rest pose to a sensible sprung one.

**Nothing is wrong with her, and I had it backwards before the rest render
existed.** Looking at the animated render alone, beside Jinx, I read her tails
as "flung outward like wings". They are the tidy version. A render with no
reference is an opinion.

#### What the still run actually measures

Not ejection. **The distance from the pose the character is INSTANTIATED in to
the pose the solver settles into.** A joint inside a collider contributes to
that; so does a chain whose authored rest pose is simply not where the solver
would put it, and the second case is both more common and far larger.

`YargSpringProbe` now says so in its own output, and its header no longer
claims otherwise. **A big number there is a question, not a finding**, and the
way to answer it is the two renders. On that reading the other seven are
unremarkable settles of 8-37 mm, except Hatsune Miku (Retry Now) at 283 mm,
which has not been rendered and is the only one still worth a look.

### Hatsune Miku (Retry Now ver.): 283 mm is a correct settle, 2026-11-18

The last still-run outlier, and the answer is the same shape as Miku's but for
the opposite reason. **Nothing is wrong with her. Nothing was changed.**

`YargSpringProbe -still` reads **283 mm** from her instantiate pose to her
settled pose on a hair joint. That number cannot distinguish an ejection from
an authored rest pose the solver disagrees with, so it was rendered twice:
once with `-rebind 0`, which leaves her in the pose the bundle ships and
disables the Animator so the springs never run, and once normally.

**Both renders are fine.** That was not one of the two outcomes written down
beforehand, and it is the answer:

* **At rest her twintails already hang neatly** down either side, symmetric,
  close to the body. She was authored near where the solver wants her.
* **Sprung, they hang slightly closer still.** No ballooning, nothing flung
  out, no hair across her face.

So the 283 mm is the small distance between an already-sensible authored pose
and the solver's own. **That is why she reads 283 mm where Miku reads 1748**:
Miku is authored splayed out past her elbows and has a long way to travel,
and this one does not. A large settle means the authored pose was far from the
solver's; a small one means it was near. Neither means a fault.

#### The control is the reason this can be asserted at all

`Miku` was rendered IN THE SAME TWO RUNS, by one build of the harness. She is
the known case. Her rest render shows the splayed twintails this file already
describes, and her sprung render shows them pulled **in and up** -- and since
the Animator cannot move hair, that movement is what proves the spring solver
actually ran. Without her in frame, "both renders look fine" would have been
indistinguishable from "the springs never ran and I am looking at one pose
twice". A render with no reference is an opinion.

(Both runs log `VRMCharacter init skipped: NullReferenceException` equally, so
it is not what separates them; the control is what rules it out as a cause.)

#### A joint inside a collider is not by itself a fault

This is the part worth carrying, because it corrects something this file and
`joint_inside_check_installed.py` both imply.

She has **5 non-anchor joints that start inside one of their own chain's
colliders**, none carrying our shrink guard's 0.950 signature -- they are the
author's geometry, as expected for a downloaded VRoid bundle we never built:

| chain | inside | depth | collider r | r/centre |
|---|---|---|---|---|
| Hair | `J_Bip_L_UpperArm` | **46.4 mm** | 45 mm | **0.450** |
| Hair | `J_Bip_C_UpperChest` | 21.6 mm | 62 mm | 1.530 |
| Hair | `J_Bip_C_UpperChest` | 21.6 mm | 62 mm | 1.530 |
| Hair | `J_Bip_L_UpperArm` | 13.0 mm | 45 mm | 1.412 |
| Hair | `J_Bip_C_UpperChest` | 8.6 mm | 62 mm | 1.160 |

The docstring of that tool describes Gadget Hackwrench: three hair joints in a
0.193 sphere, one **44%** in, ejecting her hair ~100 mm on a head 0.45 wide
until it "ballooned into a mass bigger than she was", and calls that set
"exactly the set that came back looking wrong". The top row here is **45%** in
-- the same signature, near enough to the same number -- **and she renders
correctly.**

The difference is not the ratio, it is **where the collider sits and how long
the chain is**. Gadget's was on the HEAD, where every hair chain converges, and
the ejection was a fifth of the head's width. These are on the upper arm and
upper chest, and the chain is a twintail hanging past the knee, so a ~46 mm
lateral nudge near its root is a small bend in something very long.

So `joint_inside_check_installed.py` reports a real geometric fact and should
keep reporting it -- but **its output is a list of candidates, not a list of
faults**, and severity has to be read as ejection depth against the chain's own
scale and the collider's position. Deciding from the ratio alone would have had
us edit a working character.

#### Not corrected, on purpose

Jay's standing rule is that "not ours" is no reason to leave a fault. It is not
being invoked here, because **the measurement says there is no fault to
correct**: she renders correctly with the springs on and with them off. Editing
the author's colliders to satisfy a threshold she visibly does not need would
risk a working character to tidy a number.

### Animation testing: frames and a contact sheet, 2026-11-18

`YargCharAnim.cs` + `anim_sheet.py`. Renders a character as a SEQUENCE through its
own clip and tiles it into one still image, because a fault that only shows in
motion cannot be caught by the single settled frame `YargSceneShot` produces --
it calls `anim.Update(1.0f)` exactly once.

    Unity -batchmode -quit -projectPath <scratch> -executeMethod YargCharAnim.Run
          -yargchars "<path>|<Name>" -shotDir <out> -frames 12 -step 0.125 -warmup 1.0
    python anim_sheet.py <frames-dir> <sheet.png> <NamePrefix>

**A sheet, not a GIF or a video, and that is the whole design.** The output exists
to be LOOKED at, and a reader that can open a still cannot watch a GIF (it arrives
as its first frame) or a video (not at all). A contact sheet is the motion in one
still, read left to right, beside per-frame numbers.

`-warmup` settles the spring chains before frame 0, so the settle does not land in
the first frame pair and swamp the motion.

#### The control is inside the tool, at both ends

Identical frames are indistinguishable from a character correctly standing still,
and this project has already read a harness's own zero as a finding about five
characters. So `YargCharAnim` counts moved pixels between consecutive frames and
logs `CONTROL OK` / `CONTROL FAILED`, and `anim_sheet.py` checks the same thing
again from the images. Agreeing checks at both ends is deliberate: the failure is
silent at both.

#### Two faults in the measurement, caught by the numbers and not by the pictures

Both were in this tool on its first run, and both are why the numbers matter:

* **THE PODIUM WAS BEING MEASURED AS PART OF THE CHARACTER.** "Largest connected
  component" does not isolate him -- his feet touch the podium, so it returns him
  WELDED TO THE FURNITURE. The tell was two different characters agreeing to the
  pixel: both components ran to y=633 and both had their widest row at y=546. The
  podium is now found from the data by the one property it has and the character
  does not -- it does not move -- and everything below it is excluded.
* **`span` was counting filled pixels in a row rather than measuring its extent.**
  A figure with its legs apart has a gap, so a count under-reads, and it read the
  podium's solid disc as the widest thing in frame. It sat at a constant 217 across
  24 frames and two characters. **A number that never changes looks like a stable
  measurement and is usually a dead one.** Fixed to a real extent, it varies 179-209.

Neither was visible in the renders, which looked fine throughout.

#### First use

Hatsune Miku (Retry Now ver.), 12 frames at 0.125 s, with `Miku` as the control.
Both move (11 of 11 frame pairs). She steps, turns and her twintails swing with
her -- no hair flying, no clipping through her dress. That confirms in motion what
the two static renders said at rest, and it is the check the static renders could
not make.

### The roster swept in motion, 2026-11-18: no character fault, three instrument faults

All 65 installed characters rendered through their idle and ranked by
`anim_sweep.py`. **Nothing on the roster is broken in motion by anything this can
see. Every finding the sweep produced was my own instrument, and each one was
plausible enough to have been written up.**

**Jay: all the in-game idles are THE SAME ANIMATION.** That is what makes this
sweep worth running at all, and it was not known when it was built. One clip
across 65 characters means a difference between two characters cannot be "that
one has a livelier idle" -- the confound the design was braced for does not
exist. Divergence from the population is divergence in the RIG, so the
population median stops being a convenience and becomes the expected behaviour.
It also makes a false positive more dangerous, not less, because every outlier
now looks like a real rig fault.

Coverage, asserted rather than assumed: 65 of 65 logged `CONTROL OK`, 0
`CONTROL FAILED`, 0 `NO ANIMATOR`, 650 frames, 65 distinct prefixes on disk.

#### What the instrument did wrong, in the order it did it

**1. A background cutoff of 18 cut dark costumes in half.** The frames are black
and PNG is lossless, so 18 sounds conservative. A dark costume renders at 13-15.
`silhouette()` then split the character, "largest connected component" returned a
TORSO -- 18,314 px of y 131..331 where the whole figure is 46,000 px of y 75..563
-- and the bottom row of that torso, a WAIST, was measured as feet.

That produced a foot-movement reading of **1.2172 body heights on Inforder
Trogen** and 0.2787 on Elite Terrorist, against **exactly 0.0000 for the other 63**.
Two isolated outliers in a population of perfect zeros, on a shared animation
that moves nobody's feet. It looked like two broken rigs; her sheet even looked
like her lower legs had come off. At a cutoff that does not clip her costume all
65 read 0.0000 and both characters vanish from every list.

**2. A cutoff of 6 still clipped the darkest costume.** With 18 fixed, one
outlier remained and looked solid: **Kaiser Aufhanger at z=22.28**, `area_cv`
0.2031 against a roster median of 0.0208 -- ten times everyone else, with clear
air to second place at 6.78. He has **88,666 pixels in the 1..12 brightness band**.
Sweeping the cutoff is what settled it, because a real motion survives every
cutoff and a flicker does not:

| cutoff | his `area_cv` |
|---|---|
| >2 | **0.0167** |
| >6 | 0.1269 |
| >12 | 0.1572 |
| >18 | 0.0637 |

At a cutoff that captures his costume he sits BELOW the roster median. The
"finding" was his near-black coat crossing my threshold and back.

**3. The metrics are quantisation noise on a character 34 px tall.** With both
cutoffs fixed the top of the list was **Baby Groot, z=7.10 on drift** -- and he
renders at 34 px, 9% of the roster's median height. At that size a few pixels is
a large fraction of his body. Not a fault, and not a scale fault either:
`height_check_installed.py` reads him at **0.348 m** and Yoda at **0.660 m**, both
correct, 0 flagged. (Note the rendered-pixel proxy UNDERSTATED him -- 9% against a
true ~20% -- because the camera is framed for a full-height figure. Rendered px
is not a scale measurement.)

#### What the result actually is

After all three, the ranking is SMOOTH -- 7.10, 6.04, 4.93, 3.55, 3.35, 2.81 --
with no break anywhere. The calibration is what makes that readable: **Miku sits
at z=4.93, and she is independently known to be fine.** A known-good character
outranks most of the list, so nothing on it is suspicious.

#### What this sweep did NOT look at, which is most of what could be wrong

* **It is silhouette-only.** Hair across a face, a hand through a skirt, an arm
  inside a torso -- the outline is unchanged. **Aiko's open fault is exactly this
  class**, so a clean sweep is not a clean roster.
* **One yaw.** Front view only; a fault visible only from the side cannot appear.
* **10 frames of one clip**, and a `-warmup` that settles the springs first.

**The lesson, which is the same one this file keeps writing down:** a threshold
that silently discards data does not report less, it reports WRONG -- and it does
so hardest on exactly the subjects it clips, which here were the characters with
the darkest costumes. Three times the instrument produced a specific, mechanistic,
believable fault about a named character. The thing that broke each one was a
control: 63 perfect zeros making two outliers suspicious, a cutoff sweep, and a
character already known to be fine sitting mid-table.

### RETRACTED 2026-11-18: Power Girl's cape is FINE. I never measured the thing I claimed

**Jay: "I do believe her cape drops, grab some frames from later in the idle
animation." He was right and the finding below is withdrawn in full.** Nothing
is wrong with her cape, nothing should be changed, and the section beneath this
one is kept only so the mistake stays readable.

Measured side-on, pitch of the cape tip from horizontal (0 = straight out
behind, -90 = hanging straight down):

| window | frames | pitch range |
|---|---|---|
| 20 s (`-frames 20 -step 1.0`) | 20 | **-80.9 to -40.2 deg** |
| the 1.35 s I judged it on | 10 | **-83.6 to -41.4 deg** |

Her silhouette area swings **62% of its mean** across the long window. The cape
sweeps 40 degrees, reaching nearly straight down. **It drops, it swings, it
behaves like a cape.**

#### The error was not the sampling window. It was asserting what I had not measured

The first instinct -- "my window was too short" -- is ALSO WRONG, and worth
recording because it is the comfortable explanation. The short window shows a
**42.2 degree** range, slightly WIDER than the long one. The cape was swinging
through forty degrees in the very ten frames I was looking at.

What actually happened: I looked at ten thumbnails on a contact sheet, formed
the impression *"flat and straight through all ten frames, swinging as a rigid
board"*, and wrote that down as a finding. **At no point did I measure cape
pitch.** The four numbers this sweep computes are area, span, jump and drift --
none of them is "is the cape rigid", which is the claim I made.

Then the error compounded in the most convincing possible direction: I went and
built a MECHANISM for it. Read the rest pose, found `gravityPower = 0`, checked
Batman as a control, killed two rival hypotheses with real measurements, and
produced a tidy table showing identical spring parameters and a 40-degree
difference in authored rest pitch. **Every one of those measurements is correct.
They were all downstream of a premise I never tested**, and their quality is
exactly what made the conclusion persuasive.

The rest-pose numbers do still stand as facts -- her cape IS authored at -45 deg
where Batman's is at -85 deg. That difference simply has no consequence, because
the chain does not stay in its rest pose.

#### A second error inside the first: the parameters came from the wrong file

The table below quotes stiffness 0.6 / drag 0.45 "identical on both". That is
from the `.vrm` build intermediates in a scratchpad. **The installed bundles,
which are what the game loads, carry stiffness 0.850 and drag 0.800** on both
characters -- `patch_springs.py` rewrites exactly those fields. `gravityPower`
is 0.000 in both artifacts, so that part held, but I quoted a file the game
never reads. Same class as reading a height in the wrong space.

#### What this costs the rest of the sweep

The roster sweeps above sampled **1.5 s per character**, and every "no fault
found" in them is a statement about 1.5 seconds. On the evidence here that
window is not obviously too short -- Power Girl's cape showed its full range
inside it -- but no one has checked that for the other 64, and the honest
position is that the sweeps are unvalidated beyond their window rather than
clean.

**The rule that would have caught this: if the claim names a quantity, measure
THAT quantity.** A contact sheet is for noticing; it is not evidence for a
mechanical assertion about something the metrics never looked at.

---

#### SUPERSEDED, kept for the record -- the original claim, which was wrong

##### The side yaw, 2026-11-18: Power Girl's cape is a plank, and the obvious fix is wrong

The front-view sweep found nothing. **Adding one more camera angle found a real
fault on the first character it looked at**, which is the argument for the
second yaw in one line.

A second yaw is not more sampling, it is a DIFFERENT AXIS. Head-on, the
silhouette's horizontal extent is the character's WIDTH and depth is compressed
to zero -- so a cape billowing backward, a ponytail swinging forward and a hand
crossing the chest all happen along the axis the camera threw away. At 90
degrees that same extent IS depth.

65 of 65 rendered again at yaw 90: 65 `CONTROL OK`, 0 failed, 650 frames.

#### The finding

**Power Girl ranks z=7.17 side-on against z=0.88 head-on** -- the largest
front/side disagreement on the roster (+6.29). Her cape does not hang. It
projects straight out behind her like a plank, roughly 45 degrees above
horizontal, running off the edge of frame, and stays flat and straight through
all ten frames, swinging as a rigid board rather than draping.

**Batman is the control, and he is why this is readable.** He also has a cape,
also ranks high side-on (5.27), and his cape DRAPES correctly -- shoulders to
below the knee, following his body. Capes can work here. A high side-on score is
not by itself a fault; his is legitimate cape motion.

#### The mechanism, and the two hypotheses it killed

| | Power Girl | Batman |
|---|---|---|
| cape spring chains | 9 x 13 joints | 11 x 11 joints |
| stiffness / gravityPower / drag | 0.6 / **0.0** / 0.45 | 0.6 / **0.0** / 0.45 |
| vertices weighted to cape bones | 2090 | 2184 |
| **cape REST pitch** | **-44.6 to -48.3 deg** | **-84.4 to -89.2 deg** |
| cape tip offset behind | **-1.16 m** | ~0.00 m |
| chain span | **1.75 m** | 1.04-1.31 m |
| height | 1.811 m | 1.889 m |

Both killed hypotheses were plausible and both were wrong:

* **"Her cape mesh is not weighted to the chain"** -- the rigger-matched-its-own-work
  failure this project has hit before. No: 2090 vertices carry real weight on her
  cape bones, against Batman's 2184.
* **"Her spring parameters are wrong"** -- No: they are IDENTICAL to his, to every
  decimal.

What is left is the rest pose. **With `gravityPower = 0` a VRM spring chain has
no force pulling it down**: it answers to root motion and otherwise returns to the
pose it was authored in. Batman's cape is authored hanging (-85 deg), so zero
gravity leaves it hanging. Hers is authored FLARED (-45 deg, tip 1.16 m behind),
so zero gravity leaves it flared, for ever. The springs are working exactly as
configured on both.

This is the same lesson as Hatsune Miku (Retry Now) earlier the same day -- an
authored rest pose the solver will not move -- but here it is visible and wrong.

#### DO NOT "just make it hang". The obvious fix creates a worse fault

Her cape spans **1.75 m on an 1.811 m character**; Batman's is 1.20 m on 1.889 m.
Taking a shoulder at roughly 1.45 m:

| | at 45 deg (as authored) | at 85 deg (like Batman) |
|---|---|---|
| Power Girl | tip at **+0.21 m**, just clear | tip at **-0.29 m**, THROUGH THE PODIUM |
| Batman | +0.70 m | +0.35 m |

**Her 45-degree flare is very likely load-bearing** -- it is roughly what keeps a
nearly-body-length cape off the floor. Re-posing it to hang would trade a stiff
cape for one buried in the podium. (The shoulder figure is an ESTIMATE, not a
measurement; the direction is robust because a 1.75 m cape on an 1.81 m body
cannot hang vertically from the shoulders without reaching the ground, but the
exact tip heights are not measurements.)

So this is **reported, not fixed**, and it is Jay's call. The options are to
shorten the chain, to drop it partway (60-70 deg) and accept a flare, to give her
cape alone a non-zero `gravityPower` with a floor collider, or to leave it. Each
costs something different and none is obviously right.

#### What two yaws still cannot see

Anything INTERIOR. Hair across a face changes the outline side-on only if it
projects past the profile; a hand inside a skirt never does, at any angle.
**Aiko's open fault is still outside this sweep** and still needs its own render.

### Aiko RESOLVED 2026-11-18: it was the alpha queue. Finding 1 confirmed, Finding 2 is latent

Diagnosed by yarg-1 in Blender, rendered here in Unity, which is the half Blender
provably cannot do -- Cycles is a path tracer with no depth-sorted transparency,
so it cannot reproduce a no-depth-write artefact. yarg-1 said so itself and
declined to offer its attempt as evidence.

**The brief I gave it was wrong on two counts and it checked rather than
complied.** I said she needed straightening and offered three candidate causes
that all assumed a bake. She is a **YAW**, not a lean (-29.95 deg, whole body
turned), `straighten_spine.py` has nothing to do on her and was never run; the
hair breaks on a plain rebuild. I also said her `.vrm` was in
`Documents\YARG-Characters`. It is not, and never was.

#### The 2x2, with one cell dropped, and predictions registered BEFORE the run

Her two faults have different signatures IN TIME, which is what separates them:

| build | alphaMode | hair chains | isolates |
|---|---|---|---|
| `aiko-control` | BLEND/BLEND/BLEND | inverted (UP) | both, as rebuilt today |
| `aiko-ALPHAONLY` | OPAQUE/MASK/OPAQUE | inverted (UP) | the chains alone |
| `aiko-RECIPE` | OPAQUE/MASK/OPAQUE | correct (DOWN) | both fixed |
| `Miku` | - | - | known-good yardstick |

Verified independently here before rendering, with tooling written fresh rather
than taking the report on trust -- and the last row is the one that matters:

| build | chains aim | roots vs Head bone |
|---|---|---|
| control / ALPHAONLY | UP x4 | -121.3 .. -106.8 mm (the tips) |
| RECIPE | DOWN x4 | **+80.5 .. +89.0 mm** (the crown) |
| **Aiko.vrm, as shipped** | DOWN x4 | **+80.5 .. +89.0 mm** |

RECIPE does not invent a rig. It recovers the shipped one, on a character who is
now square.

#### FINDING 1 CONFIRMED -- the sheet is a draw-order artefact

`aiko-control` shows the dark sheet over her face **in every frame, frame 0
included**, at both 1.4 s and 20 s sampling. Its stated death -- "if frame 1 is
clean my whole Finding 1 is wrong" -- does not fire. `aiko-RECIPE` is **clean in
every frame** at both windows: face visible, hair on the scalp.

**The CAUSE is measured; the MECHANISM is reasoned, and they are different
claims** (yarg-1 drew this distinction on its own finding and it is right).
MEASURED: aiko-control and aiko-ALPHAONLY differ in alphaMode ALONE, and the
sheet is present in one from frame 0 and absent in the other. One variable.
REASONED, never isolated: that a BLEND material sits in the transparent queue
and writes no depth, so hair behind her head draws over her face. That story
fits every fact and nothing here tested it. The fix does not depend on it being
right, and it must not be written down as though it had been shown.

Two of her three materials went BLEND on an alpha that is opaque at every pixel.

**It is a REGRESSION, not a gap in her recipe.** The honour-the-authored-blend
step landed in `e921bf62` on 2026-11-09; her shipped intermediate is 2026-11-07,
built before it. The claim elsewhere in this file that `GirlsInAction.blend` with
`^Girl2\.[0-9]` "is not her whole recipe" is WRONG -- the recipe is fine and the
builder changed underneath it. Corrected in all three places.

#### FINDING 2 IS LATENT -- real in the file, invisible in the game

`aiko-ALPHAONLY` differs from `aiko-RECIPE` by chain direction ALONE, and across
**both** windows the two are indistinguishable: area range 2.83% vs 2.55% at
1.4 s, and **15.22% vs 15.23% at 20 s**, with her hair staying on her scalp
throughout. By yarg-1's own registered death condition -- "if indistinguishable
from RECIPE across the whole clip, Finding 2 is cosmetic" -- **it is cosmetic.**

The inversion is REAL: independently measured, chain roots sit 107-121 mm BELOW
the Head bone aiming upward instead of 80-89 mm above it aiming down. It simply
has no visible consequence in this idle. Whether it bites in some other
animation is unknown and untested; the honest label is latent, not harmless.

The 20 s re-run exists because the prediction was explicitly time-dependent
("as the clip plays") and the first run sampled 1.4 s of it. After the Power
Girl retraction above, judging a time-dependent claim on a short window was not
a thing to do twice.

#### Not a finding: she renders as bare skin

All three rebuilds show her untextured. **So does the installed bundle that
shipped**, rendered in the same run as the control. That is how the character
is, not a regression, and it is recorded here only so the next person does not
rediscover it as one.

#### Source material rescued

Everything needed to rebuild her -- `GirlsInAction.blend`, textures, her `.vrm`
intermediates -- existed ONLY in a session scratchpad under `Temp\claude\`,
which a cleanup removes. Copied to `build/aiko-source-2026-11-18/` (135 MB,
outside every repo, with a README warning against committing it). yarg-1 found
this and correctly refused to move another session's material unasked.

#### Still not installed

The recipe is verified but nothing has been installed. That is a separate
decision, and `MASK` versus the `OPAQUE` she shipped with has not been compared
by eye.

### Aiko, MASK vs OPAQUE, 2026-11-18: take OPAQUE. And my harness cannot see the thing MTOON_ALL changes

Four builds, **one character geometrically** -- yarg-1 verified 81 of 81 bones to
better than 0.10 mm and 81 of 81 directions to better than 0.05 deg, only the
materials move. That is what makes pixel-differencing legitimate here.

| build | Body | HairFace | Scalp |
|---|---|---|---|
| shipped | OPAQUE PBR | OPAQUE PBR | OPAQUE PBR |
| `aiko-RECIPE-OPAQUE` | OPAQUE PBR | OPAQUE PBR | OPAQUE PBR |
| `aiko-RECIPE` | OPAQUE PBR | **MASK MToon UNLIT** | OPAQUE PBR |
| `aiko-RECIPE-MTOONALL` | **unlit** | **MASK MToon UNLIT** | **unlit** |

**MASK is inseparable from a shading-model change in this builder** -- `mt.enabled`
is driven by `cut or blend` and the exporter will not write MASK unless MToon is
on, which exports `KHR_materials_unlit`. So "MASK vs OPAQUE" was never one
variable and my request for it was not achievable. yarg-1 said so instead of
building what I asked and letting the result look like an answer. It also caught
that my suggested route to the OPAQUE build -- dropping `HairFace` from
`VRM_CUTOUT_MATERIALS` -- yields BLEND, not OPAQUE, which would have
reintroduced the original fault.

#### The numbers

Geometrically identical pair, so the pixels are directly comparable:

| pair | differs in | mean abs diff on the character |
|---|---|---|
| OPAQUE vs RECIPE | HairFace only | **2.91** |
| OPAQUE vs MTOONALL | all three materials | **2.95** |
| MTOONALL vs RECIPE | Body + Scalp, lit vs unlit | **0.047** |

And the torso is **pixel-identical, exactly zero**, between OPAQUE and RECIPE --
which is also the internal check that the comparison is sound, because if the
scene had lit them differently the torso could not match.

Hair edges, measured as the isoperimetric ratio of the head silhouette: MASK is
wispier, stable in direction across every head fraction, **by 0.5%** -- iso 3.967
against 3.943, perimeter identical to the pixel, area differing 277 px in 41,000.
Real, and far too small to see.

**No face or jaw seam.** The Peach configuration does not bite here.

#### THE CONTROL FAILED, and the failure is the finding

yarg-1 pointed out the four builds give a free positive control: OPAQUE is lit
everywhere, MTOONALL is unlit everywhere, neither has a seam, so if a flatness
measure cannot separate those two it cannot have detected a seam in RECIPE
either and a clean reading from it means nothing.

It could not separate them. Torso luminance std 30.446 against 30.437; gradient
2.2954 against 2.2941. **0.03%.**

The instrument is not blind. The PREMISE is false: **under this scene's lighting
an unlit material and a lit one render almost identically on skin**, which the
direct pixel difference confirms independently at 0.047.

**I first wrote that this was a limitation of my harness -- white light being
the least discriminating setting for a lit-versus-unlit question. THAT WAS
WRONG, and yarg-1 caught it by applying my own morning rule to me:** 0.047 on
0-255 is **0.018%**, and that is not "small", it is very nearly exactly
nothing -- the tell for a dead number rather than a steady one. It offered a
rival hypothesis I had not considered: that the unlit flag never reaches the
renderer at all. Both hypotheses predict zero, so the measurement could not
separate them.

**TESTED, and the rival won.** Added `-light r,g,b` and shot both builds under
a pure RED light, where an honoured unlit material must ignore the light while a
lit one takes its colour:

| | (G+B)/R on the torso |
|---|---|
| white light, lit build | 1.6242 |
| white light, unlit build | 1.6242 |
| **red light, lit build** | **1.3881** |
| **red light, unlit build** | **1.3895** |

The light change WORKED -- both moved from 1.624 to 1.388, which is the control
for the mechanism. **And they moved TOGETHER.** An honoured unlit material would
have stayed at 1.624. Both responded, so both render LIT.

**`KHR_materials_unlit` is not honoured in this render path.** So the
lit-versus-unlit trade described above is not real here: `VRM_MTOON_ALL` changes
the exported materials and changes nothing anyone can see, the "two shading
models on her head" risk is moot in this path, and **the Peach row crediting
`VRM_MTOON_ALL=1` is crediting a switch that does not do what it says** -- at
least through this renderer.

WHAT IS STILL UNTESTED: whether the SHIPPED GAME honours it. This is the editor
batch path that every visual check in this project goes through, which is the
point -- any past or future visual conclusion about MToon or unlit drawn from
this harness is suspect by the same argument.

#### The recipe is ONE environment variable, proved by hash not by reasoning

With `VRM_OPAQUE_MATERIALS=HairFace` set, `VRM_CUTOUT_MATERIALS=HairFace` is
INERT -- the force-opaque gate clears whatever the cutout branch did. yarg-1
built it both ways rather than asserting it and the outputs are BYTE-IDENTICAL,
md5 `f24f1d432a813e68844126bc8a0e59ee`:

    VRM_OPAQUE_MATERIALS=HairFace blender -b --python build_vrm.py --       <...>/girls14/inner/GirlsInAction.blend  <...>/girls14/textures       1.70 mixamo Aiko <out>.vrm 1024 '^Girl2\.[0-9]' '' hair

plus the alpha-guard patch. One variable, not two.

#### The seam worry measured out at ZERO, and that is not the same as it not existing

Recording this as yarg-1 asked, because a worry that was checked and came back
zero is worth more than one quietly dropped. **The Peach configuration IS
present in `aiko-RECIPE`** -- two shading models sharing one head, 3,905
HairFace verts unlit against 3,984 Body verts lit, overlapping within
millimetres. It produced **no visible seam on her.**

Both halves matter. The next character with that configuration is not
guaranteed to be as lucky, and Peach IS the case where it went wrong, so this
file must not be read as making her outcome the typical one. It is one
measurement on one character under one light.

#### The missing colliders were a HARNESS fault, and the log said so five times

The pre-install gate stopped the install: the candidate carried **0 colliders**
against the installed bundle's **9 in 1 group**, leaving 4 of 4 hair chains
unguarded. My proposed remedy -- `patch_springs.py --collide` -- was WRONG, and
yarg-1 stopped it before it ran.

Cause: it built from a COPY of `build_vrm.py` in its own scratch directory. The
collider step does `sys.path.insert(os.path.dirname(__file__))` then
`import vrm_colliders`; `__file__` was the copy, that folder had no
`vrm_colliders.py`, the import raised, **a try/except swallowed it**, and the
build exported a valid character with no colliders.

**The log says so in plain words, in all five builds**, and went unread for hours:

    collider setup failed: ModuleNotFoundError: No module named 'vrm_colliders'

**A GREP WRITTEN FROM WHAT YOU EXPECT TO SEE CAN ONLY RETURN WHAT YOU EXPECT TO
SEE.** Every filter run over those logs matched `colliders:`, `hair rig:`,
`material`, `VERIFIED` -- the lines a SUCCESSFUL build prints. A step failing on
every run was invisible to a filter built from the happy path. **The builder in
this repo is FINE**: yarg-1's control, built from today's unmodified file,
failed identically for the same reason.

Measured from the files, which is what settles where her colliders came from:

| file | date | colliders | chains guarded |
|---|---|---|---|
| `Aiko.vrm` (behind the installed bundle) | 2026-11-07 | **0** | 0 of 4 |
| `aiko/Aiko.vrm` | 2026-11-12 | **9 in 1 group** | 4 of 4 |
| today's five builds | 2026-11-18 | **0** | 0 of 4 |

**Her installed nine never came from a build.** The intermediate behind the
shipped bundle has zero; the nine arrived via a separate `add_colliders.py`
round trip, exactly as this file already records for Sayuri and Jessica Rabbit
("that is where her colliders come from"). So the fix is a correct rebuild --
which produces them from the build itself -- not a patch.

#### I ran the same test on my OWN logs, and that is the part to repeat

Grepping my Unity logs for failure vocabulary I had never filtered for returned
**2,379 "shader not found"** and 1,017 "Fallback" -- alarming enough to overturn
the unlit finding committed minutes earlier. They are all Unity's built-in
**Terrain** shaders, benign import chatter, and the unlit-test log is clean with
UniVRM v0.131.0 loaded. **The finding stands -- but only because I looked for
what my filters hid rather than trusting that they had found nothing.**

A related one from the same hour: one of my own scripts **exited 0 having
rendered ZERO frames** after a C# compile error, and the task notification
reported "completed" exactly as on a real run. Wrappers must assert their own
postconditions; an empty result is not a success.

#### CAVEAT CLOSED 2026-11-18: re-tested WITH the colliders, and the verdict holds

The caveat below was recorded, then tested rather than left standing. ALPHAONLY
against RECIPE again, both rebuilt with the **10 colliders** a real install
carries, 20 frames over 20 seconds:

| | area range | span range | cx range |
|---|---|---|---|
| chains INVERTED | 15.14% | 64 | 129.2 |
| chains CORRECT | 15.09% | 75 | 130.8 |

Still indistinguishable, and specifically **no ejection**: if the inverted roots
107-121 mm below the Head bone were being pushed out of the head sphere, area
and span would have GROWN. They did not. Confirmed by eye too -- hair on her
scalp, face clear, all 20 frames.

So the inversion is latent WITH guards as well as without. It remains real in
the file and untested in any other animation; it is not a fault in this one.

#### A caveat this puts on Finding 2 above

The chain-inversion verdict -- ALPHAONLY indistinguishable from RECIPE, therefore
**latent** -- was measured on rigs that had **no colliders at all**. The
comparison is internally valid (both sides lacked them equally), but an inverted
chain whose roots sit 107-121 mm BELOW the Head bone would start inside the head
sphere the collider step fits at about that height. Nobody is claiming the
verdict changes. It was measured without the colliders a real install carries,
and that belongs here now rather than being discovered later.

#### INSTALLED 2026-11-18, and what the gate caught on the way

Installed `aiko-RECIPE-OPAQUE-v2-colliders`, 3,342,003 bytes. Verified AFTER the
copy, against the file now in the game's folder:

| check | before | after |
|---|---|---|
| yaw off square | **-29.95 deg** | **+0.03 deg**, spread 0.15 |
| height | 1.700 m | 1.700 m, 0 flagged |
| colliders | 9 in 1 group | **10 in 1 group**, all used |
| chains unguarded | 0 of 4 | **0 of 4** |
| sheet over her face | present | **gone, all 10 frames** |

Backup at `character-backups/aiko-2026-11-18/Aiko.yargchar.pre-ropaque`, verified
byte-identical before anything was replaced.

**The gate earned its keep twice.** First it stopped the v1 install over missing
colliders. Then, on the verification render, a script edited by `sed` rendered a
STALE bundle under the label `FinalINSTALLED` -- the label said one thing and the
path said another, and reading the label would have "verified" the install
against a file that was never installed. The rerun names the actual path in its
own output and asserts a frame count, so neither can drift again.

#### Recommendation: `aiko-RECIPE-OPAQUE`

It keeps the fix that matters -- the depth-write cure for the sheet over her
face, which is the actual reported bug -- reproduces the shipped look, keeps her
responding to light, and gives up only a 0.5% hair-edge refinement nobody can
see. MTOONALL buys nothing measurable here and costs a property this harness
cannot test. Not installed; the decision is Jay's.

Note what the builder cannot offer: **one shading model, LIT, with cutouts
kept.** MASK requires MToon and MToon exports unlit. So this is a trade between
three imperfect options rather than a fix, and Peach's row should not be read as
making MTOON_ALL the answer in general -- for Peach the alternative was a tan
plate across her brow, here the alternative is the character as she already
ships.

#### A harness artefact worth knowing

The podium's emissive ring renders **purple in one run and cyan in another**. It
is per-instantiation and it is large: it dominated a naive whole-frame band
analysis and produced an apparent difference at 70-100% of the figure's height
that had nothing to do with the character. Any whole-frame metric must exclude
the podium -- `anim_sheet.py` already does, by finding it as the static blob.

### `Documents\YARG-Characters` IS NOT THE INSTALLED CHARACTERS. Not one file matches

Found 2026-11-18 by yarg-1 while checking the Aiko install from its side, and
measured here across the whole store. There are **three** different Aiko bundles
on this machine:

| bytes | where | what it is |
|---|---|---|
| 3,345,402 | `Documents\YARG-Characters` | a build snapshot from **2026-11-07** |
| 3,305,669 | `character-backups/aiko-2026-11-18/` | what was ACTUALLY installed at 00:45 |
| 3,342,003 | the game's `custom/characters` | today's install |

That snapshot is eleven days and three patches behind what was really running:
the 11-12 colliders, the 11-15 shine flattening and the 11-16 reclear are all
absent from it.

**AND IT IS NOT JUST HER.** Compared every `.yargchar` in that store against its
installed counterpart by size:

    identical            0
    DIFFERENT           42
    not installed at all 2
    largest divergence   Doom Slayer, 34,689,963 against 21,532,236 installed

**Zero of forty-four match.** Every file in that folder is a build-time snapshot
from 7-8 November; the installed folder has 65 characters and has been patched
repeatedly since. Anyone who reads that store as "the installed character" is
comparing against the wrong artefact **every single time**, and will get a clean,
confident, wrong answer.

This is the same failure as reading a spring parameter out of a `.vrm` build
intermediate when the shipped bundle carries different values, and as a render
labelled `FinalINSTALLED` that loaded a stale path -- all three happened in one
day. **The installed folder is the only artefact that answers "what is in the
game".** The store is useful as build output and as nothing else.

#### REFRESHED on Jay's instruction, 2026-11-18

The 44 stale bundles were backed up first, then the folder was refreshed from
the installed characters.

    backed up    44 bundles, 446 MB, to character-backups/yarg-characters-store-2026-11-18/
                 every one verified byte-identical to its source before anything was written
    copied in    65 installed bundles
    verified     0 mismatches of 65 -- the store now matches the game byte for byte

**Deliberately NOT touched**, because the point was the staleness and not a
clear-out:

- the **25 `.vrm` build intermediates** (807 MB) -- the irreplaceable part, and
  the reason this folder exists at all;
- `README.md`, the `.blend`, and the `backup-2026-11-13-sidedness` DIRECTORY
  (65 files, 575 MB, an earlier snapshot);
- **two bundles that exist only here** and have no installed counterpart --
  `Junio Sonic.yargchar` and `Shadow the Hedgehog.yargchar`. Installed has a
  differently-named `Sonic.yargchar`, so these are older or alternate builds and
  deleting them would have destroyed the only copy.

The store is 67 bundles now: the 65 installed plus those two orphans.

Note the folder's own `README.md` always said *"Installed copies live in
%USERPROFILE%\AppData\LocalLow..."*, so it never claimed to BE the installed
set. The trap was not the folder lying; it was that the two had silently
diverged to the point where nothing matched, and a reader checking "what is in
the game" against the nearest convenient copy got a confident wrong answer 44
times out of 44.

### The real reason `VRM_MTOON_ALL` does nothing to an installed character, 2026-11-18

Chased because yarg-1 and I disagreed on a detail and only one of us could be
right about the file. **Neither of us was wrong. We were reading different
artefacts, and the second fact is much bigger than the first.**

| artefact | what it carries |
|---|---|
| `aiko-RECIPE-MTOONALL.vrm` | MToon present, `shadeColorFactor` == `baseColorFactor` == (1,1,1) |
| `AikoMTOONALL.yargchar` -- **OUR EXPORTER'S BUNDLE** | `_BaseColor, _Color, _EmissionColor, _SpecColor` -- **standard Lit. NO MToon properties at all** |
| `Hatsune Miku (Retry Now ver.).yargchar` -- downloaded | `_ShadeColor, _OutlineColor, _RimColor, _MatcapColor` -- the full MToon set |

**OUR EXPORTER DOES NOT CARRY MToon THROUGH TO THE BUNDLE.** `VRM_MTOON_ALL=1`
writes MToon into the `.vrm` and the Unity export turns it into a standard
shader. yarg-1's shade==base observation is true of the intermediate and MOOT:
a real shade colour would not survive the export either.

The corroboration was already on the table and neither of us had joined it up:
of the **6 installed bundles carrying MToon, all six are downloaded and none is
ours**. That is not a coincidence about which characters need toon shading --
it is what "our exporter drops MToon" looks like from the other end.

**So `VRM_MTOON_ALL` is inert for anything WE build and install** -- which is
what I originally guessed, for an entirely different and wrong reason. The
switch is not ignored by the renderer; it never reaches the renderer, because
the bundle build does not preserve it.

Consequences worth carrying:

- **Peach's recipe row crediting `VRM_MTOON_ALL=1`** is crediting something that
  cannot survive our export. This file already hedged that row for a different
  reason -- her recorded arguments describe a build that was never installed.
- **A toon-shaded character cannot currently be BUILT by us**, only downloaded.
  If one is ever wanted, the exporter is where the work is, not the builder.
- MToon itself renders fine, proven on the downloaded bundles -- see the
  correction below.

### CORRECTED 2026-11-18: MToon DOES render. My "unlit is not honoured" was unsupported

Checking Hatsune Miku (Retry Now ver.) overturned my own finding from earlier
the same day. **MToon renders correctly in this path. Nothing below it about
`VRM_MTOON_ALL` "doing nothing anywhere" should be relied on.**

#### What was wrong with the test

I shot two builds under a red light, saw both take the colour, and concluded
`KHR_materials_unlit` was being dropped. **MToon IS A LIT SHADER** -- it has a
shade ramp. So "both responded to light" is equally consistent with *MToon
rendering correctly*, and my test could never have told MToon-lit from
standard-lit. It was the wrong discriminator and I read a null from it as a
finding.

#### What actually shows

Rendered Miku (Retry Now, 23 of 23 MToon) beside our own Miku (no MToon at all):
hers is **flat, cel-shaded, with crisp anime shading**; ours has **gradient
falloff and specular highlights**. A plain visible difference, in the direction
MToon predicts.

And the mechanism, read from the materials -- MToon's visible effect is the gap
between `_Color` and `_ShadeColor`:

| bundle | MToon materials | with a REAL shade colour |
|---|---|---|
| Hatsune Miku (Retry Now ver.) | 23 | **7** -- hair base(1,1,1) -> shade(0.00,0.80,1.00), delta **1.000** |
| `aiko-RECIPE-MTOONALL` | yes | **none -- no `_ShadeColor` written at all** |

**That is the whole explanation for the 0.047.** `VRM_MTOON_ALL` on Aiko
produced MToon materials carrying no shade colours, so MToon had nothing to
draw and the result matched PBR. Not because the shader was ignored -- because
the builder gave it nothing to work with. A different claim with a different
consequence: the switch is not useless, it is incomplete on a character whose
source has no toon shading to carry over.

**So the 6-of-65 list below stands as a FACT and its interpretation does not.**
Those six carry MToon and it renders; they are not "rendering lit where their
authors intended otherwise".

#### A fourth false zero on the way to this

The colour reader that produced the table above returned "no shade/base pairs"
on its first run, for a bundle I had **already measured** as carrying
`_ShadeColor` on all 23 materials. The entries are TUPLES `("_Color", {...})`
and it was reading `e.get("second")`. The earlier measurement is the only
reason the zero was not believed -- a known positive beside the zero, again.

### The unlit finding, BOUNDED: 6 of 65, all of them downloaded, none of ours

"Any past visual conclusion about MToon or unlit from this harness is suspect"
was true and unbounded. yarg-1 narrowed it to 8 candidate recipes from the
README; the installed bundles -- the only artefact that can answer -- narrow it
further. `mtoon_sweep_installed.py`, 65 bundles, 65 readable, 96 distinct
material property names seen:

| character | MToon materials |
|---|---|
| Adachi Rei | 39 of 45 |
| Inforder Trogen | 26 of 26 |
| Kaiser Aufhanger | 24 of 24 |
| Hatsune Miku (Retry Now ver.) | 23 of 23 |
| Harq Alkahana | 18 of 18 |
| Hatsune Miku (Dark) (Retry Now ver.) | 14 of 14 |

**Six, and they are exactly the DOWNLOADED VRoid bundles this file already
lists as not ours.** Not one character WE build carries an MToon material --
including **Peach, the only one documented as built with `VRM_MTOON_ALL=1`**.
That is consistent with what this file already admits about her: her recorded
arguments describe a build that was never installed, and she was fixed with
`patch_springs.py` rather than rebuilt.

So the blast radius is six author-made bundles, and the practical consequence
is theirs: they are authored with MToon and this render path does not honour
`KHR_materials_unlit`, so they render lit where their authors intended
otherwise. Nothing we built is affected, because nothing we built has an MToon
material to begin with.

#### The first version of this sweep returned a confident, meaningless ZERO

It read the shader NAME off each material. A bundle references shaders it does
not contain, so `m_Shader.read()` throws, a `try/except` swallowed it, and the
sweep reported **"0 of 65 carry MToon"** having read no shader at all.

**Its own control is what caught it**: zero MToon is plausible, but zero
DISTINCT SHADER NAMES across 65 characters is impossible if the read worked.
The rewrite matches MToon's distinctive material PROPERTIES instead, and prints
the property-name count beside the result so the same failure cannot return
silently. Third instance in one day of a wrapper reporting success about
something it never read.

### Why nothing we build carries MToon: OUR OWN EXPORTER remaps every material, 2026-11-18

"Nothing we built has an MToon material to begin with", above, is true, and it reads like a
property of the models we convert. It is not. It is one `Shader.Find` in our own exporter.

`YargCharExporter.cs` does this to every material on every renderer:

    var urp = Shader.Find("Universal Render Pipeline/Lit");
    ...
    if (urp == null || src.shader == urp) continue;
    var nm = new Material(urp) { name = src.name + "_urp" };

and then copies a FIXED LIST of properties onto the new material: `_BaseMap`/`_MainTex`,
`_BaseColor`, `_BumpMap`, `_MetallicGlossMap`, `_EmissionMap`. Every material is rebuilt as
URP/Lit unconditionally. `_ShadeColor`, `_ShadingToonyFactor`, `_ShadingShiftFactor`,
`_RimColor`, `_OutlineColor` and `_MatcapColor` have nowhere to go and are discarded BY
CONSTRUCTION -- not dropped by glTF, not by Unity, not by the bundle format.

So `VRM_MTOON_ALL=1` is not doing nothing. It does exactly what it claims to the `.vrm`, and
then the Unity export stage throws the result away. That is why the intermediate and the
bundle disagree, and it is the fourth artefact-layer divergence recorded in this file.

**The remap is not there for shading at all.** Its own comment says what it is for: a fresh
URP/Lit culls back faces, the Standard material the glTF import produces has no cull property
to carry the source's intent, and single-sided sheets -- a hair fringe, an ear, an eye plane --
vanish from the side their normals face away from. It is a CULL AND ALPHA fix. Flattening the
shader is a side effect of how that fix was built, not its purpose.

#### RETRACTED, and it is my own text one section up: "a bundle references shaders it does not contain"

That sentence is false, and the inference resting on it did the damage.

Measured, three bundles, with a type histogram as the control -- zero distinct types would
mean the read failed, so the numbers below are not a silent zero:

| bundle | Shader objects CARRIED | materials whose shader resolves in-bundle |
|---|---|---|
| Hatsune Miku (Retry Now ver.) | 3 | 23 of 23 |
| Hatsune Miku (Dark) (Retry Now ver.) | 3 | 14 of 14 |
| Aiko (ours) | 3 | 3 of 3 |

Every bundle CONTAINS its shaders. What actually fails is reading `m_Name` on a bundled
Shader -- it comes back EMPTY -- and an empty name was read as an absent object. The real name
is in `m_ParsedForm.m_Name`, and with that:

    Hatsune Miku (Retry Now ver.)  ->  VRM10/Universal Render Pipeline/MToon10
    Aiko (ours)                    ->  Universal Render Pipeline/Lit

**The consequence is the entire point.** If a shader lived outside the bundle, shipping MToon
ourselves would depend on the GAME BUILD carrying MToon -- and it does not: MToon is absent
from `m_AlwaysIncludedShaders` (three built-in shaders are listed, and nothing in
`ProjectSettings/` mentions MToon at all). The false premise therefore produced the
discouraging answer. In fact the character carries its own shader, the one Miku carries is the
URP variant that already ships in the `com.vrmc.vrm` package in this project
(`MToon10/Shaders/vrmc_materials_mtoon_urp.shader`), and the game build never needs to know.

An empty string is not a failed read, and "not here" is not the only thing a blank name can
mean. Two conclusions in one day rested on that, in opposite directions.

#### What this establishes, and what it does NOT

MEASURED: the loss is ours, and it is one unconditional remap at a known line; bundles are
self-sufficient for shaders; the MToon URP shader is already in this project; a downloaded
MToon character resolves entirely in-bundle.

NOT MEASURED, and required before anyone says we can ship a toon-shaded character: **nobody
has built one.** Preserving MToon through the exporter must still deliver the cull and alpha
intent the remap exists for. MToon carries its own cull and alpha modes, so it is probably
expressible -- but "probably" is not a measurement, and the history in this file is mostly of
plausible things that turned out not to be true. Build one, render it, and compare it against
a downloaded MToon character before writing a conclusion here.

### YARG_KEEP_MTOON: the exporter CAN preserve MToon. Built one, 2026-11-18

Opt-in, because 59 installed characters and 40 working alpha cutouts were all built by the
flattening path and a default-on change would move every one of them at once.

    YARG_KEEP_MTOON=1  blender-built .vrm  ->  Unity export  ->  .yargchar on MToon

PAIRED BUILD, same `.vrm`, same arguments, only the flag differing, so the difference cannot be
the source:

| | shaders carried | materials | kept |
|---|---|---|---|
| `AikoMToonCONTROL` (flag off) | `Universal Render Pipeline/Lit` | 3 -> Lit | **0** |
| `AikoMToonKEEP` (flag on) | `VRM10/Universal Render Pipeline/MToon10` | 3 -> MToon | **3** |

Sidedness still carried, via `_M_CullMode`, and the log NAMES the property it used. MToon10-URP
spells cull `_M_CullMode` while MToon0X spells it `_CullMode`, and `SetFloat` on a property a
shader does not have is a silent no-op -- no throw, no warning -- so a sidedness fix written the
obvious way would report success having done nothing.

Most of the Lit path turns out to be MOOT for MToon rather than needing translation. MToon has no
specular and no environment reflection, which is the entire reason `YARG_NO_SHINE_MATERIALS`
exists; and base colour, normal, emission, shade, rim, outline and matcap are already correct on
the imported material. **Copying is what loses them.** The Lit path copies five slots and
discards the rest by construction.

#### The import produces MToon, not Standard -- the file's own comment was wrong

A `source shader` log line now prints for every material, and it settles a question that had been
guessed at: UniVRM registers `[ScriptedImporter(1, "vrm")]`, so a `.vrm` arrives as REAL MToon
materials. The exporter's comment calling them "the Standard material it was imported as" is true
of a Blender glTF and false of an MToon VRM -- and that wrong comment is what made the flattening
look unavoidable.

#### THE VARIANT IS AS LOAD-BEARING AS THE SHADER, and this cost a build

The first working build rendered a FLAT MAGENTA SILHOUETTE. The importer hands back
`VRM10/MToon10` -- the BUILT-IN pipeline shader -- and this project is URP.

| | magenta pixels |
|---|---|
| ours, built-in MToon10 | **37.39%** |
| ours, after forcing the URP variant | **0.56%** |
| URP/Lit control, same `.vrm` | 0.00% |
| Hatsune Miku (Retry Now ver.), downloaded | 1.97% (her dress, confirmed by looking) |

That bundle **built cleanly, loaded, and CARRIED its shader** -- `bundle_shaders.py` passed it
without complaint. A built-in surface shader simply has no pass URP will run.

**"The shader is in the bundle" and "the shader works" are different claims, and only a render
separates them.** The bundle-level check added earlier the same day would have shipped a magenta
character with a green tick.

The fix assigns `VRM10/Universal Render Pipeline/MToon10` -- one property block between the two
variants, so every value carries. If that shader is ever missing the exporter logs an error and
falls through to URP/Lit rather than ship magenta, and the log says explicitly not to read the
absence of magenta as the flag having worked.

#### WHAT IS NOT PROVEN: she renders, but she does not look toon

Measured in the BUNDLE, which is the artefact that matters and the layer neither of us had
checked -- the `.vrm` reading was taken this morning:

    _ShadingToonyFactor 0.900   _ShadingShiftFactor -0.200   26 float + 6 colour properties
    _Color == _ShadeColor == (1.000, 1.000, 1.000) on ALL THREE materials, delta 0.000

So the MToon property block survives fully populated -- the preservation is real -- and Aiko has
**no shade-to-base gap to show**. MToon's visible effect IS that gap. She is mechanically ideal
for this test and visually mute, and her render differs from the Lit control mainly by the absent
specular.

**A toon-shaded character has therefore NOT been demonstrated.** What has been demonstrated is
that the pipeline no longer destroys the information needed for one. Proving the look needs a
character with an actual shade colour, which is a different build.

#### A GREEN RUN ON DIRTY STATE IS NOT EVIDENCE THE STEP WORKS

Found on the way: `YargCharExporter` created only the leaf `Work` folder and assumed
`Assets/__TempExport` existed. `AssetDatabase.CreateFolder` returns an empty GUID rather than
throwing when its parent is missing, so there was no folder, no error, and a
`DirectoryNotFoundException` three lines later on the `File.Copy` -- **a failure that accuses its
own input**, reading as "the .vrm is missing" when the .vrm was fine.

It had therefore NEVER worked on a clean project. It passed only because a previous run left the
folder behind, while the standing instruction for this pipeline is to delete `Assets/__TempExport`
after every run. The cleanup and the exporter contradicted each other, and the contradiction was
invisible to every individual run because nobody did both in the same session.

#### CORRECTION: `VRM_CUTOUT_MATERIALS` on Aiko is OVERRIDDEN, not inert

Rebuilt from source rather than quoted from a note, because both original artefacts had been
deleted and the surviving logs carry no checksum:

    opaque-only         md5 f24f1d432a813e68844126bc8a0e59ee   2,736,540 bytes
    opaque-plus-cutout  md5 f24f1d432a813e68844126bc8a0e59ee   2,736,540 bytes

Byte-identical, and matching the size of the deleted `aiko-RECIPE-OPAQUE.vrm`, so the recipe is
deterministic. But the build logs differ: with the flag, `HairFace` takes the CUTOUT branch and
reads the base map's own alpha, and `VRM_OPAQUE_MATERIALS` then erases the difference downstream.

> With `VRM_OPAQUE_MATERIALS=HairFace` set, `VRM_CUTOUT_MATERIALS=HairFace` is OVERRIDDEN, not
> inert: it still selects the cutout branch and still touches the base map's alpha, and the
> force-opaque switch downstream erases the difference. Output is byte-identical
> (md5 `f24f1d432a813e68844126bc8a0e59ee`, 2,736,540 bytes). **Equal output under one
> configuration is not equal behaviour.**

The distinction is load-bearing, not pedantic. "Inert" invites the next person to drop the flag as
a no-op -- and the moment anyone removes `VRM_OPAQUE_MATERIALS` to try MASK, which is the obvious
next experiment, the cutout flag becomes the thing deciding her hair, through a branch that
reaches for a texture on a dead `F:` path.

**A MEASUREMENT IS ONLY AS DURABLE AS THE ARTEFACT IT WAS TAKEN FROM.** Deleting an input silently
converts every number derived from it into a recollection. A provenance table that maps
measurements to surviving carriers is the right instrument, and this one still slipped through it,
because a checksum has no filename and so looks like a fact rather than a measurement needing a
carrier.

### Two hazards for anyone building an instrument in this project, 2026-11-18

Both were hit the same afternoon, from opposite ends, by two sessions working on unrelated
problems. Neither announced itself.

#### THIS PROJECT IS URP, AND BUILT-IN-PIPELINE MACHINERY FAILS SILENTLY IN IT

Three separate shapes of the same trap, all measured:

  - `Camera.RenderWithShader` is a **NO-OP under URP**. It does not fail and does not warn --
    the camera just renders normally, with the real materials. A depth probe decoded that colour
    frame as depth and got a confident, plausible, entirely fictional depth map: pale skin
    decoded to ~1.0 and read as "no geometry", the dark podium decoded to ~0 and read as "the
    nearest surface in frame". It LOOKED like a depth map.
  - A **built-in-pipeline shader assigned as a material** under URP draws NOTHING, silently. The
    obvious fix for the above turned the fiction into a blank.
  - A **built-in-pipeline shader inside a bundle** renders FLAT MAGENTA. `VRM10/MToon10` built,
    bundled, loaded and passed a shader-name check; it has no pass URP will run.

> **AN INSTRUMENT THAT IS NOT RUNNING DOES NOT NECESSARILY PRODUCE NOTHING.** It can produce
> output that passes every check except "did the mechanism run".

Log the active render pipeline at instrument startup, and make anything built-in-RP announce
itself rather than degrade quietly.

#### CHOOSE A CONTROL ON MECHANISM, NOT ON PROVENANCE

Twice in one day a control was picked because the artefact came from the fault's HISTORY --
"this is the build that was installed when the fault was reported" -- rather than because it
carried the fault's CAUSE. Both times the control was a perfectly good artefact that simply did
not contain the thing being measured, so it returned a TRUE number answering a question nobody
had asked:

  - A positive control that pushed hair TOWARD the camera, for a probe whose entire job is to
    ignore geometry that is genuinely in front. A zero would have read as a broken probe and
    invited "fixing" a correct instrument. Under the measurement it replaced, that bad control
    would have PASSED.
  - A pre-fix character used as a real-artefact positive, when that build had already been
    flattened to OPAQUE and never carried the BLEND hair material that causes the fault. The
    sentence ruling it out was already written in the author's own note.

The failure is specific and worth naming because it does not look like a failure: the numbers
can support a coherent, well-evidenced wrong explanation. In the second case the aux-half bone
counts genuinely did support "the probe is blind on this rig" -- and the frames showed the face
was clear, so the near-zero reading was simply CORRECT. **The numbers agreeing with a wrong
explanation is the condition under which almost everyone stops looking.**

Ask of any control: does this artefact CARRY THE CAUSE? Provenance is not mechanism.

And the narrower rule, which is the half that nearly cost more:

> **WHEN YOU HAVE AN EXPLANATION FOR WHY A CONTROL FAILED, THAT IS THE MOMENT THE CONTROL NEEDS
> CHECKING -- NOT THE MOMENT IT IS EXPLAINED. A good explanation for a null is how a null
> survives.**

The bone-count story was GOOD: `PREFIX Neck=9838/auxTris=1865` against `FIXED Neck=7960/auxTris=2987`
really is consistent with "more hair sits on a humanoid bone in the older build, so it lands in
the body half and cannot violate" -- a real mechanism, real numbers, right direction. Accepting it
would have written a LIMITATION INTO THE TOOL THAT DOES NOT EXIST, and that invented limitation
would then have explained away the failure of the bad control, protecting it from scrutiny.

What killed it was opening two PNGs and seeing the face was clear.

#### A measurement that changes when nothing changed is the furniture

A conservation check reported a 1,888 px discrepancy and it was read as a transparency
signature. The same character then read 0, 1,899 and 0 across three runs with nothing altered.
It was the PODIUM. `anim_sheet.py` locates the podium from the data and excludes it; rendering
the subject alone on a private layer is the better fix, and both characters then read exactly 0.

### Jessica Rabbit RE-OPENED 2026-11-18, and her top ranking is not what it looked like

Jay re-opened her after the interior-fault probe put her WORST on the roster: 0.1085, z=8.5, on
her chest and along the dress slit over her thigh.

**TWO NUMBERS IN THE FIRST VERSION OF THIS SECTION WERE WRONG AND ARE CORRECTED HERE.** I wrote
"5,675 violating pixels". 5,675 is the `overlap px` column — the DENOMINATOR, pixels where body
and aux overlap on screen — and the column is labelled that. I misread a correctly-labelled
column and then repeated the figure twice. **Her actual flagged pixels are 598**, about 0.2% of a
512 frame, in 25 components averaging 24 px. Her case is far smaller than the first write-up
made it sound.

**THE CORROBORATION WAS AGAINST A STALE LINE IN THIS FILE.** The finding was supported by the
playtest row reading "dress static while the body moves" -- a fault FIXED on 2026-11-16, whose
own fix is recorded in this same document 376 lines further down. Read in the shipped bundle
rather than in the README: `Object_1`, 24,035 verts, her bodice, sits on **9 bones including
`breast.L` (15.6%) and `breast.R` (12.1%)** -- the post-fix state exactly. The fix is installed.
The row has been struck.

> A DOCUMENT THAT RECORDS A FAULT AND ITS FIX 376 LINES APART WILL BE READ AS RECORDING THE
> FAULT. Strike the original where it sits; do not rely on a later section to correct it.

**AND SHE HAS NO BLENDED MATERIALS AT ALL.** `alpha_sweep_installed.py` on the shipped bundle:
**opaque=11**. Every one. Nothing in her fails to write depth.

That matters because the probe's stated mechanism is that `BLEND` does not write depth, so
geometry behind composites over the body in front. **She cannot produce that mechanism, and she
is the top row by a factor of 1.5.** So either the probe measures more than it claims --
interpenetrating OPAQUE geometry gives near-coincident depths along the intersection curve, where
which surface wins is arbitrary -- or it has a false-positive mode on opaque geometry. Those are
different findings and the roster ranking means different things under each. A prediction
committed before looking: under the first, her violation pixels should lie on a THIN CURVE where
two surfaces cross; a filled region would favour the second.

**THAT PREDICTION FAILED AND INTERPENETRATION IS NOT SUPPORTED.** Erosion test on the painted
frames — strip one pixel from the boundary and a curve 1-3 px wide nearly vanishes while a blob
keeps its area:

    Jessica Rabbit   (11 opaque mats)  n=598  retained(1px) 0.510  25 components, largest 239
    AikoCONTROLBLEND (3 BLEND mats)    n=469  retained(1px) 0.663  13 components, largest 340

0.510 against a curve threshold of 0.25. Her pixels are not a curve, and their shape is CLOSER
to the known draw-order positive than to an intersection line. It does not establish the
false-positive branch either — 0.510 sits between the two expectations and the known positive
only reaches 0.663, so the discriminator is weak. **The mechanism behind her score is
UNIDENTIFIED.** Ruled out so far: transparency (she has none), backface culling (tested, moved
the numbers the wrong way), and a clean interpenetration curve.

A method note that nearly cost the test: the obvious way to extract the violation mask is to
select the marker colour the frames were painted with. **HER COSTUME HAS GREEN ON IT.** The mask
was taken by differencing the painted frame against the plain one instead, which is exact.
Selecting on the marker would have measured her dress and returned a confident number either
way.

> **THE RANKING IS NOT EVIDENCE OF FAULTS.** It is a list of characters where something the probe
> reacts to is concentrated, and on opaque geometry that something is still unidentified.

**WHY SHE MAY BE A REAL FINDING ANYWAY, stated as a hypothesis.** Her dress is fixed, but her
**right leg is still 92.4 mm higher than her left**, from a Hips bone rolled 25.71°. That is the
fault this file closed as "leave her", on the grounds that every available correction trades the
buried shoe for a twisted pelvis. A thigh 92 mm out of place inside a correctly-rigged skirt
interpenetrates it -- **at the dress slit, which is where the probe found it**. If that holds, the
closure was decided on an incomplete symptom list: it weighed a buried shoe against a twisted
pelvis and did not know the same bone also pushes her leg through her dress.

**The test that would have connected her leg to the probe's score is the one that just failed**, so
the leg is NOT folded into the probe result and remains a hypothesis with one measurement behind
it.

**The re-opening still stands, on its own terms.** The 92.4 mm displacement is measured, open, and
the worst limb-height fault on the roster at double the next. Its closure weighed a buried shoe
against a twisted pelvis. Whether that trade is right is worth re-reading — but on the leg's own
evidence, not on a probe score whose mechanism is unidentified.

#### A README ACCUMULATES STATEMENTS BUT NOT THEIR EXPIRY

Two stale-row incidents from this one file in a single day, one each. A recipe row read as a fact
about an installed bundle; and a fault row sitting 376 lines above the row recording its own
repair. The common shape is that **the newest fact about a character is not where you look for
it** — the file grows by appending, so the oldest claim is the most prominent and nothing marks
it dead.

Strike superseded text WHERE IT SITS, in the same edit that records the new finding. A later
section that corrects an earlier one only works for a reader who reaches it.

### The interior-fault sweep ANSWERED: no character shows a large one, 2026-11-18

> **MARKER LIFTED. THE NULL SURVIVED THE CORRECTED INSTRUMENT AND IS STRONGER FOR IT.** It was
> marked provisional for an hour on the report that "every reading went up" — and that report
> was itself wrong. See "A RATE IS NOT A COUNT" below: the rates rose because the DENOMINATOR
> fell, while the violating pixels themselves fell 19% roster-wide. The marker was still the
> right action on the information available, and is recorded rather than deleted.

The roster was swept for the one fault class every other instrument here is blind to -- geometry
wrongly occupying another part's space, which no silhouette measure can see. 65 characters, all
harness controls clean, 46 measurable by the depth-order test and 19 held out and then proven
safe. **The answer is a NULL, and it is usable only because the positive control passes beside
it.**

#### MOST OF THE RAW RANKING WAS A SYMMETRIC CONFOUND

The probe flags "aux visible where the body is geometrically nearer". The puzzle was that 44 of
46 characters showed some violation while most carry NO transparent material at all -- and
without transparency every surface writes depth, so the stated mechanism cannot fire.

The thing that cracked it was already in the control numbers:

    AikoCONTROLBLEND (broken)  forward 0.381922  reverse 0.107492   ratio 3.55
    Aiko (fixed, clean)        forward 0.005191  reverse 0.015033   ratio 0.35

**THE CLEAN CHARACTER READS THREE TIMES HIGHER IN REVERSE THAN FORWARD.** A character with
nothing wrong should read near zero in both directions. Reverse exceeding forward is the
signature of a process that is not a draw-order fault at all -- and SSAO, cast shadows and
anti-aliasing all qualify, because each changes the shading of a surface that WAS ALWAYS SHOWN,
at the boundary, regardless of which side is nearer. A real draw-order fault is directional; a
shading confound is not.

So rank on FORWARD MINUS REVERSE and the symmetric part subtracts out. It cost no render time:

    forward-dominant  19 of 46        reverse-dominant  27 of 46

| character | asym | fwd | rev | ratio | rank |
|---|---|---|---|---|---|
| Lola Bunny | 0.0696 | 0.0740 | 0.0044 | 17.0 | 2 -> **1** |
| Yoda | 0.0504 | 0.0516 | 0.0013 | 41.0 | 4 -> **2** |
| Jessica Rabbit | 0.0478 | 0.1013 | 0.0536 | **1.89** | **1 -> 3** |
| Batman | 0.0437 | 0.0469 | 0.0032 | 14.5 | 6 -> 4 |
| Gordon Freeman | 0.0209 | 0.0648 | 0.0439 | **1.48** | 3 -> 7 |

A MAJORITY OF THE ROSTER BEING REVERSE-DOMINANT is the confirmation: a large symmetric component
was sitting in the raw ranking. **Jessica Rabbit is nearly symmetric at 1.89**, so roughly half
her forward signal is matched in reverse and most of what put her top was confound. She falls to
third and her probe case is weaker again.

This also made the SSAO experiment unnecessary. Disabling screen-space effects would not have
touched cast shadows or AA, so a null would have cleared nothing -- while the asymmetry
correction subtracts all three at once WITHOUT needing to name which.

#### THE ANSWER (CONFIRMED by the corrected instrument — see below)

**No character on this roster shows a large interior fault.** The worst directional reading is
0.07 of the body/aux overlap, edge-concentrated, on a character with no transparent material. A
genuinely broken artefact reads 0.38 forward at ratio 3.55. The new leader, Lola Bunny, is a THIN
LINE ALONG ONE EAR EDGE, about 119 px -- her ears are aux geometry on non-humanoid bones and the
signal traces their boundary.

#### AND A NAMED LIMITATION THAT COULD ACCOUNT FOR THE ENTIRE RESIDUE

Subtracting symmetric confounds does not subtract a DIRECTIONAL one, and there is a directional
one by construction: **the aux half is typically OPEN, SINGLE-SIDED geometry** -- hair cards,
cloth, Lola's ears -- **while the body is a CLOSED mesh**. The depth pass runs Cull Off, so for
open aux it records whichever side is nearest INCLUDING A BACKFACE THE RENDERER NEVER DRAWS,
while for a closed body it cannot. That bias points one way and survives forward-minus-reverse
untouched. The Cull Back run moving magnitudes by up to 1.74x is consistent with it.

So Lola Bunny's ear line is exactly what a sidedness mismatch predicts AND exactly what a real
ear-ordering fault predicts, and nothing measured so far separates them. The test that would:
match **each material's OWN cull mode** in the depth pass instead of forcing one globally. That
is a build, not a read.

> A NULL FROM AN INSTRUMENT WITH AN UNQUANTIFIED DIRECTIONAL BIAS IS WORTH LESS THAN THE SAME
> NULL FROM ONE WITHOUT. The residual here is small and edge-shaped; the reason to resolve it is
> not Lola's ear, it is that this probe will be pointed at future characters and its nulls have
> to mean something.

#### The sidedness hypothesis is DEAD, and the instrument is better anyway

The directional limitation named above — open single-sided aux against a closed body, with the
depth pass running Cull Off — was tested by matching **each material's own cull mode**.

THE STOP CONDITION HELD, which was the real risk of the change: a depth pass that agrees more
closely with the renderer could suppress the genuine signal as easily as the bias.

    AikoCONTROLBLEND  global Cull Off  forward 0.374791  ratio 4.01
                      per-material     forward 0.415679  ratio 4.15   UNMOVED, slightly stronger
    synthetic positive still monotonic, and over a WIDER range than before

**And the hypothesis failed. Nobody fell — every reading went UP.**

| character | before | after | cull modes |
|---|---|---|---|
| Jessica Rabbit | fwd 0.1013 r1.89 | fwd 0.1877 r2.07 | **mixed** (Back=20, Off=2) |
| Batman | fwd 0.0469 r14.5 | fwd 0.0798 r16.6 | |
| Lola Bunny | fwd 0.0740 r17.0 | fwd 0.0823 r5.00 | Back ONLY |
| Yoda | fwd 0.0516 r41.0 | fwd 0.0634 r33.5 | Back ONLY |
| Aiko | fwd 0.0052 r0.35 | fwd 0.0038 r0.38 | |

So sidedness does not account for the residue, which remains unexplained. The instrument is
nonetheless more correct, because the depth pass now sees the faces the renderer sees.

> **AN EXPERIMENT IS NOT TESTING WHAT ITS NAME SAYS UNLESS THE THING IN ITS NAME ACTUALLY
> VARIES.** Lola Bunny and Yoda report a SINGLE cull mode, Back. For them "per-material cull"
> was simply global-Off to Back, with no per-material variety involved at all. Only Jessica
> Rabbit is genuinely mixed — and she moved most. Without a log of the cull modes actually
> found, the change would have been credited for movement it did not cause on most of its own
> subjects.

Lola's ratio falling 17.0 to 5.00 is the one figure not to over-read: her overlap denominator
also collapsed, 1,609 px to 486, so both halves of the fraction moved — and hers was already
the row flagged as noise-prone on a small denominator.

#### A RATE IS NOT A COUNT, and quoting one as the other cost an hour

The alarm that "every reading went up by roughly 1.7x" was true of the RATES and FALSE of the
COUNTS. Split across all 46:

    median ratio NEW/OLD
      violation FRACTION   1.165
      violating PIXELS     0.904   <- the NUMERATOR FELL
      overlap DENOMINATOR  0.641   <- the denominator fell much further
      total violating px   3,714 -> 3,025   (-19% roster-wide)

**The fractions rose BECAUSE THE DENOMINATOR SHRANK.** Backface culling removes aux surfaces
from the depth map, so the region in which an ordering decision exists AT ALL got smaller
faster than the violations did. The more correct instrument finds FEWER violating pixels, which
is the opposite of the story its rates tell.

AND IT PUT AN ARTEFACT AT THE TOP OF THE NEW TABLE. Gordon Freeman jumped 7th to 1st on
asymmetry at ratio 13.33 — while his violating pixels went **81 to 40, halved**. His overlap
collapsed 1,156 to 261, so the fraction doubled because the denominator quartered. Lola Bunny
is the same shape: 121 to 40 pixels on a denominator falling 1,632 to 486.

> **A RATIO WHOSE NUMERATOR AND DENOMINATOR BOTH CHANGE IS TWO FINDINGS WEARING ONE NUMBER.**
> So the third answer to "did the ranking rescale or reshuffle": IT RESHUFFLED, AND THE
> RESHUFFLE IS THE DENOMINATOR MOVING, NOT THE SUBJECTS.

**A fraction is not comparable across instrument VERSIONS when the instrument moves the
denominator.** Within one sweep it remains the right cross-character statistic — it is the only
scale-free one between a 1.9 m character and a 0.9 m one — but any row whose overlap is a few
hundred pixels is noise, and that now includes the top row. `MIN_REGION_PX` guards the face
region; **the overlap denominator has no equivalent guard and should.** That is a defect in the
tool, not a caveat about this run.

> **FIXED 2026-11-18.** The guard is built, in both tools, and what it does to this run is
> written up under *The denominator guard* below. Read that before re-using any number above:
> the headline is that **the guard changes none of the figures in this section**, which is a
> result about this roster and not a reason the guard was unnecessary.

#### FINAL: the null, on the corrected instrument

**No character on this roster shows a large interior fault, and the corrected instrument makes
that MORE certain.** Roster-wide violating pixels fell 19%; the largest single-character count
is about 590 px on Jessica Rabbit; the strongly directional rows are 40-100 px at edges. A
genuinely broken artefact reads 0.42 forward at ratio 4.15. Both controls passed BEFORE the
sweep, in that order.

Four candidate causes for the residue are ruled out: **transparency** (rho 0.11), **symmetric
confounds** (26 of 46 reverse-dominant after subtraction), **interpenetration** (shape test
failed), **sidedness** (fixing it REDUCED violations rather than removing them). What remains
is 3,025 px across 65 characters, at edges, nothing above ~590.

**STOPPING HERE IS THE RIGHT CALL.** The remaining signal is smaller than the uncertainty in
how to count it, and the next honest step is the denominator guard — not another hypothesis.

#### The 19 hold-outs are provably safe, re-verified from the bundles

The depth-order test held out 19 of 65 for having **no aux half** — every triangle dominantly
weighted to a humanoid bone. That reason is derived from *rigging*, but the fault is a property
of *materials*: rigid hair weighted hard to `Head` on a blended material fails identically and
is just as invisible to a bone-based split. So "held out" never meant "rigid, therefore safe".

`holdout_triage.py` separates the two by reading `_Surface` from each installed bundle: **SOUND**
if no material sits in the transparent queue (no draw-order fault can exist whatever the
rigging), **HIDING** if one does. The answer is **19 SOUND, 0 HIDING, 0 unreadable**, and it has
now been produced twice — once in the original sweep, once re-run on 2026-11-18 after both the
sweep's `part_overlap.json` and its `AikoCONTROLBLEND` control bundle had been deleted. The tool
therefore accepts a **name list** as well as a JSON (`holdouts-2026-11-18.txt`): a tool whose
only input no longer exists cannot re-verify its own published result.

**The control is the tool's now, not the operator's**, and it is the strongest form available,
because the field under test exists on this roster: `_Surface == 1.0` is found on 19 materials
across 9 non-held-out characters (Adachi Rei, Alcina Dimitrescu, Alice Ivy, Ariel, Gordon
Freeman, Heels, Pomni, Prix, Sayuri). So a hold-out reading zero is a fact about that character.
The tool refuses to publish a verdict if the control finds nothing, prefers `_Surface == 1.0`
over the weaker `_AlphaClip` fallback, and counts key **presence** separately — 141 of the
roster's 535 materials carry no `_Surface` key at all, so a reader treating a missing key as zero
would call a quarter of the roster opaque while measuring nothing.

Roster census, measured: **65 bundles, 535 materials, 19 transparent on 9 characters, 25 cutout
on 10.** That corrects a "40 working alpha cutouts" figure this repo's own exporter comment
carried, and the claim beside it that every installed character was built by our export path —
6 of the 65 carry MToon, which the exporter cannot produce, so those were downloaded.

> **The separation was already done when it was proposed as the next task.** The sweep note said
> "the two cases are not separated here" and answered it 86 lines later; a coordinator read the
> first sentence and proposed the work. The line is struck in place rather than deleted, because
> a stale line reads exactly like a current one and this document had already been bitten the
> same way by a playtest row quoted 376 lines above its own repair.

#### The denominator guard

Built 2026-11-18, in `part_overlap.py` (`overlap_floor`, `guard_overlap`) and used by
`asymmetry_rank.py`. Covered by `overlap_guard_test.py`.

**The floor is derived, not chosen.** One pixel of a fraction over `N` px is worth `1/N`. The
ranking is done in robust-z units whose unit is the MAD, so when `1/N` exceeds the MAD a single
pixel moves a row by more than a whole z and the rate is quantised more coarsely than the scale
ranking it. That is not a noisy row, it is an unrankable one, and `ceil(1/MAD)` is where it
starts. The floor is then held at no less than the run's own `MIN_REGION_PX`, because guarding
one denominator at 200 px and the other at nothing is an inconsistency in the direction that
flatters the result.

**On this run the derived bound would have been WEAKER than the one we already had.** Median
0.012829, MAD 0.007560, so `ceil(1/MAD)` = 133 px against `MIN_REGION_PX` = 200. The 200 binds
and the output says so in those words — a derivation that let a reader think the population
chose 200 would be false, and at 200 px one pixel is worth 0.66 of a z, which is coarse but
genuinely rankable. The derived bound only binds on a tighter population; on the `asym` scale,
whose spread is narrower, it derives 222 px, so **the two tools disagree about a row at 210 px
and that disagreement is kept** rather than reconciled by a shared constant nobody derived.

**What it changes here: nothing.** No character in the ranking has a denominator below 200 px —
Gwen Stacy is the smallest at 262 — so the table, the ranking and the null all stand exactly as
recorded above. The guard is for the next sweep. Saying this plainly matters more than the guard
does: a new cutoff that arrives alongside an unchanged conclusion is very easy to describe as
having confirmed it.

**What it changes about how the table READS is the actual gain.** Every ranked row now carries
`viol_px` (the numerator) beside `overlap_px` (the denominator), and `z/px`. Gwen Stacy's fifth
place reads **14 violating pixels over 262 px at 0.51 z/px** — her position is three pixels wide,
visible in the row instead of recoverable only by a reader who knows which column is which. That
is the same confusion that produced `5,675` being reported three times as a violation count by
the person who wrote the column; the fix for a unit error is to print both units, not to
remember harder.

**Held out, never dropped.** A row below the floor gets a `depth_out` reason naming its own
pixel count and appears in the existing *HELD OUT — unmeasured, NOT clean* list. The output also
names which rows the guard removed **and the rank each held ungated**, because a guard that
quietly removed the top row is the one case that changes a conclusion. It deliberately does NOT
print a column of rank shifts: removing rows cannot reorder the survivors, so every row below a
removal shifts up one and a "moved" marker fires on all of them — the first version printed nine
such markers, not one of which was a real change in relative order.

**Two passes, reported, never a silent loop.** The floor comes from the population it then
filters, so it is re-derived on the survivors and the output says whether it moved. It is not
re-applied at the new value: a floor that moves when its own filtering is undone is a floor
partly chosen by the rows it removed, and that is a fact for the reader, not something to
iterate away.

**Verified against a synthetic fixture, and that is a limitation.** The real
`part_overlap.json` no longer exists — not anywhere under `C:\dev` to depth 7, checked with a
control for a file known to be present before concluding it. So `overlap_guard_test.py` builds a
run that **reproduces the recorded median and MAD**, and *asserts* that it does rather than
claiming it in a comment: the first version centred the filler on 0.012829 and landed the
population at 0.0147, because the eight high rows pull the median up, and its own check caught
that. The fixture is not that sweep and cannot re-measure any character. `--null-guard` stubs
the guard out and the three hold-out assertions go red while every control stays green, so the
suite has been seen to fail.

#### What it still cannot see

Everything the brief said it could not: this is a rendered-view test, so geometry hidden from the
camera at every sampled frame is unmeasured, and the idle is one animation. The 19 hold-outs are
proven free of transparent material, which rules out draw-order faults on them specifically --
it does not make them faultless.

### The limb-capsule sweep, 2026-11-17

Closed. The open item read *"every character built before 2026-11-15 still
carries MEDIAN limb capsules ... not swept"*, which is true of the files and
badly overstates the work.

**35 of the 65 have no spring chains at all.** A limb capsule exists only to
deflect a spring joint, so on those 35 it is inert whatever its radius, and
`patch_springs.py` refuses them by design. Nine more are already right
(Alice Ivy, Batman, Heels, Killer Clown, Lola Bunny, Peach, Sayuri, Tenna,
Yoda). That leaves **21 characters and 194 limb resizes**, median +11.7 mm.

Every shrink among them was clipped by the clearance guard -- none came from
the percentile -- and the one refusal is Hatsune Miku's left upper arm, where
a spring joint's own sphere reaches the bone axis.

**What the still run says.** Zero wind, no root motion, so any displacement is
a collider ejecting a joint: **0 characters worse, 1 better, 20 unchanged to
0.01 mm**. The better one is Inforder Trogen, **33.15 -> 8.34 mm**, where the
guard cut capsules that had been swallowing his own joints. `YargCharLoadTest`
reads old and new identically on all 20 comparable pairs -- clips, humanoid
bones, skinned meshes, bones, chains and joints.

**Alcina Dimitrescu is HELD, on an a-priori reason rather than a measured
regression.** She passes every check, and p90 on her legs is her GOWN: her
thigh goes 0.111 -> 0.207 and her shin 0.091 -> 0.199, against flesh whose
median is already inflated by the same dress. This file named her for exactly
this when the percentile was chosen -- *"her lower leg has its furthest vertex
at 0.401 ... that vertex is her dress"* -- and for her the median is the
closer approximation of a leg. Her still run is 0.10 mm either way, so nothing
is lost by leaving her.

#### Two instruments were wrong, and both were caught by their own output

* **`patch_springs.py` reported a missing file as "has no spring chains".** The
  list of characters to patch was generated by a helper whose output picked up
  CRLF, so every path carried a trailing `
`; all 21 reported no spring
  chains, Prix and her five among them, and the run wrote nothing while
  looking like a finding about the roster. It now checks `os.path.isfile`
  first and names the likely cause.
* **`YargSpringProbe -still` was not still.** It prints *"no root motion, so
  any displacement is a collider ejecting a joint"* while setting a 14 m/s
  wind from the `-wind` default, so every chain was being blown about. A still
  run now gets no wind unless `-wind` is passed, and prints the vector either
  way. **Re-running with the wind at zero reproduced all 21 figures to two
  decimals**, which says the external force was never reaching the solver at
  all -- so the numbers were sound, and the file's own header claim that wind
  "is the way to deflect a chain" is not.

~~**Eight characters eject a spring joint at rest**~~ -- **WRONG, corrected
below the same day.** They do not. See "Miku's 1748 mm is her springs working",
2026-11-17.

### Kronk leans because his source was mid-dance, 2026-11-17

Straightened and installed. He is the OTHER case from The Mandalorian, and
having both is what makes either legible.

**His lean is in the geometry as well as the bones.** The mirror fit reads his
lower body at -6.10 mm and his upper at +31.10 (bones -3.00 and +27.92, so
geometry and bones agree to ~3 mm), and his silhouette in the podium render
puts his head 45-80 mm to his right of his torso where Spartan Mark V reads
0.0. So the BAKED straightening is right for him -- the one that threw Mando's
helmet 50 mm off, because Mando's body was plumb and only his bones leaned.

**Where it came from.** His source is `Kronk_Doing_the_Hokey_Pokey.usdz` -- a
model mid-dance. The builder bakes that static pose as the rest pose
(*"keeping a static pose on 86 bones ... this is the model's shape, not a stray
frame"*), and the T-pose step then squares his LIMBS and never touches the
spine. His arms come out 0.0 degrees off X and his limb segments mirror to four
decimals, while the spine keeps the dance. So the lean is the uncorrected
remainder of a correction this pipeline already half-made, which is why
finishing it is restoring intent rather than deforming an artist's work.

**Rebuilt from source**, because he has no `.vrm` intermediate. The rebuild
reproduces the shipped bundle's lean exactly -- range 57.0 mm, every bone
matching to 0.1 mm -- shifted by a uniform 16.9 mm, which is the centring step
that did not exist when he was first built. That uniform offset IS the control:
it says the rebuild is the same character.

| | installed | rebuilt (control) | straightened |
|---|---|---|---|
| skeleton spread | 57.0 mm | 57.0 mm | **13.4 mm** |
| geometry lean (lower → upper plane) | 37.2 mm | — | **9.6 mm** |
| spine plumb? | no | no | **yes, 4.9 mm at every joint** |
| height | 1.950 m | — | 1.947 m |

Installed as 1,490,455 bytes, sha256 `af6ff1a36b38`; backup
`Kronk.prestraighten-2026-11-17.yargchar` (sha256 `3b07ad858bd9`). Load test
reads old and new identically: 38 humanoid bones, 1 skinned mesh, 105 bones,
`humanoid=True`, 0 failed.

The residual 13.4 mm is his arms at -6.7 mm against his legs at +6.7 -- they
genuinely do not share a centreline, and `--recentre` splits the difference so
neither is favoured. Before straightening they were 30.9 mm apart.

#### Two defects in `--recentre`, both caught by its own re-measure

Worth recording because the first one would have shipped a broken rig.

* **It translated the OBJECTS** while measuring in ARMATURE space, so the
  measurement could not see its own operation. It printed `-15.78 mm` before
  and `-15.78 mm` after -- honest, and only because the re-measure existed.
* **Moving every edit bone one at a time is not a rigid translation.** A
  CONNECTED bone's head is pinned to its parent's tail, so moving the parent
  moves the child, and moving the child again gives it TWICE the offset. The
  exported bundle had his **Chest 15.8 mm adrift of his Spine and Head, and his
  feet 15.8 mm adrift of his knees** -- while the four bones the re-centre
  aimed at read a clean `-0.00 mm`. **A check that re-measures only what the
  operation targeted will pass while the operation has broken everything else.**
  The replacement asserts that EVERY bone moved by exactly the offset, and it
  was watched failing first: with the disconnect removed it names `n78` moved
  -31.556 mm against -15.778, which is 2x to three decimals.

### The Mandalorian is NOT two half-skeletons -- CORRECTED 2026-11-16

**Everything in the section below this one is wrong, and so is the check that
produced it.** He has no step. His spine LEANS, 37.2 mm from feet to head,
about 3.3 degrees, and it is inherited from his source. The measurements are
kept because the correction is only legible beside them.

#### What the old check could not see

`half_body_check_installed.py` reported "-18.5 mm for hips, knees and feet,
+18.7 mm for shoulders, elbows and hands, to a tenth of a millimetre, with no
gradient between them". The agreement is real and it is worthless: **its six
pairs are the legs and the arms, and nothing in it lies between them.** On a
standing figure the three leg pairs inherit the hip bone's X rigidly; on a
T-posed figure the three arm pairs inherit the shoulder's. Six numbers which
are two numbers, measured three times each. "No gradient between them" was
written off a check with no sample between them.

`plumb_check_installed.py` walks the SPINE and prints X at every height:

```
    height   what                       x (mm) vs the one below
    0.0871   pair   Foot                 -18.5
    0.9766   pair   UpperLeg             -18.5         -0.0
    1.0330   spine  Hips                 -14.0         +4.5
    1.1332   spine  Spine                 -5.3         +8.8
    1.2518   spine  Chest                  1.3         +6.5
    1.3877   spine  UpperChest             7.5         +6.2
    1.4543   pair   Hand                  18.7        +11.2
    1.4543   pair   UpperArm              18.7         -0.1
    1.5193   pair   Shoulder              12.7         -6.0
    1.5408   spine  Neck                  13.7         +1.0
    1.5686   spine  Head                  16.7         +3.0
    range 37.2 mm over 11 bones; largest single gap 11.2 mm -- A LEAN
```

Every gap is 4.5 to 11.2 mm and the largest is 30% of the range. **Spartan
Mark V reads 0.0 at all eleven heights**, so the instrument returns a true
zero. **Kronk is the same and worse: 57.0 mm, also spread** -- so two of the
three characters this file called "two halves" are not that, and the third
(Jessica Rabbit) should be re-read before anyone acts on her.

#### The reported fault is real, and it is this lean

Reported as his armour not being centred on his chest. It is not the armour:
on the podium render his pauldron midpoint and his knee-plate midpoint are
about 35 mm apart, which is the lean, measured in the picture. **His armour is
coherent with itself.** Fitted independently, the helmet shell's own plane of
symmetry is **-8.6 mm** and the chest plate's is **-8.0 mm** -- two separate
pieces, two separate fits, agreeing to 0.6 mm. Nothing is skewed inside him;
his whole upper body stands to his right of his hips.

The plate's BOX centre is +22.9 mm against that plane, which looks like a
contradiction and is not: his chest plate genuinely extends further on one
side than the other, and a box centre measures the extent while the fit
measures the symmetry. Reading the box alone would have produced a confident
"the plate is 23 mm off" and sent the fix to the wrong place.

#### It is inherited, and that was measured rather than assumed

The source mesh (`Mando_for_mixamo.fbx`) and the shipped bundle contain the
same connected islands -- the vertex counts match one for one. Matching the 25
whose count is unique in both and fitting a robust line through source centre
against bundle centre gives **median |residual| 2.06 mm**, and the chest
plate's residual is **+4.6 mm**: ordinary. Our pipeline moved nothing. (The
two large residuals, +375 and -337 mm, are the forearm armour, which the
T-pose step moves on purpose.)

#### Why a whole-body mirror fit cannot help here

`mesh_mirror_installed.py` fits a plane to the SURFACE, sampled by area rather
than at the vertices. On Spartan Mark V every one of his six meshes reads
**x = +0.00 mm with a 0.75 mm residual**, and lets the plane turn as well as
slide he reads **-0.00 degrees**. On The Mandalorian no mesh gets below 5.5 mm
and the curves barely climb: he wears a cape over one shoulder, a bandolier
across his chest and a holster on one thigh, and **no plane mirrors him**.
That is a fact about the character, not a failure of the tool, and it is why
the answer had to come from individual armour pieces instead.

The first version of that tool ran on VERTICES and was useless for the same
question in a different way -- Spartan read 0.00 mm because his mesh is
mirrored vertex for vertex, and Mando read 23 mm on a curve flat to within
1 mm over +-5 mm, which is a low-poly mesh being measured with a ruler made of
its own edge length. Sampling the surface puts the floor where the tool
chooses it rather than where the tessellation does.

#### What a fix would cost, and why it was not made

Straightening him means rotating each bone of the spine chain so the chain
runs vertical. That is a deformation of the torso -- the class of operation
this file ruled out for Jessica Rabbit on the same day -- and it reaches a
3.3 degree lean that the artist put there. `VRM_STANDUP` already does exactly
this operation and **its gate is 25 degrees of spine tilt**, so it does not
fire for him and should not: it exists for characters that are falling over.

It also cannot be patched into the bundle. Every bone in that chain is a
MAPPED humanoid bone, and a rest-pose patch of one of those is discarded by
the Animator (Master Chief, four structures written, byte-identical result).
So it needs a rebuild -- and **his Mixamo-rigged FBX is not on this machine**.
Downloads holds `Mando_for_mixamo.fbx`, the input, and four `T-Pose*.fbx` that
all predate it. Rebuilding him means re-uploading to Mixamo and re-rolling the
whole rig, which changes everything else about him to correct 3.3 degrees that
his source already had.

**Put to Jay 2026-11-16 with those numbers, and he said try it.**

#### Tried, 2026-11-17: it works on the skeleton and does not show

Straightening was attempted and it is BUILT, not fixed, because the result
does not justify replacing a working character without Jay saying so.

**A rebuild turned out to be available after all.** `Mandalorian.vrm` is in
`%USERPROFILE%\Documents\YARG-Characters` -- the build intermediate, same 150
bones with the same names (`n29`..`n185`) at the same heights, X negated as
Blender/VRM always is against Unity. So no Mixamo round trip was needed; the
correction goes into the VRM and back out through `YargCharExporter`.

**The claim the day before that his rig was not on this machine was WRONG, and
this file already said so.** "Reach is bounded by what still exists — but by
MORE than the scratchpad" names that store and counts its 25 VRMs, a thousand
lines above, as a correction to an earlier claim that 35 characters had
"neither source nor VRM". Searching Downloads for a Mixamo FBX, not finding
one and concluding no rebuild was possible walked straight back into the
mistake this file had already corrected once. **Check
`%USERPROFILE%\Documents\YARG-Characters` before calling a character
unrebuildable**; names differ between the two stores, so match case by case.

`straighten_spine.py` (new) poses the spine joint by joint onto vertical,
iterated, and `--keep` restores the arms' and legs' original ORIENTATION at
their new positions so the limbs ride the correction without tilting. The
hips joint has to be IN the chain -- it is the steepest, 8.76 mm over 100 mm --
and leaving it out gets 37.2 mm only to 24.4.

**Three builds, because `--control` is what makes the other two readable:**

| build | skeleton spread | chest plate plane | helmet plane |
|---|---|---|---|
| the shipped bundle | 37.2 mm | -8.0 mm | -8.6 mm |
| `--control` (round trip, no correction) | **37.2 mm** | **-8.0 mm** | -9.6 mm |
| baked (body straightened with the bones) | **5.9 mm** | -24.3 mm | **-58.6 mm** |
| `--no-bake` (bones moved inside the body) | **5.9 mm** | **-7.7 mm** | **-8.8 mm** |

The control measures the shipped bundle **identically** -- every bone to
0.1 mm, mesh extents equal to four decimals (-0.0590..+1.8294) -- so the trip
through Blender costs nothing and the differences below are the correction.

**Baking is the WRONG operation for him and the numbers say why.** It takes
the skeleton plumb and throws his HELMET 50 mm to one side, visibly, in the
rest render. That is because his body is ALREADY plumb and only the bones lean
inside it: his limb geometry is centred on its bones to a millimetre or two,
while his chest plate sits 9 mm and his helmet 25 mm to one side of the bones
that carry them. Rotating the body with the bones therefore tips a body that
was straight.

**`--no-bake` is correct and invisible.** Same plumb skeleton, geometry
untouched by construction and measured so, rest render indistinguishable from
the current one, and his two foot bones come level as a bonus (0.0972/0.0770
to 0.0875/0.0867). It also costs nothing: no spring chains exist on him to
lose (the shipped bundle has none, despite the cape note in his recipe).

**But it does not show.** Rendered on the podium in the ANIMATED pose -- what
the game draws -- the current build, the `--no-bake` build and even the baked
build are indistinguishable. And `YargYawProbe` moves barely at all: hips
5.28 to 4.88 degrees, shoulders -5.82 to -5.87, against Spartan's 0.00
control. That probe reads a TWIST and the fault is a sideways lean, so it was
the wrong instrument and says only that nothing got worse.

#### INSTALLED 2026-11-17, on Jay's call

Re-exported from `MandoSKEL.vrm` under the name `The Mandalorian`, load-tested
and installed as **10,056,662 bytes, sha256 `b04cdeb907a3`**, backup
`The Mandalorian.prestraighten-2026-11-17.yargchar` (sha256 `93e23bcb18e6`,
10,046,538 bytes). The `--no-bake` build is the one that went in; the baked one
is kept beside it in `character-backups/mando-straighten-2026-11-17/` as the
record of what the other reading of "straighten" does.

Read back off the installed file, with Spartan Mark V in the same run:

```
The Mandalorian                          Spartan Mark V (control)
  Foot        -13.6                        Foot        -0.0
  UpperLeg    -13.6                        UpperLeg    -0.0
  Hips        -14.0                        Hips        -0.0
  Spine       -14.0                        Spine       -0.0
  Chest       -14.0                        Chest       -0.0
  UpperChest  -14.0                        UpperChest  -0.0
  Hand         -8.1                        Hand        -0.0
  UpperArm     -8.2                        UpperArm    -0.0
  Shoulder    -14.2                        Shoulder    -0.0
  Neck        -14.0                        Neck        -0.0
  Head        -14.0                        Head        -0.0
  range 6.0 mm                             range 0.0 mm
```

**37.2 mm to 6.0 mm, and the armour did not move**: chest plate plane -8.00 to
-7.70, helmet -8.60 to -8.80. `YargCharLoadTest` reads the old and the new
bundle identically -- 52 humanoid bones, 4 skinned meshes, 150 bones,
`humanoid=True`, 0 failed -- the bundle still calls itself
`the mandalorian.yargchar` with 155 GameObjects, and the podium renders at
yaw 0 and yaw 35 are indistinguishable before and after.

**A trap in the verification, worth knowing.** `height_check_installed.py`
reads him as **1.828 m before and 1.888 m after**, and `--strict` re-derives
the same figures from the vertices, so it is not a stale `m_LocalAABB`. He did
not change size: his SKINNED WORLD extents are identical to four decimals
(-0.0590..+1.8294) before and after, and his on-screen silhouette occupies the
same rows in both renders. What changed is the mesh's own LOCAL space -- the
VRM round trip rescales the vertices and compensates in the bind poses, which
leaves world positions untouched. The `--control` build shows the same 1.888
while being world-identical to the shipped bundle, which is how this was
separated from the correction. **Do not read a height change out of that tool
across a VRM round trip without checking the world extents.**

### SUPERSEDED: the old "two half-skeletons" write-up, 2026-11-16

Reported as his armour not being centred on his chest. It is not the armour.

`half_body_check_installed.py` reads the WORLD positions of the pairs the
Avatar itself calls left and right, and reports each pair's separation, each
pair's centre, and the segment lengths down each limb:

```
Hips       lower  left  -0.1576  right  +0.1206  sep  0.2782  centre   -18.5 mm
Knees      lower  left  -0.1576  right  +0.1206  sep  0.2782  centre   -18.5 mm
Feet       lower  left  -0.1576  right  +0.1206  sep  0.2782  centre   -18.5 mm
Shoulders  upper  left  -0.1979  right  +0.2352  sep  0.4331  centre   +18.7 mm
Elbows     upper  left  -0.4432  right  +0.4805  sep  0.9237  centre   +18.7 mm
Hands      upper  left  -0.6888  right  +0.7262  sep  1.4150  centre   +18.7 mm
```

Every lower pair centres at **-18.5 mm** and every upper pair at **+18.7 mm**,
to a tenth of a millimetre, with **no gradient between them**. His limbs are
near perfect: arm segments 0.2453/0.2456 against 0.2453/0.2457, legs
0.4590/0.4304 against 0.4590/0.4307. That is not a lean and not a twist. It is
a **37.2 mm step between two half-skeletons** -- which is what his recipe
predicts, since his source glTF has two collapsed skeletons and he was
re-rigged through Mixamo.

**Nothing shows at rest, and that is why four earlier measurements missed it.**
`part_bones_installed.py` says his raw and skinned vertex positions agree to
four decimal places, so the geometry sits exactly where the bones put it; and
slicing the body by height gives x-midpoints wandering +-20 mm with no
structure, which is min/max noise and not a finding. The fault is that the
bones are in the wrong place INSIDE the geometry. His chest pivots about an
axis 18.7 mm off the centreline his legs define, so everything the chest
carries swings off-centre **the moment he is animated** -- the same shape as
"a fault only animation shows".

**The Animator is not the mechanism, and only a control could say so.**
`YargYawProbe` after `Rebind()`:

| | as instantiated | after Rebind |
|---|---|---|
| The Mandalorian | 5.28 / -5.82 | 9.25 / -14.24 |
| **Spartan Mark V** (known good) | **0.00 / 0.00** | **4.56 / -7.96** |
| Steve | 12.04 / -6.23 | 18.42 / -14.65 |

Spartan is square in his bundle and still reads 4.56 / -7.96 after Rebind, so
the Animator adds about +4.7 deg of hip and -8.4 deg of shoulder yaw to
everybody. Mando's excess over that control is exactly his instantiate value.
Read without Spartan, his 9.25 / -14.24 would have been written up as the
Animator wrecking him.

#### Three characters, and two that only look like them

**Two of the three are now known not to be.** The Mandalorian and Kronk both
read as LEANS once anything is sampled between the legs and the arms; see the
corrected section above. Jessica Rabbit has not been re-read with
`plumb_check_installed.py` and her -86.5 mm should not be acted on until she
has been.


| character | step | legs | reading |
|---|---|---|---|
| **Jessica Rabbit** | **-86.5 mm** | vertical | **two halves** |
| **The Mandalorian** | **+37.2 mm** | vertical | **two halves** |
| **Kronk** | **+30.9 mm** | vertical | **two halves** |
| Alcina Dimitrescu | -26.0 mm | **splay 188 mm** | posed -- read with care |
| Thanos | +8.8 mm | **splay 249 mm** | posed -- read with care |
| B1 Battle Droid | +9.3 mm | vertical | a lean, or mixed; only just over threshold |

**The verdict rule had to be corrected before this table was trustworthy.**
Its first version compared only the pair CENTRES, and on that rule Alcina read
"TWO HALVES" exactly like Mando. But her leg pairs separate 0.2806, 0.3824 and
0.4683 going down -- her legs splay, so she is posed, and this file's own note
on her says her static pose IS her shape and must never be reset. She also
stands 127.7 mm off the origin by design. Legs whose pairs separate
identically at hip, knee and foot are vertical and unposed, and only then has
an offset upper half nowhere to come from but the rig. Both spreads are now
printed on every flagged line so the verdict can be checked rather than
trusted.

Note which characters are NOT here. Of the seven whose yaw lines disagree --
Steve, Jessica Rabbit, The Mandalorian, Alastor, Peacemaker, Vigilante,
Alcina -- only three are flagged. The other four have a genuinely displaced
limb instead, so the two checks separate two different faults rather than
restating one.

**Jessica Rabbit's -86.5 mm is the largest on the roster and she was rebuilt
the same day**, so it is either inherited from her source or made by our own
builder, and that is worth knowing before anything else is done to her. Her
reported fault was that her dress and the sprung parts of her body "float
around separate of each other", and an 86.5 mm offset between her upper and
lower halves is a candidate for exactly that. **Not investigated.**

**No fix yet, deliberately.** Correcting this means moving bones without
moving the geometry they carry -- changing a bone's rest position while
compensating its bind pose, so the rest pose is byte-identical and only the
pivot moves. That needs the mesh's own centreline established first, and the
slice measurement above is too noisy to supply it. Choosing a correction on
the strength of a +-20 mm wander would be guessing.

### The clearance guard cleared a joint's CENTRE, not its sphere, 2026-11-16

Nothing had ever checked the spring chains that **already have** a collider
group. `--collide` checks a chain before it HANDS it one, and that is the
easier direction: the groups that matter were written by `vrm_colliders.fit`
and by the characters' own authors, not by that guard.

`joint_inside_check_installed.py` asks the other question, and across the 65
installed bundles **87 non-anchor spring joints in 18 characters start inside a
collider of their own chain's group.** A joint inside a collider is not
restrained by it, it is EJECTED to its surface -- the fault that ballooned
Gadget Hackwrench's hair into a mass bigger than she was.

**17 of those joints carry our own arithmetic's fingerprint.** `add()` shrinks
a collider to `near * 0.95` where `near` is the distance to the nearest
non-anchor joint's **centre**, so wherever the guard is what set the radius,
`radius / centre_distance` is exactly 0.950. It is, on 10 characters -- Jinx 6,
Sayuri 2, Power Girl 2, and one each on Xenomorph, Scott Hall, Lola Bunny,
Jessica Rabbit, Gwen Stacy, Ariel and Aiko. Jessica was rebuilt the same day
with this builder and is in the list, which is what ruled out "old builds".

The solver's condition is `centre_distance >= collider_radius + joint_radius`.
Clearing the centre by 5% therefore leaves the nearest joint overlapping by
`joint_radius - 0.05 * centre_distance`, which at our 0.02 hit radius is
**14 to 19 mm on every affected character**.

**The file already knew.** Twenty lines above the guard, choosing a limb
percentile, it reasons: *"A spring joint is a SPHERE of hit_radius 0.02, so the
capsule only has to come within 0.02 of the furthest vertex."* The sizing rule
accounted for the joint sphere and the guard forgot it, in the same function.

#### What it costs, measured in the engine with the character standing still

`YargSpringProbe.cs` gained `-still 1`: hold the character perfectly still and
let the solver settle. A still run *should* read ~0 mm for every bone, so
anything it reports is a collider shoving geometry off where the model was
authored -- permanently, since this is a constraint and not an impulse.

Jinx, as installed, `-wind 0,0,0`:

```
Jinx-ORIG: peak deflection during a STILL run (should be ~0) 76.04 mm
Jinx-ORIG: 15 of 128 bone(s) moved more than 1 mm
        braid_r.008_end       76.041 mm
        braid_l.008_end       70.187 mm
        bangs_d.002_end       38.807 mm
```

**Her braid tips are 76 mm out of place while she does nothing at all**, and
the ejection is four times the overlap because it propagates down the chain: a
17 mm push at `braid_r.005` is 76 mm by the tip.

The run was repeated with the probe's default `-wind 14,0,6` and with
`-wind 0,0,0`, and the two agree **to three decimal places on every bone**, so
none of it is the external force. That control matters: a still run with wind
on would have been a measurement of the wind.

#### Fixed in both guards, because there are two copies

The rule lives in `vrm_colliders.add()` (the builder) and in
`patch_springs.py --limbs` (the patcher), and both ignored the joint radius
while having it to hand -- the patcher had it in `joints[pid][4]` all along.
Both now clear the joint's **surface**:

```python
near = min(_seg_dist(g, centre, tail) - jr for g, jr in guard)
```

It reduces to the old behaviour exactly when `jr` is 0, which is what the
downloaded VRoid rigs carry, so nothing about them changes. Both warn instead
of shrinking a collider out of existence -- deleting one is the documented
catastrophe that cost the Xenomorph his torso capsule.

**This costs nothing in reach**, which is the thing worth being clear about.
The surface the solver actually tests is `radius + joint_radius`. Taking the
radius down by the joint radius leaves that surface exactly where the joint
rests, which is on the body; before the fix it sat 19 mm *outside* the body.
The collider's number gets smaller and the barrier does not move.

#### `--reclear` for the installed bundles

The builder fix only reaches a character that gets rebuilt, and 35 of the 65
have no source file left. `--limbs` reaches the limb capsules of the rest but
not the head sphere or the torso capsule, which is where Jinx's bangs sit.

`patch_springs.py --reclear` is a fifth independent fix: shrink **any**
collider that swallows a non-anchor joint's sphere, to 0.95 of the real
clearance. It only ever shrinks, it skips a chest chain like every other fix
here, it leaves the limb capsules to `--limbs` when both are asked for so the
two compose rather than race, and it refuses with a warning where shrinking
would delete the collider.

Verified end to end on a scratch copy of Jinx -- **nothing has been installed**:

| | joints inside | still-run peak | bones over 1 mm |
|---|---|---|---|
| as installed | 15 | **76.04 mm** | 15 of 128 |
| `--limbs` only | 8 | 38.81 mm | 3 of 128 |
| `--reclear` | **0** | **0.61 mm** | **0 of 128** |

`--reclear` changed 6 colliders -- `head`, `pelvis`, both thighs, both calves
-- each by exactly **-19.0 mm**, and the read-back reports 6 changed, 0 gone,
0 added. `--limbs` alone leaves her bangs at 38.8 mm because the `head` sphere
is not its to touch, which is the whole reason `--reclear` exists.

**10 characters carry the signature** and 18 have at least one joint inside.
*(An earlier version of this section said 13 characters; that was a miscount of
this file's own table, corrected the same day.)*

#### APPLIED to the 14 of ours, 2026-11-16

Of the 18, **four are not ours and were not touched**: `Harq Alkahana`,
`Hatsune Miku (Retry Now ver.)` and `Inforder Trogen` are downloaded VRoid
bundles, and `Adachi Rei` carries 28 of the 87 on **author-made colliders** --
hers sit on dedicated bones named `apronL0-collider`..`apronR3-collider` at a
300 mm radius, which is not a shape `fit()` produces, and none of her findings
carries the 0.950 signature. All six downloaded bundles still read
`2026-11-06 19:16`.

That leaves 14. Every one was backed up to `<name>.prereclear-2026-11-16` and
each backup verified against its source with `cmp` before anything was written.

| | before | after |
|---|---|---|
| bundles with a joint inside | 18 | **6** |
| joints inside | 87 | **41** |
| joints with OUR signature | 17 | **1** |

All six that remain are accounted for: the four that are not ours, plus Sayuri
and Yoda, where the floor refuses (below).

**Thirteen changed; Yoda did not.** His only offending collider is below the
floor, so `--reclear` wrote nothing and his file is byte-identical to his
backup. Every other read-back reported exactly the expected number of objects
changed, 0 gone and 0 added -- 1 object for nine of them, 2 for Power Girl and
Sayuri, 3 for Chibi Rem, 6 for Jinx.

Load-tested all 13 against their own backups in one run, 26 bundles: **every
POST matches its PRE exactly** on renderers, materials, bones, skinned meshes,
chains and joints, 0 failed.

And measured in the engine, still, zero wind -- the number that matters:

| character | before | after |
|---|---|---|
| Power Girl | **78.46 mm**, 11 of 432 bones | 0.65 mm, **0** |
| Jinx | **76.04 mm**, 15 of 128 | 0.61 mm, **0** |
| Scott Hall | **32.13 mm**, 8 of 98 | 0.05 mm, **0** |
| Chibi Rem | **13.02 mm**, 4 of 181 | 0.09 mm, **0** |
| Gwen Stacy | 2.82 mm, 1 of 95 | 0.00 mm, **0** |

Not one bone on any of the five is now displaced by more than a millimetre
while the character stands still.

#### The floor, and why it exists

The first run of this had no real floor -- only `near * 0.95 <= 1e-5`, which a
clearance of 0.0001 m passes. It wrote a 0.1 mm collider, which is a deleted
collider with extra steps:

```
reclear: CC_Base_R_Upperarm       0.019 -> 0.000 (-19.0 mm)
reclear: Hips                     0.020 -> 0.002 (-17.9 mm)     (Yoda)
```

**That is the Xenomorph catastrophe, reintroduced by the guard written to
prevent it.** Sayuri and Yoda were restored from their backups, the floor went
in -- never below 5 mm, never below a quarter of the radius that was there --
and both were re-run. Sayuri keeps her hip fix and her arm collider; Yoda is
left exactly as he was. The floor refused those two and nothing else: the other
nineteen reductions are all between 60% and 92% of the original radius.

Past the floor the tool leaves the overlap and says why, because the honest
reading is that a joint sitting on the bone axis has a hit radius too large for
that geometry -- and a collider that is gone cannot deflect anything at all.

Installed md5s: Aiko `72a5413`, Ariel `4af1c3e`, Chibi Rem `cd79f57`,
Gwen Stacy `46eb986`, Heels `afdd17d`, Jessica Rabbit `bab26ee`, Jinx
`2385017`, Lola Bunny `e0a347b`, Peach `9dfdb3a`, Power Girl `bb54236`,
Sayuri `406a9bb`, Scott Hall `9e60553`, Xenomorph `3146949`. Yoda unchanged at
`04fe94c`.

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


### Jessica Rabbit's dress, 2026-11-16: 37,310 vertices on one bone

Reported as *"her dress clips through her body and isn't rigged to her body;
the spring boned parts of her body and her dress are floating around separate
of each other, which makes a huge mess"*. All three halves of that are literally
true and they are one fault.

**Her dress is two meshes and every vertex of both is weighted to a single
bone.** Measured on the installed bundle, in the hips' own frame:

| mesh | verts | influences per vertex | weighted to | extent y |
|---|---|---|---|---|
| `Object_1`, the bodice | 24,035 | **1** | **`spine` only** | −0.11 .. +0.40 |
| `Object_2`, the skirt | 13,275 | **1** | **`spine` only** | −1.02 .. −0.01 |
| `mesh_11`, her body | 39,668 | 1 to 4 | 158 bones | — |

`spine` IS her humanoid hips, so the dress follows her hips and nothing else.
It cannot bend with her legs, her torso or her chest: the body moves inside a
rigid shell. Her only spring chains are `breast.L` and `breast.R`, and the one
part of her that does move therefore swings inside cloth that is not following
it. That is the "huge mess", exactly.

*(Those two chains carry no collider group. An earlier version of this file
called that a second fault and attached one; it is the builder's deliberate
choice for a chest chain, and the change was reverted -- see "RETRACTED: her
chest chains had no collider group BY DESIGN" below.)*

A control: shaken in the spring runtime, the installed character's ONLY moving
bones are the two breast tips, at 90.6 mm. Everything else reads 0.000.

#### What the rebuild fixes, and what it does not

Her recipe is the best-documented on the roster and is verified to reproduce
her, so it was followed to the letter. Rebuilt and installed:

| | installed | rebuilt |
|---|---|---|
| skirt weighting | 1 bone, 1 influence | **17 bones, 1-3 influences** |
| spring chains | 2 (breasts) | **10** — 4 hair, 4 skirt cloth, 2 breast |
| colliders | 2, referenced by **no** chain | **10, referenced by 8 of 10** |
| peak deflection, shaken | 90.6 mm (breast tips only) | **1024 mm** (skirt), 400 (hair) |
| clips / meshes / textures / materials | 6 / 16 / 12 / 11 | identical |

The skirt is now rigged and sprung, against leg colliders -- which is Peach's
fault avoided rather than repeated.

**THE BODICE IS NOT FIXED: 24,035 vertices are still one influence on `spine`.**
The mechanism is in the build log and is worth recording, because the pipeline
does this to itself:

```
2349  auto-weighted unrigged mesh 'Object_9' (24035 verts) to the skeleton
2377  T-pose bake: 'Object_9' has 87 groups, 24035/24035 verts weighted
2389  orphan bones: 1 bone(s) sit ABOVE the humanoid root ... so their weight
      moved down to 'spine' instead -- GLTF_created_0_rootJoint, 26804 vertices
```

The bodice arrives unrigged, is auto-weighted correctly to 87 groups, and then
the orphan-bone step moves 26,804 vertices of weight off `GLTF_created_0_rootJoint`
-- the GLB's own root, which sits above the humanoid root and can never be
driven -- and onto the hips. Confirmed in the built `.vrm`: `Object_1`, 24,035
verts, joint 1, `spine`, one influence.

Moving an orphan's weight to the hips is RIGHT for a small share (Miku's
`Bip01 Pelvis`, 985 vertices) and wrong when it is an entire garment, because
the result is a garment welded to the hips -- which is the fault being fixed.
The remedy is to keep undrivable bones out of automatic weighting in the first
place, so nothing lands on them; that is not done here because the hips are not
known at the point the weighting runs, and a rule that guesses which parentless
bone is the stray is worth more thought than this evening.

#### RETRACTED: her chest chains had no collider group BY DESIGN

**Everything in this sub-section's first version was wrong, and the change it
describes has been reverted on all five characters it reached.** It is kept
because the way it passed every check is the lesson.

What was claimed: her `breast.L`/`breast.R` chains shipped with no collider
group, nothing restrained them, this was Peach's fault again, and nineteen
installed characters shared it.

What is true: **a chest chain with no collider group is this project's own
decision.** `vrm_colliders.add()` skips exactly these when it attaches the
group, and the reason is written beside `CHEST` in that file:

> Chest springs sit ON the torso, so handing them the torso capsule would push
> them out of the body they belong to.

The torso capsule is a crude cylinder fitted outside the ribcage. A chain that
sits on the chest is inside it almost by definition, so the group does not
restrain such a chain, it holds it off the body. `cloth_collide_installed.py`
carries the same constant for the same reason, and says so in as many words:
*"A check that flags a decision as a fault teaches the reader to skim its
output."* That is precisely what happened, to the author of the check.

**`patch_springs.py` already carried `CHEST` itself**, defined at the top and
used twice -- to exclude chest chains from `--cloth` and from the `--limbs`
clearance guard. The `--collide` block was written three hundred lines below
the constant, in the same file, and named Jessica's breast chains as its
motivating case.

**The clearance guard did not catch it, and could not.** It asks whether a
joint starts INSIDE a collider, and four of the five characters cleared every
collider of the group at rest -- Jessica's tightest was `breast.R` at
**+19.5 mm**. The geometry really is clear; it is the intent that is not. A
physical check can only answer the question it is given, and *"is this
possible"* is not *"is this what the builder decided"*.

**The one measurement that should have stopped it was already in hand.**
Jessica's chest deflected **90.62 mm** under the spring probe before the attach
and **90.62 mm** after. That was written up as the colliders restraining the
motion without suppressing it. It is nothing of the kind: an identical figure
means the joints never reach the collider under that motion, so the attach did
nothing at all. A change with no measured effect is not a validated change, and
"unchanged" is the weakest possible evidence for a benefit.

**Reverted.** All five restored from their `prechestcollide-2026-11-16`
backups and verified byte-identical with `cmp`: Jessica Rabbit (md5
`f6192dce...`, 15,989,409 bytes -- note the patched file was 1.9 MB *smaller*,
which is the repacker, not content), Tenna `5a29b774`, Power Girl `69803005`,
Sayuri `dd918f1a`, Heels `63f95aad`. Nothing else was ever touched.

**And the roster claim collapses.** Re-swept across all 65 installed bundles
with the chest skip in place, the number of characters carrying a non-chest
chain that has no collider group and clears the group's colliders at rest is
**zero**:

| what the sweep finds | characters | verdict |
|---|---|---|
| chest chains only | Jessica Rabbit, Killer Clown, Tenna, Power Girl, Prix, Sayuri, Heels, Lola Bunny | **by design** -- `--collide` now names them and declines |
| a non-chest chain, joint starts inside a collider | Miku (`Tie`: 44.4, 30.5, 7.4 mm inside `Bip01 Spine`) | refused by the clearance guard |
| several collider groups, so no group to infer | Adachi Rei, Harq Alkahana, both Hatsune Mikus, Inforder Trogen, Kaiser Aufhanger | tool declines without `--group`; the five VRoid bundles are not ours |
| a genuine candidate | **none** | |

The sweep printed those seven lines while walking all 65 bundles, so the zero
is a measured zero rather than a search that never ran.

So the sweep offered after the first version of this section -- seven
characters, "exactly Jessica's fault" -- would have changed seven characters
and been wrong about every one.

**`--collide` keeps its purpose**, which is real: a NON-chest chain with no
collider group is restrained by nothing and swings through the body, and that
is half of Peach's dress. It now has two guards rather than one, the clearance
check and the chest skip, and the docstring says why each exists. Miku remains
a good control for the first, reporting her `Tie` joints at 44.4, 30.5 and
7.4 mm inside `Bip01 Spine` -- the same three figures a different tool measured
the day before, reproduced independently.

**What is actually open on Jessica.** Her two chest chains peak at 90.6 mm, and
whether that is too much is a question about the chains' own stiffness and
drag, not about colliders. Untouched and unmeasured against anything.

#### FIXED in the builder: re-weight a mesh once it has been CARRIED into place

The cure is one step in `build_vrm.py`, placed after the T-pose bake. By then
the scale stage has carried the mesh to where it belongs and bone heat works in
WORLD space, so the fix is simply to weight it again there. No geometry is
baked and nothing is moved: the useless weights are thrown away and recomputed
against a skeleton that is finally around the mesh instead of thirty units
away.

It is deliberately narrow. A mesh qualifies only if **this script auto-weighted
it itself** (it was in `UNRIGGED`) **and** at least 90% of it then landed on
**one bone that is an ancestor of the humanoid hips** -- a bone nothing can
ever drive. A binding somebody authored is never touched, and neither is a prop
legitimately riding a single DRIVEN bone: Joker's pistol keeps `Gun_joker`.
`VRM_NO_RECARRY=1` switches it off; `VRM_RECARRY_MIN` moves the 0.9.

It refuses rather than shipping a bad result: if re-weighting leaves the mesh
on fewer than two bones, or leaves over half of it unweighted, or moves the
geometry by more than a micron, the build aborts.

```
carried mesh: 'Object_10' (13275 verts) came out of automatic weighting with
  100% of itself on 'GLTF_created_0_rootJoint', a bone ABOVE the humanoid root
  that nothing can drive -- it was weighted while it stood away from the
  skeleton. Weighting it again now that it is in place.
    now on 13 bone(s); 13275/13275 vertices weighted; geometry moved 0.0000 mm
carried mesh: 'Object_9' (24035 verts) ... 100% of itself on 'GLTF_created_0_rootJoint'
    now on 10 bone(s); 24035/24035 vertices weighted; geometry moved 0.0000 mm
```

What shipped, measured on the installed bundle:

| mesh | before | after |
|---|---|---|
| bodice `Object_1` | 1 bone, `{1: 24035}` | **9 bones**, `{1: 913, 2: 4318, 3: 5411, 4: 13393}` |
| skirt `Object_2` | 1 bone, `{1: 13275}` | **21 bones**, `{1: 3258, 2: 5618, 3: 3488, 4: 911}` |

The bodice's bones now include **`breast.L` and `breast.R`**, which is the
reported fault answered directly: the cloth over her chest deforms WITH the
sprung chest underneath it instead of being a shell it swings through. The
skirt's include `thigh.L` and `thigh.R`, so it follows her legs. Her extents
are unchanged to the millimetre (bodice y −0.107..+0.397 against −0.108..+0.397),
and the orphan-bone step's load falls from 26,804 vertices to 13,856.

**The control is what makes this safe to put in a builder every character goes
through.** Spartan Mark V, rebuilt from the same source and arguments before
and after the change: the step does not fire, and the two `.vrm` files are
**byte-identical**, md5 `b68ce9e41e52a49a` both times.

Installed at md5 `f6192dce…`, 15,989,409 bytes; load test 16 renderers / 11
materials / 194 bones / 10 chains, 0 failed. Backup
`character-backups/Jessica Rabbit.prebodice-2026-11-16.yargchar`.

#### Chasing the bodice, 2026-11-16: why it is not a weights problem you can patch

The builder's own `trace()` says where the bodice is at every stage, and its
docstring says why to use it -- *"chasing a part that ends up in the wrong
place by reasoning about matrices is how three wrong fixes got written"*:

```
TRACE after import    Object_9   z  6.204.. 9.474
TRACE after realign   Object_9   z  6.204.. 9.474
TRACE after pose bake Object_9   z  6.204.. 9.474
TRACE after scale     Object_9   z  0.914.. 1.420
```

It does not move until the scale, because **it is being CARRIED by the bone it
is welded to**. In the GLB everything with 160 vertex groups -- the body, the
hair, the eyes -- stands at z 32..44, and everything with ZERO groups stands at
z 0..10.6: the dress sculpt, beside the mic-stand cubes and cylinders. The
dress is a separate unskinned model thirty units from the character, and the
only bone anywhere near it is the file's own root joint, **38.56 units long**,
running from z 0.33 to z 38.90 straight through the pile. Bone heat has nothing
else to choose.

So the obvious remedy -- just give the dress the body's weights -- would tear
it off her, because its data is not where the body's is. Which is why the
patch route was tried and measured rather than assumed.

#### The patch route is closed, and the number that closes it

`patch_transfer_weights.py` copies the body's weights onto a garment by nearest
vertex, rewriting the two weight channels in the vertex buffer. Its central
guard is that **re-weighting must not move the mesh at rest**: with consistent
bind poses every bone's `world * bindPose` is the same data-to-world map, so
the rest pose does not depend on which bones carry a vertex.

On her it refuses, at **35.7 mm**, and the reason is in the file:

| bone | where `world * bindPose` sends one body vertex |
|---|---|
| `spine` | (−0.1558, +1.2776, −0.0694) |
| `spine.003` | (−0.1558, +1.2776, −0.0694) |
| `breast.L` | (−0.1558, +1.2776, −0.0694) |
| **`thigh.L`** | (−0.1536, **+1.1754**, **+0.0834**) |

The spine chain agrees to four decimals and `thigh.L` is 102 mm out in y and
153 mm in z; across all 194 bones the spread reaches 0.96 m. About 31 bones'
bind poses disagree with their rest pose -- the build straightened her legs
(*"worst thigh is 28.0 deg off vertical"*) and baked a non-identity rest on 31
bones. **Any re-weighting in this bundle is unreliable wherever it touches
those bones**, and a garment hanging from the hips to the ankles touches them.

Adopting the donor's bind poses as well changes nothing: it is the same 35.7 mm,
because the disagreement is between bones and not between meshes.

The tool is kept, and it has been exercised rather than merely written: a
self-transfer of the body onto itself reproduces its influence distribution
exactly ({1: 6576, 2: 12026, 3: 6299, 4: 14767}), moves the rest pose by
**0.0002 mm**, and the rewritten bundle loads in Unity at 16 renderers / 11
materials / 194 bones / 10 chains, 0 failed. So the vertex-buffer rewrite is
byte-correct and the refusal is a finding about her file, not a bug in the
tool.

**The bodice therefore needs fixing in the BUILD**, at a point where the
geometry has been carried onto the body and the bind poses are about to be
generated together -- not in the bundle. That is a real change to the order of
`build_vrm.py` and it is not made here.

#### A rule that was written and NOT shipped

`build_vrm.py` detects unrigged meshes as `not o.vertex_groups`, which cannot
see a mesh bound to one bone at weight 1. A rule was added to treat such a mesh
as unrigged when several deform bones stand inside its own bounding box -- a
dress has thighs, shins and feet inside it, where Joker's pistol has its one
bone. **It never fired on her**, because her GLB's dress is genuinely unrigged
and the fault is introduced later, so it was reverted rather than shipped
unexercised. The fault class is real -- the installed bundle is an instance of
it -- so the rule is recorded here for whoever meets it in a source.

### Aiko, 2026-11-16: turned 30 degrees, and her recipe does not reproduce her

Found by the yaw sweep, not by a report: she stands **29.95 degrees off**,
the worst on the roster, and nobody has looked at her on a podium. Her build
predates `build_vrm.py`'s facing stage -- her log has no `facing:` line --
which is the same story as Spartan Mark V.

**The turn itself rebuilds out cleanly.** Today's builder detects it
unprompted:

```
facing: feet point (-0.5, -0.87, 0.0), 30 deg off forward
        - turning the character 30 deg about Z
```

and the rebuilt bundle reads **+0.03 deg, spread 0.15** against her installed
**-25.24, spread 23.61**. Her height verification line matches her original
build exactly (1.7000 m, width 1.0868 m).

**And the rebuild is NOT installed, because it breaks her hair.** Rendered, the
rebuilt character wears her hair as a flat black sheet hanging over her face.
Two builds were made to find out whether the hair RIGGER was to blame -- her
recipe row records no hairrig, but her installed bundle carries four
`HairSpring_*` chains, so one was used:

| build | chains | hair |
|---|---|---|
| no hairrig | 0 (67 transforms against her 84) | **over her face** |
| hairrig `hair` | 4 chains of 4, 84 transforms, every count matching | **over her face** |

The second reproduces her structure exactly -- 6 clips, 1 controller, 1 mesh,
3 textures, 3 materials, 84 transforms, 4 chains / 16 joints, and the load test
puts it beside the installed one at 81 bones each. The hair is wrong in both,
so the rigger is not the cause: **the rebuild misplaces her hair whatever is
done about springs** -- and the claim that `GirlsInAction.blend` with
`^Girl2\.[0-9]` is therefore not the whole recipe is **WRONG, corrected
2026-11-18**: the recipe reproduces her, the builder changed underneath it.

So she keeps her 30 degrees for now. That is the honest trade: the turn has
never been reported, the hair would be reported immediately, and a fault nobody
has seen is not worth a regression anybody would.

**Kronk (-6.97 deg, spread 0.00) was not attempted.** His source is a USDZ of
him doing the hokey pokey and his row warns that he looks T-posed and is not;
on the evidence of Aiko, a rebuild of a character this old is as likely to cost
something as to fix the 7 degrees nobody has noticed.

### Spartan Mark V, 2026-11-16: the Animator does not read what we patch

Re-reported the next day — *"master chief's leg is still sticking out at the
right hip"* — and the reporter is right twice over. The section below this one
is correct about the fault and correct about the edit, and the edit **never
reaches the screen**.

#### 1. The patch is in the file, and it is right

Everything the earlier work claimed holds up on re-measurement. In the shared
parent's frame `thigh.R` is now the exact negate-X mirror of `thigh.L`,
0.00000 on every pair; the right leg's FLESH mirrors the left at a median of
0.0 mm in the spine's own frame, against 51.4 mm before; and the source
confirms negate-X IS the mirror for this rig (0.000 mm on all 29 pairs).

Even the number that was withdrawn turns out to have been right. "92.12 mm
from the mirror of his `thigh.L`" was struck on 2026-11-15 as coming from a
tool that compared local offsets under a rotated shared parent. The withdrawal
was too broad: that comparison is invalid between bones with DIFFERENT parents,
and both thighs hang off `spine`. The offsets were (−0.10623, +0.12118,
+0.01496) and (+0.19379, +0.14891, +0.00781), and the distance from the
negate-X mirror is 92.12 mm exactly.

#### 2. And the game throws it away

Unity's humanoid `Animator` re-poses the skeleton from the **Avatar**. The four
structures this pipeline writes — `Transform.m_LocalRotation`, the Avatar's
`m_AvatarSkeletonPose` and `m_DefaultPose`, and
`m_HumanDescription.m_Skeleton` — are **not what retargeting reads**. Measured
in Unity, instantiating the prefab and then calling `Animator.Rebind()` and
`Update()`, which is what the game's own preview does:

| | hips L / R at instantiate | after `Rebind()` |
|---|---|---|
| the pre-patch backup | 161.8 / 244.5 mm, diff **−82.7** | 161.8 / 244.5, diff −82.7 |
| the patched, installed bundle | 161.8 / 161.8 mm, diff **0.0** | 161.8 / **244.5**, diff **−82.7** |

The patched file and the unpatched file produce **the same animated character**.
The bind pose is corrected and discarded one frame later.

**This is not a fact about Spartan Mark V.** It applies to every bundle-level
rest-pose edit on a bone the humanoid rig maps, which is what
`patch_mirror.py` exists to make — so that tool cannot do what it says for any
character with a humanoid Animator, and every character here has one but
Kasane Teto. It does NOT apply to bones outside the humanoid map: a humanoid
Animator drives only the bones it maps, so Miku's necktie re-aim (`Bone01`) and
her spring chains are untouched by this and stand.

#### 3. And he is turned 20 degrees, which is the hip that was reported

A separate fault, found while looking for the first. Every line that is
left-right by construction agrees:

| | hips | shoulders | knees | feet |
|---|---|---|---|---|
| **Spartan Mark V** | +20.00° | +20.00° | +20.00° | +20.00° |
| Miku | 0.00 | −0.06 | 0.00 | 0.00 |
| The Rock | −0.32 | −0.03 | −0.32 | −0.32 |
| Doom Slayer | 0.00 | 0.00 | +0.01 | +0.01 |

He stands turned, so his left hip faces the camera and reads as sticking out —
on the RIGHT of the picture, which is what was reported. The cause is in the
source and is not a defect there: `MkVSKETCHFAB.blend` is a perfect mirror
about a plane **20.00°** off the world x axis, because the model was built at
an angle, and nothing in this pipeline squares a character up.

Four lines agreeing to two decimals is what makes this the body turned rather
than a limb displaced, and `patch_body_yaw.py` refuses to turn a character
whose lines disagree for exactly that reason.

#### He is not the only one — the sweep across all 65

`body_yaw_check_installed.py` over the installed roster, reading the four
structural lines. The SPREAD is what separates the two faults, and it separates
them cleanly: three characters have every line agreeing, and seven have one
line arguing with the others.

| character | mean yaw | spread | reading |
|---|---|---|---|
| **Aiko** | **−29.95°** | 0.15 | turned, and worse than Spartan |
| **Spartan Mark V** | **+20.00°** | 0.00 | turned |
| **Kronk** | **−6.97°** | 0.00 | turned |
| Elite Terrorist | −1.51° | 2.47 | turned, but slightly |
| Steve | +7.47° | 18.27 | NOT a turn — a limb |
| Jessica Rabbit | −2.30° | 12.79 | NOT a turn — a limb |
| The Mandalorian | +2.50° | 11.10 | NOT a turn — a limb |
| Alastor | −7.48° | 10.04 | NOT a turn — a limb |
| Peacemaker | −2.28° | 9.12 | NOT a turn — a limb |
| Vigilante | +5.16° | 7.19 | NOT a turn — a limb |
| Alcina Dimitrescu | −1.73° | 6.91 | NOT a turn — a limb |

The other 54 are square. **Aiko has never been reported**, which is the useful
part of a sweep: she stands 30 degrees off and nobody has looked at her on a
podium yet. The seven with disagreeing lines are a separate question and one
this check is not the tool for — a single line arguing with three others is
what a displaced limb looks like, and `limb_socket_check_installed.py` clears
all of them, so they need a look rather than a patch.

#### What was built, and what it is good for

`patch_body_yaw.py` squares the bind pose: it measures the yaw from those four
lines, turns the humanoid root bone by that angle about world +Y, writes the
four rest structures, and re-measures the written bytes. On him, +20.00° →
−0.00° on every line. **It was not installed, because finding 2 applies to it
too** — the Animator discards it, and the rendered character is pixel-identical
apart from the podium's own colour cycling. It is kept because the bind pose
being square is still correct, because the measurement half is what found the
fault, and because a rebuilt character will need checking against it.

Its own re-measure caught a sign error that would otherwise have shipped: Unity
is left-handed Y-up, a positive turn about +Y takes +Z toward +X, and the yaw
measured as `atan2(z, x)` therefore comes out as `yaw − t`. The correction is
`+yaw`, not `−yaw`. Signed the intuitive way it turned a character 20° off into
one **40°** off, and the refusal-on-re-measure is the only reason that did not
reach disk.

#### What fixed him: a rebuild, and the builder ALREADY knew

Rebuilt and installed 2026-11-16. There is no patch-level alternative — the
data retargeting reads is the Avatar's own precomputed human axes, and
inserting a node above the skeleton to rotate it is not available either,
because every bone's path is what the Avatar's `m_TOS` looks it up by. So the
Avatar has to be regenerated, which means a build.

**And the extra step prepared for it was not needed.** A `square.py` was
written to turn the source rig before building, and the control build — the
UNMODIFIED source through today's `build_vrm.py` — says this in its own log:

```
facing: feet point (0.34, -0.94, 0.0), 20 deg off forward
        - turning the character -20 deg about Z
```

`build_vrm.py` has a facing stage and it already detects and corrects exactly
this. The installed bundle was simply made before that stage existed. Both
builds were measured and both come out square, 0.000 mm leg mirror error on
every pair, so **the recorded recipe needs no addition** and what shipped is
the plain one. Building the control first is the only reason that is known
rather than assumed: with only the straightened build in hand, the rotation
would have been credited with a fix the builder was doing anyway.

**Verified where the patch failed** — in Unity, through the Animator:

| | hips L / R at instantiate | after `Rebind()` | yaw after `Rebind()` |
|---|---|---|---|
| old, installed | 161.8 / 161.8 mm | 161.8 / **244.5** | hips 24.64°, shoulders 12.28° |
| **rebuilt** | 143.3 / 143.3 mm | **143.3 / 143.3** | hips **4.56°**, shoulders **−7.96°** |
| Doom Slayer, control | 133.3 / 133.3 | 133.3 / 133.3 | hips 4.20°, shoulders −7.89° |

The rebuilt figures match the control to a fraction of a degree, and that
residual is the idle animation's own stance rather than anything about him.
Note the hip offset: **both** of his hips were wrong in the old build, not just
the right one — patching `thigh.R` onto `thigh.L` made them agree at 161.8 mm
when the source says 143.3.

Same character: 20,989 vertices and 6 meshes in both the rebuild and the
installed bundle, 29,692 triangles. Load test 6 renderers / 6 materials /
65 bones, 0 failed. Installed at 20,336,186 bytes, md5 `dea599c1…`, against
20,002,228 and `cd31325a…`; the old file is
`character-backups/Spartan Mark V.preyaw-2026-11-16.yargchar`.

**His recipe now reproduces him**, which it did not before: the row below used
to record that building from `MkVSKETCHFAB.blend` gave a different `thigh.L`
with its X sign flipped, because the installed character came from a pipeline
that no longer exists. The installed character is now the one this recipe
makes.

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


### Miku's necktie, 2026-11-15: modelled for physics that never came across

Seen in game and reported as sticking straight out. It is not ours, and it predates everything
done to her today — the first two things measured were both checks on that claim rather than on
the tie.

**It is not today's work.** `Miku.nosprings.yargchar`, the backup taken before this morning's
twintail change, has the tie region identical to the shipped file: same bones, same vertex counts,
same world boxes to the millimetre, and the character's whole z profile at chest height matching
decile for decile.

**It is not ours at all.** Her source `Miku.fbx` has the same chain at **69.1° and 72.4° off
vertical**, against the 71° measured in the bundle. That is the same story the per-model table
already records for her hair — *"splayed outward in the ORIGINAL download, not by us"*. She is an
MMD-style rig (`Bip01` biped plus generic `BoneNN`) whose tie was meant to be settled by rigid-body
physics, and a VRM export carries none.

**What it is.** `Bip01 Spine1` → `Bone01` → `Bone02` → `Bone03`:

| bone | world position |
|---|---|
| `Bone01` | (0, 1.2498, **+0.1178**) |
| `Bone02` | (0, 1.2034, **+0.2391**) |
| `Bone03` | (0, 1.1612, **+0.3724**) |

89 mm of drop for 255 mm of reach, and the geometry runs out to **z +0.545** — half a metre of
necktie standing out in front of a chest whose surface is at about z +0.08.

**The fix is a rotation, not a rebuild.** Rotating `Bone01` carries `Bone02`, `Bone03` and all 20
of their vertices as a rigid unit, so the tie swings to where it should hang and its geometry is
untouched. `patch_bone_aim.py` computes the MINIMAL rotation taking the bone's current direction
to the target, which leaves its roll alone, and writes it to the four structures that hold a
bone's rest transform.

**Straight down is wrong, and measuring said so.** Aimed at (0, −1, 0) the tie reads z 0.115..0.140
over y 0.800..1.210 while her body front over that band reaches z +0.167: **14 of its 20 vertices
end up behind the body surface**. Her chest is in the way, which is exactly what a necktie rests
on. Swept over forward leans:

| lean from vertical | tie z range | vertices behind the body |
|---|---|---|
| 0° | +0.115..+0.140 | **14 of 20** |
| 10° | +0.123..+0.217 | 4 |
| 15° | +0.126..+0.255 | 4 |
| 20° | +0.130..+0.292 | 4 |
| 30° | +0.136..+0.361 | 4 |

The 4 that never clear are the **knot**, the top four vertices at y 1.209–1.211 sitting 22 mm
inside the collar — where a knot belongs, and where they already were, since the root is the pivot
and does not move. Everything below hangs clear from 10° on: y 1.15 at z 0.143 against a body
front of 0.128, y 0.96 at z 0.207 against 0.150, and the tip free at y 0.82.

**15° was chosen** over the 10° minimum for margin in motion: she is animated, and a tie that
clears by 15 mm standing still is a tie that clips when she leans. Beyond 20° it stops reading as
hanging and starts reading as blowing.

**`verify_rebuild.py` cannot see this change, and that is worth knowing.** It reports CULL-ONLY —
no bone moved — because it compares each bone's rotation MAGNITUDE, `2·acos(|w|)`, and both the old
quaternion (0.000000, −0.506897, +0.862007, 0.000001) and the new one (0.000000, +0.071175,
+0.997464, 0.000001) have w = 0 and therefore both read as 180°. **It is blind to a rotation about
a different axis through the same angle.** The assurance for this patch comes from the fingerprint
instead: every object's full typetree compared before and after, **2 of 249 changed** — the
`Transform` and the `Avatar` — with 0 gone and 0 added, and `bundle_audit` identical at 6 clips /
1 controller / 42 humanoid / 22 fingers / 1 mesh.

**And the tool checks its own work**, as `patch_mirror.py` learned to: after writing, it re-reads
the patched bytes, re-measures the direction, and refuses to write unless it has landed within a
degree of the target. It reports **0.00° off**.

**What is still wrong with her.** Her twintails are splayed in the source too and are left alone —
the README already records that and the hairrig that tried to fix it sheared the ribbons apart.
And this morning's twintail springs drive very little: none of the bones that actually carry her
twintails (`Bone06`–`Bone13`) is on a spring chain at all, so that fix is doing less than was
claimed for it. That is a separate thing to answer for.


### The Rock's arms, 2026-11-16: a cached bounding box, and a day spent on the wrong suspect

**FIXED AND INSTALLED.** Upper arm 0.344 → **0.176** of height against a human
0.186, forearm 0.145 → 0.142 against 0.146, reach 1.272 → **0.932** against the
0.938 his own recipe row says to expect.

**Everything in the section below this one is wrong, and it is wrong because
of a bug in the scaffolding, not in the pipeline it accused.** It is kept
because the way it failed is the lesson.

#### The cause: `Object.bound_box` is a cache, and it goes stale

`scale_rig.py` sized the skeleton from `o.matrix_world @ o.bound_box`. That
box is a CACHED value. Applying a transform to an armature leaves every
parented child's cached box describing the old space, and
`evaluated_get(depsgraph).bound_box` hands back the same stale numbers — so
the staleness survives the one call that looks like it would clear it. On him
the cached box read a **1.9638 m** character as **3.2915 m**, a factor of
1.6761. Measured side by side in one file:

```
bound_box[0]   [ 75.2318, 186.50391, -265.62634]
a vertex .co   [-13.1399, 160.2856,     8.3811 ]
```

The skeleton was then scaled by **0.6668** where his recipe row records
**0.3978**, and nothing complained: a plausible number was printed about a
height the model has never had.

`scale_rig.py` now reads the vertices. They cannot go stale, 22,844 of them
cost nothing, and the cached box is still computed and reported when it
disagrees — a stale box upstream is worth knowing about.

#### `fit_joints.py` was innocent, and the midpoint rule is right

On a correctly scaled rig, the rule the section below convicts agrees with the
rig's own joints almost exactly:

| | the rig says | midpoint of the two flesh centroids |
|---|---|---|
| elbow | 48.9% | **50.7%** |
| knee | 51.5% | **51.9%** |

And on the rig scaled by the stale factor it lands at **69.5%** — against the
shipped bundle's **70.3%**. That is the reproduction. The shipped character is
what the correct rule produces on an incorrectly scaled skeleton, which is why
every attempt to fix the rule made things worse.

#### How a day went into the wrong suspect

The staging written to reproduce his build selected the armature **and all 21
of its meshes** and applied transforms to all of them at once. The meshes are
parented to the armature, so their world transform already contains the
armature's, and applying both counts it twice: a 1.9638 m model came out at
3.2915 m. Every measurement after that was of a character two thirds too big,
and all of it was self-consistent — which is exactly why it read as a finding
rather than as a broken rig.

The new staging applies the armature's transform **only**, and then checks:
the mesh's world bounding box before and after must agree to a tenth of a
millimetre or nothing is saved. It reads 0.000000 m. A staging step that
silently resizes the model is worse than one that fails, and this one had no
way to fail.

So the three rejected "fixes" below — excluding the arm chain, scale-only, and
taking the interior joints from the rig's proportions — were all answers to a
question that was never asked. The legs tell the same story: "1.06 before the
fit and 4.97 after" was the double-applied staging, and the rebuilt character's
thigh and shin (0.315 / 0.224) are **identical to the shipped ones**, so his
leg proportions were never touched by the fit at all and are simply the model's.

#### What shipped

Staged (prefix stripped, armature transform applied, geometry verified
unmoved), `scale_rig.py` at the correct 0.3978, `fit_joints.py`, then
`build_vrm.py` at 1.96 m with `mixamo` and the 10 textures in `rocksrc`.
`patch_shine.py '*'` afterwards, because he is one of the 26 flattened on
2026-11-15 and a rebuild predates that.

Same character: 25,083 vertices installed against **25,093** rebuilt, 21 meshes
both, and the load test reads 21 renderers / 21 materials / 52 bones, 0 failed.
`limb_check` elbow 0.0/0.0 and knee 0.0/0.0; `limb_socket_check` 0 limbs out of
socket. Installed at 7,834,248 bytes, md5 `57dc0bc2…`; the old file is
`character-backups/The Rock.prearms-2026-11-16.yargchar`, md5 `e16ed2d5…`.

---

### ~~The Rock's arms, 2026-11-15: the flesh does not locate the joint~~ (SUPERSEDED — see above)

Reported in the first thirteen as "arms are squiggly", twice worked on, and still wrong — seen in
game on 2026-11-15 with the words "the arms have not changed at all", which is exactly right.

**What is wrong is a LENGTH, which is a third kind of limb fault.**

| | upper arm | forearm | ratio | shoulder→wrist |
|---|---|---|---|---|
| his source `Rock.fbx` (of span) | 0.135 | 0.140 | **0.96** | 0.275 |
| installed (of height) | **0.300** | 0.127 | **2.37** | 0.427 |
| population norm | 0.186 | 0.146 | 1.27 | 0.332 |

His upper arm is **61% over** the norm and his forearm 13% under. Every existing check passes him:
`limb_check_installed.py` reads elbow 0.0/0.0 and wrist 1.9/0.9 because nothing is BENT wrong, and
`limb_socket_check_installed.py` clears him because nothing is DISPLACED — the segments are the
wrong lengths, and no tool measured that. `proportion_check_installed.py` holds the numbers but
reports "0 of 1 more than 2.5 sigma", because with one character there is no population to deviate
from.

**It is not a bone that drifted off its mesh.** Tracing the arm's radius from the shoulder, the
flesh pinches at 520–560 mm and the elbow bone sits at 533.6, with the skinning handing from
`LeftArm` to `LeftForeArm` exactly there. The mesh was stretched WITH the bones, which is why no
patch to the bundle can fix it and why this one needed a rebuild.

**The cause: his arm flesh does not locate his arm joints.** Measured on his own rig after
`scale_rig.py`:

| | position | % of the arm |
|---|---|---|
| his rig's elbow, and his source's | 439.8 mm | **48.9%** |
| upper-arm flesh spans | 334.5 .. 649.1 mm | |
| forearm flesh spans | 625.8 .. 880.7 mm | |
| midpoint-of-centroids rule (what the fitter uses) | 625.1 mm | **70%** |
| boundary-of-the-two-clusters rule | 630.0 mm | **70%** |
| **the installed bundle** | 533.6 / 759.1 | **70.3%** |

The last line is the reproduction: the shipped character is exactly what this rule produces. His
upper-arm group keeps dominant weight **209 mm past the real joint**, so the clusters put the
elbow at 70% when it belongs at 49%. **A better formula does not help** — the boundary rule, which
is what the fitter's own header says it wants, lands within 5 mm of the midpoint rule. Both are
reading clusters that are not where the rule assumes.

**TWO FIXES WERE TRIED AND BOTH ARE WRONG. Nothing was installed.** They are recorded because
each one fails in a way that says something about the problem.

**1. Exclude the arm chain (`FIT_ARMS=0`).** His arms come back to ratio 0.96 — and the same
rebuild's LEGS come out at thigh 0.527 / shin 0.106 against a norm of 0.245 / 0.246. The rule
breaks his legs exactly as it breaks his arms: **1.06 before the fit, 4.97 after**. So excluding
the arms is treating one symptom of a rule that is wrong on every limb he has.

**2. Exclude both, i.e. scale only.** Worse than either. Measured on his scale-only rig, his
**hand bone sits 1,537 mm from his hand flesh**, the finger bones at z 2.735 while his knee is at
z 1.488. That is the "fingers stretch into strips past his knees" this file already records, and
it is why the fit cannot simply be turned off. The fit is doing something essential: it is the
only thing that can pull his hand back a metre and a half to where his hand actually is.

**3. Keep the distal joint from the flesh, take the interior from the rig's own proportions.**
This looked right and is not. At the `.blend` it gives everything at once — arms 0.96, legs 1.06,
hand bone 46 mm from its flesh instead of 1537. But the built `.vrm` comes out **3.331 m tall
against a required 1.96**, because placing the hand where the flesh says while spreading the
interior joints by the rig's fractions keeps the RATIO and inflates the LENGTH: his arm goes from
914 units to 1774. The chain's ROOT is mis-scaled too, and a rule that only pins the far end
stretches everything between.

So the real statement is narrower than "the midpoint rule is wrong": **his whole arm is the wrong
length AND wrongly divided, and the flesh clusters can fix only the end of it.** Fixing both needs
the root as well, which none of the three attempts addresses. `fit_joints.py` is unchanged on
disk.

#### Two things the recorded recipe does not say, and cannot run without

> **The second one below is right about WHAT is needed and wrong about HOW.**
> Applying the transforms of the armature and its parented meshes together
> counts the armature's twice and resizes the model by 1.676. Apply the
> ARMATURE'S ONLY — Blender keeps parented children where they are — and
> verify the mesh's world bounding box did not move. See the correction above.

Reproducing "scale_rig.py then fit_joints.py" on his source fails twice before it gets anywhere,
and both are properties of the tools rather than of him.

**The `mixamorig:` prefix has to be stripped first.** `scale_rig.py` aborts with "no hips bone
found"; `fit_joints.py` does not abort — its chains are bare names like `LeftArm`, nothing
matches, and it repositions **nothing while reporting success**. Stripping happens in
`build_vrm.py`, which in the recorded order runs LAST.

**The object transforms have to be applied first.** `fit_joints.py` reads mesh vertices in WORLD
space (`o.matrix_world @ v.co`) and writes the answer into edit-bone coordinates, which are
ARMATURE space. The two agree only when the armature's transform is identity. His FBX imports with
the armature at scale 0.0254, and the fit then produces an **upper arm of 2,863 mm against a
forearm of 5.7 mm** — a ratio of 505. Whoever built the shipped character had applied transforms,
since the shipped result matches the fit's correct-space answer; but nothing in the tool or the
recipe says so, and the failure is silent in the sense that it writes a file and prints "joints
repositioned: 10".


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
- `YargFootProbe.cs` (scratch Unity project) — does the Animator PRESERVE a humanoid bone's
  position? It does not: every leg bone is re-posed by 2 to 45 mm on `Rebind()` + `Update()`, on
  a correct character as much as a broken one, so **the rest pose in the bundle is not what the
  game draws**. What matters is whether a FAULT survives it. Jessica's 92.4 mm foot-height
  difference becomes 94.05 mm; Jinx, symmetric in her bundle, lands at **1.75 mm**, which is the
  Animator's own asymmetry and the noise floor. Run a symmetric character alongside or the
  re-posing reads as the finding
- `pair_offset_check_installed.py <dir|yargchar...>` — left/right asymmetry needing **no
  centreline and no mirror assumption**. A pair's X cannot be compared without knowing where the
  middle is, and on Jessica Rabbit the middle is what would not be established; `dy` and `dz` need
  no middle, so a difference is measured against nothing but the pair. **Spartan Mark V reads 0.0
  on every pair and every axis and 32 of 65 bundles are symmetric to within 0.1 mm**, which is the
  control that makes a reading mean anything. Found Jessica's whole right leg **92.4 mm higher**
  than her left and her right arm 29.0 mm higher and 74.1 mm back, with her shoulder bones
  symmetric to a tenth of a millimetre. **Read dy and dz separately:** a pure `dz` difference with
  `dy` at zero is the body being TURNED, which `body_yaw_check_installed.py` already measures
  (Aiko's `dz` -100.2 mm over 190 mm of leg separation is her known 29.95 deg), while a `dy`
  difference cannot come from a yaw at all. The tool classifies each character and prints the yaw
  each `dz` implies, so the two instruments can be cross-checked rather than double-counted.
  `PAIR_MM` moves the 5 mm threshold
- `centreline_check_installed.py <yargchar> [mesh]` — where is the geometry's own centreline?
  **MEDIAN x per height band, not the midpoint of the extremes**, which is the point: slicing
  Mando and taking (min+max)/2 gave midpoints wandering ±20 mm, a measurement of his outliers.
  Selects by dominant bone so a torso band is not contaminated by the arms crossing it. Prints the
  quartiles and the count per band **because that is what shows when the median is not a
  centreline at all** — on Jessica the band medians spread 169.6 mm with quartiles like
  q25 -0.0197 / median +0.1233 / q75 +0.1568, which is a cluster on one leg rather than a body
- `half_body_check_installed.py <dir|yargchar...>` — is the UPPER half of a skeleton laterally
  offset from the LOWER half? Reads WORLD positions of the pairs the Avatar itself calls left and
  right, so it needs no axis convention and no reference to x = 0 — one half of the character
  against the other is the only anchor here that cannot itself be wrong. **This is not
  `mirror_check_installed.py`**, which was deleted for negating X on local offsets. It reports each
  pair's separation, each pair's centre, and the segment lengths down each limb, because a limb
  SCALING fault shows in the lengths and a step does not. **It CANNOT tell a step from a lean, and
  its three-decimal agreement is not evidence that it can.** Its six pairs are the legs and the
  arms: on a standing figure the leg pairs inherit the hip bone's X rigidly and on a T-posed one
  the arm pairs inherit the shoulder's, so the six numbers are two numbers measured three times
  each, with nothing sampled in between. It called The Mandalorian a 37.2 mm step between two
  half-skeletons and he has no step at all — run `plumb_check_installed.py` on anything this
  flags, BEFORE acting on it. **Read both spreads, not the step alone:** legs whose pairs separate
  identically at hip, knee and foot are vertical and unposed, and only then has an offset upper
  half nowhere to come from but the rig — Alcina's legs splay 188 mm, so she is posed and her
  26 mm means something else. `HALF_STEP` moves the 8 mm threshold
- `YargCharLoadTest.cs` — the acceptance check before an install: makes UNITY open a `.yargchar`,
  build the humanoid rig, walk the hierarchy and `Rebind()` it, then prints clips, humanoid bone
  mappings, skinned meshes, bones and VRM spring chains/joints. Every other measurement here reads
  the bytes with UnityPy, and a file can read perfectly and still fail in the engine. Run the OLD
  and NEW bundles in ONE invocation and compare the counts; a count that drops is the question to
  answer before anything is replaced. Copy it beside the exporter in `Assets/__TempExport/Editor/`
  and delete the folder afterwards. **Rewritten 2026-11-17** after the only copy was deleted with
  a scratch Unity project — it had never been committed, which is why it is here now
- `straighten_spine.py` (Blender) — takes a lean out of a character's spine in the build
  INTERMEDIATE, where it can still be done: a rest-pose edit on a MAPPED humanoid bone is
  discarded by the Animator, so a bundle patch cannot. It poses each spine joint onto vertical,
  iterated, and `--keep` restores named limb roots to their original ORIENTATION at their new
  positions so arms and legs ride the correction without tilting. **`--control` runs the whole
  round trip with a ZERO correction** and its output must measure the same as the shipped bundle,
  or nothing measured on a corrected build means anything. **`--no-bake` is the other sense of
  the word and the choice is the whole decision:** baking rotates the BODY with the bones (right
  when the body leans), not baking moves the BONES inside a body that stays put (right when the
  body is plumb and the skeleton leans inside it). On The Mandalorian baking threw his helmet
  50 mm off and `--no-bake` left both armour planes within 0.3 mm
- `islands_installed.py <yargchar> [min-verts]` — splits each skinned mesh into CONNECTED
  islands and gives each one its world box, its box centre in X, the bone that drives most of it
  and that bone's own X. This is what finds a part a report names when the part has no mesh of its
  own: The Mandalorian's chest plate is a 280-vertex island inside `Object_0`, and his helmet's two
  ears are 190 and 190. **The box centre is not a centreline** — that plate's box reads +22.9 mm
  and its own plane of symmetry is −8.0 mm, because it extends further on one side than the other.
  Find the island here, then ask `mesh_mirror_installed.py` where it is centred
- `plumb_check_installed.py <dir|yargchar...>` — every humanoid bone's X against its HEIGHT,
  walking the spine, with the limb roots beside it. A lean comes out as a gradient and a step as a
  step, and it prints the largest single gap beside the total range so the two can be told apart
  rather than asserted. Written because `half_body_check_installed.py` cannot see the difference
  and this file published a 37.2 mm "step" that is a 3.3 degree lean. **Spartan Mark V reads 0.0
  at all eleven heights** — run him alongside anything new. `PLUMB_MM` moves the 5 mm threshold
- `mesh_mirror_installed.py <yargchar...> [--control] [--yaw]` — where the GEOMETRY's own
  centreline is, fitted with no bone, no axis convention and no left/right labelling: the plane
  the SURFACE is most nearly symmetric about, scored by the median nearest-neighbour distance of
  the reflected cloud. It samples each triangle by area rather than using the vertices, because a
  vertex-to-vertex distance has a floor set by the tessellation and that floor is what the first
  version actually measured. `--yaw` lets the plane turn as well as slide, so a character standing
  a few degrees off axis is measured instead of being mistaken for an asymmetric one. **Read the
  residual and the climb, never the optimum alone** — Spartan Mark V reads +0.00 mm on all six of
  his meshes with a 0.75 mm residual, while The Mandalorian gets no mesh below 5.5 mm on curves
  that barely climb, because a cape, a bandolier and a holster mean no plane mirrors him
- `part_bones_installed.py <yargchar> [name-regex]` — what drives each mesh, and where that mesh
  ends up. Per skinned mesh: the bones that dominate it and by how much, the world box and
  centroid of the SKINNED result, and for each top bone the centroid of the flesh it dominates
  against the bone's own position. The bone SPREAD is the diagnostic — one bone at 100% is a rigid
  island (Mando's helmet, 2,219 verts all on `n37`), nine bones is a skinned garment — which tells
  a misplaced prop apart from bad weights before anything is rebuilt. Note that `m_Bones` holds
  TRANSFORM PPtrs: routing them through the GameObject table returns None for every bone, every
  name collapses to `?`, and every mesh reads as having exactly one dominant bone, which is
  precisely the finding this tool exists to make
- `joint_inside_check_installed.py <dir|yargchar...>` — does a spring joint START INSIDE a
  collider of its own chain's group? A joint inside one is not restrained by it, it is EJECTED to
  its surface, permanently, and that is what ballooned Gadget Hackwrench's hair. `--collide` asks
  this of a chain before it HANDS it a group; nothing asked it of the 306 chains that already had
  one, where the answer was **87 joints in 18 of the 65 bundles**. It reports `r / centre_distance`
  per finding, because **0.950 is our own shrink guard's fingerprint** — that is how the
  centre-vs-sphere defect was identified as ours rather than the authors', on 17 joints across 10
  characters. The chain's FIRST joint is reported separately and is not a fault: it is the anchor,
  its position comes from the skeleton, and no collider can eject it. Chest chains are excluded, as
  everywhere else here. `INSIDE_CONTROL=3.0` multiplies every radius so the sweep must flag — it
  reaches 27 bundles, which is what proves a quiet run walked the set
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
- `patch_bone_aim.py <yargchar> <bone> [--aim x,y,z] [--out X] [--dry-run]` — re-aims a
  bone chain so a dangling part HANGS, for geometry modelled sticking out because the author
  expected physics to settle it. Rotating the bone carries its children and all their flesh
  as a rigid unit, so the part swings and its geometry is untouched. The rotation applied is
  the MINIMAL one taking the bone's current direction to the target, so its roll is left
  alone, and it goes to the same four structures as a bone's position. Default aim is
  straight down, which is often wrong: Miku's tie aimed at (0,-1,0) puts 14 of its 20
  vertices inside her chest, so it took 15° of forward lean. After writing it re-reads
  the bytes, re-measures the direction and refuses unless it landed within a degree —
  which matters here because `verify_rebuild.py` is BLIND to this edit: it compares rotation
  MAGNITUDE, and both of Miku's quaternions have w = 0, so both read as 180°
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
- `patch_add_springs.py <yargchar> <out> --chain A,B,C [--chain ...] [--group N|none]
  [--stiff/--drag/--grav/--radius V] [--name N]` — puts bones that ALREADY EXIST onto spring
  chains in an installed bundle. The opposite of `--unrig-hair`, and it exists for a fault that
  tool cannot describe: every rigger here selects bones by NAME, so a rig whose author called
  the twintails `Bone07` and the necktie `Bone01` is invisible to `DEFAULT_SPRING` and is left
  entirely rigid by a rule that is working correctly. It reports how many vertices each chain
  DOMINATES, because "3 chains added" is a fact about the file and says nothing about how much
  of the character moves. Guards, in order: every bone exists; none is a humanoid bone; none is
  already on a chain; each is a CHILD of the one before it, because a VRM chain is a path and a
  list of unrelated bones is not one; a chain has at least two bones, the last being only a tip;
  and **no joint may start INSIDE one of its own colliders** — a rest pose in penetration is not
  a collision that gets handled, it is a displacement on frame one, and on Miku's necktie
  (44.4 mm inside the torso capsule) it would have undone a fix made the same morning.
  `--group none` is the escape and is a real trade: no colliders means the chain can swing
  through the body. Joints are created by copying one the file already has — UnityPy 1.25 has
  no API for adding an object — so it refuses on a file with no joint to copy, and the result
  is checked by re-reading the written BYTES and, for the first patch here that adds objects
  rather than edits them, by Unity's own loader with the pre-patch file as the control
- `patch_springs.py <yargchar> [--cloth] [--limbs] [--unrig-hair] [--collide] [--group <path_id>] [--out X] [--dry-run]` — fixes
  the spring simulation IN THE INSTALLED BUNDLE, five independent defects, any or all. `--reclear` shrinks any collider that SWALLOWS a non-anchor spring joint's sphere, to 0.95 of the real clearance — the installed-bundle half of the centre-vs-sphere guard defect, and the only fix that reaches the head sphere and torso capsule. It only ever shrinks, leaves the limb capsules to `--limbs` when both are asked for, and warns rather than deleting a collider. On Jinx it takes a still character's hair from **76.04 mm out of place to 0.61 mm**. `--collide` gives a chain that has **no collider group at all** the file's own group, and only such a chain — nothing restrains one without, so it swings through the body (Peach's dress). **Two guards.** It refuses when a joint would START INSIDE one of those colliders, since the solver's first act is to push it out: on Miku's `Tie` it reports 44.4, 30.5 and 7.4 mm inside her torso capsule and writes nothing. And it skips a **chest** chain outright, because a chest chain with no group is `vrm_colliders.add()`'s deliberate choice rather than an omission — without that skip it attached the group to five characters' breast chains, every one of which passed the clearance guard, and all five had to be reverted. Across all 65 installed bundles it now finds **zero** chains that should be given a group. `--cloth`
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
| Prix | mixamo | 1.70 | **SHE HAS A SOURCE AND A RECIPE AS OF 2026-11-16** — Jay supplied `prix.glb` (53,038,136 bytes, sha256 `7b3d7836af17a1e4`, Sketchfab-16.56.0). **Bake the joint scale FIRST**, or her hair arrives 22x too small: `python glb_bake_joint_scale.py prix.glb prix_baked.glb`. Then build from the BAKED file with `VRM_GLTF_BIND_POSE=node` (her IBMs and node tree disagree and the importer follows the IBMs, which puts her hair at the world origin), `VRM_BLEND_MATERIALS="Hair"`, `VRM_CUTOUT_MATERIALS="cejas1"`, and exclude `^(Icosphere\|[LR]_iris_.*)$` — the Icosphere is a 2 m sphere that wrecks the height, and the two iris meshes are 100% transparent in the source so they are better dropped than cut out. Shape keys still drop by default, which is what keeps her off 0.42 m. Earlier note follows: shape keys must be dropped, else she builds at 0.42 m. **As installed 2026-11-12:** `aiStandardSurface4` (the lens on `L_iris`/`R_iris`) is set to alpha 0.08 with `set_material_alpha.py` — it shipped OPAQUE, wearing her SKIN atlas, parked in front of perfect blue eyes. She has no source here, so this is an edit to the built `.vrm`, not a rebuild; census identical and only the two collider helper nodes differ in rotation. **Her hair stays untouched** |
| Pomni | pomni | 1.70 | exclude `^Circle`; `VRM_VISEME_GAIN=3.0` (4.4 turns her upper lip inside out); `VRM_BLINK_BAKE="EyelidSup.L=1,0.55,0,0;EyelidInf.L=1,-0.5,0,0;EyelidSup.R=1,0.5,0,0;EyelidInf.R=1,-0.5,0,0"` and `VRM_BLINK_LASH="^Lashes"` (lash ticks lie on the closed seam, 4 mm in front of the lid, keeping 40% of their height) -- her blink is four eyelid BONES (peak at frame 30 of `Animation`), not a shape key; her `Lashes/Closed` key only moves two lash ticks and leaves the eyes open. The bake applies Solidify+Subsurf to the lid meshes, writes the closed pose as a `Blink` key and binds it. Rendered at weight 1.0: dark lids with a slit, matching her Sketchfab blink. Her iris `Big`/`Small` keys ride on YARG's own facial events: `VRM_EXPR="Wide_eyed=Eye.L/Big;Squint=Eye.L/Small"` makes them custom expressions named for lipsync event types, which `VRMCharacter.TryGetExpressionKey(string)` sets by name -- `Big` fills the eye with iris, `Small` shrinks it to a pinpoint (rendered, both eyes). The chart generator emits `Squint` but not `Wide_eyed`. **Added 2026-11-12, and she cannot be rebuilt without it:** `VRM_VISEME="aa=Face/A,ee=Face/ClosedTeeth,ih=Face/ClosedTeeth@0.7,oh=Face/OpenNoTeeth,ou=Face/OpenNoTeeth@0.6"` — her mouth shapes are named for an artist and only `A` is guessable, so without this she builds at 1/5 visemes. 32,764 triangles, 16 meshes, 27 morph targets, 5/5 bound. **Rebuilt and reinstalled 2026-11-12 for the collider-group fix alone** (item 0a) — no alpha change; backup `.precolgroup` |
| Sayuri / Aiko | cc_base / mixamo | 1.70 | hairrig `^Hair$` — no hair bones of their own. **Sayuri as installed 2026-11-11:** add `VRM_BREASTRIG=1` (the recovered ARGV is the original build and omits it — without it the rebuild comes back with 4 spring chains against her 6) and `VRM_TEX="Eye_Shadows=Eyelashes_Opacity.png:alpha"` (she has one `Eyelashes_Opacity.png` and two materials that need it; the picker gives it to the one whose name matches). Her model is `source/Sayuri dans.fbx`, its texture paths point at `C:\Temp\CharacterCreator4Temp\` on someone else's machine and the builder relocates all 8 of them. 91,632 triangles. **As installed 2026-11-12:** add `VRM_BLEND_MATERIALS="Eyelashes;Eye_Shadows;Lace;Moles;Hair"`, then run the result through `add_colliders.py` with `VRM_RECOLLIDE=1`. **That last step is not optional and is not in the ARGV**: what is installed went through that round trip, which adds 19 named collider nodes and normalises bone rolls, so a direct build reads as `differs` against the installed bundle (25 bones off by exactly 90° or 180°) until it has been round-tripped too |
| Aiko | mixamo | 1.70 | exclude `^Girl2\.[0-9]` — one girl, 15 Mixamo clips. **CORRECTED 2026-11-18 -- it DOES reproduce her; the 2026-11-16 reading below was the builder's alphaMode regression, not the recipe.** (was: "This recipe does NOT reproduce her"): built from `girls14/inner/GirlsInAction.blend` with `girls14/textures` it matches her counts exactly when the hairrig `hair` is added (84 transforms, 4 chains / 16 joints, 6 clips, 3 materials) — and her hair comes out hanging over her face, with and without that rigger. Something about her hair is not in this row |
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
| Joker / Miku | maxbiped | 1.85 / 1.58 | **Miku, as installed 2026-11-15:** build from `miku-final.blend`, textures `miku_orig/textures`, exclude `^ts_bot`, **spring argument EMPTY** and `VRM_CLEAR_SPRINGS=1 VRM_FINGER_FILL=1`. Her intermediate carries the `HairSpring_1_*`/`HairSpring_2_*` twintail chains an earlier session built, so `VRM_CLEAR_SPRINGS` wipes those and `DEFAULT_SPRING` rebuilds ~~exactly one chain per twintail~~ **two chains on the RIGGER'S OWN bones** — `DEFAULT_SPRING` matches `HairSpring_1_0` because the word is in its name, and matches nothing of hers, because her twintails are `Bone06`..`Bone15`. 2 chains, 4 joints each, 10 colliders, `MonoBehaviour` 22 -> 41, and 38 of her ~500 twintail vertices moving. **The installed bundle is no longer this build**: `patch_add_springs.py` added 7 chains on her own bones on 2026-11-15 evening, so a rebuild from this row loses them and they would have to be re-applied. **Do NOT pass `$^` as the spring argument** (see below), and do not pass `VRM_EXPORT_POSE=rest`: her recipe has never had it and adding it moves 18 bones, 45 deg on the fused thumb metacarpals. Her skirt still does not swing and cannot be rigged by the current interface — one mesh, one material, no skirt bones, so no pattern can isolate it |
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
| Spartan Mark V | rigify_plain | — | **Source located 2026-11-15** and newly recorded here: `halo-mk-v-model.zip` → `source/MkVSKETCHFAB.blend` with `textures/`, no exclude, no spring pattern, no hairrig. Proven his by the bundle's own names — its six meshes are the `.blend`'s six (`MKVHELMET`, `MKVLEGS`, `MKVLIMBS`, `MKVPOUCHES`, `MKVTORSO`, `MKVUNDERSUIT`) and its 65 bones are the `.blend`'s Rigify set. **No height is given on purpose**: he is installed at 2.146 m and nothing records that as a chosen target, so `height_targets.tsv` still has no row for him. ~~**This recipe does NOT reproduce the installed bundle**~~ — it did not, because the installed character came from a pipeline that no longer exists; **as of 2026-11-16 it does**, because he was rebuilt from exactly this row and that rebuild is what is installed. Built at 2.146 m, `rigify_plain`, textures 1024 (all 22 of his are 1024×1024), no exclude, no spring pattern, no hairrig. `build_vrm.py`'s facing stage turns him −20° about Z on its own — his source is modelled at an angle — so nothing has to be added here to square him. What the rebuild DOES establish is that today's builder produces a perfectly mirrored rig from this source, 0.000 mm on every leg pair, which is why his right leg was patched rather than rebuilt |
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
`HairSpring` bones were in the file with nothing whatever to move them.

> **CORRECTION, same day, evening.** The sentence that stood here called those
> "all eight twintail bones". **They are not her twintail bones.** They are
> eight bones an earlier hair-rigger run INVENTED and hung off `Bip01 Head`,
> and they carry 38 vertices between them. Her twintails are modelled on
> `Bone06`..`Bone15` and their `(mirrored)` twins, twenty bones carrying 462,
> and none of those was on a chain. So the fix recorded above restored motion
> to **38 of her ~500 twintail vertices** and the section read that as the
> twintails swinging. See "Miku's twintails and necktie, 2026-11-15 (evening)".

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
isolates her skirt. ~~and no skirt bones to spring either -- her 70-bone rig is
`Bip01 *` plus the eight `HairSpring` bones and nothing else~~ — **that is
wrong, and it is the same error as above**: her rig also carries `Bone01`
through `Bone15`, their `(mirrored)` twins and `Dummy01`/`Dummy02`. Two of
them, `Bone04` and `Bone05`, sit at hip height 150 mm out to each side and
carry 8 vertices apiece. So there ARE two bones in her skirt region; they are
simply too small to be the skirt. The rest of it has nothing to swing it, which
is the original conclusion reached for a reason that was not true.

Note this is a different fault from "her dress does not move with her", which
was undriven WEIGHT above the humanoid root and was fixed on 2026-11-11; the
skirt follows her hips correctly and simply has nothing to make it swing.

### Miku's twintails, 2026-11-16: two things wrong, and one of them was mine

Re-reported the next day, unchanged: *"only the middle is spring-boned"*. The
chains were all in the file and the report was right anyway.

#### 1. A component is a two-way link, and only one side was written

A Unity MonoBehaviour names its GameObject in `m_GameObject`, and the
GameObject must list the component back in `m_Component`. `patch_add_springs.py`
wrote the first and not the second, so **21 of her 29 joints were orphans**:
present, deserialised, reachable by pointer, and not a component of anything.

The verification missed it because it only ever followed the pointers the patch
had written. The Unity load test did the same -- it walks the Springs array's
own `Joints` list -- and reported `9c/29j`, 0 null, on the broken file and the
fixed one alike. **A check that follows the links the patch created can only
confirm the patch created them.** Both the tool and the load test now check the
other direction, and the tool refuses to write an orphan.

In fairness to the evidence: measured afterwards, Unity attaches those
components at instantiate anyway, so the orphan state is a real defect in what
was written and is NOT demonstrated to be what stopped the motion. It is fixed
because it is wrong, not because it is proven guilty.

#### 2. The crown was left rigid on an assumption, and the project's own rule says otherwise

`Bone06` and its mirror carry **158 vertices** -- a third of her twintails --
at the top of her head, and the 2026-11-15 pass deliberately left them rigid,
reasoning that a chain rotates its first joint and swinging the bun would be
Lola Bunny's attachment-bone fault. That reasoning was never measured against
the rule written for it. `_trim_anchor` fires only when the first bone is
LONGER than the rest of its chain **and** carries at least as much weight:

| | `Bone06` | the rest of the chain |
|---|---|---|
| length | **0.133 m** | **0.774 m** |

It fails the length test by a factor of six, so it is an ordinary first segment
and not an anchor. It also clears the head collider at rest by +13.7 mm and
+11.9 mm, so the penetration guard accepts it.

With the crown included, **462 of 462 twintail vertices are on a chain**,
against 304 yesterday and 38 before that. Plus the 20 of the necktie.

#### Verified in the spring runtime, and it took six tries to measure

`YargSpringProbe.cs` drives `Vrm10Instance.Runtime.SpringBone` -- the same
object YARG's `VRMCharacter` uses -- and reports PEAK deflection per bone.
Five earlier versions reported **0 bones moved** for Gadget Hackwrench and
Harq Alkahana, whose springs work. Each zero was the harness, and the controls
are the only reason that was known rather than believed. What they were
missing, in order:

1. **`InitializeAsync` builds nothing in the editor.** Its body is wrapped in
   `if (Application.isPlaying)`, which is false in batch mode, so the spring
   buffers were never constructed for anybody. `ReconstructSpringBone()` is
   public, runs the same construction through an `ImmediateCaller` and has no
   such guard.
2. **`SetModelLevel` is a no-op before the buffer exists** -- it tests
   `m_bufferCombiner.Combined is FastSpringBoneCombinedBuffer` and returns
   silently -- so it has to come after, not before.
3. **The character has to MOVE.** With `gravityPower` 0 and no effective
   external force, a chain at rest correctly stays at rest, so a still
   character reads rigid whether its chains work or not. Shaking the root is
   what an idle animation on a podium does.
4. **PEAK, not final.** A chain that swings and settles back reads zero at the
   end -- the same number a rigid one gives.
5. **Shake in a STRAIGHT LINE.** The first moving version used an ellipse,
   which is chiral: it reaches one side before the other, and reported
   `Bone10` at 807 mm against `Bone10(mirrored)` at 1484. That asymmetry was
   the harness. Under a linear shake the two sides agree within 10%.

#### What it says

Peak deflection under the same shake, before and after:

| bone | 2026-11-15 build | today |
|---|---|---|
| `Bone07` / `(mirrored)` | **0.001 / 0.001 mm** | 242 / 242 |
| `Bone11` / `(mirrored)` | **0.001 / 0.000 mm** | 183 / 183 |
| `Bone10` / `(mirrored)` | 565 / 621 | 807 / 1484 |
| `Bone13` / `(mirrored)` | 544 / 706 | 989 / 1010 |
| `Bone02`, `Bone03` (necktie) | 161 / 359 | 161 / 359 |

Both sides, linear shake: every twintail bone between 143 mm and 422 mm, the
two sides within 10% of each other. The necktie swings 161 and 359 mm and is
unchanged, because its chain was not touched.

**THE ORPHANS WERE NOT THE CAUSE, and the section above said so before this was
measured.** The 2026-11-15 build with all 21 joints orphaned still peaks at
706 mm under motion -- orphaned components are not inert here, because Unity
attaches them at instantiate anyway. What was actually rigid was the TOP: the
crown (`Bone06`, 158 vertices) carried no chain at all, and `Bone07` and
`Bone11`, the chain roots, are pivots whose own heads never move. That is
roughly 187 vertices of dead geometry at the top of each twintail, and it is
what "only the middle is spring-boned" was describing.

Adding the crown is what fixed it. The orphan repair is still right, and it
remains a defect worth not writing.

### Miku's twintails and necktie, 2026-11-15 (evening): the rigger's own bones were the only ones moving

Reported as "her twintails are only spring-boned where they were repaired; the
rest of her twintails are rigid", with the necktie offered as a second chain
worth springing now that it hangs. Both are exactly right, and the first one
names the fault better than three earlier passes at her did.

**What was moving.** Two chains, `HairSpring_1_*` and `HairSpring_2_*`, four
joints each, on eight bones hanging straight off `Bip01 Head`. Those eight
bones were **made by a hair-rigger run**, not by her modeller, and the rigger
weighted a little of her hair onto them. Counting the vertices each bone
DOMINATES:

| | bones | vertices |
|---|---|---|
| on a spring chain (`HairSpring_*`) | 6 of 8 | **38** |
| her own twintail bones, rigid | 20 | **462** |
| her own necktie bones, rigid | 3 | **20** |

`HairSpring_1_0` and `HairSpring_2_0` dominate nothing at all. So 7.6% of her
twintails moved, and the count of chains in the file -- which is what every
check here had been reading -- was 2 either way.

**Why nothing found it.** Every automatic rigger in this pipeline selects bones
by NAME. `build_vrm.py`'s `DEFAULT_SPRING` is a regex over bone names, and
`spring_scan.py` uses the same vocabulary: `hair|ponytail|pigtail|braid|bang|
tail|skirt|...|tie`. Her twintails are called `Bone06`..`Bone15` and her
necktie `Bone01`..`Bone03`. **Not one of those words appears in her rig**, so
the pattern matched nothing of hers — and then matched `HairSpring_1_0`,
because the rigger's own invented bones have `hair` in their names. The build
reported two chains made and was telling the truth.

This is a class, not a quirk. Any rig whose author numbered the bones instead
of naming them is invisible to a name-matching rigger, and the failure is
silent in the worst way: it reports success, with a count.

**The fix: `patch_add_springs.py`**, a new tool, the opposite of
`patch_springs.py --unrig-hair`. It puts bones that already exist onto chains
in an installed bundle. Seven chains were added:

| chain | bones | vertices |
|---|---|---|
| `Twintail_0` | `Bone07` → `Bone08` → `Bone09` → `Bone10` | 77 |
| `Twintail_1` | `Bone11` → `Bone12` → `Bone13` | 59 |
| `Twintail_2` | `Bone14(mirrored)` → `Bone15(mirrored)` | 14 |
| `Twintail_3` | the mirror of `Twintail_0` | 75 |
| `Twintail_4` | the mirror of `Twintail_1` | 64 |
| `Twintail_5` | `Bone14` → `Bone15` | 15 |
| `Tie` | `Bone01` → `Bone02` → `Bone03` | 20 |

324 vertices that were rigid now move, against 38 before. Parameters are her
own existing chains' to the digit: stiffness 0.60, drag 0.45, gravity 0,
hitRadius 0.02.

**`Bone06` and its mirror are deliberately left rigid.** They sit at the top of
her skull, 145 mm above `Bip01 Head`, and they carry 158 vertices — the buns
the twintails are tied into. A VRM chain rotates its first joint, so putting
`Bone06` at the head of a chain would swing the whole twintail about a pivot on
her crown and take the bun with it. That is Lola Bunny's attachment-bone fault,
which `build_vrm.py`'s `_trim_anchor` exists to avoid. The chains start at
`Bone07`, just below the tie.

#### The necktie gets no colliders, and that is the measured answer

The six twintail chains were given the `Body` collider group — 10 capsules and
one head sphere — and the tie was going to get it too. It must not:

| tie bone | nearest collider | clearance |
|---|---|---|
| `Bone01` | capsule on `Bip01 Spine`, r 132 mm | **−44.4 mm** |
| `Bone02` | the same | **−30.5 mm** |
| `Bone03` | the same | **−7.4 mm** |

All three START INSIDE it. A spring solver's first act is to push a joint out
to the collider's surface, so this is not a collision that would be handled —
it is a displacement, on frame one, before anything moves. Attaching that group
would have thrown the knot 44 mm forward and reproduced the **"tie sticking
straight out"** fixed that same morning by re-aiming the chain, which is as
close to an own goal as this pipeline has come.

The capsule is not wrong, it is crude: a cylinder of 132 mm radius standing in
for a torso, on a character who is slim. Shrinking it is not available — the
twintail chains share it and rely on it. So the tie chain carries no collider
group, and can in principle swing through her chest. With gravity 0 it holds
its 15° rest pose and only sways about it, which makes that the smaller of the
two faults. For hair it would be the larger one.

Every twintail bone, by contrast, clears every collider at rest, the tightest
being `Bone14(mirrored)` at **+8.6 mm** from the head sphere. The guard is now
`patch_add_springs.py`'s, not a one-off measurement.

#### Verifying a bundle that has objects in it UnityPy invented

The joints had to be CREATED — 21 of them — and UnityPy 1.25 has no API for
adding an object to a bundle. Each new joint is a shallow copy of one the file
already carried, given a fresh `path_id` and its own typetree, inserted into
the `SerializedFile.objects` dict that `save()` iterates. That works because a
copy inherits the donor's `assets_file`, `type_id`, `serialized_type` and
`class_id`, so nothing about the object is invented except its contents.

**UnityPy reading back what UnityPy wrote is not evidence that Unity can read
it**, and this is the first patch here to add objects rather than edit them.
So it went through Unity's own loader, with the pre-patch file beside it as the
control, and the load test was extended to resolve each chain's joint PPtrs —
a joint Unity cannot deserialise arrives as a **null entry in the list**, not
as an exception, so counting chains alone would have missed it:

```
character                    bundle    prefab    rend   mats  bones    smr    springs
Miku-NEW                     ok        ok           1      1     88      1     9c/29j
Miku-OLD-control             ok        ok           1      1     88      1      2c/8j

2 loaded with content, 0 FAILED
```

29 joints resolved, 0 null. The control reads 2c/8j, so the column is not stuck
on a constant.

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

## Nine reports from the character select screen, 2026-11-21

Jay looked at the installed roster in the game's own character select and reported nine faults.
**They are recorded here BEFORE any of them is measured**, with the words he used, because the
order they are written in is not an order of severity and a report is not a diagnosis. This
project has twice built a correct mechanism for a fault that turned out not to exist, and once
named a cause off a render that the weights contradicted.

| # | Character | Reported | Class (provisional) |
|---|---|---|---|
| 1 | Elite Terrorist | hand is crumpled | deformation |
| 2 | Miku | tie clips through her clothes | penetration |
| 3 | Kronk | right hand isn't set to a grip for the mic | hand pose |
| 4 | Judy Hopps | hand isn't set to a grip for the mic | hand pose |
| 5 | Batman | cape clips through his body | penetration |
| 6 | B1 Battle Droid | still holding his blaster, which will conflict with a mic | stray geometry |
| 7 | Alcina Dimitrescu | face, eyelashes etc are incorrect | material or geometry |
| 8 | Prix | right arm and hand are twisted around and crushed | deformation |
| 9 | Jessica Rabbit | dress clips through her body | penetration |

The "class" column is a guess at what kind of thing each is, written down so it can be shown
wrong. Three of them cluster as hand faults (1, 3, 4, and arguably 8), three as one surface
passing through another (2, 5, 9), and 6 and 7 stand alone. **Clustering is a hypothesis about
shared cause, not evidence of one** -- the skirt-streak investigation looked like one fault with
one cause and the weights named thighs where the eye named a forearm.

### What the game does with the hand, which settles what "a grip" even means

`BackgroundManager.cs` does **not** pose the hand. It reads six humanoid bones off the Avatar and
puts the microphone where the fingers already are:

```csharp
var mic = Instantiate(..., rightHand);                       // parented to the hand
var yuiIndexGripCenter = Vector3.Lerp(rightThumbDistal.position,
                                      rightIndexProximal.position, 0.25f);
mic.transform.position = yuiIndexGripCenter;
```

So reports 3 and 4 are not "the grip animation failed to play" -- there is no grip animation.
The mic is placed at a point one quarter of the way from the right thumb's distal joint to the
right index's proximal joint, and if the fingers are open that point sits in open air with the
mic hanging in it. The question those two reports actually ask is **where those bones are**, and
that is a number this repo can read out of the installed bundle.

Two things have to be true before a rest-pose finger measurement can answer it, and neither is
assumed here:

1. **The required six must be mapped at all.** `GetBoneTransform` returns null rather than
   throwing for an unmapped bone -- the comment at `BackgroundManager.cs:1046` records what that
   cost, since the null escaped the `try`, the character never reached its `SetLayer`, and
   Alastor was invisible rather than mic-less. A character missing them does not get a floating
   mic; it does not get drawn.
2. **The animation must not drive the fingers.** The mic is placed after `animator.Update(0f)`,
   so the pose at that instant is the animation's, not the bundle's rest pose. If the default
   vocal clips carry finger curves then the rest pose is the wrong thing to measure and the
   answer is in the clips instead.

Report 6 is the same mechanism seen from the other side: B1's blaster is geometry weighted into
the hand, so the mic will be placed into a fist that is already full. Nothing about the mic code
can avoid that -- the fix, if there is one, is at build time.

### Reports 3, 4 and 6 ANSWERED: the hands cannot close, and nine characters are worse off

Two new tools, both population-wide over the 65 installed bundles, both with the unreported
characters as controls: `hand_grip_check_installed.py` (what the Avatar binds) and
`mic_placement_check_installed.py` (where the mic is actually put).

#### The grip is a limitation of the models, and the fused bones are ours

`VoxMicGrab.anim` drives twenty **humanoid muscle curves** through a mask that enables exactly
one body part, `RightFingers`. A muscle curve addresses a SLOT, not a transform, so a slot the
Avatar does not bind is discarded in silence. The sweep is not uniform -- 48 of 65 bind all
fifteen right-finger slots, 14 partial, 3 none -- so it discriminates, and the 48 are the
control that makes a low score mean something.

**Kronk and Judy Hopps both read 9 of 15, missing the identical six slots: all of Middle and all
of Ring.** Jay named exactly those two. Yoda reads the same 9 of 15 and was not reported.

But the cause is not a mapping that was missed, and the second probe is what said so: **their
rigs contain no middle or ring bone at all**, and every finger bone either of them does have is
one THIS PIPELINE INVENTED. Their real finger nodes number zero; the eighteen `*_fused` names in
each rig come from the `VRM_FILL_FINGERS` block in `build_vrm.py`, which synthesises thumb,
index and little -- the three the microphone code dereferences -- and deliberately leaves middle
and ring alone because nothing reads them. Those bones are **weightless on purpose**: they exist
so a null does not make the character invisible, and they deform nothing.

So the chain is complete and it is nobody's bug: a three-fingered cartoon rig has no finger
bones, we add weightless stand-ins so the game can find them, the muscle curves move the
stand-ins, and no skin follows. **The hand cannot close and no change to the mapping will make
it.** This belongs in the "limitation of the model, not a failure" category.

#### The hypothesis that the mic would be flung down the forearm is WRONG

When no complete finger exists to copy from, `VRM_FILL_FINGERS` lays the stand-ins out by
stepping along the forearm. Since the game computes `Lerp(RightThumbDistal, RightIndexProximal,
0.25)`, that looked certain to put the microphone somewhere off the wrist, and the obvious fix
was to place the stand-ins in the palm instead. **It measures as nothing.** Distance from the
computed mic point to the nearest right-hand vertex, as a percentage of each character's own
height, because a millimetre is not comparable across a roster this varied:

```
54 characters whose two mic bones are REAL         median 0.24%   worst 1.45%
 4 whose mic bones this pipeline INVENTED          median 1.20%   worst 1.86%
```

Kronk's 1.20% sits beside Batman's 1.22%; Judy's 1.86% is the worst reading on the roster and is
still 19.6 mm. **The mic lands in the hand for every character that gets one.** The stand-ins
are stepped a third of a hand-length at a time from the hand's own head, so they never get far.
A fix was designed before it was measured, and the measurement killed it.

#### What the sweep found that nobody reported: nine characters get no microphone

Nine bundles fail `BackgroundManager`'s six-bone requirement outright:

| missing | characters |
|---|---|
| five of the six | B1 Battle Droid, Mannequin, Steve |
| `Right Thumb Distal`, `Right Little Distal`, `Right Little Proximal` | Sonic, Yui Suzukaze |
| `Right Little Distal`, `Right Little Proximal` | Vegeta, Mickey Mouse |
| `Right Thumb Distal` | Peacemaker, Vigilante |

**What that costs depends on which build is running, and the difference is severe:**

- With commit `0d3d4e4f` (2026-11-09, "stop a missing finger bone making a character
  invisible"): the explicit null check returns cleanly, `SetLayer(newCharacter, "Venue")` on the
  next line still runs, and the character is drawn holding nothing.
- Without it: `GetBoneTransform` returns null rather than throwing, the null escapes the `try`
  and surfaces at `rightThumbDistal.position` outside it, the throw leaves `LoadCharacter`
  before the `SetLayer`, and the venue camera culls the character. **INVISIBLE.**

**The build Jay is running does not have the fix.** `fork-build\YARG_Data\Managed\
Assembly-CSharp.dll` is dated 2026-11-04 08:41; `0d3d4e4f` landed on `dev` five days later. So
all nine are invisible in gameplay today, and a rebuild is the whole fix -- nothing about the
characters needs to change for it. None of this shows in the character-select podium, which does
not go through `BackgroundManager` at all, which is why nine broken characters look perfect in
the screenshots that prompted the other eight reports.

**This also corrects report 6.** B1 Battle Droid's blaster cannot "conflict with a mic", because
B1 has no right hand bone mapped at all and is never given one. The blaster is still wrong, but
the mechanism named in the report is not the one operating, and the fix for it is at build time.

#### A zero that was my harness, not the subject

The first run of `mic_placement_check_installed.py` reported "no right-hand geometry found" for
Kronk and Judy and nobody else, which reads as a finding about them. It was not. The tool picked
hand vertices with a regex over bone names, and their bones are called `n6`, `n38`, `n83` --
numbered, not named -- so the regex matched nothing on exactly the two characters the tool was
written to measure. It now takes the hand's descendants from the `m_TOS` hierarchy, by structure.
The reason it was caught rather than believed is that the tool prints "unmeasured, NOT good"
instead of a zero ([[verify-a-zero-with-a-control]]).

### Report 7 ANSWERED: Alcina has no colour textures, and her eyelashes were already fixed

Two separate things are bundled in "face, eyelashes etc are incorrect", and they have different
answers. Both were partly on record already -- the standing row for her says *"her colour maps
are all noise fields and she renders white; that is the archive, not the build"* -- so this
checked the installed artefact rather than repeating the note.

**The eyelashes are fixed and the fix is in the installed bundle.** `alpha_sweep_installed.py`
reads her as `blend=1 cutout=1 opaque=11` with **0 UNUSED, 0 HARDCUT, 0 INVISIBLE, 0 NOALPHA**.
The blend material is `Material.006` (`CILIOS`), moved there on 2026-11-12 precisely because it
had shipped opaque and put a black slab over her eyes. Whatever is still wrong with her lashes,
it is not an alpha mode, and no finding in that sweep supports changing one.

**The face is the archive, and it now has a number instead of a word.** "Noise field" was the
recorded description; measured against Jessica Rabbit as a control, with mean RGB and a
structure figure (mean absolute difference between adjacent texels of the image downscaled to
32x32 -- real detail survives downscaling, per-pixel noise averages flat):

| character | base-colour map | mean RGB | sd | structure |
|---|---|---|---|---|
| Alcina | `(null)_Base_Color` | (184.4, 184.4, 184.4) | 2.3 | 0.96 |
| Alcina | `None_Base_Color` | (189.7, 187.6, 187.2) | 14.3 | 2.77 |
| Alcina | `Material.014_Base_Color` | (65.3, 65.3, 65.3) | 4.0 | 1.66 |
| Jessica Rabbit | `Image_5` | (147.3, 98.0, 83.2) | 142.2 | **40.98** |
| Jessica Rabbit | `Image_0` | (118.9, 0.0, 17.5) | 112.9 | 2.29 |

**Every one of Alcina's base-colour maps is ACHROMATIC** -- R, G and B equal to a decimal place
-- and flat. A face map is not grey. Jessica's skin map carries forty times the structure and a
real skin hue; her `Image_0` is the red of the dress. The one textured thing Alcina has is
`CABELOO_preto_1.png`, her hair, at 4.72, which is why the hair is the one part of her that
reads as itself.

Compare base colour against base colour only. The `.standard` and `.normal` maps are flat on
purpose for everybody -- Jessica's five roughness maps are a uniform 205 with a structure of
exactly 0.00 -- so a sweep that pooled all textures would have called her broken too.

**So there is nothing to fix in the build.** She renders pale and featureless because her source
textures are pale and featureless, and no material, shader or alpha change reaches that. It
needs different source art, which is a different kind of task from the other eight reports.

One thing worth knowing about how this gets looked at: her row records that **at 2.9 m her head
is above the character-select camera**, so hers was accepted on numbers alone and a podium render
cannot verify a change to her face. The image in the report is a head-and-shoulders view with no
podium and no name banner, unlike the other eight, so it did not come from that screen. The
texture measurement holds either way -- an achromatic map is achromatic under any light -- but
if her face is being judged from a view this project has never used, it is worth saying which.

### Reports 2 and 8 NARROWED by the existing record, and what each now needs

Neither is new. Both have a measured entry above them already, and in both cases the report is
evidence bearing on a decision this file had made deliberately -- which is more useful than a
fresh investigation would have been, and is the reason to read the last mention before starting
one.

**Report 2, Miku's tie clipping through her clothes, is a KNOWN AND ACCEPTED consequence.** The
tie's spring chain carries no collider group on purpose: all three of its bones start *inside*
the `Bip01 Spine` capsule -- `Bone01` at **-44.4 mm**, `Bone02` at **-30.5 mm**, `Bone03` at
**-7.4 mm** -- and a spring solver's first act is to push a joint out to the collider surface,
so attaching the `Body` group would have thrown the knot 44 mm forward and reproduced the "tie
sticking straight out" fault fixed the same morning. The entry says in terms that the tie "can
in principle swing through her chest", and judged that the smaller of the two faults because
gravity is 0 and it only sways about its 15 degree rest pose.

**Jay's report is the first evidence that it is not only in principle.** That does not overturn
the measurement -- the clearances are what they are -- but it does move which of the two faults
is worse, and the entry's reason for not fixing it was that *shrinking the capsule is not
available, because the twintail chains share it*. **A third option was never considered: give
the tie its own collider group.** A chain does not have to share `Body`; a single narrower
capsule sized to her chest, referenced only by the tie, breaks the dependency that made shrinking
impossible. That is the thing to measure next -- what radius clears all three tie bones at rest
while still sitting inside her chest silhouette -- and it is a build change, not a patch.

**Report 8, Prix's right arm twisted and crushed, has a named mechanism waiting for it.** He is
already the project's worst rest-pose case: a Mixamo rig whose T-pose step *prints nothing*, so
the VRM add-on was the only thing ever T-posing him, and the rest-pose guard **fires on him at
`forearm 21.2 deg` off X**. The entry above spells out why that matters: *"Unity builds the
humanoid avatar on the bind pose, so shipping him bent would have mis-aimed every muscle axis he
has -- the same fault as the hands, applied to the whole body."* A mis-aimed muscle axis is
exactly what produces a limb that animates twisted and collapsed.

So the question for Prix is not what the mechanism is, it is **whether the installed bundle
predates the guard**. That is one measurement -- read the bind pose out of `Prix.yargchar` and
check forearm and upper arm against X, joint to joint. Measure it **joint to joint, never by
bone axis**: the first version of that guard asked which way each bone points and reported his
arms as 90.0 degrees off and his legs as 180.0, both sides, to the decimal. Numbers that round
are not a pose -- a bone's tail is synthesised wherever the rig does not pin one, so a bone axis
is a fact about the importer and the head of the next joint down is a fact about the model.

### Report 2 FIXED: Miku's tie has a collider group of its own, 2026-11-21

The recorded decision was that the tie could carry no colliders, because its three bones start
44.4, 30.5 and 7.4 mm inside the `Body` group's 132.2 mm spine capsule and the solver would
displace the knot on frame one. The reason given for not shrinking that capsule was that *the
twintail chains share it* -- which rules out shrinking the SHARED capsule and not much else. A
chain references a list of groups; nothing says two groups may not sit on the same bone.

**`tie_collider_fit.py` derives the radius from her geometry rather than picking one.** Two
bounds, both expressed as a capsule radius:

- **below** each joint's rest distance to the axis, or the joint starts inside and gets shoved;
- **above** the body surface beside each joint, or the tie sinks into her chest anyway.

Both bounds are on the same quantity and **the joint's own 20 mm radius belongs in both**,
because the solver holds the joint CENTRE at `r_capsule + r_joint`.

| joint | rest d | body surface beside it | min r | max r |
|---|---|---|---|---|
| `Bone01` | 107.8 mm | 105.3 mm | 85.3 | **87.8** |
| `Bone02` | 121.7 mm | 98.3 mm | 78.3 | 101.7 |
| `Bone03` | 144.7 mm | **105.5** mm | 85.5 | 124.7 |

**Feasible interval r in [85.5, 87.8] mm. Applied at the midpoint, 86.6 mm.** The interval is
2.3 mm wide because a tie knot physically RESTS on the chest -- there is almost no room between
"outside the body" and "where it already is". That tightness is the honest answer, not a weak
one.

Measured on the patched bundle, clearance against its own new capsule:

```
Bone01   rest 107.8 mm   clear +1.2 mm    held at 106.6 mm vs body surface 105.3  (+1.3 outside)
Bone02   rest 121.7 mm   clear +15.1 mm   held at 106.6 mm vs body surface  98.3  (+8.3 outside)
Bone03   rest 144.7 mm   clear +38.1 mm   held at 106.6 mm vs body surface 105.5  (+1.2 outside)
```

**THE FIRST VERDICT THAT TOOL PRINTED WAS WRONG, AND IT WAS WRONG TOWARDS GIVING UP.** It
compared the capsule radius bound (87.8) directly against the body surface distance (98.3),
concluded the bounds crossed, and said the fix was not available. Those are not the same
quantity: one is a radius, the other is a distance to a joint centre, and the 20 mm joint radius
sits between them. Subtracting it from both turns an apparent 10.5 mm contradiction into a
2.3 mm feasible interval. A tool written to be able to say "impossible" said it, convincingly,
on arithmetic that had dropped a term.

#### What was written, and how it was checked

`patch_chain_collider.py` clones the capsule the chain is stuck inside, gives the clone the
derived radius on the same axis, puts it in a new group (`TieChest`), and points only that chain
at it. The shared `Body` group is untouched. It refuses a chain that already has a group, and it
refuses a radius that would leave any joint inside at rest.

**Both sides of the component link are written and the one that can fail is the one verified.**
A MonoBehaviour names its GameObject in `m_GameObject` and the GameObject must list it back in
`m_Component`; writing only the first makes an orphan that deserialises fine and is a component
of nothing. Miku shipped exactly that way on 2026-11-15 with 21 orphaned joints. So the check
walks the bone GameObject's component list -- the direction that can come back empty -- rather
than following the group pointer, which works whether or not the attachment exists.

Verified on the bytes before they were written, and then independently afterwards by a tool that
did not do the writing: `collider_group_check_installed.py` reads **11 colliders in 2 groups,
all grouped and used, clean** (it was 10 in 1), the `Tie` chain references only the new group,
and all eight other chains still reference the original one.

Backed up first to `character-backups/Miku.yargchar.2bb66a80.bak`.

#### What this does NOT fix, stated rather than left to be discovered

**A capsule is rotationally symmetric and a torso is not.** The surface figures above were
measured in front of each tie joint, which is where the tie is, and the standoff is right there
to within 1.3 mm. The LATERAL surface was not characterised: a band sweep around the spine axis
came back contaminated by arm geometry (p90 of 607 mm is an arm, not a torso), so it is not
reported here as a number. If the tie swings sideways it may stand a little off her side. With
gravity 0 and a 15 degree rest pose it sways rather than swings, so the excursion is small --
but "small" is an argument, not a measurement, and this paragraph is the honest extent of it.

**This is a patch to the installed bundle, not to her recipe.** Her installed file is already a
patched artefact -- `patch_add_springs.py` put 7 chains on her own bones on 2026-11-15 -- so a
rebuild from her recorded row loses both those chains and this collider. Anyone rebuilding her
must re-apply both.

**And it is not verified in motion.** Every number here is the rest pose. Whether the tie
visibly stops clipping is a question for the running game, and the spring runtime is the only
thing that can answer it.

### Report 8, Prix: the recorded mechanism is RULED OUT, and my replacement check failed its control

`rest_pose_check_installed.py` measures what the build-time guard measures, but on the installed
bundle -- which is the artefact that matters for a character already on disk. Each limb segment
is the vector between two humanoid joints' world positions, and the number is its angle away
from the axis a T-pose puts it on. **Joint to joint, never by bone axis:** the build-time guard's
first version asked which way each BONE POINTS and reported Prix's arms as 90.0 degrees off and
his legs as 180.0, both sides, to the decimal. Numbers that round are not a pose -- a bone's tail
is synthesised wherever the rig does not pin one.

**Prix reads 0.0 degrees on all eight segments.** So does every other reported character. The
sweep is not uniform, which is what makes that mean something: Thanos reads 17.5, Gadget
Hackwrench 15.5, Xenomorph 12.3, and the roster's worst-segment angle runs median 0.0, p75 2.6,
p90 5.4, max 17.5. The exact zeros are expected rather than suspicious -- the VRM add-on applies
a T-pose of its own, so a character that went through it lands exactly on the axis.

**The bent-bind-pose mechanism this file records for Prix is therefore not what is wrong with
his installed bundle.** His arm is still reported twisted and crushed, so the cause is something
else, and the entry above that named the mechanism should not be read as having answered this
report.

#### A check I built to replace it, and withdrew

The obvious next question is whether the MESH agrees with that T-posed skeleton: a limb that
animates twisted is what a disagreement between the bind pose and the rest pose looks like, and
`bind_check.py` makes exactly that measurement -- but it needs Blender and a `.vrm`, and only
about a third of the roster still has one.

So I wrote the bundle equivalent, on the premise that `world(m_Bones[i]) @ m_BindPose[i]` should
be the identity. **It is not committed, because its control failed and I could not establish
why.** Spartan Mark V -- this project's standing control, the character that reads 0.0 on every
left/right pair -- came back with a worst bone of **1604.7 mm**. Prix read 1490.4 mm and Jessica
Rabbit 1434.7 mm, and both of them render correctly.

Two corrections went in before I stopped, and neither was enough:

- **"Expect the identity" ignores the renderer root.** `m_BindPose` is relative to the root
  while `world()` is global, so a scale or offset on the character appears in every skin matrix
  and is not a defect. Re-anchoring every bone to the HIPS should have cancelled it. The numbers
  did not move by a decimal place, which says the hips frame was already the identity and the
  root transform was never the explanation.
- **"Carries any weight" is too loose a filter.** A four-bone influence routinely includes a
  bone at 0.0001, and such a bone can sit anywhere. Restricting to bones that DOMINATE at least
  one vertex dropped 11 of Spartan Mark V's bones and 38 of Prix's -- and left the worst reading
  unchanged at 1604.7 mm, on a bone that does dominate vertices.

**CORRECTION, found minutes later and three sections up this same file: the premise is not
merely wrong, it is a false positive this project already characterised and gave a control.**
The row reads:

> `SKINDEV` 300 bone/renderer pairs off, fingers worst at 917 mm -- **Alcina reads 600 pairs and
> 2957 mm and is fine.**

`SKINDEV` is bone-against-renderer deviation, which is the same quantity I rebuilt from the
bundle side. It is ALREADY KNOWN to read hundreds to thousands of millimetres on characters that
are not broken, and Alcina at 2957 mm is already the control that says so. My 1604.7 mm on
Spartan Mark V is not an unexplained instrument failure; it is this measurement behaving exactly
as recorded, on a tool written without reading the row that describes it.

So the finding stands and is now attributed: **a large `world(bone) @ bindPose` offset is not
evidence of anything**, the tool stays out of the repo, and none of its numbers are findings.
The useful instrument for a hand fault is the one that section recommends -- `HandIsolate`,
which keeps only the triangles whose vertices are all weighted to that hand, switches every
other renderer off, and asks the Animator's humanoid map rather than matching bone names.

**This is the third time in one session that these notes had already closed a question I set
about answering** -- Alcina's eyelashes, Miku's tie clearances, and now this. The pattern is
consistent enough to be a rule: before building an instrument, grep this file for the quantity
it measures, not for the character's name.

### Reports 5 and 9: Batman's cape and Jessica's dress have ONE cause and TWO answers

Both are "guarded" by `cloth_collide_installed.py` -- Batman 12 chains and 0 unguarded, Jessica
8 and 0 unguarded. **That does not mean what it looks like.** "Guarded" there means the humanoid
part the chain hugs carries *a* collider; it says nothing about whether that collider is the
right SIZE. Miku's tie was the first case where the difference mattered, and it is the same
difference here.

(Jessica's "2 chest chains skipped on purpose" is the `breast|bust|pectoral|boob` regex, which
is her breast rig, not her dress. Her dress is the four `ClothSpring_1_*` chains.)

`tie_collider_fit.py` generalises to any chain, and the two characters come out opposite.

#### Batman: the bounds CROSS, and the fix is not available as one capsule

| | |
|---|---|
| capsule standing in for his torso | `fml_un_C_pelvis_att`, **111.8 mm** |
| cape joints, rest distance from that axis | 141.7 mm rising to 919.0 mm |
| body surface beside the top cape joints | median **149.4 mm**, min 123.4 mm |
| feasible interval | **r in [144.8, 121.7] mm -- EMPTY, crossed by 23.1 mm** |

So his cape is currently held at `111.8 + 20 = 131.8` mm from the axis while his body surface is
at 149.4 mm: **the solver is holding the cape about 18 mm inside his own silhouette**, which is
the clipping. But it cannot simply be made bigger, because the cape's top joints are *authored*
at 141.7 mm -- inside the 149.4 mm surface. A cape attaches under the skin at the shoulders, so
any capsule big enough to reach his surface starts with those joints inside it and displaces the
whole cape on frame one.

**Not attempted, and the shape of what would work is recorded instead of built:** collision
would have to apply to the lower cape only, with the attachment joints excluded, or the capsule
would have to follow the back rather than the pelvis axis. Both are design decisions about his
rig, not a radius. Seven of his eleven cape chains were not measured individually.

#### Jessica: a radius exists, and it is comfortable

| | |
|---|---|
| feasible interval | **r in [164.9, 186.6] mm** |
| suggested | **175.7 mm** (midpoint), 21.8 mm wide |
| first dress joint | held at 195.7 mm vs body surface 184.9 mm -- **+10.9 mm outside** |
| rest clearance at that radius | **+10.9 mm** |

The remaining three joints of that chain hang clear of her body entirely (no body vertex within
60 mm), so they constrain nothing, and their rest clearances are +68.0, +97.7 and +202.8 mm.

**This is NOT applied.** It is the same class of change as Miku's tie, on a character nobody has
asked to have patched, and only one of her four `ClothSpring` chains has been measured -- the
other three may want different radii or may share one. The number above is a result, not a
recommendation to run.

### The rebuild landed, 2026-11-21: the nine mic-less characters are no longer invisible

Built from `dev` at `e2e1aba1`, clean tree, which contains `0d3d4e4f`. 582 MB, 51.8 minutes,
`result Succeeded`, 111 warnings and **2 errors**, both `RenderTexture.Create failed` -- one in
`Preprocess Player` and one building `Gameplay.unity`. Those are the `-nographics` artefact
`BuildPlayerHeadless` already documents, which is why that file prints `PASS WITH 2 ERROR(S)`
rather than a clean pass: it names them and leaves the judgement to the reader instead of
swallowing them.

`YARG_BUILD_DEVELOPMENT=1` was set and the log confirms `development build (plain http
allowed)`. That is not cosmetic -- the fork sets `insecureHttpOption` to `DevelopmentOnly`, so a
RELEASE build refuses plain `http://` and reports "Insecure connection not allowed" for the song
server on the LAN, which reads as a network fault and is not one.

**Verified in the binary, both directions, with an absent control:**

| string | new build 2026-11-21 | old build 2026-11-04 |
|---|---|---|
| `"Vocalist came from "` (added by `0d3d4e4f`) | **PRESENT** | absent |
| `"NOTHING -- no vocalist will appear"` (added by `0d3d4e4f`) | **PRESENT** | absent |
| `RescanForBrowse` (added by `4fa71518`, 11-03) | PRESENT | PRESENT |
| `MergeRemoteCatalog` | PRESENT | PRESENT |
| `ZzzNotARealSymbolZzz` | absent | absent |

Those literals are in the `#US` heap and so are **UTF-16**, while the symbol names in `#Strings`
are **UTF-8** -- the probe tests both and prints both columns, because a UTF-16-only probe once
reported every symbol in this same DLL as missing.

That table does two things. It confirms the new build carries the fix, and it confirms the old
one did not -- so the claim that those nine characters were invisible in gameplay on the build
in use was correct, rather than merely plausible.

**The old build is not overwritten and nothing was installed over anything.** The new tree is at
`C:/Users/ENG2/yarg-test/fork-build-20261121/`. Settings and custom characters live under
`LocalLow/FatalException/YARG-FE/`, keyed by company and product rather than by executable path,
so both builds see the same 65 characters and the same song-server configuration. Launch
whichever one is being tested; there is nothing to migrate.

**Still unverified by use:** that the nine actually appear. The symbol table says the code is
there; only the running game says they are drawn.

### Report 1, Elite Terrorist: what his hand is NOT, and why that is worth having

`knuckle_bend_installed.py` brings the 2026-11-14 flattening measurement to the artefact the
game actually loads. That earlier work rebuilt 35 characters from source and found the add-on
replacing authored bend with exactly 0.0 degrees; this asks the installed bundles the same
question, joint to joint, and distinguishes a finger that reads 0.0 from one whose slots are
not mapped at all -- printed as `-`, never as 0.0, because a blank and a zero mean opposite
things and averaging them hides every mitten hand on the roster.

**Elite Terrorist reads 0.0 on all four of his mapped fingers. So do 43 of 65 characters.**

| | Thumb | Index | Middle | Ring | Little | mapped |
|---|---|---|---|---|---|---|
| Gadget Hackwrench | 28.3 | 29.9 | 45.3 | 29.0 | 29.0 | 5/5 |
| Thanos | 32.3 | 22.0 | 44.1 | 28.7 | 32.6 | 5/5 |
| Doom Slayer | 35.3 | 34.3 | 21.8 | 30.5 | 20.9 | 5/5 |
| **Elite Terrorist** | **0.0** | **0.0** | **0.0** | **-** | **0.0** | **4/5** |
| Batman | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 5/5 |
| Jessica Rabbit | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 5/5 |
| Spartan Mark V | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 5/5 |
| The Rock | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 5/5 |

19 carry bend, **43 read flat**, 3 have no mapped finger at all. **Flatness is the population
norm and therefore cannot be what singles Elite out** -- Batman, Jessica Rabbit, The Rock and
the roster's own control all read exactly the same and nobody has reported their hands. This is
the shape of mistake this file already records once: a reported shine that turned out to be a
shader default 63 of 65 characters shared. Fix the reported one, report the population, do not
sweep.

**That is a useful negative.** The obvious reading of "his hand is crumpled" plus "the add-on
flattens hands" is that he needs rebuilding with `VRM_EXPORT_POSE=rest`, and acting on it would
have meant touching 43 characters to chase a default.

#### What IS unusual about him, and why it still does not close the report

- **His rig has three real fingers.** `RightHandThumb1-4`, `Index1-4`, `Middle1-4`, and
  **no ring bone anywhere**. His little finger is `right_little_*_fused` -- one of ours, from
  `VRM_FILL_FINGERS`, weightless by design.
- **270 vertices on the whole right hand across 9 bones**, against Batman's ~600 across 20.
- `RightHandIndex1` carries no geometry at all, while `Index2` and `Index3` carry 20 and 16.

None of that distinguishes him from characters nobody has complained about. Kronk and Judy Hopps
have fewer finger bones than he does; Vigilante, Peacemaker, Xenomorph and Pomni are all 4 of 5
mapped. **So no measurement in this repo currently separates Elite's hand from hands that are
reported as fine**, and saying so is the honest end of this pass rather than picking the most
alarming number on his row and calling it the cause.

#### What would actually answer it

"Crumpled" is a claim about SHAPE, and every number above is about pose or topology. The
instrument this file already prescribes for that is `HandIsolate` -- keep only the triangles all
of whose vertices are weighted to that hand, switch every other renderer off, frame on the
hand's own axes, and bound the kept triangles by hand rather than trusting
`RecalculateBounds`, which measures the whole vertex array and once framed an "isolated hand"
inside a 1049 x 1200 x 492 mm box.

**It cannot be pointed at him as things stand:** `YargCharHandRender` takes `-vrmList`, and
Elite Terrorist has no surviving `.vrm` -- 25 exist under `Documents/YARG-Characters` and he is
not among them. Either the renderer needs to accept a `.yargchar`, or his source has to be
found. That is the next step and it is a build task, not a measurement.

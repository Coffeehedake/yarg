# Character models (`.yargchar`)

What a model must be, and must contain, to load as a YARG character.

## Why this file exists

There is no written specification for the model itself. The wiki's
[Venue Creation](https://wiki.yarg.in/wiki/Venue_Creation) page is excellent on the **animator**
— trigger names, loop counts, hit frames — and says nothing about the rig, the VRM version, the
bundle layout or how a character is exported; the only export it documents is
`Export Background` → `.yarground`. The asset-sourcing guidelines pinned in `#venue-artist` set
**no technical requirements at all** — that document is entirely about licensing. The remaining
knowledge is a 22-minute tutorial video in a role-gated Discord channel.

So the specification below was **read out of this repository's own source**, on 2026-11-06, at
the commit this file lands in. Every claim cites the code that makes it true.

The pipeline that applies it lives in [`tools/character-pipeline/`](../tools/character-pipeline/)
— a Blender builder, a Unity exporter and the diagnostic scripts each trap below was found
with. The **characters** it produces are personal-use conversions of third-party models and are
deliberately not in this repository.

## Status of each claim

| Confidence | What it covers |
|---|---|
| **Verified by building 59** | The whole pipeline, end to end — on 2026-11-07 we exported a `.yargchar` from a VRM and watched it load, render and idle in the character selector, then converted 58 more third-party models through the same pipeline. Only that first one has been watched **in game**; the rest are verified by measurement and by rendering the pre-export scene, which is a weaker claim and is why the traps below are stated as measurements rather than as appearances |
| **Verified by running it** | The install location, and that a stock `.yargchar` loads and renders in a self-built fork |
| **Read from source** | The remaining details below — the bundle layout and the animator contract |

The one thing a file cannot tell you from outside: a `.yargchar`'s block data is compressed, so
`strings` on a shipped bundle yields only its `CAB-…` archive name. The internal layout below is
what the loader *asks for*, not what was observed inside someone else's file.

## The container

A `.yargchar` is a **Unity AssetBundle**, not a model file. It begins `UnityFS`. You cannot
rename a `.vrm` into one.

| Requirement | Value | Source |
|---|---|---|
| The root asset | A `GameObject` at **`Assets/_Character.prefab`**, loaded lowercased | `BackgroundHelper.CHARACTER_PREFAB_PATH`; `BackgroundManager.GetCustomCharacterFromBundle` |
| macOS shaders | A sibling bundle `_character_metal_shaders.bytes`, materials cloned with the prefix `_metal_` | `BackgroundHelper.CHARACTER_SHADER_BUNDLE_NAME`, `BACKGOUND_OSX_MATERIAL_PREFIX` |
| Display name | **VRM metadata first**, filename as fallback | `CharacterDisplayManager.LoadCharacterFromFile` |

The Character Select screen reads `Vrm10Instance.Vrm.Meta.Name` and `.Authors`, and only falls
back to `Path.GetFileNameWithoutExtension` when the name is null or whitespace. The author line
under the podium is `Meta.Authors` — joined with commas when there is more than one, and the
localised *UnspecifiedAuthor* string when the list is empty. Verified 2026-11-07: a VRM whose
meta carried a single author rendered that author verbatim beneath the character.

The settings picker is the one place that *is* filename-only
(`CustomCharacterSetting.ValueToString`), so the two can disagree. Set both to the same thing.

## The model

| Requirement | Detail | Source |
|---|---|---|
| **VRM 1.0** | A `Vrm10Instance` component on the root. VRM 0.x must be migrated first | `VRMCharacter.Initialize` |
| **Humanoid rig** | Unity humanoid, driven by YARG's own animations | `VenueCharacter`, animator contract below |
| **Finger bones** | `RightHand`, `RightThumbDistal`, `RightIndexProximal`, `RightIndexIntermediate`, `RightLittleProximal`, `RightLittleDistal` are fetched **by name** to shape a vocalist's mic grip | `BackgroundManager`, commit `b712ad83` |
| **Visemes** | The standard VRM expressions `Aa`, `Ih`, `Ee`, `Ou`, `Oh`, plus `Blink`, drive lipsync | `VRMCharacter.GetExpressionKey`, `TryGetExpressionKey` |
| **Custom expressions** | Every clip in `Vrm.Expression.CustomClips` is keyed **by clip name** and addressable from chart events | `VRMCharacter.Initialize` |
| **Spring bones** | Driven at runtime — wind, and a pause so hair and cloth do not flail when the character is moved | `VRMCharacter.SetWind`, `SetSpringPause` |

Missing finger bones broke the game outright until **2026-10-31** (`b712ad83`, *"Don't break
completely when custom characters are missing hand bones"*). Treat a fully rigged hand as
required; the tolerance for one is weeks old.

### The right hand is clamped shut on purpose

`DefaultController` has a second layer named **`Hold Microphone`**, and in its clips every
`RightHand.*` finger muscle is a **two-key constant** at a closed value, while the matching
`LeftHand.*` muscles carry 19–31 keys and animate freely:

```
R 'RightHand.Index.2 Stretched'  keys=2  range=[-0.615,-0.615]  CONSTANT
L 'LeftHand.Index.2 Stretched'   keys=30 range=[ 0.182, 0.498]  animated
```

So a vocalist's right hand holds a fixed grip while the left performs. This is **not** a rigging
fault, and it is worth knowing before you go looking for one: a correctly weighted, correctly
mapped hand still renders as a motionless fist.

Two consequences:

- **In the character-select screen there is no microphone in it.** `AddMicrophoneToCharacter`
  runs from `BackgroundManager.LoadCharacter` — the gameplay path only — so the selector shows a
  fist closed around nothing.
- **The grip was authored for slim hands.** A bulky or armoured hand closing to the same muscle
  values will self-intersect and look crushed. Relaxing it means supplying your own controller
  and setting `UseCustomAnimations`, which costs you the stock performance animations.

Nothing requires an anime style. MToon is the convention, not the contract — the project's own
macOS shader bug report tested URP Lit materials alongside MToon ones on the same model.

## Materials must be URP

**This project renders with URP** (`com.unity.render-pipelines.universal`). A material on the
built-in pipeline's **`Standard`** shader compiles, bundles and loads without a single warning,
and then draws **solid magenta** in game, because an SRP cannot render it.

This is a trap worth naming, because it does not look like a missing asset:

```
[YARGCHAR] MAT 'Silver Part' shader='Standard' findable=True
```

`findable=True`. The shader is present — it is simply the wrong pipeline's. Searching for an
absent shader finds nothing and the bundle build reports success.

It bites specifically when the VRM did **not** come from a VRM-native authoring tool. A VRM
carrying `VRMC_materials_mtoon` imports onto `VRM10/MToon10`, which the player ships, and works.
A VRM exported from Blender as plain glTF PBR has no MToon extension, so UniGLTF imports it onto
`Standard` — and you get a magenta silhouette on the podium.

Fix it before export by retargeting every material to **`Universal Render Pipeline/Lit`** (or to
`VRM10/MToon10` for a toon look), carrying the maps across:

| From glTF/Standard | To URP/Lit |
|---|---|
| `_MainTex` | `_BaseMap` (and `_BaseColor` for the tint) |
| `_BumpMap` | `_BumpMap` + enable `_NORMALMAP` |
| `_MetallicGlossMap` | `_MetallicGlossMap` + enable `_METALLICSPECGLOSSMAP` |
| `_EmissionMap` | `_EmissionMap` + enable `_EMISSION` |

Both shaders resolve in the editor (`URP/Lit found=True  MToon10 found=True`), so either is a
valid target.

## Ship an animator controller

`BackgroundManager.LoadAnimationDefaults` assigns `Animations/{Type}/{genre}/DefaultController`
from Resources at **gameplay** when a character has none, so a controller-less character still
performs on stage.

**The character-select screen has no such fallback.** `CharacterDisplayManager` instantiates the
prefab only to read its name and author; it never touches the `Animator`. A character that ships
no `RuntimeAnimatorController` therefore stands in its bind pose — usually a T-pose — in the
picker, while the ones that ship one idle normally. Two of the nine characters measured on
2026-11-07 had this, and it is cosmetic only.

Assign `Assets/Resources/Animations/Vocals/Default/DefaultController.controller` to the Animator
before exporting and the character idles in the selector too. Gameplay still overrides it unless
`UseCustomAnimations` is set, so this costs nothing.

## A valid avatar is not enough: the mesh must be skinned

A character can have a humanoid avatar that reports `isHuman` **and** `isValid`, an animator
controller, and all six bones YARG needs for the microphone grip, and still be incapable of
moving a single vertex. Unity drives the skeleton; the skeleton only drags geometry with it
through a **`SkinnedMeshRenderer`**. A mesh exported as a static `MeshRenderer` is parented to a
node and nothing more.

Measured 2026-11-07 on a hand-built cartoon rig. In Blender every mesh was correctly parented to
the armature, carried an Armature modifier and had 65–71 vertex groups naming real bones. The
exported VRM had **18 mesh nodes and not one of them referencing a skin** — a skin existed, with
75 joints, and nothing used it. In engine the avatar built, the controller ran and the character
stood perfectly still.

The cause was residual object transforms. The VRM exporter writes a mesh as a static node
carrying a scale rather than as a skinned one when the object is not at identity, and the scale
that survives is easy to miss:

- `matrix_basis` does **not** include Blender's delta transforms. Clear the basis, leave a
  `delta_scale`, and the object still has a non-identity `matrix_world` — so assert on
  `matrix_world`, never on `matrix_basis`.
- Baking a child's transform does not bake its parent's. `transform_apply` on a mesh parented to
  an armature bakes only that object's own local matrix; Blender pushes the parent's share into
  `matrix_parent_inverse` so the viewport does not jump. Detach every object first, bake each as
  a root, then re-parent with an identity parent inverse.

**Check the exported file, not the editor's report.** Parse the glTF JSON and count how many
nodes with a `mesh` also have a `skin`. The answer should be all of them. Nothing upstream of
that file — not the viewport, not `isValid` — distinguishes a character that will move from one
that will not.

## The skeleton must be a T-pose facing -Y

VRM 1.0 requires it and Unity builds the humanoid avatar on that assumption, so a model that
ships otherwise is not merely untidy — every arm muscle is retargeted from the wrong rest
orientation. In game it reads as **arms bending the wrong way the moment an animation plays**,
while the character looks perfectly fine standing still.

The measurement that identifies it: compare the upper-arm bone's head to the hand's. A T-pose has
them far apart in **X**. A character whose arms hang at its sides has them at the same X — Pomni's
both sat at 0.1030, while the two characters that looked right, the Xenomorph and Prix, both ran
shoulder-to-wrist along X.

**Before correcting it, look for a T-pose the file already contains.** A rig auto-rigged on
mixamo.com carries its T-pose in an **animation**, not in the rest skeleton; the rest skeleton is
whatever the uploader supplied, and that is usually arms-down. Two measured: Sonic HD rests 57.9
degrees off X, Yoda 93.4. A pipeline that drops every attached action on sight — which is the
right default, since most clips in these archives are jumps, ragdolls and walk cycles — throws
away the only T-pose in the file and then has to rebuild one.

A rebuilt one is not as good, and the gap is invisible to any measurement of *direction*. The
synthesized rotation puts the arm **on** the X axis while carrying no information about the limb's
axial **roll** or the orientation of the hand, so the arm arrives twisted along its own length. It
reads as a wavy, squiggly arm, and on a robed character it webs the sleeves to the body. An
animator posed the clip and got all of that right.

So measure both poses and keep the better one. The test has to be narrow, because a clip that is
*not* a T-pose must still be dropped:

- the animated pose's arms within 10 degrees of X, and the rest pose's not
- the animated pose's **legs** within 20 degrees of straight down

The leg test is what separates a T-pose from a frame of motion; arms alone are not enough, because
a jump or ragdoll frame can have one arm out. Do **not** substitute a test on the root bone's
translation: Mixamo's own T-pose clip moves the hips 11 units of a 57-unit rig, so a drift test
rejects the very pose the check exists to keep.

**Take every angle in world space.** Bone heads live in the armature's own space, and an FBX import
leaves the armature object rotated 90 degrees about X so the source's Y-up becomes Blender's Z-up.
Measured in that local space Sonic stands 57 units tall along **+Y**, and a perfectly straight pair
of legs reads 87.9 degrees away from -Z — so a real T-pose looks like a frame of motion and the
check above rejects it. X survives the rotation unchanged, which is exactly why an arms-only test
passes anyway and hides the bug.

When there is no authored pose to keep, correcting it takes three steps, and each has a trap:

- **Converge, do not compute.** One rotation lands on some rigs and not others: on a Mixamo rig
  carrying a shoulder bone, a single computed 53-degree correction left the arm **74 degrees out,
  worse than it started**. Measure after each attempt and apply the remainder.
- **Keep the rotation and nothing else.** Assigning `pose_bone.matrix` can leave scale and
  translation in the basis when the parent chain is not unit-scaled, and a convergence loop then
  re-applies it on every iteration. Gordon Freeman came out **7.58 m wide** — a copper rod.
  Decompose and write back rotation only.
- **Move the geometry with the bones** before making the pose the rest pose, or the mesh keeps the
  old bind. Compute the deformation by hand rather than applying the armature modifier: these
  meshes also carry Solidify and Subdivision, so the evaluated mesh has a different vertex count.
- **Straighten the arm joint by joint, not shoulder-to-hand.** Driving the *hand* onto the X axis
  satisfies every shoulder-to-wrist measurement while leaving the elbow bent, because a bent elbow
  and a straight one can put the hand in the same place. Alcina Dimitrescu's rest elbow bends 5.4
  degrees and her posed elbow 119.3; the correction put her hand on X and left the crimp, which
  pinched the sleeve. Drive shoulder-to-elbow onto the axis, then elbow-to-wrist, measuring each.

**Facing** matters just as much, and is easy to miss because the model still *looks* like itself.
Batman's model faces +X, so the T-pose correction swung his arms front-to-back instead of out, and
his cape, seen edge-on, read as destroyed geometry. Read the facing off the **feet**, which point
where the character does, and turn the whole rig about Z.

Do not trust the feet blindly, though: a cartoon rig can have them splayed sideways. Sonic's point
along -X, which would have cost him a 79-degree turn and taken his already-correct T-pose off axis.
If the arms already lie along X the orientation is right, and only a ~180-degree turn preserves it.

## A hand posed around a prop that is no longer there

Props get excluded because they inflate the bounds or skewer the model, and the hand that was
holding one stays clamped around the hole where it was. Alcina Dimitrescu's cigarette holder is
dropped from the build; her left thumb and middle finger stayed clenched around nothing, which
reads as a mangled hand.

The model usually supplies its own control, and that is what makes this safe to correct
automatically. Her **right** hand's pose is identical to its rest pose on all five finger chains,
to 0.0 degrees, while her left thumb is 125.7 degrees further curled than rest and her middle
finger 112.9 — with the index left straight, which is a holder gripped between thumb and middle
finger. So the rest pose **is** the modeller's own neutral hand, and relaxing the posed hand to
rest reproduces the hand the model already has on the other side rather than inventing one.

Fire only on that asymmetry: one hand at rest, the other 20 or more degrees from it. A character
posed with **both** hands gripping shows no asymmetry and must be left alone — YARG puts a
microphone in the hand, so a deliberate two-handed grip is a real thing to ship. Touch finger bones
only: a blanket reset to rest is a different and far more destructive operation, and it is what
compressed Alcina's head and torso to 59% of their size the first time she was built.

**Measure the shape of the hand, never the direction its bones point.** A direction test also sees
the whole arm's rotation: her right hand measures 65.9 degrees "off rest" purely because her static
pose lifts that arm, and the asymmetry the check depends on vanishes. Compare **curl** — the angle
between consecutive bones, summed down each finger — which rotating the whole hand does not change.

## VRM checks the hierarchy, not the names

Every humanoid bone must be a descendant of the one above it, **and the chain must not pass through
another mapped bone**. The export cancels with a message naming only the bone it gave up on, which
says nothing about the real cause. Four shapes of this turned up in a single batch:

| What the rig does | Example | What it needs |
|---|---|---|
| Legs hang off a *sibling* of the pelvis | Batman: spine under `C_pelvis`, legs under `C_pelvis_att` | Hips is the nearest common ancestor of the spine and both legs |
| Legs hang off the **spine** | 3ds Max Biped: thighs parented to `Bip001 Spine` | That bone is really the hips — promote it and shift the spine chain up |
| Shoulders hang off the **neck** | 3ds Max Biped again: `Bip001 L Clavicle` under `Bip001 Neck` | Re-parent: reaching the right ancestor is not enough if a mapped bone sits between |
| The rig is **flat** | Tenna: a Rigify DEF export whose shoulders, arms and thighs were all unparented roots | Rebuild the hierarchy from the map |

Re-parenting at rest is **deformation-neutral** — the armature reads `bone.matrix_local`, which
re-parenting does not move — so repairing the hierarchy costs nothing and can be automated.

## Spring bones need bones

Hair, a skirt or a cape stays rigid however well the character animates, because Unity's humanoid
rig has no muscle for it. VRM moves them with spring bones and YARG drives those at runtime, but
only if the chains exist in the skeleton. Three of five models checked had their hair skinned
straight to the head bone with no chain at all, so there was nothing to spring.

Where chains do exist, detect them rather than naming them per model — `hair`, `ponytail`, `braid`,
`bang`, `tail`, `skirt`, `cape`, `coat`, `hat` and the like — excluding any bone that is also a
humanoid bone. Two things are easy to get wrong:

- **Follow every branch.** A walk that takes only the first child silently sprang one of Prix's
  three hair strands and left the other two rigid, because all three hang off a shared `hairAll`.
- **A bone may belong to only one chain**, so emit a shared trunk separately rather than repeating
  it in every branch.

Chains can also be **built** for a model that has none: find the hair by mesh or material name,
anchor the top third to the head, split the loose remainder into strands, run a short bone chain
down each, and weight the hair onto them with a ramp that holds it to the scalp. Verify by **posing
the chains**, never at rest — at rest every weighting is the identity, so a torn rig and a good one
look exactly alike. And clear whatever held the hair before: a model that keeps its hair on one
rigid bone leaves that weight at 1.0, and the armature normalises by total weight, so the old bone
simply out-votes the new chain.

## Three ways a material lies

- **Emission with no map.** An imported material can carry a leftover white emission colour, and
  the exporter writes it out as `emissiveFactor [1,1,1]`. The surface then glows pure white and
  drowns its own base colour. Thanos had a blank face for this reason while his armour textured
  correctly, and every obvious check came back clean: the texture was a real purple map, the UVs
  were healthy, the normals were sound, and the exported file genuinely carried the right
  `baseColorTexture`. The proof was dimming the render lights to 15% — everything went dark and
  **the face stayed pure white**, which over-exposure cannot do. Zero emission wherever no emissive
  map is wired; a material that really glows has one.
- **Alpha mode is not inferred.** Blender 4.2 removed `Material.blend_method`, and with nothing
  left to read the VRM add-on wrote `alphaMode=BLEND` for **every** material in the file, skin and
  all. Blended opaque geometry sorts against itself and samples the base map's alpha channel, which
  turned one character's skin into brown and white blotches. Set `mtoon1.alpha_mode` explicitly.
- **Texture matching needs more than the material's name.** Materials called `ai_skin`, `phong1` or
  `lambert8` name nothing. Try, narrowest first: files naming the material; files sharing a *word*
  with it (`shoes` and `sonic_shoes`, which slug matching misses); files sharing a word with the
  **mesh** it sits on (`female_body_Prinx` and `body 3_initialShadingGroup_BaseColor.png`); then
  everything. Never let the widest pool assign a base colour to a material that already carries a
  real one — doing so handed Pomni's flat Blue, Red and Yellow an unrelated texture and wiped her
  colours out.

## What actually arrives in an archive

Converting 45 downloads turned up the same handful of surprises repeatedly. Check for them before
blaming the pipeline:

- **Props inflate the bounds.** Alastor's microphone sat 3 m from his body, so scaling to a target
  height shrank *him* to a doll. Jessica Rabbit arrived with a mic stand skewering her.
- **Empty placeholder meshes.** Four of the B1 droid's five mesh objects had zero vertices. They
  still count as meshes, so the real geometry can be mistaken for scenery.
- **Two half-characters on two armatures.** Batman ships a body and a separate cape-plus-head
  attachment, the cape mesh being 2,099 vertices of which 1,901 are cape. The body skeleton carries
  the cape bones too, so rebind the cape onto it and discard the second armature.
- **Inverted-hull outlines.** A Solidify shell plus a black "line art" material draws an outline in
  Blender; exported, the shell is just more geometry and wraps the character in translucent
  duplicates.
- **Unrigged bodies.** A mesh with no armature modifier and no vertex groups exports as a static
  node. Automatic weighting can sometimes rescue it, but only after excluding the `_end` tips an FBX
  import adds and any facial bones — both sit inside the mesh, and bone-heat hands them whole limbs.
  Where it will not converge, **mixamo.com's auto-rigger** is the answer rather than more weighting
  experiments; see the open questions, where this is now measured rather than open.
- **The texture folder is the whole extracted archive.** It also holds the `.fbx`, the `.blend`,
  `readme.txt` and a `.mtl`. Left in the candidate pool those compete as textures like any other
  file — and since the last-resort rule is "largest file first", the **model** is the strongest
  candidate in the folder. Yoda's eye material was assigned `yoda_rigged.fbx` and his eyes rendered
  magenta, which reads as a missing texture rather than as a texture that is a 3D model. Blender
  reports only `failed to load image buffer`, one line among a hundred packing warnings, so nothing
  in the build output looks wrong. Filter the listing to image extensions.

  It only bites a material with **no other candidate**: two other models load a model file the same
  way and came out correct, because every one of their materials had a packed image to win with.
  Finding that line in a log does not by itself mean the build is wrong — check whether a material
  actually took it.
- **A part can be textured in one container and not another.** Yoda's USDZ carries no eye map at
  all; the original `.zip` of the same character does. Merging both folders and pinning the material
  to the file by name is cheaper than re-authoring the map.

## Rig families mapped so far

Each is a bone-naming convention rather than a tool. Recognise it from the bone names and the rest
of the pipeline is identical.

| Family | Tell |
|---|---|
| Mixamo | `mixamorig:Hips`, or the same names under another prefix |
| Reallusion / Character Creator | `CC_Base_Hip` |
| Rigify | `DEF-spine`, or the same names with no prefix |
| Unreal mannequin | `pelvis`, `clavicle_l`, `thigh_l` |
| Renderpeople | `<scan name>_upperarm_l` |
| DAZ Genesis | `lShldrBend`, `lThighBend` |
| Source engine | `ValveBiped.Bip01_L_UpperArm` |
| 3ds Max Biped | `Bip001 L UpperArm` — space separated, prefix varies |
| Advanced Skeleton | `Root_M`, and `Shoulder_L` is the upper arm |
| Auto-Rig Pro | `root.x`, `arm_stretch.l` |
| MultiVersus | `fml_un_L_uparm` |
| Maya namespaced | `<ns>:jnt_l_arm_wrist` |
| Smash Bros / NUD rip | `_15_-_LShoulderJ` — every bone numbered in hierarchy order. The ordinal is position, not identity, so map on what follows it; `LShoulderN` is the clavicle and `LShoulderJ` the upper arm |
| Zelda OoT (Blender rip) | CamelCase parts with `.l`/`.r`, a numbered `Spine_NN` chain, and the forearm spelled `Upperarm.l.001`. A parallel `_ik` skeleton sits beside it and must **not** be mapped — an IK control is not a deform bone |
| Mario N64-era rip | Short Maya-style joints with an `L_`/`R_` prefix (`L_Shold`, `L_Elb`). No chest bone, and the clavicles hang off the **neck** |
| Hand-built | Meaningless `Bone.0NN`; map it by reading the hierarchy |

## The animator contract

From the wiki page, which remains the authority here, and from `VenueCharacter`:

| Thing | Name | Notes |
|---|---|---|
| Speed | float **`SpeedAdjustment`** | Multiplier on Idle and Playing, "Parameter" ticked |
| Variation | int **`RNG`** | Detected by name; absent means no variation | 
| Bends | bool **`isBend`** | *Can Transition To Self* unchecked |
| Hand shapes | **`HandPositionOne`** … **`HandPositionTwenty`** | Triggers, exact names |
| Strums | **`StrumUp`**, **`StrumDown`**, **`Pick`**, **`Slap`**, **`Finger`** | Other strum states go in `Strum Up States` |
| Drums | **`Kick`**, **`OpenHat`**, and the rest of the kit | |
| Loop size | `Actions Per Animation` | 8 for a drummer, 10 for a strumming guitarist |
| First hit | `FramesToFirstHit` | The frame the strum or hit visually lands |

`RNG` is read as `Animator.StringToHash("RNG")` in `VRMCharacter.Initialize`, so the parameter is
found by name or not at all.

`VenueCharacter.Type` is one of **`Guitar`, `Bass`, `Drums`, `Vocals`, `Keys`**, and
`CharacterGender` picks the default singer for a song's vocal gender tag.

**Today only `Vocals` is reachable from a file.** The picker and the gameplay path both write and
read `CustomCharacters[CharacterType.Vocals]` only (`CharacterDisplayManager`,
`BackgroundManager.GetCustomVocalsCharacter`). The other four types exist in the enum and in
venues.

## Measure the base mesh, not the scene

**A morph target's weight is zero in engine.** Whatever the authoring tool composites for its
viewport, the base mesh is what YARG renders — so a build that measures the evaluated scene can
describe a model that will never exist.

Measured 2026-11-07, and it cost three rounds of wrong diagnosis. A downloaded FBX shipped 37
shape keys with six set to non-zero values, at least one holding a corrupt body four times
oversized. Blender's viewport, `evaluated_get()` bounds and every render therefore agreed the
character was 1.95 m of tangled shards. The base mesh — the real character, a clean T-pose — was
0.478 m. The builder scaled to make the *garbage* 1.70 m, which left the real geometry at
**0.416 m**, and that is exactly the size the character arrived at in game.

Every symptom pointed at a scale bug: it looked like a unit conversion, then like a scale trapped
in the armature's bind pose. Both stories fitted and both were false. The giveaway was that the
evaluated bounds and the raw vertex data disagreed, which no amount of rescaling can reconcile.

So, when preparing a model:

- Zero every shape key and keep the base mesh before measuring anything. This is strictly more
  faithful than collapsing at the author's values, because zero is what the engine uses.
- Assert on the **raw vertex extent** after baking, and make it fatal. The scene measuring 1.7000 m
  proves nothing — it measured exactly that in both of the builds that shipped broken.
- Render the result before shipping it. A metrics-only check passed a model that was visibly
  shattered; a 700×1000 front render took seconds and settled it. Render a known-good character
  through the same path first, or an empty frame reads as a pass.

## Exporting

There is no tool. The exporter is an editor context menu inside this project:

1. Open the fork in **Unity 6000.3.5f2** (the pinned editor — see `docs/WORKSPACE.md` in
   `yarg-song-server`).
2. Put the VRM on the venue's replaceable vocalist.
3. Right-click the **`BundleBackgroundManager`** component → **Export Vocalist**.

`BundleBackgroundManager.ExportCharacter()` → `BackgroundHelper.Export(…, ExportType.Character)`,
both `#if UNITY_EDITOR`. A standalone content-creation package has been
[proposed upstream](https://discord.com/channels/1086048856678084609/1530274700989825084) and is
still an open suggestion with no replies.

### It can be driven headlessly

`BackgroundHelper.Export` has **two** overloads. The one the context menu calls opens an
`EditorUtility.SaveFilePanel`; the other takes an explicit `path`. The second makes the whole
thing scriptable from `-batchmode`, with no editor window and no dialog:

```
Unity.exe -batchmode -nographics -quit -projectPath <repo> \
  -executeMethod <YourClass>.<YourMethod> -logFile <log>
```

Proven on 2026-11-07. Gotchas that cost time:

- **The prefab must carry a `VRMCharacter`** with `Type = Vocals`. There is no null check —
  `BackgroundManager.LoadAnimationDefaults` dereferences it immediately, so a bundle without one
  throws rather than degrading.
- **`Unity.exe` detaches on Windows.** The launcher returns instantly with exit code 0 while the
  editor carries on in another process. Waiting on the launcher looks exactly like a silent
  failure; wait on the `Unity.exe` process that holds the project lock instead.
- **Export always builds a `StandaloneOSX` shader bundle first** and throws `FileNotFoundException`
  if the module is absent. "MacOS Build Support (Mono)" is required even to export on Windows.
- Quote paths. `-projectPath` splits on spaces if the arguments are passed unquoted.

## Installing

`<persistent data>/<release channel>/custom/characters/*.yargchar`

The channel subfolder is **not** the git branch. This fork's builds report channel `release`, so
they read `…\FatalException\YARG-FE\release\custom\characters\`, even though the branch is `dev`.
A file in the wrong channel folder produces *"No characters available"* with no error anywhere —
the Character Select screen simply found nothing. Check which folder a running build touches
before concluding the model is bad.

## Clearance

The sourcing guidelines are licensing-only, and they are strict. A model is usable if it is
original YARG-community work, covered by a signed agreement, or under a Creative Commons licence
that is **not** no-derivatives. Anything carrying bare terms of use needs review by the YARG team
before it can be shipped, non-commercial use must be permitted, and non-original assets must be
credited in the launcher or in-game.

That is why no public library of `.yargchar` files exists: the cleared set is a Drive folder
pinned in `#venue-artist`, and a Setlist Manager's own answer to "is there anywhere more
organised?" was *"you probably aren't going to find any place more organized than right here"*.

## Known traps

- **VRM 1.0 rejects a negative scale**, and the export *cancels* rather than warning. One
  mirror-duplicated eyelash with `scale = -1` on an axis is enough to stop the whole file being
  written. Bake the mirror into the geometry and flip the winding to match.
- **The VRM add-on's validator wants a `CollectionProperty`,** not a list. Hand `detect_errors`
  a plain list and it raises `AttributeError`, so a cancelled export reports no reason at all.
- **VRM 0.x will not load.** `GetComponent<Vrm10Instance>()` returns null and `Initialize` dies.
- **macOS transparency is broken** for UniVRM10 MToon materials in front of opaque geometry —
  reported 2026-02-23 with a four-eye test rig; Windows under Vulkan and DX11 is correct.
- **Materials need Mac-specific settings** before a bundle is shared, per the maintainer.
- **`_browAggressive`, `_browDown`, `_browOpenmouthed`, `_squint`** are declared in `VRMCharacter`
  and assigned nowhere in the project. The expression surface is still moving.

## Open questions

Not answered by the code, and worth measuring before authoring anything expensive:

- **Scale and height.** Nothing normalises the model. A figure built at **1.70 m**, feet on z=0
  and centred on the origin, sits correctly on the podium — measured 2026-11-07. Whether the
  podium tolerates much taller or shorter is still unmeasured. Measure the base mesh — see
  *Measure the base mesh, not the scene* above.
- **Polygon and texture budget.** No limit is enforced or documented. The eight cleared models
  run 5.6–10.7 MB as bundles. A deliberately heavy character — 639,859 triangles with 1K
  textures — bundled to **31.4 MB** and loaded and rendered without complaint, so the ceiling is
  well above the cleared set. Note the compression ratio: that same model was a 63 MB `.vrm`.
  Geometry is cheap in the bundle; textures dominate. Dropping 4K maps to 1K took the `.vrm`
  from 215 MB to 63 MB, while discarding 73% of the triangles saved only ~24 MB and visibly
  faceted every curved panel.
- **How far automatic weighting can rescue an unrigged body — now answered, and the answer is
  "not far enough; use a service".** One model arrived with a 17,064 vertex body carrying no
  armature modifier and no vertex groups at all. Binding it is easy; binding it *well* is not.
  Excluding the `_end` tips and the facial bones moved the arm bones into the top weights, but the
  arm geometry still would not follow the skeleton into a T-pose, and a further attempt tore the
  arms apart instead. Occlusion-aware variants were tried twice and made it worse. The skeleton was
  provably right throughout — upper arm and hand shared a Z and ran along X — so the failure was
  always in the binding, not the rig. The route that works is to upload the bare geometry to
  **mixamo.com's auto-rigger** and build from what comes back; four models were rescued that way.
  Note what the download actually is — a rest skeleton in the uploader's own pose plus a T-pose
  *animation* — and keep that animation, per *The skeleton must be a T-pose facing -Y*.
- **Whether a non-`Vocals` type loads from a file at all**, or only from a venue.
- **What a missing viseme does** — silent fallback, or a visible mouth stuck shut.

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

## The bind pose is not always the rest pose

A rest pose is where the skeleton sits; a **bind** pose is the configuration the geometry was
built around. Usually they are the same and the distinction never comes up. On a posed sculpt
they are not.

Anakin Skywalker ships as `anakin pose.fbx`: one character frozen in a mid-air leap, a skinned
head, and sixteen thousand vertices of body carrying no armature modifier and no vertex groups at
all. Measured against those unrigged meshes, his bone midpoints sit **0.443 m** from the nearest
vertex at rest and **0.067 m** posed. At rest the skeleton is not inside the body, so there is
nothing to weight to; the leap is where the model actually lives.

Measure it on the **unrigged** meshes, and on raw vertex coordinates. A skinned mesh stores its
vertices at bind position, so for those the rest pose wins by construction and the comparison is
circular. An unrigged mesh is static geometry, so where it sits is evidence.

Two things follow, and both bit:

- **Settle the rest pose before anything binds to it.** A bind is expressed relative to rest, so a
  rest pose that changes afterwards is applied twice to everything bound before the change and
  once to everything bound after. Anakin's body was auto-weighted while the armature stood in his
  leap and the leap was baked into rest underneath it; he exported in pieces.
- **Weights authored against the discarded rest are stale.** His head, eyes, hair and shoulder
  tabards — the only parts the file itself had bound — then floated half a metre above a perfectly
  good body. Neither binding was wrong; they were not the same binding. Dropping those few rigid
  attachments and re-binding everything in one pass fixed it. This is opt-in, because a properly
  skinned character carries real weights worth keeping.

## Do not reimplement the armature modifier

Baking a pose into the rest pose means moving the geometry with the bones, and the obvious way to
do that is to sum `w * (pose @ rest-inverse) @ v` over each vertex's groups. That expression looks
exactly like the armature modifier and is not it. Weight normalisation, unweighted vertices and
the object's own parenting all feed into the real deform.

It is wrong in a way that hides: on Anakin it left every unrigged mesh correct to 0.000 m and
moved the one mesh that was already skinned — his head — by **0.523 m**. One mesh out of fifteen.

Evaluate the object with only its armature modifier enabled and copy the result back. `to_mesh()`
returns coordinates in the object's own space, which is what the base mesh wants, and a deform
modifier cannot change the vertex count. This is also why the stack cannot simply be applied: a
Solidify or Subdivision ahead of the armature *would* change that count.

## A T-pose is a STANDING pose

Every arm measurement assumes a spine that runs up +Z. Anakin's lies **102 degrees** off vertical,
so the arm correction put both arms neatly along X and left him lying flat on his face — a
character that passes every check in this document while being unusable.

Standing one up takes three steps, in this order:

1. Turn the whole rig until hips→head runs up. A whole-object rotation cannot break a binding.
2. Straighten each leg onto -Z joint by joint. A global rotation cannot do this, because the legs
   are folded *relative* to the spine.
3. Re-aim the facing. The facing step runs much earlier, and standing him up spun him about the
   vertical axis as well.

Two traps. `Armature.transform()` did nothing at all here — hips→head read `(-0.748, -0.385,
-0.183)` before and after, to three decimals — so write `EditBone.matrix` instead, which carries
head, tail and roll together. And **converge**: a connected bone's head is pinned to its parent's
tail, so setting every bone's matrix at once is not the rigid rotation it looks like. One pass took
102.3 degrees only as far as 76.3.

Keep this **opt-in**. Measured automatically it fires on characters that are already standing —
Sonic reads 115.4 degrees "off vertical" while standing perfectly upright — and standing an
upright character up is a regression, not a fix.

## Where automatic weighting actually gives out

Not at "unrigged", which the Mixamo route handles. At **contorted**.

Bone heat decides a vertex's owner by proximity, so two body parts that touch in the bind pose
share weights. That is harmless while they stay together and tears the moment they separate:

- Anakin binds with one knee folded against his chest. Every bone ends up measuring 0.0 degrees —
  spine vertical, legs down, arms along X — and one leg's *geometry* still smears across the robe,
  because the bones moved and the vertices were never only that leg's.
- Judy Hopps binds with her arms straight down against her body, 86.6 degrees off X. Her rest pose
  is a far better 40.2, but her geometry was sculpted in the posed one, so that is where the bones
  are. Straightening the arms webs them to her torso.

The tell is precise and worth knowing: **the bones measure correct and the mesh does not follow.**
When that happens the rig is fine and the weights are not, so more rig correction will not help.
Re-rig the bare geometry from scratch — see the open questions — rather than refining the pose.

## Numbered rigs come in families

Bones called `n8`, `n115`, `Bone.057` carry no information, so the map has to be read off the
hierarchy and the rest positions. That was done by hand for Judy Hopps and for the Mandalorian,
and the third time it turned out not to be a third time at all: **Peacemaker and Vigilante are the
same rig.** Identical tree, identical rest positions to three decimals, and names offset by a
constant — Peacemaker's hips are `n115`, Vigilante's are `n8`, and every other bone sits the same
distance behind.

So a family of this kind is a table of OFFSETS from the hips, and the hips are found rather than
named: the parentless bone with three children, which in a numbered rig is the only thing that can
be the junction of a spine and two legs. Then **check every name the table produces exists**, and
abort if one does not. Without that check a wrong base does not fail, it maps a leg to a finger.

Reading one of these takes four numbers per bone and nothing else:

- **The spine** is the chain from the hips to the furthest bone along the body's long axis.
- **Thumb or finger**: a thumb's first bone starts at the PALM, level with the wrist; the fingers'
  proximals start out at the knuckles. Peacemaker's thumb is two bones beginning at x 0.585 with
  his hand at 0.581, so the first of them is the metacarpal and the distal joint is simply absent.
  Leave it unmapped. A finger bone on the wrong joint is worse than a missing one.
- **Which finger is which**: they run in order across the hand, so sort them on the across-hand
  axis and the sequence is index to little. Confirm it with chain length — the little finger is
  always the shortest — and with the thumb, which sits beside the index.
- **Left or right** comes off the sign of X, never off the name.

### Do not generalise this into an automatic mapper

It is tempting, and it was tried. A mapper that found the extremities and walked the hierarchy was
checked against the two rigs already mapped by hand, and on Judy it returned `hips n15` with
`chest` ALSO `n15`, both legs sharing one chain, and a fingertip for the hand — against a
hand-written map of `hips n14 ... head n28` that is known to build 47 of 47. It took four lines of
output to reject.

The check is the point. Validating a new mapper against rigs whose answers are already known costs
one run, and it is the difference between finding this out now and finding it out in a render.

## A skeleton can be in the file and not be in the MODEL

A rig that deforms the mesh is not necessarily a rig that fits it. The Fortnite
Mandalorian ships two complete skeletons, a Mixamo-named one and an Unreal-named one, and
**both are collapsed**: his foot bone sits at z -150.40 and his head bone at z -149.76, two units
apart, on a mesh 144 units tall. Every bone is stacked at roughly one height.

He still renders perfectly, because at rest the deformation is the identity and the vertices sit
where the artist left them. Nothing is visibly wrong until something moves a bone -- and then the
whole character smears, which is exactly what the T-pose correction did to him.

So before trusting a skeleton, check that it is **inside** the mesh: mean distance from bone
midpoints to the nearest vertex, against the mesh's own size. The same measurement that identifies
a bind pose (above) identifies a useless skeleton, and a rig whose head and foot share a height is
not a rig at all. The fix is the same as for no rig: re-rig the geometry.

## An absent map is an answer

Texture matching fills gaps, and for a base colour that is right: every material has one, so the
widest guess beats no texture at all. **An opacity map is the opposite.** Most materials have none,
so absence is the normal answer rather than a gap, and a wrong one does not miscolour the mesh, it
deletes parts of it.

Scott Hall's folder holds exactly one opacity file, `Hall_eyelash_opacity.png`, and all forty of
its filenames begin with `Hall`. So the pool of "files sharing a word with the material" matched
all forty on the character's own name — which narrows nothing — and that eyelash cutout went onto
his boots, both kneepads, both elbow pads, his tights and his vest. Ranking candidates by size,
which fixed the same map reaching all nine of Prix's materials, cannot help when there is only one
candidate.

So an alpha map now comes from a file that names the material, or not at all. Sweeping all 109
source archives bounds that exactly: 12 contain an opacity-like file, and 11 of those name the
material in the filename (`Bikini_Opacity`, `Hair_Opacity`, `t-800_HP_Head_AlbedoTransparency`).
The twelfth is Power Girl, whose materials are called `mesh0`, `mesh1`, `mesh2`, and she needs
`VRM_TEX="mesh2=Supergirl_A_Hair_Alpha.png:alpha"` — which is why `VRM_TEX` learned to pin an
alpha at the same time, and to REJECT a map kind nothing reads rather than accepting it, printing
it, and doing nothing.

Give a sweep like that a control. "No opacity map in this archive" and "this archive was never
opened" look identical in a count of zero, so the sweep reports each archive's image count beside
its opacity count: 75 archives hold images and no opacity map, which is a real zero, and 23 hold
no images at all, which is a different fact entirely.

## A second figure in the file sets the height

Peacemaker's USDZ carries two skeletons, and the second one is not a duplicate of the first — it
is a fragment of a DIFFERENT figure at a different scale. Three small meshes hang off its chest
bone and sit at z 1.54 to 1.85 while his own body tops out at 1.459: a helmet, floating above his
head.

Nothing about that is visible in a bone count or a humanoid count, both of which were perfect. It
shows up in one measurement — the tallest mesh is not part of the character — and the consequence
is that scaling the file to 1.85 m scales the HELMET to 1.85 m and leaves Peacemaker 1.51 m tall,
18% short, with every proportion intact so that nothing looks wrong until he stands next to
someone. Alcina's floating hat was the same failure and cost a 0.5568 rescale of her whole rig.

Check the extremes of the bounding box against the body, not just its size.

## Building a chest bone where there is none

47 of the 66 characters here have no chest bones, so for them the bones have to be built the way
the hair rigger builds hair chains. The method is: find the bust in the geometry, root a short
bone on the ribs behind it, weight a patch of the surface onto that bone, and let the spring
section do the rest.

Finding it is the whole difficulty, and five plausible answers were wrong before one worked.

**The 16 characters that DO carry authored chest bones are the calibration set.** Their skeletons
and their humanoid maps are both inside the shipped `.yargchar`, so 48 authored bones can be read
off without rebuilding anything — and what they say is that there is no such thing as a standard
offset. The bones sit anywhere from 0.10 of the shoulder span out (Ariel's pectorals) to 0.41
(Alcina), median 0.25. A detector built on that median lands on the wrong part of most chests: at
0.25 Alcina's apex came out 11 cm inboard of the bone she already has, pinned against the edge of
its search column, which is what a window in the wrong place always looks like.

So the detector profiles the front surface across the half-chest in bins and takes the peak. The
peak is the apex by construction, and it costs nothing to let the geometry say where it is.

### The four other wrong answers

- **A clavicle is not a shoulder.** Both shoulder bones begin at the sternum, so measuring the
  "shoulder span" between them gave 0.055 m for a 2.9 m Alcina. Every threshold here is a fraction
  of that span, so one wrong number moved the search band, the side split and the protrusion test
  together, and all three still looked reasonable. It is measured across the UPPER ARMS now, and
  asserted against the height of the torso.
- **x = 0 is not the midline.** Nothing promises the character is centred on the origin, and
  Alcina is not: her spine sits at x = −0.131. Her authored bones at +0.050 and −0.311 look wildly
  asymmetric until you notice they are symmetric about her spine, not about zero.
- **The most forward thing on a chest is usually clothing.** Her gown hangs 6 cm in front of her
  body, and the first apex found was one of its frills — rigging that would wobble the GOWN, which
  is a cloth problem and not this one. Several meshes stack in this space: body, underwear, dress.
  The body is the innermost, so the LAYER is chosen first and the apex second.
- **A trace of shoulder weight is not an arm.** Rejecting any vertex carrying 0.05 of arm weight
  threw away all but 61 of Sophia's chest vertices: she is a scan whose shoulder weights bleed a
  little way across the upper chest, which is what good weighting looks like. The test is whether
  the arm OWNS the vertex, not whether it touches it.

### The hinge of a breast is its base

The first bone ran from the spine out to the apex, which looks right in a wireframe and shears the
mesh in motion: a spring rotates a bone about its HEAD, so a long bone swings the whole mass
sideways off the ribcage. On a 30-degree test Prix's bust slid sideways and her bikini cup was
left hanging over a hollow. The bone is now short — rooted on the ribs directly behind the apex,
pointing forward, about as long as the bust is deep — and the same test moves the surface the way
a bust moves.

Judge it at a spring-sized angle, not at the stress-test angle. At 30 degrees everything looks
broken; a chain at 0.85 stiffness reaches about 12, and that is the render to look at.

### What it refuses

It declines a flat chest, and it has to: the protrusion test is what stops it rigging a man.
Peacemaker reads flat, and so does Sophia at 5.9% and 1.6% of her shoulder span against a 6%
threshold — she is clothed and only 8,320 vertices, and on geometry that sparse the two sides
disagree. A detector that refuses is recoverable; one that invents a bust on a low-poly model
ships a defect nobody is looking for.

Protrusion alone is not enough, and the first handful proved it. **Pomni passed it and should
not have:** her chest peaks 0.06 of a shoulder span from her spine and stands 11% proud of the
surface around it, which is a collar, and the rigger built her a pair of bones and weighted 1,414
vertices onto them. So two more tests, both read off the calibration set:

- **A floor on how far out the peak is.** The innermost of the 48 authored bones is Ariel's
  pectoral at 0.10 of the span, so a peak inside 0.12 is something on the sternum.
- **The two sides must agree.** A character is symmetric, so a detector that puts the apex 0.22
  of the span out on one side and 0.30 on the other has found noise on at least one of them.

This is the argument for doing a handful before a rollout: the failure was not a crash or a
missing bone, it was a plausible-looking success on a character nobody would have thought to
check.

### A refusal here is a limitation, not a failure

Everything above refuses because of something about the MODEL, so it is reported that way and
the build carries on. The one time a refusal was wired as an abort it cost Gadget Hackwrench
her whole conversion over a feature that only adds jiggle.

**Not enough mesh to move.** A spring moves vertices, and below a certain count the patch
deforms as a handful of flat facets, which reads worse than a chest that does not move at all.
Gwen Stacy is the measured borderline: 55 front vertices on each side of her chest, against
385 a side for Prix and more for Sayuri. The default floors are 120 front vertices a side to
measure from (`VRM_BREASTRIG_MIN_VERTS`) and 40 in the patch itself
(`VRM_BREASTRIG_MIN_PATCH`).

**Proportion cannot tell a bad humanoid map from an unusual body.** The check exists because
Alcina's "shoulder span", measured between two clavicles that both begin at the sternum, came
out as 0.055 m for a 2.9 m character — and every threshold in the rigger is a fraction of that
span, so one wrong number moves all of them together and each still looks reasonable. But
measured across all 66 installed characters the two ranges **overlap outright**: arm span over
torso height runs 0.203 (Gadget, a chipmunk, whose arms are correctly mapped) to 1.407, while
clavicle span over torso runs 0.034 to 0.554. There is no line to draw, and the first version
of the check drew one at 0.35 and threw Gadget away.

Within any ONE character they never overlap — of the 19 that map both, the clavicle span is
the smaller every time, by at least 2.5x and typically 3.2x. So the rigger asks which pair the
humanoid map actually handed it, which is known rather than inferred, and only refuses when
there are no upper arms to measure between. **Prefer the question you can answer exactly over
the one you have to threshold.**

## A set of one is not a set

Maps ship in sets, and the builder keeps a material inside its own set so a metalness map
cannot be borrowed from the wrong one — Link's tunic took the equipment metalness once and came
out chromed. The set is derived from the base colour's filename with its map token stripped.

**When that strip fails the set contains one file, and "take only from this set" silently means
"take nothing".** Gwen Stacy's files are `GwenStacyDifuselMap.jpg`, `GwenStacyNormalMap.jpg`
and `GwenStacyMetallnessMap.jpg`. The token regex spelled out an optional trailing `map` after
`normal` and nowhere else, so `difuselmap` survived whole, the prefix became her entire base
stem, and her normal and metalness maps sat in the same folder being ignored. She shipped with
a base colour and nothing else.

Two fixes, and the second is the one that generalises: every map token may now be followed by
`map`, and **a set with one member is treated as no set at all**.

### The check that was wrong about Alcina

Alcina looked like the same bug — `Material.014`'s normal and roughness missing from her
rebuild. They were not missing. The comparison script called `os.path.splitext` on an image
called `Material.014_Normal_OpenGL`, which cuts at the LAST dot and leaves `Material`, so every
one of her numbered maps normalised to the same token and the script reported a file that
contains both as having neither.

She was held back for a day on the strength of it, and the fix to the real bug would have been
credited with fixing hers too. **A comparison is a measurement and gets the same scepticism as
any other**: when it disagrees with the build log, find out which one is lying before acting on
either. The build log had said `rough=Material.014_Roughness.png,
normal=Material.014_Normal_OpenGL.png` all along.

## A prop can share a MESH with the kit

An exclude pattern is a blunt instrument: it takes whole meshes, and a model is not obliged to
put the character in one mesh and its props in another. Vigilante's weapons, the sheath on his
back and the holster on his hip are **four islands of one mesh**. Excluding it disarms him and
strips his kit; keeping it leaves a sword and a gun in the hands where YARG puts a microphone.

What separates them is not the name but the BONE: a held weapon is weighted to a hand, worn gear
to the spine or the hips. So `VRM_DROP_ISLAND="<mesh-pattern>=<bone>[+<bone>]"` drops the islands
of a named mesh that a named bone CARRIES — 540 vertices on `n17`/`n50` out, 204 on `n10`/`n8`
left where they are.

**The mesh pattern is not optional, and it is the whole safety of the switch.** A hand is itself
weighted to the hand bone. A bone named on its own would take the hands off with what they are
holding, and the only reason it does not here is that the pattern names the prop's own mesh —
after which the hand islands, 80 vertices each in `Vigilante_obj_Pewter_001_0`, are not even
candidates.

### "Connected" has to mean welded first

The island walk follows EDGES, and a USD import arrives fully split: every face carries its own
copy of each corner and no two faces share one. Run on Vigilante's weapons mesh it reported **146
islands of four vertices each** instead of four islands of 224, 184, 108 and 96 — every quad its
own island. The drop still removed the right vertices, because the test is per-vertex, but the
log became 146 lines of nothing and the rule "most of this island is the hand's" was trivially
true of every single quad. A safety margin that can only ever pass is not one.

So the walk can weld by position first, and the drop asks it to. It is **off by default** because
island RANKS are addressable elsewhere — `island:7+8` picks Miku's twintails, `island:0` pins
Sonic's quills — and welding renumbers them.

### Then look at the hands

Removing what a hand holds is the first half. Alcina's lesson is the second: a hand posed around
a prop stays clamped around the hole. The automatic relax does not fire here, because it needs
one hand at rest to compare against and Vigilante grips with both — so check the hands rather
than assume, and **look from above**, where a curl is visible. His open flat, fingers straight,
thumb clear: nothing to fix. That was luck of the model, not the pipeline being clever.

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

## Promoting the hips orphans whatever was above them

The second row of the table above — "legs hang off the spine, so that bone is really the hips" —
is right, and it has a consequence that went unwritten for a year. Hips is the **root** of the
humanoid, so promoting a bone to hips puts everything above it outside the hierarchy. Those bones
are still exported and still carry their weights; nothing ever moves them again.

Miku measures it: her thighs hang off `Bip01 Spine`, that bone is promoted, and `Bip01 Pelvis` —
its own parent — is left holding 985 vertices, **23.7% of her body**, her skirt among them. In
game her dress stood still while she moved, and it read as missing spring bones.

Such a bone **cannot be adopted**. Every humanoid bone is one of its descendants, so re-parenting
it builds a cycle; Blender refuses, silently, and a fix that re-parents it will log success and
change nothing. Move the **weight** down to the humanoid root instead.

## A prop with a bone of its own is addressable, however buried

Joker is one mesh with one material, so nothing about his name, material or structure separates
his pistol from his suit. It is still trivially findable: it is a connected island of 262
vertices and it hangs off a bone called `Gun_joker`. Link is the same with the master sword and
shield, on bones called `Sword` and `Shield`.

So the probe worth having is **islands of a BUILT .vrm, each with the bone that carries it**
(`scratchpad/islands_vrm.py`). Weld by position first, since an imported mesh often arrives
split, then take the dominant joint per island. Both props fell out of one listing, and Link's
scabbard `Fourreau` was visible in the same listing as the thing NOT to drop.

## What a texture fault is, before reaching for a fix

Three reports read as "the textures are wrong" and they were three different things. The
distinction is worth making before changing anything, because only one of them was ours:

| | Gordon Freeman | Batman | Alastor |
|---|---|---|---|
| material to image | **wrong** — `gordon_d`, his face map, on his eyes, suit and suit mesh, five copies, with `onefreeman` absent from the bundle | right (he has one base map; there is nothing to get wrong) | right |
| image content | right | right | right — `aleyes.png` plainly holds a pink iris with a black pupil |
| UVs | right | right | **wrong** — the eyes land beside the iris; the pupil renders as a stray mark next to the eye |
| fixed by | a rebuild | nothing; does not reproduce | nothing a rule can do |

**Read the image, not just the filename.** Dumping the base map out of the built file and
looking at it is what separated Alastor's case from Gordon's: both were "textures wrong", and in
Alastor's the texture was already correct and already attached.

A pipeline can fix which map a material gets. It cannot fix a mesh whose UVs were authored
against a different layout, and should not try to guess one.

## Only bones that deform are exported

The VRM export writes bones with `use_deform` set and drops the rest. That is correct and it is
not the whole story, because **weights are not checked against it**: a vertex group naming a
dropped bone is simply orphaned, and the glTF exporter hands the orphaned weight to a bone of its
own invention, `neutral_bone`, parented at the root.

A Rigify rig carries three bones per joint — `ORG-` (original), `MCH-` (mechanism) and `DEF-` (the
one that deforms) — and only the DEF- bones have the flag. Gadget Hackwrench's eyes are
bone-parented to `MCH-eye.L` and `MCH-eye.R`, which is a perfectly ordinary way to attach a rigid
prop and works in Blender up to the moment of export. 172 joints came out of her 647-bone
armature, and nothing in the build mentioned the 475 that went.

Walking up to the nearest ancestor that *will* be written is the first answer and it frequently
finds nothing: `MCH-eye.L`'s thirteen ancestors up to `root` are every one of them non-deform,
because the control bones are a tree of their own running parallel to the DEF- bones. The fallback
is the nearest humanoid bone, which for an eye is the head.

## A bone is a segment, and its head is not where it is

The hair rigger has to know which end of a group is attached. Hair hangs below the head, so for
hair the top of the group is the attached end — true for every character until a cape turned up,
and Mando's cape is anchored at his chest in a scene whose z runs the other way. Rigged on that
assumption it pinned the hem to his thighs and left the swinging tip at his collar.

The anchor bone is the physical attachment and is already known, so measure against it. The first
attempt compared against the bone's **head** along z alone and flipped Gadget's hair: her head
bone's head is down at the neck, 0.80, and her hair runs 0.50 to 1.25, so the bottom of her hair
measured nearer to it than the top. The bone occupies 0.80 to 1.21 and its middle, 1.01, is inside
the skull where the hair is rooted.

**Compare against the middle of the bone, in three dimensions.** Where a bone starts is not where
it is.

## A fixed bone index is a guess about someone else's rig

`rigify_def` mapped the head to `DEF-spine.005` and the neck to `DEF-spine.004`, indices read off
the first rig that needed them. Rigify names a spine chain `DEF-spine`, `DEF-spine.001`, ... and
where it ends depends on how many bones the rigger drew. Tenna and Gadget both run to
`DEF-spine.006`, so both had their head mapped to their neck, their neck mapped to the bone below
it, and the actual skull bone — 41 cm of it on a 1.30 m Gadget — left out of the humanoid
altogether. Head-look pivoted at the throat.

Nothing caught it because the map was complete and self-consistent: every bone it named existed
and the readback matched. **A mis-mapping is only visible if you ask where the bone IS.** Count
the chain instead of indexing into it.

## use_deform is the armature's switch, not a setting for bone heat

The unrigged-mesh rescue takes tip, facial and co-located helper bones "out of the running"
before automatic weighting, by clearing `use_deform`. That is the right intent and the wrong
switch: `use_deform` stops the bone deforming **anything**, including the meshes that were
already rigged and perfectly weighted before the rescue ran. It was never turned back on.

Jessica Rabbit measures it. Her rig carries 160 bones and the rescue takes 73 out, leaving 87.
Her body is weighted to those 73 as well, so every vertex weighted only to a disabled bone
stopped deforming and stayed in the bind pose:

| stage | her body's evaluated box |
|---|---|
| after import | z 0.472..11.649 |
| after CHILD_OF | z 0.472..11.649 |
| **after realign** | **z 0.472..43.606** — half standing, half still bound |
| after scale | x -0.040..0.040, hence "implausibly narrow" |

The scale step then measured a figure nearly four times too tall and squashed her to 0.08 m
wide. **Every count stayed right the whole time**: a verified height, a full 52/52 humanoid,
every mesh skinned, no undriven weight — and the character was a twisted mass, while her SOURCE
rendered perfectly.

Restore the flags the moment bone heat is done with them.

### VRM_TRACE is what found it, in one run

`VRM_TRACE=<mesh substring>` prints that mesh's evaluated world box at every stage. It exists
because "chasing a part that ends up in the wrong place by reasoning about matrices is how three
wrong fixes got written", and this was the fourth: before using it, time went on a weight
transfer, a posed-donor copy and a donor-selection fix, all of which were real improvements to
code that was not the problem. **Set the trace first.** `VRM_NO_REALIGN` then ruled out the
stage the trace pointed at, which narrowed it to the rescue sitting in the same gap.

## A T-pose has straight legs

Straightening a leg already existed -- `_straighten_axis` against -Z -- but only inside the
stand-up step, which is opt-in AND requires the spine to lie more than 25 degrees off vertical.
A character who stands upright with her legs crossed can never reach it: Jessica sings at a
microphone with her thighs 28.0 degrees off vertical, and baked a crossed-leg bind that every
animation in the game would then deform from.

Legs are now measured on the same terms as the arms, in the same block, so one geometry bake
covers both. `VRM_STRAIGHTEN_LEGS=1` asks for it, because straightening a leg is a DEFORMATION
and on weights taken from a contorted pose it is the deformation that tears -- the caution the
stand-up path already records about Anakin, whose knee was folded against his chest when he was
bound. The measurement prints either way, so a character that needs it says so in its own log.

## Shape keys: zero them, do not delete them

A shape key's weight is ZERO in engine, so the base mesh is what to MEASURE. Prix proves why
that matters: her FBX ships six keys non-zero, one holding a corrupt four-times-oversized body,
so Blender's viewport and every render showed a 1.95 m tangle while the real character was
0.478 m. The build scaled the garbage to 1.70 m and she arrived in game at 0.416 m.

All of that argues for **zeroing**. None of it argues for deleting, and for a long time the
build did the second. Pomni is what it cost: her irises are supposed to resize -- that is the
character -- and her source carries `Big`, `Small`, `SpiralEyes`, three doodle keys, eight
facial expressions and `Closed` on each set of lashes. Every one was deleted, so she exported
with zero morph targets and the eyes that are meant to animate had nothing to animate. Nothing
downstream reported a loss; by then there was nothing left to lose.

Two things fall out of keeping them:

- **`Mesh.transform()` leaves shape keys behind unless asked.** A mesh that has keys is
  EVALUATED from the keys, so moving the vertices without them is invisible in every render and
  shows up only as the mesh DATA and the evaluated bounds disagreeing. Pomni's lashes went
  through `flatten()` that way and her mesh DATA measured 1.3949 m against a 1.70 m target. The
  height guard caught it. Those call sites were correct for exactly as long as the keys were
  being thrown away.
- **They are not free.** Prix's 37 keys on a 61k-vertex mesh take her from 8.6 MB to 28.3 MB,
  for morphs that are no part of her. So keeping the full set is opt-in (`VRM_KEEP_MORPHS=1`)
  and a blink key is spared regardless -- one key, not thirty-seven.

## What YARG actually drives, which is one expression

Before adding anything a character "could" use, read `VRMCharacter.cs`. YARG builds a
dictionary of the VRM's custom expressions and then looks one up **only by lipsync event
name**; `LipsyncType.Blink` maps to `ExpressionKey.Blink`. Nothing emits "Big" or "SpiralEyes",
so those can sit in the file forever and never be asked for.

Measured across all 66 installed characters: **not one has a morph bind on any of its 18 preset
expressions.** The presets are all present and all empty. So every character that ships an
eye-closing shape key has had a blink available and unwired the whole time.

The matching has to be narrow, because a wrong bind is a face that collapses every time the
game blinks:

| | Pomni | Heels (Character Creator) |
|---|---|---|
| key | `Closed` | `Eye_Blink_L`, `Eye_Blink_R` |
| on | `Lashes.L`, `Lashes.R` | one `CC_Base_Body`, plus eye occlusion and tear line |
| side comes from | the mesh name | the KEY name |
| must NOT catch | `ClosedTeeth`, `ClosedTeethVariation` | `Mouth_Close` |

Both faults in the first cut looked identical from the outside -- "this model has no blink key":
the pattern was anchored with `match()`, which cannot see the word in `Eye_Blink_L` and so found
nothing across a whole rig family while reporting cleanly; and the side was read off the mesh,
which would have called both of Heels' eyes the same side. **A matcher that reports absence is
making a claim, and it is only as good as what it looked at.**

### Correction, 2026-11-10: a bound blink can be invisible, and facial events CAN reach custom expressions

Two things in the section above were incomplete, and one was wrong in effect.

**Pomni's bound blink did nothing visible.** `Lashes.L/Closed` and `Lashes.R/Closed` were bound
and counted ("bound 2 eye-closing shape keys"), and at weight 1.0 they move two lash ticks while
the eyes stay fully open -- in the build and in her untouched source file alike. Her real blink is
**four eyelid bones** (`EyelidSup.L/R`, `EyelidInf.L/R`) rotating about X on frames 26-34 of her
`Animation` action, peaking at frame 30 (`Sup` +0.55 / `Inf` -0.5 on X, in quaternion `(1, x, 0, 0)`
form, mirrored symmetrically). A VRM expression can only drive a morph target, never a bone, so
none of it was reachable. A bind existing is not the same as a bind doing something: **render the
expression at weight 1.0 before calling it done.** The count in the build log cannot tell.

The fix is `VRM_BLINK_BAKE`, which poses the named bones to the closed frame, stores the lid
meshes' deformation as a `Blink` shape key and binds it to the plain `blink` expression:

```
VRM_BLINK_BAKE="EyelidSup.L=1,0.55,0,0;EyelidInf.L=1,-0.5,0,0;EyelidSup.R=1,0.5,0,0;EyelidInf.R=1,-0.5,0,0"
VRM_BLINK_MESH="^EyeLid"        # default; which meshes get the key
```

Three details that each cost a build:

- **The lid meshes carried Solidify and Subsurf ahead of the armature modifier, and nothing in the
  build applies them** -- the exporter does, at write time. A key written on the 81-vertex base
  would not survive that. The bake applies them first (the lids have no shape keys yet, and the
  armature is last in the stack, so `modifier_apply` has no ordering complaint). The first attempt
  refused with "evaluated 674 vertices, mesh has 81", which is the guard doing its job.
- **Baked keys must be excluded from the auto-detector**, which matches a key named `Blink`. Left
  in, they were bound twice and would have closed the lids to double weight.
- They are bound to `blink` only, not `blink_left` / `blink_right`: the mesh names carry an `L`
  that does not reliably mean the eye's side (`EyeLidSup.L.001` sits on the other eye), and YARG
  drives only `blink` anyway.

**Lashes close with the lids (`VRM_BLINK_LASH="^Lashes"`).** In her source the lash ticks collapse onto the seam where the lids meet (z-spread 0.009 against 0.024 open, at the eye's centre height). Her own `Closed` key does that in the source and does not survive the build: it moved the lashes 0.011 the wrong way. So the bake writes a fresh `Blink` key on each lash mesh from the closed lids: seam height from the nearest Sup/Inf pair, a ray cast from the front onto the closed lids, 4 mm in front of the surface, and 40% of each tick's height kept. Flattening them to zero height left degenerate lines that rendered as nothing -- the first attempt. The old `Closed` binds are skipped on baked meshes, or the two keys would add.

Verified by render at weight 0 and 1: eyes open at rest, dark lids with a thin slit when closed,
matching her published blink. Pomni's triangle count is unchanged at 32,764.

**Custom expressions ARE reachable, by lipsync event name.** `VRMCharacter.TryGetExpressionKey(string)`
looks a custom expression up by exact name, and every `LipsyncEvent` carries a `LipsyncType`
whose `ToString()` is that name. So a character's own facial shape keys can be driven with no
change to the game, provided the expression is called by one of those names. `VRM_EXPR` does it:

```
VRM_EXPR="Wide_eyed=Eye.L/Big;Squint=Eye.L/Small"       # Name=Mesh/Key;Name=Mesh/Key
```

It spares the named keys through the drop pass and adds a custom expression per name with a
morph bind of weight 1.0. Pomni's `Big` fills the eye with iris and `Small` shrinks it to a
pinpoint, on both eyes (rendered at weight 1.0).

#### What a facial event gives you to play with

An event is `LipsyncEvent(Type, Value, time)`. That is all of it:

| Parameter | What it is |
|---|---|
| `Type` | one name from the fixed `LipsyncType` list -- it selects which expression fires |
| `Value` | one float weight, 0 to 1 |
| time | when it applies. **There is no duration, curve or blend mode in the event** |

Everything else is on the model's side, or in how the generator stacks events:

- **Shape over time** comes from a stream of events, about 30 per second (`STEP_TIME = 1/30`),
  eased with smoothstep (`EmitRamp`). Blink ramps 0 -> 1 over 0.05 s and 1 -> 0 over 0.10 s,
  every 2-6 s. Brows ease in and out over `BROW_FADE_TIME = 0.8` s or a quarter of the section.
- **Strength** is the morph bind's `weight` in the VRM, so it can be scaled or retargeted per
  character. One expression can bind several keys, so a single name can drive a pupil change and a
  brow dip together.
- **Names that reach a custom expression:** `Blink` (preset, not custom), `Brow_aggressive`,
  `Brow_down`, `Brow_dramatic`, `Brow_openmouthed`, `Brow_pouty`, `Brow_up`, `Squint`,
  `Wide_eyed`, and the `exp_*` set (`exp_rocker_smile_intense_01`, `exp_banger_roar_01`,
  `exp_dramatic_mouthopen_01`, and so on). The match is exact and case-sensitive.
- **Cannot do:** blend several expressions with different weights from one event, loop, or time
  anything independently of the chart's event list.

#### What the generated charts actually send

When a song has no authored lipsync, `LipsyncGenerator` writes one brow state per vocal section (a
section is a run of vocals with gaps of 2 s or less; `BROW_SECTION_GAP`):

- primary brow, intensity **0.3 to 0.7**, plus an optional secondary;
- picked by weight: `Brow_down` 5, `Brow_pouty` 5, `Brow_aggressive` 5, `Brow_up` 2, `Squint` 1.5,
  `Brow_dramatic` 1;
- about **8%** of sections (`EXPRESSION_CHANCE`) use the full-face `exp_rocker_smile_intense_01`
  instead of a brow.

**`Wide_eyed` is never generated**, so it fires only from authored charts. A key bound to it is
reachable but will rarely move. Bind to a name the generator actually emits (`Brow_up`, `Squint`)
if the effect should be seen on ordinary songs. Pomni currently has `Wide_eyed` -> `Big` and
`Squint` -> `Small`, so her irises pinch now and then and do not widen on their own.

Not verified in game: all of this is from the code and from renders in Blender. Nothing here has
been watched running in YARG.

## A hand can ship turned 100 degrees, and only the written file shows it

2026-11-10. Judy Hopps' hands stood UP out of her cuffs in game, like white sticks, beside a
character such as the Joker whose hands follow the arm. In Blender her rebuilt hands rendered the
same way, but the numbers that should have explained it did not: her wrist angle matched her source
model exactly (21.3 degrees in both), because that figure was measured on raw vertices and the
fault is not in the vertices.

**The fault is in the skeleton the game poses against the mesh.** A VRM stores node transforms
(what the game poses the bones with) and inverse bind matrices (what the mesh was bound against).
Where they disagree, the mesh is deformed by exactly the disagreement. Importing the file and
comparing every bone's pose with its rest found it: `n50`, her hand, and everything under it were
**100.1 degrees** off, about the bone's own axis; her forearm was 1.7. `tools/character-pipeline/
bind_check.py` does this for any exported `.vrm` and should read zero. Pomni: 0 bones over 5
degrees. Judy as shipped: 106 of 141.

**The cause was the stub-finger step.** YARG's microphone code dereferences six finger bones and a
null makes the character invisible, so the build synthesises weightless stubs for any missing
finger. With no donor finger (Judy, Miku) it laid them along the hand bone's direction -- and
Judy's hand bone points almost straight down. Built with the step off, the same file measured 8
bones off, none of them the hand. Laid along the forearm instead: 14 off, all weightless thumb stubs
plus ears that are 11 degrees off with or without it, and the hand renders straight out along the arm.

Three things that cost time and should not again:

- **A check inside the build cannot see it.** I added a pose-versus-rest test just before export and
  it reported "every bone is at rest" for the broken character; the defect only exists in the written
  file. Measure the exported file, in a fresh import.
- **Edit mode was blamed first and was innocent.** Entering and leaving it did rotate nothing (0
  bones). The bone pointing straight down made a roll singularity the obvious suspect, and
  recording and restoring every bone around the round trip changed nothing. Measure the suspect
  before building the repair.
- **Folding the finger weights into the hand bone changed nothing** either, for the same reason:
  the hand bone itself was the one turned, not the fingers.

Her real hands are closed fists with the thumb out -- the source model is modelled that way -- and
her finger bones are not in the humanoid map, so they do not animate. That is a separate matter from
the 100 degrees. **Miku took the same no-donor path.** In her installed build her hand and finger bones measured
62.1 degrees off (88 bones, 44 over 5 degrees); rebuilt with the stubs along the forearm it is 22,
none of them her hands (the rest are weightless thumb stubs and ~6 degree drift on legs and one
finger that was already there). Her old render showed the hands flared up at the wrists; the new one
lies along the arms. Triangles unchanged at 4,588.

## Grey strips at the hands: the T-pose step left shape-keyed meshes in the A-pose

2026-11-10. Alastor, Alice Ivy, Chibi Rem and Heels each showed thin grey rods, 30-40 cm long,
reaching out from the hands in game (in-game screenshots of all four, taken at the character-select
podium). It had been guessed at twice and measured never.

**It only shows when the animation runs, and the first four checks could not see it.**

- Blender renders of the exported `.vrm`: clean hands.
- Unity renders at rest: clean hands -- an editor pass does not re-skin the mesh until something
  forces it, so a "rest" render shows the unskinned mesh.
- Unity renders AFTER `Animator.Update`: the bones moved and the mesh did not. `Animator.Update`
  moves the transforms but the skinned mesh is not refreshed in that pass. Bake each skinned mesh with
  `SkinnedMeshRenderer.BakeMesh` and render the baked copy, and the rods appear exactly as in game.
  `tools/character-pipeline/YargCharHandRender.cs` does this (opt-in `-renderDir`; run Unity WITHOUT
  `-nographics`, which has no GPU context to render with).

**The cause.** For a character whose arms start in an A-pose the build rotates the arm bones out to
a T-pose and moves the mesh with them. It moved `vertices[i].co` and nothing else. A mesh that keeps
shape keys is evaluated and exported from its KEY BLOCKS, not from `vertices[].co`, so every keyed
mesh (the blink and viseme keys are kept on purpose) stayed in the old pose while the skeleton went to
T. The finger bones then sat 20-33 cm from their own fingers, and when the animation curled a bone the
mesh rotated about a pivot far away and was thrown out as a long thin strip. A 30-degree A-pose on a
60 cm arm is about 30 cm at the hand, which is the size of the offset.

**The measurement that found it** is `tools/character-pipeline/bone_fit.py`: for every bone that
carries at least 10 vertices, the distance from the centroid of those vertices to the bone's
head-to-tail segment, in the exported file. Expect a few centimetres. Over all 28 installed characters
the finger bones separated cleanly:

| | finger bones over 5 cm from their mesh | worst |
|---|---|---|
| Alastor | 17 of 17 | 30.9 cm |
| Alice Ivy | 30 of 30 | 32.7 cm |
| Chibi Rem | 30 of 30 | 22.2 cm |
| Heels | 30 of 42 | 32.2 cm |
| Doom Slayer | 8 of 42 | 10.6 cm (clean, see below) |
| Jinx, Lola Bunny | 2 of 34, 2 of 30 | 7.0, 5.9 cm (clean, see below) |
| the other 21 | 0 | at most 4.9 cm |

The four reported characters, and only they, are the ones that started with arms 30 degrees off the
T axis AND carry shape keys. Ariel and Jinx start with the arms already on the axis, so nothing was
rotated. Doom Slayer, Jinx and Lola were rendered in the animated pose and are clean: **the
threshold is a flag, not a verdict.** Jinx's two "finger" bones were `calf_twist` (the filter matched
`f_`; it now excludes calf, twist, toe and spring bones). Lola's right index and ring finger are 5.9 and
5.1 cm out under a thick glove. Doom Slayer's knuckle bones are 5-11 cm from armour plates that are
weighted to them, and his hip and upper-arm bones are 38 and 24 cm from large armour meshes; his hands
animate as closed gauntleted fists. What marks the bug is 20-30 cm on ALL the fingers of a hand,
together with rods in the animated render.

**The fix** is in the T-pose bake in `build_vrm.py`: build one blended skinning matrix per vertex
(a weighted sum of the bone matrices -- linear blending is linear, so it applies to any coordinate
set) and apply it to every shape-key block as well as to the vertices. Rebuilt Heels: 0 of 42 finger
bones over 5 cm, worst 0.9 cm, against 30 of 42 at 32 cm. Alice Ivy 0 of 30 (1.0 cm), Alastor 0 of 17
(1.5 cm), Chibi Rem 0 of 30 (0.5 cm). Triangle counts identical to the references. **In game: Heels and
Alice Ivy confirmed fixed. Alastor and Chibi Rem are installed and not yet seen.**

**What was ruled out on the way, and what that cost.** Each of these looked likely and was measured
before it was believed:

- *The animator.* Heels and Ariel get identical bone deltas from the same controller, rotation only,
  no scale, no translation; Ariel's animated hand is clean.
- *The thumb bind.* Heels' thumb joints are 22.9 degrees off pose-versus-rest and Ariel has no
  deviation anywhere, which made it the tempting cause. It is a symptom: the same wrong-pose mesh. A
  rotation of 23 degrees about a thumb joint cannot move skin 25 cm.
- *Single-bone vertices.* Every vertex fully weighted to one bone kept its distance to that bone in
  the animated pose. Nothing there was stretching.
- *Translation.* `bind_check.py` only measured rotation. Measured about each bone's own head the
  position error is 25 mm or less; an earlier reading of 265 mm was a small rotation measured from the
  character's feet. `bind_check.py` now reports both.
- *Materials.* The finger faces use ordinary skin and nail materials.

**The lesson is the same as Judy's, one step further.** Pose and rest agreed with each other and both
disagreed with the mesh, so `bind_check.py` read clean while the bones were not inside the character.
Check the bones against the MESH they carry, in the written file, and look at the animated pose.

**A separate fault on the same hands, Alastor only.** His outline shell (`BodyOutline`, an untextured
near-black material) is rebuilt as URP/Lit and picks up a specular sheen that shows as pale lines
along every finger. The exporter now gives any untextured near-black material no smoothness,
metallic, specular highlights or environment reflections. Rendered before and after: the double pale
lines become a solid black edge. One thin pale line per finger gap remains, unexplained.

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

**Sometimes another archive.** Lola Bunny's download is a zip holding `textures/` beside a
`source/` that contains one `.rar`; Peach's holds a `model.zip`. A tool that walks the
extracted tree looking for a model finds textures and no model, and reports the archive as
having none — which reads as a bad download rather than as one more layer to open. Both of
them stalled a rebuild until somebody looked inside by hand.

Peach's inner zip then holds `model.dae`, `model.fbx`, `model.mtl` and `model.obj`: four
spellings of the same character, and the `.mtl` and the model files are exactly the non-image
candidates the texture pool has to filter out.

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
- **Two skeletons, neither usable.** A game rip can carry both the engine's rig and an imported
  one. Check which deforms the mesh, and check that it fits -- see *A skeleton can be in the file
  and not be in the MODEL*.
- **A format Blender cannot read.** One Judy Hopps archive is an FBX 7300 whose import dies with
  `KeyError: Root Model` on every combination of import options. Yoda's first archive was an ASCII
  FBX, which Blender also refuses. Ask for another format rather than fighting the importer.
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
| Hand-built | Meaningless `Bone.0NN`; map it by reading the hierarchy, the rest geometry and what each bone actually deforms |

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

## Transparency has three states, not two

The builder knew OPAQUE and CUTOUT. A cutout is a *mask*: each pixel is in or out. A **blend**
is neither, and a material authored as one is a statement, not something to infer.

Pomni's `EyeDetails` is a detail sheet laid over her eye. In the source, `Eyes.png` feeds both
Base Color and Alpha, the material's `blend_method` is `BLEND`, and that image is **69.2% fully
clear**. Shipped `alphaMode=OPAQUE`, every clear pixel rendered as the black underneath it --
"black marks above and below her iris". Inferring a cutout instead was tried earlier and is
worse: masking her eyes made them see-through into her skull.

Blender 4.5 still carries `Material.blend_method`, so read it at the top of the material loop,
*before* the loop rewires anything, together with whether an image was wired into Alpha. When
both hold, ship `alphaMode=BLEND`. No measurement, no guess -- the author already wrote it down.

## A name match is a guess; the UVs are a measurement

A base map picked because its name is a *substring* of the material's name is a weak claim. The
token guard beside it only protects a material carrying an authored colour, and that left a hole.

`PomniEyes` is the white of her eye: 0.814 grey, **no texture of its own in the file**. It took
`Eyes.png` because "Eyes" is inside "PomniEyes". Measured against its own 1476 faces, that map is
**67% fully transparent** -- so two-thirds of her sclera sampled a clear pixel and shipped black.

So measure instead of arguing about the name: sample the candidate's alpha under the UVs of the
faces that actually use the material. A base colour map is not two-thirds transparent across its
own geometry. Materials that really are see-through take the cutout or blend path above, where
the transparency is the point and this test is never reached.

Having declined the nearest thing in the folder, do **not** fall through to the widest pool --
that reaches for something further away still.

## A spring chain must not swing on an attachment bone

A VRM chain moves each joint by rotating the one before it, so joint 0 is not a passenger: its
rotation swings everything below it. That is exactly wrong for a bone whose job is to hold the
mesh *on*.

Lola Bunny's hair chain was `hair_att -> hair1 -> hair2`, and `fml_un_C_hair_att` is **0.260
long carrying 51.9% of the hair**, against 0.100 and 48.1% for the whole rest of the chain. The
simulation swung the bulk of her hair on a lever two and a half times the length of the hair
itself, pivoting at the base of her skull -- and with **zero colliders** in the file, nothing
caught it. Her ponytail left her head.

The rig says which bone this is, if you measure rather than read the name: **longer than the rest
of the chain put together** (that is the lever) **and carrying at least as much of the mesh**
(that is what the lever throws). Both tests, or an ordinary long first segment gets dropped.
Anchor at the next bone down; the `_att` bone then stays rigid to the head, which is correct.

The builder already treated `_att` as an attachment point for chest bones. It just never applied
the same idea to hair.

## Feet cannot point along the shoulders

Reading facing off the feet is right until the feet are themselves posed.

Jessica Rabbit is a posed statue -- feet crossed in heels -- and her toe direction measured
`(1.00, -0.02, 0.00)`, within **2 degrees of her own shoulder line**. No body stands like that:
feet point *across* the shoulders, never along them. Aligning her by the feet turned her 89
degrees and shipped her in profile. The existing guard ("the arms already lie along X") could not
save her, because her arms were posed down too -- and the arm straightening that runs afterwards
works per-arm from its own side, so the arms came out along X regardless and nothing downstream
noticed she was sideways.

Cross-check the feet against something posing cannot move. The **heads of the shoulder bones**
sit at the collarbone roots beside the spine: they are where the arm starts, not where it points,
so they stay put however the arm is posed. That gives the left-right axis outright, and forward is
perpendicular to it.

A perpendicular has two directions, and the feet cannot break the tie when it was the feet that
were wrong. The **knees** can: a leg bends forward, so the knee sits in front of the line from hip
to ankle. Read it *before* the legs are straightened, while the bend is still there to measure.
If the knees are silent too, leave the orientation alone rather than guessing.

## Spring bones need something to hit

Every one of the 66 characters installed here shipped with **zero colliders**. A VRM spring
chain that collides with nothing passes straight through the body, which is Gadget's hair
through her face, Power Girl's through hers, and why Lola's ponytail had nothing to catch it.

Two colliders per character, both **measured**, because these models run from Yoda to Skibidi
Toilet to a 2.9 m Alcina and one hardcoded radius would be a helmet on one and a pebble on
another:

- a **sphere on the head**, centred on the centroid of the vertices whose dominant group is the
  head bone or one of its descendants, *minus any bone a spring already drives* — the hair must
  not be part of the thing it collides with, or it pushes itself off the head;
- a **capsule down the torso**, whose axis comes from the mapped spine bones but whose **ends
  come from the geometry**. Gadget is why: her shipped humanoid map has `hips -> root`, a bone
  sitting on the floor at z=0.005, so a capsule drawn between the mapped bone heads ran from her
  feet to her neck. The bones can be mapped oddly and the capsule still has to land on the torso.

The radius is the **median** distance, not the maximum, and that is deliberate. Hair rests on
the scalp, so the sphere wants to sit at the skull rather than enclose the nose, ears and chin.
A collider too small lets hair sink slightly in; one too big holds it visibly off the head, which
reads as broken rather than imperfect. `VRM_COLLIDER_SCALE` moves both without an edit.

Chest chains are deliberately left out of the group: they sit *on* the torso, so handing them the
torso capsule would push them out of the body they belong to.

## A collider must never contain a joint it is attached to

The first collider build was worse than no colliders, and the reason is the one thing the VRM
spec makes unavoidable: **a collider ejects whatever is inside it**. A spring joint that starts
inside is shoved to the surface on frame one and stays there.

Gadget Hackwrench is the case. Three of her hair joints sat inside a 0.193 head sphere, one of
them 44% in, and the ejection pushed her hair out by about 10 cm on a head 0.45 m wide: it
ballooned into a mass bigger than her body. Measured across the batch, **8 of 23** characters
had at least one joint inside — and that set is exactly the ones that came back looking wrong.

So the radius is now the largest that **clears every joint the group is attached to**, or the
measured median, whichever is smaller:

| | measured | shrunk to | nearest joint |
|---|---|---|---|
| Gadget Hackwrench | 0.193 | 0.103 | 0.108 |
| Tenna | 0.243 | 0.158 | 0.166 |
| Killer Clown | 0.121 | 0.081 | 0.086 |
| Yoda (capsule) | 0.072 | 0.020 | 0.021 |

On a rig whose hair roots sit deep in the skull this leaves a small collider, and that is the
right trade: a small collider still stops hair driving through the face, while an ejecting one
is a visible catastrophe. Fourteen of the 23 needed shrinking.

The failure was in the *direction* of the error I had reasoned about. I had written "too big
holds the hair off the head" — which sounds like a cosmetic gap. It is not: too big does not
hold hair off, it **throws hair outward from inside**, and the magnitude is the whole collider
radius rather than a few millimetres.

## The built VRM is not necessarily what is installed

`rollout/out/<name>.vrm` is whatever was last built. The installed `.yargchar` may have come from
somewhere else entirely — in particular from a **backup restored after a bad build**.

The Mandalorian was restored from backup earlier in the session because a build had shipped him
upside-down. The restore replaced the installed `.yargchar`; the broken VRM stayed on disk. When
colliders were later retro-fitted from `rollout/out`, that broken VRM was faithfully carried
forward and installed over the good one, undoing the restore. He came back upside-down, hanging
below the podium.

Checking is cheap and there is now a probe for it: head above hips, feet below hips, read off the
humanoid map. Mando measured head y=-1.355, hips -0.829, feet -1.642 — every bone below the floor
and the head under the hips. Run it on anything before shipping it.

Note the one false positive it has: Gadget's humanoid map says `hips -> root`, a bone on the
floor, so her feet measure *above* her hips while she is perfectly upright.

## Most of the characters have no source file any more

Worth stating plainly, because it bounds what any future fix can reach. The 66 characters are
personal-use conversions whose sources were downloads living in per-session scratchpads, and
nothing durable holds them — not the repo (deliberately), not `C:\dev`. Of the 66 installed:

- **31** have a built `.vrm` on this machine, and of those **24** have spring chains at all;
- **35** have neither source nor VRM, so they cannot be rebuilt without re-acquiring the original
  download and re-deriving the recipe.

So `add_colliders.py` retro-fits a *built* `.vrm` — import, fit, re-export — rather than
rebuilding from source. It shares `vrm_colliders.py` with `build_vrm.py` so the measuring cannot
drift between the two paths, and it prints a **census before and after** (triangles, meshes,
materials, images, springs) so a lossy round trip shows up as a number rather than as a character
that looks wrong in game three days later.

## A probe that is approximately right is worse than no probe

The first readback for the colliders walked the glTF node tree accumulating **translations only**,
ignoring every rotation. It reported the head sphere 5 cm from where it had been placed, which
looked exactly like the offset having been written in the wrong coordinate space — a plausible,
specific, entirely wrong diagnosis that would have cost an afternoon.

Composing the full 4x4 matrices instead showed the build was already exact:

| | measured in Blender (Z-up) | exported (Y-up) |
|---|---|---|
| head sphere | `(0.002, -0.159, 1.252)` | `[0.002, 1.252, 0.159]` |
| torso capsule | `(0.0, -0.177, 0.731)` | `[0.0, 0.731, 0.177]` |

The same trap as *The check can be the bug*, and the same answer: a measurement tool gets verified
against a case whose answer is already known before its output is allowed to steer anything.

## A partial hair rig is worse than none

Rigging *some* of a hair mesh tears it. Miku's hair is ~250 separate ribbon strips, and the
rigger reported its own problem plainly:

```
hair rig: 198 hair verts spanning 0.529 m
hair rig: built 2 chains of 4 bones
hair rig: weighted 59 hair vertices onto the new chains
```

59 of her 3,974 vertices ended up with any spring weight, and on the strips that got some, the
chain owned only 11% against `Bone06` 38% and the head bone 33%. So a handful of ribbons were
dragged a fraction of the way while the ribbons beside them stayed put, and the hair sheared
into what looked in game like loose floating shards.

Three drivers on one mesh is the tell. Either the chain owns the hair or it should not touch it.

## Measure before blaming the pipeline

Miku's twintails splay straight out sideways, and that looks exactly like a rigging fault. It is
not ours. Measured at all three stages, normalised by height:

| | hair x-span / height | hair z-span / height |
|---|---|---|
| `Miku.fbx`, the original download | 0.93 | 0.70 |
| `miku-final.blend`, our intermediate | 0.93 | 0.70 |
| `Miku.vrm`, as shipped | 0.92 | 0.70 |

Unchanged end to end: **the model was authored with the hair flying outward**. Only a re-pose of
the hair bones would change it, and that is a modelling decision rather than a defect to fix.

Note the original is 0.019 units tall, so absolute numbers are useless at two decimals -- the
first comparison said "x -0.01..0.01" for both and looked like a match by accident. Normalise,
or the precision decides the answer for you.

## An intermediate .blend carries its own spring configuration

`ext.spring_bone1` lives in the .blend. A source that has been through this pipeline before
arrives with the chains it was given last time, so asking for no springs still ships springs --
they were never *added* by that run, they were inherited.

Miku's intermediate holds the `HairSpring` chains an earlier session built. Rebuilt with the hair
rigger off and a spring regex matching nothing, the log said `spring bone chains added: 0` and
the exported file still had two. `VRM_CLEAR_SPRINGS=1` wipes what the file came with, before
anything is added. Opt-in on purpose: the VRoid characters arrive with their own authored chains,
which are correct and must not be thrown away.

## Lipsync needed shapes the pipeline was deleting

Measured across all 28 built characters: **not one had a single viseme bound**. Lipsync could
not work on any of them. Only three could even blink.

The models were not the problem. Heels' source carries **420 shape keys**, including the whole
Character Creator viseme set -- `V_Open`, `V_Wide`, `V_Tight`, `V_Tight_O`, `V_Explosive`,
`V_Dental_Lip`, `V_Affricate` -- and what shipped was two keys, both blink. The shape-key pass
drops everything except blink by default, for a good reason (Prix goes 8.6 MB to 28.3 MB with
all of hers kept), and visemes were simply never on the spared list.

So spare and bind the handful that are actually used, not all 420. On Heels that is four keys:
10.70 MB to 12.21 MB, +14%, triangles unchanged, and all five mouth expressions bound.

The mapping is phoneme-group to phoneme-group and approximate by nature. Character Creator has
no separate IH, so `ih` and `ee` both take `V_Wide` -- a limitation of the source set, not a
guess that a different key would improve.

Match viseme names **anchored**. A loose `mouth` match would catch the seventy-odd
`Mouth_Smile` / `Mouth_Pucker` / `Mouth_Blow` shapes sitting directly beside the visemes on a CC
body, and bind a vowel to a smirk.

## A character with no shape keys cannot lipsync, and nothing can fix that

Batman has **zero morph targets**. So does Jessica Rabbit, and most of the roster. The 18 preset
expressions are present in every exported file because VRM declares them, which reads as a
working lipsync setup right up until nothing moves -- the distinction that matters is
*declared* versus *bound*:

| character | mesh morph targets | bound |
|---|---|---|
| Batman | 0 | none |
| Jessica Rabbit | 0 | none |
| Pomni | 2 | blink only |
| Heels (after this change) | 44 | aa, ee, ih, oh, ou, blink |

When a character will not lipsync, check for morph targets before looking at the venue, the
`VRMCharacter` component or the chart. If the count is zero the answer is the source model, and
the only route is a different model or a face rig built by hand.

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

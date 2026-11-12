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

*(That was the state before the viseme work. Re-measured from the bundles on 2026-11-12 with
`viseme_audit.py`: **13 of 65 now have all five visemes bound and 10 can blink.** The 52 with
none are mostly characters with no mouth shape keys at all — see* Who can lipsync at all *in the
tooling README for the per-character list.)*

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

## Alastor in game: what the renderer does that the editor does not

2026-11-10. After the finger strips were fixed, Alastor still looked wrong in game (character-select
screenshots; no close-ups are possible, so everything below was measured on the files and judged by
eye in game). Three separate faults, found one at a time.

**1. His mask showed through his fringe.** The hair, ears and mask are one mesh on one bone and one
material (`Head.001`), so this is not skinning. The VRM marks every one of his materials
`doubleSided`, which is how a single-sided sheet stays visible from both sides. The exporter rebuilds
each material as a fresh URP/Lit, which culls back faces, and the source materials are `Standard`,
which has no cull property to read -- the flag is lost on import and cannot be recovered from the
imported material (a first attempt that tried read `source cull -1` for all four). So it is a named
list: `YARG_CULL_OFF_MATERIALS="Head.001;Eyes.001"` draws those double-sided. Seen in game: the fringe
now covers the mask and the eyes have their brows. Double-sided is not free: the lighting on back
faces changed, which is the next fault.

**2. A cool purple tint and a blown-out face.** URP/Lit's default smoothness and environment
reflections read as a sky tint on a flat toon character. `YARG_NO_SHINE_MATERIALS="Body.001;Head.001;
Eyes.001"` (or `*` for every material) sets smoothness, metallic, specular highlights and
environment reflections to zero. Alastor's hair and ears are red again in game. Heels, Gwen Stacy and
Ariel were also installed no-shine (`*`) to compare; the editor shows the difference much less than
the game does, so the editor is not a guide to how bad the shine looks. Ariel's aquamarine hairline
was already like that before the shine was removed: it is not a regression. **Known bug:** the
exporter sets `_Metallic` to 1 for any material with a metallic map AFTER this switch runs, so for
those materials the switch is only partly applied.

**3. The coat, pants and boots looked inside-out.** Vertex normals agree with the face winding (0% of
faces against it, mean dot 0.94) and the winding is identical in the source model and every build, so
nothing was flipped by the pipeline. What the measurement shows is that the clothing was MODELLED
inside-out. Measured as the share of faces whose normal points away from the local body axis, in the
mesh `BodyOutline.001`: legs and boots 12%, the coat skirt 0%, the red cuffs 0%, the first shoe
faces 1%, the second set of shoe faces (`BodyOutline.002`) 16%. This is the toon outline workflow:
the clothes are wound inwards and a black hull (`Material.001`) is drawn over them. **That black
material is not just an outline.** Over his body it is about half of the faces of `BodyOutline.002`,
and the lower legs of that mesh are 100% black material and the shoes 52%. Dropping it by name leaves
the clothes bare and, with them still inside-out, hollow: the first try at that (installed without
flipping anything) turned the boots into open tubes and broke more than the boots.

The fix is two build options, used together: `VRM_DROP_MATERIAL_FACES="Material.001"` deletes the
hull, and `VRM_FLIP_FACES="BodyOutline.001:z<0.9;BodyOutline.002:z<0.15"` reverses the winding AND
the split normals of everything below those heights. Measured afterwards: legs and boots 12 -> 88%,
skirt 0 -> 100%, cuffs 0 -> 100%, first shoe faces 1 -> 99%, second shoe faces 16 -> 84% (the rest
are probably interior surfaces). Triangles 40,124 -> 21,415, so the install guard needs `-Force`.
**In game, after the legs and cuffs were flipped, the pants were fixed; after the shoes were added
too, it looks right.** Not flipped: the collar (10% outward) and the torso and coat top (about 40%).
He loses his black outline.

**A second pass found the rest of him inside-out too (same day).** The z-band flip had only covered
what was named. Measuring every region against the bone that drives it
(`tools/character-pipeline/facing_check.py`) showed his forearms and hands 0% outward, head and
collar 2%, spine 2-8%, even after the legs were flipped. `VRM_ORIENT_OUTWARD="Body.001@0.25"` does
it from the data: for each mesh, material and driving bone, if fewer than that share of the faces
point away from the bone's nearest point, the WHOLE group is flipped (winding and split normals
together). Mixed groups are left alone: the double-layered coat top reads 38% and a flip would only
trade one half for the other. Result: body-material faces outward 17% -> 76% (second mesh) and
9% -> 88% (first mesh); 1,805 + 2,820 faces flipped across head, spine, arms, forearms, hands,
thumbs, ring fingers, legs and feet. This replaces the `VRM_FLIP_FACES` z bands in his recipe.
Installed 2026-11-10; the in-game result of this pass is not recorded yet.

**Sweep of the other 27 (and what it cannot say).** `facing_check.py` was validated first: Ariel and
Heels read 83-100% outward on their skin, hair and clothes, and only thin or interior parts
(eyelashes, brows, teeth) read low. Over all 28 installed VRMs, no character other than Alastor
shows the signature (textured clothing at 0-17% outward behind an untextured hull). The rest of
the low readings sit at 45-60% and are hair cards, teeth, eyelashes, cloth sheets and layered
armour, which have no inside to be wrong about. Sonic's one low material (shoes, 30%) is an
artefact: every shoe face is driven by `Thigh_L` and his whole body by `Hips`, so "away from the
driving bone" means nothing there. Doom Slayer's large armour material reads 50% and Jinx, Sayuri
and Chibi Rem read 59-63% overall; none of them is anywhere near Alastor's numbers and none has been
looked at for this. A low reading is a prompt to look, not a verdict.

**The group flip was wrong too: it cut across connected pieces (same day, later).** Alastor's
screenshot after the group pass showed the coat skirt still inverted and patches missing from the gloves
and cuffs. The winding-conflict count explains the patches: the unflipped surface had 0% of its shared
edges in conflict, because every connected piece was wound uniformly (just the wrong way round), and
the group flip left 3%. Flipping a group that cuts across a piece flips some faces and not their
neighbours, and the inverted side of each such edge is culled. `VRM_ORIENT_CONSISTENT="Body.001;..."`
works on whole connected pieces instead: faces are joined by shared edges with vertices welded by
position (so a UV seam does not split a piece), one winding is propagated through each piece, and each
piece is then oriented as a whole. Result: 0% winding conflicts, body faces outward 85% / 91%
(group flip 76% / 88%).

**A closed piece has an exact answer: its signed volume.** The coat skirt (a 670-face piece, z 0.47-1.01)
was still inside-out after that pass. Its bone vote read 52% outward, because the thigh bones that
drive it run through its middle, and a vote taken against the wrong bone says nothing. For a piece whose
edges are 95% or more shared by exactly two faces, the signed volume (divergence theorem) is positive
when the faces point outward and negative when the whole piece is inside-out, and needs no bone: it read
-0.00301 m3 before and after. The build now decides closed pieces by signed volume and uses the bone
vote only for open sheets. `facing_check.py` prints VOLUME lines for inside-out closed pieces and a
VOLSUM per file. Validated: the unflipped Alastor reads 16 of 19 closed pieces inside-out; Heels and
Ariel 0 of 10 each. How much to trust a negative volume: Alastor's real inside-out solids fill 11-39% of
their bounding box; a paper-thin double-layer shell fills 1-2% and its sign is noise.

**Sweep with the exact test, all 28 installed VRMs.** 22 characters have no inside-out closed piece.
Candidates, with size (nothing near Alastor's): Alcina Dimitrescu 3 (a 0.9 cm sphere, a 1.6 cm shell, a
flat 5 cm plane at z 2.66), Chibi Rem 2 (a pair, 10 x 6 x 3 cm, 13% solid, at hip height), Jessica
Rabbit 1 (4 x 1.2 x 1 cm), Pomni 1 (flat, 1.4% solid: ignore), Power Girl 1 (head-sized but 6% solid).
None has been looked at in the game and none was changed. Alastor's own five (all `Head.001`) were
hair and ear pieces drawn double-sided, so they looked right either way.

**Head test (installed 2026-11-11, in-game result not recorded yet).** To find out whether the mask
showing through the fringe was ever a missing double-sided flag, the head was oriented outward the same
way (`VRM_ORIENT_CONSISTENT="Body.001;Head.001"`: 0 of 19 closed pieces inside-out, winding conflicts 1%
-> 0%) and `Head.001` taken OFF the cull-off list, leaving only `Eyes.001` double-sided. If the fringe
still covers the mask, it was winding; if the mask pokes through again, the sheets need double-sided
whatever their winding.

**The eyes were inverted and nobody could see it.** `Eyes.001` is two open sheets of 89 faces and all
89 pointed back into the head (0% facing the front), hidden by the double-sided material and below
every size threshold used so far (the 100-150 face minimums). Oriented: 99% facing the front. Installed
2026-11-11 together with the small-piece fix below; the in-game result is not recorded yet.

**What the small pieces showed (79 of Alastor's 103 pieces are under 100 faces).** 17 look wrong: about
15 lone single-triangle pieces at z 0.53 pointing inward (at about the height of the torn coat hem, so
probably hem teeth missing from outside; not confirmed), a CLOSED 30-face head piece that is inside-out
(z 1.54-1.57, near the eyes: a monocle or piercing is a guess), and two 2-face head slivers. The build
missed them by construction: it skips a material with fewer than 40 faces on a mesh, never flips a
piece under 3 faces, and joins only the faces of the materials it was told to orient, so a small shell
touching anything else can look open and be judged by the unreliable bone vote. Also in the file: an
80-face untextured `Icosphere` spanning z -0.90..0.90 that has not been explained.

**Fixed in the build, with one exception.** `VRM_ORIENT_CONSISTENT` now has no size floor, judges a piece of
any size down to a single triangle, and joins faces across EVERY material of the mesh (only pieces that contain a
face of a named material are oriented), with a nearest-neighbour weld at 0.1 mm instead of rounding. Small pieces that
look wrong: 17 -> 1. The one left is a closed solid about 3 x 3 x 2 cm at z 1.55, next to the eyes: inside-out in the
original, left exactly as it was by the pass that fixed its neighbours (including the 64-face piece beside it). In the
build it appears as fragments of 8, 12 and 24 faces rather than one closed piece, and a wider weld did not join them;
the cause is not found. `VRM_ORIENT_DEBUG=1` prints every small piece's closed share, volume, vote and decision.

**What was tried and did not matter.** Each was measured, in the editor, before it was believed:
culling the black material's back faces (renders identical); letting the black hull cast shadows or
not, with soft shadows on (nearly identical, no dark patches either way); making every material
double-sided (clipping fixed, tint made worse); and stripping the shine from the black material
alone (fixed the pale lines along his fingers, nothing on the coat).

**What the game does that the editor cannot show.** The character scripts do not touch materials or
shaders, so the game draws the bundle's materials exactly as built. The High profile adds
screen-space ambient occlusion (depth normals, intensity 0.5, radius 0.25), a 4096 soft shadow map
with four cascades, per-pixel additional lights with shadows and 4x MSAA. None of that is in a
plain editor render, which is why the coat looked fine in every render and wrong in game. When
something is inside-out only in game, measure the winding of the geometry; do not expect to see it.

**Three process notes.** (1) An experiment that DELETES data has to be measured against what it
deletes: "drop the outline shell" was installed over a working character on the belief that the
material was an outline, when the same material is half his clothes. (2) A switch that reads a
property the source shader does not have fails silently (`-1`); log what it read. (3) The renderer's
`YARG_SHADOWS=1` set `QualitySettings.shadowDistance`, and Unity SAVED it into
`ProjectSettings/QualitySettings.asset` (40 -> 20). It is restored after each render now; check
`git status` for that file before committing.

Still open on Alastor: one thin pale line per finger gap, the collar, the torso and coat top, and
his eye UVs (a source-model fault, not fixable here).

## Rendering on the game's own podium, without the game and without touching the repo

2026-11-11. Every fault on Alastor that only showed in game (a purple tint, a coat that read inside-out)
was invisible in the plain editor renders, because the game lights the character with its own scene and
its High render profile. So: render the real thing. `tools/character-pipeline/YargSceneShot.cs` opens the
game's real `CharacterSelect.unity`, instantiates the real podium prefab (found through the
`DisplayManager`'s serialized `_displayPrefab`) in the "selected" slot, loads a `.yargchar` with
`AssetBundle.LoadFromFile` and the same `CHARACTER_PREFAB_PATH` lookup the game uses, steps the animator,
bakes each skinned mesh (an editor pass does not re-skin), and renders through the scene's own camera
with the High quality level selected.

**It runs in a scratch copy of the project, never in the real one.** Copy the project tree WITHOUT `.git`
(`robocopy <project> C:\dev\_unity-scratch\<project> /E /XD <project>\.git`; `Library` included, so there is
no full reimport; about 9 GB for YARG), drop the script into `Assets/<anything>/Editor/` THERE, and run
Unity hidden: `-batchmode` (no `-nographics`, the render needs a GPU context) with
`-executeMethod YargSceneShot.Run -yargchars "<file>|<Name>;..." -shotDir <out>`. At below-normal priority
it takes about two minutes for two characters and creates no window (the main window handle was sampled
during the run and was never set). The real project stays free to open in Unity, which only allows one
instance per project, and nothing written there can leak into the repo: an earlier render once saved a
shadow distance into `ProjectSettings/QualitySettings.asset`.

**Validated against the game, on builds that had been seen in it.** The build that showed a purple tint in
game renders with the purple-grey hair, pale face with dark eye ovals, glossy patchy coat and shiny jointed
legs. The build where the jacket skirt still read inverted renders with the dark maroon hair, red eyes,
darker patchy skirt panels and jagged hem. That is what makes the method trustworthy for troubleshooting;
check a new setup the same way before relying on it.

Known differences: the ring colour animates with time, so its hue depends on when the frame is taken; the
game poses the character with its own idle animation, here the animator is stepped by hand; and the script
does not run the game's `DisplayManager`, so the spotlight keeps its scene values (warm white, intensity 20)
and not the gold the game uses for the SELECTED character. Not required for these comparisons, but it
would matter for judging colour on a selected character.

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

### Two was not enough, and nothing counted it (2026-11-11)

*The section above described the whole collider set until this date. It is now the first half of
it, and the paragraph that said "two colliders per character" was a statement of what the code
did, never a measurement that two sufficed.*

A head and a torso leave **the arms and legs with nothing on them**. A skirt hanging around the
thighs is then unguarded: the leg sweeps through it, because the body's geometry is invisible to
the spring simulation and only a collider can stand in for it. Peach's in-game report was "dress
springs so reactive her legs clip through it", and her skirt chains turn out to be *stiffer* and
more damped than her hair's — 0.85/0.80 against 0.60/0.45. Reactivity was never the problem.

`tools/character-pipeline/cloth_collide_installed.py` measures it over the installed bundles:
for each spring chain, which humanoid part its joints sit nearest, and whether that part carries
any collider. **107 of 422 chains across 18 of the 65 characters** came back unguarded.

The benchmark is in the same folder and was authored by somebody else. The downloaded VRoid
bundles — Harq Alkahana, Inforder Trogen, both Hatsune Mikus — carry **28 colliders** each across
arms, legs and torso, and every one of them reports zero unguarded chains. Adachi Rei carries 16.

`vrm_colliders.fit` now also places a capsule per arm and leg bone: upper arm, forearm, thigh and
shin, both sides, ten colliders in all. Two details carried over from the torso capsule and one
is new:

- the radius is still the **median** distance of the flesh that bone carries, so it scales with
  the character;
- the clearance guard still applies, and it is what makes this safe — measured before any code was
  written, every limb on Peach, Power Girl, Chibi Rem and Batman had room (Peach's thigh wants
  0.061 and her nearest skirt joint is at 0.114), and only Jinx clashed, her braids at 0.061
  against an 0.083 thigh. Her thigh capsule is shrunk to clear them;
- the axis is the **bone**, not the geometry. Capsules drawn between bone heads meet at the elbow
  and the knee with no gap. Two independently geometry-clipped capsules would leave one, and a gap
  at the knee is where a hem slips through.

Nine characters were refitted and reinstalled (Peach, Batman, Chibi Rem, Gwen Stacy, Jinx, Link,
Power Girl, Prix, Sayuri), taking the count to **58 of 391**. What remains is two third-party
bundles, four characters whose `.vrm` no longer exists here, and two whose `.vrm` is measurably
not the build that is installed.

One thing found on the way: `fit` had always claimed in its docstring to replace an existing
group rather than add to it, and there was no removal code at all. A second call would have
doubled every collider. Nothing had called it twice, so the claim sat there untested and reading
as a guarantee.

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

**And anchored matching means some characters will never match, so they must be mapped by hand
and the map must go in the recipe table.** Gordon Freeman's keys are FACS action units and
Pomni's are artist names; neither matches anything, both were mapped with `VRM_VISEME=`, and in
Gordon's case the map was lost on the next rebuild because nobody had written it down. See
*A hand-written mapping that is not in the recipe table will be lost*.

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

## Faithful is not the same as correct

Heels and Ariel render with blank white eyes on the podium. The obvious diagnosis -- the known
"missing eye textures" item -- is wrong: **every eye material has its texture**. Checked first,
which is the only reason the real measurement happened.

What the source actually says:

```
Std_Cornea_L   HASHED   alphaVal 0.553   alphaLinked False
Std_Cornea_R   HASHED   alphaVal 0.553   alphaLinked False
Std_Eye_L/R    HASHED   alphaVal 1.000   (opaque, correctly -- that is the eyeball)
```

So a Character Creator cornea is 55% transparent by a plain Alpha **value**, with nothing wired
into it. The builder's authored-blend rule demands `blend_method == BLEND` **and** an image in
Alpha, so the cornea fails both tests and ships `alphaMode: OPAQUE`. That is a genuine gap, and
`VRM_VALUE_ALPHA=1` now carries such a value across, on the base colour factor's alpha.

**And it made her worse.** With the cornea opaque, its own diffuse was drawing her iris. Export
it 55% transparent and the iris washes out against the white sclera behind it -- visible in a
head close-up before and after. On the podium, at character-select distance, it changed nothing
at all.

Hence opt-in. Three things worth keeping from it:

- A faithful export is not automatically a better one. The source's intent was authored against
  Blender's renderer, not against URP with a different sort order.
- Ariel does not share the cause: she reports **zero** value-alpha materials, her Sclera and
  Irises being plainly OPAQUE. Same symptom, different fault -- *answered* below, in
  *glTF has nowhere to put a separate opacity map*.
- The close-up and the podium disagreed, and the podium is the one that matches the game. A
  change that only improves a Blender render has not been shown to improve anything.

## glTF has nowhere to put a separate opacity map

Ariel's eyes rendered as flat white discs, and a pale band ran across her forehead. They look
like two unrelated faults. They are one.

glTF has no opacity map. Alpha is `baseColorTexture`'s **own alpha channel** times
`baseColorFactor.a`, and nothing else. The builder was loading `X_Opacity.png` into a second
image node and wiring it to the Principled node's Alpha input -- a Blender-side arrangement that
has to survive translation. It does not. The builder enables `mtoon1` for every cutout (it has
to; without it `alphaMode` ships OPAQUE), and MToon carries **one** base colour texture, so the
second image has nowhere to go. It is dropped silently.

Measured on the exported file, which is the only place the question can be settled:

| Material | opacity map | exported base texture | result |
|---|---|---|---|
| `Cornea` | 100% below 10% opacity | `Cornea_BaseColor.png`, **RGB** | an opaque **pure white** shell over the eye |
| `EyeMoisture` | 49% clear, 46% partial | RGB | a second white film |
| `Hair Cap` | 19% clear, 45% opaque | RGB | an opaque scalp cap -- the forehead band |

With no alpha channel, alpha falls back to 1.0 and every pixel passes the MASK cutoff. The
cornea is *supposed* to be invisible; it was being drawn as a white disc in front of her iris.

So do the merge in the builder rather than hoping the exporter does it -- `_bake_opacity_into_base`
writes the opacity into the base map's alpha channel, where glTF reads it, and no later stage can
lose it. Verify by extracting the texture from the `.vrm` and checking its PNG colour type is
**RGBA**: the symptom and the cause are both invisible in Blender, where the second node works
fine.

Heels shows the same fault partially masked: five of her cutouts carry a texture UniGLTF managed
to merge, and the two that stayed plain RGB -- `High_Heels`, `Underwear_Bottoms` -- are the two
that are wrong. "It works for most materials" was what made this hard to see.

### Which channel of the opacity file holds the opacity

Not always the colour, and the filename cannot be trusted to say. UniGLTF writes a **merged**
texture named `<A>_Diffuse-<B>_Opacity.png` whose RGB is the diffuse and whose alpha is the
mask, and the name matcher picks those up as opacity maps. Heels has six and they are not
alike — `img.depth` tells them apart where the name cannot:

| file | depth | what it actually is |
|---|---|---|
| `High_Heels_Diffuse-High_Heels_Opacity` | 24 | RGB, greyscale — **dark leather diffuse** |
| `Underwear_Bottoms_Diffuse-…_Opacity` | 24 | RGB, coloured — **a diffuse** |
| `Std_Eyelash_Diffuse-Std_Eyelash_Opacity` | 8 | one channel — a real mask |
| `Std_Tearline_L_Diffuse-…_R_Opacity` | 16 | grey + alpha — mask in **A** |
| `tail_Transparency_Diffuse-…_Opacity` | 32 | RGBA — mask in **A** |

So: an alpha channel that **varies** is the mask; a single-channel image can only be a mask, so
use its value; and an RGB image with a merged name has lost its alpha and carries no opacity at
all, so decline it rather than inventing one from the colour.

Each clause is load-bearing, and two were written only after a render disagreed:

- Taking the colour of `High_Heels_Diffuse-High_Heels_Opacity` put the shoes at 0.25, under the
  0.5 MASK cutoff, and **her shoes vanished**. The triangle count was identical and every
  automated check passed. Only the render caught it.
- Power Girl's `Supergirl_A_Hair_Alpha.png` is depth 32 with a varying alpha (mean 0.19) and a
  red channel at 0.83. Reading the colour gave **blocky rectangular hair cards**; reading the
  alpha gives cut-out strands.
- The variance test exists because an RGB mask in an RGBA container would otherwise report
  "fully opaque" and erase a cutout the colour was carrying.

## A colour can only veto a texture if the colour means something

A material carrying a real colour is allowed to refuse a texture that merely shares a word with
its name. That guard exists for Pomni, whose `RedEyes` and `BlueEyes` are geometry rather than a
picture and were being painted over by `Eyes.png`.

It assumes the colour is art direction. For some exports it is not. **All 26** of Ariel's
materials carry a different saturated pastel -- a pure green cornea `(0.03, 1.0, 0.03)`, teal
teeth, yellow toenails. Nobody authored that; it is a per-material palette the exporter
generated, and it carries no information at all. The veto then fired on the three materials that
could least afford it, and her eyebrows shipped **purple**, her eyelashes pink and her scalp cap
navy.

The two kinds separate cleanly when measured, because a real colour is almost always either
**neutral** (grey, white, black) or **hue-pure** (a primary, other channels near zero), while a
generated palette is spread across mid-range pastels where neither holds. Over every build log
in the rollout:

| Fraction neutral or hue-pure | Characters |
|---|---|
| 100% | Pomni, Heels, Peach, Prix, Sayuri, Gadget, Judy, Alastor, Killer Clown, Link, Yoda, Mando |
| 79-95% | Alice Ivy, Alcina, Jessica Rabbit, Gordon, Doom Slayer |
| 50% | Peacemaker -- muted but real: navy, brown hair, skin, neutral silver |
| **4%** | **Ariel** |
| **0%** | **Power Girl** (her materials are named `mesh0`, `mesh0.001`) |

Nothing else in the set falls below 79%. The threshold sits at **25%**, a factor of two clear of
Ariel on one side and of Peacemaker on the other -- deliberately well under Peacemaker, because
the test under-counts muted-but-real colours and it is the generated palettes that have to be
unmistakable. It is decided **once per file**, which is right: it is a property of the export,
not of any one material.

## An emissive map is not proof of emission

Daz writes a full PBR channel set per surface, and that set includes an emission-**colour** map
whether or not the surface glows. In Daz it is gated by an emission *strength* that no FBX
carries, so it arrives looking exactly like a glow mask -- and wiring it sets strength 1.0 and
lights the surface up.

Ariel shipped `Irises_Emissive.png` that way, at `emissiveFactor [1,1,1]`.

**Mean brightness is the obvious test and it is the wrong one.** It looked decisive on a sample
of two — Master Chief's maps at 0.0, Ariel's at 88 — and that is exactly how far it was taken
before being checked. On the full set it collapses: in linear terms Thanos's gauntlet sits at
0.013 and K-2SO's `DROID_Misc` at 0.044, both genuine glows, leaving no honest gap above them.
A threshold drawn from the first two would have **stripped Thanos's gauntlet**, the one case the
existing code comment already named as a material that legitimately glows.

What separates them is not how bright the map is but how much of it is **lit**. A glow mask is
local — a visor, a gauntlet, a pair of eyes — on a black field. A colour copy covers the whole
UV layout:

| Map | black | lit |
|---|---|---|
| Master Chief `MKV_Helmet` | 99.98% | 0.01% |
| K-2SO `DROID_Body` | 99.90% | 0.03% |
| Thanos gauntlet | 95.43% | 4.06% |
| Clone Trooper Phase 1 helmet | 93.73% | 4.17% |
| K-2SO `DROID_Misc` | 89.91% | 9.10% |
| Prix eyes | 43.82% | 0.92% |
| **Ariel `Irises_Emissive`** | **0.00%** | **100.00%** |

Not one black pixel in Ariel's. Every genuine mask lights at most 9.1% of its area; the copy
lights all of it. The threshold is **50%** — five times clear of the genuine maps on one side
and twice clear of the copy on the other.

Worth noting what this did *not* explain: killing the emission changed her render not at all.
It is a real defect and it is fixed, but it was never the reason her eyes were white. Rendering
the hypothesis before shipping it is what kept that from being written down as the answer.


## Posing is the only check that can see a detached part

The podium browser covers textures, colliders, proportions and the spring sim. It cannot cover
this class of bug at all, and the reason is in *Spring bones need bones* above: **at rest a bone
nothing drives and a bone that is driven are identical.** A part hanging on a dead bone renders
perfectly on the podium and hangs in space the moment the character moves.

`tools/character-pipeline/pose_check.py` is the test that can see it. It reads the humanoid bone
map out of the file, rotates eight of those bones, and then **measures** rather than renders:
every mesh is evaluated at rest and again posed, and each vertex's displacement is compared.

Measure, not look, because a posed *picture* misleads exactly the way the podium does — and
measure **per vertex**, not per mesh, because the documented cases are a belt and a pair of eyes
that live inside a mesh which does move. A per-mesh maximum calls those healthy.

The detector is verified in both directions, because one that has never been seen to fire has not
been verified:

- `POSE_CONTROL=<mesh>` unbinds a mesh from the armature before posing. Lola's hair then reports
  `max=0.0000  <-- WHOLE MESH DID NOT MOVE`, and the moved count drops from 4 to 3.
- `POSE_STATIC_EPS=0.05` raises the static threshold until the partial branch has to fire. Judy's
  `Cloth` mesh then reports `26.9% static (2453 verts), z 0.28..0.49` — the hip and pelvis
  vertices that genuinely sit near the pivots. At the real 1 mm threshold it reports nothing.
- If *nothing* moves the run prints `CONTROL FAILED` and says so, rather than reporting a clean
  sweep.

**Measured 2026-11-11, and the table in the pipeline README is stale.** Every character listed
there as hanging off an undriven bone now poses clean — every mesh moves, and no mesh has a
static region above 1 mm:

| character | result | does it describe the INSTALLED bundle? |
|---|---|---|
| Ariel, Heels | clean | **yes** — built and installed from these exact VRMs this session |
| Lola Bunny | clean | yes — the install was written minutes after the VRM |
| Judy Hopps | clean | yes — same |
| Doom Slayer, Jinx | clean | yes — same |
| Gadget Hackwrench | clean | **no** — the VRM is NEWER than the installed bundle |
| Joker | clean | unknown — no VRM in the collider set to tie to it |
| Sonic | clean | **unknown, and not determinable** — see below |

Sonic is the honest gap. Five candidate `.vrm` files exist and all five carry **10,259 verts** and
the same texture names, because what went wrong with him was the *rig*, not the geometry — "wrong
rig family breaks skinning while preserving every triangle". Reading the installed bundle does not
settle it either: UnityPy reports `verts=0` for a `.yargchar`, which is a limit of the reader, not
a measurement. So his pose result cannot be attributed to what is installed. His podium shot can,
because that is rendered from the installed bundle, and it is correct.

Timestamps are the weakest evidence in that table and are marked as such on purpose: `Copy-Item`
preserves `LastWriteTime`, which this project has already been caught by once.

## The rig is readable from a .yargchar even when the geometry is not

*The built VRM is not necessarily what is installed* leaves a question it does not answer: given
an installed bundle and several candidate `.vrm` files, **which one produced it?** The obvious
checks do not settle it. Triangle and vertex counts are identical across a character's variants
whenever what differs is the rig, and UnityPy reports `verts=0` for a `.yargchar` — a limit of
the reader, not a measurement, and exactly the kind of zero that reads as an answer.

The rig *is* readable. GameObject names survive in a bundle and every bone's `Transform` carries
`m_LocalPosition` and `m_LocalRotation`. `tools/character-pipeline/identify_build.py` compares
those in three steps of increasing resolution — **skeleton names** catch a different rig family,
**bone lengths** catch a rescale, and **rotation angles** catch a re-pose, which neither of the
other two can see. Rotations are compared as angle magnitude (`2*acos|w|`), which survives the
Unity/glTF handedness difference where a raw quaternion does not.

Sonic was the case that needed it: five candidates, all carrying 10,259 verts and the same four
textures.

| candidate | names | verdict |
|---|---|---|
| `JunioSonic` | 0.0% | nothing in common — a different model |
| `withcols/Sonic` | 4.3% | the wrong-rig-family rebuild, `Hips` 180° against 0° |
| `SonicHD`, `SonicHD_nt` | 97.1% | `Hips` 0.518 against 0.5206 — ruled out on length |
| `rollout/out`, `reg-Sonic`, `SonicHD_fix` | 97.1% | **34/34 bones agree in length and rotation — INSTALLED** |

The two ruled-out ends are the controls. A comparison in which nothing fails has not been shown
to discriminate, and the 0.0% / 4.3% rows are what make the 97.1% rows mean something.

### Sonic's wrists are NOT off — retracting the previous entry

**The entry that stood here was wrong, and so was the one before it.** Both reported a wrist
defect in Sonic's installed build. There isn't one. It is worth keeping the record of how two
different measurements each produced a confident wrong answer, because both traps are easy to
fall into again.

**Wrong answer 1: local rotations.** Comparing each bone's rest rotation against its mirror gave
`LeftHand` 0.87° against `RightHand` 69.76°, and `LeftHandIndex1` 0.09° against 127.43°, with the
shoulders symmetric to 1° as an apparent control. Those numbers are real. They mean nothing: a
local rotation is relative to the parent, and left/right bone **rolls** need not match. The
shoulders agreeing showed only that two particular bones happened to agree, not that disagreement
implies misplacement.

**Wrong answer 2: bone axes.** Measuring the angle between each bone's own head-to-tail direction
gave "the wrist is bent exactly 90.00° on both sides" on the reverted build — a number so clean it
read as a diagnosis. It is an artefact. The VRM importer **synthesises a bone tail** wherever the
hierarchy does not pin one, and a synthetic tail points somewhere arbitrary. Measured:

| rig | `Hand` tail vs child head | bone length | reading |
|---|---|---|---|
| Sonic, installed | gap 0.0000 | 0.1418 | 0.00° — genuine |
| Sonic, reverted | gap **3.4903** | 1.8199 | "90.00°" — **artefact** |
| Ariel | gap **0.0741** | 0.0067 | "86.8°" — **artefact**, eleven times the bone |

Ariel renders with perfectly straight arms, which is what made her the case that exposed it.

**What is actually true.** Measured joint to joint — the angle between the shoulder-to-elbow
segment and the elbow-to-wrist segment, built from bone **head** positions only, which no
synthesised tail can disturb — Sonic's installed rig is straight and symmetric:

| | installed |
|---|---|
| elbow | 0.00° / 0.00° |
| wrist | 0.00° / 0.00° |
| knee | 0.02° / 0.00° |
| ankle | 55.6° / 57.0°, Δ1.5° — an ankle is *supposed* to be bent |

Mirrored bone heads agree to 2–7 mm, the humanoid map is correct and symmetric on both sides, and
close-up renders show two correctly formed, correctly attached mirror-image gloves. **There is
nothing to fix**, and the attempt to fix it was abandoned for that reason rather than completed.

`tools/character-pipeline/limb_check.py` is the measurement that survived. It uses joint positions
only, reports how many bones carry a synthetic tail so nobody re-derives the artefact and believes
it, and has a `LIMB_CONTROL=1` mode that displaces a wrist to prove the detector fires — it reads
73.46° on the bent side against 0.00° on the other.


## Sweeping all 66: check the bundle, and calibrate the threshold

Only **29 of the 66** characters still have a `.vrm` anywhere, so a sweep over source files silently
covers less than half the set — and covers it with builds that may not be what is installed. Both
problems go away by reading the installed `.yargchar` instead, which carries everything needed:
every bone's `Transform`, and the Avatar's `m_HumanDescription.m_Human`, a list of `m_BoneName` ->
`m_HumanName` that *is* the humanoid map. `tools/character-pipeline/limb_check_installed.py` does
that, and it agrees exactly with the `.vrm`-based check where both can run, which is how it was
validated.

Two traps were hit building it, both the same shape as ones already in this document:

- Unity spells body bones `LeftUpperArm` but finger bones `Left Index Proximal`, **with spaces**.
  Looking up only the first form dropped every wrist row, and a missing row reads exactly like a
  clean one.
- Writing the fix through a bash heredoc turned `` into a literal `0x01` byte, so the
  substitution silently deleted the capital it was meant to keep. The file *looked* right when
  printed. See *Bash heredoc eats backslashes* — same quirk, new disguise.

**The first thresholds were guesses, and wrong.** "Bent more than 30°" is meaningless for the
wrist: the index finger naturally starts off to one side of the wrist, so the population median
there is **16.9°** and a healthy character reads 20. Measured over all 66:

| joint | median | p90 | max | asym median | asym p90 | asym max |
|---|---|---|---|---|---|---|
| elbow | 0.0 | 0.0 | 15.4 | **0.0** | 0.0 | 0.0 |
| wrist | 16.9 | 23.6 | 36.1 | **0.0** | 2.7 | 16.0 |
| knee | 0.0 | 2.2 | 8.9 | **0.0** | 0.0 | 0.0 |
| ankle | 62.6 | 75.4 | 97.4 | **0.0** | 1.2 | 26.4 |

**Asymmetry is the signal worth trusting.** Its median is 0.0 at every joint, and elbow and knee
asymmetry is *exactly* 0.0 for all 66 — a character compared against its own other side needs no
population baseline. Absolute angle only means something where the population says the joint
should be straight, which is the elbow and the knee.

### What the sweep found

| character | reading | verdict |
|---|---|---|
| **The Mandalorian** | ankle **45.9 / 72.3, Δ26.4** and wrist Δ10.1 | **his authored stance** — see below. Visible (left boot pointed over the podium edge, right flat) but carried in from the source, not introduced here |
| Alcina Dimitrescu | wrist 28.7 / 12.7, Δ16.0 | **expected** — her static pose *is* her shape, and the pipeline deliberately "relaxes the left hand, 61.3 vs 0.0 deg" |
| Kasane Teto | elbow 15.4/15.4, knee 8.9/8.9 | symmetric; she is the one that does not animate at all and stands in her T-pose |
| Adachi Rei | knee 6.6/6.6 | symmetric, mild |
| Jessica Rabbit, Shrek, Peacemaker | wrist Δ5.2–6.5 | marginal, just over the 5° limit |
| Jessica Rabbit | ankle **7.3/7.3** against a median of 62.6 | symmetric — her feet are pointed, which is what heels do |
| B1 Battle Droid, Mannequin, Steve, Shadow | no finger bones mapped | no wrist row; worth knowing rather than reading as a pass |
| B1 Battle Droid, Mannequin, Peacemaker, Steve, Vigilante | no toe bones mapped | no ankle row |

### The Mandalorian's ankle is his stance, and the installed build is the best one there is

The sweep's one striking outlier turned out to be authored, and the investigation is worth keeping
because every intuition along the way was wrong.

**A symmetric build appeared to exist.** `rollout/out/The Mandalorian.vrm` measures ankle Δ1.96
against the installed Δ26.4, carries the same ten textures and the same 28,748 triangles, and has
the 4-spring cape rig. It is also **upside down** — head at z −1.355 below hips at −0.829. It is
the stale VRM from the incident where he came back inverted, and installing it on the strength of
one good-looking number is precisely the move that broke him before.

**The other candidate is worse, not better.** `Mandalorian.vrm` is upright, same geometry, and has
*straighter* wrists (0.00 against 19.8/29.9) and a better ankle (Δ9.27). It also has **0 spring
bones** — no cape rig at all, the thing the recipe works hardest to get — and **28 humanoid bones
against the installed 52**. Swapping to it would trade a 26° ankle for a static cape and half the
animation mapping.

**And a rebuild would not help, because the asymmetry is in the source.** In the Mixamo re-rig
`mando-mx.blend` the feet mirror correctly in X and Z and differ in Y by **7.3 cm**:

| | LeftToeBase | RightToeBase |
|---|---|---|
| X | 0.2212 | −0.2096 — mirrored |
| Z | 0.0614 | 0.0603 — matches |
| **Y** | **−0.1623** | **−0.0897** |

His left foot is further forward and more extended than his right in the source model's own pose.
That is a relaxed standing stance, the same class as Jessica Rabbit's pointed feet (7.3° against a
population median of 62.6 — heels) and Alcina's pose-as-shape. The pipeline did not introduce it
and cannot remove it without editing the rest pose by hand, which would change the skinned mesh's
rest relationship for a cosmetic gain.

**So nothing was changed.** The installed Mandalorian is the best build that exists: upright,
caped, 52 humanoid bones, no detached parts, and correct on the podium. The sweep's job was to
find outliers, and it did; this one's explanation is "that is how he stands".

## What is in the bundle: animation, and which fingers the game can actually move

A render shows the mesh. It cannot show whether the character has anything to *play*, or which
bones the game is able to drive. Both are readable from the installed `.yargchar`, and
`tools/character-pipeline/bundle_audit.py` reads them across all 66.

**Animation.** A character with no `AnimatorController` and no `AnimationClip` stands in its bind
pose forever, however good the rig is. Measured: **Kasane Teto is the only one of the 66**, with
`clips=0 ctrl=0` against 5 or 6 clips and 1 controller for everyone else. That confirms what the
pipeline README already recorded, and now by measurement rather than by inspection of one file.

**Finger coverage.** Unity retargets through the humanoid map, so a finger bone that is not in
that map is never driven, whatever the animation does. Across the 66:

| mapped finger bones | characters |
|---|---|
| 30 (all five, both hands) | 48 |
| 24 | 6 |
| 28 / 22 / 18 / 12 | 1 each |
| 6 (index only) | Sonic, Yui Suzukaze |
| **0** | B1 Battle Droid, Mannequin, Steve, **Shadow the Hedgehog** |

**Shadow corrects a documented claim.** The pipeline README says his "fingers do not move" because
of "finger bones that are mapped but not weighted". They are **not mapped at all** — zero finger
bones in his humanoid map, and only 21 humanoid bones in total against a typical 52. The symptom
was right and the stated cause was wrong.

**And the "closed fists" complaints are not what they look like.** Judy Hopps maps 18 finger bones
— index, little and thumb, with **no middle and no ring** — and Miku maps 22, missing ring entirely
and carrying middle at only 4 of 6. That correlation is tempting. But rendering their hands settles
it: **both rest poses are open, flat hands with the fingers extended**, not fists. So this is not a
rest-pose defect. What *is* true, and worth recording in its place, is that the unmapped fingers
can never be moved by the game — during a performance Judy's middle and ring will stay straight
while her index and little curl.

Judy's mapped chains are named `*_fused`, which is the deliberate fifth-finger fusing step, so some
of that reduction is by design rather than by accident. Telling the two apart needs the recipe, not
the count — which is why the count alone was not treated as the answer.

## Kasane Teto: the stated cause does not survive reading the game code

Teto's bundle really does have **no `AnimatorController` and no `AnimationClip`**, and she really
is the only one of the 66. But "and that is why she does not animate" does not follow, and the
attempt to fix her on that basis failed for a reason worth keeping.

**The game already supplies a controller.** `BackgroundManager.LoadAnimationDefaults` runs as the
first statement of `LoadCharacter`, and when the animator has none it loads
`Animations/Vocals/Default/DefaultController` from Resources. That controller **has states named
`Idle` and `Playing`** — exactly the two Teto's `VRMCharacter` is configured to use. `GetDefaultGenre`
returns the constant `"Default"`, so the path always resolves. Every hypothesis built on "the
controller is missing" dies here.

**She has no source, so a rebuild is not available either.** She is a *downloaded* `.yargchar`
(a copy sits in `yargchar-dl`), not something this pipeline built, which is why no controller was
baked in. There is nothing to re-export.

**What the sweep did establish.** Seven characters carry `_enableAnimationStates = 1` with
`Idle`/`Playing` — Adachi Rei, Harq Alkahana, both Hatsune Mikus, Inforder Trogen, Kaiser
Aufhänger and Teto. They are one family of community bundles built to drive their own clips. Six
ship 5–7 clips and a controller; Teto is the only one that ships neither.

### The bundled controller is discarded for 65 of the 66 characters

Reading the guard closely:

```csharp
if (!vrmCharacter.UseCustomAnimations && animator != null)
{
    var controller = animator.runtimeAnimatorController;
    if (controller == null || !vrmCharacter.UseCustomAnimations)
```

The outer test already guarantees `UseCustomAnimations` is false, so the inner `|| !UseCustomAnimations`
is **always true** and the `controller == null` check is dead. The default controller is therefore
loaded over whatever the bundle carried, for every character whose `UseCustomAnimations` is false.
Measured across the 66, **exactly one** has it set: **Adachi Rei**. Hers is the only bundle whose
own controller survives; the other 65 have theirs replaced, including the clips the exporter takes
trouble to bake in.

That is worth knowing on its own, independently of Teto — it means a bundled controller is nearly
always inert.

**So Teto is not fixed, and the cause is not known.** What is known is what it is *not*: not a
missing component (she has `VRMCharacter`, same script set as Judy, who works), not
`UseCustomAnimations` (hers is 0), not a mismatched state name, and not a failed Resources path.
Settling it needs the game rebuilt and run with logging around `LoadAnimationDefaults`, which is
the same rebuild the Gordon and Heels lipsync question is already waiting on.

## A .yargchar can be opened and edited in the editor. It cannot be written back.

"No source located" has been treated as terminal for three characters, and that is too strong —
a `.yargchar` **is** a Unity AssetBundle, and the podium shot harness already loads one every time
it runs. So the obvious repair route is: open the bundle, edit the prefab, export it again. Half of
that works.

**Opening and editing works.** Measured on Kasane Teto, whose bundle is the one of 66 with no
controller:

```
[REPAIR] assets in bundle: 2
[REPAIR] prefab asset: assets/_character.prefab
[REPAIR] BEFORE: animator=True controller=NULL avatar=human
[REPAIR] AFTER : controller=DefaultController
```

`AssetBundle.LoadFromFile` returns `_character.prefab`, it instantiates like any GameObject, and
its `Animator` is editable. That also confirms the missing controller through Unity itself rather
than only through UnityPy.

**Writing it back does not.** `BackgroundHelper.Export` reported success and exited 0, and the file
it wrote is **2,552 bytes against the original's 6,357,076**. Reading both back:

| | original | re-exported |
|---|---|---|
| GameObject | 149 | **0** |
| Mesh | 20 | **0** |
| Material / Texture2D | 7 / 3 | **0 / 0** |
| Avatar | 1 | **0** |
| contents | the character | `AssetBundle` + `TextAsset`, nothing else |

An empty shell. The cause is structural: the bundle builder packs assets from the **AssetDatabase**,
and a prefab instantiated from a *loaded bundle* references runtime objects that have no asset path.
Nothing is on disk for it to pack, so it packs nothing — and reports success doing it.

**So the route is not available as it stands.** Repairing a sourceless character would mean
serialising those runtime objects back into project assets first — meshes, materials, textures and
the avatar — which is a different and much larger job than "edit it in the editor". Worth knowing
before someone spends an afternoon on the obvious version, and worth noting that the file size was
the only thing that gave it away: exit code 0, a file present, and the log line saying OK.

## A rig can be wrong by a different amount in each limb

The Rock was reported as "limbs stretched into metre-long spikes". The cause is measurable from
the installed bundle alone: his skeleton spanned **4.47 m** against a **1.96 m** mesh, with bones
running 1.7 m *below* the floor. Across all 65 installed characters nothing else exceeds 2.50, and
that one is Alcina, who is canonically 2.9 m.

**Scaling fixed half of it.** The hips were already right — 1.122 on a 1.960 mesh is 0.573, and the
installed population sits at the same ratio — so scaling the rest skeleton about that point,
anchored on feet-on-floor, gave a factor of 0.387 and a skeleton of 1.73 m with the head at 1.76
(ratio 0.897 against a population norm of ~0.89).

**And it could not fix the rest, because the rig is not uniformly wrong.** Measuring each arm bone
against the centroid of the vertices it actually drives:

| bone | bone mid x | mesh centroid x | gap |
|---|---|---|---|
| LeftShoulder | 0.149 | 0.228 | −0.08 |
| LeftArm | 0.350 | 0.599 | −0.25 |
| LeftForeArm | 0.611 | 0.869 | −0.26 |
| LeftHand | 0.789 | 1.066 | −0.28 |

The legs needed 0.387 and the arms about 0.557, so one factor cannot satisfy both: the scale that
put his feet on the floor left his arms 26 cm short, flipping the error's sign rather than removing
it. Note this is **not** the A-pose/T-pose mismatch `bone_fit.py` warns about — both mesh and
skeleton have the arms horizontal at z≈1.5. The arms are simply the wrong length.

`tools/character-pipeline/fit_joints.py` places each limb joint at the boundary between the flesh
it separates — the midpoint of the weighted-vertex centroids of the two bones meeting there. That
is expressible per joint, which a scale is not:

| build | finger bones >5 cm from mesh | worst | all bones >5 cm |
|---|---|---|---|
| original | 30/30 | **135.3 cm** | 50/51 |
| scaled only | 30/30 | 27.2 cm | 41/51 |
| **joint-fitted** | **0/30** | **4.1 cm** | **4/51** |
| Ariel, for reference | 0/36 | 3.0 cm | 29/151 |

`bone_fit.py` documents "expect 0", and the fitted build is the first Rock to reach it.

**One bug worth keeping.** Connected bones must be disconnected before their positions are
written, or a child's head is dragged back to its parent's tail. But disconnecting also stops
children following their parent — so the first fitted build moved the hands and left all thirty
finger bones exactly where they were, and `FINGERFIT` came back **byte-identical at 27.2 cm**. A
number that does not move at all is a stronger signal than a number that moves the wrong way: the
fix now records every bone's original head and carries each untouched descendant by its nearest
fitted ancestor's displacement.

Verified end to end: geometry unchanged at 44,359 triangles across 21 meshes, upright, limbs
symmetric, posed displacement down from **2.36 m to 0.93 m** (Ariel 0.79), and the podium render
shows properly formed hands where there were spikes.

## An alpha channel in a game rip is as likely to be a specular mask as an opacity map

Added 2026-11-12, after sweeping every built `.vrm` for materials shipping `alphaMode: OPAQUE`
over a base map that carries real transparency. Roughly half the hits were not defects, and the
ways they were not are the useful part.

Gordon Freeman is the whole lesson in one character. He is a Half-Life 2 model and carries three
alpha channels of three different kinds:

| map | alpha | what it is |
|---|---|---|
| `lens` | median 63/255, **no extremes at all** | opacity. A uniformly semi-transparent pane, which is what a lens is |
| `eye-iris-green.tga` | median 113/255, black **exactly on the iris disc** | a specular mask. Honouring it makes his irises invisible |
| `onefreeman` | mean **0.1/255** | a specular mask. Honouring it erases his entire HEV suit |

Source engine stores an environment-map mask in the base texture's alpha as a matter of course,
and the histogram cannot tell you which kind you have. What can: **ask what the texture is FOR,
and whether honouring its alpha would erase that.** An alpha that is black precisely where the
subject is, is not an opacity map.

Three more shapes worth recognising, all met the same day:

- **An outline, not a silhouette.** Peach's crown map is 67.3% clear and reads as a clean cutout.
  Its opaque part is the *outline* of the jewel, so masking it carved the jewel out of the setting
  and left a wire ring. "77.4% solid" says nothing about *which* 77.4%.
- **Atlas padding.** An atlas is mostly empty space between its UV islands and that space is
  usually transparent, so measured over the whole image an ordinary body atlas looks exactly like
  a cutout. Measuring only inside the material's own UV triangles took the sweep from 24 hits on
  10 characters to 13 on 6, and the three it dropped to clean were three a render had already
  cleared.
- **Feathered, not two-valued.** The rule `build_vrm` uses to decide a *cutout* demands a mostly
  two-valued alpha, which eyelashes, hair cards and soft decals are not. Sayuri's lash map is
  46.7% clear and 0.3% solid and failed that test — while her lashes were two opaque black slabs
  over her eyes. "Is this a clean mask?" and "does this material ignore real transparency?" are
  different questions and only the second one is the defect.

### Three provenance holes, all in the same direction

The cutout inference only trusts a map whose provenance it recognises, and it was refusing the
three strongest:

- a texture the **author** wired into the material (`already_good` sets `_base_authored` and never
  set `base_from`, which the gate tested);
- a texture an **operator** pinned with `VRM_TEX` (the override branch set neither);
- and the probe itself measured a **blurred copy** — `image.copy()`, `scale(96, 96)`, which is a
  *filtered* resize, so it averaged. Averaging destroys the exact property being tested. Alcina's
  eyelash map measures 0.875 at full resolution, which passes, and 0.790 after the resize, which
  fails; her lashes shipped as black slabs because of it. The finer and sparser the mask, the
  worse it gets, and eyelashes and hair cards are precisely that.

### Enabling a cutout changes the SHADING MODEL, and on a big surface that shows

MToon is turned on only for materials that need transparency, so a character ends up with two
shading models. On hair cards and tear lines nobody notices. Peach's face is split across meshes
with `Peach_faceN` carrying a rectangular hole that another mesh fills, and the moment the filling
plate became a cutout it turned unlit while the face around it stayed lit — a tan plate on a cream
face with a hard polygon seam across her brow. `VRM_MTOON_ALL=1` puts the whole character on one
model, which is the answer when a cutout shares a continuous surface with an opaque material.

**Only a render showed it.** Every count was identical.

## A hand-written mapping that is not in the recipe table will be lost

Gordon Freeman's shape keys are FACS action units — `AU26ZR+AU26ZL`, `AU12R+AU12L`,
`AU18R+AU18L.001` — and they match none of the anchored viseme patterns, so his five bound visemes
came from a `VRM_VISEME=` map written by hand that his recipe row never recorded. Rebuilding him
from the documented recipe on 2026-11-12 dropped all 32 of his shape keys and bound nothing, and
**every count a census checks stayed identical**: 7,169 triangles, 4 meshes, 7 materials, 6 images.

The map was recovered from the bundle that still had it, by reading its `morphTargetBinds` back —
node, target index and weight — rather than reconstructed from the AU numbers.

Two rules out of it. **An env var a character cannot be rebuilt without belongs in the recipe
table the moment it is used.** And a census of triangles and meshes does not cover expressions:
`viseme_audit.py` reads `VRM10Expression` out of the bundle and reports which have real
`MorphTargetBindings`, because every VRM declares all 18 presets whether or not anything is wired
to them — a file always *looks* lipsync-capable. Measured over the installed set: **13 of 65 have
all five visemes, 52 have none, 10 can blink.** Of the 52, most have no mouth shape keys at all
and never can.

## A node name is not unique, and `identify_build` believed it was

`identify_build.py` compares the installed bundle's rig against a candidate `.vrm` by bone name.
A glTF node name is not unique and a VRM routinely reuses one: Pomni's meshes are called `Arm.L`,
`Leg.L`, `Eye.L` and so are her bones. The mesh node sits at the origin with an identity rotation,
the bone carries the real transform, and whichever was written last won the dictionary.

It therefore reported her rebuild as differing from her installed bundle at exactly those five
names, with every real bone identical to four decimal places — and on that reading she was
excluded from the collider rollout **twice**, as "the `.vrm` is not what is installed".

An ambiguous name is now dropped from the value comparison and counted. It is *not* dropped from
the name-overlap score: doing both pushed her from 92.5% to 87.1% and under the threshold, which
replaced one wrong verdict with another. The fix is verified in four directions — Pomni matches,
a known-good character still matches, Gadget Hackwrench still differs at 57 rotations because
hers is a real re-pose, and a deliberately wrong pairing still reports nothing in common.

The general shape, and it is the fourth instance of it in this document: **a comparison that
cannot name what it compared will quietly compare the wrong thing.**

## Choosing a viseme needs a render, and the framing must come from the skeleton

Pomni's mouth shapes are named `A`, `ClosedTeeth`, `ClosedTeethVariation` and `OpenNoTeeth` —
artist names that say nothing about which vowel they suit, which is why she sat at one bound
viseme while this document claimed five. Rendering each at weight 1.0 settles it in one look:
`A` is a wide open mouth with teeth and tongue, `ClosedTeeth` is lips retracted over a full row of
teeth, `OpenNoTeeth` is a rounded oval. That gives `aa`, `ee`/`ih` and `oh`/`ou`.

Worth recording how *not* to frame that render. Four attempts at pointing a camera at her mouth
using the shape key's own displacement — the full moved band, then the most-displaced quartile,
then an explicit z window — all landed on her **eyes**, because her mouth keys move the eye region
more than they move her lips. Framing on the head BONE, which `render_closeup.py` already did for
every other close-up, worked first time. `RENDER_KEY="Face/A=1.0"` drives the key and reuses that
framing.

And a gain applied to a shape that has never carried one must be checked at full weight **front
and side** before shipping, per *Exaggerate the mouth, or nobody sees it*: doubling a shape key
can tear geometry, and the front view hides a lip flip.

## Nothing in the project could express alpha blending, and nobody had counted

2026-11-12. Re-sweeping the whole installed set turned up one defect that is not a character's
fault at all. **Of the 396 URP/Lit materials in the 59 characters this pipeline built, 40 are
alpha-tested cutouts and not one is alpha-blended.** The single transparent material anywhere in
the 65 belongs to Adachi Rei — a downloaded MToon bundle we did not build.

The cause is one branch in `YargCharExporter.cs`:

```csharp
var rt = src.GetTag("RenderType", false, "");
if (rt == "TransparentCutout" || rt == "Transparent")
{
    nm.SetFloat("_AlphaClip", 1f);
    ...
}
```

Alpha testing and alpha blending are different things, and that `||` treated them as one. The
comment above it says "Hair, eyelashes and lace are alpha-cut cards", which is true of the case
it was written for; the `Transparent` arm was added to catch blends and catches them by
converting them into cutouts.

**Gordon Freeman is what it cost, and he is recorded in the README as fixed.** `lens.png` was the
reason `VRM_BLEND_MATERIALS` exists; its alpha has no extremes at all, which is what a lens is,
and the builder did its half correctly — his `.vrm` carries `alphaMode: BLEND`. Then the exporter
ran. Measured off the installed bundle: alpha from **0.153 to 0.624, mean 0.330**, against
`_Cutoff = 0.5`. So **79.3% of the lens is clipped away and the remaining 21% draws fully
opaque.** His glasses are not glass; they are a speckled mask. There is no value of `_Cutoff`
that expresses "uniformly 33% opaque" — that is the whole point of a blend.

The fix separates the two cases and gives `Transparent` URP's transparent surface (`_Surface 1`,
SrcAlpha/OneMinusSrcAlpha, `_ZWrite 0`, queue 3000, the `RenderType` override tag). The cutout
path is left byte-identical on purpose: the 40 materials that work today must not move.

### Why the render that confirmed Gordon's fix could not have caught this

It was a render of the **VRM**, where the blend is correct. The conversion happens later, in the
Unity exporter, and the only render that would have shown it is one of the installed bundle —
which is what `YargSceneShot.cs` is for. The general rule is already in this document in another
form: *a green must come from the thing being tested*. A fix verified one stage upstream of where
it is applied is not verified.

### The second half of the fix, DONE 2026-11-12

Everything below describes the gap as it stood; the resolution is the section
"The builder had no lever for a blend, and that is why it took a second day" further down.
Across the installed set `HARDCUT` went **20 → 1** and blended materials **1 → 20**.

The exporter can now carry a blend across. It does not decide to make one, and that decision is
`build_vrm.py`'s: the opacity-map path emits `alphaMode: MASK`, so a merged diffuse-plus-opacity
texture becomes a cutout whatever its alpha looks like. For a two-valued mask that is right. For
a feathered one it is destructive, and `alpha_sweep_installed.py` counts **20 materials across 6
characters** in that state:

| character | material | texture | clipped by the 0.5 threshold |
|---|---|---|---|
| Heels | `Heels_5` | `Std_Eyelash_Diffuse_OPA` | **99.6%** |
| Alcina Dimitrescu | `AlcinaDimitrescu_11` | `CILIOS.png` | 96% |
| Ariel | `Ariel_10` | `EyeMoisture_BaseColor` | 95% |
| Ariel | `Ariel_20` | `Ariel_Eyelash-Brow_Eyelashes_Base_Color` | 86% |
| Sayuri | `Sayuri_8`, `Sayuri_11` | `Eyelashes_Diffuse_OPA` | 85% |
| Gordon Freeman | `GordonFreeman_4` | `lens.png` | 79% |
| Heels | `Heels_18`, `Heels_19` | `front_hair_Transparency`, `tail_Transparency` | 56% |
| Alice Ivy | `AliceIvy_5` | `Std_Eyelash_Diffuse_OPA` | 45% |
| Sayuri | `Sayuri_10` | `Hair_Diffuse_OPA` | 40% |
| Sayuri | `Sayuri_1` | `Lace_Diffuse_OPA` | 32% |
| Ariel | `Ariel_25` | `Ariel_Hair_Cap_Base_Color` | 25% |
| Alice Ivy | 4 hair materials | `Hair_100n_Transparency_Diffuse_OPA` | 1% each |

Heels' eyelashes are the extreme and they are worth stating plainly: **99.6% of that texture is
below the threshold, so her eyelashes are very nearly not drawn at all** — and her row in the
README says her transparency was "Resolved 2026-11-11". It was resolved as far as the VRM. The
rebuild does keep all five of her transparent materials; it keeps them as cutouts that throw
almost everything away.

**99.6 and not 100.** The tool printed `100% clipped` at first, because the format was `%.0f`.
That is a claim of total invisibility, and the arithmetic does not support it — the separate
`INVISIBLE` test, which fires only when the texture's alpha *maximum* is under the cutoff, had
already and correctly declined to fire. A rounded number that reads as an absolute is the same
mistake as reading a count in a comment as a measurement; the format is `%.1f` now.

## The floating-prop sweep came back empty, and the first version of the check was the bug

Runlist item 2 had asked for a height sweep over the installed set since Peacemaker: his USDZ
carried a second figure's helmet floating above his head, and because the builder scales a model
to its target height by its own bounding box, scaling the FILE to 1.85 m scaled the HELMET to
1.85 m and left Peacemaker 1.51 m. Nothing in the build log said so, and nothing in a render of
him alone says so either — he is correctly proportioned, just small, which only reads as wrong
beside somebody else.

`m_LocalAABB` makes this cheap. It is in the mesh's own local space, and for these exports that
space *is* the model root: Peacemaker's head mesh reports a centre at y=1.535, head height for a
1.85 m man rather than anything local. So the union of the AABBs is the figure, with no
transforms to compose. That is asserted rather than assumed — `--strict` re-derives every bound
from the raw vertex buffer and aborts on a millimetre of disagreement, and it does not abort.

Incidentally, `identify_build.py`'s header says the mesh data "is not readable that way". That is
true of UnityPy's `obj.read()` convenience wrapper, which reports `verts=0`, and false of
`read_typetree()`, which hands over the whole vertex buffer. A limit of one accessor was written
down as a property of the format.

**The result: 51 of the 52 characters with a documented target height measure it to within
0.8%**, Peacemaker among them at 1.850 exactly, and **no character in the set carries a mesh
detached from its body.** The one exception is Jessica Rabbit at 1.867 m against a documented
1.80 — +3.7%, carried in from whatever exclude shipped her.

### The check flagged twelve characters, and all twelve were the check's fault

The first version measured *how far the tallest mesh clears the top of everything else*, which
sounds like the same question. It flagged 12 of 65, and the names gave it away at a glance: Judy
Hopps' tallest mesh is her **face**, Lola Bunny's is `C038_SkelMesh` — her whole body — and
Shadow's is `RIG`. On any character whose accessories sit low, the tallest mesh is the character.
Adachi Rei scored 99%, because she has two meshes and one of them is a flat sliver at her feet,
so "clears the rest" was the height of her entire body.

What Peacemaker's helmet did was sit above him **with nothing in between**: its lowest vertex was
higher than his highest. That is a test about *disjointness*, not about rank, and it cannot fire
on a body mesh, because the body is what everything else is measured against. The body is now
defined as the mesh of greatest vertical extent, its span grows to absorb anything overlapping it
— repeatedly, so a hat that overlaps the head and a plume that overlaps the hat are both part of
the figure — and only a mesh whose whole span is clear of that counts.

**And a check that fires on nothing has to be shown firing.** `--selftest` runs the real decision
function (not a copy of it, which would be free to agree with itself) over four shapes:
Peacemaker's actual geometry, which must flag at +22.5% inflation, and Judy's, Lola's and Adachi
Rei's, which must all come back clean. Without that, "0 of 65" and "the detector cannot detect"
are the same output.

## Three of the eight classes are closed, and that is a result worth recording

The same sweep re-ran every installed-side check over all 65. Three came back with nothing new,
and saying so is the point — an unswept class and a clean class look identical in silence:

- **Limb geometry.** Every character the sweep flags is already explained above: the
  Mandalorian's ankle is his authored stance, Alcina's wrist is her pose-as-shape, Jessica
  Rabbit's pointed feet are heels, and the marginal wrists are marginal. No new findings.
- **Animation and finger mapping.** Unchanged: one controller and 5–7 clips everywhere except
  Teto, and the finger-coverage table stands.
- **Floating props.** Zero, as above.

Against that, one class turned out to be five times larger than it had ever been counted, because
the tool that measured it could only read a `.vrm`, and **25 `.vrm` files survive here, covering
about 22 of the 65 characters** — four of them are variants of Iron Man alone, and a `.vrm` being
present does not even mean it is the build that is installed, which `identify_build.py` has caught
twice.
`alpha_sweep.py` found Miku's skirt, Peach's eyes, Alcina's eyelashes, Sayuri's lashes and Heels'
transparency — and had never been pointed at the other forty-odd. Silence from a tool that never looked
is not a clean result, which is the verify-a-zero-with-a-control lesson arriving from a third
direction. Read from the bundle instead, the alpha class is **74 materials across 22 characters**:
45 opaque-with-alpha, 20 soft-alpha-as-cutout, 9 cutouts with no alpha at all.

Most of the 45 will not be defects. Gordon alone carries three alpha channels of three different
kinds and only one is opacity; The Rock's `eye_ov` was already investigated and retracted. The
honest output is a candidate list with its instrument attached, and the instrument here is weaker
than the `.vrm` sweep's in one specific way: it is **not UV-masked**, so a material sharing an
atlas can read as alpha-carrying because of a region its geometry never samples. That limitation
is in the tool's header rather than in a conversation.

## ~~The six characters could not be rebuilt~~, and the patch that looked right rendered worse

**All six were rebuilt on 2026-11-12** — see "The builder had no lever for a blend" below.
What follows is how the wrong conclusion was reached and what the stopgap measured, both of
which are still worth having.

2026-11-12, the same day. With the exporter able to express a blend, the obvious next step was to
rebuild the six characters whose soft alpha ships as a hard cutout. None of them can be rebuilt
on this machine, and finding that out took three measurements rather than one.

**~~Three have nothing to rebuild from.~~ WRONG, and corrected the same day — every source
archive is in `%USERPROFILE%\Downloads\`.** This paragraph originally said Sayuri, Alice Ivy and
Gordon Freeman had no source and that "the archives lived in a session scratchpad that is gone".
They are all there, along with essentially the whole set, downloaded on 2026-11-07.

**The search was wrong, not the disk.** The recipe rows name the file *inside* the archive —
`Alcina102.blend`, `Valve_Gordon_Freeman.fbx`, `source/Sayuri dans.fbx` — so that is what was
searched for, and a file inside a `.zip` matches no `find`. The archives themselves are named
after the model listing, never after the character:

| character | archive in Downloads |
|---|---|
| Alcina Dimitrescu | `alcina-dimitrescu-resident-evil-village.zip` → `source/Alcina102.blend` |
| Gordon Freeman | `valve-gordon-freeman-model.zip` → `source/Valve_Gordon_Freeman.fbx` |
| Sayuri | `sayuri-dans.zip` |
| Alice Ivy | `alice-ivy-animated-by-jungle-jim.zip` |
| Heels | `topless-sexy-girl-with-heels.zip` → `source/untitled.zip` |
| The Rock | `the-rock.zip` → `source/The_Rock.7z` |
| Steve | `the-perfect-steve-rigged.zip` |
| Mickey Mouse | `talking.zip` |

**So search for the CONTAINER, not the content**, and sort by modification time: the whole set was
pulled within a few hours of 2026-11-07, so one known archive's timestamp finds all the others.
That is how the rest were located after this was challenged.

The consequence is not small. Everything below about the blend fix being unreachable was reasoned
from a false premise: these characters **can** be rebuilt, which means they can have real alpha
blending from the corrected exporter rather than the lowered cutoff that was installed instead.
The cutoff builds are a stopgap, and the rebuild is the fix.

What remains true is the `.vrm` half: `%USERPROFILE%\Documents\YARG-Characters\` holds 25 `.vrm`
files covering about 22 of the 65, and the three relevant ones are older than what is installed.

**Three have a `.vrm` and all three are OLDER than what is installed.** `identify_build.py`:

| | names | length Δ | rotation Δ | verdict |
|---|---|---|---|---|
| Heels | 84.6% | 0 | 0 | differs — 130 installed bones against 110 compared |
| Ariel | 89.7% | 0 | 0 | differs — same shape |
| Alcina Dimitrescu | 95.1% | 0 | 0 | **MATCH** |

Zero mismatches with a name overlap below 90% is not a different model; it is **the same rig
minus some bones**, and the missing ones are the spring bones the 11-11 chest rig added. Exporting
either would trade a newer fix for an older one.

**And Alcina's MATCH is the instructive one.** Her rig matches and her materials do not: the
installed build carries the two cutouts her 11-12 rebuild added and the `.vrm` carries none.
`identify_build.py` compares names, bone lengths and rotation angles, and says so in its own
header — so a MATCH means *the same skeleton*, not *the same build*. That distinction had never
been written down anywhere a reader would meet it before relying on the verdict.

### A .yargchar cannot be rebuilt by Unity, but it CAN be rewritten by UnityPy

These are different operations and the project had only measured the first. `BackgroundHelper.
Export` on a prefab loaded from a bundle writes a 2,552-byte shell, because the bundle builder
packs from the AssetDatabase and nothing loaded from a bundle has an asset path. UnityPy does not
build anything — it edits the serialized file and writes it back — so that limit does not apply.

Measured on Gordon Freeman: load, change one material's render state, save, and the result still
reports `clips=6 ctrl=1 humanoid=52 fingers=30 meshes=4`, 5/5 bound visemes and 1.800 m, with a
read-back proving the other six materials byte-identical. The file shrinks (7.70 MB to 5.66 MB)
because the recompression differs, not because anything was lost.

### Every number was right and the render said no

`patch_alpha_blend.py --mode blend` set the full URP transparent state on his lens: `_Surface 1`,
`_AlphaClip 0`, SrcAlpha / OneMinusSrcAlpha, `_ZWrite 0`, queue 3000, `RenderType Transparent`,
`_SURFACE_TYPE_TRANSPARENT` added to the keywords — and that keyword *is* in the bundle's own copy
of URP/Lit, 68 keywords including `_ALPHATEST_ON` and `_ALPHAPREMULTIPLY_ON`. Every check passed.

Rendered on the real podium, **his lens turned into a solid opaque white rectangle covering both
eyes.** The cutout it replaced is 79.3% clipped, which at least leaves holes to see his eyes
through. The patch was strictly worse.

The leading explanation is that the *variant* carrying `_SURFACE_TYPE_TRANSPARENT` was never
compiled into this bundle, because no material used it at build time, and URP's `Alpha()` forces
`alpha = 1.0` whenever that keyword is not defined — so removing the clip bought nothing. A
keyword appearing in `m_KeywordNames` does not contradict that: that is the shader's keyword
table, not its list of compiled variants. This is stated as the leading explanation rather than
as established, because enumerating the compiled variants means decoding the subprogram blob and
that was not done.

**So the blend fix only works through a rebuild**, where the shader is compiled with a transparent
material present. The exporter change is still right and still necessary; it is just not
retrofittable.

### The podium harness is not deterministic, and the pixel diff nearly fooled me

Before reading the faces I diffed the two renders: 0.623% of pixels differed, with the large
differences spread over the whole body rather than the glasses. That looked like evidence the
patch had changed something global.

It was not. Rendering **the same file twice** under two names gives 0.593% differing pixels, max
difference 410 against the comparison's 643 — the same magnitude. The harness jitters that much
run to run, so a pixel diff cannot support any claim smaller than that, and the bounding box I
had read as "the change is everywhere" was describing noise.

What the control *did* establish is that the lens is stable: the same file rendered twice shows
the identical see-through lens both times, in first and second position. So the white pane is the
patch and not the harness. **The qualitative read survived the control that the quantitative one
failed** — which is the opposite of the usual order, and worth remembering before reaching for a
diff because it produces a number.

### Lowering the cutoff is the fix that works on a bundle, and it needs a render each

A cutout's threshold is a plain float the already-compiled `_ALPHATEST_ON` path reads, so moving
it depends on no shader variant and cannot fail the way the blend did. It cannot produce a
feathered edge — the result is still a hard cut — but for an eyelash losing 98.7% of itself at
0.5, a hard-edged lash is the difference between a lash and nothing.

Rendered on Heels, who is the worst case:

| `--keep` | lash `_Cutoff` | rendered result |
|---|---|---|
| installed | 0.500 | no eyelashes at all; hair sparse |
| 0.90 | 0.039 | lashes return, and the faint fringe draws at FULL opacity — a heavy red-brown rim around each eye. Worse than nothing |
| 0.45 | 0.165 | a fine dark lash line on both eyes, no rim. Her hair at 0.157 is fuller too |

**The two good values came from opposite ends and landed in the same place.** Her eyelash wanted
`--keep 0.45` and her two hair materials wanted `0.90`, and those are 0.165 and 0.157. A share of
the ink is the right way to *discover* a value; the value itself then travels between materials
better than the share does, which is why `--cutoff-to` exists.

**And an absolute cutoff needs a floor, or it becomes the defect it is undoing.** A flat `0.16`
suits her lash and her hair and would have **erased her tear line**, whose alpha peaks at 0.047 —
the tool printed `keeps 0% of the ink` for it, in the same run that printed 90% and 46% for the
other three. A cutoff is now capped at 90% of the material's own maximum alpha, and the same
material re-run comes back `0.500 -> 0.042 (keeps 100% of the ink) [capped: its alpha peaks at
0.047]`. A patch that can reduce a material to nothing is not a repair, and this one was one run
away from proving it the hard way.

### All six rendered at 0.16, and the verdict is different for every one of them

This is the part that could not have been predicted from the numbers. Every one of these
materials is the same kind of defect, measured the same way, repaired with the same value — and
the outcome ranges from "fixes a glaring fault" to "introduces a worse one".

| character | materials | rendered result | installed? |
|---|---|---|---|
| **Alice Ivy** | `AliceIvy_5` eyelash | **solid black bars over both eyes become real lashes.** The biggest single improvement in the set, and it was ranked next to last by clipped-ink share (34%) | **yes** |
| **Heels** | eyelash, two hair, tear line | lashes appear where there were none; hair noticeably fuller; tear line preserved by the cap | **yes** |
| **Sayuri** | two eyelash, hair, `Moles` | modest: slightly heavier, better-defined lashes, slightly fuller hair. No regression | **yes** |
| **Ariel** | eyelash, hair cap, **eye moisture**, **cornea** | **regression — her irises disappear.** `EyeMoisture` at 0.16 draws an opaque white film over the eye, so she looks blank-eyed. Re-run on the lash and hair cap ALONE: irises back, lashes slightly fuller, no regression | **yes**, the two-material version |
| **Alcina Dimitrescu** | `CILIOS` eyelash | **no visible change at all** — the two renders are byte-identical in size. At 2.9 m her head is above the character-select camera, which this document already records | no |
| **Gordon Freeman** | `lens` | the cutoff route cannot help a pane: any threshold gives a hard-edged lens. Needs the blend, which needs a rebuild | no |

**The lesson is in the ranking.** Alice Ivy was 11th of 11 by clipped-ink share and produced the
most visible improvement in the set, because her lash card sits directly over her eyes at a size
the camera can see. Alcina was 2nd by share and produced nothing, because her head is out of
frame. **How much of a texture a threshold destroys says nothing about how much of the CHARACTER
is destroyed** — that depends on where the material sits and whether anything is looking at it.
The measurement is how you find candidates; it is not a ranking of importance, and treating it
as one would have installed the regression and skipped the best fix.

**Measured after installing**, the remaining loss is roughly halved everywhere it was touched:
Alice Ivy comes back completely clean, Heels' lash went 98.7% → 53.8%, Sayuri's went 71.5% →
40.9% and 77.3% → 43.7%, Ariel's 73.4% → 31.3%.

Two materials no cutoff can ever help are now named by the sweep rather than hidden among the
cutouts: **Heels' `Std_Eye_Occlusion_L` has an alpha maximum of 0.000** — the texture carries no
opacity data at all, so it draws nothing whatever the threshold is — and **Ariel's `Cornea` peaks
at 0.051**, which is a pane and wants a blend. Both predate this work and both need a rebuild.

Ariel's failure is the same thing from the other side. `EyeMoisture` is a transparent film over
the eyeball — its alpha is 95.4% mid-range, exactly the signature that says "this wants a blend,
not a cutout". Giving it a lower cutoff instead makes *more* of a thing draw that should not be
drawing opaquely at all. **A material that genuinely needs a blend is made worse by a better
cutoff**, and the sweep cannot tell those apart from the lashes, which need exactly the same
numbers and want the opposite treatment.

## The Rock had gorilla arms, every check passed him, and our own repair did it

2026-11-12, found by looking at him in the game rather than by any tool here. His silhouette is
wrong — the arms start far too wide and the whole figure reads ape-like — and **every measurement
this project owns said he was fine**:

- `limb_check_installed.py` → `worst=0.38`, elbow 0.0/0.0, knee 0.0/0.0. Perfectly symmetric.
- `height_check_installed.py` → 1.960 m against a documented 1.96. Dead on.
- `bundle_audit.py` → 52 humanoid bones, 30 fingers, 6 clips, 1 controller.

All three are correct and none of them measures the thing a person notices first, which is
**segment length relative to the body**. Angles can all be right and totals can all be right
while the pieces in between are the wrong size. That gap is now closed by
`proportion_check_installed.py`, and the first run named him immediately:

| | shoulders | reach | upperarm | forearm | thigh | shin |
|---|---|---|---|---|---|---|
| population median (65) | 0.249 | 0.938 | 0.181 | 0.174 | 0.292 | 0.286 |
| **The Rock, installed** | **0.548** | **1.268** | 0.208 | 0.152 | 0.320 | 0.227 |
| The Rock, before our fit | 0.276 | 0.931 | 0.160 | 0.167 | 0.294 | 0.276 |

**His arms are not long. His shoulders are twice as far apart as anyone else's** — +4.9 sigma, the
widest in the set — so the arms begin out at the edge of the silhouette. "Gorilla arms" is the
right description and the wrong diagnosis, which is why measuring the arm segments alone would
have found nothing.

### The pre-fit backup is the control, and it exonerates the model

`The Rock.prescale.yargchar` is the build from before `fit_joints.py` ran. Its proportions are
**normal on every segment** — shoulders 0.276 against a median of 0.249, reach 0.931 against
0.938 — on a skeleton 4.18 m tall for a 1.96 m mesh. So the source rig was correctly proportioned
and merely the wrong size, and the thing that broke him is our own repair.

### Why the fit broke exactly this joint

`fit_joints.py` places a joint at the midpoint of the weighted-vertex centroids of the two bones
meeting there. That is sound where two flesh clusters lie along one axis and the joint really is
the boundary between them: an elbow, a knee, a wrist, an ankle. The arm chain was written as
`Shoulder → Arm → ForeArm → Hand`, so its **first** fitted joint was the clavicle-to-upper-arm
one — and there the rule does not hold. The clavicle's cluster is a small patch beside the neck;
the upper arm's is a large mass offset sideways. Their midpoint sits out in the deltoid, not at
the joint, and the more muscular the model the further out it lands. The Rock is the most
muscular model in the set.

The leg chain never had this problem because it starts at `UpLeg`, so its first fitted joint is
the knee and the hip is never moved. The arm chain now starts at `Arm` for the same reason.
`FIT_SHOULDER=1` restores the old behaviour, so the measurement above can be reproduced.

His legs were distorted too, less visibly: shin 0.276 → 0.227 and thigh 0.294 → 0.320, a knee
pushed down by about 17% of the shin. That is the same rule applied to a joint it does suit,
getting a worse answer than leaving it alone — which is the harder half of this finding. The
centroid fit is not merely wrong at the shoulder; on a heavily muscled figure whose rig was
already proportioned correctly, it was not needed at all.

**The lesson for the tool list**: a repair that moves geometry needs a check that can see what it
moved. `fit_joints.py` shipped with `bone_fit.py` as its verification — "how far is each bone from
the mesh it carries" — which rewards exactly what the centroid method does, and so could never
have caught this. A verification derived from the same idea as the fix agrees with the fix.

### Rebuilding him found a step that was documented and never written down

His archive is `the-rock.zip` in Downloads, holding `source/The_Rock.7z`, so he can be rebuilt.
The first rebuild reproduced the **original defect verbatim** — a skeleton spanning 4.4726 m for
a 1.96 m mesh with the feet 1.7011 m below the floor — because the first of the two documented
corrections exists in no script. His row says "scale the rest skeleton about the hips (already
correct at 0.573 of height) anchored on feet-on-floor" and then "`fit_joints.py` does both".
It does not; it only moves joints. The scale was done by hand, once, and was therefore not
repeatable. It is `scale_rig.py` now, and run on a fresh build it measures the documented numbers
back out: hips at 0.5725 of height, factor 0.3978.

**And then the fit turned out not to be needed at all.** Three builds, measured and rendered:

| build | shoulders | reach | upperarm | forearm | thigh | shin | rendered |
|---|---|---|---|---|---|---|---|
| population median | 0.249 | 0.938 | 0.181 | 0.174 | 0.292 | 0.286 | — |
| **scale only** | **0.276** | **0.931** | 0.160 | 0.167 | 0.294 | 0.276 | **correct** — deltoids, biceps, hands with fingers |
| scale + corrected fit | 0.295 | 1.272 | 0.344 | 0.145 | 0.315 | 0.224 | arms smeared into thin tapered tubes, hands flattened |
| installed (fit incl. shoulder) | 0.548 | 1.268 | 0.208 | 0.152 | 0.320 | 0.227 | gorilla arms |

(Ratios are scale-invariant, so the scale-only row is the same before and after `scale_rig.py`;
what the scale changes is stature, 4.18 m of skeleton down to 1.663 m for a 1.96 m mesh, where
the old build sat at 1.536.)

The scale alone puts every segment on the population median and leaves the geometry intact. The
fit, even with the shoulder excluded, moves rest bones out from under the skinned mesh and
smears the arms — the same "limbs stretched into spikes" symptom the fit was written to cure.

### That conclusion was wrong, and the podium render is what said so

The paragraph that stood here claimed the second stage was unnecessary — *"one uniform scale
about the hips satisfies both, and the evidence for the second stage was an artifact of the first
stage not being reproducible"*. It was written from a **rest-pose render of the VRM**, where the
scale-only build looks correct, and it is wrong.

Exported and put on the real podium, the scale-only build's **hands are destroyed**: every finger
stretches into a long curling strip hanging past his knees. That is the original "limbs stretched
into spikes" fault, surviving in the hands, and it is exactly what `FINGERFIT` measures — 30 of 30
finger bones more than 5 cm from their mesh, at 135.3 cm, before the fit ever ran.

**Only the animated pose shows a skinning fault.** That sentence is already in this document, two
sections above, about `YargCharHandRender.cs`. I rendered the rest pose, saw clean arms, and drew
a conclusion the posed render reverses — the same mistake as verifying Gordon's lens on the VRM
rather than on the bundle, made in the same day, after writing that one up.

So the honest reading of the three builds is narrower than "the fit is unnecessary":

- the **shoulder** step of the fit is harmful and is now removed — it doubled his span;
- the **scale** step was missing from the scripts entirely and is now `scale_rig.py`;
- the rest of the fit — elbow, wrist, knee, ankle, and the descendants it carries — **is load
  bearing**, because the source rig's hands genuinely do not sit in the source mesh's hands.

Which means the original claim this section doubted — that the rig is wrong by a different factor
in different places — holds for the hands even though it does not hold for the shoulders. The
defect was never "fitting is wrong"; it was "fitting the shoulder is wrong", and one bad joint in
a four-joint chain discredited the whole method.

### Resolved: scale, then fit everything except the shoulder

All three built, exported and rendered on the podium:

| build | shoulders | hands | verdict |
|---|---|---|---|
| installed since 11-11 | 0.548 | intact | gorilla arms |
| scale only | 0.276 | **fingers stretched past his knees** | worse |
| **scale + corrected fit** | **0.295** | **intact** | **installed 2026-11-12** |

The third fixes both: his arms hang at his sides instead of splaying out, and his fists are
fists. Everything else is unchanged — 6 clips, 1 controller, 52 humanoid bones, 30 fingers, 21
meshes, 1.960 m — and his wrist angle improves from 24.9/25.1 to 1.9/0.9. `The
Rock.pregorilla.yargchar` is the backup.

So the final recipe is **`scale_rig.py`, then `fit_joints.py` with the shoulder excluded**, and
the two earlier conclusions were each half right: the fit was never the problem and the shoulder
always was, and the scale was never optional and was never in a script.

## The builder had no lever for a blend, and that is why it took a second day

2026-11-12, after the exporter fix and after the source archives were found. The remaining
assumption was that a rebuild would now produce blended materials, because the exporter could
carry one across and the sources existed. It would not have, and one measurement said so before
a single build ran: **of the 20 flagged materials, only 3 were `alphaMode: BLEND` in their
`.vrm`** (`vrm_alpha_modes.py`)**.** The other 17 were `MASK`.

| character | BLEND in the `.vrm` | MASK |
|---|---|---|
| Heels | `Std_Eye_Occlusion_R`, `Std_Tearline_R` | 7, including the 99.6%-clipped eyelash |
| Gordon Freeman | `lens` | — |
| Alice Ivy, Sayuri, Alcina, Ariel | none | all |

So a plain re-export would have reproduced every cutout exactly, and reported success doing it.
**The cutout was the builder's choice, not the exporter's**, made by the opacity-map path, which
emits `MASK` whatever the alpha looks like.

`VRM_BLEND_MATERIALS` already existed for exactly this, and was guarded on `not cut`. A dedicated
opacity map sets `cut` before that branch runs, so naming such a material did nothing at all —
the one lever that could have said "this alpha is feathered, do not threshold it" declined to
fire on every material that needed it. **"A dedicated opacity map is the stronger signal" is an
answer to OPAQUE vs not. It is not an answer to MASK vs BLEND**, which is a question about the
*shape* of an alpha rather than its provenance, and an explicit name from someone who has looked
at the texture outranks an inference either way. The guard is gone; the switch now overrides an
established cutout and says so in the build log.

### Heels' left eye, and why the asymmetry was real

Her `_R` tear line and eye occlusion were `BLEND` while the `_L` of each pair was `MASK`. That is
not a quirk of the sweep: the archive's merged texture is literally
`Std_Eye_Occlusion_L_Diffuse-Std_Eye_Occlusion_R_Opacity.png`, so the opacity picker matched `_R`
by name, gave it the map, and left `_L` to ship as a cutout. The same class of fault as Sayuri's
`Eye_Shadows`, one archive later. **Name both halves of a left/right pair in any material list**,
because a texture named for one of them is not evidence that only one of them needs it.

### Hair was built both ways, because the cost of a blend cannot be read off an alpha channel

A blended card sets `_ZWrite 0`, so overlapping hair sorts by draw order instead of by depth; a
cutout does not have that problem. Whether that costs more than the hard edge gains is not
visible in any number the sweep produces, so Heels, Alice Ivy and Sayuri were each built twice
and rendered side by side on the podium.

| character | ink the threshold destroys | rendered | installed |
|---|---|---|---|
| Sayuri | 24.4% | hair stops being speckle and reads as hair | **blended** |
| Heels | 25.5% | hair continuous instead of dotted | **blended** |
| Alice Ivy | **1%** | the two are near-indistinguishable; the blend is slightly softer | **left a cutout** |

The rule that falls out: **blend the hair only where the sweep flags it.** At 1% there is nothing
to recover, so the blend is all cost and no benefit. This is also the measurement that retired
the "pane" rule withdrawn earlier the same day — that rule picked Alice Ivy's four hair materials
on a shape test, and the right answer for them turns out to be *leave them alone*.

### The clipped-ink number mis-ranked this twice, in opposite directions

It had already been recorded that the number over-ranked Alcina (2nd of eleven, renders nothing,
her head is above the camera) and under-ranked Alice Ivy (11th, biggest visible gain from the
stopgap). The rebuild inverted it again: **Gordon's lens was 6th at 79% and is the most improved
thing in the set** — a speckled mask over both eyes became glass you can see his eyes through —
while Alice Ivy, the previous champion, barely moved, because her lashes had already been
repaired by the stopgap. The number measures the texture. Nothing about it measures the
character.

### Gordon needed no rebuild, and that was the safer answer

His `.vrm` already said `BLEND`; his fault was entirely the exporter's. So his installed bundle
is a straight re-export of the same `.vrm` that is already installed — which also keeps his 32
FACS shape keys out of reach of a rebuild, and a rebuild is exactly what silently dropped all 32
of them once before. **Check whether a fix needs the earlier stage at all before re-running it.**

## Four colliders per character were guarding nothing

Found while rebuilding the six, and the more serious of the two faults.

`vrm_colliders.py` built its collider group by keeping the element that `sb.colliders.add()`
returned and reading `.uuid` off it afterwards. `sb.colliders` is a Blender
`CollectionProperty`; `.add()` may reallocate its storage, which leaves every earlier reference
pointing somewhere it should not. The add-on resolves each group reference by uuid at export and
silently drops the ones that do not match.

**The builder's log said `colliders: 10 in one group`. The exported file's group held six.**
Sayuri's was `[4, 5, 6, 7, 8, 9]`: her head, hip and left arm were measured, fitted, written into
the file, and guarded nothing. The surviving slice depends on when Blender happens to reallocate,
so it is not even stable — the same character built twice in one batch came out `[4..9]` once and
`[8, 9]` the next.

**A count printed from the builder's own list is not a measurement of what reached the file.**
That is the same distinction as the render-of-the-VRM above, one stage earlier, and it is the
second time in two days it has cost something here. The fix keeps the uuid string rather than the
element, and adds a check that compares the group's references against the colliders actually
present, so the log can no longer claim ten and ship six.

`collider_group_check.py` over all 30 `.vrm` files behind an installed character found three —
**Alcina, Pomni and the Xenomorph, four orphans each, always the head/spine and the left arm.**
All three are rebuilt and installed. The sweep prints a line for every file including the ones
with no colliders, and ends with a tally, for the reason already recorded in this document: a run
that finds nothing and a run that examined nothing look identical.

### A recipe row records the build, not the steps after it

Sayuri's rebuild came back `differs` against her installed bundle — 25 bones off by exactly 90°
or 180°, with every bone *position* identical — and her recipe row gave no hint why. The answer
is that `add_colliders.py` is a **round trip through the VRM**, and the installed Sayuri went
through it: that is where her 19 named collider nodes come from, and where the bone rolls were
normalised. Running the rebuild through the same round trip took her back to a clean `MATCH`.

Exact angles of 90° and 180° on bones whose roll is arbitrary — eyes, teeth, toes, share-bones —
are the signature of a convention difference rather than a re-pose. A re-pose does not land on
round numbers.

## Alice Ivy had a black disc over each eye, and it was a 5% film shipped at 100%

Reported from a render on 2026-11-12, after the alpha rebuild: the whites of her eyes were
black. The first thing to settle was whether the archive was like that. **It was not** — the
source `.fbx` rendered straight out of Blender has ordinary eyes, white sclera, grey-green
irises.

Her `Custom_Eye` mesh carries four materials: `Eye_Left` and `Eye_Right`, which are the eyeballs
and are correctly textured, and `EyeMoisture_Left` and `EyeMoisture_Right`, a wet-film shell that
sits in front of them. In the source that film is **black, `blend_method=HASHED`, alpha 0.051,
with no texture at all** — a 5% sheen. It shipped as `baseColorFactor [0, 0, 0, 1]`: the same
black at full opacity, which is a solid disc. Her real eyes were there the whole time, behind it.

**The lever already existed and is opt-in for a reason that does not apply here.**
`VRM_VALUE_ALPHA=1` carries a transparency stated as a VALUE across, and it is off by default
because it made Heels worse: her `Std_Cornea_L/R` are `HASHED` at **alpha 0.553 with a textured
base**, and honouring that washed her iris out against the sclera behind it. Alice's is the
opposite shape — **0.051, no texture, pure black** — and the difference between "55% transparent
over a texture that is doing work" and "95% transparent over nothing" is the whole decision.

Scanned before turning the switch on, because it is global to a character: on Alice it changes
those two materials and **nothing else**. Every other material of hers either has an image wired
into Alpha or sits at 1.000. That check is worth running for any character before enabling it,
and the same scan over the other four sources on disk says Alice is the only one affected —
Ariel and Alcina state no value transparency at all, Heels has the documented cornea pair, and
Sayuri's `Eye_Shadows` states alpha 0.000 but has `Eyelashes_Opacity.png` deliberately pinned
over it.

### Two things this says about the sweeps

**It is older than the work that exposed it.** The black discs are identical in the before and
after renders of the alpha rebuild, so neither that nor the collider fix caused it. It had been
shipping since she was built, through every automated check in the project.

**No alpha sweep could have found it.** `alpha_sweep_installed.py` keys on a material's base
MAP, and this material has none — it is a bare colour factor, so there is no texture to measure
and the material is simply invisible to the sweep. The general version, "an opaque untextured
material with a dark base colour is a solid slab of that colour", was run over all 30 characters
and flags five, of which four are false: Pomni's and Jessica Rabbit's flat-colour materials are
flat on purpose, which this document already records. **The heuristic cannot settle it; only the
source can.** That is why the first move here was to render the archive rather than to reason
about the bundle.

### The other four extracted sources were checked, and none of them has it

Alice's fault is a *class*, not a one-off, so the obvious next question is which of the other
characters carries it. `tools/character-pipeline/value_alpha_scan.py` is that check: it
reproduces every clause of the builder's `VRM_VALUE_ALPHA` condition except `not cut`, which
cannot be read from a source file at all — the builder also finds opacity maps by filename and
through `VRM_TEX`, and neither is visible in the material. So a hit is a **candidate**, not a
defect.

Run over the five sources that are extracted on disk, with Alice as the positive control:

| Source | Candidates | Verdict |
|---|---|---|
| Alice Ivy | **2** of 22 — `EyeMoisture_Left/_Right`, HASHED, alpha 0.051, base `[0,0,0]` | the defect, now fixed |
| Heels | 2 of 23 — `Std_Cornea_L/R`, HASHED, alpha 0.553, base **textured** | leave alone, and it is already documented why |
| Sayuri | 1 of 13 — `Eye_Shadows`, HASHED, alpha 0.000, base `[0.8,0.8,0.8]` | `cut` by the map `VRM_TEX` pins over it; never reaches the branch |
| Alcina Dimitrescu | **0** of 17 | states no value transparency at all |
| Ariel | **0** of 26 | states no value transparency at all |

The shipped side agrees, and it is the half that decides. Alice's pre-fix build carries the
signature exactly — `OPAQUE`, `baseColorFactor [0, 0, 0, 1]`, **no base map**. Heels' corneas
ship `OPAQUE` with `baseColorFactor [1, 1, 1, 1]` and a base map, so the flattening costs her a
55% see-through and paints nothing: that is a different, milder thing, and honouring the value
is the measured regression that made her iris vanish. Sayuri's `Eye_Shadows` ships `BLEND` and
textured, which is correct already. Head renders of all four confirm it: no disc over any eye.

Two cautions on reading the zeroes. **Ariel's 26 of 26 are opaque because her FBX wires no alpha
maps at all** — every transparency she has is found by the builder from filenames, so the
value-alpha branch has nothing to act on by construction, not by luck. And **Alcina ships three
materials at `baseColorFactor [0, 0, 0, 1]` with no base map** (`Material.013`, `Material.007`,
`Material.022` at 0.119): those are opaque *in the source too*, counted under `alpha>=0.99`.
Black by design is not a flattened transparency, and the generic "dark untextured opaque"
heuristic cannot tell the two apart — which is the same reason it returns four false positives
across the set.

**The other 25 installed characters are unchecked and cannot be checked.** This test reads the
source archive; theirs are not on disk, and nothing in a `.yargchar` or a `.vrm` distinguishes
"black on purpose" from "a 5% film flattened to 100%". Re-acquiring a model is the only way.

## The other 35 characters had never been checked, and the sweep that cleared them was reading half the set

`collider_group_check.py` reads `.vrm` files. Only **30 of the 65** installed characters still
have one on this machine, so when it came back clean it had cleared 30 characters and said
nothing whatever about the other 35 — while reading as though the question were closed. That is
the same hole this document already records under *Verify a zero with a control*, in a tool
written to avoid it.

`collider_group_check_installed.py` closes it. The spring-bone configuration survives the Unity
import whole, so the question the `.vrm` check asks of indices can be asked of the bundle's
path_ids:

    Vrm10Instance.SpringBone.Springs[].ColliderGroups[]   -> group path_ids
    VRM10SpringBoneColliderGroup.Colliders[]              -> collider path_ids
    VRM10SpringBoneCollider                               -> the collider

### Result: every character built here is clean, and the one orphan is not ours

**65 bundles: 26 clean, 1 with a fault, 38 with no colliders at all.**

The fault is **Adachi Rei — 16 colliders in 14 groups, `LowerBody` in none of them**. She is a
**downloaded bundle we did not build**, and her structure says so: 14 hand-authored groups,
mostly one collider each, named after the garment they guard (`apronL0-collider`, `HeadTip`,
`LegD_R-collider`). Ours are one group of ten. Her author made a collider for the lower body and
never put it in a group; nothing in this pipeline touched it. **It is not the Blender bug, and
it is not ours to have caused.** Leaving it is the correct answer, for the reason already
recorded about rewriting bundles we did not build.

### Two things the check had to learn before its output was worth reading

**A group that no chain references is not automatically a fault.** `VRM_BREASTRIG` gives a
character two chest chains, and chest chains are deliberately given no collider group — handing
them the torso capsule would push them out of the body they belong to. Alcina Dimitrescu has
*only* chest chains, so her one group is referenced by nothing, correctly. The first version of
this check called that a fault. A check that reports a design decision as a defect teaches the
reader to skim its output, which is worse than not running it.

**A character with colliders and no chains at all is a different statement** from one whose
colliders are all grouped, and both are printed. "Found nothing" and "examined nothing" look
identical otherwise.

### Verified by failing, twice

The pre-rebuild `Alcina Dimitrescu.yargchar` kept as a control comes back
**`4 ORPHANED: forearm.L, spine, spine.005, upper_arm.L`** — independently reproducing, from the
bundle, the same four the `.vrm` check found, and matching the documented signature of the bug
(the head/spine and the left arm). `CGC_CONTROL=1` discards every group's membership, and then a
clean character reports all ten of its colliders orphaned. A check that has never been seen to
fail has not been verified.

### A by-product worth recording: three characters with long hair had no hair chains

The sweep surfaced it because all three report "every chain here is a chest chain": **Alice Ivy,
Jessica Rabbit and Alcina Dimitrescu** each carried exactly two spring chains, both chest, and no
hair chain at all, while all three have long hair. Two of the three are fixed; the third turned
out not to be rebuildable at all.

## All three got their hair chains, and the third needed her recipe corrected first

Each build below is that character's own recorded recipe byte for byte, with **one** thing added
— the hair-rig argument in positional 10 — so anything that came out different is attributable.

| | Hair pattern | What the hair is | Result |
|---|---|---|---|
| **Alice Ivy** | `Hair` | mesh `HS_SBH_Hair_G9_Shape`, 30,717 verts, hanging to z=1.394 under a head bone at 1.533, skinned to the head | 4 × 4-joint `HairSpring`, **25,713 verts weighted**, 149 bones compared with **0 length and 0 rotation mismatches** |
| **Alcina Dimitrescu** | `Material.005` | its own 160,985-vert mesh with **no vertex groups at all** | 4 × 4-joint `HairSpring`, **125,849 verts weighted**, 80 bones compared with **0 length and 0 rotation mismatches** |
| **Jessica Rabbit** | `^hair` (already in her recipe) | mesh `Object_33`, 50,440 verts, material `hair_1` | 4 × 4-joint `HairSpring` + her 4 skirt chains, **32,227 verts weighted**, 178 bones compared with **0 rotation mismatches** — but only after her recipe was corrected, below |

All three come back from the installed-bundle sweep as `all grouped **and used**`, where before
they read `referenced by no chain`. Alcina's entry in the collider table — "her
colliders attach to nothing and reinstalling her changes nothing observable" — was that, and it
is now resolved: the colliders she was fitted with in the morning have something to push against.

**What a render can and cannot settle here.** A rest-pose render shows the rigging did not tear
or explode the mesh, and all three look intact. It says **nothing** about how the hair will
swing, because springs only act at runtime. The measurement that stands in for it is
`weight_check.py`: the new bones carry real weight on real vertices, at a maximum combined weight
of 1.000. The swing itself needs the game.

### Jessica Rabbit's recipe described a build that was never installed

Two values in her row were blend-era, and both were wrong for the character actually installed.
Finding that out took one measurement that had been available the whole time: **what her
installed bundle calls its own nodes.**

**Her source is `jessica_rabbit.glb`.** The installed bundle contains `GLTF_created_0_rootJoint`
and sixteen meshes named `Object_7` through `Object_43`. Those names exist only in the GLB; the
`.blend` in her zip calls the same meshes `Jessica`, `hair1.001`, `gloves`, `eyes`, `NurbsPath`.
A names diff against a blend-built control shows nineteen installed-only names and ten
candidate-only ones, and every one of the nineteen is a GLB name.

> This document asserted the opposite earlier on the same day, from the exclude pattern:
> `BezierCurve`, `Cube` and `Cylinder` are mesh names in the `.blend` and in no GLB, so the
> source "must" be the `.blend`. The pattern was read correctly and the inference was still
> wrong — the exclude is blend-era, like the `VRM_TEX` beside it, and describes a build that was
> never the installed one. **A recipe row records what somebody typed, not what shipped.** The
> node names settle it in one command and were never consulted.

**The exclude has to be rewritten for GLB names, and without it the build will not run at all.**
The installed bundle holds 16 of the GLB's 23 meshes. The seven it does not hold are `Icosphere`
and `Object_12`, `_13`, `_15`, `_17`, `_19`, `_21` — a stray sphere below the feet and the six
`metal` mic-stand parts, which are also exactly the unrigged ones. They are the same seven
objects the blend-era exclude drops under their `.blend` names. Left in, they inflate the scene's
Z by 3.33x before the scale step, and the build refuses to write a file:
*implausibly narrow (0.1397 m wide for 1.8000 m tall)*. With them excluded the scene measures
1.8000 m tall and 0.5172 m wide and the build completes.

**`VRM_TEX` is not just stale for her, it is actively destructive.** Her recorded
`rskin=Skin_makup_0003_Body_multires_sculpt.001_m.jpg` is an atlas built for the `.blend`'s UV
layout: a set of body islands on a BLACK background. Mapped onto the GLB's UVs, the face samples
that background, and she comes out with **half her face and the inside of her mouth painted
solid black**. The installed bundle carries the GLB's own embedded `Image_5` for her skin and
none of the zip's `Body_resculpt1*` maps, so the correct build passes **no `VRM_TEX` and an empty
texture directory** — the builder matches files out of that directory by name, and every file in
her zip belongs to the other UV layout.

### What her recipe actually is, and how close it comes

GLB + the GLB-name exclude + her own `VRM_RIG_MORE` skirt group + hairrig `^hair`, then a round
trip through `add_colliders.py`. The round trip is not optional and is not cosmetic: the
installed bundle carries colliders, which only that round trip puts there, and it normalises bone
rolls on the way through. Before it, 31 bones disagreed on rotation; after it, **zero** — the
same correction Sayuri needed on the same day, and the same signature.

Against the original installed bundle the corrected rebuild reports **178 of 178 node names
shared, 0 rotation mismatches, and 177 of 178 bone lengths equal to within half a millimetre.**
It exports to 15,706,041 bytes against the original's 15,590,635 — the difference being the
spring bones and colliders it gained.

**The one residual** is `GLTF_created_0_rootJoint`, 0.1971 m in the original against 0.1837 m in
the rebuild: a 13.4 mm difference on the root and on nothing else, which is consistent with a
different foot re-seat and is not explained further here.

**Her 1.867 m is not a height at all, it is a bounds artifact — and she is the only one.**
`height_check_installed.py` over all 65 with the documented targets loaded flags exactly one
character: hers, at +3.7%. The other 51 with a target hit it, 48 of them to within 0.5%. So
whatever this is, it is hers alone and not something the exporter does to everyone.

What it is: **her REST mesh data spans 1.8672 m while her POSED model measures 1.8000 m.** Both
numbers are measured — the build prints `VERIFIED scene height 1.8000 m` from the evaluated
scene, and the `.vrm`'s own POSITION accessors span 1.8672 from floor to crown. Her bind pose
compresses her by 3.7%, and the sweep reads the rest bounds, because that is what a bundle's
renderer bounds are. The same 1.8672 is in the `.vrm` behind the ORIGINAL installed build, so it
is not new and not something the rebuild introduced.

The inference, which is not measured here: the game skins and poses her, so she should stand
1.80 m in play and the flag is spurious. **Her row in the issue table — "Jessica Rabbit is 3.7%
too tall" — is therefore measuring the wrong thing**, and nothing about her height needs fixing.
Confirming it needs her standing next to a 1.80 m character in game.

Worth noting for the sweep itself: four other characters' rest data dips a few millimetres below
the floor (Batman −8.9 mm, Power Girl −11.5 mm, Link −7.0 mm, Gwen Stacy −6.2 mm) and the
Xenomorph's by 588 mm, which is his crouch. None of them moves a total enough to flag, and all
of them still span their target exactly.

## Nobody else can be lipsynced, and that is a measurement now rather than a subtraction

The target was every character lipsynced. **It cannot be reached, and the limit is in the models.**

`viseme_audit.py` over the installed set: **13 of 65 bind all five visemes, 52 bind none.** This
document's account of the 52 was that "35 have no mouth shape keys and never can; the rest are
characters whose source has them but whose installed build predates the viseme work" — 18
characters, arrived at by subtraction and never checked. It is wrong.

`viseme_fit.py` over all 30 surviving `.vrm` files splits them cleanly, with nothing in between:

| | |
|---|---|
| **22** | **zero shape keys.** Not "no mouth shape" — no shape keys at all. Nothing in the pipeline can give a model a mouth it has not got |
| **8** | mappable: Alastor, Alice Ivy, Chibi Rem, Doom Slayer, Gordon Freeman, Heels, Pomni, Sonic |

**Seven of those eight are already installed at 5/5.** The eighth is Sonic, and he is the whole
remainder of the problem — see below. The four extracted source archives were measured the same
way and agree: Sayuri, Alcina, Ariel and Jessica Rabbit's GLB carry **zero shape keys** each,
and all four were inside the "18 whose source has them".

**The control that makes the 22 readable.** A reading of zero from an importer is worth nothing
without proof the importer can read a non-zero. The same code path, the same Blender, the same
VRM importer reports 16 shape keys for Chibi Rem, 13 for Pomni, 10 for Heels and 5 for Sonic. So
the zeroes are the models.

### Sonic is the one gap, and closing it would mean swapping the character

His `.vrm` carries `A`, `E`, `I`, `O`, `U` on `Sonic_Event.001` — a complete vowel set — and it
already **binds all five visemes**. His installed bundle binds none. That is exactly the "build
predates the viseme work" case, and exporting that `.vrm` would fix it.

Except it is not his bundle's model. `identify_build.py` puts the two at **4.3% of names shared,
6 bones compared**, with the rotations differing on `Head`, `Hips`, `Neck` and `Spine`. They are
unrelated rigs: the installed Sonic carries Mixamo's `HeadTop_End` and is the HD one, and this
`.vrm` is the other model in the download set. Installing it would not give Sonic a mouth, it
would replace Sonic. **Left alone — that is a decision about which character to ship, not a
defect to repair.**

### `add_visemes.py`, which is the tool this needed and still deserves to exist

A character whose `.vrm` holds mouth shapes but whose bundle predates the binding work needs only
the bindings, and most such characters have no source file left — the same situation that made
`add_colliders.py` necessary. `add_visemes.py` is the same round trip for expressions: it
consumes the `VRM_VISEME=` line `viseme_fit.py` emits, so **the measuring is not duplicated** and
the mapping is visible in between where a human can disagree with it.

It refuses to write a file when the mapping names a mesh or key the file has not got — verified
by failing, with `aa=NoSuchMesh/Nope`:

    ABORT: VRM_VISEME names mesh 'NoSuchMesh', which this file has not got (it has: Sonic_Event.001)

That is the check that matters, because the add-on writes a binding to a name that does not exist
without complaining, and the result is a file that looks lipsync-capable and moves nothing —
which is the entire class of bug this area keeps producing.

## Gadget Hackwrench's installed build IS her `.vrm`, and she had two chains guarding nothing

Her row said her installed build "is not any `.vrm` here (57 rotation mismatches, a real
difference)". The number was right and the reading was wrong, in the way this project has now
been caught by three times: **0 length mismatches and 57 rotation mismatches is the
`add_colliders.py` round-trip signature**, not a different build. Sayuri's was 25 bones, Jessica
Rabbit's 31, hers 57.

Round-tripping her own `.vrm` through `add_colliders.py` with `VRM_RECOLLIDE=1` reports
**MATCH — 177 bones compared, 0 length and 0 rotation mismatches** against the installed bundle,
and takes her from **2 colliders to 10**. She had 2 of her 4 hair chains unguarded; she now has
none, and her group reads `all grouped and used`. Installed over a hash-verified backup.

### The export collided with a file that is not ours

The first export died on `IOException: Cannot create a file when that file already exists`. The
file is `Assets/Gadget Hackwrench.yargchar_metal.bytes`, one of the untracked `_metal` artefacts
this repo carries that **were not produced here and must not be committed or deleted**. The fix
is to park them and put them back, by hash both ways:

    parked   Gadget Hackwrench.yargchar_metal.bytes        6F00593DCE1C VERIFIED
    restored Gadget Hackwrench.yargchar_metal.bytes        6F00593DCE1C VERIFIED

The export writes its own `_metal_*GadgetHackwrench_*.mat` files as a side effect. They are
untracked, they are the same class, and they stay out of every commit.

## Prix's eyes were a flat lens parked in front of them, which is the third time

Reported only as "Prix's eye textures". A render of her own `.vrm` shows the symptom clearly:
**blank, featureless eyes** — no iris, no pupil, a pale shell where the eye should be.

### What it was not

**Not a missing texture.** Her file carries `eyes_lambert2SG_BaseColor`, a 1024² atlas with a
proper blue iris and veined sclera in it, and `eyes1` — the material on `L_eye`/`R_eye` — is
wired to it.

**Not the iris material's texture either, which is wrong but is not the fault.**
`aiStandardSurface4`, on `L_iris`/`R_iris`, is textured with `body 3_initialShadingGroup_BaseColor`
— her **skin** atlas, reached by the same loose filename fallback that gave her hair a different
model's map. Repointing it at the eye atlas and re-rendering changed **nothing**: the iris mesh's
UVs span u 0.502–0.978, which is the flat half of that atlas. So the texture is wrong and fixing
it buys nothing, which is worth recording because it is the obvious move and it is a dead end.

### What it was

**`L_iris`/`R_iris` are a lens shell over the eyeball, and the shell ships OPAQUE.** Hiding those
two meshes and re-rendering gives her perfect blue eyes with pupils. Her eyes were never damaged;
they were covered — and that is now the **third** occurrence of one fault:

| | the shell | how it was fixed |
|---|---|---|
| Alice Ivy | `EyeMoisture_Left/_Right`, black at the source's own alpha 0.051 | `VRM_VALUE_ALPHA=1` at build time, honouring the authored value |
| Ariel | `Cornea`, alpha max 0.051 under a 0.50 cutoff | left as it is — deliberate, recorded |
| **Prix** | `aiStandardSurface4` on `L_iris`/`R_iris`, opaque, wearing the skin atlas | `set_material_alpha.py`, below |

### She has no source, so the fix is on the built file

Prix exists on this machine only as a built `.vrm`, so there is no archive whose authored alpha
could be honoured and no rebuild available. `set_material_alpha.py` is the same round trip
`add_colliders.py` and `add_visemes.py` use, applied to one material's alpha.

**0.08 is a choice, not a measurement**, and it was settled by rendering three ways — as shipped,
at 0.08, and with the lens hidden entirely as the control. At 0.08 she is indistinguishable from
the control while the lens is kept for its highlight.

The round trip changed nothing else: triangles 105,480, 10 meshes, 9 materials, 10 images, 5
springs, 10 colliders, 138 nodes — **identical before and after** — and `identify_build.py`
against her installed bundle reports 0 length mismatches and 2 rotation mismatches, both on
collider helper NODES rather than deform bones. Installed over a hash-verified backup; she now
reports `all grouped and used` and 0 unguarded chains.

**Her hair is still not touched**, and the reason is unchanged: the only hair map in her folder is
a different model's atlas reached by the loose fallback, so honouring its alpha leaves her bald.
The two `UNUSED` rows that remain on her are that.

## The four NOALPHA materials are all benign, and the sources say so

`alpha_sweep_installed.py` flags four materials as `NOALPHA` — a cutout whose base map has no
alpha variation, so the cutout clips nothing "and may be hiding a lost opacity map". The second
half is the part worth checking, and it checks out clean:

| | | |
|---|---|---|
| Sayuri | `Clock_Diffuse_OPA`, `Scrunchie_Diffuse_OPA` | the archive's `Clock_Opacity.png` and `Scrunchie_Opacity.png` measure **254..255** — the artist shipped blank opacity maps |
| Heels | `High_Heels_Diffuse`, `Underwear_Bottoms_Diffuse` | her archive merges the names into one file, `High_Heels_Diffuse-High_Heels_Opacity.png`, and that file is **RGB with no alpha channel at all** — the opacity never existed in it |

The control is `Eyelashes_Opacity.png` from the same Sayuri folder, which measures 0..255 with
57% of it clear. So the reader sees real transparency when there is some, and the blank readings
are the files.

Nothing is lost in any of the four and nothing renders wrongly — the materials simply pay a
cutout's cost to clip zero pixels. **Not worth churning two characters for**, and recorded here so
the next sweep that flags them does not re-investigate.

## Is anybody else's eye covered? A sweep, because three accidents is a pattern

Three characters have shipped with a flat shell over perfect eyes, and each was found by
accident. `eye_shell_sweep.py` looks for the shape they have in common, which is **not** their
alpha and **not** their texture: a mesh or material whose NAME says it is a layer in front of the
eye, drawn solid.

**It has to read both the bundle and the `.vrm`, and that is the interesting part.** A bundle
renames every material to `<Character>_<n>`, so only mesh names survive — and Alice Ivy's shell
was a *material* (`EyeMoisture_Left`) inside an ordinarily-named mesh (`Custom_Eye`). The bundle
pass cannot see that shape of the fault at all. The `.vrm` keeps the authored names, and 30 of
the 65 characters still have one.

**The positive control is free**: run over the pre-fix `.vrm` files, the sweep reproduces both
known faults — Alice Ivy's two `EyeMoisture` materials OPAQUE with no base map, and Prix's
`aiStandardSurface4` OPAQUE on `L_iris`/`R_iris`. A sweep that cannot find the bugs it was
written for is worth nothing, and this one finds them.

### Nothing new turned up. Four candidates, four explanations

| | | |
|---|---|---|
| **Spider-Man PS** | `24_lens_…` OPAQUE, with `24_eye_…001` and `.002` **behind it** | the one that looks most like Prix, and is not. He is MASKED: the lens is the white eye piece of the mask and the eyes modelled beneath are meant to be hidden. Making it transparent would show human eyes through his mask |
| **Yui Suzukaze** | `…EyeIris…` OPAQUE | VRoid construction — `EyeWhite` behind, `EyeIris` on it, `EyeHighlight` on top. The iris is *supposed* to be solid; transparent, the white would show through it |
| **Ariel** | `Irises` OPAQUE | that is her eye, not a shell. Her `EyeMoisture` and `Cornea` are the deliberate `MASK` pair already recorded, and her irises render correctly |
| **Heels** | `Std_Cornea_L/R` OPAQUE | deliberate and documented: honouring their authored 0.553 over a textured base washed her iris out |

So **Prix was the last one**, and the sweep is kept because the next character acquired will be
checked by a tool rather than by somebody noticing.

## The 45 UNUSED alpha candidates are 14, and the other 30 can be ruled out on their histograms

`alpha_sweep_installed.py` flags 44 materials as `UNUSED` — an opaque material whose base texture
carries an alpha channel — and warns, correctly, that *"an alpha channel in a game rip is as
likely to be a specular mask as an opacity map; confirm with a render before changing anything"*.
That warning has kept the list untouched and uncounted for weeks.

It does not have to stay a list of 44 unknowns. **The sweep already prints the shape of each
alpha channel**, and the shape is the discriminator:

- **An opacity map is BIMODAL.** It is a stencil: pixels are in or out, so `clear + solid ≈ 1`
  and `mid ≈ 0`. Hair cards, lace, a cut-out logo.
- **A specular, gloss or ambient-occlusion map is CONTINUOUS.** Its whole job is mid-tones.

And one more, which needs no judgement at all: if honouring the alpha would erase **most of the
surface**, it was never an opacity map, because nobody ships a body that is 99.9% invisible.

| | | |
|---|---|---|
| **11** | `clear ≥ 0.88` | honouring would erase almost everything. `onefreeman` at **0.999** would delete Gordon Freeman. Ruled out |
| **15** | `mid ≥ 0.10` | continuous, so specular/gloss. The Xenomorph's headcap is **100% mid-tones**; Shadow's `body_d` 65%. Ruled out |
| **14** | bimodal, `0.05 < clear < 0.95`, `mid < 0.10` | the only shape a real opacity map takes. **These are the list** |

### The 14, and which of them can be acted on at all

Yui Suzukaze (4), Gadget Hackwrench (4 — `Jumpsuit` and `Body` ×3), Peach (2, the same texture
duplicated), Shrek (`t_Shrek_alpha_c`, whose name says it), Scott Hall (`Hall_hair_color`), Jinx,
and Steve.

**Only three of those characters still have a `.vrm`** — Gadget Hackwrench, Jinx and Peach. For
Yui Suzukaze, Shrek, Scott Hall and Steve there is no `.vrm` and no source, so even a confirmed
finding has no route to a fix: `set_material_alpha.py` and every other repair here needs a `.vrm`
to round-trip.

**Not acted on, deliberately.** Honouring one of these means switching a material to MASK or
BLEND so the map's alpha is used, and on Gadget's `Body` that would make 32% of her disappear.
Whether the result is better is a judgement about how the character should look, not a defect
with a right answer — which is exactly what the sweep's own warning says. The triage is the
deliverable: 44 unknowns reduced to 14, with reasons, and three of them reachable.

## Honouring the alpha ruins all three, and the histogram could not have told me

The triage left 14 bimodal candidates, three of them on characters that still have a `.vrm` and
are therefore fixable at all: **Gadget Hackwrench, Jinx and Peach.** All three were tried.

### First, a better number — which turned out not to help

`alpha_sweep_installed.py` measures the WHOLE texture. An atlas has unused regions and unused
regions are usually clear, so a shared atlas can read "32% clear" while every clear pixel lies
outside any UV island. `uv_alpha.py` samples the alpha at the material's **own vertex UVs**
instead, which is the set of texels the geometry can actually reach.

It did not let the candidates off. Measured under their own UVs:

| | | |
|---|---|---|
| Gadget `Body` | **34.0%** clear, 1.7% mid | *higher* than the texture-wide 31.6% |
| Gadget `Hair` | **25.0%** clear, 1.9% mid | bimodal, and 25% is exactly what hair cards look like |
| Gadget `Jumpsuit` | **64.4%** clear, 0.8% mid | |
| Jinx | **28.4%** clear, 11.8% mid | one material across eyes, teeth and body |
| Peach `_6` / `_6.002` | **73.1%** / **82.7%** clear | crown and a hands mesh |

Gadget's `Hair` was the best candidate anyone could ask for: a hair material, bimodal, 25%
clear, under 2% mid-tones. Every number said opacity map.

### Then the renders, which settle it

**Gadget's hair comes out full of holes.** Honouring `Body` and `Jumpsuit` as well shreds her —
chunks missing from her face, torso and legs. **Jinx is destroyed**: her face disappears and her
body is cut to ribbons. **Peach changes by literally zero pixels** — 0 of 700,000 above a
threshold of 8, because the two materials sit on stacked Smash-rip expression meshes that are not
visible from the front anyway.

So: **two catastrophic, one no-op, none installed.**

### The result worth keeping is the negative one

`alpha_sweep_installed.py` has always carried this warning:

> *An alpha channel in a game rip is as likely to be a specular mask as an opacity map; confirm
> with a render before changing anything.*

That was advice. It is now **measured**: the best statistical case available — bimodal, 25%
clear, under 2% mid, on a material literally called `Hair` — was wrong. **The histogram cannot
distinguish an opacity map from a specular mask, and no refinement of it will.** The triage in
the previous section narrows what is worth rendering; it does not decide anything, and the
remaining 11 candidates on characters with no `.vrm` can be left alone without regret, because
there is no reason to think any of them is different.

Both tools are kept — `uv_alpha.py` for the narrowing and `honour_alpha.py` for the five-minute
test — so the next candidate is settled by a render rather than by an argument.

## "No surviving source" was never checked against the Downloads folder

Three characters were recorded as beyond repair — *"Aiko, Scott Hall, Shadow the Hedgehog, 11
unguarded chains between them. Nothing can re-fit them without re-acquiring the source"* — and
several others carry the same assumption in passing. It is true that only 30 of the 65 have a
`.vrm` here. It does not follow that the rest have no source.

**28 of the 36 characters with no `.vrm` have a plausible source archive sitting in Downloads.**
Scott Hall's is `scott-hall.zip`, and he was *already extracted* at `C:\dev\_tmp\scott-hall-2`.
Shadow's is `shadow-the-hedgehog-sonic-forcesgmod.zip`. Only 8 have nothing — Aiko, Adachi Rei,
Harq Alkahana, Inforder Trogen, Kaiser Aufhänger, Mickey Mouse, Spartan Mark V, Yui Suzukaze —
and five of those are the downloaded bundles that were never built here at all.

The matching is by name tokens and every row is a **candidate**: `Skeleton Mage` matches
`terminator-t-800-endo-skeleton-damaged.zip` on the word "skeleton" and is certainly wrong. The
point is not the list, it is that **nobody had looked**, and two of the three characters declared
unrecoverable had their archives on the same disk the whole time.

This is the fourth time in two days: Ariel's "no source archive", Jessica Rabbit's "built from
the GLB" then "built from the blend", Gadget Hackwrench's "not any `.vrm` here". **A note saying
something is unavailable is a note, not a measurement.**

## Scott Hall: colliders at last, and a texture downgrade caught on the way

His recipe was recorded in full and his archive was extracted. Two things were in the way, and
neither was the one the docs named:

**The outer zip's `textures/` folder is missing the right elbow pad maps.** That is the omission
his recorded `VRM_TEX` exists to work around — and the build aborts on it, because `VRM_TEX`
names a file that is not there. The **nested** `scott_hall_2k20__rigged__by_dexpac_df16783.zip`
inside `source/` carries a complete `PNGs/` folder, all 40 maps. Build from that.

**The recipe records no TEXMAX, and 1024 is wrong for him.** Built at 1024 he came out
22,451,264 bytes against the installed 35,377,899 — a **36% smaller bundle**, because his
installed build keeps **seven textures at 2048²** and 1024 quietly halved them. The bundle is the
measurement: built at 2048 he exports to 35,405,370 bytes, **27 KB from the original**, which is
the collider data he gained.

That downgrade would have shipped silently. Nothing in the recipe, the build log or any sweep
would have said a word about it — `height_check`, `collider_group_check` and `identify_build` all
pass either way. **Read the installed bundle's texture sizes before choosing a TEXMAX.**

With that: rig **identical** — 79 bones compared, 0 length and 0 rotation mismatches. The only
name differences are the hair bones' naming convention (`HairSpring_0_0` then,
`HairSpring_0_0_0` now, same sixteen bones) and the Unity-side wrappers. He gains **10 colliders
in one group attached to all 4 of his chains**, so his 4 unguarded chains are 0.

## Shadow the Hedgehog: three unguarded chains and no fingers, both from one rebuild

His recipe was two values — `sonicforces`, 1.05 — and his archive is
`shadow-the-hedgehog-sonic-forcesgmod.zip`. Rebuilt from it:

| | before | after |
|---|---|---|
| colliders | **0** | 10 in one group, attached to **3 of 3** chains |
| unguarded chains | **3** (Tail, Wing_L, Wing_R) | **0** |
| humanoid bones | **21** | **39** |
| finger bones | **0** — flagged `NO FINGERS MAPPED` | **18** |

The rig is otherwise untouched: **169 bones compared, 0 length and 0 rotation mismatches**, the
same three chains by the same names. 2,076,841 bytes before, 2,079,923 after — the 3 KB is the
collider data. His textures top out at 512², so a 1024 TEXMAX downgrades nothing; that was checked
first, after Scott Hall.

The finger half is the more interesting one. `build_vrm.py` now **fills missing finger chains
with weightless bones fused to a real one, because YARG's microphone code dereferences them and a
null makes the character INVISIBLE**. His installed build predates that, and the rebuild logs it
filling six chains. Whether it was ever actually at risk in game is not known — he has been
installed and nobody has reported him missing — but the mapping is right now and it was not.

### Set-wide, after Scott Hall and Shadow

**51 unguarded chains across 6 characters → 42 across 3.** The three left are the three that
cannot be reached: **Aiko** (4 chains, and a search of Downloads and `C:\dev` finds nothing of
hers), **Kaiser Aufhänger** (36 — a downloaded bundle whose own author covered his arms and torso
and not his legs) and **Adachi Rei** (2 orphaned colliders, also downloaded). Fixing any of them
means synthesising collider objects inside somebody else's bundle, which is a different kind of
operation from anything here.

### Five more characters have a finger-mapping defect, and four have a source

`bundle_audit.py` across the 65: **B1 Battle Droid** (humanoid 18, fingers 0), **Mannequin** (15,
0), **Steve** (15, 0), **Sonic** (28, 6 — index only) and **Yui Suzukaze** (28, 6). All but Yui
have an archive in Downloads and a recorded recipe.

Two of them are probably correct as they are: **Steve is Minecraft Steve**, whose hands are
blocks, and the Mannequin is a featureless artist's dummy. Mapping fingers onto a hand that has
none is not a fix. The other three are worth a rebuild and have not had one.

## Open questions

Not answered by the code, and worth measuring before authoring anything expensive:

- ~~**Where does Jessica Rabbit's 3.7% gain its height?**~~ **Answered 2026-11-12, and the
  answer is that there is no height to explain.** Her REST mesh data spans 1.8672 m while her
  POSED model measures 1.8000 m; the sweep reads rest bounds, so it reads 1.8672. She is the
  only one of the 52 with a documented target that misses it. What is left open is one line of
  confirmation in game — standing her beside a 1.80 m character — and, if that confirms it,
  deleting the "3.7% too tall" row rather than trying to fix it.
- **Scale and height — the build side is now measured, the PODIUM side is not.** Nothing
  normalises the model, and as of 2026-11-12 every installed character has been measured out of
  its own bundle: 51 of the 52 with a documented target hit it to within 0.8%, none carries a
  detached mesh setting its height, and the set runs from Yoda at 0.66 m to Alcina at 2.90 m.
  What is still unmeasured is what the podium and the character-select camera tolerate. Two
  characters are known to sit outside it — Alcina's head is above the select camera at 2.9 m, and
  **Baby Groot measures 0.348 m**, a quarter the height of anything else and the shortest figure
  in the set by a factor of two. Neither has a documented target, so neither is a build defect;
  both are a framing question nobody has answered. Measure the base mesh — see *Measure the base
  mesh, not the scene* above.
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
- **Whether a bundled AnimatorController is ever used, and what is really wrong with Teto.**
  Both need the game rebuilt and run with logging around `LoadAnimationDefaults`; the reading of
  the source is written up above and filed upstream as YARC-Official/YARG#1769, and neither is
  settled without that run. This is the one thing on this list that blocks other work.
- ~~**Prix's eye textures**~~ **Answered and fixed 2026-11-12:** a lens shell shipped opaque over perfect eyes, the third occurrence of that fault. Her hair is unchanged and must stay that way — the only hair map in her folder is a different model's atlas reached by the loose fallback, so honouring its alpha leaves her bald. The fault is the texture's provenance, not its channel.
- **Alcina's colour maps.** Every base-colour map in her archive is a grey noise field, so she
  renders as a white statue; her appearance lives in her `.blend`'s material nodes, which no glTF
  export carries. Recovering it means baking those to textures, which nothing here does. Her head
  is also above the character-select camera at 2.9 m, and her height is canon.
- **Collider groups are verified across the whole installed set, not assumed.** 2026-11-12: a
  stale Blender reference meant four colliders per character resolved to nothing in Alcina, Pomni
  and the Xenomorph, while the build log reported all ten. All three are rebuilt, and both ends
  are now swept — `collider_group_check.py` over every `.vrm`, and
  `collider_group_check_installed.py` over all 65 `.yargchar`. **Every character built here is
  clean.** The single orphan in the set is in Adachi Rei, a downloaded bundle. See *The other 35
  characters had never been checked* below.
- ~~**Three characters with zero colliders and no surviving `.vrm`**~~ — **two of the three are fixed.** Scott Hall and Shadow the Hedgehog both had their source archives in Downloads the whole time; rebuilt, they report 0 unguarded chains and rigs identical to their installed builds. **Aiko** is the one that was genuinely unrecoverable, and that is now a measurement — nothing of hers is in Downloads or under `C:\dev`.
- **Kaiser Aufhänger has colliders on his arms and torso and none on his legs**, which leaves
  **36 unguarded chains — 70% of every unguarded chain remaining in the set**, in one character.
  He is a downloaded MToon bundle with no source, so this is the same wall as the three above, but
  it is worth separating because the arithmetic is so lopsided: the other five affected characters
  share 15 chains between them. Also worth a look before anyone acts: 30 of his 36 are named
  `TopsUpperArm` while hugging his legs, which is either a naming quirk in the original or a sign
  that his chains are not what their names say.
- ~~**Gadget Hackwrench's installed build is not any `.vrm` here**~~ **Answered 2026-11-12: it IS her `.vrm`.** 0 length mismatches and 57 rotation mismatches is the `add_colliders.py` round-trip signature, not a different build — Sayuri's was 25 bones and Jessica Rabbit's 31. Round-tripped, it reports MATCH, and the re-fit took her from 2 colliders to 10 and her 2 unguarded chains to 0. Installed.
# The sign-flip cloth test: what it measures, and the finding that reframes the question

Date: 2026-11-22. Instrument: `YargClothInside.cs`. Subject: Power Girl, installed bundle
(`...\FatalException\YARG-FE\release\custom\characters\Power Girl.yargchar`), one frame, the pose
the Animator produces after `anim.Update(1.0)`.

Nothing was committed to any character, bundle or project asset. No renders were taken.

## What was built, and why it is not the previous instrument

`YargClothPenetration.cs` asked the question in screen space and failed its own controls: the
proximity term that correctly excluded a cape hanging behind a chest also excluded a limb that had
fully broken through, so the reading went blind exactly as severity rose. The replacement asks a
geometric question that is monotone in severity by construction:

    for each cloth vertex:  nearest point on the body surface
                            sign of (vertex - nearest) . N      N = area-weighted pseudonormal

No camera, no depth shader, no render pipeline, no painted colours. The denominator is all cloth
vertices, measured independently of the numerator — the specific thing the previous version got
wrong.

## THE CENTRAL CLAIM OF THE DESIGN HOLDS

Displacing both upper arms outward, re-applied after every `anim.Update`, on the per-triangle
weight split that every instrument in this project has used:

| armPush | INSIDE | >2mm | >5mm | >10mm | >20mm | >40mm | LeftUpperArm | RightUpperArm |
|---|---|---|---|---|---|---|---|---|
| 0.000 | 6638 | 6367 | 5810 | 4931 | 3381 | 2112 | 259 | 323 |
| 0.005 | 6645 | 6374 | 5817 | 4938 | 3388 | 2119 | 264 | 324 |
| 0.010 | 6648 | 6377 | 5820 | 4941 | 3394 | 2127 | 272 | 326 |
| 0.020 | 6664 | 6393 | 5836 | 4958 | 3411 | 2148 | 285 | 329 |
| 0.040 | 6681 | 6410 | 5853 | 4975 | 3428 | 2180 | 313 | 335 |

35 readings, strictly increasing, no reversal in any column — and the rise **localises to the bone
that moved**: LeftUpperArm +21% against +0.6% globally. That is what the proximity version could
not do, where five magnitudes gave 397, 395, 396, 397, 398.

So the sign-flip framing responds to severity and says where. That result is independent of
everything below.

## CONTROL A FAILED, AND THE FAILURE WAS THE USEFUL PART

The precondition for a pseudonormal sign is a closed surface. Measured, before any count was
printed:

    WEIGHT split   closedness 0.887   parts 231   closed 0   (0 of 23,449 tris, 0.000%)

Not one closed piece. A per-triangle weight test cuts the skin along every weight boundary, so the
body half is skin shredded into 231 patches with 4,209 boundary edges, and a patch has no interior.
The tell that this was an artefact rather than a finding: the deepest "penetration" was **220.44 mm,
on an upper arm about 90 mm thick, and it was 220.44 mm at every one of the five magnitudes**. Plus
435 cloth vertices whose nearest body triangle had a degenerate normal.

Applying the same humanoid map at piece granularity instead — label each connected piece by its
weight majority and keep it intact — fixed exactly what it was predicted to fix:

| | closedness | parts | deepest | zero-normals | median depth |
|---|---|---|---|---|---|
| WEIGHT (per triangle) | 0.887 | 231 | 220.44 mm | 435 | 20.9 mm |
| COMPONENT (per piece) | 0.960 | 105 | **63.99 mm** | **1** | 5.9 mm |

Part 0 of the component split is a 23,572-triangle shell with **4** boundary edges out of 59,341.

## BUT THE SPLIT THAT HAS A VALID ZERO POINT HAS NO RESPONSE

| armPush | WEIGHT INSIDE / >10mm / >40mm | COMPONENT INSIDE / >10mm / >40mm |
|---|---|---|
| 0.000 | 6381 / 4725 / 2049 | 4601 / 1693 / 111 |
| 0.005 | 6389 / 4733 / 2057 | 4601 / 1693 / 111 |
| 0.010 | 6391 / 4735 / 2063 | 4602 / 1693 / 111 |
| 0.020 | 6403 / 4748 / 2080 | 4604 / 1693 / 111 |
| 0.040 | 6415 / 4760 / 2105 | 4614 / 1693 / 111 |

Every band above 10 mm is **dead flat** across 40 mm of arm displacement. So one split has a
response and no valid zero point; the other has a valid zero point and no response. Neither is yet
an instrument.

## THE FINDING: ON THIS CHARACTER, SKIN AND COSTUME ARE NOT SEPARABLE GEOMETRY

I predicted the cause and was wrong, which is how the real one surfaced. My prediction was that a
fitted garment is skinned to the same humanoid bones as the skin beneath it, so its piece would come
back with a humanoid share near 1.0 and be mislabelled body. Measured instead:

    piece 0  tris=23572  humanoid_share=0.568  -> BODY   weight-split-would-call-body=12584
    piece 1  tris=12504  humanoid_share=0.542  -> BODY   weight-split-would-call-body= 6294
    piece 2  tris= 5513  humanoid_share=0.302  -> cloth  weight-split-would-call-body= 1529
    piece 3  tris= 2237  humanoid_share=0.000  -> cloth  weight-split-would-call-body=    0
    piece 4  tris= 2202  humanoid_share=0.000  -> cloth  weight-split-would-call-body=    0
    piece 5  tris=  602  humanoid_share=0.000  -> cloth
    piece 6  tris=  528  humanoid_share=0.000  -> cloth
    piece 7  tris=  528  humanoid_share=0.000  -> cloth
    piece 8  tris=  138  humanoid_share=0.614  -> BODY
    piece 9  tris=  138  humanoid_share=0.604  -> BODY

Not 1.0 — **0.568 and 0.542**. The two largest pieces, 36,076 triangles between them, are each
about **half skin-weighted and half garment-weighted, fused into one connected shell**. The skin
and the costume share edges: they are one manifold surface, welded at the garment boundary. 161 of
451 pieces have a mixed share between 0.2 and 0.8.

That reframes everything above:

* **The weight split was not shredding the body out of clumsiness.** Cutting along the weight
  boundary is the only thing a per-triangle test *can* do when that boundary runs through the
  interior of a single surface. The 231 patches are a faithful report of fused geometry.
* **"Is the cloth inside the body" presupposes two surfaces.** For most of this character there is
  one. The question is not hard here; it is ill-posed, and ill-posed because of how the character
  is authored rather than because of the instrument or the split.
* **The flat response may be a TRUE NEGATIVE.** If her sleeve is the same shell as her deltoid,
  displacing the upper arm cannot push anything through anything, because there is no separate
  garment over it. The pieces that *are* genuinely separate (share 0.000) are cape, hair and boots —
  and her cape is parented under her clavicles, which this project already measured, so it follows
  the shoulder rather than being left behind.

The last point is the one that matters and the one I cannot currently settle: **a flat positive
control is indistinguishable from a character with nothing to find**, which is the signature that
says a control is required. The control that would separate them is a displacement of a bone that
genuinely sits under a *separable* garment piece. On Power Girl the separable pieces are the ones
with humanoid_share 0.000, and the upper arm is not under any of them.

## WHAT THIS SAYS ABOUT EVERY OTHER INSTRUMENT HERE

The per-triangle humanoid-weight split is used by `YargCharParts.cs`, `YargClothPenetration.cs` and
the interior-fault sweep. It is not measuring "body versus cloth". It is measuring **what drives a
triangle**, and on fused skin-and-costume geometry that boundary runs through the middle of a single
surface. Those instruments' body/cloth triangle counts are still correct as counts of
*dominant-weight classes*; what cannot be read off them is that the two halves are two surfaces.

## STATE

* `YargClothInside.cs` compiles clean, runs on the installed bundle, 5/5 runs clean, writes
  `inside.json`.
* Controls: A fails on WEIGHT and nearly passes on COMPONENT (0.960, one 4-edge shell); B passes
  (median nearest 8.5 mm, 1,166 of 15,030 beyond cutoff); D passes strongly on WEIGHT and is flat
  on COMPONENT; E is uninformative here, see below.
* **Batman was NOT run.** The positive control does not pass on the split that has a valid zero
  point, so a number from his shoulder could not have been graded.

## Two notes on controls, from being wrong about my own

**Symmetry tests the measurement, not the premise.** Control E passed 8/8 on the WEIGHT split while
that split was ill-posed, because a shredding artefact on a symmetric body is itself symmetric. It
catches errors with a handedness; an error in the framing is shared by both sides and sails
through. (On the COMPONENT split it dropped to 1/1 pair and says even less.)

**Threshold-free is not the same as right.** I defined "closed" as zero boundary edges and defended
it in the file as exact, definitional, no judgement — then it threw out a 23,572-triangle body shell
over 4 boundary edges in 59,341 and reported on 491 of 15,030 vertices while announcing itself as
the trustworthy subset. An exact definition can be exactly the wrong one. Counts are now attributed
per piece with each piece's boundary count printed beside them.

**And one bug that never ran, worth recording because of its shape.** The first draft had
`Grid.Nearest` return the distance and the normal but not the nearest *point*, so the offset was
computed against the vertex itself and was identically zero — which prints `INSIDE=0` for every
character, a perfect clean sweep from a dead instrument. Caught by re-reading the inner loop. It
would also have been caught by control D, which must *rise*: a dead offset is flat at zero, and
flat is a failure. The control set covered the thing its author was afraid of, from a different
direction.

---

# Part two: two more attempts at a positive control, both defeated by hair

Continued the same evening. The instrument's geometry held up throughout; what follows is entirely
about failing to find a character on which its positive control can be run.

## Power Girl cannot host the control

Piece identity, measured rather than assumed, on the installed bundle:

    piece 3  tris=2237  share=0.000  y=1.558..1.598  nearest=Head@82mm
    piece 4  tris=2202  share=0.000  y=1.565..1.620  nearest=Head@74mm
    piece 5  tris= 602  share=0.000  y=1.569..1.604  nearest=Head@66mm
    piece 6  tris= 528  share=0.000  y=1.636..1.676  nearest=Head@111mm
    piece 7  tris= 528  share=0.000  y=1.634..1.673  nearest=Head@112mm

**Every separable piece she has is hair.** No boots, no gloves; her costume is fused into pieces 0
and 1. The proposed lower-leg control would have been run against hair and returned a flat
indistinguishable from the flat already in hand. Confirming identity first is what stopped that.

**MATERIAL NAMES CANNOT IDENTIFY A PIECE IN A BUNDLE.** The exporter renames every material to
`<Character>_N`, and pieces 3, 4, 5, 6 and 7 all come back as `mesh1 / PowerGirl_3` — one name over
five separate shells. Identity had to come from geometry.

Also measured, and unexpected: **the idle moves almost nothing but the left hand.** Over six frames
the ten largest bone travels are all left-hand finger bones at 270–296 mm. No limb in the top ten.
It is a guitar hand, which is obvious in retrospect for a rhythm game and was not in any of my
reasoning about which bone a control should move.

## The roster survey, 65 of 65 characters, one editor session

    characters with NO separable garment piece at all        27 of 65
    characters with a separable piece over a limb bone        20 of 65   <-- WRONG, see below
    characters with a separable piece over a hand             7 of 65

**27 of 65 characters have no separable garment piece at all.** On those, "is the cloth inside the
body" is ill-posed in principle, exactly as on Power Girl. That number is the most durable thing on
this page and it does not depend on the broken column beside it.

## THE RANKING IS WITHDRAWN. IT RANKED HAIR.

The survey ranked Jinx first: 197 separable pieces, 168,475 separable triangles, bones listed as
LeftFoot, LeftLowerLeg, LeftUpperLeg, RightFoot. A lateral lower-leg sweep on her went flat — 4,833
inside vertices at 0 mm **and 4,833 at 220 mm**, with the response saturating (median nearest
42.24 → 40.57 → 40.19 → 40.15 → 40.11 → 40.07 mm). A 220 mm shin displacement putting a shin
entirely outside a trouser cannot leave the count unchanged, so that was a bug signature, not a
null.

It was not loose clothing, which is what I said first. Her pieces:

    piece 0  tris=12779  share=0.000  y=0.172..1.527  nearest=LeftUpperLeg@200mm  mats=hair_base / Jinx_0
    piece 1  tris=12696  share=0.000  y=0.171..1.552  nearest=LeftUpperLeg@203mm  mats=hair_base / Jinx_0
    piece 2  tris=12649  share=0.000  y=0.177..1.533  nearest=LeftUpperLeg@213mm  mats=hair_base / Jinx_0
    ... six such pieces, 73,835 triangles in all

**Her braids.** They run from her head to her ankles, so each one's centroid lands nearest
`LeftUpperLeg`, and `bodyTris=30297` against `clothTris=175496` means only 15% of her was labelled
body — her legs are not in the body surface at all. Displacing them moved a great deal of *cloth*
and created no crossing, which is why distances changed while the inside set did not.

So **`over_non_head` counted any hair that hangs below the head as garment-over-limb**, and it did
so for all 65 characters. The candidate list it produced must not be used.

## What this costs, and the one pattern behind all three

Three attempts at piece identity, three failures, each a plausible instrument answering a slightly
different question:

1. **Material name** — the bundle exporter had already destroyed it.
2. **Nearest humanoid bone to the piece centroid** — a braid hanging past the knee is "over the
   leg" by that measure. Hair and a legging are indistinguishable to it.
3. **Separable-piece count and triangle totals** — size says nothing about what a piece is, and
   Jinx's hair outweighs most characters' entire wardrobes.

A discriminator that would work, offered as a direction and not a claim: a garment **wraps** its
limb and hair **hangs beside** it, so the test is angular coverage around the nearest bone's axis —
near 360° for a sleeve or a legging, a narrow sector for a braid. `cloth_collide.py` already has the
point-to-segment machinery. Not built, not measured.

## STATE AT THE END OF PART TWO

* The instrument is sound where it can be pointed: closedness 0.981 on Jinx and 0.960 on Power
  Girl, physically plausible depths, no crash, 11 of 11 Unity runs clean.
* **It still has no passing positive control on any character**, because no character has yet been
  shown to carry a separable garment over a limb. Two candidates were examined and both were hair.
* **The `over_non_head` ranking is withdrawn.** The three survey counts that survive are 27 of 65
  with no separable piece, 65 of 65 coverage, and the per-character piece inventories themselves.
* Batman was not run, and should not be until a positive control passes somewhere.

---

# Part three: the guard, and the condition a displacement control actually requires

The angular garment-versus-hair discriminator was **declined** rather than built: every piece
confirmed so far is hair, so it could have been shown to reject hair and never shown to accept a
sleeve, which is the standing of the three heuristics it would have replaced. What replaced it
needs no identity at all.

## The guard caught its own ordering bug on its first run

Built as: bake the character twice, before and after the displacement, and assert the forcing
landed. Its first run refused **both** cases, including the one built to pass, reporting
`pushed_travel=0.000mm` everywhere — because the reference bake sat *after* the push was applied,
so both bakes were post-push and identical. A guard tested only against the case it should refuse
would have looked perfect. Reordered, it reads `pushed_travel=40.000mm (asked 40.000mm)` on both
characters.

## It then refused neither — and that is the result

| | pushed_verts | travel | pushed_on_body | static_near_push | moving_near_push | cloth_over_push | inside_over_push |
|---|---|---|---|---|---|---|---|
| Jinx, lower legs | 25,651 | 40.000 mm | 8,164 | 160 | 84 | 10,838 | 237 |
| Power Girl, upper arms (WEIGHT) | 5,217 | 40.000 mm | 3,092 | 10,907 | 159 | 2,234 | 746 |
| Power Girl, upper arms (COMPONENT) | 5,217 | 40.000 mm | 5,217 | 10,907 | 159 | 104 | 0 |

**Two corrections to earlier parts of this document, both forced by these numbers.**

1. I wrote that Jinx's legs were **not in the body surface at all**, inferring it from
   `bodyTris=30297` against `clothTris=175496`. Wrong: 8,164 of her lower-leg vertices are on the
   component body surface and all of them moved the full 40 mm.
2. I then wrote that the condition was **nothing to cross**. Also wrong:
   `cloth_over_push=10,838` on Jinx. There is a great deal of cloth over her legs.

## The condition is cloth that STAYS while the body moves

Jinx's 10,838 cloth vertices over her legs are **skinned to those legs**, so they travel with the
push and nothing ever changes side: `static_near_push=160` against `moving_near_push=84` is all the
crossable population she has there, out of 89,743 cloth vertices. A rigidly-skinned garment cannot
be penetrated by displacing the bone that drives it, at any magnitude. That is why 0 mm and 220 mm
both read 4,833.

Power Girl is the opposite shape and still cannot host it. She has **10,907 static vertices near
her upper arm** — her cape, which is spring-driven and does not follow the arm — and only **104**
whose *nearest body triangle* is the arm. The cape hangs **beside** the arm, resting against her
torso. A radial outward push moves the deltoid *away* from where the cape actually is, so no
magnitude and no character property would make that control fire; the push direction is wrong for
the geometry, and the two counts together are what say so.

So a bone can host this control only where there is cloth that

* is **not driven** by that bone (it stays put — `static_near_push`), **and**
* **rests against** that bone (`cloth_over_push`, nearest-body attribution, not proximity).

Both are now measured, neither needs to know what a piece is, and hair is excluded for free: a
braid hanging beside a leg has its nearest body triangle wherever it actually rests.

## What that makes the next measurement

Not a choice between characters, which is what I have been guessing at all evening. A census, per
character and **per bone**, of static cloth whose nearest body triangle that bone drives —
maximised over bones. That picks the control subject from the data rather than from my suspicion
about boots, and it is the same two numbers above computed for every bone instead of one.
Not built.

## STATE

* `YargClothInside.cs`: compiles clean, 15 of 15 Unity runs clean. Carries the two splits, the
  piece inventory, piece location by driving bone, `-pushBones` / `-pushAxis`, `-inventory`, and
  the five-number guard.
* **Still no passing positive control, and now a measured reason rather than a suspicion.** The two
  subjects fail for opposite reasons: Jinx's leg cloth moves with the leg, Power Girl's arm-adjacent
  cloth rests on her torso rather than her arm.
* Batman not run.
* The `over_non_head` ranking remains withdrawn. The inventory now prints raw driving-bone names
  with no category derived from them, because three derived categories in one evening were wrong.

---

# Part four: the census, and the first passing positive control

## The census

Per character and per bone: cloth vertices that **rest on** bone B (nearest body triangle is driven
by B or its subtree) and are **not driven by** B. Both terms from skin weights, no push needed, so
every bone is scored in one pass over the cloth as a bit operation. 65 characters, one editor
session.

Hair is **not** excluded. It was earlier disqualified for being mislabelled a *garment*, which is a
different question from what the control needs: non-body geometry that stays while the body moves.
Hair is ideal for that, never being driven by a limb bone.

    65 characters, 38 produced a control line
    30  at least one hostable bone
     8  NO HOSTABLE BONE -- every cloth vertex hangs from the bone it rests on
    27  UNMEASURED, no separable cloth at all (the same 27 as part two)

Winning bone by character count: **RightShoulder 6, LeftShoulder 4, RightUpperLeg 4, LeftUpperLeg 3,
LeftUpperArm 3, Head 2, Neck 2.** Shoulders are the most common host, which confirms the prediction
made before the run: the two conditions are anti-correlated by how clothes are made, so they hold
together mainly where geometry hangs from one branch of the rig and rests against another — hair and
scarves on shoulders, driven from head and neck.

The 8 "NO HOSTABLE BONE" characters are the anti-correlation holding absolutely, and they are a
statement about authoring rather than a failed search.

## The control direction has to be derived too

The top nominee by count was Jinx / LeftUpperLeg, 14,607 hostable — the same character as part two
but a **different bone** and a direction of `0.028,-0.869,-0.494`, mostly **downward**. The lateral
X push I chose myself was simply wrong. Power Girl's arm control failed on direction for the same
reason: her cape rests on her torso beside the arm, so a radial outward push moved the deltoid away
from it.

## K-2SO / LeftUpperArm: it fires

Nominated on 711 hostable vertices at a 12.5 mm centroid gap, pushed along its own derived
`-0.191,-0.981,0.044`. RightUpperArm (669 hostable, 12.6 mm) left **unpushed** as an internal
reference.

| push | guard travel | pushed_on_body | static_near_push | inside_over_push | cloth_over_push | fraction | RightUpperArm |
|---|---|---|---|---|---|---|---|
| 0 | — | — | — | — | — | — | 21 |
| 5 mm | 5.000 / 5.000 | 3,856 | 2,444 | 45 | 901 | 5.0% | 21 |
| 10 mm | 10.000 / 10.000 | 3,859 | 2,447 | 43 | 896 | 4.8% | 21 |
| 20 mm | 20.000 / 20.000 | 3,855 | 2,445 | 60 | 874 | 6.9% | 21 |
| 40 mm | 40.000 / 40.000 | 3,852 | 2,451 | 82 | 790 | **10.4%** | 21 |

Three independent reasons this is a pass and not a trend:

1. **The unpushed arm is constant at 21 across all five runs.** Exact localisation, measured on
   geometry the control never touched.
2. **The onset matches a separate measurement.** The census put the gap at 12.5 mm. Nothing happens
   at 5 or 10 mm; the rise begins between 10 and 20 mm and climbs from there. A response that starts
   where an independently measured gap says it must is a prediction confirmed.
3. **The fraction rises faster than the count**, because the denominator shrinks as the arm moves
   away — 901 → 790 while the numerator nearly doubles.

**READ `inside_over_push`, NOT THE TOTAL, AND NOT THE REGION ROW.** The total moves 228 → 265 with a
dip, and the LeftUpperArm *region* count **falls** 32 → 33 → 32 → 27 → 19. That is an attribution
artefact and not a loss of signal: region is assigned by the nearest body triangle, so as the arm
descends, vertices that were nearest the arm become nearest the shoulder and leave the bucket while
remaining inside. The bone-scoped count uses the ancestry bitmask and is stable under that motion.
Anyone reading the region row alone would conclude the control had failed.

## STATE

* **The instrument has a passing positive control**, on K-2SO / LeftUpperArm, with the subject and
  the direction both chosen by the census rather than by guesswork, the forcing asserted by the
  guard, and an unpushed internal reference flat across the sweep.
* 20 of 20 Unity runs clean.
* Batman is **no longer blocked** by the control. The next step is him on both bundles
  (`a9b26646` installed against `f7d268e0` backup), read on `inside_over_push` for the shoulder
  bones, plus the original probe on the same frames — with the clavicle capsules measured at
  51-56 mm proud, the two should disagree, and the size of that disagreement is a result about
  every cape number this project has published.

---

# Part five: the baseline closes, and measurement A is VOID

## The baseline: a measured zero response, not noise

`-pushBones` now builds its bone set independently of the push MAGNITUDE, so the 0 mm row reports
`inside_over_push` like every other row. K-2SO / LeftUpperArm:

    rest   5mm   10mm   20mm   40mm
     45     45     43     60     82

At rest it is **45**, and 5 mm is **also 45**. So the flat start is not noise — it is a measured
**zero response below the gap**, and the census put that gap at 12.5 mm. The response begins between
10 and 20 mm, exactly where an independent measurement says it must. (10 mm reads 43, two *below*
rest; a small negative excursion, not perfect flatness, and worth stating as such.)

This cost no extra run. The number was already being computed and had no way to be printed.

## Measurement A is VOID on both bundles

Two bundles, one instrument, no forcing, one pose, both verified by MD5 rather than filename:
`a9b26646` installed (clavicle yoke) against `f7d268e0` (grav70-5chains-spinecape).

    a9b26646  bodyTris=3486  clothTris=15332  INSIDE=208  medDepth=122.1mm  deepest=249.9mm
              beyond-cutoff=7478/8677   cloth_over_push=2  inside_over_push=1
    f7d268e0  bodyTris=3486  clothTris=15332  INSIDE=239  medDepth=132.4mm  deepest=249.7mm
              beyond-cutoff=7462/8676   cloth_over_push=0  inside_over_push=0

**DO NOT READ 208 AGAINST 239.** It looks like the clavicle build winning by 31 and it is two
readings taken against a body surface that is Batman's head.

    piece 0  tris=6438  share=0.355  -> cloth   y=0.327..1.601  nearest=Hips@19mm     <- his TORSO AND LEGS
    piece 2  tris=2045  share=0.515  -> BODY    y=1.478..1.878  nearest=Head@77mm     <- his COWL

His torso and legs, the largest piece in the model, are labelled **cloth** at a humanoid share of
0.355, because his rig drives the suit from non-humanoid helper bones. The only body-labelled piece
of any size is his cowl. So the body surface is 3,486 triangles of head, 86% of cloth vertices have
no body within the 250 mm cutoff, and the 122-250 mm "depths" are distances to his head.

**The controls caught this before I read the numbers.** `beyond-cutoff=7478/8677`, `deepest` within
0.1 mm of the cutoff, and the cutoff warning fired twice — once per split. That is control B and the
cutoff guard doing exactly what they were written for.

## Three characters, three different failures of one rule

The component split's "humanoid share > 0.5 per piece" is now wrong on every character it has been
pointed at, and not in a consistent direction:

| character | share of the big piece | effect |
|---|---|---|
| Power Girl | 0.568 | **over**-labels: skin and costume are one fused shell, so the sleeve is swallowed into the body |
| Jinx | — | **under**-labels: only 15% of her is body |
| Batman | 0.355 | **under**-labels catastrophically: only the cowl is body |

A majority vote on bone weights cannot identify a body, because weights describe what DRIVES
geometry and a rig is free to drive a torso from helper bones. Three directions of error rule out
tuning the 0.5.

**The direction that suggests itself, not built:** the body is the piece that **encloses the
skeleton**. For each piece, count how many humanoid bone POSITIONS lie inside it — using the
inside/outside test this file already implements, pointed at itself. A cowl contains one bone; a
torso shell contains a dozen; a cape contains none. That is geometric, needs no weights, and has no
threshold to pick.

## Measurement B is blocked by the same defect

Capsules against the mesh surface, one pose, no forcing, same cloth vertices — the only version of
that comparison that concludes anything — requires the mesh surface to BE the body. On Batman it is
his head. So B cannot be run on the character whose capsules are the ones measured at 51-56 mm
proud until the split is fixed. Running it now would compare authored capsules against a cowl and
return a large disagreement that means nothing.

## STATE

* Baseline closed; the positive control on K-2SO stands and is now a zero-response-then-rise with
  its onset predicted by an independent gap measurement.
* **Measurement A void**, for a stated and measured reason, on both bundles. The yoke is ungraded.
* **Measurement B blocked** by the same defect.
* 23 of 23 Unity runs clean; two of them announced their own invalidity, which is the system working.
* Nothing committed by me. No character, bundle or backup written. The `f7d268e0` backup was opened
  read-only and its MD5 re-verified after the run.

---

# Part six: the enclosure counts, and the capsule justification withdrawn

## First, this file's own rationale is withdrawn

`YargClothInside.cs` was written citing a measurement that the clavicle capsules stood 51-56 mm
proud of the skin, which would have meant anything inside a ~5 cm shell of that joint counted as
penetration without touching the body. **That figure was retracted on 2026-11-23 by the session that
produced it**, and the docstring has been corrected rather than left citing it. Radius minus
distance-to-nearest-body-vertex is not an over-read when the capsule's centre sits inside the body,
which a clavicle's does. Re-measured directionally, ~200 samples per collider against the farthest
surface point in a 12 degree cone:

    C_head (small)   55.8 mm  proud in  24/200  median  6.4 mm   <- CONTROL, it fits a head
    C_head (large)   83.7 mm  proud in  71/200  median 35.3 mm
    C_spine_b       111.8 mm  proud in  63/200  median 62.6 mm
    L_clav           94.4 mm  proud in   4/200  median 14.2 mm
    R_clav           94.7 mm  proud in   3/200  median  8.7 mm

The clavicles are proud in 3 and 4 directions of 200: they FILL a shoulder. So `fml_un_L_clav`
owning 21.7% of recorded cape contact is **not** capsule over-read, and "a fat capsule swallows a
yoke, a surface does not" is not true of that capsule. The instrument keeps its place on its own
control — K-2SO at 45, 45, 43, 60, 82 with the unpushed arm flat at 21 — and not on that argument.

## Three directions of error is why the 0.5 cannot be tuned

| character | share of its body piece | effect of "share > 0.5 per piece" |
|---|---|---|
| Power Girl | 0.568 | **over**-labels: skin and costume are one fused shell, the sleeve is swallowed |
| Jinx | — | **under**-labels: 15% of her is body |
| Batman | 0.355 | **under**-labels: only the cowl is body, so the body surface is a head |

One rule failing in three directions is not a calibration problem.

## The enclosure counts, raw

Per piece: how many humanoid bone POSITIONS lie inside it. **Nothing is labelled from this.**

    PowerGirl  piece 0  vol 0.0635  closed 1.000  ENCLOSES 48   <- the body
               piece 1  vol 0.0044  closed 0.997  ENCLOSES  4   [Neck Head shoulders]
               piece 2  vol 0.0030  closed 1.000  ENCLOSES  0   <- the cape
    Batman     piece 0  vol 0.0993  closed 0.994  ENCLOSES 41   <- the torso
               piece 1  vol 0.0242  closed 0.989  ENCLOSES  0   <- the cape
               piece 4  vol 0.0035  closed 0.990  ENCLOSES  3   <- the cowl
               piece 2  vol 0.0067  closed 1.000  ENCLOSES  3   <- a boot, enclosing foot bones
    Jinx       piece 1  vol 0.0092  closed 0.992  ENCLOSES 25   <- her torso
               piece 0  vol 0.0135  closed 1.000  ENCLOSES  3   <- her hips and legs

All three solved cases reproduce: the body ranks first or near-first and encloses most of the
skeleton, both capes read **0**, and the cowl reads 3 against a torso's 41.

## Two corrections the data forced, neither of them my first guess

**My inverted-winding hypothesis was wrong.** The first run had a 92-triangle shell reporting 46 of
52 bones enclosed, and I predicted inverted normals. Signed volumes **disproved** it: that piece is
+0.00016 m3, positive, like almost every other piece, and the one negative piece reported an
unremarkable 5. The real defect was that a sign test answers fluently for points nowhere near the
piece — the hips are ~0.65 m from a 163 mm-tall hair shell. Fixed with a geometric necessity rather
than a threshold: **a point inside a shell cannot be further from its surface than the shell's own
largest half-extent.**

**Ranking by triangle count hid the Jinx case entirely.** Her six braids are ~12,000 triangles each
and her body was not in the top twelve, so the test never saw the thing it was being validated
against and read 0 everywhere. Ranked by volume it appears immediately: a body piece is 0.0635 m3
against a hair shell's 0.00002 m3, a factor of three thousand, while their triangle counts are
within 10x. Triangle count measures how finely a thing was modelled; volume measures whether it is
a solid.

## WHAT IT DOES WITH A 1-BONE PIECE: nothing, by design

It reports the count and stops. No label is derived here, and "the piece enclosing the most bones"
is deliberately **not** implemented, for a reason the counts now demonstrate:

* Enclosure identifies "wraps a bone", which is true of a body AND of every tight garment. Batman's
  boots enclose 3 foot bones each; his cowl encloses 3. A rule admitting a 1-bone piece readmits the
  cowl on any character whose head is a separate shell.
* **Jinx's body is not one piece.** Her torso encloses 25 and her hips-and-legs piece encloses 3,
  separately. A single-piece rule would take her torso and lose her legs. That is a constraint on
  the decision rule that no amount of care about the count would have revealed.

## Residual defect, stated not buried

Three small open shells on Power Girl (closed 0.481-0.689, 38-76 triangles, near the head) still
report 3 bones each. The half-extent constraint does not suppress them because they are tall and sit
beside the neck. Small counts, no longer absurd, and still wrong — an open shell has no inside, so
anything it reports is an artefact. A piece's closedness is printed beside its count so a reader can
discount them, which is the same discipline as printing driving-bone names raw.

## STATE

* Enclosure counts reproduce all three solved cases. **No split rule is written from them.**
* 26 of 26 Unity runs clean.
* Measurement A still ungraded; measurement B still blocked, and now also no longer confirming a
  prior figure, since the 51-56 mm claim is withdrawn.
* Nothing committed. No character, bundle or backup written.

---

# Part seven: the greedy cover, and one fixture that was wrong

## The rule

1. order the pieces by signed volume, descending
2. a piece joins the body set **iff** it encloses at least one humanoid bone no selected piece encloses
3. stop when nothing can add a new bone; the rest is cloth

No threshold, and a COVER rather than a selection. Both failures of a single-piece rule are now on
record: ranking by triangle count loses Jinx's body entirely (not in the top twelve), and
"largest-volume piece" loses her torso, because her largest piece is her legs.

**Triangle count measures how finely a thing was modelled. Volume measures whether it is a solid.**

## Fixture results

    PowerGirl  pieces=2  covered=50/52  best_single=48   expected 1  -> FIXTURE WRONG, see below
    Jinx       pieces=9  covered=42/52  best_single=25   expected >=2  OK
    Batman     pieces=3  covered=45/52  best_single=41   expected >=2  OK

**The Power Girl fixture encoded a wrong expectation and I am correcting the expectation, not
relaxing the assertion.** The hand-check assumed her body piece already covered Neck and Head, so
the second piece would be redundant. It does not: piece 0 encloses 48 bones and piece 1 adds
`Neck Head LeftShoulder RightShoulder`. Piece 1 is **her head** — 12,504 triangles, closed 0.997,
`share=0.542` where every hair shell on her reads 0.000, spanning y=1.471..1.789 above her body's
1.577. Selecting it is correct. Her body is two shells, as Jinx's is nine.

(That identification is inferred from weight share, enclosure and extent, not from a name: the
bundle exporter destroys material names, so all five of her hair shells read `PowerGirl_3`.)

## Two divergences from the predicted walk, both worth knowing

**Batman takes torso + both boots, NOT the cowl.** His torso piece reaches y=1.601 and already
encloses his head bone, so the cowl adds nothing new and falls out as cloth. The predicted walk had
the cowl joining. Consequence to carry forward: his cowl is now measured AS CLOTH, so it can be
reported penetrating his head, and a cowl-shaped finding on Batman should be read with that in mind.

**Jinx takes 9 pieces**, and the extras are structurally right rather than noise: pieces 13 and 16
add 9 bones each at closed 1.000 and tiny volume — hands, enclosing finger bones. Two pieces carry
the OPEN-SHELL flag at closed 0.875 and add 2 bones each.

## The five assertions, all live

* **A piece enclosing 0 bones can never be selected.** Structural, not statistical. Both capes read
  0; every hair shell measured reads 0. This single invariant replaces four identity heuristics that
  each came back with hair.
* **The largest-volume piece must enclose a bone or the run is REFUSED** — the triangle-count
  failure turned into a guard, since that run reported 0 everywhere and looked like a finding.
* **The union covers at least as many bones as the best single piece** — checked every run
  (50>=48, 42>=25, 45>=41).
* **Uncovered bones are reported BY NAME, never silently.** All three characters leave finger and
  thumb tips uncovered, which is legitimate: a fingertip bone can sit outside every closed shell.
* **Closedness is flagged beside every selected piece, below 0.9** — a flag on the report, not a
  threshold in the decision.

## The limitation, stated before it bites

This finds the **outermost enclosing shell**. A full-body outer garment over skin wins the cover and
the skin beneath it becomes cloth, so penetration INTO that shell is measurable and penetration OF
it is not. Right for Batman, whose suit is the visible silhouette and whose cape-into-suit is the
fault being chased; wrong for any character whose coat is the thing to be tested. Same shape as the
fused-surface limit and not fixable by tuning. No later run may quietly assume otherwise.

## Measurement A on the cover split: measured, and it does NOT grade the yoke

Two bundles, one instrument, no forcing, one pose. Both verified by MD5.

The body surface is real now: **beyond-cutoff 332/5540, six percent**, against 86% on the component
split, median nearest 29.6 mm.

| band | clavicle `a9b26646` | spinecape `f7d268e0` |
|---|---|---|
| INSIDE | 317 | 283 |
| >5 mm | 187 | 175 |
| >20 mm | 117 | 119 |
| >40 mm | **100** | **100** |
| LeftShoulder | 79 | 81 |
| RightShoulder | 55 | 53 |
| (non-humanoid) | 142 | 108 |

**At the shoulders the two builds differ by two vertices per side, in opposite directions.** That is
indistinguishable, and the shoulders are where the yoke lives. The aggregate gap of 34 sits almost
entirely in `(non-humanoid)`, which the controls do not vouch for; the >40 mm band is **identical at
100**, a shared artefact tail rather than a shared fault; the cutoff warning fired three times per
run; and `deepest=229 mm` into a shoulder is physically impossible.

So **the re-parent made no measurable difference to cloth-into-body at the shoulders.** That is
weaker than either direction of win and it is what the data supports. 317 against 283 is not
reported as the clavicle build being worse.

### A reporting defect, found while reading this and not yet fixed

`bodyTris` prints **3486** on the COVER rows, which is the WEIGHT split's tally. The cover's actual
body is 6438+896+896 = **8,230** triangles. Anyone comparing `bodyTris` across splits is comparing
one split's count three times. It does not affect the measurement, only the label beside it, and it
should be fixed before the next sweep.

### The label is fixed and verified

`bodyTris` now reports each split's own body: **8230** on the COVER rows, exactly 6438+896+896, with
`clothTris=10588`. INSIDE is unchanged at 317 and 283, which confirms the change touched the label
and not the measurement.

---

# THE FINDING OF THE WEEK, which part six buried inside a comparison

**79 and 55 cloth vertices sit inside Batman's left and right shoulders, in BOTH bundles, on a real
body surface.** That is the fault Jay reported — localised to a bone and counted — for the first
time. The bundle comparison was the question asked; this is the answer that was needed, and it was
written up as a row in a table about something else.

**Nothing measured this session says what fixes it.** The cape's parenting does not: the two builds
differ by two vertices per side, in opposite directions. Do not read the re-parent as the cause, and
do not read these two numbers as graded by anything yet.

`cloth-inside-body-HANDOFF.md` carries what is not in this file: the five identity rules tried and
discarded, the approaches that looked right and were not, and the instrument's ten open edges —
including that **push mode is validated and animation mode is not**, and that three characters
(DoomSlayer, Sayuri, AlcinaDimitrescu) have pathological component counts that were never diagnosed.


---

# Part eight: the 134 is attributed, and the headline is WITHDRAWN

Date: 2026-11-23. Same instrument, same installed bundle (`a9b26646`), one frame and four frames,
plus Power Girl in the same editor session. `YargClothInside.cs` gained a per-vertex attribution.

## What was wrong with the headline

Part seven reported **79 and 55 cloth vertices inside Batman's left and right shoulders** as the
fault Jay reported, localised and counted. "Inside LeftShoulder" names **where a vertex LANDED** --
the region is the humanoid bone of its nearest *body* triangle. It does not name **what put it
there**. The two are different quantities and only the second one can be fixed.

So the instrument now carries the dominant bone and source mesh of every welded vertex, and
attributes the inside set with no filter of any kind. **Conservation is the control:** attributed
317 of inside 317, `no_bone=0`, on every run. An attribution that drops vertices prints the same
clean shoulder as a character that has none.

## The 134, named

| region | driving bone | n | median depth | max | mesh |
|---|---|---|---|---|---|
| LeftShoulder | `fml_un_C_neck_b` | 28 | 88.7 mm | 127.3 mm | Object_400 |
| LeftShoulder | `fml_un_C_head` | 20 | **198.2 mm** | 225.1 mm | Object_400 |
| LeftShoulder | `fml_un_C_neck_a` | 12 | 79.0 mm | 92.2 mm | Object_400 |
| LeftShoulder | `fml_un_L_cape_a_a` | 6 | 6.4 mm | 11.7 mm | Object_7 |
| LeftShoulder | `fml_un_L_capeTrap` | 6 | 5.1 mm | 18.6 mm | Object_7 |
| LeftShoulder | `fml_un_C_cape_a` | 6 | 4.0 mm | 6.0 mm | Object_7 |
| LeftShoulder | `fml_un_C_cape_b` | 1 | 1.6 mm | 1.6 mm | Object_7 |
| RightShoulder | `fml_un_C_neck_b` | 21 | 89.6 mm | 129.9 mm | Object_400 |
| RightShoulder | `fml_un_C_neck_a` | 14 | 56.9 mm | 96.4 mm | Object_400 |
| RightShoulder | `fml_un_C_head` | 13 | 177.6 mm | 229.0 mm | Object_400 |
| RightShoulder | `fml_un_R_capeTrap` | 4 | 11.4 mm | 18.8 mm | Object_7 |
| RightShoulder | `fml_un_C_cape_a` | 2 | 3.2 mm | 3.2 mm | Object_7 |
| RightShoulder | `fml_un_R_cape_a_a` | 1 | 0.1 mm | 0.1 mm | Object_7 |

**108 of the 134 are his COWL AND NECK, in the body mesh.** 19 of the left 79 and 7 of the right 55
are cape, at medians of 0.1 to 11.4 mm.

The two meshes, measured rather than named -- `Object_400` carries body, cowl, belt and blades,
`Object_7` is the cape:

    Object_400  n=246  median  17.434mm  max 229.028mm
    Object_7    n= 71  median   3.339mm  max  26.228mm     <- THE CAPE, all of it, whole character

## The 229 mm deep tail is diagnosed

Open edge 2 of the handoff recorded `deepest=229 mm` into a shoulder as physically impossible and
never diagnosed. It is `fml_un_C_head` at a median of 177.6 to 198.2 mm: **the cowl's head
geometry.** His torso shell reaches y=1.601 and already encloses the `Head` bone, so the cowl falls
out of the cover as cloth and sits genuinely inside the body shell, while its nearest *body*
triangle is 229 mm away at the shoulder. The depth is correct. The instrument is correct.

**Open edge 4 predicted this exactly** -- "his cowl is now measured AS CLOTH, so it can be reported
penetrating his head" -- and it still cost a headline, because the finding arrived labelled
**LeftShoulder** and the caveat was written against **Head**. A caveat keyed to one name does not
fire when the artefact appears under another.

## Against the reference cape: Batman is not worse

Power Girl in the same editor session, same instrument, same pose source. She is the character this
project treats as correctly built and her cape is parented under her clavicles.

| | Batman | Power Girl |
|---|---|---|
| inside, total | 317 | 1,318 |
| `>20 mm` band | 117 | 17 |
| `>40 mm` band | 100 | **0** |
| LeftShoulder / RightShoulder | 79 / 55 | **1 / 1** |
| cape mesh | 71 @ median 3.3 mm, max 26.2 mm | 541 @ 4.3 mm, max 20.1 mm and 772 @ 4.3 mm, max 35.3 mm |

Read the last row first: **Batman's cape penetrates his body no more than hers does, and by median
slightly less.** A few millimetres at the contact patch is how both capes are built, which is the
case the instrument's own docstring warns is not a defect.

**The shoulder rows are NOT comparable between them, and that is the confound.** The cover selected
Power Girl's HEAD as a body piece (12,504 triangles) and did not select Batman's cowl, so her
equivalent head shell is on the body side where it cannot be counted as cloth and his is on the
cloth side where it must be. 134 against 2 is mostly a difference in what the cover chose, not in
how the two characters are built.

## What this leaves

* **The headline of part seven is withdrawn as a measurement of the reported fault.** It was not
  wrong about any number. It was wrong about what the numbers were of.
* **This instrument, in this pose, does not distinguish Batman's cape from the reference cape.**
  That is not the same as Jay seeing nothing -- he reported it from the podium in the game, and
  animation mode is still unvalidated (open edge 1). It means the fault is not where this
  measurement was pointed.
* Shoulder counts across four frames of the idle: left 79, 69, 67, and right 55, 52 -- while the
  idle moves bones up to 199 mm. Persistent, shallow for the cape, and not produced by the motion.
* Everything shallow and un-dramatic is authored: `R_belt` 21 at 3.8 mm, `C_breast` 16 at 0.03 mm,
  the blades at 17 to 20 mm. A waistband inside the skin is how a waistband is built.


---

# Part nine: the pose was right all along, the WINDOW was 19% of it

Date: 2026-11-23, later. Same installed bundle (`a9b26646`). `YargClothInside.cs` gained four
things: the animation driver as an argument, the clip phase printed every frame, the real spring
solver, and `-coverOnly`.

## The driver question is answered, and it is dead

Jay asked for the instrument to be pointed at "the podium pose you actually see". It already was,
and here is why that was worth an hour rather than an assumption.

The instrument drives the character the way `CharacterPreview.cs` does -- the SETTINGS preview
pane: `Initialize()`, `SetPreviewIdle()`, a trigger, then `Rebind()`. `Podium.SetCharacter` -- the
character select screen, the podium -- does **none** of that. It instantiates, parents, and sets
**one** trigger. Two drivers over one clip have already been measured on this project sharing 0 of
120 frames, so this was a live difference, not a pedantic one.

So the driver became the third field of a subject entry and three of them ran in one editor
session: `preview` (the committed behaviour), `podium` (`Podium.SetCharacter` verbatim), and `raw`
(nothing but the warmup `Update`, as the control).

**All three produced byte-identical numbers.** inside 317, LeftShoulder 79, RightShoulder 55,
`Object_7` 71 at a 3.339 mm median, every band, every digit. And the Animator, asked rather than
predicted, named the same thing three times:

    controller=DefaultController layers=2 hasAttract=False hasIdle=True
    layer0 "Base Layer"        VoxIdle    w=1.000  normTime=0.095
    layer1 "Hold Microphone"   VoxMicGrab w=1.000  normTime=1.000

Two reasons the drivers cannot differ here, both of which the run exposed and neither of which was
predicted:

* **`hasAttract=False`.** The podium's first branch never fires on this character; it falls through
  to the `Idle` trigger, and `raw` sets nothing and lands in the same state, so the state is the
  controller's default rather than anybody's trigger.
* **`[INSIDE] Batman-preview: VRM init skipped: NullReferenceException`.** The preview driver's
  `Initialize()` **throws**, inside a `try` that logs and continues. So the settings-preview driver
  has never been applied either. Both named drivers were no-ops the whole time.

That is what the `raw` arm was for. Without a driver that deliberately does nothing, three
identical results read as "the driver does not matter" instead of "no driver ran".

## The real defect: every number so far is ONE INSTANT of a 10.55 s idle

`VoxIdle` is **10.550 s and looping**, and the single-frame runs of parts one to eight all read it
at `normalizedTime=0.095`. 17 frames at 0.125 s covers 0.095 to 0.284: **19% of the clip.** This
project has already published findings from 38% of an animation without saying so. This is worse
and it is the same mistake.

**The cape is not quiet across that window. It was quiet at the frame I picked.** `Object_7`, the
cape renderer, per frame:

| | n | median | max |
|---|---|---|---|
| f0 -- the frame every earlier part reports | **71** | **3.339 mm** | **26.228 mm** |
| minimum over 17 frames | 46 | 3.090 mm | 19.494 mm |
| **maximum over 17 frames** | **164** (f4) | **10.475 mm** (f3) | **79.610 mm** (f4) |

f0 is at or near the bottom of all three ranges. The cape's penetration more than **doubles** in
count and **triples** in depth within 2 s of the idle.

## So part eight's second headline is WITHDRAWN TOO

Part eight said: *"Batman's cape penetrates his body no more than hers does, and by median
slightly less"* -- 71 at 3.3 mm against Power Girl's 541 at 4.3 mm and 772 at 4.3 mm.

**That comparison was two single frames, one each, and neither was chosen.** Both characters were
read at whatever phase a warmup of 1.0 s happens to land on, and on Batman that phase is his
quietest. His max alone goes to 79.6 mm four frames later, which is more than double anything
measured on her at one frame. The claim is not merely unsupported in its direction -- the
quantities being compared are not comparable at all.

A per-frame comparison on the **same frames** is the only version of that sentence that can stand,
and it is running. Until it reports, the honest statement is: **we do not know whether his cape is
worse than hers.**

## Two frames where the split collapses

f11 and f15 read `>40 mm = 1` where every other frame reads 87 to 107, and `Object_400`'s max falls
from ~230 mm to ~40 mm. The deep cowl tail disappears at those two frames and comes back.

That is the cover changing its mind, not the cowl moving 190 mm in an eighth of a second -- and the
selection-changed guard added in part ten names it rather than leaving it to a guess. On both those
frames the cover takes a **fourth piece of 2,040 and 2,044 triangles**, so that geometry becomes
**body** and stops being measurable as cloth, which is where the deep readings go. The cape's own
row is still there at f11 and f15 (64 and 80 vertices), so the piece that joined is **not** the
cape, and this happens with **no solver running at all**.

An earlier draft of this paragraph said the torso shell "presumably stops" enclosing the `Head`
bone. The direction was right and the route was a guess; the guard measures the route. It is open
edge 5 arriving as a number, and **a reason not to read any single frame of this instrument on this
character** -- the same lesson as the section above, from the other direction.

## What was blind, and is no longer: THE SOLVER NEVER RAN

The cape's bones are non-humanoid spring joints. `VoxIdle` is 372 humanoid muscle curves and
animates none of them. Unity's spring solver is what moves them -- and in edit mode
`Vrm10FastSpringboneRuntimeStandalone.InitializeAsync` reads, in full,
`if (Application.isPlaying) await ConstructSpringBoneAsync(...)`, so nothing is built and nothing
is simulated.

**So every cape number in parts one to nine describes the cape where SKINNING leaves it.** The
instrument's docstring justifies skipping the solver, and the justification is true: *"the shoulder
yoke is RIGIDLY SKINNED -- its bones are on no spring chain -- so its animated position is pure
skinning and needs no solver."* It is about the **yoke**. It was never true of the **cape**, and it
sat at the top of the file reading like a general licence.

`CapeCollisionProbe.cs` established the edit-mode sequence months of this folder ago -- touch
`Runtime`, take `SpringBone`, `ReconstructSpringBone()`, `Process(dt)` -- and established that an
empty buffer must **refuse** rather than report. Both are now in `YargClothInside.cs` behind a
fourth subject field, with `-substep` so the solver runs at 1/60 rather than taking one 0.125 s
step, and a 1.0 s settle so frame 0 is not an instantiation transient.

**The control is the joint's LOCAL rotation.** A spring joint's world position moves with the
solver off, because it rides an animated parent; what only the solver can change is its rotation
relative to that parent, and the clip does not touch these bones. So the solver-off arm must print
`maxLocalRot ~0` and the solver-on arm must not. Five spring probes on this project have read zero
for every character where the zero was the harness; this is the test that tells those apart, and it
has both cases by construction.


---

# Part ten: the solver runs, and the SPLIT turns out to be a per-frame result

Four arms in one editor session -- {Batman, Power Girl} x {solver off, solver on} -- 17 frames
each at 0.125 s, podium driver, `-coverOnly`. Batman `a9b26646`, Power Girl `49a7c173`.

The coverage statement from part nine is now printed beside the numbers it qualifies, and the
run was gated on it:

    [COVERAGE] Bat-ON: 2.000s of 10.550s = 18.957% at 17 frame(s) x 0.125s -- PARTIAL --
               counts and maxima are a FLOOR, and no cross-subject comparison is valid
               unless both arms cover the SAME phases

`-requireCoverage 0.15` passed at 18.957% and would have refused the run above 0.19, naming the
`-frames` to pass instead. Everything below is inside that 19%.

## The solver control passes, in both directions

    [SPRING] Bat-ON: runtime=Vrm10FastSpringboneRuntimeStandalone springs=5 logics=50
                     colliderSlots=260 colliderComponents=52 joints=55
    [SPRING] Bat-ON: settled 60 steps of 0.017s (1.002s) before frame 0
    [SPRING] Bat-ON f1: joints=55 moved=55 maxLocalRot=178.427deg
    [SPRING] PG-ON:  springs=16 logics=135 colliderSlots=140 joints=151
    [SPRING] PG-ON f1: joints=151 moved=111 maxLocalRot=51.058deg

The off arms print nothing, because they have no joints to report -- which is the silent half of
the control. The buffer is non-empty on both on-arms, so the empty-buffer refusal did not fire,
and every joint's rotation relative to its parent changes, which only a solver can do. **The
solver is running.** That is the whole of what the control establishes, and the next section is
why that distinction matters.

## THE COVER IS NOT STABLE UNDER SIMULATION, and this is the finding

On **5 of Batman's 17 frames** (f7 to f11) the greedy cover selected a **fourth** piece:

    [COVER] Bat-ON: SELECT piece 1 tris=2955 vol=0.02203201 closed=0.988 adds=10 bones

2,955 triangles, 0.022 m3, closed 0.988, enclosing **7 to 15 humanoid bones**. That piece is his
**cape**. With the solver running it moved far enough around him to qualify as a body part.

**Nothing in the report looks wrong when this happens**, which is what makes it expensive:

* the cape stops being cloth, so its `BY MESH` row **disappears**. A missing row is not a zero
  and reads as one.
* the body surface now *includes* the cape shell, so the cowl and belt are measured against a
  surface wrapped around them: **800 vertices at a 109 mm median**, where four frames earlier the
  same character read 250 at 8 mm.
* **the conservation control still passes** -- 800 of 800, `no_bone=0`. It checks that nothing was
  dropped, not that the right thing was measured. A control is only ever a control of one thing.

This is **open edge 5** -- *"the cover finds the outermost shell"* -- arriving in a form nobody
predicted. It was written as a static property of a character ("a full-body coat wins the cover").
It is also a **dynamic** property of a frame: a cape in motion is a full-body coat for an eighth of
a second. The split was validated on three characters in static poses, and that validation does not
carry to a moving one.

`YargClothInside.cs` now pins the cover's selection on frame 0 and **warns, naming both
signatures**, whenever a later frame chooses differently. Running it told me something I had
already written down wrongly:

    [COVER] Bat-OFF f11: THE SELECTION CHANGED -- body is now pieces [896+896+2040+6438]
                         where frame 0 had [896+896+6438]
    [COVER] Bat-ON  f7:  THE SELECTION CHANGED -- body is now pieces [896+896+2955+6438]
    [COVER] Bat-ON  f11: THE SELECTION CHANGED -- body is now pieces [896+896+2040+2951+6438]

**It fires twice on the solver-OFF arm, at f11 and f15.** So the cover is not merely unstable under
*simulation* -- it is unstable across the *pose*, with no solver anywhere, and a 2,040-triangle
piece joins the body at those two phases. That is exactly the collapse part nine recorded and
explained with a "presumably"; the guard names it instead. **What the solver changes is how often:
2 frames of 17 become 6, and the piece that joins is the 2,951-triangle cape rather than the
2,040-triangle one.** At f11 with the solver both of them join.

So the honest form of the finding is: the greedy cover's selection is a **per-frame** result that
nobody was reading as one, and simulation makes it three times worse.

**And the guard has its silent case, run on purpose rather than assumed.** It had fired 8 times
across two Batman arms, and a guard that fires on everything it has been pointed at has the same
hole as one that has never fired. Power Girl's solver-on arm is the strong accepting case -- the
solver running, 151 joints moving up to 62 degrees, and the cover asked to stay put:

    selection-changed warnings: 0
    [COVER] PG-ON: pieces=2  x17 frames

So the guard distinguishes the two states rather than reporting one of them.

## Does the solver change the cape's penetration? YES, on the frames that stayed comparable

Frames are comparable **between the arms** only where both chose the same pieces: f0-f6, f12-f14
and f16 at the base 3-piece split, plus f15, where both arms took the same fourth piece. f7 to f11
are not comparable in either direction. Twelve frames survive, and none of f11 or f15 is comparable
with *frame 0* within its own arm. `Object_7` is the cape renderer, measured from the renderer the
triangle was drawn with:

| frame | off: n / median / max | on: n / median / max |
|---|---|---|
| f0 | 71 / 3.3 / 26.2 mm | 88 / 6.4 / 34.8 mm |
| f3 | 127 / 10.5 / 51.8 mm | 142 / 16.1 / 74.9 mm |
| f4 | 164 / 10.2 / 79.6 mm | 180 / **19.4** / 73.9 mm |
| f5 | 109 / 5.0 / 61.4 mm | 176 / 12.1 / **100.3 mm** |
| f6 | 70 / 3.5 / 47.8 mm | 96 / 9.7 / 69.7 mm |
| f13 | 68 / 3.3 / 47.5 mm | 100 / 9.6 / 56.4 mm |

**Count up on 12 of 12. Median up on 12 of 12** -- roughly doubled. Max up on 8, unchanged on 3,
down on 1. Peak with the solver: **100.3 mm of cape inside his body.**

## The replacement for the withdrawn comparison

Same instrument, same 17 frames, same session. Her cover is stable so all 17 of hers count.

| peak over the window | Batman (`Object_7`) | Power Girl (`mesh2`) |
|---|---|---|
| vertices inside, solver off | 164 | 775 |
| vertices inside, solver on | 180 | **1761** |
| median depth, solver on | **19.4 mm** | 7.8 mm |
| **deepest, solver on** | **100.3 mm** | **52.1 mm** |

**Her cape penetrates about ten times as many vertices at under half the median depth; his reaches
twice as deep.** Broad and shallow against narrow and deep -- and narrow-and-deep is the signature
of something going *through* rather than resting *against*. That is the first supported statement
that his cape behaves differently from the one this project calls correctly built.

Four things it is not, each of which would make it less than it sounds:

1. **The medians are not comparable across differently-sized sets.** Hers includes a large shallow
   resting contact that pulls her median down; a fraction whose denominator moves is not a
   measurement, which this project has already paid for. Read the counts and the maxima.
2. **Her idle barely moves.** `mesh1` reads 541 at 4.338 mm, max 20.086 mm, *identical to three
   decimals on all 17 frames of both arms* -- it is not spring-driven at all, and her animation
   moves little but her left hand. So this compares a moving subject with a nearly static one.
3. **19% of the clip**, as part nine. Both arms cover the same phases, which is what makes them
   comparable at all, but neither covers the idle.
4. **The simulated cape may not be the game's cape.** See below.

## WHY NO NUMBER ABOVE SHOULD DRIVE A CHANGE YET

Two readings from the on-arm are hard to credit as cloth:

* **`maxLocalRot` reaches 178.4 degrees in one measured frame** and bounces -- 178, 177, 154, 167,
  89, 165, 86, 82, 144, 180. A joint nearly reversing relative to its parent in an eighth of a
  second is not a cape settling. Power Girl, same solver, same session, same timestep, reads
  **51 to 62 degrees** -- so his cape's joints swing about **three times as hard as the reference
  character's**, which is either the fault itself or the solver misbehaving on his rig, and this
  measurement cannot say which.
* **The cape enclosed 7 to 15 humanoid bones.** A cape that engulfs a seventh of the skeleton has
  not draped, it has wrapped around him.

The history says this is the right thing to be suspicious of: *"The cape was FLYING, not clipping"*
was a real diagnosis on this character, and a zero-stiffness settle on this project once predicted
488 mm of hair travel where the engine at its real stiffness showed none. **Nothing measured here
distinguishes the edit-mode solver from the one the engine runs.** The solver being *present and
stepping* is not the solver being *right*, and this folder has already shipped "present is not
working" once.

So: the instrument is now faithful in its pose, faithful in its driver, and runs the real solver
with a control that proves it ran. The next question is not about Batman. It is **whether this
solver's output matches the engine's** -- against `CapeCollisionProbe`'s recorded travel figures on
the same bundle, or against a render -- and until that is answered the on-arm numbers are a
measurement of a simulation nobody has graded.

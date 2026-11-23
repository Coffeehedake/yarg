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

# Handoff: what is NOT in the cloth-inside-body files

> **CORRECTED 2026-11-23, read this first.** The section below titled "THE FINDING THAT MATTERS
> MOST" is **withdrawn**. Those 79 and 55 vertices were attributed per vertex and **108 of the 134
> are his cowl and neck in the body mesh**, not cape: `fml_un_C_head` at a 198 mm median,
> `fml_un_C_neck_a`/`_b` at 57 to 90 mm. Only 19 left and 7 right are cape, at 0.1 to 11.4 mm, and
> the cape's whole penetration anywhere on him is 71 vertices at a 3.3 mm median -- no worse than
> Power Girl's. **Open edge 2 (the 229 mm tail) is now diagnosed** and is the same cowl geometry.
> **Open edge 4 predicted all of it and did not fire, because the finding was labelled
> `LeftShoulder` and the caveat was filed under `Head`.** Part eight of
> `cloth-inside-body-2026-11-22.md` has the numbers.

> **ALSO CORRECTED 2026-11-23 (part ten).** Part eight's *second* headline -- "his cape is no worse
> than Power Girl's" -- is **withdrawn too**. It compared two characters at ONE UNCHOSEN FRAME
> each, out of a 10.55 s looping clip, and Batman's frame was his quietest (his cape runs n 46-164,
> median 3.1-10.5 mm, max 19.5-79.6 mm over 17 frames). **Open edge 1 is now closed in part**: the
> spring solver had never run, so every cape number before part ten described the cape where
> skinning leaves it. With the solver on, the cover selects his CAPE as a body piece on 5 of 17
> frames and the cape's row disappears while conservation still passes -- open edge 5 as a property
> of a frame. **New open edge: nothing distinguishes the edit-mode solver from the engine's**, and
> `maxLocalRot` of 178 degrees per frame says it should not be trusted until something does.

Written 2026-11-23 at the end of the session that built `YargClothInside.cs`. The *results* are in
`cloth-inside-body-2026-11-22.md` and in the commits. **This file is the part that dies with the
context:** what was ruled out and why, what looked right and was not, and where the instrument's
edges actually are. Read it before extending the tool or re-opening a question.

---

## THE FINDING THAT MATTERS MOST, AND I UNDER-REPORTED IT

**79 and 55 cloth vertices sit inside Batman's left and right shoulders — in BOTH bundles, on a
real body surface.** That is the fault Jay reported, localised to a bone and counted, for the first
time. I framed that run as a bundle comparison and buried the measurement inside it; the comparison
was the question asked, this is the answer that was needed.

**Nothing measured this session says what fixes it.** The re-parent does not: the two builds differ
by two vertices per side, in opposite directions. Do not read the cape's parenting as the cause.

---

## FIVE IDENTITY RULES TRIED AND DISCARDED

Each looked principled. Four of the five returned **hair**.

| # | rule | why it failed |
|---|---|---|
| 1 | material name | the bundle exporter renames everything `<Character>_N`; five of Power Girl's separate shells all read `PowerGirl_3` |
| 2 | nearest humanoid bone to the piece centroid | Jinx's braids run head to ankle, so each 12,000-triangle braid reported as being over `LeftUpperLeg` |
| 3 | separable-piece count and triangle totals | ranked Jinx top of the roster on 168,475 "separable triangles over a limb" — all hair |
| 4 | per-triangle humanoid weight (the original split, used by `YargCharParts.cs`, `YargClothPenetration.cs` and the interior-fault sweep) | cuts the skin along every weight boundary; Power Girl's body became **231 open patches, 0 closed** |
| 5 | per-piece weight majority (share > 0.5) | failed in **three directions**: Power Girl 0.568 over-labels, Jinx under-labels to 15%, Batman 0.355 leaves only his cowl |

**A sixth was declined rather than built:** angular coverage around the bone axis, to separate a
garment that *wraps* from hair that *hangs*. Every piece confirmed at that point was hair, so it
could have been shown to reject hair and never shown to accept a sleeve. Do not revive it without a
confirmed garment piece to validate against.

**What replaced all of them** is one structural invariant, not a better heuristic: *a piece
enclosing zero humanoid bones can never be the body.* Both capes read 0; every hair shell measured
reads 0.

---

## APPROACHES THAT LOOKED RIGHT AND WERE NOT

These are the expensive ones, because each had a mechanism and a plausible story.

**Screen-space proximity (the predecessor, `YargClothPenetration.cs`).** A fault pixel was cloth +
body + body nearer + gap below a drape distance. The proximity term fixed a false positive and
bought a false *negative* that **scales with severity**: as a limb emerges further the gap grows, so
those pixels leave the drape window. It catches the instant of emergence and loses the emerged
state. Five magnitudes read 397, 395, 396, 397, 398. That file is kept unmodified as the record.

**Proximity as a stand-in for "rests against".** Power Girl has **10,907** static cloth vertices
within 250 mm of her upper arm and only **104** whose nearest body triangle *is* the arm. Her cape
hangs beside the arm, resting on her torso. Near is not on.

**Inverted winding as the explanation for absurd enclosure counts.** A 92-triangle shell reported 46
of 52 bones enclosed and I predicted flipped normals. Signed volume came back **+0.00016 m³**,
positive like almost every piece. The real cause: a sign test answers fluently for points nowhere
near the piece — hips ~0.65 m from a 163 mm shell.

**Three explanations of Jinx's flat sweep, in order, the first two mine and both wrong:** "loose
clothing over a 42 mm measured clearance" (it was hair); "her legs are not in the body surface"
(8,164 of her leg vertices were in it and all moved the full 40 mm); "nothing to cross"
(`cloth_over_push=10,838`). The actual reason is a property of the **method**: a bone displacement
cannot penetrate cloth skinned to that bone, because the cloth travels with it.

**My own "closed = zero boundary edges" gate.** Exact, definitional, judgement-free — and it
discarded a 23,572-triangle body shell over 4 boundary edges in 59,341, then reported on 491 of
15,030 vertices while announcing itself as the trustworthy subset. Threshold-free is not the same as
right.

**My claim that the enclosure test had "no threshold to pick".** The count is threshold-free; the
**decision rule over it** is where the threshold returns, and a cowl enclosing `Head` at 3 beside a
boot at 3 is where it bites.

---

## OPEN EDGES OF THE INSTRUMENT

Ordered by how likely each is to mislead someone.

1. **PUSH MODE IS VALIDATED. ANIMATION MODE IS NOT.** The positive control (K-2SO / LeftUpperArm:
   45, 45, 43, 60, 82, unpushed arm flat at 21, onset matching an independently measured 12.5 mm
   gap) validates **synthetic displacement only**. The subject-moved guard does not even apply
   without a push. Nothing in this session validates reading the instrument over an animation, and
   the two are different forcings — this project already measured that sampling a clip directly and
   letting the Animator retarget give 0 of 120 matching frames. An animation-mode result needs its
   own control.
2. **THE DEEP TAIL IS CONTAMINATED EVEN ON A VALID BODY SURFACE.** On Batman, `deepest=229 mm` into
   a shoulder with `>40 mm = 100` *identical across both bundles*, and the cutoff warning firing
   three times per run. Shallow bands are trustworthy; the tail is not. A 229 mm penetration of a
   shoulder is physically impossible and was not diagnosed.
3. **READ `inside_over_push`, NOT THE REGION ROW.** The region count *falls* while the fault grows —
   K-2SO's LeftUpperArm goes 32, 33, 32, 27, 19 across a rising sweep — because region is assigned
   by nearest body triangle, so vertices leave the arm's bucket for the shoulder's as the arm moves.
   Reading the region row alone looks exactly like a failed control.
4. **BATMAN'S COWL IS CLOTH.** His torso piece reaches y=1.601 and already encloses his head bone,
   so the cowl adds nothing to the cover and can be *reported penetrating his head*. Any
   cowl-shaped finding on him must be read that way.
5. **THE COVER FINDS THE OUTERMOST SHELL.** A full-body outer garment over skin wins the cover and
   the skin beneath becomes cloth: penetration *into* that shell is measurable, penetration *of* it
   is not. Right for Batman, wrong for a character whose coat is the thing to test. Not fixable by
   tuning.
6. **27 OF 65 CHARACTERS CANNOT BE ASKED THIS QUESTION AT ALL.** Their skin and costume are one
   fused connected shell, so "is the cloth inside the body" has no referent. Power Girl's two
   largest pieces are each about half skin-weighted and half garment-weighted
   (`share` 0.568 and 0.542), welded at the garment boundary. This is authoring, not instrument.
7. **8 OF 38 HAVE NO HOSTABLE BONE.** The two control conditions — cloth not driven by a bone, and
   cloth resting on that bone — are anti-correlated by how clothes are made, and on 8 characters
   they never co-occur. That is a structural fact, not a failed search.
8. **THREE SMALL OPEN SHELLS ON POWER GIRL** (closed 0.481–0.689, 38–76 triangles, beside her neck)
   report 3 bones each. Pure artefact — an open shell has no inside. Volume ordering means they are
   covered by the time the walk reaches them, so they fall out as cloth without a cutoff, but they
   are still printed and should be discounted via the closedness column.
9. **NEVER DIAGNOSED: three characters have pathological component counts.** DoomSlayer 87,527
   parts, Sayuri 47,995, AlcinaDimitrescu 24,062 — on meshes of ordinary size. That means welding at
   1e-5 m failed to connect their geometry, so almost every triangle is its own component and the
   cover cannot work on them. I noticed this early and never followed it up. **Do not sweep those
   three without understanding it first.**
10. **The cover uses a 32-piece window** with a coverage guard that warns if a piece outside it
    carries more than 1% of the largest volume. The guard has never fired; that is not the same as
    the window being right.

---

## THINGS THAT ARE SAFE TO RELY ON

* The body/cloth split is now a **greedy cover of the skeleton by descending volume**, validated
  against three characters with known-correct answers and three different directions of prior error.
  Power Girl selects 2 pieces (body + head), Jinx 9 (including hands enclosing finger bones),
  Batman 3 (torso + both boots).
* Both capes read **0 enclosed bones** on every run.
* The failure filter in the launch scripts has its own negative control, after `FATAL` matched the
  `FatalException` in every install path — a false positive documented one morning and reimplemented
  the same afternoon. **Any pattern that greps for trouble gets run against a known-good log first.**
* 30 of 30 Unity runs clean. Two of them announced their own invalidity, which is the controls
  working rather than failing.

---

## WHAT IS DEMOTED, NOT PENDING

**Measurement B — capsules against the mesh surface — is demoted.** It was first meant to confirm a
51–56 mm clavicle over-read, which the session that produced it **withdrew** on 2026-11-23: radius
minus distance-to-nearest-vertex is not an over-read when the capsule's centre sits inside the body.
Re-measured directionally, the clavicles are proud in 3 and 4 directions out of 200 — they fill a
shoulder. `C_spine_b` and the larger head sphere *are* genuinely proud, so the collider set
over-claims in places, and the clavicle is not one of them. What B would now grade is the **capsule
probe**, an instrument being replaced. The over-read question stays interesting and is off the
critical path. `YargClothInside.cs`'s docstring was corrected so it no longer cites the withdrawn
figure as its own rationale.

**The yoke stays installed on Jay's decision and on Power Girl parity alone.** Measurement A did not
grade it.

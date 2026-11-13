# Thirteen faults reported from the game, 2026-11-12

Jay looked at the installed characters and listed thirteen visible faults. **Every one of them
passed every check this project has**: collider groups, unguarded chains, heights, alpha modes,
visemes, eye shells, the census, `identify_build`. That is the first thing to say about this
list, and the most important.

The faults are mostly RIGGING and WEIGHTING — where geometry sits relative to the bones that move
it — and nothing here measures that. The tools built so far read material state, bone *counts*,
spring-bone structure and file-level census. A dress that is not weighted to the body, a hair
mesh parked beside the head, a leg bone mirrored wrongly: all of those files are perfectly
well-formed.

| # | character | reported fault | first guess at the class | touched 2026-11-12? |
|---|---|---|---|---|
| 1 | **Alice Ivy** | hair is detached, floating off a bald scalp | hair rig / spring chain — **and I added her hair chains today** | **YES** |
| 2 | **Heels** | eyes have no irises | the `Std_Cornea_L/R` pair left opaque on purpose — may be the wrong call | no |
| 3 | **Thanos** | armour discoloured, whole body too dark | texture or colour space | no |
| 4 | **Spartan Mark V** | right leg detached and asymmetrical | rig / weighting | no |
| 5 | **The Rock** | arms are squiggly | weighting or a bad fit — he had a shoulder fit applied | no |
| 6 | **Gadget Hackwrench** | mesh not rigged properly at all | weighting — **and I re-collidered her today** | **YES** |
| 7 | **Miku** | hair missing pieces | geometry dropped, or a cutout eating it | no |
| 8 | **Peach** | dress clips through legs, moves as one solid piece | dress not weighted / rigid-bound | no |
| 9 | **Killer Clown** | hair clips through her hat | layering / weighting | no |
| 10 | **Shadow the Hedgehog** | eyes closed | the documented wrong eye-atlas frame — **and I rebuilt him today** | **YES** |
| 11 | **Pomni** | hair clips through face and head | layering / weighting | no |
| 12 | **Jessica Rabbit** | dress not rigged to her body | weighting — **and I rebuilt her today** | **YES** |
| 13 | **Alcina Dimitrescu** | textures discoloured and mapped wrongly | the known noise-texture archive problem, plus UVs — **and I gave her hair chains today** | **YES** |

**Five of the thirteen are characters changed today**, which has to be the first thing
investigated rather than the last: a fault I introduced this morning and a fault that has been
there for weeks look identical in a screenshot.

The backups of all five are hash-verified in `C:\dev\_tmp\yarg-char-backup\2026-11-12-prehair`,
so reverting any of them is a file copy.

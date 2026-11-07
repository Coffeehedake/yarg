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

## Status of each claim

| Confidence | What it covers |
|---|---|
| **Verified by running it** | The install location, and that a stock `.yargchar` loads and renders in a self-built fork |
| **Read from source** | Everything else below — the bundle layout, the rig and expression requirements, the animator contract |
| **Not verified** | Nothing here has been proved by *building* a `.yargchar`. We have never run the exporter |

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
| Display name | **The filename**, minus the extension. No metadata is read | `CustomCharacterSetting.ValueToString` |

Name the file as you want it to read in the picker.

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

Nothing requires an anime style. MToon is the convention, not the contract — the project's own
macOS shader bug report tested URP Lit materials alongside MToon ones on the same model.

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

- **VRM 0.x will not load.** `GetComponent<Vrm10Instance>()` returns null and `Initialize` dies.
- **macOS transparency is broken** for UniVRM10 MToon materials in front of opaque geometry —
  reported 2026-02-23 with a four-eye test rig; Windows under Vulkan and DX11 is correct.
- **Materials need Mac-specific settings** before a bundle is shared, per the maintainer.
- **`_browAggressive`, `_browDown`, `_browOpenmouthed`, `_squint`** are declared in `VRMCharacter`
  and assigned nowhere in the project. The expression surface is still moving.

## Open questions

Not answered by the code, and worth measuring before authoring anything expensive:

- **Scale and height.** Nothing normalises the model. The podium expects a figure of some size;
  we have not measured what.
- **Polygon and texture budget.** No limit is enforced or documented. The eight cleared models
  run 5.6–10.7 MB as bundles.
- **Whether a non-`Vocals` type loads from a file at all**, or only from a venue.
- **What a missing viseme does** — silent fallback, or a visible mouth stuck shut.

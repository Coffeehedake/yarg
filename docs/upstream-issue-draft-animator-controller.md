# Draft upstream issue — not filed

Target: https://github.com/YARC-Official/YARG/issues (Issues is enabled and active; a search for
custom character animation returns no existing report). `CONTRIBUTING.md` names Discord for
discussion and YouTrack for the feature list, and does not name a bug channel — so Discord may be
the better first stop before opening this.

---

**Title:** `LoadAnimationDefaults` always overwrites a custom character's own AnimatorController — the `controller == null` check is unreachable

**Body:**

### Summary

A custom vocalist that ships its own `AnimatorController` and `AnimationClip`s has them replaced by
`DefaultController` unless it also sets `UseCustomAnimations`. The guard that looks like it should
preserve an existing controller cannot ever do so, because the condition that would protect it is
short-circuited by a second term that is already known to be true.

### Where

`Assets/Script/Gameplay/BackgroundManager.cs`, `LoadAnimationDefaults` (line 616 on `master` at
f5bfbe69), called as the first statement of `LoadCharacter` (line 536):

```csharp
if (!vrmCharacter.UseCustomAnimations && animator != null)      // line 621
{
    var controller = animator.runtimeAnimatorController;
    if (controller == null || !vrmCharacter.UseCustomAnimations) // line 624
    {
        ...
        animator.runtimeAnimatorController = newController;
        animator.Rebind();
        vrmCharacter.AnimationStates.Clear();
        vrmCharacter.LayerStates.Clear();
    }
}
```

The outer condition at 621 already establishes that `UseCustomAnimations` is `false`. Inside that
block `!vrmCharacter.UseCustomAnimations` is therefore always `true`, so the inner `||` at 624 is
always satisfied and `controller == null` never affects the outcome. The default controller is
assigned whenever `UseCustomAnimations` is false, whether or not the character brought one.

### Why it matters

A `.yargchar` is an AssetBundle, and a character author can bundle their own controller and clips.
Reading the bundles of an installed set of 65 custom characters:

| character | bundled clips | `UseCustomAnimations` | outcome |
|---|---|---|---|
| Harq Alkahana | `NFIdle, NFIdleRealtime, NFMellow, defaultsing, intensesing` | 0 | replaced |
| Inforder Trogen | same five | 0 | replaced |
| Kaiser Aufhänger | same five | 0 | replaced |
| Hatsune Miku (Retry Now ver.) | same five | 0 | replaced |
| Hatsune Miku (Dark) | same five | 0 | replaced |
| Adachi Rei | `MCU_af_Stand_Sing_01, arm down, arm up, discspin, hold recorder`, … | **1** | kept |

Characters built by a VRM pipeline are unaffected in practice — their bundled clips are the game's
own `VoxIdle / VoxIdleRealtime / VoxMellow / VoxMicGrab / VoxPlaying`, pulled in as
`DefaultController` dependencies, so the swap is a no-op. The five above are not: their clip names
are entirely distinct, and those animations are never played.

Adachi Rei is the only character in that set with `UseCustomAnimations` set, and she is the only one
whose own controller survives — which is consistent with the flag being the *only* thing that
decides, and the `controller == null` test contributing nothing.

### What I have and have not verified

- **Verified by reading** the current `master` source (fetched from raw.githubusercontent.com, not a
  local clone): the inner condition is unreachable as described.
- **Verified by measurement** across 65 installed bundles: the clip names and `UseCustomAnimations`
  values in the table, read from the bundles' `VRMCharacter` MonoBehaviour.
- **Not verified at runtime.** I have not instrumented a running build to observe the controller
  being replaced. The conclusion follows from the code and the bundle contents, and that inference
  could be wrong if something later restores the bundled controller.

### Suggested fix

If the intent is "use the default only when the character has not supplied one", the inner test
should drop the redundant term:

```csharp
if (controller == null)
```

If the intent is the current behaviour — always normalise to the default unless the character opts
out via `UseCustomAnimations` — then the inner `if` is doing nothing and could be removed entirely,
which would at least stop the code implying a protection it does not provide.

I do not know which was intended, which is why this is a report rather than a pull request.

# Trial types

Every trial is given exactly one of nine trial types. They are computed in the **Trial type** section of `embedding_and_labels.m` and written to `data/<session>/binned_labels/trial_type.csv`: one code per time bin, the code of the trial the bin falls in, and `0` for bins between trials. `video.TRIAL_TYPES` holds the same names, for the info panel and `warp.py`.

## Building blocks

Each definition is built from these trial-level properties:

- **Correct**: the trial's port is one of its block's rewarded pair (`Correctness == "correct"`). `CorrectBlock` spells the pair out: `56` is ports 5 and 6.
- **Rewarded**: the trial was rewarded (`Rewarded == "rewarded"`). This is separate from correct, because the session contains correct unrewarded trials and incorrect rewarded ones.
- **Patch**: a pair of neighbouring ports that reward together. Patch 1 is ports 1–2, patch 2 is ports 3–4, patch 3 is ports 5–6, and patch 4 is ports 7–8. A trial's patch is the patch of the port it was at. A block's rewarded patch is the patch of its `CorrectBlock` pair.
- **Block**: a run of consecutive trials with the same `CorrectBlock`.
- **Patch identified** (pre / post): a block's patch counts as identified once the mouse has had three correct rewarded trials at the block's pair. Every later trial in the block is *post*, and every trial up to and including the third is *pre*. The count restarts each block.
- **Switch / stay**: a trial and the trial before it are both correct and rewarded, in the same block, and at the block's pair. If the mouse moved to the pair's other port, it's a switch. If it went back to the same port, it's a stay.

## Definitions

### Before patch identification

| Code | Type | Definition |
|---|---|---|
| 1 | pre rewarded | Any rewarded trial, correct or not. |
| 2 | pre perseveration | Unrewarded, at the **previous** block's rewarded patch. A visit to the current block's own rewarded patch never counts as perseveration, even if the two blocks share a patch. |
| 3 | pre exploration | Unrewarded, anywhere else. This includes unrewarded visits to the current block's correct port, and every unrewarded trial of block 1, which has no previous block. |

### After patch identification

| Code | Type | Definition |
|---|---|---|
| 4 | post switch | A switch: correct and rewarded, after a correct rewarded trial at the same pair, at the pair's other port. |
| 5 | post stay | A stay: correct and rewarded, after a correct rewarded trial at the same pair, at the same port. |
| 6 | post return | Correct and rewarded, but neither a switch nor a stay, because the trial before it was not correct and rewarded at the pair. In practice it's the first rewarded trial after an omission or a wrong-port visit. |
| 7 | post omission | Correct port, unrewarded. |
| 8 | post exploration | Wrong port, unrewarded. |
| 9 | post wrong rewarded | Wrong port, rewarded. |

## Notes

- **Unrewarded trials before identification are not split by correctness.** A correct but unrewarded visit before identification is pre exploration, but after identification it's post omission. Before identification the mouse does not yet know which patch is correct, and such trials are rare (1–3 per session).
- **Reward size matches switch and stay** but doesn't define them. In every session checked, every switch got 30 ms and every stay got 15 ms. Return trials are mostly 30 ms.
- **What precedes a return:** in session 17_05, 44 of the 56 return trials follow an omission and 12 follow a post exploration trial.
- **Coverage:** the MATLAB section asserts that every trial matches exactly one type, and prints how many trials each type has.

## Example counts (session 17_05, 410 trials)

| Code | Type | Trials |
|---|---|---|
| 1 | pre rewarded | 18 |
| 2 | pre perseveration | 37 |
| 3 | pre exploration | 34 |
| 4 | post switch | 78 |
| 5 | post stay | 80 |
| 6 | post return | 56 |
| 7 | post omission | 68 |
| 8 | post exploration | 38 |
| 9 | post wrong rewarded | 1 |

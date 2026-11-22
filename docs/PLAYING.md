# Patching and playing

## Apply the right patch

1. Back up your original ROMs and saves.
2. Obtain the Ages and Seasons BPS patches from `patches/` or the project's release assets.
3. In a BPS-compatible patcher, select an original retail ROM and its matching patch.
4. Save the result as a new ROM file and play it with your preferred emulator or hardware.

The patches are cumulative and apply directly to the original USA/Australia
retail versions. Do not stack releases or apply the patches to modified ROMs.
Japanese and European ROMs are not supported. Each input is 1,048,576 bytes.

| Game | Required input SHA1 | CRC32 |
| --- | --- | --- |
| Ages | `880374fb978b18af4aa529e2e32f7ffb4d7dd2f4` | `3800a387` |
| Seasons | `ba1268290fb2b1b70505d2d7b5825fc8a4816a4b` | `d7e9f5d7` |

Full SHA256 checksums for the inputs, outputs and patches are in
[`patches/manifest.json`](../patches/manifest.json). A mismatched input should be
rejected rather than forcing the patch to apply.

An optional Python-only patcher is included for these two patches. It needs only
Python's standard library, and verifies both input and output checksums:

```sh
python -B tools/apply_patch.py ages /path/to/original-ages.gbc /path/to/new-ages.gbc
python -B tools/apply_patch.py seasons /path/to/original-seasons.gbc /path/to/new-seasons.gbc
```

The input files are never overwritten. Use new output filenames.

## Two-game flow

Start either title as a normal new game. Finish and save Game 1, then use its
game-transfer secret to start the other title as a linked game. Keep returning
to the first save to complete secret quests and exchange their return passwords
with Game 2, as in the original linked system.

Hero's Cave is open from the start in Game 1, with its original puzzles and
equipment requirements. In Seasons Game 1, use the upper door above the original
wooden-sword cave; the ledge is reachable on foot from the western screen. The
lower door still leads to the wooden sword. Linked games keep their native cave
entrances.

After Game 1's completion save, collect the extra heart chest on its reload
screen. Ages also gains its required sea passage when it is Game 1. Collect the
normal heart-secret reward as well.

Two original Game 1 quests now give paired ring rewards:

| Game 1 | Original quest | Rings awarded |
| --- | --- | --- |
| Ages | Mayor Plen | Spin + Swimmer's |
| Ages | Mamamu Yan's dog | Snowshoe + Heart Ring L-1 |
| Seasons | Master Diver | Swimmer's + Spin |
| Seasons | Great Fairy / Temple | Heart Ring L-1 + Snowshoe |

Appraise both at Vasu, then use the ordinary ring secret to exchange rings.
Game 2 does not need to be finished. There are no added follow-up passwords or
extra secret quests; Farore's book keeps its original entries. Normal return
secrets for the other quests and upgrades still work as before.

Finish the linked second game and accept its completion save. Return to Vasu
for the Victory Ring and exchange that ring between saves as well.
The Room of Rites entrance closes after this completion save. Declining the
ending save leaves the entrance available in the previous save.

Advance Shop rings retain their native GBA hardware requirement. For emulation,
use the emulator's appropriate GBA compatibility mode. Automated checks cover
the shop's hardware-ID gate; authentic GBA boot and physical hardware have not
been verified for this patch.

## Saves and troubleshooting

The hack does not add fields to the save format. Paired rewards apply when a
quest is first completed; a quest already claimed in an older build does not
retroactively award its new second ring. Keep a pre-reward save when changing
experimental versions. Existing experimental linked
clears with the broad Game 1 completion markers are normalized on load. Keep a
backup before changing ROM versions; emulator save states are tied to a build
and are not a substitute for battery saves.

When reporting an issue, include game/order, patch checksum or release, emulator
and version, completion state, exact steps and whether it reproduces from a
battery-save reload. Avoid uploading ROMs. Public issue discussions should use
descriptions and steps; arrange private handling if a save is needed.

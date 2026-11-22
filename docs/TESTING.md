# Testing and evidence

## ROM-free checks

```sh
python -B tools/check_public_tree.py
python -B -m unittest discover -s tests/unit -v
```

These validate publication contents, syntax, patch metadata, BPS roundtrips and
rejection of corrupt inputs, source-patch context and unsafe paths. They do not
establish gameplay correctness.

## Emulator regressions

See DEVELOPING.md for private input preparation and dependencies. Run:

```sh
python -B tools/test.py
```

The 22-suite runner covers world/role isolation, family, trades, rescue-role
retirement, Maku advice, paired ring quests, native Farore returns, heart
sequences, chest graphics/persistence, caves, sea access, story prerequisites,
boot/input, full credits, ending save boundaries, Victory Ring, full storage,
ring exchanges, linked starts, Advance Shop hardware-ID gates and the native
Farore book. No reference ROM builds are required: book passwords and pixels
are compared directly with the supplied retail ROMs.

Paired reward tests use all four native Game 1 sources at zero, 62, 63 and 64
unappraised rings. They cover invalid passwords where applicable, both native
pickups, completion only after both, blocked menus during pickup, save/reload,
repeat conversations, actual dog recovery and the Diver failure route. A
separate suite appraises each earned pair at Vasu, transfers it through the
ordinary ring secret to an unfinished linked Game 2, and verifies saved ownership.
The paired-transfer suite runs after ring-quests because it uses its earned SRAM.
For a focused run, select both suites together:

```sh
python -B tools/test.py --suite ring-quests --suite paired-transfer --suite native-book
```

Tests distinguish prepared progression state from actions performed in the
emulator. They do not operate on player saves. Callback assertions are collected
explicitly where needed so emulator callback handling cannot hide failures.

Early cave tests traverse the actual outdoor doors with swordless/starting-sword,
Hero-mode and linked saves. They check matching exits, re-entry, save/reload,
Start/Select graphics restoration, native death menu options and unset completion
flags. Seasons also exercises all four season values. Original sword-cave and
ring-prize checks remain in the cave suite.

Room of Rites tests walk into the real portal before the linked final save and
across its former position afterward, checking both the visible actor and warp
tile. They cover Start/Select menus, room exit/return, native save/reload and
accepting or declining the native ending save prompt. Prepared ending fixtures
include the persistent room bits written by Ganon's death handler. An unrelated
Seasons dungeon portal is also checked after completion.

## Additional review probes

```sh
python -B tests/review3_technical.py
python -B tests/review4_inventory.py
python -B tests/review4_death.py
python -B tests/review4_pending_rewards.py
python -B tests/review4_late_trades.py
python -B tests/review4_sweep.py ages
python -B tests/review4_sweep.py seasons
```

Run the inventory before the sweeps. These check linker bank bounds and overlap,
ROM checksums, chest graphics outside intended changes, live completion
predicates, death/continue, pending rewards and late trades. Review the emitted
NPC text and source references for narrative consistency. A text inventory alone
is not a story audit. Sweep probes simulate the engine delivering an A-button
event to initialized actors; they are script boundary checks rather than
navigation recordings. Output remains under ignored .local/.

## Evidence and limits

reports/release-validation.json and reports/export-validation.json identify the
exact release bytes and checks performed. Old reports do not certify new bytes.

These tests use prepared checkpoints, not full playthroughs of both game orders.
They do not replay every puzzle, boss, collapse route or optional challenge.
The Diver success case starts at the successful-course reward boundary; its
failure case plays the native timed route. Advance Shop tests set the hardware
ID boundary rather than emulating a genuine GBA boot. Physical hardware and
serial linking remain unverified. Passing tests are evidence within that scope,
not a guarantee that no bug exists.

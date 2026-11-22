# Oracle 100 Percent

Complete Oracle of Ages and Oracle of Seasons with **one playthrough of each
game, in either order**: start a normal game, then play the other as a linked game.
Keep both save files; passwords and return visits are still part of the flow.

## Download the patches

- **[Oracle of Ages — 100 Percent.bps](patches/Oracle%20of%20Ages%20-%20100%20Percent.bps)**
- **[Oracle of Seasons — 100 Percent.bps](patches/Oracle%20of%20Seasons%20-%20100%20Percent.bps)**

Apply each patch directly to its matching **original USA/Australia retail ROM**.
Do not stack it on an earlier patch. ROMs and emulators are not included.
See **[patching instructions and required ROM hashes](docs/PLAYING.md)**.
Players do not need Python, the disassembly, PyBoy or a build toolchain if using
a BPS-compatible patcher.

## What changes

- A postgame heart-container chest in Game 1 provides its otherwise missing heart.
  The normal heart secret remains part of completing both saves.
- Hero's Cave is available from the start in Game 1. Discover it early, then
  return as the original equipment puzzles allow, and earn its otherwise missing ring.
- Ages' otherwise inaccessible sea/map area is reachable when Ages is Game 1.
- Two of Game 1's original ring quests each award both counterpart rings.
  Appraise them at Vasu and transfer them with the ordinary ring secret while
  Game 2 is still in progress. The original ten secret quests and Farore book remain.
- Game 2 offers a completion save, making the Victory Ring obtainable afterward.
  Its postgame world uses appropriate peaceful roles while keeping the family,
  unfinished trades and original linked secret givers available.
  The Room of Rites entrance closes after this saved final victory.

This targets collectible/upgrade completion across both saves. It does not make
every mutually exclusive story variant occur in both game orders. Advance Shop
rings retain the games' hardware check; see the player guide.

## Source and development

```text
patches/       Ready-to-apply BPS files and input/output checksums
src/           Reviewable source delta and exact upstream revision/hash manifest
tools/         Source preparation, build, patching, testing and publication tools
tests/         ROM-dependent regression fixtures and ROM-free tooling tests
docs/          Player guide, design, development, testing and release instructions
reports/       Sanitized validation summaries for the shipped patch bytes
.github/       ROM-free public CI checks
```

The full disassembly, ROMs and dependencies are obtained separately and kept in
ignored `.local/` or `.venv/` folders. Source deltas target a pinned
[oracles-disasm](https://github.com/Stewmath/oracles-disasm) revision, rather than
vendoring the entire game source/assets into this repository.

- [Build and development setup](docs/DEVELOPING.md)
- [Testing and coverage limits](docs/TESTING.md)
- [Design and two-game flow](docs/DESIGN.md)
- [Publishing a release](docs/RELEASING.md)
- [Current changes](CHANGELOG.md)
- [Contributing](CONTRIBUTING.md)

Tests cover paired pickups, appraisal and transfer before Game 2's final clear,
full storage, save/reload, native Farore rendering/passwords and the cumulative
world changes. These use prepared states, rather than complete playthroughs of
both orders. See [testing limits](docs/TESTING.md) and
[validation facts](reports/release-validation.json).

Original project contributions are MIT licensed. Nintendo/Capcom content,
upstream disassembly content and external dependencies are not relicensed by
that grant. See [LICENSE](LICENSE), [NOTICE](NOTICE.md) and [credits](CREDITS.md).

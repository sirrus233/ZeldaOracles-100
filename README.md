# Oracle 100 Percent

Completing Oracle of Ages and Oracle of Seasons with [100% Completion](https://zelda.fandom.com/wiki/100%25_Completion#Oracle_of_Ages_&_Oracle_of_Seasons) is a nightmarish affair that requires 
two entire playthroughs of each game. The ROM hack in this repository makes various adjustments
that allow achieving 100% in a single 2-game playthrough, with the games being playable in either
order. 

Please be warned that "I made" this hack with extensive use of LLMs. I think that a hack like this
should exist, but do not have any ROM hacking experience myself, and this is well and truly a
fully vibe-coded project. Bugs may occur. If that happens, please file an issue and I will do
my best to fix the problem.

My sincerest thanks to [@ShadowOne333](https://github.com/ShadowOne333) who's excellent Zelda hack
projects inspired this work, [@d0k3's wiki](https://github.com/d0k3/oracles-disasm/wiki/Make-100%25-possible-on-one-linked-playthrough)
that provided many helpful implementation suggestions, and to [@Stewmath for their work on the Zelda Oracle disassembly](https://github.com/stewmath/oracles-disasm). 

## Download the patches

- **[Oracle of Ages — 100 Percent.bps](patches/Oracle%20of%20Ages%20-%20100%20Percent.bps)**
- **[Oracle of Seasons — 100 Percent.bps](patches/Oracle%20of%20Seasons%20-%20100%20Percent.bps)**

Apply each patch directly to its matching **original USA/Australia retail ROM**.
Do not stack it on an earlier patch. ROMs and emulators are not included.
See **[patching instructions and required ROM hashes](docs/PLAYING.md)**.

GitHub Releases provide both individual patches and a player ZIP with instructions.

## ROM Hack Changes

### Missing Heart Container
**Original:** In the first game played, Link caps out at 14 heart containers. A secret carried over
from a linked game brings this to 15, leaving the second row of hearts incomplete.  

**ROMHack:** A heart-container now appears in a chest by the Maku tree in the first game, after the game is completed.

### Hero's Cave Ring
**Original:** The Hero's Cave is a special dungeon that only appears when playing a Linked game. The Hero's Cave reward
is different, depending on if your linked game is Ages or Seasons.

**ROMHack:** The Hero's cave is available in both games (even a non-linked game). Since the cave exists in a reduced form
in a non-linked Oracle of Seasons game, a new entrance is added for the special dungeon (near its vanilla placement).

### Inaccessible Oracle of Ages Map Square
**Original:** A single square of the map can never be reached in a non-linked Oracle of Ages game.

**ROMHack:** The square is now reachable whether or not Ages is played as a linked game.

### Ring Secret Quests 
**Original:** A linked game provides 10 secret quests with various rewards. Among these rewards are two rings
in each game (a total of four) that cannot be obtained in the other game.

**ROMHack:** A secret quest that would award one of these rings, now awards both.  
* Note: This does mean that, depending on your order of play, you will only ever seen 10 of the 20 possible secret quests.

### Victory Ring
**Original:** The Victory Ring is a special ring that can only be obtained after defeating Ganon in a linked game, and then
starting a fresh playthrough with the Hero's Secret password.

**ROMHack:** Completing a linked game now offers a completion save (just like a non-linked game does), allowing for
post-game play. During the post-game of a linked game, the world uses appropriate "peaceful" dialogue, and the Victory
Ring can be claimed by visiting Vasu.

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

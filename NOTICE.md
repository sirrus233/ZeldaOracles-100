# Provenance and license scope

Original project tools, tests, documentation and original implementation changes
are provided under MIT. This grant covers only rights the contributors can grant.
It does not confer rights to the underlying games or copied upstream content.

- The Legend of Zelda: Oracle of Ages and Oracle of Seasons are Nintendo/Capcom
  games. This is an unofficial fan modification and is not endorsed by them.
- Source deltas target [Stewmath/oracles-disasm](https://github.com/Stewmath/oracles-disasm)
  at the revision recorded in `src/upstream.json`. The supplied upstream archive
  has no top-level license file. Its content is not relicensed by this project.
  Developers obtain it separately; the public repository contains our deltas,
  including limited upstream context needed to apply them.
- [PyBoy](https://github.com/Baekalfen/PyBoy) 2.9.0 declares
  [LGPL-3.0-only](https://pypi.org/project/pyboy/2.9.0/).
  PyBoy and its dependencies are not bundled. Developers install them separately
  to run emulator tests; players do not need them to apply a patch.
- [WLA-DX](https://github.com/vhelin/wla-dx) is an external build dependency.
  No assembler/linker executables are included.

No game ROMs, save files, save states, full disassembly trees, game screenshots,
Python environments, or third-party binaries are included in the public tree.
The BPS files are game modifications, not standalone games, and require matching
retail input ROMs supplied locally by the player.

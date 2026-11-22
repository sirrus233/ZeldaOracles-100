# Contributing

Start with docs/DEVELOPING.md and docs/DESIGN.md. Players should use the BPS
downloads; contributors prepare the pinned disassembly locally and supply their
own matching retail inputs for testing.

Keep source changes reviewable in `src/changes.patch`, with matching affected-file
hashes in `src/upstream.json`. Do not vendor the prepared source tree. Original
contributions use the MIT license; copied upstream context retains its separate
provenance and is not relicensed by this project.

For a change, explain:

- The player-visible trigger and resulting behavior in each affected game/order.
- Which flags, NPC roles, saved fields, ROM banks or graphics regions are affected.
- How pre-completion, post-completion, cancellation, repetition and save/reload
  behave, including any deliberate narrative or usability differences.
- The tests run, exact output hashes and remaining coverage gaps.

Use `--development` for local builds/tests while intentionally changing the code.
Update public patches and validation records together only after reviewing the
new behavior. An old passing report is evidence only for its recorded ROM bytes.
Fresh space checks matter: some script banks have very little free space.

Run the ROM-free publication checks before submitting. Full emulator tests run
locally; public CI cannot reproduce them without private game inputs. Keep ROMs,
saves, states, generated game images and third-party environments out of commits.

For bugs, include game/order, release or patch hash, emulator/version, progression
state, precise reproduction steps and whether a battery-save reload reproduces
the problem. Do not attach a ROM.

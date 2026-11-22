# Development setup

Players only need the BPS patches. Development additionally needs Python 3.12,
WLA-DX 10.6, the pinned upstream archive, and privately supplied retail ROMs for
testing and patch verification. No dependency, ROM or upstream archive is fetched
automatically. The tools do not install anything.

## 1. Obtain dependencies separately

Install Python dependencies into a project-local virtual environment if needed:

```sh
python -m venv .venv
# Activate that environment using your platform's normal activation command.
python -m pip install --no-cache-dir --disable-pip-version-check -r requirements-test.txt
```

`requirements-build.txt` suffices for building. The test requirements pin the
versions used for the emulator checks. WLA-DX is separately obtained from
[its upstream project](https://github.com/vhelin/wla-dx); provide its binary
directory with `--wla-dir` or put `wla-gb` and `wlalink` on PATH.

For a fully contained environment, put temporary/cache directories under `.local/`
before running dependency installers. The project tools themselves redirect
temporary, cache and AppData variables into `.local/scratch/`. They never invoke
pip, an installer or a network downloader.

## 2. Prepare the pinned disassembly

Download the archive URL recorded in `src/upstream.json` from upstream. Use that
exact commit, not a moving branch archive. Keep the downloaded ZIP under `.local/`:

```sh
python -B tools/prepare_source.py --archive .local/oracles-disasm.zip
```

The preparer verifies the archive's commit marker, affected-file input hashes,
patch context and resulting hashes. It refuses to overwrite an existing source
tree. It extracts into ignored `.local/source/`, then applies `src/changes.patch`.
If preparation fails, inspect the error and move the failed local source aside
before retrying; no automatic recursive deletion is performed.

## 3. Build and compare the release

```sh
python -B tools/build.py --wla-dir /path/to/wla-dx-binaries
```

On Windows the directory may contain `wla-gb.exe` and `wlalink.exe`. On other
platforms the tools may have no extension. The build recipe uses Python rather
than requiring a POSIX shell. WLA-DX's version affects output; use 10.6.

The build creates only local outputs and checks that both ROM SHA1 values match
the release manifest. A mismatch stops the command. With intentional source
changes, use `--development` to finish building both games without asserting a
release match. This prints the differing games and does not update any release
artifact. Review the change and test it before updating the manifest; do not use
this option to dismiss an unexplained mismatch.

## 4. Import private test inputs and run tests

```sh
python -B tools/import_roms.py --ages /path/to/ages.gbc --seasons /path/to/seasons.gbc
python -B tools/test.py
```

Inputs are hash-checked before being copied into ignored `.local/roms/`. The
runner validates the current build/input hashes, stages the current BPS files
locally and runs the 22 source regression suites. Two transfer phases run
sequentially after the independent tests. Logs and exact ROM hashes are under
`.local/test-results/`; generated fixtures/screenshots stay under `.local/`.

For focused checks:

```sh
python -B tools/test.py --suite heart --suite ring-quests
python -B tools/test.py --suite native-book --suite paired-transfer
```

There is no dependency on the original author's workspace, desktop paths, saved
test checkpoints or bundled Python installation. The tests create prepared saves
from locally supplied ROMs. The old private verification-package launchers and
historical prototype-generation scripts are deliberately not part of this repo.

## Editing the source delta

Edit the ignored prepared source while developing. Build with `--development`,
then run `python -B tools/test.py --development` to test those local edits. The
test runner still checks retail input hashes, but generates matching BPS files
only under `.local/outputs/`; it does not replace the public release or its
validation reports. The result records the actual development ROM hashes.

For publication, regenerate
the unified delta against a clean copy of the pinned archive, including the one
added graphics source file, and update its before/after hash manifest. Keep the
patch paths relative (`a/...` and `b/...`). The manifest/preparer intentionally
reject stale or mismatched changes. Review ROM-bank capacity and graphics
allocations along with functional changes. See TESTING.md and RELEASING.md.

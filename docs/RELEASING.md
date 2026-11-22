# Publishing and maintaining releases

This folder is the repository root. Initialize Git here, review the files, and
push it to the GitHub repository you choose. No remote or author identity is
preconfigured. Committing and pushing remain manual; pushing a version tag
publishes a release automatically after the public checks pass.

From this folder, a typical first publication starts with:

```sh
git init
git add .
python -B tools/check_public_tree.py
git status --short
git commit -m "Initial public patches, source and tests"
```

Then add the GitHub remote you own and push. Review the staged files before the
commit; initialize in this clean repository folder, not a parent workspace.

## Automatic GitHub releases

Commit and push the current repository, then tag that exact commit and push the
tag. For example, from a clean working tree:

```sh
git tag -a v0.1.0 -m "Oracle 100 Percent v0.1.0"
git push origin v0.1.0
```

The workflow runs the public checks on branch/tag pushes and pull requests.
Only a pushed tag beginning with `v` publishes a release, and only after those
checks pass. The release contains both individual BPS patches, the player ZIP,
SHA256SUMS and the manifest. The ZIP includes its own player README. Release
notes also link to the tagged version's player guide.

Tags containing a hyphen, such as `v0.1.0-beta.1`, publish as prereleases.
Ordinary branch pushes and pull requests do not publish. The workflow uses
GitHub's built-in token; no personal access token is required. Only the release
job receives `contents: write` permission. Repository or organization policies
must permit that permission and GitHub Actions.

Use a new tag for each release. Rerunning an already-published tag does not
overwrite its release or assets; release creation will fail because it exists.
The workflow packages the committed patches and does not build ROMs or run the
ROM-dependent emulator suite. Complete local gameplay validation before tagging.

## Manual packaging

To make the player ZIP locally instead:

```sh
python -B tools/check_public_tree.py
python -B -m unittest discover -s tests/unit -v
python -B tools/make_release.py
```

Upload `dist/Oracle-100-Percent-Patches.zip` as a release asset. The archive
contains only the two patches, player instructions, checksums, manifest and
notice. `dist/` is ignored; the generated player ZIP need not be committed.
The archive tool refuses to overwrite a previous release ZIP.

The public repository keeps `patches/*.bps` committed so visitors can download
without a release page. Choose a new tag/version when you publish and update the
changelog for that release. Do not label the export as a fully tested
end-to-end 100% playthrough.

## What belongs in Git

- The two current BPS patches and input/output/patch checksums.
- Source deltas, pinned upstream revision and affected-file hashes.
- Original build/test utilities, regression code, documentation and sanitized facts.
- MIT license for original contributions and separate provenance notices.

## What stays private or external

- Retail or patched ROMs, symbols, object files, full upstream sources/assets.
- Battery saves, save states, generated screenshots and raw emulator evidence.
- Python environments, PyBoy and dependencies, WLA-DX binaries and downloaded ZIPs.
- Personal workspace notes, machine paths, older patch experiments and local play saves.

The exporter has kept these out of the publication folder. Future development
places them under ignored `.local/` or `.venv/`. Do not force-add those directories.
The publication checker also inspects tracked files when run inside a Git repo,
so a force-added ignored file can be caught before publication.

## Changing the release

For a new patch, regenerate BPS files from the matching retail inputs and newly
built ROMs, using `tools/bps.py`'s original project writer. Update the manifest,
SHA256SUMS, source delta/hash manifest and changelog together. Re-run appropriate
emulator checks and review narrative/usability and graphics/bank risks; then
record the exact new hashes and evidence. Old validation facts apply only to
their recorded ROM bytes and must not be presented as evidence for changed bytes.

Do not upload ROMs to GitHub Actions. The included workflow deliberately runs
only ROM-free checks. Full emulator tests run locally with separately supplied
game files and dependencies.

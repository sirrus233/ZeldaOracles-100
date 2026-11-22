# Source layout

`changes.patch` contains the cumulative assembly/text changes and the additional
chest-graphics assembly source. It is not a patch for a game ROM; players use
the BPS files in `patches/`.

`upstream.json` identifies the exact disassembly archive and records raw original
file hashes and normalized UTF-8/LF resulting file hashes. Sixty-three existing
files are changed and one file is added. The preparer verifies these rather than
applying a patch with guessed offsets or fuzz.

Obtain upstream separately, then use `tools/prepare_source.py` as documented in
`docs/DEVELOPING.md`. The public repository deliberately does not vendor the
entire upstream disassembly or its game assets. Its licensing is separate from
the MIT grant for original project contributions; see NOTICE.md.

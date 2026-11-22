"""Apply the checked-in cumulative BPS patch to a matching retail ROM."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
from layout import REPO
from bps import apply_patch

def apply(game, rom, output):
    entry=json.loads((REPO/'patches/manifest.json').read_text())['games'][game]
    if output.exists():raise ValueError('Output already exists; choose a new filename')
    base=rom.read_bytes()
    if sha256(base).hexdigest()!=entry['source_sha256']:
        raise ValueError('Wrong ROM revision; compare patches/manifest.json')
    patch=(REPO/entry['patch']).read_bytes()
    if sha256(patch).hexdigest()!=entry['patch_sha256']:raise ValueError('Patch checksum mismatch')
    result=apply_patch(patch,base)
    if sha256(result).hexdigest()!=entry['target_sha256']:raise ValueError('Output checksum mismatch')
    output.parent.mkdir(parents=True,exist_ok=True);output.write_bytes(result)
    print(f'Patched {game}: {output}')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('game',choices=('ages','seasons'))
    parser.add_argument('rom',type=Path);parser.add_argument('output',type=Path)
    args=parser.parse_args()
    apply(args.game,args.rom,args.output)

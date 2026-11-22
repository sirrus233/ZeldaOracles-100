"""Prepare the exact upstream archive locally, then apply the reviewed delta."""
import argparse
from hashlib import sha256
import json
from pathlib import Path, PurePosixPath
import zipfile
from layout import REPO, SOURCE, LOCAL, local_environment
from source_patch import apply_directory

def prepare(archive):
    spec = json.loads((REPO/'src/upstream.json').read_text())
    if SOURCE.exists(): raise ValueError('Source already exists; use a fresh checkout or move .local/source aside')
    with zipfile.ZipFile(archive) as z:
        if z.comment.decode('ascii') != spec['commit']: raise ValueError('Wrong upstream archive commit')
        entries = {}
        for info in z.infolist():
            if info.is_dir(): continue
            name = '/'.join(info.filename.split('/')[1:])
            path = PurePosixPath(name)
            if not name or path.is_absolute() or '..' in path.parts or '\\' in name or ':' in name:
                raise ValueError('Unsafe archive path')
            if (info.external_attr>>16)&0o170000 == 0o120000: raise ValueError('Archive contains a symlink')
            if name in entries: raise ValueError('Duplicate archive path')
            entries[name] = info
        for name, hashes in spec['changed_files'].items():
            before = hashes['before_sha256']
            if before is not None and sha256(z.read(entries[name])).hexdigest()!=before:
                raise ValueError(f'Upstream content mismatch: {name}')
        for name, info in entries.items():
            dest = SOURCE/name; dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(z.read(info))
    apply_directory(SOURCE,(REPO/'src/changes.patch').read_text(encoding='utf-8'))
    for name, hashes in spec['changed_files'].items():
        if sha256((SOURCE/name).read_bytes()).hexdigest()!=hashes['after_sha256']:
            raise ValueError(f'Patched source mismatch: {name}')
    print(f'Prepared {len(spec["changed_files"])} source changes at {SOURCE}')

if __name__=='__main__':
    local_environment()
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive',required=True,type=Path)
    args=parser.parse_args()
    prepare(args.archive)


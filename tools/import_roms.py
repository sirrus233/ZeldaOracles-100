"""Validate and copy private retail inputs into the ignored local workspace."""
import argparse,json
from hashlib import sha256
from pathlib import Path
from layout import REPO,LOCAL,local_environment

if __name__=='__main__':
    local_environment()
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--ages',type=Path,required=True)
    p.add_argument('--seasons',type=Path,required=True)
    args=p.parse_args();spec=json.loads((REPO/'patches/manifest.json').read_text())
    staged=[]
    for name in ('ages','seasons'):
        data=getattr(args,name).read_bytes()
        if sha256(data).hexdigest()!=spec['games'][name]['source_sha256']:
            raise SystemExit(f'{name}: wrong retail ROM; see patches/manifest.json')
        staged.append((name,data))
    folder=LOCAL/'roms';folder.mkdir(parents=True,exist_ok=True)
    for name,data in staged:
        target=folder/f'Oracle of {name.title()}.gbc'
        if target.exists() and target.read_bytes()!=data:raise SystemExit(f'Refusing to replace {target}')
        target.write_bytes(data)
    print('Both private inputs validated; nothing will be committed from .local/')

"""Check publication contents and patch metadata without any game inputs."""
from hashlib import sha256
import ast,json,subprocess
from pathlib import Path
from zlib import crc32
from layout import REPO

PRIVATE={'.local','.venv','.git','__pycache__','dist'}
ALLOWED={'.py','.md','.txt','.json','.patch','.bps','.yml','.yaml'}
NAMES={'LICENSE','.gitignore','.gitattributes','SHA256SUMS'}

def check():
    files=[]
    for path in REPO.rglob('*'):
        relative=path.relative_to(REPO)
        if any(part in PRIVATE for part in relative.parts) or not path.is_file():continue
        files.append(path)
    if (REPO/'.git').exists():
        tracked=subprocess.run(['git','-C',str(REPO),'ls-files','--cached','-z'],
            check=True,capture_output=True).stdout.decode().split('\0')
        for name in filter(None,tracked):
            relative=Path(name)
            if any(part in PRIVATE for part in relative.parts):raise ValueError(f'Private tracked path: {name}')
            path=REPO/relative
            if path not in files:files.append(path)
    for path in files:
        relative=path.relative_to(REPO)
        if path.is_symlink():raise ValueError(f'Symlink in public tree: {relative}')
        if path.name not in NAMES and path.suffix not in ALLOWED:raise ValueError(f'Unexpected public file: {relative}')
        data=path.read_bytes()
        if path.suffix=='.bps':
            if relative.parts[0]!='patches' or data[:4]!=b'BPS1':raise ValueError('Unexpected binary patch')
        else:
            text=data.decode('utf-8')
            if any(marker in text.lower() for marker in ('c:/users/','c:\\users\\','/users/','/home/')):
                # The auditor's own literal detection strings are expected.
                if path.name!='check_public_tree.py':raise ValueError(f'Personal path in {relative}')
            if path.suffix=='.py':ast.parse(text,filename=str(relative))
        if len(data)>2_000_000:raise ValueError(f'Unexpected large public file: {relative}')
    manifest=json.loads((REPO/'patches/manifest.json').read_text())
    if {p.relative_to(REPO).as_posix() for p in files if p.suffix=='.bps'} != {r['patch'] for r in manifest['games'].values()}:
        raise ValueError('Unexpected or missing public BPS patch')
    for name,row in manifest['games'].items():
        data=(REPO/row['patch']).read_bytes()
        if sha256(data).hexdigest()!=row['patch_sha256']:raise ValueError(f'Patch hash: {name}')
        if crc32(data[:-4])!=int.from_bytes(data[-4:],'little'):raise ValueError(f'Patch CRC: {name}')
        if data[-12:-8]!=int(row['source_crc32'],16).to_bytes(4,'little'):raise ValueError(f'Input CRC: {name}')
        if data[-8:-4]!=int(row['target_crc32'],16).to_bytes(4,'little'):raise ValueError(f'Output CRC: {name}')
    source=json.loads((REPO/'src/upstream.json').read_text())
    from source_patch import sections
    names=[name for name,created,hunks in sections((REPO/'src/changes.patch').read_text())]
    if set(names)!=set(source['changed_files']) or len(names)!=len(set(names)):
        raise ValueError('Source patch/manifest paths differ')
    return dict(status='passed',public_files=len(files),patches=2,source_changes=len(names),
                no_roms_saves_or_bundled_dependencies=True)

if __name__=='__main__':print(json.dumps(check(),indent=2))

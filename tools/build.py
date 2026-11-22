"""Build both patched Oracle ROMs with a portable WLA-DX recipe."""

from hashlib import sha1
import os
from pathlib import Path
from shutil import copyfile
import subprocess
import sys


from layout import REPO, SOURCE, SCRATCH, LOCAL, local_environment
WLA_GB = None
WLALINK = None


def run_python_recipe(script, arguments):
    old_argv = sys.argv
    old_path = sys.path.copy()
    try:
        sys.argv = [script.as_posix(), *(value.as_posix() if isinstance(value, Path) else value for value in arguments)]
        sys.path.insert(0, str(script.resolve().parent))
        exec(compile(script.read_bytes(), str(script), 'exec'), {
            '__name__': '__main__', '__file__': str(script.resolve()),
        })
    finally:
        sys.argv = old_argv
        sys.path[:] = old_path


def build(game):
    build_dir = Path(f'build_{game}_v')
    for folder in ('gfx', 'rooms', 'tileset_layouts'):
        (build_dir / folder).mkdir(parents=True, exist_ok=True)

    for folder, source in (
        ('rooms', Path('precompressed/rooms') / game),
        ('tileset_layouts', Path('precompressed/tileset_layouts') / game),
        ('gfx', Path('precompressed/gfx_compressible/common')),
        ('gfx', Path('precompressed/gfx_compressible') / game),
        ('.', Path('precompressed/text') / game),
    ):
        for asset in source.iterdir():
            if asset.is_file():
                copyfile(asset, build_dir / folder / asset.name)

    for filename in sorted((Path('rooms') / game / 'small').glob('*.bin')):
        destination = build_dir / 'rooms' / filename.with_suffix('.cmp').name
        if not destination.exists():
            run_python_recipe(Path('tools/build/compressRoomLayout.py'), (filename, destination))

    run_python_recipe(Path('tools/build/parseText.py'), (
        Path('text') / game / 'dict.yaml', Path('text') / game / 'text.yaml',
        build_dir / 'textData.s', str(0x74000 if game == 'ages' else 0x71C00),
    ))

    for directory in (Path('gfx/common'), Path('gfx') / game):
        for filename in sorted(directory.iterdir()):
            if filename.suffix not in ('.bin', '.png'):
                continue
            destination = build_dir / 'gfx' / filename.with_suffix('.cmp').name
            if filename.suffix == '.png':
                binary = destination.with_suffix('.bin')
                run_python_recipe(Path('tools/gfx/gfx.py'), ('--out', binary, 'auto', filename))
            else:
                binary = filename
            payload = binary.read_bytes()
            destination.write_bytes(b'\0' + len(payload).to_bytes(2, 'little') + payload)

    for asm, obj in ((Path(game + '.s'), game), (Path('code/audio.s'), 'audio')):
        subprocess.run([
            WLA_GB, '-o', build_dir / (obj + '.o'),
            '-D', 'BUILD_VANILLA', '-D', 'ROM_' + game.upper(),
            '-D', f'BUILD_DIR="{build_dir.as_posix()}/"', asm,
        ], check=True)
    linkfile = build_dir / 'linkfile'
    linkfile.write_bytes(Path('linkfile_' + game).read_bytes().replace(b'BUILD_DIR', build_dir.as_posix().encode()))
    rom = Path(game + '.gbc')
    subprocess.run([WLALINK, '-S', linkfile, rom], check=True)
    print(f'{rom}: {sha1(rom.read_bytes()).hexdigest()}', flush=True)


def main():
    import argparse,json
    from shutil import which,copytree,ignore_patterns
    from source_patch import apply_directory
    local_environment()
    parser=argparse.ArgumentParser(description='Build the patched disassembly with WLA-DX 10.6')
    parser.add_argument('--wla-dir',type=Path,help='Directory with wla-gb and wlalink (or .exe)')
    parser.add_argument('--development',action='store_true',help='Build intentional edits without claiming a release hash match')
    args=parser.parse_args()
    def executable(name):
        if args.wla_dir:
            for suffix in ('','.exe'):
                path=args.wla_dir.resolve()/(name+suffix)
                if path.is_file():return str(path)
            raise SystemExit(f'Missing {name} in --wla-dir')
        found=which(name)
        if not found:raise SystemExit(f'Missing {name}; provide --wla-dir or add WLA-DX to PATH')
        return found
    global WLA_GB,WLALINK
    WLA_GB=executable('wla-gb');WLALINK=executable('wlalink')
    source=SOURCE
    if not source.is_dir():raise SystemExit('Run tools/prepare_source.py first')
    os.chdir(source)
    expected=json.loads((REPO/'patches/manifest.json').read_text())
    changed=[]
    for game in ('ages','seasons'):
        build(game)
        actual=sha1(Path(game+'.gbc').read_bytes()).hexdigest()
        if actual!=expected['games'][game]['target_sha1']:
            if not args.development:raise SystemExit(f'{game}: build differs from release manifest: {actual}')
            changed.append(game)
    if changed:print('Development output differs from the release manifest: '+', '.join(changed))
    else:print('Both ROMs match the expected hashes')

if __name__=='__main__':
    # Upstream recipes execute in this interpreter and read UTF-8 game text.
    # An environment variable alone cannot change an already-started interpreter.
    if not sys.flags.utf8_mode:
        raise SystemExit(subprocess.call([sys.executable,'-X','utf8','-B',str(Path(__file__).resolve()),*sys.argv[1:]]))
    main()

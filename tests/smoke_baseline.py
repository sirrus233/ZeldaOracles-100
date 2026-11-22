"""Compare the boot and file-selection traces of rebuilt and retail ROMs."""

from hashlib import sha256
from io import BytesIO
import os
from pathlib import Path
import sys
from time import perf_counter


from repo_paths import ROOT, SCRATCH, SOURCE


def trace(rom, menu_mode):
    emulator = PyBoy(BytesIO(rom.read_bytes()), window='null', sound_volume=0)
    emulator.set_emulation_speed(0)
    try:
        emulator.tick(900, True)
        result = [snapshot(emulator, menu_mode)]
        for _ in range(2):
            emulator.button('start')
            emulator.tick(120, True)
            result.append(snapshot(emulator, menu_mode))
        return result
    finally:
        emulator.stop(save=False)


def snapshot(emulator, menu_mode):
    return emulator.memory[menu_mode], sha256(emulator.screen.ndarray.tobytes()).hexdigest()


if __name__ == '__main__':
    SCRATCH.mkdir(exist_ok=True)
    for variable in ('TMP', 'TEMP', 'TMPDIR', 'APPDATA', 'LOCALAPPDATA', 'XDG_CACHE_HOME'):
        os.environ[variable] = str(SCRATCH)
    from pyboy import PyBoy

    for game in ('ages', 'seasons'):
        retail, = (ROOT / 'roms').glob(f'*Oracle of {game.title()}*.gbc')
        mode_address, = (line.split()[0].split(':')[1] for line in
                         (SOURCE / f'{game}.sym').read_text().splitlines()
                         if line.endswith(' wFileSelect.mode'))
        start = perf_counter()
        retail_trace = trace(retail, int(mode_address, 16))
        rebuilt_trace = trace(SOURCE / f'{game}.gbc', int(mode_address, 16))
        assert retail_trace == rebuilt_trace, (game, retail_trace, rebuilt_trace)
        assert len({screen for _, screen in retail_trace}) == len(retail_trace), (game, retail_trace)
        print(f'{game}: retail and rebuilt boot/input traces match in {perf_counter() - start:.2f}s', flush=True)

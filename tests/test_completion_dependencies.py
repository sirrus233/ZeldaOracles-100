"""Boundary tests for completion dependencies; prepared inputs, real game reward code.

Password generation is an explicit native-function unit boundary, in a separate
emulator. Password entry and rewards are exercised with normal controller input.
No executable ROM changes or reward/completion flag injection occur during actions.
"""
from io import BytesIO
from pathlib import Path
import json
import os
import sys

import test_postgame_chest as chest
from emit_heart_patches import PROJECT, SOURCE, apply_patch
from test_postgame_chest import Game, ROOT, SCRATCH
from test_heros_cave import load, walk, room, position, retail_rom
from test_ring_quests import quest_save, choose, continue_text, finish_conversation, flag, enter_password
from test_victory_ring import update_save, SHOPS

OUT = PROJECT / 'outputs' / 'Postgame Verification' / 'audit'
OUT.mkdir(parents=True, exist_ok=True)
RESULTS = []


def record(label, **details):
    RESULTS.append(dict(test=label, status='passed', **details))
    (OUT / 'dependency-results.json').write_text(json.dumps(RESULTS, indent=2))
    print(label, details, flush=True)


def generate(game, sram, kind, index=0):
    """Invoke the ROM's codec in isolation, without pretending to complete a quest."""
    with game.boot(sram) as emulator:
        game.press(emulator, 'a')
        game.press(emulator, 'a', 180)
        emulator.memory[game.address['wShortSecretIndex']] = index
        # Native codec returns into a small test-only RAM wait loop. This isolated
        # emulator is discarded; its SRAM is never used as an acquisition result.
        emulator.memory[0xC300:0xC303] = [0xC3, 0, 0xC3]  # jp $c300
        registers = emulator.register_file
        registers.SP = 0xC2B0
        emulator.memory[0xC2B0:0xC2B2] = [0, 0xC3]
        registers.B = 0
        registers.C = kind
        registers.PC = game.address['secretFunctionCaller']
        emulator.tick(3, False)
        assert registers.PC == 0xC300, ('native codec did not return', hex(registers.PC))
        length = {0: 20, 2: 15, 3: 5}[kind]
        start = game.address['w7SecretText1']
        password = bytes(emulator.memory[7, start:start + length])
        assert 0 not in password, password
        return password


def farore_save(game, base, *, finished, index=None, begun=True, hearts=15):
    location = (4, 0xE8, 0x49, 0x58) if game.name == 'seasons' else (5, 0xCF, 0x49, 0x58)
    first_flag = 0x50 if game.name == 'ages' else 0x64
    data = quest_save(game, base, location, linked=True, finished=finished,
                      flags=(first_flag + index,) if begun and index is not None else (),
                      treasures=(0x2C,))
    return update_save(game, data, [('wLinkMaxHealth', hearts * 4, 0),
                                   ('wLinkHealth', hearts * 4, 0),
                                   ('wSwordLevel', 2, 0), ('wShieldLevel', 2, 0),
                                   ('wRingBoxLevel', 2, 0), ('wObtainedRingBox', 1, 0),
                                   ('wMaxBombs', 0x30, 0), ('wSeedSatchelLevel', 2, 0)]), location


def talk_farore(game, emulator):
    walk(game, emulator, 'up', 15)
    game.press(emulator, 'a', 100)
    try:
        choose(game, emulator, 0)
    except AssertionError:
        game.screenshot(emulator, 'audit-farore-no-talk')
        print('actors', [(hex(slot), list(emulator.memory[slot:slot+3]), emulator.memory[slot+0xB], emulator.memory[slot+0xD]) for slot in range(0xD040, 0xE000, 0x100) if emulator.memory[slot]], flush=True)
        raise
    continue_text(game, emulator, lambda: game.read(emulator, 'wOpenedMenuType') == 6)


def farore_return(game, base, index, *, finished, begun=True):
    sram, location = farore_save(game, base, finished=finished, index=index, begun=begun)
    password = generate(game, sram, 3, (0x30 if game.name == 'ages' else 0x10) + index)
    done = (0x5A if game.name == 'ages' else 0x6E) + index
    with game.boot(sram) as emulator:
        load(game, emulator, location)
        talk_farore(game, emulator)
        enter_password(game, emulator, password)
        if not begun:
            finish_conversation(game, emulator)
            assert not flag(game, emulator, done)
            assert game.read(emulator, 'wLinkMaxHealth') == 60
        else:
            for _ in range(90):
                if flag(game, emulator, done):
                    break
                if index in (1, 2, 3, 6, 8) and flag(game, emulator, 0x2C):
                    # Farore's chest is tile $75; approach from below normally.
                    finish_conversation(game, emulator)
                    game.move_to(emulator, 'x', 0x78, 'left', 'right')
                    walk(game, emulator, 'down', 50)
                    game.move_to(emulator, 'y', 0x89, 'up', 'down')
                    game.move_to(emulator, 'x', 0x58, 'left', 'right')
                    walk(game, emulator, 'up', 10)
                game.press(emulator, 'a', 90)
            else:
                game.screenshot(emulator, 'audit-farore-stuck')
                raise AssertionError((game.name, 'Farore reward did not finish', index, finished, position(game, emulator)))
            expected = {0: ('wSwordLevel', 3), 1: ('wLinkMaxHealth', 64),
                        2: ('wNumBombchus', 0x10), 4: ('wShieldLevel', 3),
                        5: ('wMaxBombs', 0x50), 7: ('wSeedSatchelLevel', 3),
                        9: ('wRingBoxLevel', 3)}
            if index in expected:
                symbol, value = expected[index]
                assert game.read(emulator, symbol) == value, (game.name, index, symbol, game.read(emulator, symbol), value)
            elif index in (3, 6):
                ring = {('ages', 3): 0x15, ('ages', 6): 0x13,
                        ('seasons', 3): 0x2F, ('seasons', 6): 0x21}[game.name, index]
                assert game.read(emulator, 'wNumUnappraisedRingsBcd') == 1
                assert game.read(emulator, 'wUnappraisedRings') & 0x3F == ring
            else:
                assert emulator.memory[game.address['wObtainedTreasureFlags'] + 0x0C // 8] & (1 << (0x0C % 8))
            finish_conversation(game, emulator)
            game.screenshot(emulator, f'audit-farore-{index}-{finished}')
            saved = game.save_from_menu(emulator)
        if not begun:
            saved = game.save_from_menu(emulator)
    with game.boot(saved) as emulator:
        game.press(emulator, 'a')
        game.press(emulator, 'a', 180)
        assert flag(game, emulator, done) == begun
    record('Farore return password', game=game.name, index=index, postgame=finished, begun=begun)


if __name__ == '__main__':
    for variable in ('TMP', 'TEMP', 'TMPDIR', 'APPDATA', 'LOCALAPPDATA', 'XDG_CACHE_HOME'):
        os.environ[variable] = str(SCRATCH)
    from pyboy import PyBoy
    chest.PyBoy = PyBoy
    for name in ('ages', 'seasons'):
        game = Game(name)
        assert game.rom == apply_patch((PROJECT / 'outputs' / f'Oracle of {name.title()} - 100 Percent.bps').read_bytes(), retail_rom(name))
        base = game.new_file()
        for finished in (False, True):
            for index in (range(10) if '--all' in sys.argv else (1,)):
                farore_return(game, base, index, finished=finished)
        farore_return(game, base, 1, finished=True, begun=False)

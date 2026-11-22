"""Compare the four recipients with retail at their earlier story stages."""

import os
import sys

import test_postgame_chest as chest
from test_heros_cave import load, retail_rom, walk
from test_postgame_chest import Game, ROOT, SCRATCH
from test_ring_quests import continue_text, finish_conversation, quest_save


def test_flippers():
    game = Game('seasons')
    base = game.new_file()
    location = (5, 0xBD, 0x48, 0xC8)
    sram = quest_save(game, base, location, linked=True, finished=False, essences=7,
                      equipped=False, treasures=(0x54,))
    for rom in (retail_rom('seasons'), game.rom):
        game.rom = rom
        with game.boot(sram) as emulator:
            load(game, emulator, location)
            assert sum(bool(emulator.memory[slot]) and emulator.memory[slot + 1] == 0x8D
                       for slot in range(0xD040, 0xE000, 0x100)) == 1
            walk(game, emulator, 'up', 48)
            game.press(emulator, 'a', 100)
            flippers = game.address['wObtainedTreasureFlags'] + 0x2E // 8
            continue_text(game, emulator, lambda: emulator.memory[flippers] & (1 << (0x2E % 8)))
            finish_conversation(game, emulator)
    print('Normal linked Seasons Flippers award passed in retail and patched ROMs.', flush=True)


def snapshot(game, sram, location, ids, *, direction='up'):
    with game.boot(sram) as emulator:
        load(game, emulator, location)
        actors = sorted((emulator.memory[slot + 1], emulator.memory[slot + 2],
                         emulator.memory[slot + 11], emulator.memory[slot + 13])
                        for slot in range(0xD040, 0xE000, 0x100)
                        if emulator.memory[slot] and emulator.memory[slot + 1] in ids)
        walk(game, emulator, direction, 48)
        game.press(emulator, 'a', 200)
        text = None
        if game.read(emulator, 'wTextIsActive'):
            text = (game.read(emulator, 'wTextIndexH_backup'),
                    emulator.memory[7, game.address['w7TextIndexL_backup']],
                    emulator.screen.ndarray[104:144, 8:152].tobytes())
        return actors, text


if __name__ == '__main__':
    for variable in ('TMP', 'TEMP', 'TMPDIR', 'APPDATA', 'LOCALAPPDATA', 'XDG_CACHE_HOME'):
        os.environ[variable] = str(SCRATCH)
    from pyboy import PyBoy
    chest.PyBoy = PyBoy
    if '--story-only' not in sys.argv:
        test_flippers()
    if '--flippers-only' in sys.argv:
        sys.exit(0)

    for name, location, ids, stages in (
        ('seasons', (1, 0xB6, 0x30, 0x68), (0x8B, 0xCD),
         ((False, 0, (), ()), (False, 7, (), ()), (False, 15, (), ()),
          (False, 255, (), ()), (True, 255, (), ()))),
        ('seasons', (1, 0xAD, 0x40, 0x50), (0xD5,),
         ((False, 0, (), ()), (False, 255, (), ()), (True, 255, (), ()))),
        ('ages', (3, 0xF8, 0x60, 0x70), (0xCC,),
         ((False, 0, (), ()), (False, 63, (0x11,), ()), (True, 255, (), ()))),
        ('ages', (2, 0xE7, 0x3A, 0x48), (0x53,),
         ((False, 0, (), ()), (False, 63, (), ((0, 0xE7, 0x20),)),
          (True, 255, (), ()), (True, 255, (), ((0, 0xE7, 0x20),)))),
    ):
        game = Game(name)
        base = game.new_file()
        patched = game.rom
        for finished, essences, flags, room_flags in stages:
            # The Diver intentionally returns home after a linked ending.
            # Other affected NPCs retain native roles even after Ganon.
            if finished and name == 'seasons' and location[1] == 0xB6:
                continue
            sram = quest_save(game, base, location, linked=True, finished=finished,
                              essences=essences, flags=flags, room_flags=room_flags, equipped=False)
            game.rom = retail_rom(name)
            original = snapshot(game, sram, location, ids)
            game.rom = patched
            actual = snapshot(game, sram, location, ids)
            assert actual == original, (name, location, finished, essences,
                                         actual[0], original[0], 'story behavior differs')
            if name == 'seasons' and location[1] == 0xB6 and not finished:
                assert not any(actor[0] == 0xCD for actor in actual[0]), 'secret receiver appeared before postgame'
            print(name, hex(location[1]), 'finished', finished, 'essences', hex(essences),
                  'matches retail', flush=True)

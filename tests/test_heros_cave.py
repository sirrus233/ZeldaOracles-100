"""Regression checks for the Hero's Cave entrances using saved games and controller input."""

import os
import sys

import test_postgame_chest as chest
from emit_heart_patches import PROJECT, apply_patch
from test_postgame_chest import Game, ROOT, SAVE_SLOT_COPIES, SAVE_SLOT_LENGTH, SCRATCH


ENTRANCES = {'ages': (0, 0x48, 0x38, 0x88), 'seasons': (0, 0xD4, 0x18, 0x48)}
SEASONS_LOWER_DOOR = (0, 0xD4, 0x68, 0x48)
CHALLENGE = {'ages': (4, 0xCE), 'seasons': (5, 0x30)}
BUNDLE = PROJECT / 'outputs' / 'Postgame Verification'


def fixture(game, base, location, *, early=False, equipped=False, **status):
    sram = game.fixture(base, 3 if early else 14, **status)
    primary = SAVE_SLOT_COPIES[0]
    saved = sram[primary:primary + SAVE_SLOT_LENGTH]
    def write(symbol, value, index=0):
        offset = game.address[symbol] - game.address['wFileStart'] + index
        saved[offset] = value

    for field, value in zip(('group', 'room', 'y', 'x'), location):
        write(f'wDeathRespawnBuffer.{field}', value)
    if early:
        write('wEssencesObtained', 0)
        write('wc6e5', 0)
    if equipped:
        gear = (0x03, 0x05, 0x15, 0x17, 0x19, 0x2E, *range(0x20, 0x25))
        if game.name == 'ages':
            gear += (0x04, 0x0A, 0x0F, 0x11, 0x16, 0x25, 0x26, 0x27, 0x4A)
        else:
            gear += (0x06, 0x07, 0x08, 0x13)
        offset = game.address['wObtainedTreasureFlags'] - game.address['wFileStart']
        for item in gear:
            saved[offset + item // 8] |= 1 << (item % 8)
        for symbol, value in (
            ('wSwordLevel', 1), ('wSeedSatchelLevel', 1), ('wNumBombs', 0x10),
            ('wMaxBombs', 0x10), ('wNumRupees', 0x50),
            ('wInventoryA', 0x05), ('wInventoryB', 0x17),
        ):
            write(symbol, value)
        for index, item in enumerate(item for item in gear if item < 0x20 and item not in (5, 0x17)):
            write('wInventoryStorage', item, index)
        for seed in ('Ember', 'Scent', 'Pegasus', 'Gale', 'Mystery'):
            write(f'wNum{seed}Seeds', 0x20)
        if game.name == 'ages':
            write('wSwitchHookLevel', 2)
            write('wBraceletLevel', 2)
            write('wSelectedHarpSong', 3)
        else:
            write('wBoomerangLevel', 2)
            write('wSlingshotLevel', 2)
            write('wFeatherLevel', 2)
            write('wObtainedSeasons', 0x0F)
            write('wGroup4RoomFlags', 0x20, 6)  # The wooden sword was already taken.
    checksum = sum(int.from_bytes(saved[i:i + 2], 'little') for i in range(2, len(saved), 2))
    saved[:2] = (checksum & 0xFFFF).to_bytes(2, 'little')
    for offset in SAVE_SLOT_COPIES:
        sram[offset:offset + SAVE_SLOT_LENGTH] = saved
    return sram


def room(game, emulator):
    return game.read(emulator, 'wActiveGroup'), game.read(emulator, 'wActiveRoom')


def load(game, emulator, location):
    game.press(emulator, 'a')
    game.press(emulator, 'a', 180)
    assert room(game, emulator) == location[:2], (game.name, room(game, emulator), location)


def retail_rom(name):
    path, = (ROOT / 'roms').glob(f'*Oracle of {name.title()}*.gbc')
    return path.read_bytes()


def walk(game, emulator, direction, frames=75):
    emulator.button_press(direction)
    emulator.tick(frames, False)
    emulator.button_release(direction)
    emulator.tick(45, True)


def position(game, emulator):
    return tuple(game.read(emulator, f'w1Link.{axis}h') for axis in ('y', 'x'))


def settle_entrance(game, emulator):
    emulator.tick(105, True)
    game.dismiss_pickup_text(emulator)
    emulator.tick(30, True)


def enter_seasons_door(game, emulator, *, shows_title):
    emulator.button_press('up')
    for _ in range(220):
        emulator.tick(1, False)
        if game.read(emulator, 'wTextIsActive'):
            break
        if not shows_title and game.read(emulator, 'wDeathRespawnBuffer.group') == 4:
            break
    emulator.button_release('up')
    emulator.tick(2, True)
    assert bool(game.read(emulator, 'wTextIsActive')) == shows_title, (
        'Seasons', room(game, emulator), 'unexpected entrance title', shows_title,
        position(game, emulator),
    )
    if shows_title:
        assert game.read(emulator, 'wTextIndexH_backup') == 2 + 4
        emulator.tick(95, True)
        game.screenshot(emulator, f'cave-title-{room(game, emulator)[0]}')
        game.dismiss_pickup_text(emulator)
    else:
        assert game.read(emulator, 'wDeathRespawnBuffer.room') == 4


def approach_upper_ledge(game, base):
    west = 0, 0xD3, 0x18, 0x90
    with game.boot(fixture(game, base, west, equipped=True)) as emulator:
        load(game, emulator, west)
        walk(game, emulator, 'right', 45)
        assert room(game, emulator) == ENTRANCES['seasons'][:2]
        game.move_to(emulator, 'y', 0x11, 'up', 'down')
        game.move_to(emulator, 'x', 0x30, 'left', 'right')
        game.move_to(emulator, 'x', 0x3B, 'left', 'right')
        game.press(emulator, 'a', 22)  # Clear the Octorok patrolling under the door.
        game.move_to(emulator, 'x', 0x48, 'left', 'right')
        game.screenshot(emulator, 'cave-upper-ledge-approach')
        enter_seasons_door(game, emulator, shows_title=True)
        assert room(game, emulator) == CHALLENGE['seasons']
    print('seasons upper ledge reached from the west passed', flush=True)


def test_ring(game, base):
    group, cave, ring = (4, 0xC5, 0x06) if game.name == 'ages' else (5, 0x34, 0x03)
    location = group, cave, 0x39, 0x78
    with game.boot(fixture(game, base, location, equipped=True)) as emulator:
        load(game, emulator, location)
        game.screenshot(emulator, 'cave-prize-before')
        assert emulator.memory[game.address['wRoomLayout'] + 0x27] == chest.CLOSED_CHEST
        walk(game, emulator, 'up', 9)
        game.press(emulator, 'a', 150)
        game.dismiss_pickup_text(emulator)
        emulator.tick(180, True)
        game.screenshot(emulator, 'cave-prize-after')
        assert game.read(emulator, 'wNumUnappraisedRingsBcd') == 1, (game.name, 'prize count')
        assert game.read(emulator, 'wUnappraisedRings') & 0x3F == ring, (game.name, 'wrong prize')
        saved = game.save_from_menu(emulator)
    with game.boot(saved) as emulator:
        game.press(emulator, 'a')
        game.press(emulator, 'a', 180)
        assert game.read(emulator, 'wNumUnappraisedRingsBcd') == 1, (game.name, 'prize lost on reload')
        assert game.read(emulator, 'wUnappraisedRings') & 0x3F == ring, (game.name, 'wrong reloaded prize')
    print(game.name, 'reward and save/reload passed', flush=True)


def test_wooden_sword(game, base):
    location = 4, 6, 0x39, 0x78
    with game.boot(fixture(game, base, location, early=True, finished=False)) as emulator:
        load(game, emulator, location)
        assert game.read(emulator, 'wSwordLevel') == 0
        game.screenshot(emulator, 'sword-prize-before')
        walk(game, emulator, 'up', 9)
        game.press(emulator, 'a', 150)
        for _ in range(12):
            if not game.read(emulator, 'wTextIsActive'):
                break
            game.press(emulator, 'a', 90)
        assert not game.read(emulator, 'wTextIsActive'), 'wooden sword dialogue did not finish'
        emulator.tick(250, True)
        game.screenshot(emulator, 'sword-prize-after')
        assert game.read(emulator, 'wSwordLevel') == 1
        assert room(game, emulator) == ENTRANCES['seasons'][:2]
    print(game.name, 'wooden sword pickup and return passed', flush=True)


if __name__ == '__main__':
    for variable in ('TMP', 'TEMP', 'TMPDIR', 'APPDATA', 'LOCALAPPDATA', 'XDG_CACHE_HOME'):
        os.environ[variable] = str(SCRATCH)
    from pyboy import PyBoy

    chest.PyBoy = PyBoy
    names = ('seasons',) if '--seasons-only' in sys.argv else ENTRANCES
    for name in names:
        spawn = ENTRANCES[name]
        game = Game(name)
        base = game.new_file()
        if '--fixtures' in sys.argv:
            (SCRATCH / f'{name.title()}-cave.sav').write_bytes(fixture(game, base, spawn, equipped=True))
        patched_rom = game.rom
        game.rom = retail_rom(name)
        with game.boot(fixture(game, base, spawn)) as emulator:
            load(game, emulator, spawn)
            walk(game, emulator, 'up', 35)
            assert room(game, emulator) == spawn[:2], (name, 'postgame entrance already exists on retail')
        if name == 'seasons':
            with game.boot(fixture(game, base, SEASONS_LOWER_DOOR, early=True, finished=False)) as emulator:
                load(game, emulator, SEASONS_LOWER_DOOR)
                enter_seasons_door(game, emulator, shows_title=True)
                assert room(game, emulator) == (4, 4)
        game.rom = patched_rom
        lower_door = SEASONS_LOWER_DOOR if name == 'seasons' else spawn
        for mode, status, location in (
            ('incomplete', {'finished': False, 'early': True}, spawn),
            ('completed', {}, spawn),
            ('sword', {}, lower_door),
            ('early-sword', {'finished': False, 'early': True}, lower_door),
            ('linked', {'linked': True, 'finished': False, 'early': True}, lower_door),
            ('hero', {'hero': True, 'finished': False, 'early': True}, spawn),
            ('old-door', {}, (0, 0xD4, 0x68, 0x18)),
        ):
            if name == 'ages' and ('sword' in mode or mode == 'old-door'):
                continue
            _, _, y, x = location
            sram = fixture(game, base, location, **status)
            with game.boot(sram) as emulator:
                load(game, emulator, location)
                game.screenshot(emulator, f'cave-{mode}-outside')
                if name == 'seasons' and mode in ('incomplete', 'completed', 'linked', 'hero', 'sword', 'early-sword'):
                    enter_seasons_door(game, emulator, shows_title='sword' not in mode)
                else:
                    walk(game, emulator, 'up', 35)
                    settle_entrance(game, emulator)
                game.screenshot(emulator, f'cave-{mode}-entered')
                expected = (4, 4) if 'sword' in mode else CHALLENGE[name] if mode in ('incomplete', 'completed', 'linked', 'hero') else location[:2]
                assert room(game, emulator) == expected, (name, mode, room(game, emulator), expected)
                if expected != location[:2]:
                    walk(game, emulator, 'down')
                    game.screenshot(emulator, f'cave-{mode}-exited')
                    assert room(game, emulator) == location[:2], (name, mode, room(game, emulator), position(game, emulator))
                    assert abs(position(game, emulator)[1] - x) <= 4, (name, mode, position(game, emulator), x)
                    game.move_to(emulator, 'y', y, 'up', 'down')
                    walk(game, emulator, 'up', 35)
                    settle_entrance(game, emulator)
                    assert room(game, emulator) == expected, (name, mode, 're-entry', room(game, emulator))
                print(name, mode, 'passed', flush=True)
        test_ring(game, base)
        if name == 'seasons':
            approach_upper_ledge(game, base)
            test_wooden_sword(game, base)

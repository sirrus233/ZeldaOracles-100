"""Test ring-secret exchange, GameID rejection and the Advance shop boundary."""
import json
import os
import sys

import test_postgame_chest as chest
from emit_heart_patches import PROJECT
from test_postgame_chest import Game, ROOT, SCRATCH
from test_heros_cave import load, room, walk, fixture, retail_rom
from test_ring_quests import quest_save, choose, continue_text, finish_conversation
from test_victory_ring import update_save, SHOPS

OUT = PROJECT / 'outputs' / 'Postgame Verification' / 'audit'
OUT.mkdir(parents=True, exist_ok=True)
RESULTS = []

def record(label, **details):
    RESULTS.append(dict(test=label, status='passed', **details))
    filename = 'starts-results.json' if '--starts' in sys.argv else 'transport-results.json'
    (OUT / filename).write_text(json.dumps(RESULTS, indent=2))
    print(label, details, flush=True)


def rings(emulator, game):
    start = game.address['wRingsObtained']
    return bytes(emulator.memory[start:start + 8])


def ring_save(game, base, mask, *, linked, game_id=0x1234):
    group, map_id, _, _ = SHOPS[game.name]
    location = group, map_id, 0x58, 0x68
    saved = quest_save(game, base, location, linked=linked, finished=True,
                       flags=(8,), treasures=(0x2C,))
    edits = [('wObtainedRingBox', 1, 0), ('wRingBoxLevel', 1, 0),
             ('wGameID', game_id & 255, 0), ('wGameID', game_id >> 8, 1)]
    edits += [('wRingsObtained', value, index) for index, value in enumerate(mask)]
    return update_save(game, saved, edits), location


def talk_snake(game, emulator):
    walk(game, emulator, 'up', 48)
    game.press(emulator, 'a', 120)


def ring_password(game, saved, location):
    with game.boot(saved) as emulator:
        load(game, emulator, location)
        talk_snake(game, emulator)
        choose(game, emulator, 1)
        emulator.tick(120, True)
        start = game.address['w7SecretText1']
        password = bytes(value for value in emulator.memory[7, start:start + 18] if value not in (0, 0x20))
        assert len(password) == 15, password
        choose(game, emulator, 1)
        finish_conversation(game, emulator)
        record('Red Snake generates ring secret', game=game.name)
        return password


def enter_ring_password(game, emulator, password, *, file_menu=False):
    if not file_menu:
        continue_text(game, emulator, lambda: game.read(emulator, 'wOpenedMenuType') == 6)
    emulator.tick(110, True)
    if game.read(emulator, 'wFileSelect.mode2') == 4:
        game.press(emulator, 'a', 30)
    symbols = bytes(emulator.memory[game.address['secretSymbols']:game.address['secretSymbols'] + 64])
    tilemap = game.address['w4TileMap']
    for character in password:
        choices = {}
        for row in range(5):
            for col in range(13):
                tile = emulator.memory[4, tilemap + 0xA3 + row * 64 + col + int(col >= 8)]
                choices.setdefault(symbols[(tile >> 1) & 0x3F], (row, col))
        target_row, target_col = choices[character]
        for direction, attempts, axis, target in [('up', 6, 16, target_row), ('right', 13, 1, target_col)]:
            for _ in range(attempts):
                cursor = game.read(emulator, 'wFileSelect.cursorPos')
                if (cursor // 16 if axis == 16 else cursor % 16) == target:
                    break
                game.press(emulator, direction, 9)
        assert game.read(emulator, 'wFileSelect.cursorPos') == target_row * 16 + target_col
        game.press(emulator, 'a', 12)
    game.press(emulator, 'start', 12)
    game.press(emulator, 'a', 100)


def accept_rings(game, saved, location, password, expected, *, reject=False):
    with game.boot(saved) as emulator:
        load(game, emulator, location)
        before = rings(emulator, game)
        talk_snake(game, emulator)
        choose(game, emulator, 0)
        enter_ring_password(game, emulator, password)
        if reject:
            assert game.read(emulator, 'wOpenedMenuType') == 6, 'Unrelated GameID unexpectedly accepted'
            assert rings(emulator, game) == before
            record('Ring secret rejected for unrelated GameID', game=game.name)
            return saved
        finish_conversation(game, emulator)
        assert rings(emulator, game) == (before if reject else expected), (game.name, rings(emulator, game).hex(), expected.hex())
        saved = game.save_from_menu(emulator)
    with game.boot(saved) as emulator:
        game.press(emulator, 'a')
        game.press(emulator, 'a', 180)
        assert rings(emulator, game) == (before if reject else expected)
    record('Ring secret rejected for unrelated GameID' if reject else 'Ring secret union and save/reload', game=game.name)
    return saved


def ring_roundtrip(first):
    second = 'seasons' if first == 'ages' else 'ages'
    g1, g2 = Game(first), Game(second)
    mask1, mask2 = bytes([0x55] * 8), bytes([0xAA] * 8)
    s1, loc1 = ring_save(g1, g1.new_file(), mask1, linked=False)
    base2 = g2.new_file()
    s2, loc2 = ring_save(g2, base2, mask2, linked=True)
    password = ring_password(g1, s1, loc1)
    wrong, wrong_loc = ring_save(g2, base2, mask2, linked=True, game_id=0x4321)
    accept_rings(g2, wrong, wrong_loc, password, bytes([255] * 8), reject=True)
    s2 = accept_rings(g2, s2, loc2, password, bytes([255] * 8))
    # Saving in Vasu's house normally respawns at its entrance, but load() only
    # checks the room. Repositioning is an explicit fixture setup for the next visit.
    s2 = update_save(g2, s2, [('wDeathRespawnBuffer.y', loc2[2], 0), ('wDeathRespawnBuffer.x', loc2[3], 0)])
    back = ring_password(g2, s2, loc2)
    accept_rings(g1, s1, loc1, back, bytes([255] * 8))
    record('Both-direction exchange preserves all 64 ring bits', first=first, second=second,
           input_note='Complementary appraised-ring ownership is prepared input, not 64 acquisition tests')


def advance_shop(game, base):
    exterior = (1, 0x58, 0x48, 0x58) if game.name == 'ages' else (0, 0xC5, 0x28, 0x48)
    tile, opened = (0x35, 0xDE) if game.name == 'ages' else (0x14, 0xEA)
    for hardware in (1, 255):
        with game.boot(fixture(game, base, exterior, equipped=True, finished=False)) as emulator:
            emulator.memory[game.address['hGameboyType']] = hardware
            load(game, emulator, exterior)
            actual = emulator.memory[game.address['wRoomLayout'] + tile]
            assert (actual == opened) == (hardware == 255), (game.name, hardware, actual)
        record('Advance shop entrance hardware gate', game=game.name, hardware_id=hardware,
               note='HRAM hardware-ID fixture; not a GBA boot-ROM emulation test')
    interior = (3, 0xFE, 0x38, 0x64) if game.name == 'ages' else (3, 0xAF, 0x38, 0x64)
    saved = quest_save(game, base, interior, finished=True, treasures=(0x2C,))
    saved = update_save(game, saved, [('wNumRupees', 0x99, 0), ('wNumRupees', 9, 1)])
    with game.boot(saved) as emulator:
        emulator.memory[game.address['hGameboyType']] = 255
        load(game, emulator, interior)
        walk(game, emulator, 'up', 1)
        game.press(emulator, 'a', 50)  # Lift the ring from the shelf.
        walk(game, emulator, 'left', 50)
        walk(game, emulator, 'down', 12)
        game.press(emulator, 'a', 100)
        choose(game, emulator, 0)
        continue_text(game, emulator, lambda: game.read(emulator, 'wNumUnappraisedRingsBcd') == 1)
        assert game.read(emulator, 'wUnappraisedRings') & 0x3F == (0x0E if game.name == 'ages' else 0x33)
        finish_conversation(game, emulator)
        saved = game.save_from_menu(emulator)
    record('Advance ring purchased through shop interaction', game=game.name)


def linked_start(first):
    second = 'seasons' if first == 'ages' else 'ages'
    g1, g2 = Game(first), Game(second)
    interior = (5, 0xCF, 0x49, 0x58) if first == 'ages' else (4, 0xE8, 0x49, 0x58)
    initial = quest_save(g1, g1.new_file(), interior, linked=False, finished=True)
    with g1.boot(initial) as emulator:
        load(g1, emulator, interior)
        walk(g1, emulator, 'up', 15)
        g1.press(emulator, 'a', 100)
        choose(g1, emulator, 1)  # No secret to tell Farore.
        choose(g1, emulator, 0)  # Ask for the secret to the other land.
        emulator.tick(120, True)
        start = g1.address['w7SecretText1']
        password = bytes(value for value in emulator.memory[7, start:start + 24] if value not in (0, 0x20))
        assert len(password) == 20, password
    with g2.boot() as emulator:
        g2.press(emulator, 'a', 100)  # Blank file's New game / Secret / Link menu.
        assert g2.read(emulator, 'wFileSelect.mode') == 5
        g2.press(emulator, 'down')
        g2.press(emulator, 'a', 100)
        assert g2.read(emulator, 'wFileSelect.mode') == 6
        enter_ring_password(g2, emulator, password, file_menu=True)
        assert g2.read(emulator, 'wFileSelect.mode') == 1
        g2.press(emulator, 'a')
        g2.press(emulator, 'a', 180)
        assert g2.read(emulator, 'wFileIsLinkedGame') == 1
        assert g2.read(emulator, 'wFileIsHeroGame') == 0
        assert g2.read(emulator, 'wLinkMaxHealth') == 16
        assert bytes(emulator.memory[g2.address['wGameID']:g2.address['wGameID'] + 2]) == b'\x34\x12'
    record('Farore game-transfer password creates linked four-heart Game 2 with same GameID', first=first, second=second)


if __name__ == '__main__':
    for variable in ('TMP', 'TEMP', 'TMPDIR', 'APPDATA', 'LOCALAPPDATA', 'XDG_CACHE_HOME'):
        os.environ[variable] = str(SCRATCH)
    from pyboy import PyBoy
    chest.PyBoy = PyBoy
    if '--starts' in sys.argv:
        for first in ('ages', 'seasons'):
            linked_start(first)
        sys.exit(0)
    if '--gba' not in sys.argv:
        for first in ('ages', 'seasons'):
            ring_roundtrip(first)
    if '--rings' not in sys.argv:
        for name in ('ages', 'seasons'):
            game = Game(name)
            advance_shop(game, game.new_file())

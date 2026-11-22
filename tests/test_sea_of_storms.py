"""Exercise the Sea of Storms from prepared saves with normal controller input."""

import os
import sys

import test_postgame_chest as chest
from emit_heart_patches import PROJECT, apply_patch
from test_heros_cave import fixture, load, position, retail_rom, room, walk
from test_postgame_chest import Game, ROOT, SAVE_SLOT_COPIES, SAVE_SLOT_LENGTH, SCRATCH


OUTSIDE = (0, 0xD6, 0x68, 0x18)
GATE_DIVE = (0, 0xD7, 0x68, 0x28)
BUNDLE = PROJECT / 'outputs' / 'Postgame Verification'
PATCH = PROJECT / 'outputs' / 'Oracle of Ages - 100 Percent.bps'


def sea_save(game, base, location, *, sailed=False, linked=False):
    sram = fixture(game, base, location, finished=False, linked=linked, equipped=True)
    start = game.address['wFileStart']
    saved = sram[SAVE_SLOT_COPIES[0]:SAVE_SLOT_COPIES[0] + SAVE_SLOT_LENGTH]
    saved[game.address['wEssencesObtained'] - start] = 0x7F
    saved[game.address['wNumGashaSeeds'] - start] = 1
    saved[game.address['wInventoryB'] - start] = 0x11  # Harp with Tune of Ages.
    saved[game.address['wInventoryA'] - start] = 0x15  # Shovel for the island's soil.
    storage = game.address['wInventoryStorage'] - start
    saved[saved.index(0x11, storage, storage + 16)] = 0x17
    saved[saved.index(0x15, storage, storage + 16)] = 0x05
    saved[game.address['wGlobalFlags'] - start + 6] |= 1  # Water pollution fixed.
    if sailed:
        saved[game.address['wGlobalFlags'] - start + 6] |= 0x10  # Pirates gone.
        era = game.address['wGroup0RoomFlags' if linked else 'wGroup1RoomFlags'] - start
        saved[era + (0xD7 if linked else 0xD6)] |= 0x40  # Zora let Link pass.
        saved[era + (0xC8 if linked else 0xD7)] |= 0x40  # Farewell seen.
        saved[game.address['wObtainedTreasureFlags'] - start + 9] |= 0x80  # Tokay Eyeball.
    else:
        saved[game.address['wObtainedTreasureFlags'] - start + 9] |= 0x40  # Zora Scale.
    checksum = sum(int.from_bytes(saved[i:i + 2], 'little') for i in range(2, len(saved), 2))
    saved[:2] = (checksum & 0xFFFF).to_bytes(2, 'little')
    for offset in SAVE_SLOT_COPIES:
        sram[offset:offset + SAVE_SLOT_LENGTH] = saved
    return sram


def swim_until(emulator, direction, reached, limit=1450):
    for _ in range(limit):
        if reached():
            return True
        emulator.button(direction, 2)
        emulator.tick(4, False)
    return False


def swim_to_room(game, emulator, direction, destination):
    assert swim_until(emulator, direction, lambda: room(game, emulator) == destination), (
        direction, destination, room(game, emulator), position(game, emulator),
    )
    emulator.tick(105, True)


def swim_to(game, emulator, direction, coordinate):
    axis = 0 if direction in ('up', 'down') else 1
    sign = 1 if direction in ('down', 'right') else -1
    assert swim_until(emulator, direction, lambda: sign * position(game, emulator)[axis] >= sign * coordinate), (
        direction, coordinate, room(game, emulator), position(game, emulator),
    )
    emulator.tick(105, True)


def test_closed_gate(game, base, *, sailed):
    with game.boot(sea_save(game, base, GATE_DIVE, sailed=sailed)) as emulator:
        load(game, emulator, GATE_DIVE)
        game.press(emulator, 'b', 100)
        assert room(game, emulator) == (2, 0xD7)
        assert emulator.memory[game.address['wRoomLayout'] + 0x42] == 0xE9
        assert not swim_until(emulator, 'up', lambda: position(game, emulator)[0] <= 0x35, limit=800)
        assert room(game, emulator) == (2, 0xD7)


def linked_gate(game, base):
    with game.boot(sea_save(game, base, GATE_DIVE, linked=True)) as emulator:
        load(game, emulator, GATE_DIVE)
        game.press(emulator, 'b', 100)
        assert room(game, emulator) == (2, 0xD7)
        assert emulator.memory[game.address['wRoomLayout'] + 0x42] == 0x3B
        assert any(emulator.memory[slot] and emulator.memory[slot + 1:slot + 3] == [0xAB, 0x12]
                   for slot in range(0xD040, 0xE000, 0x100)), 'linked Zora guard missing'
        game.screenshot(emulator, 'sea-linked-guard')
        return emulator.screen.ndarray[64:100, 24:56].tobytes()


def test_island(game, sram):
    with game.boot(sram) as emulator:
        load(game, emulator, OUTSIDE)
        game.press(emulator, 'b', 100)
        assert room(game, emulator) == (2, 0xD6)
        swim_to_room(game, emulator, 'right', (2, 0xD7))
        swim_to(game, emulator, 'right', 0x28)
        assert emulator.memory[game.address['wRoomLayout'] + 0x42] == 0x3B
        swim_to(game, emulator, 'up', 0x35)
        game.screenshot(emulator, 'sea-open-passage')

        # Reach the inner bay, cross its shore to the east, then circle back under the reef.
        swim_to_room(game, emulator, 'up', (2, 0xC7))
        swim_to(game, emulator, 'right', 0x37)
        swim_to(game, emulator, 'up', 0x48)
        game.press(emulator, 'b', 140)
        assert room(game, emulator) == (0, 0xC7)
        swim_to(game, emulator, 'right', 0x58)
        swim_to(game, emulator, 'down', 0x60)
        swim_to_room(game, emulator, 'right', (0, 0xC8))
        swim_to(game, emulator, 'right', 0x38)
        game.press(emulator, 'b', 140)
        assert room(game, emulator) == (2, 0xC8)
        swim_to_room(game, emulator, 'down', (2, 0xD8))
        swim_to(game, emulator, 'down', 0x18)
        swim_to_room(game, emulator, 'left', (2, 0xD7))
        game.press(emulator, 'b', 140)
        assert room(game, emulator) == (0, 0xD7)
        swim_to(game, emulator, 'left', 0x68)
        swim_to(game, emulator, 'down', 0x28)
        walk(game, emulator, 'left', 4)
        game.press(emulator, 'a', 100)
        game.screenshot(emulator, 'sea-dig-result')
        assert emulator.memory[game.address['wRoomLayout'] + 0x25] == 0xD2, 'soft soil did not appear'
        game.screenshot(emulator, 'sea-soft-soil')

        for _ in range(10):
            if game.read(emulator, 'wGashaSpotsPlantedBitset') & 0x80:
                break
            game.press(emulator, 'a', 85)
        assert game.read(emulator, 'wGashaSpotsPlantedBitset') & 0x80
        assert emulator.memory[game.address['wGroup0RoomFlags'] + 0xD7] & 0x10
        # The planting flag is set before Link finishes the planting interaction.
        # Wait for native input eligibility rather than issuing a one-frame B press early.
        for _ in range(600):
            if game.read(emulator,'w1Link.state')==1 and not any(game.read(emulator,n) for n in (
                    'wTextIsActive','wDisabledObjects','wMenuDisabled','wLinkForceState','wLinkUsingItem1','wInstrumentsDisabledCounter','wLinkInAir','wLinkSwimmingState')):
                break
            if game.read(emulator,'wTextIsActive'):game.press(emulator,'a',30)
            else:emulator.tick(1,False)
        else:raise AssertionError('Planting interaction did not return control')
        # Hold across several input polls; a single-frame press can fall on a lag frame.
        emulator.button('b',6)
        emulator.tick(700,True)  # The Tune of Ages returns Link to the past.
        assert room(game, emulator) == (1, 0xD7)
        saved = game.save_from_menu(emulator)
    with game.boot(saved) as emulator:
        load(game, emulator, OUTSIDE)
        assert game.read(emulator, 'wGashaSpotsPlantedBitset') & 0x80
        assert emulator.memory[game.address['wGroup0RoomFlags'] + 0xD7] & 0x10


def test_present_cave_route(game, base):
    shore = 0, 0xC8, 0x68, 0x38
    with game.boot(sea_save(game, base, shore, sailed=True)) as emulator:
        load(game, emulator, shore)
        game.press(emulator, 'b', 140)
        assert room(game, emulator) == (2, 0xC8)
        swim_to_room(game, emulator, 'up', (2, 0xB8))
        swim_to(game, emulator, 'up', 0x58)
        swim_to_room(game, emulator, 'left', (2, 0xB7))
        swim_to(game, emulator, 'left', 0x38)
        swim_to_room(game, emulator, 'up', (3, 0xE8))


def test_departure(game, base):
    deck = 5, 0xF8, 0x3B, 0xC8
    with game.boot(sea_save(game, base, deck)) as emulator:
        load(game, emulator, deck)
        walk(game, emulator, 'up', 10)
        game.press(emulator, 'a', 120)
        assert game.read(emulator, 'wTextIsActive'), 'Cap’n dialogue did not start'
        for _ in range(90):
            if room(game, emulator) == (1, 0xD7) and not game.read(emulator, 'wMenuDisabled'):
                break
            game.press(emulator, 'a', 90)
        game.screenshot(emulator, 'sea-captain-departure')
        flags = game.address['wGlobalFlags']
        inventory = game.address['wObtainedTreasureFlags']
        assert room(game, emulator) == (1, 0xD7), 'Cap’n did not return Link to the past sea'
        assert emulator.memory[flags + 6] & 0x10, 'departure flag was not set'
        assert emulator.memory[inventory + 9] & 0xC0 == 0x80, 'Zora Scale was not exchanged for the Tokay Eyeball'
        assert emulator.memory[game.address['wGroup1RoomFlags'] + 0xD7] & 0x40, 'farewell did not finish'


def test_chest(game, base, *, present, linked):
    cave = 0xE8 if present else 0xFF
    location = 3, cave, 0x48, 0x58
    with game.boot(sea_save(game, base, location, sailed=True, linked=linked)) as emulator:
        load(game, emulator, location)
        seeds = game.read(emulator, 'wNumGashaSeeds')
        walk(game, emulator, 'up', 8)
        game.press(emulator, 'a', 160)
        game.dismiss_pickup_text(emulator)
        ring = present == linked
        assert game.read(emulator, 'wNumUnappraisedRingsBcd') == int(ring), (present, linked)
        assert game.read(emulator, 'wNumGashaSeeds') == seeds + int(not ring), (present, linked)
        if ring:
            assert game.read(emulator, 'wUnappraisedRings') & 0x3F == 0x11


if __name__ == '__main__':
    for variable in ('TMP', 'TEMP', 'TMPDIR', 'APPDATA', 'LOCALAPPDATA', 'XDG_CACHE_HOME'):
        os.environ[variable] = str(SCRATCH)
    from pyboy import PyBoy

    chest.PyBoy = PyBoy
    game = Game('ages')

    base = game.new_file()
    starter = sea_save(game, base, OUTSIDE, sailed=True)
    if '--fixtures' in sys.argv:
        (SCRATCH / 'Ages-sea-of-storms.sav').write_bytes(starter)

    target = game.rom
    game.rom = retail_rom('ages')
    test_closed_gate(game, base, sailed=True)
    original_guard = linked_gate(game, base)
    game.rom = target
    assert linked_gate(game, base) == original_guard
    test_closed_gate(game, base, sailed=False)
    test_departure(game, base)
    print('The passage stays closed until Cap’n sails. Tokay Eyeball exchange passed.', flush=True)
    test_island(game, starter)
    print('Swam from outside to the island, planted soft soil, and saved the map visit.', flush=True)
    test_present_cave_route(game, base)
    for present in (False, True):
        for linked in (False, True):
            test_chest(game, base, present=present, linked=linked)
    print('Present cave approach and both era rewards in both game modes passed.', flush=True)

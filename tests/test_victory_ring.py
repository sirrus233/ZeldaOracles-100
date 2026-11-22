"""Exercise the credits save prompt and Vasu's original award with controller input."""

from io import BytesIO
import os
import sys

import test_postgame_chest as chest
from emit_heart_patches import PROJECT, apply_patch
from test_heros_cave import load, retail_rom, room, walk
from test_postgame_chest import Game, ROOT, SAVE_SLOT_COPIES, SAVE_SLOT_LENGTH, SCRATCH
from test_ring_quests import choose, continue_text, finish_conversation, flag, quest_save


SHOPS = {'ages': (2, 0xEE, 0x48, 0x50), 'seasons': (1, 0x91, 0x48, 0x50)}
BUNDLE = PROJECT / 'outputs' / 'Postgame Verification'


def update_save(game, sram, changes):
    result = bytearray(sram)
    start = game.address['wFileStart']
    primary = SAVE_SLOT_COPIES[0]
    data = result[primary:primary + SAVE_SLOT_LENGTH]
    for symbol, value, offset in changes:
        data[game.address[symbol] - start + offset] = value
    checksum = sum(int.from_bytes(data[i:i + 2], 'little') for i in range(2, len(data), 2))
    data[:2] = (checksum & 0xFFFF).to_bytes(2, 'little')
    for slot in SAVE_SLOT_COPIES:
        result[slot:slot + SAVE_SLOT_LENGTH] = data
    return result


def shop_save(game, base, *, finished=False, linked=True, flags=()):
    result = quest_save(game, base, SHOPS[game.name], finished=finished, linked=linked,
                        flags=(8, *flags), treasures=(0x2C,))
    changes = [('wObtainedRingBox', 1, 0), ('wRingBoxLevel', 1, 0)]
    if game.name == 'seasons' and linked:
        changes.append(('wc6e5', 9, 0))
    return update_save(game, result, changes)


def credits_fixture(game, emulator):
    """Begin at the Hero's Secret screen after credits, before any completion save."""
    emulator.memory[0xC2EF] = 0x0A  # wCutsceneIndex, an assembler alias.
    emulator.memory[game.address['wCutsceneState']] = 1
    emulator.memory[0xCBC1] = 3
    emulator.memory[0xCBC2] = 4
    emulator.memory[game.address['wPaletteThread_mode']] = 0
    emulator.memory[game.address['wScrollMode']] = 0
    emulator.memory[game.address['wDisabledObjects']] = 0x81


def ending_save(game, initial, *, save, state=None):
    with game.boot(initial) as emulator:
        load(game, emulator, SHOPS[game.name])
        inventory = bytes(emulator.memory[game.address['wInventoryB']:game.address['wInventoryStorage'] + 16])
        world_fields = ['wMapleKillCounter']
        if game.name == 'ages':
            world_fields += ['wMakuMapTextPresent', 'wMakuMapTextPast']
        world_before = [game.read(emulator, symbol) for symbol in world_fields]
        if state:
            with state.open('rb') as source:
                emulator.load_state(source)
        else:
            credits_fixture(game, emulator)
        for _ in range(130):
            emulator.tick(10, False)
            if game.read(emulator, 'wTextIsActive'):
                break
        else:
            print('ending state', list(emulator.memory[0xC2EE:0xC2F0]), list(emulator.memory[0xCBC0:0xCBC4]), game.read(emulator, 'wCutsceneState'), flush=True)
            game.screenshot(emulator, 'victory-no-save-dialog')
            raise AssertionError((game.name, 'credits save prompt did not open'))
        emulator.tick(100, True)
        assert game.read(emulator, 'wTextIndexH_backup') == 0x59
        assert not flag(game, emulator, 2)
        game.screenshot(emulator, 'victory-ending-save-prompt')
        if save and game.read(emulator, 'wFileIsLinkedGame'):
            with (SCRATCH / f'{game.name}-victory-credits.state').open('wb') as output:
                emulator.save_state(output)
            (SCRATCH / f'{game.name}-victory-credits.sav').write_bytes(initial)
        choose(game, emulator, 1 if save else 0)  # Existing prompt uses No / Yes.
        if not save:
            choose(game, emulator, 1)  # Decline the offer to return to the save prompt.
        emulator.tick(130, True)
        result = game.save_bytes(emulator)
    with game.boot(result) as emulator:
        game.press(emulator, 'a')
        game.press(emulator, 'a', 180)
        assert bytes(emulator.memory[game.address['wInventoryB']:game.address['wInventoryStorage'] + 16]) == inventory
        assert flag(game, emulator, 2) == (save and bool(game.read(emulator, 'wFileIsLinkedGame')))
        linked = bool(game.read(emulator, 'wFileIsLinkedGame'))
        assert flag(game, emulator, game.finished_flag) == (save and not linked)
        assert bool(game.read(emulator, 'wFileIsCompleted')) == (save and not linked)
        if linked:
            expected_world = world_before.copy()
            if save and game.name == 'ages':
                expected_world[1:] = [0x1C, 0x8C]
            assert [game.read(emulator, symbol) for symbol in world_fields] == expected_world
        if save:
            print(game.name, 'reload room', room(game, emulator), flush=True)
            expected = (2, 0x5E if game.read(emulator, 'wFileIsLinkedGame') else 0x5D) if game.name == 'seasons' else (0, 0x38)
            assert room(game, emulator) == expected
            before = game.read(emulator, 'w1Link.yh')
            walk(game, emulator, 'down', 8)
            assert game.read(emulator, 'w1Link.yh') != before, 'Link cannot move after reloading'
    return result


def visit_vasu(game, sram, *, eligible, claimed=False):
    with game.boot(sram) as emulator:
        load(game, emulator, SHOPS[game.name])
        walk(game, emulator, 'up', 48)
        game.press(emulator, 'a', 100)
        if eligible:
            continue_text(game, emulator, lambda: game.read(emulator, 'wNumUnappraisedRingsBcd') == 1)
            assert game.read(emulator, 'wUnappraisedRings') & 0x3F == 0x36
            assert flag(game, emulator, 6)
            game.screenshot(emulator, 'victory-vasu-award')
        else:
            choose(game, emulator, 2)  # Quit the normal Vasu menu.
            finish_conversation(game, emulator)
            assert game.read(emulator, 'wNumUnappraisedRingsBcd') == int(claimed)
            assert flag(game, emulator, 6) == claimed
        if eligible:
            finish_conversation(game, emulator)
            return game.save_from_menu(emulator)


def at_shop(game, sram):
    return update_save(game, sram, [(f'wDeathRespawnBuffer.{key}', value, 0)
                                   for key, value in zip(('group', 'room', 'y', 'x'), SHOPS[game.name])])


if __name__ == '__main__':
    for variable in ('TMP', 'TEMP', 'TMPDIR', 'APPDATA', 'LOCALAPPDATA', 'XDG_CACHE_HOME'):
        os.environ[variable] = str(SCRATCH)
    from pyboy import PyBoy
    chest.PyBoy = PyBoy
    for name in ('ages', 'seasons'):
        game = Game(name)
        base = game.new_file()
        initial = (shop_save(game, base))
        state = None
        visit_vasu(game, initial, eligible=False)
        declined = ending_save(game, initial, save=False, state=state)
        assert declined == initial, 'Declining the ending save changed SRAM'
        unlinked = ending_save(game, shop_save(game, base, linked=False), save=True)
        visit_vasu(game, at_shop(game, unlinked), eligible=False)
        saved = ending_save(game, initial, save=True, state=state)
        saved = at_shop(game, saved)
        (SCRATCH / f'{name}-victory-vasu.sav').write_bytes(saved)
        awarded = visit_vasu(game, saved, eligible=True)
        visit_vasu(game, at_shop(game, awarded), eligible=False, claimed=True)
        print(name, 'Victory Ring saved ending, declined save, Game 1 exclusion and one-time reward passed', flush=True)

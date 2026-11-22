"""Test saved linked-clear isolation, family rewards and native NPC roles."""
import json
import os
import sys

import test_postgame_chest as chest
from emit_heart_patches import PROJECT
from test_postgame_chest import Game, ROOT, SCRATCH
from test_heros_cave import load, walk, retail_rom
from test_ring_quests import quest_save, continue_text, finish_conversation, flag
from test_victory_ring import update_save, shop_save, ending_save, SHOPS

OUT = PROJECT / 'outputs' / 'Postgame Verification'
RESULTS = []
FAMILY = {'ages': ((2, 0xEA), (2, 0xEB)), 'seasons': ((1, 0x92), (1, 0x93))}


def record(test, **details):
    RESULTS.append(dict(test=test, status='passed', **details))
    OUT.mkdir(exist_ok=True)
    (OUT / ('receiver-role-results.json' if '--receivers-only' in sys.argv else 'test-results.json')).write_text(json.dumps(RESULTS, indent=2))
    print(test, details, flush=True)


def locate(game, saved, location):
    return update_save(game, saved, [(f'wDeathRespawnBuffer.{key}', value, 0)
                                    for key, value in zip(('group', 'room', 'y', 'x'), location)])


def actors(game, saved, location, ids, *, talk=False, check_king_role=False):
    with game.boot(locate(game, saved, location)) as emulator:
        load(game, emulator, location)
        found = sorted((emulator.memory[slot + 1], emulator.memory[slot + 2], emulator.memory[slot + 3])
                       for slot in range(0xD040, 0xE000, 0x100)
                       if emulator.memory[slot] and emulator.memory[slot + 1] in ids)
        if check_king_role:
            king, = [slot for slot in range(0xD040, 0xE000, 0x100)
                     if emulator.memory[slot] and emulator.memory[slot + 1] == 0x9C]
            pointer = emulator.memory[king + 0x18] | emulator.memory[king + 0x19] << 8
            ordinary = game.address['kingZoraScript_present_afterD7']
            assert ordinary <= pointer <= ordinary + 4, ('King Zora selected another role', hex(pointer), hex(ordinary))
        text = None
        if talk and ids != (0x9C,):
            walk(game, emulator, 'up', 5 if ids == (0x52,) else 48)
            game.press(emulator, 'a', 150)
            if game.read(emulator, 'wTextIsActive'):
                text = emulator.screen.ndarray[104:144, 8:152].tobytes()
        assert not flag(game, emulator, game.finished_flag)
        return found, text


def family_states(game, saved, *, first_adventure=False):
    patched = game.rom
    for stage, personalities in ((0, (0,)), (5, (0, 1, 2)), (8, range(4)), (9, range(4))):
        for personality in personalities:
            fixture = update_save(game, saved, [('wChildStage', stage, 0), ('wNextChildStage', stage, 0),
                                               ('wChildPersonality', personality, 0)])
            combined = []
            for group, map_id in FAMILY[game.name]:
                location = group, map_id, 0x68, 0x50
                if first_adventure:
                    with game.boot(locate(game, fixture, location)) as emulator:
                        load(game, emulator, location)
                        assert flag(game, emulator, game.finished_flag)
                        ids = [emulator.memory[slot + 1] for slot in range(0xD040, 0xE000, 0x100)
                               if emulator.memory[slot] and emulator.memory[slot + 1] in (0x28, 0x2B, 0x35)]
                        assert not ids
                    continue
                game.rom = retail_rom(game.name)
                expected = actors(game, fixture, location, (0x28, 0x2B, 0x35))
                game.rom = patched
                actual = actors(game, fixture, location, (0x28, 0x2B, 0x35))
                assert actual == expected, (game.name, stage, personality, location, actual, expected)
                combined += actual[0]
            if not first_adventure:
                assert combined
            record('Game 1 family departure preserved' if first_adventure else 'Family state matches ordinary linked retail',
                   game=game.name, stage=stage, personality=personality)
    game.rom = patched


def unrelated_roles(game, saved):
    patched = game.rom
    if game.name == 'ages':
        # King's ordinary dialogue requires his cure, clean seas and D7. Supply
        # those native progression prerequisites, keeping both completion markers
        # exactly as recorded by the ending under test.
        edits = []
        for byte, bits in ((4, 0x80), (6, 3)):
            current = saved[0x10 + game.address['wGlobalFlags'] - game.address['wFileStart'] + byte]
            edits.append(('wGlobalFlags', current | bits, byte))
        saved = update_save(game, saved, edits)
    cases = ([(0, 0x70, 0x68, 0x48, (0x49,)), (5, 0xAB, 0x20, 0x78, (0x9C,))]
             if game.name == 'ages' else [(1, 0xBA, 0x48, 0x50, (0xCB,)), (0, 8, 0x68, 0x50, (0x52,))])
    for group, map_id, y, x, ids in cases:
        location = group, map_id, y, x
        game.rom = retail_rom(game.name)
        expected = actors(game, saved, location, ids, talk=True)
        game.rom = patched
        actual = actors(game, saved, location, ids, talk=True, check_king_role=ids == (0x9C,))
        assert actual == expected, (game.name, 'unrelated postgame role activated', location)
        if ids == (0x9C,):
            assert actual[0], (game.name, 'King Zora not exercised', location)
        elif ids == (0x52,):
            assert actual[0] and actual[1], (game.name, 'ordinary actor/dialogue not exercised', location)
        else:
            assert not actual[0], (game.name, 'unwanted first-game-only receiver appeared', location)
        record('Unrelated NPC role matches ordinary linked retail after saved clear', game=game.name, room=[group, map_id],
               verification='actor and ordinary script selection' if ids == (0x9C,) else 'actors and dialogue')


def family_reward(game, saved, *, claimed):
    group, map_id = FAMILY[game.name][1]
    location = group, map_id, 0x48, 0x78
    saved = update_save(game, saved, [('wChildStage', 8, 0), ('wNextChildStage', 8, 0),
                                    ('wChildPersonality', 2, 0), ('wc6e2', 0x20 if claimed else 0, 0),
                                    ('wNumGashaSeeds', 2, 0)])
    if not claimed:
        (SCRATCH / f'{game.name}-linked-clear-family.sav').write_bytes(locate(game, saved, location))
    with game.boot(locate(game, saved, location)) as emulator:
        load(game, emulator, location)
        assert flag(game, emulator, 2) and not flag(game, emulator, game.finished_flag)
        walk(game, emulator, 'left', 48)
        game.press(emulator, 'a', 150)
        finish_conversation(game, emulator)
        expected = 2 if claimed else 3
        game.screenshot(emulator, f'linked-clear-family-reward-{claimed}')
        assert game.read(emulator, 'wNumGashaSeeds') == expected, (game.name, claimed, game.read(emulator, 'wNumGashaSeeds'))
        assert game.read(emulator, 'wc6e2') & 0x20
        assert game.read(emulator, 'wNextChildStage') == (8 if claimed else 9)
        game.screenshot(emulator, f'linked-clear-family-reward-{claimed}')
        saved = game.save_from_menu(emulator)
        if not claimed:
            (SCRATCH / f'{game.name}-linked-clear-family-claimed.sav').write_bytes(saved)
    with game.boot(saved) as emulator:
        load(game, emulator, location)
        walk(game, emulator, 'left', 48)
        game.press(emulator, 'a', 150)
        finish_conversation(game, emulator)
        assert game.read(emulator, 'wNumGashaSeeds') == expected
        assert game.read(emulator, 'wc6e2') & 0x20
    record('Family reward and next-stage request persist without duplicate on reload', game=game.name, previously_claimed=claimed)


def prototype_save_repair(game, saved):
    start = game.address['wFileStart']
    byte = saved[0x10 + game.address['wGlobalFlags'] - start + game.finished_flag // 8]
    legacy = update_save(game, saved, [('wFileIsCompleted', 1, 0),
                        ('wGlobalFlags', byte | 1 << (game.finished_flag % 8), game.finished_flag // 8)])
    with game.boot(legacy) as emulator:
        load(game, emulator, SHOPS[game.name])
        assert flag(game, emulator, 2)
        assert not flag(game, emulator, game.finished_flag)
        assert not game.read(emulator, 'wFileIsCompleted')
        repaired = game.save_from_menu(emulator)
    with game.boot(repaired) as emulator:
        load(game, emulator, SHOPS[game.name])
        assert flag(game, emulator, 2)
        assert not flag(game, emulator, game.finished_flag)
        assert not game.read(emulator, 'wFileIsCompleted')
    record('Earlier prototype linked-clear markers normalized and saved without losing Ganon clear', game=game.name)


def receiver_gates(game, before, after):
    if game.name == 'seasons':
        for location, actor in (((1, 0xB6, 0x60, 0x50), 0xCD), ((1, 0xAD, 0x40, 0x50), 0xD5)):
            assert not actors(game, before, location, (actor,))[0]
            assert bool(actors(game, after, location, (actor,))[0]) == (actor == 0xCD)
            if actor == 0xCD:
                ready=locate(game,after,location)
                byte=0x2e//8
                offset=0x10+game.address['wObtainedTreasureFlags']-game.address['wFileStart']+byte
                # Flippers are mandatory in a legitimate completed Seasons game.
                ready=update_save(game,ready,[('wObtainedTreasureFlags',ready[offset]|(1<<(0x2e%8)),byte)])
                with game.boot(ready) as emulator:
                    seen=[]
                    emulator.hook_register(0,game.address['showText'],lambda _:seen.append(emulator.register_file.B<<8|emulator.register_file.C),None)
                    load(game, emulator, location)
                    walk(game, emulator, 'up', 48)
                    game.press(emulator, 'a', 120)
                    from test_ring_quests import finish_conversation
                    finish_conversation(game, emulator)
                    assert not game.read(emulator, 'wOpenedMenuType')
                    assert 0x3404 in seen and not any(t>>8==0x4c for t in seen),seen
            record('Linked ending preserves peaceful roles without extra secret receivers', game=game.name, actor=actor)
    else:
        for location in ((3, 0xF8, 0x60, 0x70), (2, 0xE7, 0x3A, 0x48)):
            for saved in (before, after):
                with game.boot(locate(game, saved, location)) as emulator:
                    load(game, emulator, location)
                    walk(game, emulator, 'up', 48)
                    game.press(emulator, 'a', 120)
                    assert not game.read(emulator, 'wOpenedMenuType')
            record('Linked NPC retains ordinary role before and after Ganon', game=game.name, room=location[:2])


if __name__ == '__main__':
    for variable in ('TMP', 'TEMP', 'TMPDIR', 'APPDATA', 'LOCALAPPDATA', 'XDG_CACHE_HOME'):
        os.environ[variable] = str(SCRATCH)
    from pyboy import PyBoy
    chest.PyBoy = PyBoy
    if '--receivers-only' in sys.argv:
        for name in ('ages','seasons'):
            game=Game(name)
            receiver_gates(game,shop_save(game,game.new_file()),(SCRATCH/f'{name}-linked-clear.sav').read_bytes())
        sys.exit(0)
    if '--roles-only' in sys.argv:
        RESULTS = [row for row in json.loads((OUT / 'test-results.json').read_text())
                   if row['test'] != 'Unrelated NPC role matches ordinary linked retail after saved clear']
        for name in ('ages', 'seasons'):
            unrelated_roles(Game(name), (SCRATCH / f'{name}-linked-clear.sav').read_bytes())
        sys.exit(0)
    if '--reward-only' in sys.argv:
        for name in ('ages', 'seasons'):
            if '--ages' in sys.argv and name != 'ages':
                continue
            saved = (SCRATCH / f'{name}-linked-clear.sav').read_bytes()
            for claimed in (False, True):
                family_reward(Game(name), saved, claimed=claimed)
        sys.exit(0)
    for name in ('ages', 'seasons'):
        game = Game(name)
        base = game.new_file()
        initial = shop_save(game, base)
        if name == 'ages':
            start = game.address['wFileStart']
            initial = update_save(game, initial, [('wGroup0RoomFlags', 0x20, 0xE7),
                                                 ('wMapleKillCounter', 17, 0),
                                                 ('wMakuMapTextPresent', 0x1B, 0), ('wMakuMapTextPast', 0x8B, 0)])
        else:
            initial = update_save(game, initial, [('wMapleKillCounter', 17, 0)])
        saved = ending_save(game, initial, save=True)
        (SCRATCH / f'{name}-linked-clear.sav').write_bytes(saved)
        prototype_save_repair(game, locate(game, saved, SHOPS[name]))
        receiver_gates(game, initial, saved)
        unrelated_roles(game, saved)
        family_states(game, saved)
        for claimed in (False, True):
            family_reward(game, saved, claimed=claimed)
        unlinked = ending_save(game, shop_save(game, base, linked=False), save=True)
        family_states(game, unlinked, first_adventure=True)
        record('Actual saved linked ending isolates Ganon marker from general completion', game=name)

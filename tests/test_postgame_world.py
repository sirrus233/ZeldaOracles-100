"""Peaceful postgame populations, visuals, real dialogue, and quest isolation."""
import json
import re
import sys
from pathlib import Path
import test_postgame_chest as chest
from test_postgame_chest import Game, ROOT, SCRATCH
from test_heros_cave import load, walk, room, retail_rom
from test_ring_quests import quest_save, flag, finish_conversation, choose
from test_victory_ring import update_save
from emit_heart_patches import PROJECT, SOURCE

OUT = PROJECT / 'outputs' / 'Postgame Verification'
RESULTS = []
RESULT_FILE = 'world-results.json'


def record(test, **details):
    RESULTS.append(dict(test=test, status='passed', **details))
    (OUT / RESULT_FILE).write_text(json.dumps(RESULTS, indent=2))
    print(test, details, flush=True)


def actors(e, ids=None):
    return sorted((e.memory[slot+1], e.memory[slot+2], e.memory[slot+3],
                   e.memory[slot+11], e.memory[slot+13])
                  for slot in range(0xD040, 0xE000, 0x100)
                  if e.memory[slot] and (ids is None or e.memory[slot+1] in ids))


def save_image(game, e, label):
    game.screenshot(e, 'world-' + label)
    images = OUT / 'audit' / 'images'
    images.mkdir(parents=True, exist_ok=True)
    (images / f'{game.name}-{label}.png').write_bytes((SCRATCH / f'{game.name}-world-{label}.png').read_bytes())


def world_population(game, base):
    cases = ([(0, 0x3A, 0x68, 0x38, (0x36, 0x37), ((0x36, 0x13), (0x37, 0x11))),
              (0, 0x67, 0x58, 0x88, (0x6B,), ((0x6B, 0x15),))]
             if game.name == 'ages' else
             [(0, 0xD6, 0x68, 0x58, (0xA5, 0x4E), ((0xA5, 8), (0x4E, 0x0A)))])
    patched = game.rom
    for *position, ids, expected in cases:
        location = tuple(position)
        for linked in (False, True):
            for complete in (False, True):
                saved = quest_save(game, base, location, linked=linked, finished=complete,
                                    flags=(0x0B,), room_flags=((0, 0x3A, 0x40),) if game.name == 'ages' else ())
                # Original unlinked population and rendering is the reference for
                # the same completed-world actors, not the linked pre-clear world.
                with game.boot(saved) as e:
                    load(game, e, location)
                    actual = actors(e, ids)
                    assert sorted((a[0], a[1]) for a in actual) == (sorted(expected) if complete else []), (
                        game.name, location, linked, complete, actual)
                    assert not linked or not flag(game, e, game.finished_flag)
                    save_image(game, e, f'room-{location[1]:02x}-linked-{linked}-complete-{complete}')
                    image = e.screen.ndarray[16:144].tobytes()
                if not linked:
                    game.rom = retail_rom(game.name)
                    with game.boot(saved) as e:
                        load(game, e, location)
                        assert actors(e, ids) == actual
                        assert e.screen.ndarray[16:144].tobytes() == image, ('Game 1 rendering changed', game.name, location, complete)
                    game.rom = patched
                record('Peaceful actor set and original Game 1 behavior', game=game.name,
                       room=location[:2], linked=linked, complete=complete, actors=actual)


def talk_peaceful(game, base):
    # The animals below Nayru obstruct a direct southern approach.
    location = (0, 0x3A, 0x68, 0x40) if game.name == 'ages' else (0, 0xD6, 0x28, 0x58)
    for linked in ((True,) if '--bundle' in sys.argv else (False, True)):
        saved = quest_save(game, base, location, linked=linked, finished=True,
                           room_flags=((0, 0x3A, 0x40),) if game.name == 'ages' else ())
        if '--bundle' in sys.argv:
            saved = (OUT / 'saves' / f'{game.name.title()} - Linked clear - {"Nayru" if game.name == "ages" else "Din"}.sav').read_bytes()
        with game.boot(saved) as e:
            load(game, e, location)
            seen = []
            e.hook_register(0, game.address['showText'],
                            lambda _: seen.append((e.register_file.B << 8) | e.register_file.C), None)
            walk(game, e, 'up' if game.name == 'ages' else 'down', 30 if game.name == 'ages' else 20)
            if game.name == 'ages':
                walk(game, e, 'left', 8)
                walk(game, e, 'up', 2)
            game.press(e, 'a', 150)
            save_image(game, e, f'peaceful-dialogue-linked-{linked}')
            if not game.read(e, 'wTextIsActive'):
                print('Talk diagnostic', game.name, linked,
                      {key: game.read(e, key) for key in ['w1Link.yh', 'w1Link.xh', 'w1Link.direction',
                        'w1Link.state', 'wDisabledObjects', 'wMenuDisabled', 'wScrollMode', 'wTextIsActive',
                        'wLoadingRoomPack', 'wActiveCollisions', 'wTilesetFlags']},
                      [(hex(slot), bytes(e.memory[slot:slot+0x40]).hex()) for slot in range(0xD040, 0xE000, 0x100)
                       if e.memory[slot] and e.memory[slot+1] in (0x36, 0x37, 0xA5)], 'texts', seen, flush=True)
            assert game.read(e, 'wTextIsActive'), (game.name, 'peaceful dialogue did not open')
            expected_group = 0x1D if game.name == 'ages' else 0x3D
            # WRAM high text index includes the engine's +4 encoding.
            assert game.read(e, 'wTextIndexH_backup') == expected_group + 4
            expected_text = (0x1D23 if linked else 0x1D21) if game.name == 'ages' else (0x3D1A if linked else 0x3D18)
            assert expected_text in seen, (game.name, linked, 'wrong speech selected', seen)
            finish_conversation(game, e)
            assert not game.read(e, 'wDisabledObjects')
            record('Peaceful original/shortened speech opens and releases control', game=game.name, linked=linked,
                   actual_text_ids=seen)


def zora_gate(game, base):
    location = (5, 0x33, 0x38, 0x88)
    for linked, complete in ((False, True), (True, False), (True, True)):
        saved = quest_save(game, base, location, linked=linked, finished=complete)
        with game.boot(saved) as e:
            load(game, e, location)
            found = actors(e, (0xE7,))
            assert bool(found) == linked
            if linked:
                walk(game, e, 'up', 20)
                game.press(e, 'a', 150)
                choose(game, e, 0)
                choose(game, e, 0)
                e.tick(150, True)
                assert flag(game, e, 0x64)
                assert any(e.memory[7, game.address['w7SecretText1']:game.address['w7SecretText1'] + 5])
            else:
                assert not flag(game, e, 0x64)
            save_image(game, e, f'cave-zora-linked-{linked}-complete-{complete}')
            record('Cave Zora restricted to linked Seasons; native request preserved', linked=linked, complete=complete)


def statue_lifecycle(game, base):
    location = (0, 0x67, 0x58, 0x88)
    saved = quest_save(game, base, location, linked=True, finished=True)
    with game.boot(saved) as e:
        load(game, e, location)
        def check():
            assert [(x[0], x[1]) for x in actors(e, (0x6B,))] == [(0x6B, 0x15)]
            assert e.memory[game.address['wRoomCollisions'] + 0x35] == 0x0F
            return bytes(e.memory[3, game.address['w3VramTiles']:game.address['w3VramTiles'] + 0x300])
        tiles = check()
        game.pause_and_resume(e, 'start')
        assert check() == tiles, 'Pause changed statue base mapping'
        for direction, destination in [('right', (0, 0x68)), ('left', (0, 0x67))]:
            e.button_press(direction)
            for _ in range(240):
                e.tick(1, False)
                if room(game, e) == destination:
                    break
            e.button_release(direction)
            e.tick(100, True)
            assert room(game, e) == destination, ('Statue screen transition failed', direction, room(game, e))
        assert check() == tiles
        save_image(game, e, 'statue-after-return')
        saved = game.save_from_menu(e)
    with game.boot(saved) as e:
        load(game, e, location)
        assert check() == tiles
    record('Statue object, solid collision and base survive pause, adjacent-room return and save/reboot', game=game.name)


def native_secret_givers(game, base):
    specs = ([(0x3D, 4), (0xCB, 0), (0x4E, 3), (0xCD, 0), (0x4E, 4),
              (0x3B, 6), (0xD5, 0), (0xD6, 0), (0x66, 0x0F), (0x3D, 5)]
             if game.name == 'ages' else
             [(0xE7, 0), (0xD8, 0), (0xBC, 4), (0x30, 0x25), (0xCB, 3),
              (0xDB, 0), (0xDB, 1), (0xD5, 1), (0x3B, 7), (0xDB, 2)])
    locations = {}
    group = map_id = None
    for line in (SOURCE / f'objects/{game.name}/mainData.s').read_text().splitlines():
        if match := re.fullmatch(r'group([0-7])Map([0-9a-f]{2})ObjectData:', line):
            group, map_id = int(match[1]), int(match[2], 16)
        if match := re.search(r'obj_Interaction \$([0-9a-f]{2}) \$([0-9a-f]{2})', line):
            key = int(match[1], 16), int(match[2], 16)
            if key in specs:
                locations.setdefault(key, (group, map_id, 0x68, 0x50))
    assert len(locations) == 10, locations
    for index, (actor, subid) in enumerate(specs):
        location = locations[actor, subid]
        expected = None
        for complete in (False, True):
            saved = quest_save(game, base, location, linked=True, finished=complete,
                               flags=(0x0D, 0x18, 0x2D) if game.name == 'seasons' else (),
                               room_flags=((location[0], location[1], 0x40), (0, 0x81, 0x80)),
                               treasures=(0x41,))
            saved = update_save(game, saved, [('wTradeItem', 5, 0)])
            with game.boot(saved) as e:
                load(game, e, location)
                slots = [slot for slot in range(0xD040, 0xE000, 0x100)
                         if e.memory[slot] and e.memory[slot+1] == actor and e.memory[slot+2] == subid]
                assert len(slots) == 1, (game.name, index, location, complete, actors(e))
                slot = slots[0]
                state = (e.memory[slot+0x18] | e.memory[slot+0x19] << 8,
                         e.memory[slot+0x3E], e.memory[slot+0x3F])
                if game.name == 'ages':
                    assert state[2] == index
                elif index != 8:
                    assert state[1] == index
                if complete:
                    assert state == expected, (game.name, index, 'giver role changed after clear', expected, state)
                else:
                    expected = state
        record('Original linked secret giver retains native role after clear', game=game.name,
               secret_index=index, actor=actor, subid=subid, room=location[:2], script_state=state,
               coverage='Spawn, secret index and waiting script match pre-clear; not a conversation replay')


def seasons_tree(game, base):
    location = (2, 0x5E, 0x68, 0x50)
    saved = quest_save(game, base, location, linked=True, finished=True,
                       room_flags=((5, 0x9D, 0x40),))
    saved = update_save(game, saved, [('wc6e5', 9, 0)])
    with game.boot(saved) as e:
        load(game, e, location)
        assert game.read(e, 'ws_cc39') == 0x0E
        assert not actors(e, (0xE1,)), 'Room of Rites portal remains after saved clear'
        assert e.memory[game.address['wRoomLayout'] + 0x67] == 0x01
        game.pause_and_resume(e, 'start')
        for direction, group in [('down', 0), ('up', 2)]:
            e.button_press(direction)
            for _ in range(240):
                e.tick(1, False)
                if room(game, e)[0] == group:
                    break
            e.button_release(direction)
            e.tick(100, True)
            assert room(game, e)[0] == group
        assert room(game, e) == location[:2]
        assert not actors(e, (0xE1,))
        assert e.memory[game.address['wRoomLayout'] + 0x67] == 0x01
        assert game.read(e, 'ws_cc39') == 0x0E
        save_image(game, e, 'peaceful-tree-closed-portal-after-return')
        record('Peaceful Seasons tree stays full-grown with Room of Rites closed after pause/return', game=game.name)


if __name__ == '__main__':
    from pyboy import PyBoy
    chest.PyBoy = PyBoy
    if '--bundle' in sys.argv:
        RESULT_FILE = 'packaged-world-results.json'
        for name, label, location, wanted in [
            ('ages', 'Linked clear - Statue', (0, 0x67, 0x58, 0x88), (0x6B, 0x15)),
            ('ages', 'Linked clear - Nayru', (0, 0x3A, 0x68, 0x40), (0x36, 0x13)),
            ('seasons', 'Linked clear - Din', (0, 0xD6, 0x28, 0x58), (0xA5, 8)),
            ('seasons', 'First adventure - Cave without Zora', (5, 0x33, 0x38, 0x88), None),
            ('seasons', 'Linked clear - Cave Zora', (5, 0x33, 0x38, 0x88), (0xE7, 0)),
        ]:
            game = Game(name)
            game.rom = (OUT / f'{name.title()}.gbc').read_bytes()
            saved = (OUT / 'saves' / f'{name.title()} - {label}.sav').read_bytes()
            with game.boot(saved) as e:
                load(game, e, location)
                if wanted:
                    assert wanted in [(row[0], row[1]) for row in actors(e)]
                    assert not flag(game, e, game.finished_flag)
                    assert not game.read(e, 'wFileIsCompleted')
                else:
                    assert not actors(e, (0xE7,))
                assert not game.read(e, 'wDisabledObjects'), 'Manual scene starts with controls disabled'
                save_image(game, e, 'packaged-' + label.replace(' ', '-'))
            record('Packaged manual checkpoint loads with intended role and controls', game=name, scenario=label)
        for name in ('ages', 'seasons'):
            game = Game(name)
            game.rom = (OUT / f'{name.title()}.gbc').read_bytes()
            talk_peaceful(game, game.new_file())
        for complete in (False, True):
            game = Game('ages')
            game.rom = (OUT / 'Ages.gbc').read_bytes()
            label = ('Linked clear' if complete else 'Before final clear') + ' - Past town'
            saved = (OUT / 'saves' / f'Ages - {label}.sav').read_bytes()
            with game.boot(saved) as e:
                load(game, e, (1, 0x65, 0x58, 0x58))
                present = {(row[0], row[1]) for row in actors(e)}
                for target in ((0x37, 0x12), (0x4D, 0x0A)):
                    assert (target in present) == (not complete), (label, target, present)
                assert flag(game, e, 2) == complete
                assert not game.read(e, 'wDisabledObjects')
            record('Packaged past-town rescue roles retire only after saved clear', complete=complete)
        sys.exit(0)
    for name in ('ages', 'seasons'):
        game = Game(name)
        base = game.new_file()
        if '--talk-only' not in sys.argv:
            world_population(game, base)
            if name == 'ages':
                statue_lifecycle(game, base)
        talk_peaceful(game, base)
        if name == 'seasons':
            zora_gate(game, base)
            if '--talk-only' not in sys.argv:
                seasons_tree(game, base)
        if '--givers' in sys.argv:
            native_secret_givers(game, base)

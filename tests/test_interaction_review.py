"""Additional controller-driven probes for the cumulative interaction review."""
import json
import sys

import test_postgame_chest as chest
from test_postgame_chest import Game, ROOT
from test_ring_quests import quest_save, choose, flag
from test_ring_quests import continue_text, finish_conversation
from test_heros_cave import load, walk
from emit_heart_patches import PROJECT
from test_victory_ring import update_save, shop_save, SHOPS, credits_fixture

OUT = PROJECT / 'outputs' / 'Postgame Verification' / 'audit'


def cave_zora():
    from test_postgame_world import zora_gate
    game = Game('seasons')
    zora_gate(game, game.new_file())


def complete_ending(name):
    game = Game(name)
    location = SHOPS[name]
    saved = shop_save(game, game.new_file(), linked=True, finished=False)
    edits = [('wActiveRing', 1, 0), ('wRingBoxContents', 1, 0),
             ('wObtainedRingBox', 1, 0), ('wRingBoxLevel', 1, 0)]
    if name == 'seasons':
        edits.append(('wc6e5', 9, 0))
    saved = update_save(game, saved, edits)
    with game.boot(saved) as e:
        load(game, e, location)
        inventory_address = game.address['wInventoryB']
        original = bytes(e.memory[inventory_address:game.address['wInventoryStorage'] + 16])
        print(name, 'ring before credits', game.read(e, 'wActiveRing'), flush=True)
        # Start before the native credits equipment backup / ring disable,
        # considerably earlier than the existing stage-3 save boundary test.
        credits_fixture(game, e)
        e.memory[0xCBC1] = 0
        e.memory[0xCBC2] = 0
        e.memory[game.address['wTmpcbb3']] = 1
        last = None
        for batch in range(400):
            e.tick(120, False)
            state = tuple(e.memory[0xC2EE:0xC2F0]) + tuple(e.memory[0xCBC1:0xCBC3])
            if state != last:
                print(name, batch * 120, 'ending-state', state, 'ring', game.read(e, 'wActiveRing'), flush=True)
                last = state
            if game.read(e, 'wTextIsActive') and game.read(e, 'wTextIndexH_backup') == 0x59:
                break
            # Only advance text / the final secret screen, allowing credits to run.
            if game.read(e, 'wTextIsActive') or state[1] == 0x0A and state[2] == 3 and state[3] >= 3:
                game.press(e, 'a', 30)
        else:
            game.screenshot(e, 'review-ending-timeout')
            raise AssertionError((name, 'full ending stalled', last))
        game.screenshot(e, 'review-full-ending-save')
        print(name, 'ring before save prompt', game.read(e, 'wActiveRing'), flush=True)
        choose(game, e, 1)
        e.tick(180, True)
        actual = game.save_bytes(e)
        ring_offset = 0x10 + game.address['wActiveRing'] - game.address['wFileStart']
        print(name, 'ring on disk', actual[ring_offset], flush=True)
        symbols = sorted((address, symbol) for symbol, address in game.address.items()
                         if game.address['wFileStart'] <= address < game.address['wFileStart'] + 0x550)
        changes = []
        for offset, (before, after) in enumerate(zip(saved[0x10:0x560], actual[0x10:0x560])):
            if before == after:
                continue
            address = game.address['wFileStart'] + offset
            nearest = max((row for row in symbols if row[0] <= address), default=(address, 'unknown'))
            changes.append(dict(address=f'{address:04x}', field=nearest[1], offset=address - nearest[0],
                                before=before, after=after))
        (OUT / f'{name}-credits-save-byte-changes.json').write_text(json.dumps(changes, indent=2))
    with game.boot(actual) as e:
        game.press(e, 'a')
        game.press(e, 'a', 180)
        assert bytes(e.memory[inventory_address:game.address['wInventoryStorage'] + 16]) == original
        # Native credits actors overwrite wActiveRing (including Fist Ring),
        # then clear it. The new linked completion save persists that result.
        assert game.read(e, 'wActiveRing') == 0xFF, (name, 'ring after reload', game.read(e, 'wActiveRing'))
        assert game.read(e, 'wRingBoxContents') == 1
        assert game.read(e, 'wLinkHealth') == game.read(e, 'wLinkMaxHealth')
        assert flag(game, e, 2)
        assert not flag(game, e, game.finished_flag)
        assert not game.read(e, 'wFileIsCompleted')
        from test_heros_cave import room
        expected = (0, 0x38) if name == 'ages' else (2, 0x5E)
        assert room(game, e) == expected
        result = dict(game=name, test='Full native credits, completion save and reboot',
                      passed=True, equipment_preserved=True, active_ring_before=1, active_ring_after=255,
                      boxed_ring_preserved=True, health_restored=True,
                      specific_clear_flag=True, broad_completion_markers=False,
                      fixture='Prepared linked file, credits stage 0 before native equipment backup and ring disable; all subsequent actions use controller input. Boss fight and collapse not replayed.')
        (OUT / f'{name}-full-ending.json').write_text(json.dumps(result, indent=2))
        print(result, flush=True)


def full_ring_bag(name):
    game = Game(name)
    saved = shop_save(game, game.new_file(), linked=True, finished=True)
    saved = update_save(game, saved, [('wUnappraisedRings', 0x40, i) for i in range(64)]
                        + [('wNumUnappraisedRingsBcd', 0x64, 0)])
    with game.boot(saved) as e:
        load(game, e, SHOPS[name])
        walk(game, e, 'up', 48)
        game.press(e, 'a', 100)
        address = game.address['wUnappraisedRings']
        continue_text(game, e, lambda: 0x76 in bytes(e.memory[address:address + 64]))
        rings = bytes(e.memory[address:address + 64])
        assert rings.count(0x76) == 1 and rings.count(0x40) == 63
        assert game.read(e, 'wNumUnappraisedRingsBcd') == 0x64
        assert flag(game, e, 6)
        finish_conversation(game, e)
        actual = game.save_from_menu(e)
    with game.boot(actual) as e:
        load(game, e, SHOPS[name])
        assert bytes(e.memory[address:address + 64]) == rings
        assert flag(game, e, 6)
    result = dict(game=name, test='Victory Ring with 64 unappraised duplicates, native grant and save/reboot',
                  passed=True, ring_count=64, victory_count=1, displaced_duplicate_count=1)
    (OUT / f'{name}-full-ring-bag.json').write_text(json.dumps(result, indent=2))
    print(result, flush=True)


if __name__ == '__main__':
    from pyboy import PyBoy
    chest.PyBoy = PyBoy
    if '--bag' in sys.argv:
        for name in ('ages', 'seasons'):
            full_ring_bag(name)
    elif '--ending' in sys.argv:
        for name in (('seasons',) if '--seasons-only' in sys.argv else ('ages', 'seasons')):
            complete_ending(name)
    else:
        cave_zora()

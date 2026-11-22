"""Keep the rescue roles before Ganon; retire them in the saved postgame."""
import json
import sys
import test_postgame_chest as chest
from test_postgame_chest import Game, ROOT
from test_heros_cave import load, walk
from test_ring_quests import quest_save, finish_conversation
from emit_heart_patches import PROJECT

OUT = PROJECT / 'outputs' / 'Postgame Verification' / 'audit'
RESULTS = []


def record(**row):
    RESULTS.append(dict(status='passed', **row))
    (OUT / 'rescue-role-results.json').write_text(json.dumps(RESULTS, indent=2))
    print(row, flush=True)


def test_roles():
    game = Game('ages')
    base = game.new_file()
    for actor, subid, x, text in [(0x37, 0x12, 0x58, 0x2A23), (0x4D, 0x0A, 0x38, 0x131A)]:
        location = (1, 0x65, 0x58, x)
        for linked in (False, True):
            for complete in (False, True):
                for veran in (False, True):
                    saved = quest_save(game, base, location, linked=linked, finished=complete,
                                       flags=(0x11, 0x13, 0x33, 0x39),
                                       room_flags=((4, 0xFC, 0x80),) if veran else ())
                    with game.boot(saved) as e:
                        load(game, e, location)
                        slots = [slot for slot in range(0xD040, 0xE000, 0x100)
                                 if e.memory[slot] and e.memory[slot+1] == actor and e.memory[slot+2] == subid]
                        visible = linked and veran and not complete
                        assert bool(slots) == visible, (actor, linked, complete, veran, slots)
                        if visible:
                            seen = []
                            e.hook_register(0, game.address['showText'],
                                lambda _: seen.append(e.register_file.B << 8 | e.register_file.C), None)
                            walk(game, e, 'up', 24)
                            game.press(e, 'a', 160)
                            assert text in seen
                            finish_conversation(game, e)
                            assert not game.read(e, 'wDisabledObjects')
                    record(test='Emergency role eligibility and original pre-Ganon dialogue',
                           actor=actor, linked=linked, complete=complete, veran_defeated=veran,
                           present=visible)

    # The retained peaceful version still speaks normally after the clear.
    location = (0, 0x3A, 0x48, 0x78)
    saved = quest_save(game, base, location, linked=True, finished=True,
                       room_flags=((0, 0x3A, 0x40), (4, 0xFC, 0x80)))
    with game.boot(saved) as e:
        load(game, e, location)
        assert any(e.memory[s] and e.memory[s+1] == 0x37 and e.memory[s+2] == 0x11
                   for s in range(0xD040, 0xE000, 0x100))
        seen = []
        e.hook_register(0, game.address['showText'],
                       lambda _: seen.append(e.register_file.B << 8 | e.register_file.C), None)
        walk(game, e, 'left', 24)
        game.press(e, 'a', 160)
        assert 0x2A21 in seen, seen
        finish_conversation(game, e)
        assert not game.read(e, 'wDisabledObjects')
    record(test='Peaceful Ralph retains original training/Nayru speech', actual_text=0x2A21)


if __name__ == '__main__':
    from pyboy import PyBoy
    chest.PyBoy = PyBoy
    test_roles()

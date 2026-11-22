"""Real tree conversations and map-advice persistence across Ages completion."""
import json
import sys
import test_postgame_chest as chest
from test_postgame_chest import Game, ROOT, SCRATCH
from test_heros_cave import load, walk
from test_ring_quests import quest_save, flag, finish_conversation
from emit_heart_patches import PROJECT

OUT = PROJECT / 'outputs/Postgame Verification/audit'

def main():
    game = Game('ages')
    if '--bundle' in sys.argv:
        game.rom = (PROJECT / 'outputs/Postgame Verification/Ages.gbc').read_bytes()
    base = game.new_file()
    rows = []
    for group in (0, 1):
        location = (0, 0x38, 0x68, 0x48) if group == 0 else (1, 0x38, 0x58, 0x50)
        for linked in (False, True):
            for complete in (False, True):
                label = ('Linked clear' if complete else 'Before final clear') + (' - Maku Tree' if group == 0 else ' - Maku Sprout')
                saved = quest_save(game, base, location, linked=linked, finished=complete,
                                   flags=(0x11, 0x13, 0x33, 0x39),
                                   room_flags=((1, 0x48, 1), (4, 0xFC, 0x80)))
                if '--bundle' in sys.argv and linked:
                    saved = (PROJECT / 'outputs/Postgame Verification/saves' / f'Ages - {label}.sav').read_bytes()
                expected = (0x51c if group == 0 else 0x58c) if complete or not linked else (0x53a if group == 0 else 0x5aa)
                advice = 'wMakuMapTextPresent' if group == 0 else 'wMakuMapTextPast'
                with game.boot(saved) as e:
                    load(game, e, location)
                    assert game.read(e, 'wMakuTreeState') == 0x10
                    assert bool(flag(game, e, 2)) == (linked and complete)
                    assert bool(flag(game, e, game.finished_flag)) == (complete and not linked)
                    seen = []
                    e.hook_register(0, game.address['showText'],
                        lambda _: seen.append(e.register_file.B << 8 | e.register_file.C), None)
                    walk(game, e, 'up', 38 if group == 0 else 48)
                    if group == 0:
                        walk(game, e, 'right', 2)
                        walk(game, e, 'up', 2)
                    for repeat in range(2):
                        game.press(e, 'a', 160)
                        # Sprout's second pre-completion conversation uses the next alias.
                        assert seen[-1] == expected + (repeat if linked and not complete and group == 1 else 0), seen
                        finish_conversation(game, e)
                        assert not game.read(e, 'wDisabledObjects')
                        assert game.read(e, advice) == (seen[-1] & 0xff)
                        game.pause_and_resume(e, 'start')
                    game.screenshot(e, f'maku-completion-{group}-{linked}-{complete}')
                    (OUT / f'maku-{group}-{linked}-{complete}.png').write_bytes(
                        (SCRATCH / f'ages-maku-completion-{group}-{linked}-{complete}.png').read_bytes())
                    resaved = game.save_from_menu(e)
                with game.boot(resaved) as e:
                    load(game, e, location)
                    assert game.read(e, advice) == (expected & 0xff) + (1 if linked and not complete and group == 1 else 0)
                    assert not game.read(e, 'wDisabledObjects')
                rows.append(dict(status='passed', group=group, linked=linked, complete=complete,
                                 text_ids=seen, pause_and_repeat=True, save_reboot=True))
                print(rows[-1], flush=True)
                (OUT / ('packaged-maku-results.json' if '--bundle' in sys.argv else 'maku-results.json')).write_text(json.dumps(rows, indent=2))

if __name__ == '__main__':
    from pyboy import PyBoy
    chest.PyBoy = PyBoy
    main()

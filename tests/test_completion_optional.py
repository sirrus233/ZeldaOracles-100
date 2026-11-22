"""Check optional trade progress and NPC presence across the new completion boundary."""
import json
import os
import sys
import test_postgame_chest as chest
from emit_heart_patches import PROJECT
from test_postgame_chest import Game, ROOT, SCRATCH
from test_heros_cave import load, walk
from test_ring_quests import quest_save, choose, continue_text, finish_conversation
from test_victory_ring import update_save

OUT = PROJECT / 'outputs' / 'Postgame Verification' / 'audit'
OUT.mkdir(parents=True, exist_ok=True)
RESULTS = []

def record(label, **details):
    RESULTS.append(dict(test=label, status='passed', **details))
    (OUT / 'optional-results.json').write_text(json.dumps(RESULTS, indent=2))
    print(label, details, flush=True)


def optional_trade(game, base, finished):
    location = (2, 0xE7, 0x1A, 0x38) if game.name == 'ages' else (0, 8, 0x68, 0x50)
    saved = quest_save(game, base, location, finished=finished, linked=True, treasures=(0x41,))
    saved = update_save(game, saved, [('wTradeItem', 4, 0)])
    with game.boot(saved) as emulator:
        load(game, emulator, location)
        if game.name == 'seasons':
            game.screenshot(emulator, 'audit-biggoron-before')
            print('Biggoron before', [(hex(slot), list(emulator.memory[slot:slot+3]), emulator.memory[slot+11], emulator.memory[slot+13]) for slot in range(0xD040, 0xE000, 0x100) if emulator.memory[slot]], flush=True)
        walk(game, emulator, 'left' if game.name == 'ages' else 'up', 48 if game.name == 'ages' else 5)
        game.press(emulator, 'a', 100)
        try:
            choose(game, emulator, 0)
        except AssertionError:
            game.screenshot(emulator, 'audit-optional-no-trade')
            print('trade state', game.name, finished, game.read(emulator, 'wTradeItem'), game.read(emulator, 'wTextIsActive'), game.read(emulator, 'w1Link.yh'), flush=True)
            raise
        continue_text(game, emulator, lambda: game.read(emulator, 'wTradeItem') == 5)
        finish_conversation(game, emulator)
        saved = game.save_from_menu(emulator)
    with game.boot(saved) as emulator:
        game.press(emulator, 'a')
        game.press(emulator, 'a', 180)
        assert game.read(emulator, 'wTradeItem') == 5
    record('Optional trade remains completable across Game 2 completion', game=game.name, postgame=finished,
           trade='Doggie Mask to Dumbbell' if game.name == 'ages' else 'Lava Soup to Goron Vase')


def family_boundary(game, base):
    location = (2, 0xEA, 0x68, 0x50) if game.name == 'ages' else (1, 0x92, 0x68, 0x50)
    counts = []
    for finished in (False, True):
        saved = quest_save(game, base, location, linked=True, finished=finished)
        saved = update_save(game, saved, [('wChildStage', 8, 0), ('wNextChildStage', 8, 0),
                                         ('wChildPersonality', 2, 0)])
        with game.boot(saved) as emulator:
            load(game, emulator, location)
            ids = [emulator.memory[slot + 1] for slot in range(0xD040, 0xE000, 0x100)
                   if emulator.memory[slot] and emulator.memory[slot + 1] != 0xAC]
            counts.append(len(ids))
            game.screenshot(emulator, f'audit-family-{finished}')
    assert counts[0] > 0 and counts[1] == counts[0], (game.name, counts)
    record('Family remains after linked completion', game=game.name,
           actors_before=counts[0], actors_after=counts[1],
           consequence='General world completion stays unset in linked games')


if __name__ == '__main__':
    for variable in ('TMP', 'TEMP', 'TMPDIR', 'APPDATA', 'LOCALAPPDATA', 'XDG_CACHE_HOME'):
        os.environ[variable] = str(SCRATCH)
    from pyboy import PyBoy
    chest.PyBoy = PyBoy
    for name in ('ages', 'seasons'):
        if '--seasons' in sys.argv and name != 'seasons':
            continue
        game = Game(name)
        base = game.new_file()
        for finished in (False, True):
            optional_trade(game, base, finished)
        family_boundary(game, base)

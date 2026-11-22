"""Exercise both orders of Game 1's chest/heart secret, then the real return password."""
import json
import os
import sys
import test_postgame_chest as chest
from emit_heart_patches import PROJECT
from test_postgame_chest import Game, ROOT, SCRATCH
from test_heros_cave import load, walk
from test_ring_quests import quest_save, choose, continue_text, finish_conversation, flag, enter_password
from test_victory_ring import update_save
from test_completion_dependencies import generate, farore_save, talk_farore

OUT = PROJECT / 'outputs' / 'Postgame Verification' / 'audit'
OUT.mkdir(parents=True, exist_ok=True)
RESULTS = []

def record(label, **details):
    RESULTS.append(dict(test=label, status='passed', **details))
    (OUT / 'heart-sequence-results.json').write_text(json.dumps(RESULTS, indent=2))
    print(label, details, flush=True)


def relocate(game, saved, location):
    return update_save(game, saved, [(f'wDeathRespawnBuffer.{key}', value, 0)
                                    for key, value in zip(('group', 'room', 'y', 'x'), location)])


def chest_pickup(game, saved, hearts):
    location = game.group, game.room, 0x68, 0x50
    with game.boot(relocate(game, saved, location)) as emulator:
        load(game, emulator, location)
        game.open_chest(emulator)
        game.dismiss_pickup_text(emulator)
        assert game.read(emulator, 'wLinkMaxHealth') == (hearts + 1) * 4
        return game.save_from_menu(emulator)


def heart_quest(game, saved, hearts):
    location = (0, 0x70, 0x68, 0x48) if game.name == 'ages' else (1, 0xBA, 0x48, 0x50)
    secret = 1 if game.name == 'ages' else 0x21
    done = 0x6F if game.name == 'ages' else 0x5B
    password = generate(game, saved, 3, secret)
    with game.boot(relocate(game, saved, location)) as emulator:
        load(game, emulator, location)
        walk(game, emulator, 'up', 48)
        game.press(emulator, 'a', 100)
        choose(game, emulator, 0)
        continue_text(game, emulator, lambda: game.read(emulator, 'wOpenedMenuType') == 6)
        enter_password(game, emulator, password)
        if game.name == 'seasons':
            choose(game, emulator, 0)  # Accept the ghost-counting game.
            emulator.tick(160, True)
            choose(game, emulator, 0)  # Understand the explanation.
            emulator.tick(160, True)
            slot, = [slot for slot in range(0xD040, 0xE000, 0x100)
                     if emulator.memory[slot] and list(emulator.memory[slot + 1:slot + 3]) == [0xCB, 0]]
            for round_index in range(3):
                try:
                    continue_text(game, emulator, lambda: game.read(emulator, 'wTextIsActive')
                              and emulator.memory[slot + 5] == 3
                              and emulator.memory[slot + 0x3A] == round_index
                              and game.read(emulator, 'wTextDisplayMode') == 1
                              and emulator.memory[7, game.address['w7TextDisplayState']] == 2)
                except AssertionError:
                    print('Ghini state', round_index, game.read(emulator, 'wTextIndexH_backup'), emulator.memory[7, game.address['w7TextIndexL_backup']], list(emulator.memory[slot+0x3A:slot+0x40]), flush=True)
                    raise
                # Use the game's recorded answer as the test oracle; no game state
                # is changed. This tests normal rounds/reward, not visual counting.
                choose(game, emulator, emulator.memory[slot + 0x3C] ^ 1)
        continue_text(game, emulator, lambda: flag(game, emulator, done))
        assert game.read(emulator, 'wLinkMaxHealth') == (hearts + 1) * 4
        start = game.address['w7SecretText1']
        return_password = bytes(emulator.memory[7, start:start + 5])
        if game.name == 'seasons':
            choose(game, emulator, 0)  # Understand the return secret.
        finish_conversation(game, emulator)
        saved = game.save_from_menu(emulator)
    return saved, return_password


def return_to_second(first, password):
    second = 'seasons' if first == 'ages' else 'ages'
    game = Game(second)
    saved, location = farore_save(game, game.new_file(), finished=True, index=1)
    with game.boot(saved) as emulator:
        load(game, emulator, location)
        talk_farore(game, emulator)
        enter_password(game, emulator, password)
        waiting = False
        for _ in range(90):
            if flag(game, emulator, (0x5A if second == 'ages' else 0x6E) + 1):
                break
            if flag(game, emulator, 0x2C) and not waiting:
                finish_conversation(game, emulator)
                game.move_to(emulator, 'x', 0x78, 'left', 'right')
                walk(game, emulator, 'down', 50)
                game.move_to(emulator, 'y', 0x89, 'up', 'down')
                game.move_to(emulator, 'x', 0x58, 'left', 'right')
                walk(game, emulator, 'up', 10)
                waiting = True
            game.press(emulator, 'a', 90)
        assert game.read(emulator, 'wLinkMaxHealth') == 64
        finish_conversation(game, emulator)
        saved = game.save_from_menu(emulator)
    with game.boot(saved) as emulator:
        game.press(emulator, 'a')
        game.press(emulator, 'a', 180)
        assert game.read(emulator, 'wLinkMaxHealth') == 64
    record('Actual Game 1 heart-quest return password gives Game 2 its sixteenth heart', first=first)


if __name__ == '__main__':
    for variable in ('TMP', 'TEMP', 'TMPDIR', 'APPDATA', 'LOCALAPPDATA', 'XDG_CACHE_HOME'):
        os.environ[variable] = str(SCRATCH)
    from pyboy import PyBoy
    chest.PyBoy = PyBoy
    for first in ('ages', 'seasons'):
        if '--seasons' in sys.argv and first != 'seasons':
            continue
        game = Game(first)
        base = game.new_file()
        for chest_first in (True, False):
            saved = quest_save(game, base, (game.group, game.room, 0x68, 0x50))
            assert saved
            if chest_first:
                saved = chest_pickup(game, saved, 14)
                saved, password = heart_quest(game, saved, 15)
            else:
                saved, password = heart_quest(game, saved, 14)
                saved = chest_pickup(game, saved, 15)
            with game.boot(saved) as emulator:
                game.press(emulator, 'a')
                game.press(emulator, 'a', 180)
                assert game.read(emulator, 'wLinkMaxHealth') == 64
            record('Game 1 reaches sixteen hearts with both reward orders', game=first, chest_first=chest_first)
            return_to_second(first, password)

"""Native secret input helpers and the current paired-ring regression suite."""
import os,sys
from heapq import heappop,heappush
import test_postgame_chest as chest
from emit_heart_patches import PROJECT,SOURCE,apply_patch
from test_heros_cave import fixture,load,room,walk
from test_postgame_chest import Game,ROOT,SAVE_SLOT_COPIES,SAVE_SLOT_LENGTH,SCRATCH

def quest_save(game, base, location, *, linked=False, finished=True, flags=(), room_flags=(),
               essences=0xFF, equipped=True, treasures=()):
    # In a linked fixture "finished" means a saved Ganon clear, not Game 1's
    # general world/file completion state. No quest reward flags are implied.
    result = fixture(game, base, location, finished=finished and not linked, linked=linked, equipped=equipped)
    if linked and finished:
        flags = (2, *flags)
    start = game.address['wFileStart']
    saved = result[0x10:0x10 + SAVE_SLOT_LENGTH]
    offset = game.address['wGameID'] - start
    saved[offset:offset + 2] = b'\x34\x12'
    saved[game.address['wEssencesObtained'] - start] = essences
    if essences:
        saved[game.address['wObtainedTreasureFlags'] - start + 0x40 // 8] |= 1 << (0x40 % 8)
    for treasure in treasures:
        offset = game.address['wObtainedTreasureFlags'] - start + treasure // 8
        saved[offset] |= 1 << (treasure % 8)
    for flag in flags:
        offset = game.address['wGlobalFlags'] - start + flag // 8
        saved[offset] |= 1 << (flag % 8)
    for group, map_id, value in room_flags:
        flags_group = group & 1 if game.name == 'ages' and group < 4 else group
        offset = game.address[f'wGroup{flags_group}RoomFlags'] - start + map_id
        saved[offset] |= value
    checksum = sum(int.from_bytes(saved[i:i + 2], 'little') for i in range(2, len(saved), 2))
    saved[:2] = (checksum & 0xFFFF).to_bytes(2, 'little')
    for offset in SAVE_SLOT_COPIES:
        result[offset:offset + SAVE_SLOT_LENGTH] = saved
    return result

def continue_text(game, emulator, until, limit=100):
    for _ in range(limit):
        if until():
            return
        game.press(emulator, 'a', 90)
    game.screenshot(emulator, 'ring-dialogue-failed')
    raise AssertionError((game.name, 'dialogue timeout', room(game, emulator)))

def choose(game, emulator, option):
    # Advance preceding pages until the choice is visible.
    for _ in range(20):
        emulator.tick(100, False)
        if (game.read(emulator, 'wTextDisplayMode') == 1
                and emulator.memory[7, game.address['w7TextDisplayState']] == 2):
            break
        game.press(emulator, 'a', 30)
    else:
        raise AssertionError('no choice in dialogue')
    emulator.tick(80, True)
    selected = emulator.memory[7, game.address['w7SelectedTextOption']]
    if selected != option:
        game.press(emulator, 'right', 12)
    if emulator.memory[7, game.address['w7SelectedTextOption']] != option:
        game.press(emulator, 'right', 12)
    if emulator.memory[7, game.address['w7SelectedTextOption']] != option:
        game.screenshot(emulator, 'ring-choice-failed')
        raise AssertionError((selected, option, game.read(emulator, 'wTextDisplayMode'),
                              emulator.memory[7, game.address['w7TextDisplayState']],
                              bytes(emulator.memory[7, game.address['w7TextboxOptionPositions']:
                                                    game.address['w7TextboxOptionPositions'] + 8]).hex()))
    game.press(emulator, 'a', 30)

def enter_password(game, emulator, password):
    assert game.read(emulator, 'wOpenedMenuType') == 6, ('secret menu', game.read(emulator, 'wOpenedMenuType'))
    emulator.tick(110, True)
    if game.read(emulator, 'wFileSelect.mode2') == 4:
        game.press(emulator, 'a', 30)
    for _ in range(5):
        game.press(emulator, 'b', 9)
    tilemap = game.address['w4TileMap']
    symbols = bytes(emulator.memory[game.address['secretSymbols']:game.address['secretSymbols'] + 64])
    for character in password:
        choices = {}
        for row in range(5):
            for col in range(13):
                offset = col + int(col >= 8)
                tile = emulator.memory[4, tilemap + 0xA3 + row * 64 + offset]
                value = symbols[(tile >> 1) & 0x3F]
                choices.setdefault(value, (row, col))
        target_row, target_col = choices[character]
        cursor = game.read(emulator, 'wFileSelect.cursorPos')
        for _ in range(6):
            if cursor // 16 == target_row:
                break
            game.press(emulator, 'up', 9)
            cursor = game.read(emulator, 'wFileSelect.cursorPos')
        for _ in range(13):
            if cursor % 16 == target_col:
                break
            game.press(emulator, 'right', 9)
            cursor = game.read(emulator, 'wFileSelect.cursorPos')
        assert cursor == target_row * 16 + target_col
        game.press(emulator, 'a', 12)
    game.screenshot(emulator, 'ring-password-entry')
    game.press(emulator, 'start', 12)
    game.press(emulator, 'a', 100)

def flag(game, emulator, index):
    return bool(emulator.memory[game.address['wGlobalFlags'] + index // 8] & (1 << (index % 8)))

def finish_text(game, emulator):
    for _ in range(48):
        if not game.read(emulator, 'wTextIsActive'):
            return
        game.press(emulator, 'a', 100)
    raise AssertionError('text did not finish')

def finish_conversation(game, emulator):
    for _ in range(48):
        if not game.read(emulator, 'wTextIsActive') and not game.read(emulator, 'wDisabledObjects'):
            return
        game.press(emulator, 'a', 90)
    raise AssertionError('NPC did not return control')

def talk(game, emulator, direction='up'):
    walk(game, emulator, direction, 48)
    game.press(emulator, 'a', 120)

def test_diving_course_failure(game, base):
    layouts = [(SOURCE / 'rooms' / 'seasons' / 'large'
                / f'room06{map_id:02x}.bin').read_bytes() for map_id in (0xE8, 0xE9, 0xEA)]
    start, goal = (6, 3), (42, 1)
    previous = {start: None}
    costs = {start: 0}
    queue = [(0, start)]
    while queue and goal not in previous:
        cost, (x, y) = heappop(queue)
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y - 1), (x, y + 1)):
            if not (0 <= nx < 45 and 0 <= ny < 11):
                continue
            tile = layouts[nx // 15][ny * 16 + nx % 15]
            if tile in (0x3D, 0x2D, 0x2E, 0x59, 0x5A) or (tile == 1 and nx < 38):
                continue
            next_cost = cost + (5 if tile in (0x1D, 0x1E, 0x1F) else 1)
            if next_cost < costs.get((nx, ny), 10000):
                costs[nx, ny] = next_cost
                previous[nx, ny] = (x, y)
                heappush(queue, (next_cost, (nx, ny)))
    assert goal in previous
    path = []
    point = goal
    while point:
        path.append(point)
        point = previous[point]
    location = (7, 0xE8, 0x18, 0x68)
    with game.boot(quest_save(game, base, location, linked=False, flags=(0x53,))) as emulator:
        load(game, emulator, location)
        finish_text(game, emulator)
        frame = 0
        active_direction = None
        for x, y in reversed(path):
            map_id = 0xE8 + x // 15
            target_y, target_x = y * 16 + 4, x % 15 * 16 + 4
            if x >= 38 and y <= 1:
                target_y += 4
                target_x += 4
            if (x, y) == goal:
                emulator.button('b', 1)  # Jump from the ladder onto the prize ledge.
            for _ in range(130):
                current = room(game, emulator)[1]
                current_y = game.read(emulator, 'w1Link.yh')
                current_x = game.read(emulator, 'w1Link.xh')
                tolerance = 3 if (x, y) == goal else 8
                if current == map_id and abs(current_y - target_y) <= tolerance and abs(current_x - target_x) <= tolerance:
                    break
                if current < map_id:
                    direction = 'right'
                elif current > map_id:
                    direction = 'left'
                elif abs(current_x - target_x) > tolerance:
                    direction = 'right' if current_x < target_x else 'left'
                else:
                    direction = 'down' if current_y < target_y else 'up'
                if direction != active_direction:
                    if active_direction:
                        emulator.button_release(active_direction)
                    emulator.button_press(direction)
                    active_direction = direction
                if frame % 4 == 0 and game.read(emulator, 'wLinkSwimmingState'):
                    emulator.button('a', 1)
                emulator.tick(1, False)
                frame += 1
                if (x, y) == goal and game.read(emulator, 'wTextIsActive'):
                    break
                if room(game, emulator)[1] != current:
                    emulator.button_release(active_direction)
                    active_direction = None
                    emulator.tick(95, False)
            else:
                emulator.tick(1, True)
                game.screenshot(emulator, 'ring-course-stuck')
                raise AssertionError(('swimming route', (x, y), room(game, emulator), current_y, current_x))
        if active_direction:
            emulator.button_release(active_direction)
        emulator.tick(1, True)
        game.screenshot(emulator, 'ring-course-finish')
        assert frame > 1800, 'failure route unexpectedly finished within the time limit'
        continue_text(game, emulator, lambda: game.read(emulator, 'wTextIndexH_backup') == 0x50)
        options = game.address['w7TextboxOptionPositions']
        continue_text(game, emulator, lambda: emulator.memory[7, options + 1] != 0)
        emulator.tick(100, True)
        game.press(emulator, 'right', 10)
        assert emulator.memory[7, game.address['w7SelectedTextOption']] == 1
        game.press(emulator, 'a', 100)
        continue_text(game, emulator, lambda: room(game, emulator) == (3, 0xB6))
        assert game.read(emulator, 'wNumUnappraisedRingsBcd') == 0
        assert not flag(game, emulator, 0x5D)
        game.screenshot(emulator, 'ring-diving-course-failed')

if __name__=='__main__':
    from test_double_rewards import main
    main()

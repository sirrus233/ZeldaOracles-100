"""Targeted chest tests using synthetic late-game SRAM and normal input thereafter."""

from contextlib import contextmanager
from io import BytesIO
import os
import re
import sys

from emit_heart_patches import PROJECT, apply_patch
from smoke_baseline import ROOT, SCRATCH, SOURCE


SAVE_SLOT_COPIES = (0x0010, 0x1000)
SAVE_SLOT_LENGTH = 0x550
CHEST_POSITION = 0x55
CLOSED_CHEST = 0xF1
OPEN_CHEST = 0xF0
CHEST_FLAG = 0x7F
GAME_DATA = {
    'ages': (0x00, 0x38, 0x14),
    'seasons': (0x02, 0x5D, 0x28),
}
CHEST_ART_ADDRESSES = {'ages': 0x9600, 'seasons': 0x9000}


class Game:
    def __init__(self, name):
        self.name = name
        self.rom = (SOURCE / f'{name}.gbc').read_bytes()
        if '--patch' in sys.argv:
            retail, = (ROOT / 'roms').glob(f'*Oracle of {name.title()}*.gbc')
            patch = PROJECT / 'outputs' / f'Oracle of {name.title()} - 100 Percent.bps'
            self.rom = apply_patch(patch.read_bytes(), retail.read_bytes())
        self.group, self.room, self.finished_flag = GAME_DATA[name]
        self.address = {}
        for line in (SOURCE / f'{name}.sym').read_text().splitlines():
            if match := re.fullmatch(r'(?:[0-9a-f]{2}:|[0-9a-f]{4})([0-9a-f]{4}) (\S+)', line):
                self.address.setdefault(match[2], int(match[1], 16))

    @contextmanager
    def boot(self, sram=None):
        emulator = PyBoy(BytesIO(self.rom), ram_file=BytesIO(sram) if sram else None,
                         window='null', sound_volume=0)
        emulator.set_emulation_speed(0)
        try:
            emulator.tick(900, False)
            self.press(emulator, 'start', 120)
            self.press(emulator, 'start', 120)
            assert self.read(emulator, 'wFileSelect.mode') == 1, f'{self.name}: file menu'
            yield emulator
        finally:
            emulator.stop(save=False)

    def read(self, emulator, symbol):
        return emulator.memory[self.address[symbol]]

    @staticmethod
    def press(emulator, key, frames=40):
        emulator.button(key)
        emulator.tick(frames, True)

    def save_bytes(self, emulator):
        output = BytesIO()
        emulator.stop(save=True, ram_file=output)
        return output.getvalue()

    def new_file(self):
        with self.boot() as emulator:
            self.press(emulator, 'a')  # Select slot 1.
            self.press(emulator, 'a')  # New game.
            self.press(emulator, 'a')  # Enter the first name character.
            self.press(emulator, 'start')
            self.press(emulator, 'start')
            assert self.read(emulator, 'wFileSelect.mode') == 1, f'{self.name}: named save'
            sram = self.save_bytes(emulator)
            assert sram[SAVE_SLOT_COPIES[0]:SAVE_SLOT_COPIES[0] + SAVE_SLOT_LENGTH] != bytes(SAVE_SLOT_LENGTH)
            return sram

    def fixture(self, original, hearts, *, finished=True, linked=False, hero=False):
        """Seed a late-game starting state. The emulator runs every tested action."""
        sram = bytearray(original)
        primary = SAVE_SLOT_COPIES[0]
        saved = sram[primary:primary + SAVE_SLOT_LENGTH]
        start = self.address['wFileStart']

        def write(symbol, value):
            saved[self.address[symbol] - start] = value

        write('wFileIsLinkedGame', linked)
        write('wFileIsHeroGame', hero)
        write('wFileIsCompleted', finished)
        write('wLinkHealth', hearts * 4)
        write('wLinkMaxHealth', hearts * 4)
        write('wDeathRespawnBuffer.group', self.group)
        write('wDeathRespawnBuffer.room', self.room)
        write('wDeathRespawnBuffer.stateModifier', 0)
        write('wDeathRespawnBuffer.facingDir', 2)
        write('wDeathRespawnBuffer.y', 0x68)
        write('wDeathRespawnBuffer.x', 0x50)
        flags = self.address['wGlobalFlags'] - start
        saved[flags + (0x0A >> 3)] |= 1 << (0x0A & 7)  # Intro finished.
        saved[flags + (0x21 >> 3)] |= 1 << (0x21 & 7)  # Skip the pregame cutscene.
        if self.name == 'ages':
            saved[flags + (0x12 >> 3)] |= 1 << (0x12 & 7)  # Maku Tree saved.
            saved[self.address['wGroup1RoomFlags'] - start + 0x48] |= 1  # Present tree tileset.
            write('wMakuTreeState', 0x10)  # Postgame dialogue instead of the introduction.
        else:
            write('wc6e5', 8)  # Eight Essences. Growth 9 begins in the Room of Rites.
        write('wEssencesObtained', 0xFF)
        if finished:
            saved[flags + (self.finished_flag >> 3)] |= 1 << (self.finished_flag & 7)
        checksum = sum(int.from_bytes(saved[i:i + 2], 'little') for i in range(2, len(saved), 2))
        saved[:2] = (checksum & 0xFFFF).to_bytes(2, 'little')
        for offset in SAVE_SLOT_COPIES:
            sram[offset:offset + SAVE_SLOT_LENGTH] = saved
        return sram

    def load_slot(self, emulator):
        self.press(emulator, 'a')  # Select slot 1.
        self.press(emulator, 'a', 180)  # Confirm text speed, enter the game.
        room = self.read(emulator, 'wActiveGroup'), self.read(emulator, 'wActiveRoom')
        if room != (self.group, self.room):
            self.screenshot(emulator, 'load-failure')
        assert room == (self.group, self.room), (self.name, room, self.read(emulator, 'wFileSelect.mode'))

    def tile(self, emulator):
        return emulator.memory[self.address['wRoomLayout'] + CHEST_POSITION]

    def opened_flag(self, emulator):
        return bool(emulator.memory[self.address['wGlobalFlags'] + (CHEST_FLAG >> 3)] & 0x80)

    def chest_art(self, emulator):
        address = CHEST_ART_ADDRESSES[self.name]
        return bytes(emulator.memory[1, address:address + 48])

    def chest_pixels(self, emulator):
        # Screen position for tile $55, below the 16-pixel HUD. The bottom few
        # pixels are excluded because Link's idle sprite can overlap them.
        return emulator.screen.ndarray[96:108, 80:96].tobytes()

    def screenshot(self, emulator, label):
        emulator.screen.image.save(SCRATCH / f'{self.name}-{label}.png')

    def move_to(self, emulator, axis, destination, negative, positive):
        current = self.read(emulator, f'w1Link.{axis}h')
        if abs(current - destination) <= 1:
            return
        direction = negative if current > destination else positive
        emulator.button_press(direction)
        for _ in range(40):
            emulator.tick(1, False)
            if abs(self.read(emulator, f'w1Link.{axis}h') - destination) <= 1:
                break
        emulator.button_release(direction)
        emulator.tick(2, True)
        assert abs(self.read(emulator, f'w1Link.{axis}h') - destination) <= 3, (
            self.name, axis, self.read(emulator, f'w1Link.{axis}h'), destination,
        )

    def open_chest(self, emulator):
        self.move_to(emulator, 'y', 0x69, 'up', 'down')
        self.move_to(emulator, 'x', 0x58, 'left', 'right')
        emulator.button_press('up')
        emulator.tick(12, True)
        emulator.button_release('up')
        self.press(emulator, 'a', 180)

    def dismiss_pickup_text(self, emulator):
        for _ in range(4):
            if not self.read(emulator, 'wTextIsActive'):
                break
            self.press(emulator, 'a', 90)
        assert not self.read(emulator, 'wTextIsActive'), f'{self.name}: finish pickup text'

    def pause_and_resume(self, emulator, key):
        self.press(emulator, key, 120)
        assert self.read(emulator, 'wOpenedMenuType'), (self.name, key, 'menu did not open')
        self.press(emulator, key, 180)
        assert not self.read(emulator, 'wOpenedMenuType'), (self.name, key, 'menu did not close')

    def leave_and_return(self, emulator):
        for button, group in (('down', 0), ('up', self.group)):
            emulator.button_press(button)
            for _ in range(180):
                emulator.tick(1, False)
                if self.read(emulator, 'wActiveGroup') == group:
                    break
            emulator.button_release(button)
            emulator.tick(100, True)
            assert self.read(emulator, 'wActiveGroup') == group, (self.name, button)
        assert self.read(emulator, 'wActiveRoom') == self.room, f'{self.name}: return to the original Maku Tree room'
        # The linked-finale tree in Seasons uses a dedicated portal-spawner interaction.
        for interaction in range(0xD040, 0xE000, 0x100):
            assert not (emulator.memory[interaction] and emulator.memory[interaction + 1] == 0xE1), (
                self.name, 'Room of Rites portal appeared after the unlinked ending',
            )

    def save_from_menu(self, emulator):
        self.dismiss_pickup_text(emulator)
        # Use the game's actual menu eligibility conditions after cutscenes and
        # pickups. Text disappearance alone does not establish that menus work.
        emulator.button_release('start')
        emulator.button_release('select')
        emulator.tick(2, False)
        for _ in range(600):
            blocked = (emulator.memory[0xC2EE] != 2 or emulator.memory[0xC2EF] != 1
                       or self.read(emulator, 'wScrollMode') & 0x0E
                       or any(self.read(emulator, symbol) for symbol in (
                           'wTextIsActive', 'wLinkDeathTrigger', 'wLinkPlayingInstrument',
                           'wMenuDisabled', 'wDisableLinkCollisionsAndMenu')))
            if not blocked:
                break
            emulator.tick(1, False)
        else:
            raise AssertionError(f'{self.name}: game did not allow opening the save menu')
        emulator.button_press('start')
        emulator.button_press('select')
        emulator.tick(6, True)
        emulator.button_release('start')
        emulator.button_release('select')
        emulator.tick(84, True)
        if self.read(emulator, 'wSaveQuitMenu.state') != 1:
            self.screenshot(emulator, 'save-menu-failed')
            print('save menu state', {symbol: self.read(emulator, symbol) for symbol in (
                'wSaveQuitMenu.state', 'wOpenedMenuType', 'wMenuLoadState', 'wScrollMode',
                'wTextIsActive', 'wDisabledObjects', 'wMenuDisabled', 'wDisableLinkCollisionsAndMenu',
                'wKeysJustPressed', 'wLinkPlayingInstrument')}, flush=True)
            print('game state', list(emulator.memory[0xC2EE:0xC2F0]), flush=True)
        assert self.read(emulator, 'wSaveQuitMenu.state') == 1, f'{self.name}: save menu'
        for _ in range(180):
            if not self.read(emulator, 'wPaletteThread_mode'):
                break
            emulator.tick(1, False)
        else:
            raise AssertionError(f'{self.name}: save menu fade did not finish')
        emulator.button('down', 6)
        emulator.tick(40, True)
        assert self.read(emulator, 'wSaveQuitMenu.cursorIndex') == 1, f'{self.name}: Save and Continue'
        emulator.button('a', 6)
        emulator.tick(90, True)
        return self.save_bytes(emulator)


if __name__ == '__main__':
    for variable in ('TMP', 'TEMP', 'TMPDIR', 'APPDATA', 'LOCALAPPDATA', 'XDG_CACHE_HOME'):
        os.environ[variable] = str(SCRATCH)
    from pyboy import PyBoy

    for name in GAME_DATA:
        game = Game(name)
        base_save = game.new_file()
        for restrictions in ({'finished': False}, {'linked': True}, {'hero': True}):
            with game.boot(game.fixture(base_save, 14, **restrictions)) as emulator:
                game.load_slot(emulator)
                assert game.tile(emulator) not in (CLOSED_CHEST, OPEN_CHEST), (name, restrictions)
        with game.boot(game.fixture(base_save, 16)) as emulator:
            game.load_slot(emulator)
            assert game.tile(emulator) not in (CLOSED_CHEST, OPEN_CHEST), name
        for hearts in (14, 15):
            with game.boot(game.fixture(base_save, hearts)) as emulator:
                game.load_slot(emulator)
                game.screenshot(emulator, 'new-chest')
                assert game.tile(emulator) == CLOSED_CHEST, name
                assert not game.opened_flag(emulator), name
                chest_art = game.chest_art(emulator)
                assert chest_art[:16] != chest_art[16:32], name
                game.pause_and_resume(emulator, 'start')
                assert game.chest_art(emulator) == chest_art, (name, 'pause corrupted closed chest art')
                game.open_chest(emulator)
                assert game.chest_art(emulator) == chest_art, (name, 'pickup textbox corrupted chest art')
                assert game.tile(emulator) == OPEN_CHEST, name
                assert game.opened_flag(emulator), name
                assert game.read(emulator, 'wLinkMaxHealth') == (hearts + 1) * 4, name
                game.dismiss_pickup_text(emulator)
                assert game.chest_art(emulator) == chest_art, (name, 'closed textbox corrupted chest art')
                opened_pixels = game.chest_pixels(emulator)
                for menu_key in ('start', 'select'):
                    game.pause_and_resume(emulator, menu_key)
                    assert game.chest_art(emulator) == chest_art, (name, 'menu corrupted open chest art', menu_key)
                    assert game.tile(emulator) == OPEN_CHEST, (name, menu_key)
                    assert game.chest_pixels(emulator) == opened_pixels, (name, 'menu changed visible chest', menu_key)
                game.screenshot(emulator, 'opened-chest-after-menu')
                saved = game.save_from_menu(emulator)
            with game.boot(saved) as emulator:
                game.load_slot(emulator)
                assert game.tile(emulator) == OPEN_CHEST, name
                assert game.opened_flag(emulator), name
                assert game.chest_art(emulator) == chest_art, (name, 'reloaded chest art differs')
                game.open_chest(emulator)
                assert game.read(emulator, 'wLinkMaxHealth') == (hearts + 1) * 4, name
                if name == 'seasons':
                    game.leave_and_return(emulator)
                    assert game.tile(emulator) == OPEN_CHEST, (name, 'opened chest missing on return')
                    assert game.opened_flag(emulator), name
                    assert game.chest_art(emulator) == chest_art, (name, 'corrupt chest art on return')
                    assert game.read(emulator, 'wLinkMaxHealth') == (hearts + 1) * 4, name
                    game.screenshot(emulator, 'opened-chest-after-reentry')
        if name == 'seasons':
            with game.boot(game.fixture(base_save, 14)) as emulator:
                game.load_slot(emulator)
                game.leave_and_return(emulator)
                assert game.tile(emulator) == CLOSED_CHEST, (name, 'closed chest missing on return')
                game.open_chest(emulator)
                assert game.tile(emulator) == OPEN_CHEST, name
                assert game.opened_flag(emulator), name
                assert game.read(emulator, 'wLinkMaxHealth') == 15 * 4, name
        print(f'{name}: visibility, one heart at 14 and 15, pause/menu graphics, and save/reload passed', flush=True)

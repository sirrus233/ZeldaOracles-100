"""Exercise death/continue/save-quit from the saved linked postgame."""
import json
import sys
import test_postgame_chest as chest
from test_postgame_chest import Game,ROOT
from test_heros_cave import load,room
from test_ring_quests import quest_save,flag
from review4_sweep import FLAGS
from emit_heart_patches import PROJECT
OUT=PROJECT/'outputs/Postgame Code Review 4'

def main():
    rows=[]
    for name in ('ages','seasons'):
        game=Game(name); base=game.new_file()
        location=(0,0x38,0x68,0x50) if name=='ages' else (2,0x5e,0x68,0x50)
        saved=quest_save(game,base,location,linked=True,finished=True,flags=FLAGS[name],treasures=(0x36,))
        for option in (0,1,2):
            with game.boot(saved) as e:
                load(game,e,location)
                # Damage/death boundary; native animation, menu and continuation run.
                e.memory[game.address['wLinkHealth']]=0
                e.memory[game.address['wLinkDeathTrigger']]=0xff
                for _ in range(180):
                    e.tick(10,False)
                    if game.read(e,'wSaveQuitMenu.gameOver') and game.read(e,'wSaveQuitMenu.state')==1: break
                assert game.read(e,'wSaveQuitMenu.gameOver') and game.read(e,'wSaveQuitMenu.state')==1
                e.tick(90,False)
                for _ in range(option): game.press(e,'down',30)
                assert game.read(e,'wSaveQuitMenu.cursorIndex')==option
                game.press(e,'a',300)
                if option==2:
                    e.tick(900,False)
                    game.press(e,'start',120); game.press(e,'start',120)
                    assert game.read(e,'wFileSelect.mode')==1
                    game.press(e,'a'); game.press(e,'a',180)
                else: e.tick(180,False)
                assert room(game,e)==location[:2], (name,option,room(game,e))
                assert flag(game,e,2) and not flag(game,e,game.finished_flag)
                assert not game.read(e,'wFileIsCompleted')
                assert game.read(e,'wLinkHealth')>0
                assert not game.read(e,'wDisabledObjects') and not game.read(e,'wMenuDisabled')
                if name=='ages':
                    assert [game.read(e,s) for s in ('wMakuMapTextPresent','wMakuMapTextPast')]==[0x1c,0x8c]
                game.screenshot(e,f'review4-death-{option}')
                rows.append(dict(game=name,option=option,status='passed',clear_preserved=True,
                                 broad_completion_unset=True,correct_respawn=True,controls_restored=True))
                print(rows[-1],flush=True)
                (OUT/'death-results.json').write_text(json.dumps(rows,indent=2))

if __name__=='__main__':
    from pyboy import PyBoy
    chest.PyBoy=PyBoy
    main()

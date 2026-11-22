"""Finish the optional trades most exposed to postgame NPC role changes."""
import json
import sys
import test_postgame_chest as chest
from test_postgame_chest import Game,ROOT
from test_heros_cave import load,walk
from test_ring_quests import quest_save,choose,continue_text,finish_conversation
from test_victory_ring import update_save
from emit_heart_patches import PROJECT
OUT=PROJECT/'outputs/Postgame Code Review 4'

def main():
    rows=[]
    for name in ('ages','seasons'):
        game=Game(name); base=game.new_file()
        location=(2,0xe7,0x1a,0x38) if name=='ages' else (0,8,0x68,0x50)
        for linked in (False,True):
            saved=quest_save(game,base,location,linked=linked,finished=True,treasures=(0x41,))
            saved=update_save(game,saved,[('wTradeItem',4,0)])
            with game.boot(saved) as e:
                load(game,e,location)
                walk(game,e,'left' if name=='ages' else 'up',48 if name=='ages' else 5)
                game.press(e,'a',100); choose(game,e,0)
                continue_text(game,e,lambda:game.read(e,'wTradeItem')==5)
                finish_conversation(game,e)
                after=game.save_from_menu(e)
            with game.boot(after) as e:
                load(game,e,location)
                assert game.read(e,'wTradeItem')==5
                assert not game.read(e,'wDisabledObjects')
            rows.append(dict(game=name,linked=linked,status='passed',completed_adventure=True,
                             trade='Doggie Mask to Dumbbell' if name=='ages' else 'Lava Soup to Goron Vase',
                             controller_trade_and_save_reboot=True))
            print(rows[-1],flush=True)
            (OUT/'late-trades.json').write_text(json.dumps(rows,indent=2))

if __name__=='__main__':
    from pyboy import PyBoy
    chest.PyBoy=PyBoy
    main()

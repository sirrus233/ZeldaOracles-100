"""Appraise earned paired rings and transfer them before Game 2's final clear."""
import json,sys
import test_postgame_chest as chest
from test_postgame_chest import Game,ROOT,SCRATCH
from test_double_rewards import PAIRS,bag
from test_ring_quests import quest_save,choose,continue_text,finish_conversation
from test_heros_cave import load,walk
from test_victory_ring import update_save,SHOPS
from test_completion_transport import rings,ring_password,accept_rings
from emit_heart_patches import PROJECT

def relocate(g,saved,loc):
    return update_save(g,saved,[(f'wDeathRespawnBuffer.{key}',v,0) for key,v in zip(('group','room','y','x'),loc)])

def main():
    rows=[]
    for spec in PAIRS:
        g=Game(spec['game']);saved=(SCRATCH/f"{g.name}-paired-{spec['npc']}.sav").read_bytes()
        saved=relocate(g,saved,SHOPS[g.name])
        with g.boot(saved) as e:
            load(g,e,SHOPS[g.name]);walk(g,e,'up',48);g.press(e,'a',100);choose(g,e,0)
            continue_text(g,e,lambda:g.read(e,'wOpenedMenuType')==4)
            for _ in range(150):
                owned=rings(e,g)
                if all(owned[r//8]&(1<<(r%8)) for r in spec['pair']):break
                if g.read(e,'wSubmenuState')==0 and g.read(e,'wRingMenu.ringListCursorIndex')==0 and e.memory[g.address['wUnappraisedRings']]==0xff:
                    g.press(e,'right',40)
                g.press(e,'a',90)
            assert all(owned[r//8]&(1<<(r%8)) for r in spec['pair']),(spec,owned.hex(),bag(g,e))
            continue_text(g,e,lambda:not g.read(e,'wOpenedMenuType'));finish_conversation(g,e)
            assert not bag(g,e)
            earned=g.save_from_menu(e)
        # Red Snake stands to the right of Vasu.
        snake=(SHOPS[g.name][0],SHOPS[g.name][1],0x58,0x68)
        password=ring_password(g,relocate(g,earned,snake),snake)
        other=Game('seasons' if g.name=='ages' else 'ages')
        loc=(SHOPS[other.name][0],SHOPS[other.name][1],0x58,0x68)
        target=quest_save(other,other.new_file(),loc,linked=True,finished=False,flags=(8,),treasures=(0x2c,))
        target=update_save(other,target,[('wObtainedRingBox',1,0),('wRingBoxLevel',1,0)])
        with other.boot(target) as e:
            load(other,e,loc);initial=rings(e,other)
            assert not (e.memory[other.address['wGlobalFlags']]&4)
        expected=bytes(a|b for a,b in zip(initial,owned))
        result=accept_rings(other,target,loc,password,expected)
        with other.boot(result) as e:
            load(other,e,loc);assert not (e.memory[other.address['wGlobalFlags']]&4)
        rows.append(dict(game1=g.name,quest=spec['npc'],rings=list(spec['pair']),native_appraisal=True,ring_secret_transfer_before_game2_clear=True,save_reload=True))
        print(rows[-1],flush=True)
        (PROJECT/'outputs/Double Ring Rewards/appraisal-transfer.json').write_text(json.dumps(rows,indent=2))
if __name__=='__main__':
    from pyboy import PyBoy
    chest.PyBoy=PyBoy
    main()

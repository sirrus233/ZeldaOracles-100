"""Keep deferred Farore rewards claimable across the ending save."""
import json
import sys
import test_postgame_chest as chest
from test_postgame_chest import Game,ROOT
from test_ring_quests import flag,enter_password,continue_text,finish_conversation,choose
from test_heros_cave import load,walk
from test_completion_dependencies import farore_save,generate,talk_farore
from test_victory_ring import update_save,SHOPS,credits_fixture
from emit_heart_patches import PROJECT
OUT=PROJECT/'outputs/Postgame Code Review 4'

def relocate(game,saved,position):
    return update_save(game,saved,[(f'wDeathRespawnBuffer.{s}',v,0) for s,v in zip(('group','room','y','x'),position)])

def main():
    rows=[]
    for name in ('ages','seasons'):
        game=Game(name); base=game.new_file()
        for index in (1,3):
            initial,location=farore_save(game,base,finished=False,index=index)
            password=generate(game,initial,3,(0x30 if name=='ages' else 0x10)+index)
            done=(0x5a if name=='ages' else 0x6e)+index
            with game.boot(initial) as e:
                load(game,e,location); talk_farore(game,e); enter_password(game,e,password)
                continue_text(game,e,lambda:bool(flag(game,e,0x2c)))
                finish_conversation(game,e)
                assert not flag(game,e,done)
                pending=game.save_from_menu(e)
            with game.boot(relocate(game,pending,location)) as e:
                load(game,e,location)
                # Native Farore initialization removes unclaimed temporary chests.
                assert not flag(game,e,0x2c) and not flag(game,e,done)
                assert e.memory[game.address['wRoomLayout']+0x75]!=0xf1
            # Prepared boundary begins at the native post-credits prompt; no
            # completion flag or reward is injected during the tested actions.
            with game.boot(relocate(game,pending,SHOPS[name])) as e:
                load(game,e,SHOPS[name]); credits_fixture(game,e)
                for _ in range(130):
                    e.tick(10,False)
                    if game.read(e,'wTextIsActive'): break
                assert game.read(e,'wTextIsActive')
                choose(game,e,1); e.tick(130,True)
                completed=game.save_bytes(e)
            with game.boot(relocate(game,completed,location)) as e:
                load(game,e,location)
                assert flag(game,e,2) and not flag(game,e,game.finished_flag)
                assert not flag(game,e,0x2c) and not flag(game,e,done)
                talk_farore(game,e); enter_password(game,e,password)
                continue_text(game,e,lambda:bool(flag(game,e,0x2c)))
                finish_conversation(game,e)
                assert e.memory[game.address['wRoomLayout']+0x75]==0xf1
                game.move_to(e,'x',0x78,'left','right'); walk(game,e,'down',50)
                game.move_to(e,'y',0x89,'up','down'); game.move_to(e,'x',0x58,'left','right')
                walk(game,e,'up',10)
                continue_text(game,e,lambda:bool(flag(game,e,done)))
                finish_conversation(game,e)
                assert not flag(game,e,0x2c)
                if index==1: assert game.read(e,'wLinkMaxHealth')==64
                else:
                    assert game.read(e,'wNumUnappraisedRingsBcd')==1
                    assert game.read(e,'wUnappraisedRings')&63==(0x15 if name=='ages' else 0x2f)
                collected=game.save_from_menu(e)
            with game.boot(relocate(game,collected,location)) as e:
                load(game,e,location)
                assert flag(game,e,done) and not flag(game,e,0x2c)
                assert e.memory[game.address['wRoomLayout']+0x75]!=0xf1
                if index==1: assert game.read(e,'wLinkMaxHealth')==64
                else: assert game.read(e,'wNumUnappraisedRingsBcd')==1
            rows.append(dict(game=name,index=index,status='passed',deferred_reward_claimable_after_ending=True,
                             native_temporary_chest_reset_preserved=True,correct_reward=True,persisted_without_respawn=True))
            print(rows[-1],flush=True)
            (OUT/'pending-rewards.json').write_text(json.dumps(rows,indent=2))

if __name__=='__main__':
    from pyboy import PyBoy
    chest.PyBoy=PyBoy
    main()

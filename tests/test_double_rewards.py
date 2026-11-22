"""Real paired rewards, bounded storage, repeat/save behavior and native dog quest."""
from collections import Counter
from io import BytesIO
import json,os,sys
import test_postgame_chest as chest
from test_postgame_chest import Game,ROOT,SCRATCH
from test_ring_quests import quest_save,choose,continue_text,enter_password,flag,finish_conversation,talk
from test_heros_cave import load,walk,room
from test_victory_ring import update_save
from emit_heart_patches import PROJECT
OUT=PROJECT/'outputs/Double Ring Rewards';OUT.mkdir(parents=True,exist_ok=True)
PAIRS=[
 dict(game='ages',npc='Plen',location=(3,0xf8,0x60,0x70),index=3,pair=(0x2f,0x15),done=0x71),
 dict(game='ages',npc='Mamamu',location=(2,0xe7,0x1a,0x38),pair=(0x21,0x13)),
 dict(game='seasons',npc='Diver',location=(1,0xb6,0x60,0x50),pair=(0x15,0x2f),done=0x5d),
 dict(game='seasons',npc='Fairy',location=(1,0xad,0x40,0x50),index=0x26,pair=(0x13,0x21),done=0x60)]
ROWS=[]
def record(**row):
    ROWS.append(dict(status='passed',**row));print(ROWS[-1],flush=True)
    (OUT/('diverse-storage.json' if '--diverse-only' in sys.argv else 'pair-results.json')).write_text(json.dumps(ROWS,indent=2))
def bag(g,e):
    a=g.address['wUnappraisedRings']
    return [v&63 for v in e.memory[a:a+64] if v!=0xff and v&0x40]
def done(g,e,spec):
    return bool(e.memory[g.address['wGroup0RoomFlags']+0xe7]&0x40) if spec['npc']=='Mamamu' else bool(flag(g,e,spec['done']))
def ready_save(g,base,spec,count,diverse=False):
    flags={'Mamamu':(0x3b,), 'Diver':(0x53,0x2e)}.get(spec['npc'],())
    rooms={'Mamamu':((0,0xe7,0x20),),'Diver':((5,0xea,0x40),)}.get(spec['npc'],())
    saved=quest_save(g,base,spec['location'],linked=False,finished=True,flags=(8,*flags),room_flags=rooms,treasures=(0x2c,))
    changes=[('wObtainedRingBox',1,0),('wRingBoxLevel',1,0),('wNumRupees',0x99,0),('wNumRupees',9,1)]
    values=([r for r in range(64) if r not in spec['pair']]+list(spec['pair'])) if diverse else [0]*64
    changes += [('wUnappraisedRings',0x40|values[i],i) for i in range(count)]
    changes += [('wNumUnappraisedRingsBcd',int(str(count),16),0)]
    return update_save(g,saved,changes)
def watch(g,e,events):
    def granted(_):
        r=e.register_file
        if r.B==0x2d:events.append(dict(ring=r.C&63,menu_disabled=bool(g.read(e,'wMenuDisabled'))))
    e.hook_register(0,g.address['giveTreasure'],granted,None)
def claim(g,saved,spec,password,attempt_menu=False):
    events=[];seen=[]
    with g.boot(saved) as e:
        watch(g,e,events)
        e.hook_register(0,g.address['showText'],lambda _:seen.append(e.register_file.B<<8|e.register_file.C),None)
        load(g,e,spec['location'])
        if 'index' in spec:
            talk(g,e);continue_text(g,e,lambda:g.read(e,'wOpenedMenuType')==6)
            # Invalid passwords do not award either ring.
            enter_password(g,e,bytes([0x42]*5));assert not events and not done(g,e,spec)
            enter_password(g,e,password);assert g.read(e,'wTextInputResult')==0
        continue_text(g,e,lambda:len(events)>=1)
        assert not done(g,e,spec),'Quest marked complete after only the first award'
        if attempt_menu:
            e.button_press('start');e.button_press('select');e.tick(5,True)
            e.button_release('start');e.button_release('select')
            assert not g.read(e,'wOpenedMenuType'),'Save menu opened between rewards'
        continue_text(g,e,lambda:done(g,e,spec))
        finish_conversation(g,e)
        assert [x['ring'] for x in events]==list(spec['pair']),(spec,events)
        assert all(x['menu_disabled'] for x in events)
        assert all(r in bag(g,e) for r in spec['pair'])
        assert not any(t>>8 in (0x56,0x5a) for t in seen),'Retired follow-up dialogue still runs'
        current=bytes(e.memory[g.address['wUnappraisedRings']:g.address['wUnappraisedRings']+64])
        e.screen.image.save(OUT/f"{g.name}-{spec['npc']}-reward.png")
        saved=g.save_from_menu(e)
    with g.boot(saved) as e:
        events.clear();watch(g,e,events);load(g,e,spec['location'])
        assert done(g,e,spec)
        assert bytes(e.memory[g.address['wUnappraisedRings']:g.address['wUnappraisedRings']+64])==current
        talk(g,e,'left' if spec['npc']=='Mamamu' else 'up');finish_conversation(g,e)
        assert not events,'Repeated conversation duplicated reward'
        assert not g.read(e,'wOpenedMenuType') and not g.read(e,'wDisabledObjects')
    return saved

def native_dog(g,base):
    loc=(0,0x86,0x48,0x78)
    saved=quest_save(g,base,loc,linked=False,finished=True,flags=(0x6a,),room_flags=((0,0xe7,0xa0),))
    saved=update_save(g,saved,[('wInventoryA',0x16,0)])
    with g.boot(saved) as e:
        load(g,e,loc)
        for _ in range(600):
            if flag(g,e,0x3b):break
            dogs=[s for s in range(0xd040,0xe000,0x100) if e.memory[s] and e.memory[s+1:s+3]==[0x54,1]]
            assert dogs
            s=dogs[0];dy=e.memory[s+11]-g.read(e,'w1Link.yh');dx=e.memory[s+13]-g.read(e,'w1Link.xh')
            direction=('left' if dx<0 else 'right') if abs(dx)>=abs(dy) else ('up' if dy<0 else 'down')
            e.button(direction,2);e.tick(3,False)
            if abs(dx)+abs(dy)<24:e.button('a',8);e.tick(10,False)
        assert flag(g,e,0x3b)
        continue_text(g,e,lambda:room(g,e)==(2,0xe7))
        continue_text(g,e,lambda:bool(e.memory[g.address['wGroup0RoomFlags']+0xe7]&0x40))
        finish_conversation(g,e)
        assert Counter(bag(g,e))==Counter((0x21,0x13)),bag(g,e)
        saved=g.save_from_menu(e)
    record(game='ages',npc='Mamamu',native_dog_pursuit_pickup_return_and_both_rewards=True)

def main():
    from test_completion_dependencies import generate
    for key in ('TEMP','TMP','TMPDIR','APPDATA','LOCALAPPDATA','XDG_CACHE_HOME'):os.environ[key]=str(SCRATCH)
    from pyboy import PyBoy
    chest.PyBoy=PyBoy
    games={n:Game(n) for n in ('ages','seasons')};bases={n:g.new_file() for n,g in games.items()}
    passwords={}
    for spec in PAIRS:
        if 'index' not in spec:continue
        other='seasons' if spec['game']=='ages' else 'ages';source=games[other]
        saved=quest_save(source,bases[other],(source.group,source.room,0x68,0x50),linked=True,finished=False)
        passwords[spec['index']]=generate(source,saved,3,spec['index'])
    capacities=([(0,False),(62,False),(63,False),(64,False)] if '--diverse-only' not in sys.argv else [])
    capacities += [(62,True),(63,True),(64,True)]
    for spec in PAIRS:
        g=games[spec['game']]
        for count,diverse in capacities:
            saved=claim(g,ready_save(g,bases[g.name],spec,count,diverse),spec,passwords.get(spec.get('index')),attempt_menu=count==0)
            if count==0:(SCRATCH/f"{g.name}-paired-{spec['npc']}.sav").write_bytes(saved)
            record(game=g.name,npc=spec['npc'],initial_unappraised=count,diverse_storage=diverse,
                rings=list(spec['pair']),both_native_pickups=True,save_reload_repeat=True,completion_after_both=True)
    if '--diverse-only' in sys.argv:
        (OUT/'diverse-storage.json').write_text(json.dumps(ROWS,indent=2))
        return
    native_dog(games['ages'],bases['ages'])
    from test_ring_quests import test_diving_course_failure
    test_diving_course_failure(games['seasons'],bases['seasons'])
    record(game='seasons',npc='Diver',native_timed_failure_and_exit=True,no_rewards_on_failure=True)
if __name__=='__main__':main()

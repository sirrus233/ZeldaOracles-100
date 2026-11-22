"""Broad postgame NPC script/dialogue sweep; explicit input-dispatch boundary."""
from io import BytesIO
import json
import re
import sys
import test_postgame_chest as chest
from test_postgame_chest import Game, ROOT
from test_heros_cave import load
from test_ring_quests import quest_save, finish_conversation
from emit_heart_patches import PROJECT, SOURCE

OUT=PROJECT/'outputs/Postgame Code Review 4'
IDS={'ages':{0x29,0x38,0x39,0x3a,0x3b,0x3c,0x3d,0x3f,0x40,0x41,0x43,0x44,0x45,0x4e,0x4f},
     'seasons':{*range(0x24,0x40),0x8a,0x8b,0x8d,0xb8,0xbc,0xbd,0xbe}}
FLAGS={'ages':(0x0b,0x11,0x13,0x19,0x27,0x29,0x2b,0x2f,0x30,0x31,0x32,0x33,0x34,0x35,0x38,0x39,0x3a,0x3c,0x40,0x41,0x45),
       'seasons':(0x0d,0x0f,0x13,0x15,0x17,0x18,0x19,0x1e,0x1f,0x20,0x23,0x24,0x26)}

def locations(name):
    labels=[]
    started=False
    rooms=set()
    for line in (SOURCE/f'objects/{name}/mainData.s').read_text().splitlines():
        if m:=re.fullmatch(r'group([0-3])Map([0-9a-f]{2})ObjectData:',line):
            if started: labels=[]; started=False
            labels.append((int(m[1]),int(m[2],16)))
        elif re.fullmatch(r'\w+:',line):
            labels=[]; started=False
        if 'obj_' in line: started=True
        if m:=re.search(r'obj_Interaction \$([0-9a-f]{2}) \$([0-9a-f]{2})',line):
            if int(m[1],16) in IDS[name]: rooms.update(labels)
    return sorted(rooms)

def main(name):
    game=Game(name)
    base=game.new_file()
    texts=json.loads((OUT/f'{name}-all-text.json').read_text())
    rows=[]
    selected=locations(name)
    if '--gaps' in sys.argv:
        rows=json.loads((OUT/f'{name}-npc-sweep.json').read_text())
        selected=[tuple(r['room']) for r in rows if r['status']=='fixture-needs-route']
        rows=[r for r in rows if r['status']!='fixture-needs-route']
    for group,room in selected:
        location=(group,room,0x68,0x50)
        rooms=((0,0x3a,0x40),(1,0x48,1),(1,0x83,0x40),(4,0xfc,0x80)) if name=='ages' else ()
        saved=quest_save(game,base,location,linked=True,finished=True,flags=FLAGS[name],room_flags=rooms,treasures=(0x36,))
        with game.boot(saved) as e:
            try: load(game,e,location)
            except AssertionError:
                rows.append(dict(game=name,room=[group,room],status='fixture-needs-route',reason='Room changed during checkpoint startup'))
                continue
            slots=[s for s in range(0xd040,0xe000,0x100) if e.memory[s] and e.memory[s+1] in IDS[name]]
            if group==0 and room==0x7b and name=='ages':
                finish_conversation(game,e)
                slots=[s for s in range(0xd040,0xe000,0x100) if e.memory[s] and e.memory[s+1] in IDS[name]]
            if game.read(e,'wTextIsActive') or game.read(e,'wDisabledObjects'):
                rows.append(dict(game=name,room=[group,room],status='fixture-needs-route',reason='Automatic cutscene/text at checkpoint startup',actors=[[e.memory[s+1],e.memory[s+2]] for s in slots]))
                continue
            if not slots:
                rows.append(dict(game=name,room=[group,room],status='initialized-no-selected-actors'))
            state=BytesIO(); e.save_state(state); state=state.getvalue()
            target=[None]
            seen=[]
            def dispatch(_):
                s=(e.register_file.D<<8)|0x40
                if target[0]==s:
                    e.memory[s+0x31]=1
                    target[0]=None
            e.hook_register(0,game.address['interactionRunScript'],dispatch,None)
            e.hook_register(0,game.address['showText'],lambda _:seen.append(e.register_file.B<<8|e.register_file.C),None)
            for slot in slots:
                e.load_state(BytesIO(state))
                actor,subid=e.memory[slot+1],e.memory[slot+2]
                seen.clear(); target[0]=slot
                # Simulate only native engine delivery of an A press to this NPC.
                # The native initialized role, script branches and text selection run.
                for _ in range(90):
                    e.tick(1,False)
                    if seen: break
                target[0]=None
                row=dict(game=name,room=[group,room],actor=actor,subid=subid,
                         script_pointer=e.memory[slot+0x18]|e.memory[slot+0x19]<<8,
                         text_ids=seen.copy(),texts=[texts.get(f'TX_{t:04x}','') for t in seen],
                         boundary='Native initialized NPC; A-button recipient dispatch simulated, not a navigation replay')
                if not seen: row['status']='no-dialogue-at-boundary'
                else:
                    try:
                        finish_conversation(game,e)
                        row['status']='dialogue-returned-control'
                    except AssertionError:
                        row['status']='needs-interactive-route'
                row['text_ids']=seen.copy()
                row['texts']=[texts.get(f'TX_{t:04x}','') for t in seen]
                rows.append(row)
                print(name,hex(group),hex(room),hex(actor),hex(subid),row['status'],seen,flush=True)
        (OUT/f'{name}-npc-sweep.json').write_text(json.dumps(rows,indent=2))
    (OUT/f'{name}-npc-sweep.json').write_text(json.dumps(rows,indent=2))

if __name__=='__main__':
    from pyboy import PyBoy
    chest.PyBoy=PyBoy
    main(sys.argv[1])

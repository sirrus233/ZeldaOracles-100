"""Non-mutating cumulative ROM layout and graphics-isolation review."""
from hashlib import sha1
import json
import re
import sys
import test_postgame_chest as chest
from test_postgame_chest import Game, ROOT, SCRATCH
from test_heros_cave import retail_rom
from test_heros_cave import load, walk
from test_ring_quests import quest_save, finish_conversation
from emit_heart_patches import PROJECT, SOURCE

OUT = PROJECT / 'outputs/Postgame Code Review 3'

def layout():
    results = {}
    for name in ('ages', 'seasons'):
        rom = (SOURCE / f'{name}.gbc').read_bytes()
        text = (SOURCE / f'{name}.sym').read_text()
        rows = []
        for line in text.split('[sections]\n')[1].split('[ramsections]')[0].splitlines():
            if not line.strip():
                continue
            physical, bank_offset, cpu, size, label = line.split(maxsplit=4)
            bank, offset = (int(x,16) for x in bank_offset.split(':'))
            physical, cpu, size = (int(x,16) for x in (physical,cpu,size))
            assert physical == bank*0x4000+offset
            assert 0 <= offset < 0x4000 and offset+size <= 0x4000, (name,label)
            rows.append(dict(bank=bank, offset=offset, cpu=cpu, size=size, name=label))
        for bank in range(64):
            ranges = sorted((r['offset'],r['offset']+r['size'],r['name']) for r in rows if r['bank']==bank)
            for a,b in zip(ranges,ranges[1:]):
                assert a[1] <= b[0], (name,a,b)
        assert len(rom)==0x100000 and rom[0x147]==0x1b
        assert rom[0x14d] == (-sum(rom[0x134:0x14d])-0x19)&255
        assert int.from_bytes(rom[0x14e:0x150],'big') == (sum(rom)-rom[0x14e]-rom[0x14f])&65535
        labels={m[3]:(int(m[1],16),int(m[2],16)) for m in re.finditer(r'^([0-9a-f]{2}):([0-9a-f]{4}) (\S+)$',text,re.M)}
        for symbol in ('checkFirstAdventureFinished','checkAdventureComplete','normalizeLinkedClearState'):
            assert labels[symbol][0]==0 and labels[symbol][1]<0x4000
        assert labels['restorePostgameHeartChestGfx'][0]==4
        assert labels['recordOpenedChest'][0]==4
        bank,address=labels['postgameHeartChestGfx']
        assert address%16==0 and (address&0x3fff)+48<=0x4000
        results[name]=dict(sha1=sha1(rom).hexdigest(), section_count=len(rows), sections=rows,
            allocated_by_bank={str(b):sum(r['size'] for r in rows if r['bank']==b) for b in range(64)},
            graphics_source=dict(bank=bank,cpu=address,physical=bank*0x4000+(address&0x3fff)),
            checks='No section overlaps or bank crossing; header/global checksum; MBC5 header; helper banks; DMA alignment')
    (OUT/'layout-results.json').write_text(json.dumps(results,indent=2))

def graphics():
    import numpy as np
    rows=[]
    for name in ('ages','seasons'):
        game=Game(name)
        base=game.new_file()
        saved=game.fixture(base,14)
        patched=game.rom
        snapshots={}
        for variant,rom in [('retail',retail_rom(name)),('patched',patched)]:
            game.rom=rom
            with game.boot(saved) as e:
                game.load_slot(e)
                scenes=[]
                original_room=(game.read(e,'wActiveGroup'),game.read(e,'wActiveRoom'))
                for stage in ('initial','idle','pause','neighbor','return'):
                    if stage=='idle': e.tick(600,True)
                    if stage=='pause': game.pause_and_resume(e,'start')
                    if stage in ('neighbor','return'):
                        e.button_press('down' if stage=='neighbor' else 'up')
                        for _ in range(240):
                            e.tick(1,False)
                            current=(game.read(e,'wActiveGroup'),game.read(e,'wActiveRoom'))
                            if (current!=original_room if stage=='neighbor' else current==original_room): break
                        e.button_release('down' if stage=='neighbor' else 'up')
                        e.tick(120,True)
                        assert (current!=original_room if stage=='neighbor' else current==original_room)
                    scenes.append(e.screen.ndarray.copy())
                    game.screenshot(e,f'review3-{variant}-{stage}')
                    (OUT/f'{name}-{variant}-{stage}.png').write_bytes((SCRATCH/f'{name}-review3-{variant}-{stage}.png').read_bytes())
                snapshots[variant]=scenes
                if variant=='patched':
                    start=chest.CHEST_ART_ADDRESSES[name]
                    # The linker may put graphics in switchable slot 1 of ROM bank zero.
                    sym=(SOURCE/f'{name}.sym').read_text()
                    m=re.search(r'^([0-9a-f]{2}):([0-9a-f]{4}) postgameHeartChestGfx$',sym,re.M)
                    physical=int(m[1],16)*0x4000+(int(m[2],16)&0x3fff)
                    assert bytes(e.memory[1,start:start+48])==patched[physical:physical+48]
                    assert game.tile(e)==chest.CLOSED_CHEST
        for i,stage in enumerate(('initial','idle','pause','neighbor','return')):
            different=np.any(snapshots['retail'][i]!=snapshots['patched'][i],axis=2)
            all_pixels=int(different.sum())
            if stage!='neighbor': different[96:112,80:96]=False
            # Ages' southern neighbor is also the intentionally opened Hero's Cave.
            if name=='ages' and stage=='neighbor': different[48:64,128:144]=False
            outside=int(different.sum())
            assert outside==0, (name,stage,'Chest graphics changed other screen pixels',outside)
            rows.append(dict(game=name,stage=stage,changed_pixels=all_pixels,
                             changed_pixels_outside_expected_edits=outside))
        print(rows[-5:],flush=True)
    (OUT/'graphics-results.json').write_text(json.dumps(rows,indent=2))

def ordinary_chests():
    rows=[]
    for name,group,room,pos in [('ages',2,0xec,0x34),('seasons',2,0x9b,0x34),('seasons',3,0x9b,0x34)]:
        game=Game(name)
        base=game.new_file()
        location=(group,room,(pos&0xf0)+0x28,((pos&15)<<4)+8)
        saved=quest_save(game,base,location,finished=False)
        with game.boot(saved) as e:
            load(game,e,location)
            reward_symbol='wNumUnappraisedRingsBcd' if name=='ages' else 'wNumGashaSeeds'
            reward_before=game.read(e,reward_symbol)
            assert e.memory[game.address['wRoomLayout']+pos]==chest.CLOSED_CHEST, (name,group,'closed chest absent',
                e.memory[game.address['wRoomLayout']+pos],
                [p for p in range(256) if e.memory[game.address['wRoomLayout']+p]==chest.CLOSED_CHEST])
            walk(game,e,'up',32)
            game.press(e,'a',180)
            finish_conversation(game,e)
            assert game.read(e,reward_symbol)==reward_before+1
            assert e.memory[game.address['wRoomLayout']+pos]==chest.OPEN_CHEST, (name,group,'did not open')
            assert not game.opened_flag(e), 'Ordinary chest incorrectly sets custom heart flag'
            assert not game.read(e,'wDisabledObjects')
            game.pause_and_resume(e,'start')
            resaved=game.save_from_menu(e)
        with game.boot(resaved) as e:
            load(game,e,location)
            assert e.memory[game.address['wRoomLayout']+pos]==chest.OPEN_CHEST
            assert not game.opened_flag(e)
            assert game.read(e,reward_symbol)==reward_before+1
        rows.append(dict(game=name,group=group,room=room,position=pos,passed=True,
                         controller_open=True,reward_increment=1,pause_save_reboot=True,custom_flag_untouched=True))
        print(rows[-1],flush=True)
        (OUT/'ordinary-chests.json').write_text(json.dumps(rows,indent=2))

def predicate_contracts():
    rows=[]
    for name in ('ages','seasons'):
        game=Game(name)
        base=game.new_file()
        for linked in (False,True):
            location=(0,0x3a,0x68,0x40) if name=='ages' else (0,0xd6,0x28,0x58)
            saved=quest_save(game,base,location,linked=linked,finished=True,
                             room_flags=((0,0x3a,0x40),) if name=='ages' else ())
            with game.boot(saved) as e:
                pending=[]
                hooks=set()
                observed=[]
                errors=[]
                def guarded(callback):
                    def checked(context):
                        try: callback(context)
                        except Exception as error: errors.append(repr(error))
                    return checked
                def returned(_):
                    if not pending: return
                    entry=pending[-1]
                    r=e.register_file
                    if r.SP!=entry['sp']+2 or r.PC!=entry['return']: return
                    pending.pop()
                    assert (r.B<<8|r.C)==entry['bc']
                    assert (r.D<<8|r.E)==entry['de']
                    assert e.memory[0xff97]==entry['bank']
                    assert not (r.F & 0x80), 'Completed-adventure predicate returned Z'
                    observed.append(entry)
                def entered(_):
                    r=e.register_file
                    ret=e.memory[r.SP]|e.memory[r.SP+1]<<8
                    bank=0 if ret<0x4000 else e.memory[0xff97]
                    key=(bank,ret)
                    pending.append(dict(sp=r.SP,bc=r.B<<8|r.C,de=r.D<<8|r.E,
                                        bank=e.memory[0xff97],return_address=ret,**{'return':ret}))
                    if key not in hooks:
                        e.hook_register(bank,ret,guarded(returned),None)
                        hooks.add(key)
                e.hook_register(0,game.address['checkAdventureComplete'],guarded(entered),None)
                load(game,e,location)
                game.pause_and_resume(e,'start')
                assert observed and not pending, (name,linked,len(observed),pending)
                assert not errors, errors
                rows.append(dict(game=name,linked=linked,passed=True,calls=len(observed),
                                 preserved='BC, DE, ROM bank and stack; NZ on completed adventure',samples=observed))
                print(rows[-1],flush=True)
                (OUT/'predicate-contracts.json').write_text(json.dumps(rows,indent=2))

def ages_chest_room_return():
    game=Game('ages')
    base=game.new_file()
    rows=[]
    for opened in (False,True):
        with game.boot(game.fixture(base,14)) as e:
            game.load_slot(e)
            if opened:
                game.open_chest(e)
                game.dismiss_pickup_text(e)
            art=game.chest_art(e)
            for direction,destination in [('down',0x48),('up',0x38)]:
                e.button_press(direction)
                for _ in range(240):
                    e.tick(1,False)
                    if game.read(e,'wActiveRoom')==destination: break
                e.button_release(direction)
                e.tick(120,True)
                assert game.read(e,'wActiveRoom')==destination, (opened,direction,game.read(e,'wActiveRoom'))
            assert game.tile(e)==(chest.OPEN_CHEST if opened else chest.CLOSED_CHEST)
            assert game.chest_art(e)==art
            rows.append(dict(game='ages',opened=opened,passed=True,controller_room_return=True,art_preserved=True))
            print(rows[-1],flush=True)
            (OUT/'ages-room-return.json').write_text(json.dumps(rows,indent=2))

if __name__=='__main__':
    layout()
    from pyboy import PyBoy
    chest.PyBoy=PyBoy
    graphics()
    ordinary_chests()
    predicate_contracts()
    ages_chest_room_return()

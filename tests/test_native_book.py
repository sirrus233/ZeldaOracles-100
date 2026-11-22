"""Native Farore book: retail-equivalent passwords, pixels, navigation, exit/save."""
import json,sys
import test_postgame_chest as chest
from test_postgame_chest import Game,ROOT
from test_heros_cave import load,walk,retail_rom
from test_ring_quests import quest_save,choose,continue_text
from emit_heart_patches import PROJECT
OUT=PROJECT/'outputs/Double Ring Rewards';OUT.mkdir(parents=True,exist_ok=True)
def entries(g,linked):
    a=g.address['secretListMenu_getSecretData@'+('linked' if linked else 'unlinked')]
    p=2*0x4000+(a&0x3fff); result=[]
    while g.rom[p]: result.append(list(g.rom[p:p+3]));p+=3
    return result
def open_book(g,e,location):
    load(g,e,location);walk(g,e,'up',32);g.press(e,'a',100);choose(g,e,0)
    continue_text(g,e,lambda:g.read(e,'wOpenedMenuType')==0xa);e.tick(120,True)
def capture(g,saved,location):
    photos=[];codes=[]
    with g.boot(saved) as e:
        open_book(g,e,location)
        n=g.read(e,'wSecretListMenu.numEntries')
        flags=bytes(e.memory[g.address['wGlobalFlags']:g.address['wGlobalFlags']+16])
        for i in range(n):
            if i: g.press(e,'down',40);e.tick(90,True)
            assert g.read(e,'wSecretListMenu.cursorIndex')==i
            codes.append(bytes(e.memory[7,g.address['w7SecretText1']:g.address['w7SecretText1']+24]))
            photos.append(e.screen.ndarray.copy())
            if i>=n-2:
                e.screen.image.save(OUT/f'{g.name}-{g.variant}-{n}-{i}.png')
        g.press(e,'down',40); assert g.read(e,'wSecretListMenu.cursorIndex')==n-1
        for i in reversed(range(n-1)):
            g.press(e,'up',40);e.tick(90,True)
            assert g.read(e,'wSecretListMenu.cursorIndex')==i
            assert bytes(e.memory[7,g.address['w7SecretText1']:g.address['w7SecretText1']+24])==codes[i]
        g.press(e,'up',40);assert g.read(e,'wSecretListMenu.cursorIndex')==0
        assert bytes(e.memory[g.address['wGlobalFlags']:g.address['wGlobalFlags']+16])==flags
        g.press(e,'b',180);e.tick(120,True)
        assert not g.read(e,'wOpenedMenuType') and not g.read(e,'wDisabledObjects')
        saved=g.save_from_menu(e)
    with g.boot(saved) as e:
        load(g,e,location)
        assert bytes(e.memory[g.address['wGlobalFlags']:g.address['wGlobalFlags']+16])==flags
    return photos,codes
def main():
    import numpy as np
    rows=[]
    for name in ('ages','seasons'):
        current=Game(name);retail=Game(name);retail.rom=retail_rom(name)
        current.variant='patched';retail.variant='retail';base=current.new_file()
        location=(5,0xcf,0x58,0x38) if name=='ages' else (4,0xe8,0x58,0x38)
        for linked in (False,True):
            table=entries(current,linked)
            assert len(table)==(11 if linked else 10)
            saved=quest_save(current,base,location,linked=linked,finished=True,flags=tuple(x[1] for x in table))
            pp,pc=capture(current,saved,location);rp,rc=capture(retail,saved,location)
            assert pc==rc
            assert all(np.array_equal(a,b) for a,b in zip(pp,rp))
            rows.append(dict(game=name,linked=linked,entries=len(table),retail_pixels_and_passwords=True,scroll_exit_save_reload=True))
            print(rows[-1],flush=True)
    (OUT/'native-book.json').write_text(json.dumps(rows,indent=2))
if __name__=='__main__':
    from pyboy import PyBoy
    chest.PyBoy=PyBoy
    main()

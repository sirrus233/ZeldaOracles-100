"""Actual early entrances/exits, graphics restoration, saves and native death menus."""
from io import BytesIO
import json,os,sys
import test_postgame_chest as chest
from test_postgame_chest import Game,ROOT,SCRATCH
from test_heros_cave import ENTRANCES,SEASONS_LOWER_DOOR,CHALLENGE,fixture,load,walk,room,position,enter_seasons_door,settle_entrance
from test_victory_ring import update_save
from test_ring_quests import flag
from emit_heart_patches import PROJECT
OUT=PROJECT/'outputs/Early Hero Cave';OUT.mkdir(parents=True,exist_ok=True)
ROWS=[]

def record(**row):
 ROWS.append(dict(status='passed',**row));print(ROWS[-1],flush=True);(OUT/'early-results.json').write_text(json.dumps(ROWS,indent=2))

def starter(g,base,*,linked=False,hero=False,sword=False,season=0):
 loc=SEASONS_LOWER_DOOR if g.name=='seasons' and linked else ENTRANCES[g.name]
 saved=fixture(g,base,loc,early=True,finished=False,linked=linked,hero=hero)
 edits=[('wDeathRespawnBuffer.stateModifier',season,0)]
 if sword:edits += [('wSwordLevel',1,0),('wInventoryA',5,0),('wObtainedTreasureFlags',0x20,0)]
 return update_save(g,saved,edits),loc

def unchanged_completion(g,e):
 assert not flag(g,e,g.finished_flag) and not flag(g,e,2)
 assert not g.read(e,'wFileIsCompleted') and g.read(e,'wEssencesObtained')==0

def art(g,e,position):
 tile=e.memory[g.address['wRoomLayout']+position]
 a=g.address['w3TileMappingData']+tile*8;m=bytes(e.memory[3,a:a+8])
 pixels=[]
 for t,attr in zip(m[:4],m[4:]):
  address=0x9000+((t+128)%256-128)*16
  pixels.append(bytes(e.memory[(attr>>3)&1,address:address+16]))
 return tile,m,b''.join(pixels)

def enter(g,e):
 if g.name=='seasons':enter_seasons_door(g,e,shows_title=True)
 else:walk(g,e,'up',35);settle_entrance(g,e)
 assert room(g,e)==CHALLENGE[g.name],(g.name,room(g,e))
 assert g.read(e,'wDungeonIndex')==11

def exit_cave(g,e,loc):
 e.button_press('down')
 for _ in range(240):
  e.tick(1,False)
  if room(g,e)==loc[:2]:break
 e.button_release('down')
 for _ in range(300):
  e.tick(1,False)
  if e.memory[0xc2ee]==2 and e.memory[0xc2ef]==1 and not any(g.read(e,n) for n in ('wPaletteThread_mode','wDisabledObjects','wMenuDisabled','wDisableLinkCollisionsAndMenu')):break
 e.tick(2,True)
 assert room(g,e)==loc[:2],(g.name,'exit',room(g,e))
 # The return must use the same doorway: upper in Game 1 Seasons, lower in Game 2.
 assert abs(position(g,e)[1]-loc[3])<=4,(g.name,position(g,e),loc)
 if g.name=='seasons':assert (position(g,e)[0]<0x30)==(loc==ENTRANCES['seasons']),position(g,e)

def visit(g,base,linked,hero,sword,season):
 saved,loc=starter(g,base,linked=linked,hero=hero,sword=sword,season=season)
 door=0x28 if g.name=='ages' else 0x54 if linked else 4
 with g.boot(saved) as e:
  load(g,e,loc);unchanged_completion(g,e)
  original=art(g,e,door);assert original[0]==(0xdd if g.name=='ages' else 0xe8)
  actual_season=g.read(e,'wRoomStateModifier') if g.name=='seasons' else None
  e.screen.image.save(OUT/f'{g.name}-early-{linked}-{hero}-{sword}-{season}.png')
  enter(g,e);unchanged_completion(g,e)
  for key in ('start','select'):g.pause_and_resume(e,key)
  exit_cave(g,e,loc)
  unchanged_completion(g,e)
  if g.name=='seasons':
   # Native cave exits restore this area's default season, even after a rod change.
   pack=g.read(e,'wRoomPack');assert pack<30
   assert g.read(e,'wRoomStateModifier')==g.rom[g.address['roomPackSeasonTable']+pack]
   original=art(g,e,door)
  else:assert art(g,e,door)==original
  # Branch from the same exit checkpoint: pausing adds overworld enemy time.
  # Restoring the checkpoint isolates re-entry from those unrelated enemy movements.
  state=BytesIO();e.save_state(state)
  g.pause_and_resume(e,'start');assert art(g,e,door)==original
  walk(g,e,'down',20)
  assert room(g,e)==loc[:2],(g.name,'unexpected re-entry after pause',room(g,e))
  e.load_state(BytesIO(state.getvalue()))
  g.move_to(e,'y',loc[2],'up','down');g.move_to(e,'x',loc[3],'left','right')
  enter(g,e);unchanged_completion(g,e)
  saved_inside=g.save_from_menu(e)
 with g.boot(saved_inside) as e:
  g.press(e,'a');g.press(e,'a',180);settle_entrance(g,e)
  assert room(g,e)==CHALLENGE[g.name]
  unchanged_completion(g,e);exit_cave(g,e,loc);assert art(g,e,door)==original
 record(game=g.name,linked=linked,hero=hero,sword=sword,season=actual_season,native_season_reset=True if g.name=='seasons' else None,actual_door_entry_exit_reentry=True,pause_map_graphics=True,save_reload=True,no_completion_flags=True)

def death(g,base,linked,option):
 saved,loc=starter(g,base,linked=linked,sword=False)
 with g.boot(saved) as e:
  load(g,e,loc);enter(g,e)
  # Explicit damage boundary: all death animation, menu, respawn and control run natively.
  e.memory[g.address['wLinkHealth']]=0;e.memory[g.address['wLinkDeathTrigger']]=0xff
  for _ in range(180):
   e.tick(10,False)
   if g.read(e,'wSaveQuitMenu.gameOver') and g.read(e,'wSaveQuitMenu.state')==1:break
  assert g.read(e,'wSaveQuitMenu.gameOver') and g.read(e,'wSaveQuitMenu.state')==1
  e.tick(90,False)
  for _ in range(option):g.press(e,'down',30)
  assert g.read(e,'wSaveQuitMenu.cursorIndex')==option
  g.press(e,'a',300)
  if option==2:
   e.tick(900,False);g.press(e,'start',120);g.press(e,'start',120);g.press(e,'a');g.press(e,'a',180)
  else:e.tick(180,False)
  assert room(g,e)==CHALLENGE[g.name] and g.read(e,'wLinkHealth')>0
  unchanged_completion(g,e);assert not g.read(e,'wDisabledObjects') and not g.read(e,'wMenuDisabled')
  exit_cave(g,e,loc)
 record(game=g.name,linked=linked,native_death_menu_option=option,correct_respawn_and_exit=True,no_completion_flags=True)

def sword_after_visit():
 g=Game('seasons');base=g.new_file();saved,loc=starter(g,base)
 with g.boot(saved) as e:
  load(g,e,loc);enter(g,e);unchanged_completion(g,e)
  saved=g.save_from_menu(e)
 from test_heros_cave import test_wooden_sword
 test_wooden_sword(g,saved)
 record(game='seasons',original_sword_pickup_after_actual_early_cave_visit=True)

def main():
 for key in ('TEMP','TMP','TMPDIR','APPDATA','LOCALAPPDATA','XDG_CACHE_HOME','XDG_CONFIG_HOME','XDG_DATA_HOME'):os.environ[key]=str(SCRATCH)
 from pyboy import PyBoy
 chest.PyBoy=PyBoy
 for name in ('ages','seasons'):
  g=Game(name);base=g.new_file()
  for linked,hero,sword,season in [(False,False,False,0),(False,False,True,0),(False,True,False,0),(True,False,True,0)]+([(False,False,False,s) for s in (1,2,3)] if name=='seasons' else []):visit(g,base,linked,hero,sword,season)
  for linked in (False,True):
   for option in (0,1,2):death(g,base,linked,option)
 sword_after_visit()
if __name__=='__main__':main()

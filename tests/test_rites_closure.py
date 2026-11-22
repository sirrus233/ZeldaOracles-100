"""Portal closure after a saved linked clear; native movement, endings and saves."""
from io import BytesIO
import json,os,sys
import test_postgame_chest as chest
from test_postgame_chest import Game,ROOT,SCRATCH
from test_ring_quests import quest_save,flag
from test_heros_cave import load,room
from test_victory_ring import shop_save,ending_save,update_save
from test_postgame_world import actors
from emit_heart_patches import PROJECT

OUT=PROJECT/'outputs/Postgame Verification/audit'
ROWS=[]
LOCATIONS={'ages':(0,0x38,0x68,0x48),'seasons':(2,0x5e,0x78,0x78)}
TILES={'ages':0x57,'seasons':0x67}

def record(game,test,**details):
 row=dict(game=game.name,test=test,status='passed',**details)
 ROWS.append(row);print(row,flush=True)
 (OUT/'rites-results.json').write_text(json.dumps(ROWS,indent=2))

def relocate(game,data):
 return update_save(game,data,[(f'wDeathRespawnBuffer.{k}',v,0)
     for k,v in zip(('group','room','y','x'),LOCATIONS[game.name])])

def ready(game,base,complete):
 data=quest_save(game,base,LOCATIONS[game.name],linked=True,finished=complete,
                flags=(0x11,0x13,0x33,0x35,0x39,0x3a,0x3d,0x40) if game.name=='ages' else (),
                room_flags=((4,0xfc,0x80),) if game.name=='ages' else ())
 return update_save(game,data,[('wc6e5',9,0)]) if game.name=='seasons' else data

def assert_entrance(game,e,closed):
 tile=e.memory[game.address['wRoomLayout']+TILES[game.name]]
 portal=[a for a in actors(e,(0x80 if game.name=='ages' else 0xe1,))
         if (a[3],a[4])==((0x58,0x78) if game.name=='ages' else (0x68,0x78))]
 assert bool(portal)==(not closed),(game.name,closed,'portal object',portal,tile)
 if game.name=='seasons':
  assert (tile==0x01) if closed else (tile!=0x01),(game.name,closed,hex(tile))
 else:
  assert (tile!=0xdc) if closed else (tile==0xdc),(game.name,closed,hex(tile))
 assert flag(game,e,2)==closed
 assert not flag(game,e,game.finished_flag)
 assert not game.read(e,'wFileIsCompleted')
 return tile

def approach(game,e,closed):
 original=LOCATIONS[game.name][:2];crossed=False;trace=[]
 direction='up'
 if game.name=='ages':
  game.move_to(e,'y',0x58,'up','down');direction='right'
 e.button_press(direction)
 for _ in range(100):
  e.tick(1,False)
  pos=((game.read(e,'w1Link.yh')+4)&0xf0)|(game.read(e,'w1Link.xh')>>4)
  crossed |= pos==TILES[game.name]
  if len(trace)<12 and _%10==0:trace.append((game.read(e,'w1Link.yh'),game.read(e,'w1Link.xh'),pos,game.read(e,'w1Link.state')))
  if room(game,e)!=original:break
 e.button_release(direction);e.tick(180,True)
 if closed:
  assert crossed,(game.name,'Did not actually cross former portal tile')
  assert room(game,e)==original,(game.name,'Invisible warp remains',room(game,e))
 else:
  assert room(game,e)!=original,(game.name,'Pre-clear portal no longer works',trace,{k:game.read(e,k) for k in ('wEnteredWarpPosition','wDisableWarpTiles','wMenuDisabled','wTextIsActive','wDisabledObjects')})
 return room(game,e)

def return_to_tree(game,e):
 original=LOCATIONS[game.name][:2]
 for direction,returning in (('down',False),('up',True)):
  e.button_press(direction)
  for _ in range(360):
   e.tick(1,False)
   if (room(game,e)==original)==returning:break
  else:raise AssertionError((game.name,'Failed native tree exit/return',direction,room(game,e)))
  e.button_release(direction);e.tick(160,True)
 assert room(game,e)==original

def lifecycle(game,data,closed):
 with game.boot(data) as e:
  load(game,e,LOCATIONS[game.name]);assert_entrance(game,e,closed)
  checkpoint=BytesIO();e.save_state(checkpoint);state=checkpoint.getvalue()
  for menu in (None,'start','select'):
   e.load_state(BytesIO(state))
   if menu:game.pause_and_resume(e,menu)
   tile=assert_entrance(game,e,closed)
   e.screen.image.save(OUT/f'{game.name}-rites-{closed}-{menu}.png')
   dest=approach(game,e,closed)
   record(game,'Portal visual and actual warp boundary',closed=closed,menu=menu,tile=tile,destination=dest)
  e.load_state(BytesIO(state));return_to_tree(game,e);assert_entrance(game,e,closed)
  record(game,'Portal state persists after native room exit/return',closed=closed)
  e.load_state(BytesIO(state));saved=game.save_from_menu(e)
 with game.boot(saved) as e:
  load(game,e,LOCATIONS[game.name]);assert_entrance(game,e,closed);approach(game,e,closed)
  record(game,'Portal state persists after native save/reboot',closed=closed)

def end_choice(game,base,save):
 initial=shop_save(game,base,flags=(0x11,0x13,0x33,0x35,0x39,0x3a,0x3d,0x40) if game.name=='ages' else ())
 # Include the persistent room bits written by Ganon's native death handler.
 zroom,broom=(0xf1,0xf5) if game.name=='ages' else (0x9a,0x9e)
 changes=[('wGroup5RoomFlags',0x80,zroom),('wGroup5RoomFlags',0x80,broom)]
 if game.name=='ages':changes.append(('wGroup4RoomFlags',0x80,0xfc))
 initial=update_save(game,initial,changes)
 result=ending_save(game,initial,save=save)
 if not save:assert result==initial
 with game.boot(relocate(game,result)) as e:
  load(game,e,LOCATIONS[game.name]);assert_entrance(game,e,save);approach(game,e,save)
 record(game,'Native final save choice controls portal closure',accept_save=save,
        boundary='Prepared credits screen with native boss-death room bits; native prompt, battery save and reload')

def unrelated_portal(game,base):
 location=(5,0x20,0x88,0x78)
 with game.boot(quest_save(game,base,location,linked=True,finished=True)) as e:
  load(game,e,location)
  assert actors(e,(0xe1,)),'Unrelated dungeon portal disappeared after clear'
  game.pause_and_resume(e,'start')
  assert actors(e,(0xe1,))
 record(game,'Unrelated Seasons dungeon portal retained after linked clear')

if __name__=='__main__':
 OUT.mkdir(parents=True,exist_ok=True)
 for key in ('TEMP','TMP','TMPDIR','APPDATA','LOCALAPPDATA','XDG_CACHE_HOME','XDG_CONFIG_HOME','XDG_DATA_HOME'):os.environ[key]=str(SCRATCH)
 from pyboy import PyBoy
 chest.PyBoy=PyBoy
 for name in ('ages','seasons'):
  game=Game(name);base=game.new_file()
  for closed in (False,True):lifecycle(game,ready(game,base,closed),closed)
  for save in (False,True):end_choice(game,base,save)
  if name=='seasons':unrelated_portal(game,base)

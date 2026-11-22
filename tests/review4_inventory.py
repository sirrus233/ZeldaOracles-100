"""Collect potentially stale story text and its source references for manual review."""
import json
import re
import sys
from emit_heart_patches import SOURCE, PROJECT, WORK
import yaml
OUT=PROJECT/'outputs/Postgame Code Review 4'
pattern=re.compile(r'Twinrova|Ganon|Veran|Onox|kidnap|save.{0,30}Zelda|rescue|Impa|Holodrum|Labrynna|peace|trouble|Eye.of.Deceit',re.I|re.S)
rows=[]
terminal=[]
for game in ('ages','seasons'):
    refs={}
    for domain in ('code','object_code','scripts'):
        for p in (SOURCE/domain).rglob('*.s'):
            if ('ages' if game=='seasons' else 'seasons') in p.parts: continue
            for line_number,line in enumerate(p.read_text(encoding='utf-8').splitlines(),1):
                for tx in re.findall(r'TX_[0-9a-f]{4}',line):
                    refs.setdefault(tx,[]).append(f'{p.relative_to(SOURCE).as_posix()}:{line_number}: {line.strip()}')
    data=yaml.safe_load((SOURCE/f'text/{game}/text.yaml').read_text(encoding='utf-8'))
    text_map={}
    for group in data['groups']:
        for entry in group['data']:
            names=entry.get('name',[])
            if isinstance(names,str): names=[names]
            for tx in names: text_map[tx]=entry.get('text','')
            if pattern.search(entry.get('text','')):
                rows.append(dict(game=game,ids=names,text=entry.get('text',''),
                                 refs=[r for tx in names for r in refs.get(tx,[])]))
    (OUT/f'{game}-all-text.json').write_text(json.dumps(text_map,indent=2))
    for p in (SOURCE/'scripts'/game).glob('*.s'):
        lines=p.read_text().splitlines()
        for i,line in enumerate(lines):
            if not re.match(r'^\w.*(?:postGame|postgame|gameFinished|GameFinished|finishedGame|FinishedGame).*:',line): continue
            block=[]
            for row in lines[i+1:]:
                if re.match(r'^\w[^;]*:',row): break
                block.append(row)
            ids=list(dict.fromkeys(re.findall(r'TX_[0-9a-f]{4}','\n'.join(block))))
            terminal.append(dict(game=game,source=f'{p.relative_to(SOURCE)}:{i+1}',label=line,
                                 ids=ids,texts=[text_map.get(tx,'') for tx in ids]))
(OUT/'terminal-speeches.json').write_text(json.dumps(terminal,indent=2))
(OUT/'story-text-inventory.json').write_text(json.dumps(rows,indent=2))
print('Collected',len(rows),'story-related text entries')

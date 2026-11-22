"""Create a small player download containing only patches and instructions."""
from pathlib import Path
import json,zipfile
from layout import REPO
from check_public_tree import check

def main():
    check()
    out=REPO/'dist/Oracle-100-Percent-Patches.zip'
    if out.exists():raise SystemExit('Release archive already exists; move it aside before regenerating')
    out.parent.mkdir(exist_ok=True)
    manifest=json.loads((REPO/'patches/manifest.json').read_text())
    for row in manifest['games'].values():row['patch']=Path(row['patch']).name
    instructions='''Oracle 100 Percent — Ages and Seasons

Apply each BPS directly to its matching original USA/Australia retail ROM.
Use a BPS-compatible ROM patcher. Do not stack patches or overwrite your backups.
ROMs and emulators are not included. Python/build tools are not needed to play.

Start either game normally, then the other as a linked game. Keep both saves and
use the original password system. Hero's Cave is available early in Game 1; its
puzzles still require the original equipment. Seasons Game 1 uses the upper door
above the wooden-sword cave. Return after Game 1's clear for the extra heart
chest. Complete the original ring quests
for paired ring rewards. Appraise both and transfer them to Game 2 immediately.
Finish and save the linked second game for the Victory Ring.
The Room of Rites entrance closes after that final save.
Use Vasu's ring secrets to exchange the collected rings between saves.

Required input SHA1:
Ages:    880374fb978b18af4aa529e2e32f7ffb4d7dd2f4
Seasons: ba1268290fb2b1b70505d2d7b5825fc8a4816a4b

See manifest.json for full input/output/patch hashes and SHA256SUMS for patch
download integrity. Advance Shop rings keep their original GBA hardware check.
This unofficial modification is not endorsed by Nintendo or Capcom.

Validation uses prepared checkpoints, not complete playthroughs of both orders.
Authentic GBA startup and physical linking/hardware remain unverified.
'''
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
        for row in manifest['games'].values():
            z.write(REPO/'patches'/row['patch'],row['patch'])
        z.writestr('README.txt',instructions)
        z.writestr('manifest.json',json.dumps(manifest,indent=2)+'\n')
        z.write(REPO/'patches/SHA256SUMS','SHA256SUMS')
        z.write(REPO/'NOTICE.md','NOTICE.md')
        z.write(REPO/'LICENSE','LICENSE')
    print(out)

if __name__=='__main__':main()

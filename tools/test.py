"""Run local ROM-dependent regressions; never fetch games or install packages."""
import argparse,json,subprocess,sys
from concurrent.futures import ThreadPoolExecutor,as_completed
from hashlib import sha256
from shutil import copyfile
from time import perf_counter
from layout import REPO,LOCAL,SOURCE,local_environment

SUITES=[
 ('world','test_postgame_world.py','--givers'),('isolation','test_linked_clear.py'),
 ('rescue-roles','test_rescue_role_retirement.py'),('maku','test_maku_completion.py'),
 ('rites','test_rites_closure.py'),
 ('ring-quests','test_ring_quests.py'),('dependencies','test_completion_dependencies.py','--all'),
 ('heart-sequences','test_completion_hearts.py'),('optional','test_completion_optional.py'),
 ('heart','test_postgame_chest.py'),('caves','test_heros_cave.py'),
 ('early-caves','test_early_caves.py'),('sea','test_sea_of_storms.py'),
 ('story','test_ring_story.py'),('smoke','smoke_baseline.py'),
 ('full-credits','test_interaction_review.py','--ending'),
 ('full-ring-bag','test_interaction_review.py','--bag'),('victory','test_victory_ring.py'),
 ('native-book','test_native_book.py'),
 ('paired-transfer','test_double_reward_transfer.py'),
 ('transport','test_completion_transport.py'),('starts','test_completion_transport.py','--starts')]

def main():
    local_environment()
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--suite',action='append',choices=[s[0] for s in SUITES])
    parser.add_argument('--jobs',type=int,default=2,choices=(1,2))
    parser.add_argument('--development',action='store_true',help='Test local edits using locally generated BPS files')
    args=parser.parse_args()
    selected=[s for s in SUITES if not args.suite or s[0] in args.suite]
    if any(s[0]=='paired-transfer' for s in selected) and not any(s[0]=='ring-quests' for s in selected):
        selected=[s for s in SUITES if s in selected or s[0]=='ring-quests']
    manifest=json.loads((REPO/'patches/manifest.json').read_text())
    actual_roms={}
    for name,entry in manifest['games'].items():
        for path,expected in [(SOURCE/f'{name}.gbc',entry['target_sha256']),
                              (LOCAL/'roms'/f'Oracle of {name.title()}.gbc',entry['source_sha256'])]:
            if not path.is_file() or (sha256(path.read_bytes()).hexdigest()!=expected
                    and not (args.development and path==SOURCE/f'{name}.gbc')):
                raise SystemExit(f'Missing/mismatched input: {path}; see docs/DEVELOPING.md')
        actual_roms[name]=sha256((SOURCE/f'{name}.gbc').read_bytes()).hexdigest()
        dest=LOCAL/'outputs'/entry['patch'].split('/')[-1]
        dest.parent.mkdir(parents=True,exist_ok=True)
        if args.development:
            from bps import make_patch,apply_patch
            retail=(LOCAL/'roms'/f'Oracle of {name.title()}.gbc').read_bytes()
            target=(SOURCE/f'{name}.gbc').read_bytes()
            patch=make_patch(retail,target)
            if apply_patch(patch,retail)!=target:raise SystemExit('Development BPS roundtrip failed')
            dest.write_bytes(patch)
        else:copyfile(REPO/entry['patch'],dest)
    out=LOCAL/'test-results';out.mkdir(parents=True,exist_ok=True)
    def run(suite):
        label,script,*flags=suite;start=perf_counter()
        with (out/f'{label}.log').open('w',encoding='utf-8') as log:
            result=subprocess.run([sys.executable,'-X','utf8','-B',str(REPO/'tests'/script),*flags],
                cwd=REPO,stdout=log,stderr=subprocess.STDOUT)
        row=dict(suite=label,exit_code=result.returncode,seconds=round(perf_counter()-start,1))
        print(row,flush=True);return row
    rows=[]
    independent=[s for s in selected if s[0] not in ('paired-transfer','transport','starts')]
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        for job in as_completed([pool.submit(run,s) for s in independent]):rows.append(job.result())
    for suite in selected:
        if suite[0] in ('paired-transfer','transport','starts'):rows.append(run(suite))
    summary=dict(roms=actual_roms,development=args.development,suites=rows)
    (out/'summary.json').write_text(json.dumps(summary,indent=2))
    if any(r['exit_code'] for r in rows):raise SystemExit('Tests failed; see .local/test-results/*.log')

if __name__=='__main__':main()

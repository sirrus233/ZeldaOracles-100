"""Package committed patches and publish an existing version tag with GitHub CLI."""
import json,os,subprocess
from urllib.parse import quote
from layout import REPO
import make_release


def publish(tag, repository, server='https://github.com'):
    if not tag.startswith('v') or not repository:
        raise ValueError('A v-prefixed release tag and GitHub repository are required')
    make_release.main()
    manifest=json.loads((REPO/'patches/manifest.json').read_text(encoding='utf-8'))
    assets=[row['patch'] for row in manifest['games'].values()]
    assets += ['dist/Oracle-100-Percent-Patches.zip','patches/SHA256SUMS','patches/manifest.json']
    notes=REPO/'dist/release-notes.md'
    guide=f'{server.rstrip("/")}/{repository}/blob/{quote(tag,safe="")}/docs/PLAYING.md'
    notes.write_text(f'''Play Ages and Seasons once each, in either order, using the original linked-game password system.

Download the player ZIP for both BPS patches, a README with instructions, and checksums, or download either patch separately.
Apply each patch directly to its matching original USA/Australia retail ROM.

[Player instructions]({guide})

Automated testing uses prepared checkpoints; it does not constitute complete 100% playthroughs of both orders.
''',encoding='utf-8',newline='\n')
    command=['gh','release','create',tag,*assets,'--verify-tag',
             '--title',f'Oracle 100 Percent {tag}','--notes-file',str(notes)]
    if '-' in tag:command.append('--prerelease')
    subprocess.run(command,cwd=REPO,check=True)


if __name__=='__main__':
    publish(os.environ.get('RELEASE_TAG',''),os.environ.get('GH_REPO',''),
            os.environ.get('GITHUB_SERVER_URL','https://github.com'))

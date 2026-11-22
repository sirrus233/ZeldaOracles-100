"""Exercise release publication arguments without contacting GitHub."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import json,sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
import publish_release
from layout import SCRATCH


class ReleasePublication(unittest.TestCase):
    def test_assets_and_stable_or_prerelease(self):
        SCRATCH.mkdir(parents=True,exist_ok=True)
        for tag in ('v0.1.0','v0.1.0-beta.1'):
            with self.subTest(tag=tag),TemporaryDirectory(dir=SCRATCH) as folder:
                root=Path(folder);(root/'patches').mkdir();(root/'dist').mkdir()
                patches=['patches/Oracle of Ages - 100 Percent.bps',
                         'patches/Oracle of Seasons - 100 Percent.bps']
                manifest={'games':{str(i):{'patch':name} for i,name in enumerate(patches)}}
                (root/'patches/manifest.json').write_text(json.dumps(manifest),encoding='utf-8')
                with patch.object(publish_release,'REPO',root), \
                     patch.object(publish_release.make_release,'main') as package, \
                     patch.object(publish_release.subprocess,'run') as run:
                    publish_release.publish(tag,'example/oracle')
                package.assert_called_once_with()
                command=run.call_args.args[0]
                self.assertEqual(command[:4],['gh','release','create',tag])
                self.assertEqual(command[4:9],patches+[
                    'dist/Oracle-100-Percent-Patches.zip','patches/SHA256SUMS','patches/manifest.json'])
                self.assertIn('--verify-tag',command)
                self.assertEqual('--prerelease' in command,'-' in tag)
                self.assertEqual(run.call_args.kwargs,{'cwd':root,'check':True})
                notes=(root/'dist/release-notes.md').read_text(encoding='utf-8')
                self.assertIn(f'/blob/{tag}/docs/PLAYING.md',notes)
                self.assertIn('README',notes)

    def test_invalid_release_does_not_package_or_publish(self):
        for tag,repo in (('main','example/oracle'),('v0.1.0','')):
            with patch.object(publish_release.make_release,'main') as package, \
                 patch.object(publish_release.subprocess,'run') as run:
                with self.assertRaises(ValueError):publish_release.publish(tag,repo)
                package.assert_not_called();run.assert_not_called()


if __name__=='__main__':unittest.main()

"""Public CI: patch integrity and strict source-delta handling, no game data."""
from pathlib import Path
import sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from bps import make_patch,apply_patch
from source_patch import apply_text,sections
from check_public_tree import check

class PublicTools(unittest.TestCase):
    def test_bps_roundtrip_mixed_runs(self):
        source=bytes(range(256))*3
        target=bytearray(source);target[:4]=b'TEST';target[300:400]=bytes(100);target[-1]=7
        self.assertEqual(apply_patch(make_patch(source,target),source),target)

    def test_bps_rejects_wrong_source_and_corruption(self):
        patch=make_patch(b'original',b'modified')
        with self.assertRaises(ValueError):apply_patch(patch,b'not same')
        damaged=bytearray(patch);damaged[8]^=1
        with self.assertRaises(ValueError):apply_patch(damaged,b'original')

    def test_source_hunks_and_new_file(self):
        self.assertEqual(apply_text('one\ntwo\nthree\n','@@ -1,3 +1,3 @@\n one\n-two\n+new\n three\n'),'one\nnew\nthree\n')
        self.assertEqual(apply_text('','@@ -0,0 +1,1 @@\n+new\n'),'new\n')

    def test_source_rejects_context_and_count_mismatch(self):
        with self.assertRaises(ValueError):apply_text('wrong\n','@@ -1 +1 @@\n-old\n+new\n')
        with self.assertRaises(ValueError):apply_text('old\n','@@ -1,2 +1 @@\n-old\n+new\n')

    def test_source_rejects_unsafe_paths(self):
        for name in ('../escape','C:/escape','folder\\escape'):
            with self.assertRaises(ValueError):list(sections(f'--- /dev/null\n+++ b/{name}\n@@ -0,0 +1 @@\n+x\n'))

    def test_publication_manifest(self):
        self.assertEqual(check()['status'],'passed')

if __name__=='__main__':unittest.main()

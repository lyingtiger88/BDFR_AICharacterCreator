"""Pure Python tests for artist-authored morphs (no Maya required)."""
import json
import tempfile
import unittest
from pathlib import Path
from bdfr_morph_targets import N_VERTS, author, apply, load_folder, save

class SculptMorphTests(unittest.TestCase):
    def setUp(self):
        self.base=[(0.0,0.0,0.0)]*N_VERTS
        self.sculpt=list(self.base)
        self.sculpt[120]=(.05,.0,.01)

    def test_capture_and_blend(self):
        morph=author(self.base,self.sculpt,"breast_size","positive")
        result=apply(self.base,{("breast_size","positive"):morph},(.5,0,0))
        self.assertAlmostEqual(result[120][0],.025)
        self.assertEqual(result[121],[0.0,0.0,0.0])

    def test_unavailable_morph_does_not_distort(self):
        self.assertEqual(apply(self.base,{},(1,1,1)),[list(v) for v in self.base])

    def test_load_folder_ignores_metadata(self):
        with tempfile.TemporaryDirectory() as folder:
            save(Path(folder)/"breast_size_positive.json",
                 author(self.base,self.sculpt,"breast_size","positive"))
            (Path(folder)/"reference.json").write_text(json.dumps({"shape_key":["neutral",[],0,0,0,0]}))
            library=load_folder(folder)
            self.assertIn(("breast_size","positive"),library)

    def test_bad_channel_fails(self):
        with self.assertRaises(ValueError):
            author(self.base,self.sculpt,"chest_wall","positive")

if __name__=="__main__":
    unittest.main()

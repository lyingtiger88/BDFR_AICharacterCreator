"""Run without Maya: python -m unittest discover -s tests -v"""
import json
import tempfile
import unittest
from pathlib import Path
from bdfr_character_presets import validated, save, load

def example():
    return {"schema":1,"gender":"neutral","betas":[0.0]*10,
            "shoulder":0,"elbow":0,"hand":0,"expression":0}

class PresetTests(unittest.TestCase):
    def test_roundtrip(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"preset.json"
            data=example()
            data["betas"][0]=-3
            save(path,data)
            self.assertEqual(load(path)["betas"][0],-3.0)
            self.assertEqual(load(path)["gender"],"neutral")

    def test_bad_values(self):
        for broken in (float("nan"),float("inf"),4,"2",True):
            data=example()
            data["betas"][0]=broken
            with self.assertRaises(ValueError):
                validated(data)

    def test_invalid_gender(self):
        data=example()
        data["gender"]="invalid"
        with self.assertRaises(ValueError):
            validated(data)

    def test_extra_data_not_forwarded(self):
        data=example()
        data["unexpected"]="something"
        self.assertNotIn("unexpected",validated(data))

if __name__=="__main__":
    unittest.main()

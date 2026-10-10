"""No Maya required: python -m unittest discover -s tests -v"""
import unittest
from bdfr_body_details import deform
from bdfr_character_presets import validated

class BodyDetailsTests(unittest.TestCase):
    def test_zero_is_identity(self):
        pts=[(-.1,0.5,.1),(.1,.5,-.1)]
        self.assertEqual(deform(pts),pts)

    def test_front_breast_and_rear_glute_independent(self):
        # Simplified upright model of height 2; bell-shaped masks.
        pts=[(-.126,.41,.15),(.126,.41,.15),(.13,-.166,-.126),(0,-1,0),(0,1,0)]
        front=deform(pts,breast_size=1)
        self.assertGreater(front[0][2],pts[0][2])
        self.assertGreater(front[1][2],pts[1][2])
        self.assertEqual(front[2][2],pts[2][2])
        rear=deform(pts,glute_size=1)
        self.assertLess(rear[2][2],pts[2][2])
        self.assertEqual(rear[0][2],pts[0][2])

    def test_legacy_preset_loads_zero_details(self):
        data={"schema":1,"gender":"female","betas":[0]*10,
              "shoulder":0,"elbow":0,"hand":0,"expression":0}
        result=validated(data)
        self.assertEqual(result["breast_size"],0)
        self.assertEqual(result["hip_width"],0)
        self.assertEqual(result["glute_size"],0)

    def test_invalid_details_rejected(self):
        data={"schema":1,"gender":"female","betas":[0]*10,
              "shoulder":0,"elbow":0,"hand":0,"expression":0,"breast_size":2}
        with self.assertRaises(ValueError):
            validated(data)

if __name__=="__main__":
    unittest.main()

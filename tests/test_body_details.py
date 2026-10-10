"""Region separation tests independent of Maya."""
import unittest
from bdfr_body_details import deform
from bdfr_character_presets import validated

class BodyDetailsTests(unittest.TestCase):
    @staticmethod
    def samples():
        # Body height 2m, +Z front. Centreline anchors define local depth.
        return [(0,-1,0),(0,1,0),(0,.42,0),(0,-.12,0),
                (.16,.42,.13),(-.16,.42,.13),   # cup surfaces
                (.16,.42,-.13),                 # chest wall/back
                (.16,-.12,-.14),(-.16,-.12,-.14), # posterior cheeks
                (.16,-.12,.14),                # anterior upper thigh
                (.28,-.04,0),(-.28,-.04,0)]   # lateral hip

    def test_zero_identity(self):
        pts=self.samples()
        self.assertEqual(deform(pts),pts)

    def test_breast_only_anterior_cups(self):
        pts=self.samples()
        out=deform(pts,breast_size=1)
        self.assertGreater(out[4][2],pts[4][2])
        self.assertGreater(out[5][2],pts[5][2])
        for idx in (0,1,2,3,6,7,8,9):
            self.assertEqual(out[idx],pts[idx])

    def test_glutes_do_not_move_front_thigh(self):
        pts=self.samples()
        out=deform(pts,glute_size=1)
        self.assertLess(out[7][2],pts[7][2])
        self.assertLess(out[8][2],pts[8][2])
        self.assertEqual(out[9],pts[9])
        self.assertEqual(out[4],pts[4])

    def test_hip_is_side_only(self):
        pts=self.samples()
        out=deform(pts,hip_width=1)
        self.assertGreater(out[10][0],pts[10][0])
        self.assertLess(out[11][0],pts[11][0])
        self.assertEqual(out[9],pts[9])

    def test_old_preset_defaults(self):
        data={"schema":1,"gender":"female","betas":[0]*10,
              "shoulder":0,"elbow":0,"hand":0,"expression":0}
        result=validated(data)
        for key in ("breast_size","hip_width","glute_size"):
            self.assertEqual(result[key],0)

if __name__=="__main__":unittest.main()

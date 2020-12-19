import unittest
import cv2
from pprint import pprint
import requests_cache  # https://requests-cache.readthedocs.io/en/latest/
from geosatcollage import eumetsat, get_latest_full_disk_image, rambinfo
from geosatcollage import maskup, label_lower_left, buildcollage, satinfo, label_upper_right

class InnexpensiveTests(unittest.TestCase):
    def setUp(self):
        requests_cache.install_cache('test_cache', backend='sqlite', expire_after=36000)

    def test_eumetsat_from_euro(self):
        for sat in ['meteosat-8', 'meteosat-11']:
            url,dt,allfiles = eumetsat(sat)
            self.assertGreater(len(url), 110)
            self.assertGreaterEqual(dt.year, 2019)

    def test_get_info_from_cira(self):
        for sat in ['meteosat-8', 'meteosat-11', 'himawari', 'goes-16', 'goes-17']:
            dates = rambinfo(sat=sat)
            self.assertGreater(len(dates), 90)
            self.assertGreater(dates[-1], 20201218000000)

class ExpensiveTests(unittest.TestCase):
    def setUp(self):
        requests_cache.install_cache('test_cache', backend='sqlite', expire_after=36000)

    def test_getlatest(self):
        for sat in ['meteosat-8', 'meteosat-11', 'himawari', 'goes-16', 'goes-17']:
            filename = get_latest_full_disk_image(sat)
            self.assertGreater(len(filename), 20)
            self.assertTrue('png' in filename)
            image = cv2.imread(filename)
            resized = cv2.resize(image, (640, 640), interpolation=cv2.INTER_AREA)
            cv2.imwrite(f'{sat}/test.png', resized)

    def test_ur(self):
        filename='foo.jpg'
        newfile = label_upper_right(filename, '20201219 1600Z')

class DevTests(unittest.TestCase):
    def setUp(self):
        requests_cache.install_cache('test_cache', backend='sqlite', expire_after=3600)

    def testLabel(self):
        for sat in satinfo.keys():
            filename = get_latest_full_disk_image(sat)
            foo = label_lower_left(filename, sat)
            image = cv2.imread(filename)
            resized = cv2.resize(image, (640, 640), interpolation=cv2.INTER_AREA)
            cv2.imwrite(f'{sat}/test.png', resized)

    def testMask(self):
        filename='meteosat-8/20201219133000.png'
        maskup(filename)

    def testbuildcollage(self):
        buildcollage()

    def testone(self):
        sat='goes-16'
        filename = get_latest_full_disk_image(sat)


if __name__ == '__main__':
    unittest.main()

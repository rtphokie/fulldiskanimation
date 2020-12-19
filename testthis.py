import unittest
import cv2
from pprint import pprint
import requests_cache  # https://requests-cache.readthedocs.io/en/latest/
from geosatcollage import eumetsat, get_latest_full_disk_image, rambinfo, maskup, label_image

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
            filename = get_latest_full_disk_image(sat=sat)
            self.assertGreater(len(filename), 20)
            self.assertTrue('png' in filename)
            image = cv2.imread(filename)
            resized = cv2.resize(image, (640, 640), interpolation=cv2.INTER_AREA)
            cv2.imwrite(f'{sat}/test.png', resized)

class DevTests(unittest.TestCase):
    def setUp(self):
        requests_cache.install_cache('test_cache', backend='sqlite', expire_after=36000)

    def testLabel(self):
        for sat in ['meteosat-8', 'meteosat-11', 'himawari', 'goes-16', 'goes-17']:
            filename = get_latest_full_disk_image(sat=sat)
            print(filename)
            foo = label_image(filename, sat)
            image = cv2.imread(filename)
            resized = cv2.resize(image, (640, 640), interpolation=cv2.INTER_AREA)
            cv2.imwrite(f'{sat}/test.png', resized)

    def testMask(self):
        # filename='goes-16/20201219133021.png'
        # maskup(filename)
        filename='meteosat-8/20201219133000.png'
        maskup(filename)


if __name__ == '__main__':
    unittest.main()

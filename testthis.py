import unittest
from pprint import pprint
import requests_cache  # https://requests-cache.readthedocs.io/en/latest/
from geosatcollage import eumetsat, get_latest_full_disk_image, rambinfo

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

    def test_build(self):
        images=[]
        for sat in ['meteosat-8', 'himawari', 'goes-17', 'goes-16', 'meteosat-11', ]:
            print(sat)
            satfilename = get_latest_full_disk_image(sat=sat)
            print(satfilename)
            return
            im = cv2.imread(satfilename)
            print(im.shape)
            images.append(cv2.imread(satfilename))
        im_colage = cv2.hconcat(images)
        cv2.imwrite('foo.jpg', im_colage)

    def test_mask(self):
        sat='goes-17'
        satfilename = get_latest_full_disk_image(sat=sat)


class DevTests(unittest.TestCase):
    def setUp(self):
        requests_cache.install_cache('test_cache', backend='sqlite', expire_after=36000)

if __name__ == '__main__':
    unittest.main()

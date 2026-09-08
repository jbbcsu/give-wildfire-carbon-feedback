import unittest
from acquire_registered_heat_cutout import check_archive_identity

class TestArchiveIdentity(unittest.TestCase):
    def test_registered_url(self):
        check_archive_identity('https://files.isimip.org/api/v2/output/isimip-download-abc.zip','abc',100,'etag')
    def test_bad_url_length_etag(self):
        good='https://files.isimip.org/api/v2/output/isimip-download-abc.zip'
        for url,length,etag in [(good.replace('https','http'),100,'e'),(good.replace('files.isimip.org','example.org'),100,'e'),(good+'?redirect=1',100,'e'),(good.replace('abc','other'),100,'e'),(good,17*2**20,'e'),(good,0,'e'),(good,100,None)]:
            with self.assertRaises(ValueError):check_archive_identity(url,'abc',length,etag)

if __name__=='__main__':unittest.main()

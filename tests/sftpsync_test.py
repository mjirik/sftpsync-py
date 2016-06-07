import unittest


import os.path as op
class MyTestCase(unittest.TestCase):
    def test_connection(self):
        from sftpsync import Sftp

        sftp = Sftp('147.228.47.162', 'paul', 'P4ul')
        # hu = sftp.sftp.listdir_attr("from_server")
        dir_list = sftp.sftp.listdir_attr("from_server")
        first_fn = dir_list[0].filename
        self.assertEqual(first_fn, "test.txt")

    def test_sync(self):
        from sftpsync import Sftp

        sftp = Sftp('147.228.47.162', 'paul', 'P4ul')
        # hu = sftp.sftp.listdir_attr("from_server")
        dir_list = sftp.sftp.listdir_attr("from_server")

        src = 'from_server/'
        # src = 'to_server'
        dst = 'test_temp/'
        dst = op.expanduser(dst)

        # We don't want to backup everything
        exclude = [r'^Music/', r'^Video/']

        sftp.sync(src, dst, download=True, exclude=exclude, delete=False)

        self.assertTrue(op.exists(op.join(dst,"test.txt")))
if __name__ == '__main__':
    unittest.main()

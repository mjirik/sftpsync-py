import logging
logger = logging.getLogger(__name__)
import unittest
import shutil
import os.path as op

clean = False

class MyTestCase(unittest.TestCase):

    def test_connection(self):
        from sftpsync import Sftp

        sftp = Sftp('147.228.47.162', 'paul', 'P4ul')
        # hu = sftp.sftp.listdir_attr("from_server")
        dir_list = sftp.sftp.listdir_attr("from_server")
        self.assertIn(dir_list[0].filename, ["test.txt", "foo"])
        self.assertIn(dir_list[1].filename, ["test.txt", "foo"])
        dir_list2 = sftp.sftp.listdir_attr("from_server/foo")
        self.assertEqual(dir_list2[0].filename, 'bar.txt')

    def test_sync(self):
        from sftpsync import Sftp

        src = 'from_server/'
        dst = 'test_temp/'
        sftp = Sftp('147.228.47.162', 'paul', 'P4ul')

        dst = op.expanduser(dst)

        if op.exists(dst):
            shutil.rmtree(dst)
        # We don't want to backup everything
        exclude = [r'^Music/', r'^Video/']
        sftp.sync(src, dst, download=True, exclude=exclude, delete=False)
        self.assertTrue(op.exists(op.join(dst,"test.txt")))
        if clean and op.exists(dst):
            shutil.rmtree(dst)

    def test_sync_different_separator(self):
        from sftpsync import Sftp

        src = 'from_server/'
        dst = 'test_temp_different_separator\\'
        sftp = Sftp('147.228.47.162', 'paul', 'P4ul')

        dst = op.expanduser(dst)
        if op.exists(dst):
            shutil.rmtree(dst)

        # We don't want to backup everything
        exclude = [r'^Music/', r'^Video/']

        sftp.sync(src, dst, download=True, exclude=exclude, delete=False)
        self.assertTrue(op.exists(op.join(dst,"test.txt")))
        if clean and op.exists(dst):
            shutil.rmtree(dst)

    def test_sync_abspath(self):
        from sftpsync import Sftp

        src = 'from_server/'
        dst = 'test_temp_abspath\\'
        sftp = Sftp('147.228.47.162', 'paul', 'P4ul')

        dst = op.abspath(dst)
        dst += '\\'
        if op.exists(dst):
            shutil.rmtree(dst)

        # We don't want to backup everything
        exclude = [r'^Music/', r'^Video/']
        logger.debug("src %s", src)
        logger.debug("dst %s", dst)
        sftp.sync(src, dst , download=True, exclude=exclude, delete=False)
        self.assertTrue(op.exists(op.join(dst,"test.txt")))

        if clean and op.exists(dst):
            shutil.rmtree(dst)

if __name__ == '__main__':
    unittest.main()

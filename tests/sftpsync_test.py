import logging
logger = logging.getLogger(__name__)
import unittest
import shutil
import os
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
        self.assertTrue(op.exists(op.join(dst.rstrip("\\"),"test.txt")))
        if clean and op.exists(dst):
            shutil.rmtree(dst)

    def test_sync_abspath(self):
        from sftpsync import Sftp

        src = 'from_server/'
        dst = 'test_temp_abspath\\'
        sftp = Sftp('147.228.47.162', 'paul', 'P4ul')

        dst = op.abspath(dst)
        if not (dst.endswith('/') or dst.endswith('\\')):
            dst += '\\'
        if op.exists(dst):
            shutil.rmtree(dst)

        # We don't want to backup everything
        exclude = [r'^Music/', r'^Video/']
        logger.debug("src %s", src)
        logger.debug("dst %s", dst)
        sftp.sync(src, dst , download=True, exclude=exclude, delete=False)
        expected_path = op.join(dst.rstrip("\\"),"test.txt")
        logger.debug("Expected path: %s", expected_path)
        self.assertTrue(op.exists(expected_path))

        if clean and op.exists(dst):
            shutil.rmtree(dst)

    def test_sync_upload(self):
        from sftpsync import Sftp
        src = 'to_server/'
        src = 'c:/Users/mjirik/projects/sftpsync-py/to_server/'
        dst = 'to_server/'

        # create test dir
        srcfile = op.join(src, 'test_file.txt')

        if not op.exists(src):
            logger.debug('creating dir %s', src)
            os.makedirs(src)

        with open(srcfile,"a+") as f:
            f.write("text\n")

        # connect to sftp
        sftp = Sftp('147.228.47.162', 'paul', 'P4ul')

        # make sure that test file is not on server
        dir_list = sftp.sftp.listdir_attr("to_server/")
        fnames = [record.filename for record in dir_list]
        if 'test_file.txt' in fnames:
            sftp.sftp.remove("to_server/test_file.txt")

        # Make test: sync local directory
        exclude = [r'^Music/', r'^Video/']
        sftp.sync(src, dst, download=False, exclude=exclude, delete=True)
        dir_list = sftp.sftp.listdir_attr("to_server/")
        # check if file is created
        self.assertEqual(dir_list[0].filename, 'test_file.txt')

        # remove file and sync again
        os.remove(srcfile)
        sftp.sync(src, dst, download=False, exclude=exclude, delete=True)
        dir_list = sftp.sftp.listdir_attr("to_server/")
        # check if direcotry is empty
        self.assertEqual(len(dir_list), 0)

if __name__ == '__main__':
    unittest.main()

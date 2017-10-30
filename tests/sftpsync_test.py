import logging
logger = logging.getLogger(__name__)
import unittest
import shutil
import os
import os.path as op

clean = False


def touch(fname, times=None):
    with open(fname, 'a'):
        os.utime(fname, times)


class SftpTestBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import subprocess
        import time

        super(SftpTestBase, cls).setUpClass()
        # prepare structure for test SFTP server
        pth_from = "test_server/from_server/foo"
        pth_to = "test_server/to_server"
        if not os.path.exists(pth_from):
            os.makedirs(pth_from)
        if not os.path.exists(pth_to):
            os.makedirs(pth_to)
        touch("test_server/from_server/test.txt")
        touch("test_server/from_server/foo/bar.txt")
        # create RSA key
        if not os.path.exists("id_rsa"):
            os.system('ssh-keygen -t rsa -q -f id_rsa -P ""')

        # run test SFTP server
        # port = 22
        cls.port = 3373
        cls.host = "localhost"

        subprocess.Popen(
            "sftpserver -k ../id_rsa -p " + str(cls.port),
            cwd="test_server",
            shell=True)
        time.sleep(1)

        # Server is available for all users and any password
        # sftp://user@localhost:3373/

    @classmethod
    def tearDownClass(cls):
        super(SftpTestBase, cls).setUpClass()
        os.system("pkill sftpserver")


class SftpTests(SftpTestBase):
    def test_test_server(self):
        import paramiko
        pkey = paramiko.RSAKey.from_private_key_file('id_rsa')
        transport = paramiko.Transport(('localhost', self.port))
        transport.connect(username='admin', password='admin')# , pkey=pkey)
        sftp = paramiko.SFTPClient.from_transport(transport)
        sftp.listdir('.')
        transport.close()

    def test_connection(self):
        from sftpsync import Sftp

        sftp = Sftp(self.host, 'paul', 'P4ul', port=self.port)
        # hu = sftp.sftp.listdir_attr("from_server")
        dir_list = sftp.sftp.listdir_attr("from_server")
        self.assertIn(dir_list[0].filename, ["test.txt", "foo"])
        self.assertIn(dir_list[1].filename, ["test.txt", "foo"])
        dir_list2 = sftp.sftp.listdir_attr("from_server/foo")
        self.assertEqual(dir_list2[0].filename, 'bar.txt')

        sftp.client.close()

    def test_sync(self):
        from sftpsync import Sftp

        src = 'from_server/'
        dst = 'test_temp/'
        sftp = Sftp(self.host, 'paul', 'P4ul', port=self.port)

        dst = op.expanduser(dst)

        if op.exists(dst):
            shutil.rmtree(dst)
        # We don't want to backup everything
        exclude = [r'^Music/', r'^Video/']
        sftp.sync(src, dst, download=True, exclude=exclude, delete=False)
        self.assertTrue(op.exists(op.join(dst, "test.txt")))
        if clean and op.exists(dst):
            shutil.rmtree(dst)

        sftp.client.close()

    def test_sync_different_separator(self):
        from sftpsync import Sftp

        src = 'from_server/'
        dst = 'test_temp_different_separator\\'
        sftp = Sftp(self.host, 'paul', 'P4ul', port=self.port)

        dst = op.expanduser(dst)
        if op.exists(dst):
            shutil.rmtree(dst)

        # We don't want to backup everything
        exclude = [r'^Music/', r'^Video/']

        sftp.sync(src, dst, download=True, exclude=exclude, delete=False)
        self.assertTrue(op.exists(op.join(dst.rstrip("\\"),"test.txt")))
        if clean and op.exists(dst):
            shutil.rmtree(dst)

        sftp.client.close()

    def test_sync_abspath(self):
        from sftpsync import Sftp

        src = 'from_server/'
        dst = 'test_temp_abspath\\'
        sftp = Sftp(self.host, 'paul', 'P4ul', port=self.port)

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

        sftp.client.close()

    def test_sync_upload(self):
        from sftpsync import Sftp
        src = 'to_server/'
        dst = 'to_server/'

        # create test dir
        srcfile = op.join(src, 'test_file.txt')

        if not op.exists(src):
            logger.debug('creating dir %s', src)
            os.makedirs(src)

        with open(srcfile,"a+") as f:
            f.write("text\n")

        # connect to sftp
        sftp = Sftp(self.host, 'paul', 'P4ul', port=self.port)

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

        sftp.client.close()


class SftpTestFilePermissions(SftpTestBase):
    def setUp(self):
        from sftpsync import Sftp
        self.sftp = Sftp(self.host, 'paul', 'P4ul', port=self.port)

        self.local_dir = 'test_local_file_permissions'
        self.remote_relative_dir = 'test_remote_file_permissions'  # Relative to the remote session
        self.remote_dir = os.path.join('test_server', self.remote_relative_dir)

        self.test_local_sub_dir = os.path.join(self.local_dir, 'test_dir')
        self.test_local_file = os.path.join(self.local_dir, 'test.txt')
        self.test_remote_sub_dir = os.path.join(self.remote_dir, 'test_dir')
        self.test_remote_file = os.path.join(self.remote_dir, 'test.txt')

    def tearDown(self):
        shutil.rmtree(self.local_dir)
        shutil.rmtree(self.remote_dir)
        self.sftp.client.close()

    def test_file_permissions_download(self):
        # Make remote files.
        os.makedirs(self.test_remote_sub_dir)
        touch(self.test_remote_file)

        # Change permissions.
        os.chmod(self.test_remote_sub_dir, os.stat(self.test_remote_sub_dir).st_mode | 0o007)
        os.chmod(self.test_remote_file, os.stat(self.test_remote_file).st_mode | 0o007)

        self.sftp.sync(src=self.remote_relative_dir, dst=self.local_dir, download=True)

        # Check permissions match.
        self.assertEqual(os.stat(self.test_remote_sub_dir).st_mode, os.stat(self.test_local_sub_dir).st_mode)
        self.assertEqual(os.stat(self.test_remote_file).st_mode, os.stat(self.test_local_file).st_mode)

        # Change permissions again (to check that files are re-syncd).
        os.chmod(self.test_remote_sub_dir, os.stat(self.test_remote_sub_dir).st_mode & ~0o007)
        os.chmod(self.test_remote_file, os.stat(self.test_remote_file).st_mode & ~0o007)

        self.sftp.sync(src=self.remote_relative_dir, dst=self.local_dir, download=True)

        # Check permissions match.
        self.assertEqual(os.stat(self.test_remote_sub_dir).st_mode, os.stat(self.test_local_sub_dir).st_mode)
        self.assertEqual(os.stat(self.test_remote_file).st_mode, os.stat(self.test_local_file).st_mode)

    def test_file_permissions_upload(self):
        # Make local files.
        os.makedirs(self.test_local_sub_dir)
        touch(self.test_local_file)

        # Change permissions.
        os.chmod(self.test_local_sub_dir, os.stat(self.test_local_sub_dir).st_mode | 0o007)
        os.chmod(self.test_local_file, os.stat(self.test_local_file).st_mode | 0o007)

        self.sftp.sync(src=self.local_dir, dst=self.remote_relative_dir, download=False)

        # Check permissions match.
        self.assertEqual(os.stat(self.test_local_sub_dir).st_mode, os.stat(self.test_remote_sub_dir).st_mode)
        self.assertEqual(os.stat(self.test_local_file).st_mode, os.stat(self.test_remote_file).st_mode)

        # Change permissions again (to check that files are re-syncd).
        os.chmod(self.test_local_sub_dir, os.stat(self.test_local_sub_dir).st_mode & ~0o007)
        os.chmod(self.test_local_file, os.stat(self.test_local_file).st_mode & ~0o007)

        self.sftp.sync(src=self.local_dir, dst=self.remote_relative_dir, download=False)

        # Check permissions match.
        self.assertEqual(os.stat(self.test_local_sub_dir).st_mode, os.stat(self.test_remote_sub_dir).st_mode)
        self.assertEqual(os.stat(self.test_local_file).st_mode, os.stat(self.test_remote_file).st_mode)


if __name__ == '__main__':
    unittest.main()

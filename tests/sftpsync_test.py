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

def runServer():
    return host, port, process

class MyTestCase(unittest.TestCase):


    @classmethod
    def setUpClass(self):
        import subprocess
        import time

        super(MyTestCase, self).setUpClass()
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
        self.port = 3373
        self.host = "localhost"

        subprocess.Popen(
            "sftpserver -k ../id_rsa -p " + str(self.port),
            cwd="test_server",
            shell=True)
        time.sleep(1)

        # Server is available for all users and any password
        # sftp://user@localhost:3373/

    @classmethod
    def tearDownClass(self):
        super(MyTestCase, self).setUpClass()
        os.system("pkill sftpserver")

    def test_test_server(self):
        import paramiko
        pkey = paramiko.RSAKey.from_private_key_file('id_rsa')
        transport = paramiko.Transport(('localhost', self.port))
        transport.connect(username='admin', password='admin')# , pkey=pkey)
        sftp = paramiko.SFTPClient.from_transport(transport)
        sftp.listdir('.')

    def test_connection(self):
        from sftpsync import Sftp

        sftp = Sftp(self.host, 'paul', 'P4ul', port=self.port)
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

if __name__ == '__main__':
    unittest.main()

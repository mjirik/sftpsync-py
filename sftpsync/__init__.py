import os
import re
import socket
from stat import S_ISDIR
from datetime import datetime
import logging

import paramiko


MTIME_TOLERANCE = 3

logger = logging.getLogger(__name__)


class AuthenticationError(Exception): pass
class TimeoutError(Exception): pass
class SshError(Exception): pass


class Sftp(object):

    def __init__(self, host, username, password=None, port=22, timeout=10,
                max_attempts=3, **kwargs):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.sftp = None
        for i in range(max_attempts):
            try:
                self.client.connect(host, port=port, username=username,
                        password=password, timeout=timeout, **kwargs)
                self.sftp = self.client.open_sftp()
                return
            except (paramiko.BadHostKeyException, paramiko.AuthenticationException) as e:
                raise AuthenticationError(str(e))
            except socket.timeout as e:
                raise TimeoutError(str(e))
            except Exception as e:
                if i == max_attempts - 1:
                    raise SshError(str(e))

    def _join(self, path1, path2, remote, path2_start=None):
        if remote:
            if not path2_start is None:
                # this is necessary on windows
                # path2 is there different from the linux
                path2 = path2.replace('\\','/')
                path2_start = path2_start.replace('\\','/')
                if path2_start[-1] != '/':
                    path2_start += '/'

                if path2.startswith(path2_start):
                    logger.debug('make relative path to start')
                    logger.debug("path2       : %s", path2)
                    logger.debug("path2_start : %s", path2_start)
                    path2 = path2[len(path2_start):]
                    logger.debug("path2 after : %s", path2)

            dst = self._join_remote(path1, path2)
        else:
            dst = os.path.join(path1, path2)
            # dst = self._join_remote(path1, path2)
        return dst

    def _join_remote(self, path1, path2):
        """
        for remote path is separator always "/"
        :param path1:
        :param path2:
        :return: joined paths
        """

        path1 = path1.rstrip('/')
        return path1 + "/" + path2

    def _walk_remote(self, path, topdown=True):
        try:
            res = self.sftp.listdir_attr(path)
        except IOError:
            res = []

        for stat in res:
            file = self._join_remote(path, stat.filename)

            if not S_ISDIR(stat.st_mode):
                yield 'file', file, stat
            else:
                if topdown:
                    yield 'dir', file, stat
                    for res in self._walk_remote(file, topdown=topdown):
                        yield res
                else:
                    for res in self._walk_remote(file, topdown=topdown):
                        yield res
                    yield 'dir', file, None

    def _walk_local(self, path, topdown=True):
        logger.debug('local walk %s', path)
        for path, dirs, files in os.walk(path, topdown=topdown):
            for file in files:
                file = os.path.join(path, file)
                yield 'file', file, os.stat(file)
            for dir in dirs:
                dir = os.path.join(path, dir)
                yield 'dir', dir, os.stat(dir)

    def _walk(self, *args, **kwargs):
        remote = kwargs.pop('remote', False)
        if remote:
            return self._walk_remote(*args, **kwargs)
        else:
            return self._walk_local(*args, **kwargs)

    def _mkdir_dst(self, path, src_stat=None, remote=True, dry=False):
        if remote:
            try:
                self.sftp.lstat(path)
            except Exception:
                if not dry:
                    self.sftp.mkdir(path)
                logger.debug('created destination directory %s', path)
            if not dry and src_stat:
                self.sftp.chmod(path, src_stat.st_mode)
        else:
            if not os.path.exists(path):
                if not dry:
                    os.mkdir(path)
                logger.debug('created destination directory %s', path)
            if not dry and src_stat:
                os.chmod(path, src_stat.st_mode)

    def _makedirs_dst(self, path, remote=True, dry=False):
        paths = []
        while path not in ('/', ''):
            # break also if path is like C:/
            if len(path) == 3 and path[1:] == ":/":
                break
            paths.insert(0, path)
            path = os.path.dirname(path)

        for path in paths:
            self._mkdir_dst(path, src_stat=None, remote=remote, dry=dry)

    def _validate_src(self, file, include, exclude):
        for re_ in include:
            if not re_.search(file):
                return False
        for re_ in exclude:
            if re_.search(file):
                return False
        return True

    def _validate_dst(self, file, src_stat, remote=True):
        if remote:
            try:
                dst_stat = self.sftp.lstat(file)
            except Exception:
                return
        else:
            if not os.path.exists(file):
                return
            dst_stat = os.stat(file)

        if abs(dst_stat.st_mtime - src_stat.st_mtime) > MTIME_TOLERANCE:
            logger.debug('%s modified time mismatch (source: %s, destination: %s)',
                    file, datetime.utcfromtimestamp(src_stat.st_mtime), datetime.utcfromtimestamp(dst_stat.st_mtime))
            return
        if dst_stat.st_size != src_stat.st_size:
            return
        if dst_stat.st_mode != src_stat.st_mode:
            return
        return True

    def _save(self, src, dst, src_stat, remote=True):
        if remote:
            logger.info('copying %s to %s@%s:%s', src, self.username, self.host, dst)
            self.sftp.put(src, dst, callback=self.callback)
            self.sftp.utime(dst, (int(src_stat.st_atime), int(src_stat.st_mtime)))
            self.sftp.chmod(dst, src_stat.st_mode)
        else:
            logger.info('copying %s@%s:%s to %s', self.username, self.host, src, dst)
            self.sftp.get(src, dst, callback=self.callback)
            os.utime(dst, (int(src_stat.st_atime), int(src_stat.st_mtime)))
            os.chmod(dst, src_stat.st_mode)

    def _delete_dst(self, path, files, remote=True, dry=False):
        if remote:
            callables = {'file': self.sftp.remove, 'dir': self.sftp.rmdir}
        else:
            callables = {'file': os.remove, 'dir': os.rmdir}

        for type, file, stat in self._walk(path, topdown=False, remote=remote):
            if file not in files[type]:
                if not dry:
                    try:
                        callables[type](file)
                    except Exception as e:
                        logger.debug('failed to remove %s: %s', file, str(e))
                        continue

                logger.debug('removed %s', file)

    def _get_filters(self, filters):
        if not filters:
            return []
        return [re.compile(f) for f in filters]

    def sync(self, src, dst, download=True, include=None, exclude=None, delete=False, dry=False, callback=None):
        '''Sync files and directories.

        :param src: source directory
        :param dst: destination directory
        :param download: True to sync from a remote source to a local destination,
            else sync from a local source to a remote destination
        :param include: list of regex patterns the source files must match
        :param exclude: list of regex patterns the source files must not match
        :param delete: remove destination files and directories not present
            at source or filtered by the include/exlude patterns
        :param callback: callback function (form: func(int, int)) that accepts the
            bytes transferred so far and the total bytes to be transferred
        '''

        self.callback = callback
        include = self._get_filters(include)
        exclude = self._get_filters(exclude)

        src = src.replace('\\', '/')
        dst = dst.replace('\\', '/')
        if src.endswith('/') != dst.endswith('/'):
            logger.debug("Paths ends with different symbol. Paths are joined.")
            dst = self._join(dst, os.path.basename(src.rstrip('/')), remote=not download)
        src = src.rstrip('/')
        re_base = re.compile(r'^%s/' % re.escape(src))
        if not src:
            src = '/'

        self._makedirs_dst(dst, remote=not download, dry=dry)

        started = datetime.utcnow()
        total_size = 0
        dst_list = {'file': [], 'dir': []}

        for type, file, stat in self._walk(src, remote=download):
            file_ = re_base.sub('', file)
            file_ = file_.replace('\\', '/')
            if not self._validate_src(file_, include, exclude):
                logger.debug('filtered %s', file)
                continue

            dst_file = self._join(dst, file_, remote=not download, path2_start=src)
            logger.debug("walk      %s", file)
            logger.debug("walk full %s", dst_file)
            dst_list[type].append(dst_file)

            if type == 'dir':
                self._mkdir_dst(dst_file, stat, remote=not download, dry=dry)
            elif type == 'file':
                if not self._validate_dst(dst_file, stat, remote=not download):
                    if not dry:
                        self._save(file, dst_file, stat, remote=not download)
                    total_size += stat.st_size
                    logger.debug('copied %s to %s', file, dst_file)

        if delete:
            self._delete_dst(dst, dst_list, remote=not download, dry=dry)

        logger.debug('transferred %s bytes in %s', total_size, datetime.utcnow() - started)

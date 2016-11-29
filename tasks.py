import errno
import logging
import shutil
from abc import ABC, abstractmethod


class Task(ABC):

    def __init__(self, source, target):
        self.source, self.target = source, target

    @classmethod
    def _recursive_cmp(cls, dir, cmp):
        yield from (dir / x for x in cmp.left_only + cmp.diff_files)
        for k, v in cmp.subdirs.items():
            yield from cls._recursive_cmp(dir / k, v)

    def diff(self):
        cmp = dircmp(str(self.source), str(self.target))
        yield from self._recursive_cmp(Path(), cmp)

    @abstractmethod
    def run(confirm=False):
        pass


class CopyTask(Task):

    def run(self, confirm=False):
        for path in self.diff():
            src, dest = str(self.source / path), str(self.target / path)
            if confirm and input('Copy {} to {}? '.format(src, dest)) not in 'yY':
                continue
            try:
                shutil.copy(src, dest)
            except OSError as e:
                if e.errno == errno.EISDIR:
                    logging.info('{} is a directory'.format(src))
                    shutil.copytree(src, dest)
                else:
                    raise e from None


class RemovalTask(Task):

    def run(self, confirm=False):
        for path in self.diff():
            path = self.source / path
            if confirm and input('Remove {}?'.format(path)) not in 'yY':
                continue
            try:
                path.unlink()
            except OSError as e:
                if e.errno == errno.EISDIR:
                    logging.info('{} is a directory'.format(path))
                    shutil.rmtree(str(path))
                else:
                    raise e from None


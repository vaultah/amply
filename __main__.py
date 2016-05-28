import shutil
import errno
import argparse
from filecmp import dircmp
from pathlib import Path
from json import JSONDecoder
from collections import OrderedDict
from abc import ABC, abstractmethod

decoder = JSONDecoder(object_pairs_hook=OrderedDict)


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
                    shutil.rmtree(str(path))
                else:
                    raise e from None


parser = argparse.ArgumentParser()
parser.add_argument('source')
parser.add_argument('targets', nargs='*')
parser.add_argument('--confirm', '-c', action='store_true')
parser.add_argument('--list', '-l',  action='store_true')
parser.add_argument('--remove-extra', '-r', action='store_true')
args = parser.parse_args()

source = Path(args.source).resolve()
tasks = OrderedDict()

if args.list and (args.confirm or args.remove_extra):
    raise RuntimeError('--list/-l must be sole argument')

# Can be a path to the source directory or
# a path to the configutation file
if not source.is_dir():
    config = decoder.decode(source.read_text())
    for k, v in config.items():
        tasks[k] = [CopyTask(v['source'], Path(t).resolve()) for t in v['targets']]
else:
    tasks[source.stem] = [CopyTask(source, Path(t).resolve()) for t in args.targets]

if args.remove_extra:
    for k, v in tasks.items():
        v.extend([RemovalTask(t.target, t.source) for t in v])

for _, v in tasks.items():
    for task in v:
        if args.list:
            it = task.diff()
            # See if it has any values
            first = next(it, None)
            start = 'Difference between {} and {}'.format(task.source, task.target)
            if first is None:
                print(start, 'is empty')
            else:
                print(start + ':')
            for p in it:
                print('  * {}'.format(p))
        else:
            task.run(args.confirm)
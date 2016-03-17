import shutil
import errno
import argparse
from filecmp import dircmp
from pathlib import Path, PurePath
from json import JSONDecoder
from collections import OrderedDict

decoder = JSONDecoder(object_pairs_hook=OrderedDict)


class Task:

    def __init__(self, source, target):
        self.source, self.target = source, target

    @classmethod
    def _recursive_cmp(cls, dir, cmp):
        yield from (dir / x for x in cmp.left_only + cmp.diff_files)
        for k, v in cmp.subdirs.items():
            yield from cls._recursive_cmp(dir / k, v)

    def diff(self):
        cmp = dircmp(str(self.source), str(self.target))
        yield from self._recursive_cmp(PurePath(), cmp)

    def copy(self, path):
        src, dest = str(self.source / path), str(self.target / path)
        try:
            shutil.copy(src, dest)
        except OSError as e:
            if e.errno == errno.EISDIR:
                shutil.copytree(src, dest)
            else:
                raise e from None

    def copy_all(self):
        for path in self.diff():
            self.copy(path)


parser = argparse.ArgumentParser()
parser.add_argument('source')
parser.add_argument('targets', nargs='*')
parser.add_argument('--confirm', '-c', action='store_true')
parser.add_argument('--list', '-l',  action='store_true')
args = parser.parse_args()

source = Path(args.source).resolve()
tasks = OrderedDict()

if not source.is_dir():
    config = decoder.decode(source.read_text())
    for k, v in config.items():
        tasks[k] = [Task(v['source'], Path(t).resolve()) for t in v['targets']]
else:
    tasks[source.stem] = [Task(source, Path(t).resolve()) for t in args.targets]

for k, v in tasks.items():
    for task in v:
        if args.list:
            diff = list(task.diff())
            lines = '\n'.join(['  * {}'.format(path) for path in diff])
            print('Difference between {} and {}'.format(task.source, task.target),
                  ' is empty.' if not diff else ':\n' + lines, sep='')
        elif args.confirm:
            for path in task.diff():
                src, dest = task.source / path, (task.target / path).parent
                if input('Copy {} to {}? '.format(src, dest)) not in 'yY':
                    continue
                task.copy(path)
        else:
            task.copy_all()
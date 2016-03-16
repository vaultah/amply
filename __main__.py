import shutil
import errno
import argparse
from filecmp import dircmp
from pathlib import Path, PurePath


def to_copy(dir, cmp):
    yield from (dir / x for x in cmp.left_only + cmp.diff_files)
    for k, v in cmp.subdirs.items():
        yield from to_copy(dir / k, v)


parser = argparse.ArgumentParser()
parser.add_argument('source')
parser.add_argument('targets', nargs='+')
parser.add_argument('--confirm', '-c', action='store_true')
parser.add_argument('--list', '-l',  action='store_true')
args = parser.parse_args()

source = Path(args.source).resolve()
targets = [Path(t).resolve() for t in args.targets]


if not source.is_dir():
    # TODO: Load config from file
    pass

for target in targets:
    dc = dircmp(str(source), str(target))
    for file in to_copy(PurePath(), dc):
        if args.list:
            print(file)
            continue

        s, d = source / file, target / file
        if args.confirm:
            if input('Copy {!s} to {!s}? '.format(s, d.parent)) not in 'yY':
                continue

        s, d = str(s), str(d)
        try:
            shutil.copy(s, d)
        except OSError as e:
            if e.errno == errno.EISDIR:
                shutil.copytree(s, d)
            else:
                raise e from None


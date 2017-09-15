import argparse
import errno
import logging
import pkgutil
import shutil
from abc import ABC, abstractmethod
from collections import OrderedDict
from filecmp import dircmp
from itertools import chain
from json import JSONDecoder
from pathlib import Path


class Task(ABC):

    ''' Base class for all tasks '''

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

    def __str__(self):
        return '{}({}, {})'.format(type(self).__name__, self.source, self.target)


class CopyTask(Task):

    def run(self, confirm=False):
        for path in self.diff():
            src, dest = str(self.source / path), str(self.target / path)
            if confirm and input('Copy {} to {} (y)? '.format(src, dest)) not in 'yY':
                continue
            try:
                logging.info('Copying {} to {}'.format(src, dest))
                shutil.copy2(src, dest)
            except IsADirectoryError:
                logging.info('{} is a directory'.format(src))
                shutil.copytree(src, dest)


class RemovalTask(Task):

    def run(self, confirm=False):
        for path in self.diff():
            path = self.source / path
            if confirm and input('Remove {} (y)?'.format(path)) not in 'yY':
                continue
            try:
                logging.info('Removing {}'.format(path))
                path.unlink()
            except IsADirectoryError:
                logging.info('{} is a directory'.format(path))
                shutil.rmtree(str(path))


parser = argparse.ArgumentParser()
parser.add_argument('source', nargs='?',
                    help='a path to either a source directory or a configuration file')
parser.add_argument('targets', nargs='*',
                    help='paths to target directories')
parser.add_argument('--confirm', '-c', action='store_true',
                    help='require confirmation for every action')
parser.add_argument('--list', '-l',  action='store_true',
                    help='print difference between directories and exit')
parser.add_argument('--remove-extra', '-r', action='store_true',
                    help='sync directories by removing extra files in target directories')
parser.add_argument('--log-level', default='warning')
args = parser.parse_args()

if args.list and (args.confirm or args.remove_extra):
    raise RuntimeError('-l/--list must be sole argument')

logging.basicConfig(level=args.log_level.upper())

# Read configuration:
# First, try to parse the command line arguments. If the targets are present,
# treat the first argument as a path to the source directory; otherwise treat it as a
# path to the configuration file.
# If that fails, try to load 'config.json' from the current package
# (ZIP archive, directory) or from the directory containing the script.
if args.source and args.targets:
    logging.info('The first argument is the source directory, the rest are targets')
    config = {'<unknown>': {'source': args.source, 'targets': args.targets}}
else:
    if args.source and not args.targets:
        logging.info('No targets, reading configuration')
        data = Path(args.source).read_bytes()
    elif __spec__ is not None:
        # Load the configuration from the current package
        logging.info('Loading configuration from the current package')
        data = pkgutil.get_data(__name__, 'config.json')
        if data is None:
            raise OSError('The loader does not support get_data')
    else:
        # Load the configuration from the script directory
        file = Path(__file__).resolve().with_name('config.json')
        logging.info('Loading configuration from {}'.format(file))
        data = file.read_bytes()

    # Will keep the order of keys in configuration file
    decoder = JSONDecoder(object_pairs_hook=OrderedDict)
    config = decoder.decode(data.decode())

# Maps task names to lists of instances of Task subclasses
task_groups = OrderedDict()

# Create copy tasks
for name, params in config.items():
    task_groups[name] = []
    source = Path(params['source'])

    if not source.exists():
        logging.error('Task {name!r}: ignoring source {source} (does not exist)'.format(
                        name=name, source=params['source']))
        continue

    for tg in params['targets']:
        target = Path(tg)
        if not target.exists():
            logging.error('Task {name!r}: ignoring target {target} (does not exist)'.format(
                            name=name, target=tg))
            continue

        task_groups[name].append(CopyTask(source, target))

# Create removal tasks
if args.remove_extra:
    for _, tasks in task_groups.items():
        tasks += [RemovalTask(task.target, task.source) for task in tasks]

# Execute tasks
for name, tasks in task_groups.items():
    logging.debug('{}: {} task(s)'.format(name, len(tasks)))
    for task in tasks:
        if args.list:
            logging.debug('Calling {}.diff()'.format(task))
            it = task.diff()
            # See if it has any values
            first = next(it, None)
            start = '(One-sided) Difference between {} and {}'.format(
                                            task.source, task.target)
            if first is None:
                print(start, 'is empty')
            else:
                # Add the first value
                it = chain((first,), it)
                print(start + ':')

            for p in it:
                print('  + {}'.format(p))
        else:
            logging.debug('Calling {}.run(confirm={})'.format(task, args.confirm))
            task.run(args.confirm)

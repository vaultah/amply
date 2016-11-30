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
                shutil.copy(src, dest)
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


# TODO: better help message
parser = argparse.ArgumentParser()
parser.add_argument('source', nargs='?')
parser.add_argument('targets', nargs='*')
parser.add_argument('--confirm', '-c', action='store_true')
parser.add_argument('--list', '-l',  action='store_true')
parser.add_argument('--remove-extra', '-r', action='store_true')
parser.add_argument('--log-level', default='warning')
args = parser.parse_args()

if args.list and (args.confirm or args.remove_extra):
    raise RuntimeError('--list/-l must be sole argument')

logging.basicConfig(level=args.log_level.upper())

# First, try to load 'config.json' from the current ZIP file. If that fails, use
# the command line arguments. If the first argument isn't a directory, assume
# that it points to the configutation file; otherwise treat it as the source
# directory and the rest of positional arguments as target directories

# Maps task names to lists of instances of Task subclasses
tasks = OrderedDict()
data = None

# Create copy tasks
try:
    # TODO: Only works if the __spec__ is set. Fix?
    data = pkgutil.get_data(__name__, 'config.json')
    if data is None:
        raise OSError('The loader does not support get_data')
    logging.info('Loaded configuration from the current package')
except OSError as e:
    logging.debug('pkgutil.get_data raised an exception: {}'.format(e))
    logging.info('Loading configuration from the current package failed')
    source = Path(args.source).resolve()
    if not source.is_dir():
        logging.info('The first argument isn\'t a directory, reading configuration')
        data = source.read_bytes()
    else:
        logging.info('The first argument is the source directory, the rest are targets')
        tasks[source.stem] = [CopyTask(source, Path(t).resolve()) for t in args.targets]
finally:
    if data is not None:
        # Will keep the order of keys in configuration file
        decoder = JSONDecoder(object_pairs_hook=OrderedDict)
        config = decoder.decode(data.decode())
        for k, v in config.items():
            tasks[k] = [CopyTask(v['source'], Path(t).resolve()) for t in v['targets']]

# Create removal tasks
if args.remove_extra:
    for _, v in tasks.items():
        v += [RemovalTask(t.target, t.source) for t in v]

# Execute tasks
for k, v in tasks.items():
    logging.debug('{}: {} tasks'.format(k, len(v)))
    for task in v:
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

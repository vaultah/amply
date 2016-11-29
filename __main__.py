import argparse
import errno
import logging
import pkgutil
from filecmp import dircmp
from pathlib import Path
from json import JSONDecoder
from collections import OrderedDict
from tasks import CopyTask, RemovalTask

decoder = JSONDecoder(object_pairs_hook=OrderedDict)

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

# Create tasks
tasks = OrderedDict()

try:
    data = pkgutil.get_data(__name__, 'config.json')
    if data is None:
        raise OSError('The loader does not support get_data')
except OSError as e:
    logging.debug('pkgutil.get_data raised an exception: {}'.format(e))
    logging.info('Loading configuration from the current package failed')
    source = Path(args.source).resolve()
    if not source.is_dir():
        logging.info('The first argument isn\'t a directory')
        data = source.read_bytes()
    else:
        logging.info('The first argument is the source directory, the rest are targets')
        tasks[source.stem] = [CopyTask(source, Path(t).resolve()) for t in args.targets]
        data = None
finally:
    if data is not None:
        config = decoder.decode(data.decode())
        for k, v in config.items():
            tasks[k] = [CopyTask(v['source'], Path(t).resolve()) for t in v['targets']]

if args.remove_extra:
    for k, v in tasks.items():
        v.extend([RemovalTask(t.target, t.source) for t in v])

# Execute tasks
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

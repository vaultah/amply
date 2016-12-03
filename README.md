# Amply

Simplistic portable cross-platform backup utility written in Python designed to make replication of directories easier.

Basically, given the source directory and list of target directories, it will

 - copy the contents of the source directory to all the target directories, excluding identical files and directories

 - remove the rest of files in target directories to synchronize them with the source directory if the `-r/--remove-extra` argument is provided

If you're only interested in seeing the difference, use `-l/--list`.

## Dependencies

Just Python 3.5 or newer.

## Configuration

You may provide the directories in a configuration file or as command-line arguments.

Note that it's only possible to provide one set of source and target directories as command-line arguments. See the `-h/--help` message for more information.

This utility was designed to be run from a package (hence the `__main__.py` file), like a zip file or a directory. The script will first try to load the configuration from `config.json` in the current package. If that fails, it will use command-line arguments: if the first argument is not a path to a directory, it'll be assumed to be a path to the configuration file; otherwise it'll be treated as a source directory and the rest of positional command-line arguments will be treated as targets.

### Sample configuration file

    {
        "music": {
            "source": "/disk0/music",
            "targets": ["/disk1/music_backup"]
        },
        "images": {
            "source": "/disk0/pics",
            "targets": ["//share/pictures_store",  "/disk1/images_backup"]
        }
    }

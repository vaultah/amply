# Amply

Simplistic pure-Python utility designed to make replication of directories easier.

Basically, given the source directory and list of target directories, it will

 - copy the contents of the source directory to all the target directories, excluding identical files and directories

 - remove the rest of files in target directories to synchronize them with the source directory if the `-r/--remove-extra` argument is provided

If you're only interested in seeing the difference, use `-l/--list`.

## Dependencies

Just Python 3.5 or newer.

## Configuration

You may provide the directories in a configuration file or as command-line arguments.

Note that it's only possible to provide one set of source and target directories as command-line arguments. See the `-h/--help` message for more information.

This utility was designed to be run from a package (hence the *\_\_main\_\_.py* file), like a ZIP file or a directory, but you can also run the file directly. The script will first try to parse the command line arguments. If the targets are present, it will treat the first argument as a path to the source directory; otherwise it will be treated as a path to the configuration file. If that fails, it will try to load *config.json* from the directory/ZIP file containing the script.

This means that a directory/ZIP file having both *\_\_main\_\_.py* and *config.json* files is a self-sufficient [runnable](https://docs.python.org/3/using/cmdline.html?highlight=%3Cscript%3E#using-on-interface-options) package.

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

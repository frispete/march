#! /usr/bin/env python3
"""
Usage: {appname} [-hVv][-m march] prog [args..]
       -h, --help           this message
       -V, --version        print version and exit
       -v, --verbose        verbose mode (cumulative)
       -m, --march=flavour  select a specific march

Description:
Utility program for the execution of machine-optimised alternatives.
The general system setting is done via kernel command line: march={{v2,v3,v4}}
If the parent directory of prog exists with a -march suffix and contains
an executable with the same name, run that instead of prog.

Example:
/usr/bin/prog       # standard program
/usr/bin-v3/prog    # optimised version of program

march -mv3 prog     # would execute /usr/bin-v3/prog

Notes:
The same holds true, if you insert /usr/bin-v3 before /usr/bin in $PATH,
but {appname} does not require any $PATH modification and will work with
executables in non-standard paths as well.

Copyright:
(c)2023 by {author}

License:
{license}
"""
# vim:set et ts=8 sw=4:

__version__ = '0.1'
__author__ = 'Hans-Peter Jansen <hpj@urpla.net>'
__license__ = 'GNU GPL v2 - see http://www.gnu.org/licenses/gpl2.txt for details'
__homepage__ = 'https://github.com/frispete/march'


import os
import sys
import time
import getopt


class gpar:
    """Global parameter class"""
    appdir, appname = os.path.split(sys.argv[0])
    if appdir == '.':
        appdir = os.getcwd()
    if appname.endswith('.py'):
        appname = appname[:-3]
    pid = os.getpid()
    version = __version__
    author = __author__
    license = __license__
    homepage = __homepage__
    march = None
    # internal
    kernel_march = None


stdout = lambda *msg: print(*msg, file = sys.stdout, flush = True)
stderr = lambda *msg: print(*msg, file = sys.stderr, flush = True)


class Log:
    """Minimal logging"""
    CRITICAL = 50
    ERROR = 40
    WARNING = 30
    INFO = 20
    DEBUG = 10
    NOTSET = 0

    _levelToName = {
        CRITICAL: 'CRITICAL',
        ERROR: 'ERROR',
        WARNING: 'WARNING',
        INFO: 'INFO',
        DEBUG: 'DEBUG',
        NOTSET: 'NOTSET',
    }

    def __init__(self, appname, level):
        self._name = appname
        self._level = level
        # internal
        self._datefmt = '%Y-%m-%d %H:%M:%S'

    def getLevel(self):
        return self._level

    def setLevel(self, level):
        oldlevel = 0
        if level and level in Log._levelToName:
            oldlevel = self._level
            self._level = level
        return oldlevel

    def log(self, level, msg):
        if level >= self._level:
            lvl = self._levelToName[level]
            ts = time.strftime(self._datefmt)
            stderr(f'{ts} {lvl}: [{self._name}] {msg}')

    def critical(self, msg):
        self.log(Log.CRITICAL, msg)

    def error(self, msg):
        self.log(Log.ERROR, msg)

    def warning(self, msg):
        self.log(Log.WARNING, msg)

    def info(self, msg):
        self.log(Log.INFO, msg)

    def debug(self, msg):
        self.log(Log.DEBUG, msg)

log = Log(gpar.appname, Log.ERROR)


def exit(ret = 0, msg = None, usage = False):
    """Terminate process with optional message and usage"""
    if msg:
        stderr(f'{gpar.appname}: {msg}')
    if usage:
        stderr(__doc__.format(**gpar.__dict__))
    sys.exit(ret)


# Check that a given file can be accessed with the correct mode.
def _access_check(fn, mode):
    return (os.path.exists(fn) and os.access(fn, mode))


# slightly adjusted and simplified (unixoid) version of shutil.which
def which(cmd, mode=os.F_OK | os.X_OK, path=None):
    """Given a command, mode, and a PATH string, return the path which
    conforms to the given mode on the PATH, or None if there is no such
    file.
    `mode` defaults to os.F_OK | os.X_OK. `path` defaults to the result
    of os.environ.get("PATH"), or can be overridden with a custom search
    path.
    Provide an empty string to disable any auxiliary path processing, or
    ':' to limit the search to the current directory.
    """
    # a path was provided, short circuit processing
    if os.path.dirname(cmd):
        if _access_check(cmd, mode):
            return os.path.abspath(cmd)
        return None

    use_bytes = isinstance(cmd, bytes)

    if path is None:
        path = os.environ.get('PATH', None)
        if path is None:
            try:
                path = os.confstr('CS_PATH')
            except (AttributeError, ValueError):
                # neither os.confstr() nor CS_PATH is available
                path = os.defpath

    if not path:
        return None

    if use_bytes:
        path = os.fsencode(path)
        path = path.split(os.fsencode(os.pathsep))
    else:
        path = os.fsdecode(path)
        path = path.split(os.pathsep)

    seen = set()
    for dir in path:
        normdir = os.path.normcase(dir)
        if not normdir in seen:
            seen.add(normdir)
            name = os.path.join(dir, cmd)
            if _access_check(name, mode):
                return name
    return None


def run(args):
    """execute args via execv from alternative path, if available"""
    log.info(f'[{gpar.pid}]: started: {args}')
    march = gpar.march or gpar.kernel_march
    prog = which(args[0])
    if prog:
        if march:
            # prog was found and march was provided
            pth, exe = os.path.split(prog)
            basepath, toppath = os.path.split(pth)
            marchpath = os.path.join(basepath, toppath + '-' + march)
            marchprog = os.path.join(marchpath, exe)
            if _access_check(marchprog, os.X_OK):
                args[0] = marchprog
        else:
            log.warning(f'neither --march nor march via /proc/cmdline provided: '
                         'will exec {args} verbatim')
        # replace this process with new new one
        try:
            os.execvp(args[0], args)
        except Exception as e:
            log.error(e)
    else:
        prog = args[0]
        errmsg = f'executable "{prog}" not found'
        if not os.path.dirname(prog):
            errmsg += 'in $PATH'
        log.error(errmsg)
    # error condition: executable not found
    return 127


def main(argv = None):
    """Command line interface and console script entry point."""
    if argv is None:
        argv = sys.argv[1:]

    try:
        optlist, args = getopt.getopt(argv, 'hVvm:',
            ('help', 'version', 'verbose', 'march=')
        )
    except getopt.error as msg:
        exit(1, msg, True)

    for opt, par in optlist:
        if opt in ('-h', '--help'):
            exit(usage = True)
        elif opt in ('-V', '--version'):
            exit(msg = 'version %s' % gpar.version)
        elif opt in ('-v', '--verbose'):
            log.setLevel(log.getLevel() - 10)
        elif opt in ('-m', '--march'):
            gpar.march = par

    try:
        cmdline = open('/proc/cmdline').read().split()
    except Exception as e:
        log.error(e)

    for arg in cmdline:
        if arg.startswith('march='):
            gpar.kernel_march = arg[6:]
            break

    try:
        return run(args)
    except KeyboardInterrupt:
        return 3    # SIGQUIT


if __name__ == '__main__':
    sys.exit(main())


#! /usr/bin/env python3
"""
Synopsis:

Usage: (appname) [-hVvs][-l logfile][-m march] prog [args..]
       -h, --help           this message
       -V, --version        print version and exit
       -v, --verbose        verbose mode (cumulative)
       -s, --syslog         log errors to syslog
       -l, --log=logfile    log to this file
       -m, --march=flavour  select a specific march

Description:
Utility program for the execution of machine-optimised alternatives.
The general choice is done via kernel command line: march={v2,v3,v4}
If the parent directory of prog exists with a march suffix, and contains
an executable with the same name, run that instead of prog.

Notes:

Copyright:
(c)2023 by (author)

License:
(license)
"""
#
# vim:set et ts=8 sw=4:
#

__version__ = '0.1'
__author__ = 'Hans-Peter Jansen <hpj@urpla.net>'
__license__ = 'GNU GPL v2 - see http://www.gnu.org/licenses/gpl2.txt for details'


import os
import sys
import getopt
import shutil
import logging
import logging.handlers
import functools


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
    loglevel = logging.WARNING
    logfile = None
    syslog = False
    march = None
    # internal
    kernel_march = None


log = logging.getLogger(gpar.appname)

stdout = lambda *msg: print(*msg, file = sys.stdout, flush = True)
stderr = lambda *msg: print(*msg, file = sys.stderr, flush = True)


def exit(ret = 0, msg = None, usage = False):
    """Terminate process with optional message and usage"""
    if msg:
        stderr(f'{gpar.appname}: {msg}')
    if usage:
        stderr(__doc__.format(**gpar.__dict__))
    sys.exit(ret)


def setup_logging(loglevel, logfile, syslog_errors):
    """Setup various aspects of logging facility"""
    logconfig = dict(
        level = loglevel,
        format = '%(asctime)s %(levelname)5s: [%(name)s] %(message)s',
        datefmt = '%Y-%m-%d %H:%M:%S',
    )
    if logfile not in (None, '-'):
        logconfig['filename'] = logfile
    logging.basicConfig(**logconfig)
    if syslog_errors:
        syslog = logging.handlers.SysLogHandler(address = '/dev/log')
        syslog.setLevel(logging.ERROR)
        formatter = logging.Formatter('%(name)s[%(process)d]: %(levelname)s: %(message)s')
        syslog.setFormatter(formatter)
        logging.getLogger().addHandler(syslog)


def run(args):
    """execute args via execv* replacing this process"""
    ret = 127
    log.info(f'[{gpar.pid}]: started: {args}')

    march = gpar.march or gpar.kernel_march
    prog = args[0]
    if os.access(prog, os.X_OK):
        prog = os.path.abspath(prog)
    else:
        prog = shutil.which(prog)
    if prog:
        if march:
            pth, exe = os.path.split(prog)
            basepath, toppath = os.path.split(pth)
            marchpath = os.path.join(basepath, toppath + '-' + march)
            marchprog = os.path.join(marchpath, exe)
            if os.path.exists(marchprog) and os.access(marchprog, os.X_OK):
                args[0] = marchprog
        else:
            log.warning(f'neither --march nor march via /proc/cmdline provided: will exec {args} verbatim')
        try:
            os.execv(args[0], args)
        except Exception as e:
            log.error(e)
    else:
        log.error(f'cannot determine path of prog: will try to exec {args} verbatim')
        # try to execute verbatim
        try:
            os.execv(args[0], args)
        except Exception as e:
            log.error(e)

    # error condition: executable not found
    return ret


def main(argv = None):
    """Command line interface and console script entry point."""
    if argv is None:
        argv = sys.argv[1:]

    try:
        optlist, args = getopt.getopt(argv, 'hVvl:sm:',
            ('help', 'version', 'verbose', 'logfile=', 'syslog', 'march=')
        )
    except getopt.error as msg:
        exit(1, msg, True)

    for opt, par in optlist:
        if opt in ('-h', '--help'):
            exit(usage = True)
        elif opt in ('-V', '--version'):
            exit(msg = 'version %s' % gpar.version)
        elif opt in ('-v', '--verbose'):
            if gpar.loglevel > logging.DEBUG:
                gpar.loglevel -= 10
        elif opt in ('-l', '--logfile'):
            gpar.logfile = par
        elif opt in ('-s', '--syslog'):
            gpar.syslog = True
        elif opt in ('-m', '--march'):
            gpar.march = par

    setup_logging(gpar.loglevel, gpar.logfile, gpar.syslog)

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


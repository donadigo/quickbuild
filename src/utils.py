import os
from sys import stdout

DEVNULL = open(os.devnull, 'wb')

class Colors:
    BOLD = '\033[1m'
    ENDC = '\033[0m'
    HEADER = '\033[95m'

def log(msg):
    print('{}quickbuild:{} {}'.format(Colors.BOLD, Colors.ENDC, msg))

def log_stdout(msg):
    stdout.write('\r{}quickbuild:{} {}'.format(Colors.BOLD, Colors.ENDC, msg))

def find_program_in_path(program):
    def is_exe(fpath):
        return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

    fpath, _ = os.path.split(program)
    if fpath:
        if is_exe(program):
            return program
    else:
        for path in os.environ["PATH"].split(os.pathsep):
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return exe_file

    return None    
import subprocess
from sys import stdout
import os
import os.path
import utils
import cmakebuild
import buildconfig
import argparse

def build_meson():
    pass

def install_deps(targets):
    install_deps_ubuntu(targets)

def strip_target(target):
    idx = str.find(target, '>')
    if idx != -1:
        return target[0:idx]
    
    idx = str.find(target, '<')
    if idx != -1:
        return target[0:idx]
    
    idx = str.find(target, '=')
    if idx != -1:
        return target[0:idx]
    
    return target

def install_deps_ubuntu(targets):
    deps = set()
    for idx, target in enumerate(targets):
        utils.log_stdout('Detecting dependencies: {}/{}'.format(idx, len(targets) - 1))
        target = strip_target(target)
        if target is None:
            continue

        added = 0

        try:
            out = subprocess.check_output(['apt-file', '-l', 'find', '/usr/include/' + target])
            for dep in str.split(out, '\n'):
                if dep != '':
                    added += 1
                    deps.add(dep)
        except subprocess.CalledProcessError:
            pass
        
        if added == 0:
            try:
                out = subprocess.check_output(['apt-file', '-l', 'find', target])
                for dep in str.split(out, '\n'):
                    if str.startswith(dep, 'lib') and str.endswith(dep, '-dev') and target in dep:
                        added += 1
                        deps.add(dep)
            except subprocess.CalledProcessError:
                pass

        if added == 0:
            guess = 'lib' + target + '-dev'
            rc = subprocess.call(['dpkg', '-l', guess], stdout=utils.DEVNULL, stderr=utils.DEVNULL)
            if rc == 0:
                deps.add(guess)
        
        stdout.flush()
    print
    print(deps)


build_config = buildconfig.BuildConfig()

parser = argparse.ArgumentParser()
parser.add_argument('-c', '--clean', action='store_true',
                    help='Force cleaning the build directory before building')
parser.add_argument('-i', '--install', action='store_true',
                    help='After a successfull build, install the project to the system')
args = parser.parse_args()
build_config.clean = args.clean
build_config.install = args.install

if os.path.isfile('CMakeLists.txt'):
    cb = cmakebuild.CMakeBuild(build_config, os.getcwd())
    if not cb.precheck():
        cb.parse()
        if len(cb.deps) > 0:
            install_deps(cb.deps)
    else:
        cb.build()
    
elif os.path.isfile('meson.build'):
    build_meson()



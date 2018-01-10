import os
import cmakelists_parsing.parsing as cmlp
import utils
import shutil
import subprocess
PKG_CHECK_MODS = 'pkg_check_modules'
SET = 'set'
ADD_SUBDIR = 'add_subdirectory'
CMAKE_BUILTIN_PREFIX = 'CMAKE_'

class CMakeVariable:
    def __repr__(self):
        return 'CMakeVariable({} = \'{}\')\n'.format(self.name, self.vals)

    def __init__(self, name, vals):
        self.name = name
        self.vals = vals

    def get_vals_str(self):
        if len(self.vals) == 1:
            return self.vals[0]

        return ';'.join(self.vals)

class CMakeBuild:
    def __init__(self, build_config, root):
        self.build_config = build_config
        self.root = root
        self.deps = set()
        self.variables = []
        self.unresolved_vars = set()
        self.build_path = None

    def parse_deps(self, deps):
        for arg in deps:
            if not hasattr(arg, 'contents'):
                continue

            c = arg.contents
            var = CMakeVariable(None, [c])
            self.resolve_variable_values(var)

            for dep_id in str.split(var.vals[0], ';'):
                self.deps.add(dep_id)
            

    def get_variable_expr_names(self, expr):
        if str.startswith(expr, '${') and str.endswith(expr, '}'):
            last_idx = len(expr)
            return expr[2:last_idx - 1]
        else:
            return None

    def parse_command(self, cmd, basename):
        if cmd.name == PKG_CHECK_MODS:
            args = cmd.body
            if len(args) < 3:
                return

            if args[0].contents == 'DEPS' and args[1].contents == 'REQUIRED':
                self.parse_deps(args[2:])
        elif cmd.name == SET:
            args = cmd.body
            if len(args) < 2:
                return

            name = args[0].contents
            vals = []
            for arg in args[1:]:        
                vals.append(arg.contents.replace('\'', '').replace('"', ''))

            var = self.get_variable_by_name(name)

            if var == None:
                old = None
            else:
                old = var

            var = CMakeVariable(name, vals)
            self.resolve_variable_values(var)
            self.variables.append(var)
            if old != None:
                self.variables.remove(old)
        elif cmd.name == ADD_SUBDIR:
            args = cmd.body
            if len(args) < 1:
                return

            path = os.path.join(basename, args[0].contents, 'CMakeLists.txt')
            self.parse_file(path)

    def resolve_variable_values(self, var):
        for i, val in enumerate(var.vals):
            expr_name_start = -1
            pos = 0
            v = val

            # Resolve every variable reference ("${VARIABLE}") and replace
            # it with it's content in the value
            # TODO: Parse nested variables
            while True:
                if pos >= len(v):
                    break

                if expr_name_start != -1:
                    if v[pos] == '}':
                        expr_name_stop = pos
                        expr_name = v[expr_name_start:expr_name_stop]
                        if str.startswith(expr_name, CMAKE_BUILTIN_PREFIX):
                            pos += 1
                            continue
                        
                        var_ref = self.get_variable_by_name(expr_name)
                        if var_ref is None:
                            if expr_name not in self.unresolved_vars:
                                utils.log('Could not resolve CMake variable {}'.format(expr_name))
                                self.unresolved_vars.add(expr_name)
                        else:
                            ref_val = var_ref.get_vals_str()
                            left = v[:expr_name_start - 2]
                            right = v[expr_name_stop + 1:]
                            v = left + ref_val + right

                            # Skip at the end of the replaced string so
                            # we parse only the reset of the argument now
                            pos = len(left) + len(ref_val)

                        expr_name_start = -1

                    pos += 1
                elif v[pos:pos + 2] == '${':
                    expr_name_start = pos + 2
                    pos += 2
                else:
                    pos += 1

            var.vals[i] = v

    def get_variable_by_name(self, name):
        for v in self.variables:
            if v.name == name:
                return v
        return None

    def parse_file(self, path):
        os.chdir(self.root)

        try:
            with open(path, 'r') as f:
                fp = cmlp.parse(f.read())

                for cmd in fp:
                    if type(cmd).__name__ == 'Command':
                        self.parse_command(cmd, os.path.dirname(path))
        except IOError:
            utils.log('Could not open file {}'.format(path))

    def precheck(self):
        if utils.find_program_in_path('cmake') is None:
            self.deps.add('cmake')
            return False
        else:
            self.build_path = os.path.join(self.root, 'build')
            if os.path.isdir(self.build_path):
                output_log_path = os.path.join(self.build_path, 'CMakeFiles', 'CMakeOutput.log')
                if not self.build_config.clean and os.path.isfile(output_log_path):
                    with open(output_log_path) as f:
                        contents = f.read()
                        line = str.strip(str.split(contents, '\n')[7])
                        if int(line) == 0:
                            return True

                shutil.rmtree(self.build_path)
            os.mkdir('build')
            os.chdir(self.build_path)
            rc = subprocess.call(['cmake', '..', '-DCMAKE_INSTALL_PREFIX=/usr'], stdout=utils.DEVNULL)
            utils.log('Successfully initialized CMake build folder. Building...')
            return rc == 0


    def parse(self):
        utils.log('Parsing CMake source files...')
        self.parse_file('CMakeLists.txt')
    
    def build(self):
        if self.build_path is None:
            return
        
        os.chdir(self.build_path)
        rc = 0
        if self.build_config.install:
            rc = subprocess.call(['sudo', 'make', 'install'])
        else:
            rc = subprocess.call(['make'])

        if rc != 0:
            utils.log('Build failed with return code {}'.format(rc))            
        
        
            
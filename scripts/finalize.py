
# Important: import panda3d as the very first library - otherwise it crashes
import panda3d.core  # noqa

import sys

from shutil import copyfile
from os.path import isfile, join
from common import is_windows, is_linux, is_macos, fatal_error, get_script_dir


def find_binary():
    """ Returns the path to the generated binary and pdb file """

    source_file = None
    pdb_file = None
    possible_files = []

    abi_version = '{0}{1}'.format(*sys.version_info)
    abi_flags = ''
    if sys.version_info < (3, 8):
        abi_flags += 'm'

    if is_windows():

        # Check the different Configurations
        configurations = ["RelWithDebInfo", "Release"]
        if sys.version_info < (3, 0):
            target_file = MODULE_NAME + '.win_amd64.pyd'
        else:
            target_file = MODULE_NAME + '.cp{0}-win_amd64.pyd'.format(abi_version)

        for config in configurations:
            possible_files.append(join(config, MODULE_NAME + ".dll"))

    elif is_linux():
        if sys.version_info < (3, 0):
            target_file = MODULE_NAME + ".x86_64-linux-gnu.so"
        else:
            target_file = MODULE_NAME + ".cpython-{0}{1}-x86_64-linux-gnu.so".format(abi_version, abi_flags)
        possible_files.append( MODULE_NAME + ".so")

    elif is_macos():
        if sys.version_info < (3, 0):
            target_file = MODULE_NAME + '.darwin.so'.format(abi_version, abi_flags)
        else:
            target_file = MODULE_NAME + '.cpython-{0}{1}-darwin.so'.format(abi_version, abi_flags)
        possible_files.append( MODULE_NAME + ".so")

    else:
        if sys.version_info < (3, 0):
            target_file = MODULE_NAME + '.so'.format(abi_version, abi_flags)
        else:
            target_file = MODULE_NAME + '.cpython-{0}{1}.so'.format(abi_version, abi_flags)
        possible_files.append( MODULE_NAME + ".so")

    for file in possible_files:
        if isfile(file):
            source_file = file

            pdb_name = file.replace(".so", ".pdb").replace(".dll", ".pdb")
            if isfile(pdb_name):
                pdb_file = pdb_name

    target_pdb_file = MODULE_NAME + ".pdb"
    return source_file, pdb_file, target_file, target_pdb_file

if __name__ == "__main__":

    if len(sys.argv) != 2:
        fatal_error("Usage: finalize.py <module-name>")

    MODULE_NAME = sys.argv[1]
    source_file, pdb_file, target_file, target_pdb_file = find_binary()

    if source_file:
        dest_folder = "../../"

        # Copy the generated DLL
        copyfile(source_file, join(dest_folder, target_file))

        # Copy the generated PDB (if it was generated)
        if pdb_file:
            copyfile(pdb_file, join(dest_folder, target_pdb_file))

    else:
        fatal_error("Failed to find generated binary!")

    sys.exit(0)

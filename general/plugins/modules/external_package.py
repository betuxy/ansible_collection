#!/usr/bin/env python3
"""
Ansible module to install packages from a given external repository.
"""
from __future__ import (absolute_import, division, print_function)

from os.path import basename, join as path_join, isfile
from os import stat, chmod
from re import search
from tarfile import open as tar_open, TarError
from zipfile import ZipFile, BadZipfile
from shutil import move, which
from requests import get
from requests.exceptions import ConnectionError as requests_ConnectionError
from ansible.module_utils.basic import AnsibleModule

DOCUMENTATION = r'''
---
module: external_package
short_description: Install packages from an external repository.

version_added: "1.0.0"

description: This module installs packages from a given external repository.

options:
    name:
        description: Name of the package to install.
        required: true
        type: str
    url:
        description: URL of the package to install.
        required: true
        type: str
    destination:
        description: Dowload destination of the package.
        required: false
        type: str
        default: "/tmp"
    timeout:
        description: Timeout in seconds until operation is failed.
        required: false
        type: int
        default: 5
    unpack:
        description: Unpack downloaded archive.
        required: false
        type: bool
        default: False
    copy_binary:
        description: Copy binary from unpacked archive (Only works when unpack is true).
        required: false
        type: bool
        default: False
    binary_dest:
        description: Destination of the binary from a package.
        required: false
        type: str
        default: "/usr/local/bin"
    binary_name:
        description: Name of the binary from a package.
        required: false
        type: str
        default: name
'''

EXAMPLES = r'''
# Download specific syncthing binary from GitHub
- name: Download binary from GitHub
  external_package:
    name: syncthing
    url: https://github.com/syncthing/syncthing/releases/download/v1.27.9/syncthing-macos-amd64-v1.27.9.zip
    unpack: true
    copy_binary: true
'''


def make_executable(filename):
    """
    Make a file executable.
    """
    try:
        # Get current file permissions
        _stat = stat(filename)
        current_permissions = _stat.st_mode

        # Add execute permissions for owner, group, and others
        new_permissions = current_permissions | 0o111

        # Set the new permissions
        chmod(filename, new_permissions)

    except FileNotFoundError as file_not_found_exc:
        raise FileNotFoundError(f"File {filename} not found.") from file_not_found_exc

    except PermissionError as permission_exc:
        raise PermissionError(f'Permission denied: {filename}') from permission_exc

    except OSError as os_error:
        raise os_error from os_error


def get_file_extension(path):
    """
    Returns the extension of a file.
    """
    if not isfile(path):
        raise TypeError(f"{path} is not a file")

    try:
        filename = basename(path)
        file_extension = ""
        grep_res = search(r'\.[a-z.]+$', filename).group()
        is_file_ext = False
        for index, ext in enumerate(grep_res):
            if index + 1 > len(grep_res) - 1:
                file_extension += ext
                break

            next_char = grep_res[index + 1]

            if ext == "." and next_char.isdigit():
                continue

            if ext == "." and next_char.isalpha():
                file_extension += ext
                is_file_ext = True
                continue

            if is_file_ext and next_char.isalpha():
                file_extension += ext
                continue

            file_extension += ext

        return file_extension

    except AttributeError as attribute_error:
        raise AttributeError(f"File {path} has no extension") from attribute_error


class PathNotFileError(Exception):
    """Exception raised when a given path is not a file."""


class PathNotExecutableError(Exception):
    """Exception raised when a given path is not an executable."""


class ExternalPkgConfig:
    """
    External package configuration.
    """
    def __init__(self, config):
        self.package_name = config.get('package_name')
        self.download_url = config.get('download_url')
        self.timeout = config.get('timeout', 5)
        self.destination = config.get('destination', "/tmp")
        self.unpack = config.get('unpack', True)
        self.copy_binary = config.get('copy_binary', True)
        self.binary_dest = config.get('binary_dest', "/usr/local/bin")
        self.binary_name = config.get('binary_name', self.package_name)

    def display_config(self):
        """
        Display the configuration.
        """
        config_str = (
            f"Package Name: {self.package_name}\n"
            f"Download URL: {self.download_url}\n"
            f"Timeout: {self.timeout}\n"
            f"Destination: {self.destination}\n"
            f"Binary Destination: {self.binary_dest}\n"
            f"Binary Name: {self.binary_name}\n"
        )
        print(config_str)

    def get_config_dict(self):
        """
        Return the configuration as a dictionary.
        """
        return {
            'package_name': self.package_name,
            'download_url': self.download_url,
            'timeout': self.timeout,
            'destination': self.destination,
            'unpack': self.unpack,
            'binary_dest': self.binary_dest,
            'binary_name': self.binary_name,
        }


class ExternalPkg:
    """
    External package class.
    """
    def __init__(self, config: ExternalPkgConfig):
        self.config = config
        self.location = None
        self.extracted_path = ""

    @property
    def package_name(self):
        """
        Return the package name.
        """
        return self.config.package_name

    @property
    def download_url(self):
        """
        Return the download url.
        """
        return self.config.download_url

    @property
    def timeout(self):
        """
        Return the timeout.
        """
        return self.config.timeout

    @property
    def destination(self):
        """
        Return the destination.
        """
        return self.config.destination

    @property
    def unpack(self):
        """
        Return if binary should be unpacked.
        """
        return self.config.unpack

    @property
    def copy_binary(self):
        """
        Return if binary should be copied.
        """
        return self.config.copy_binary

    @property
    def binary_dest(self):
        """
        Return the binary destination.
        """
        return self.config.binary_dest

    @property
    def binary_name(self):
        """
        Return the binary name.
        """
        return self.config.binary_name

    def download(self):
        """
        Downloads the package or archive from the download_url.
        """
        try:
            with get(self.download_url, stream=True, timeout=self.timeout) as _pkg:
                _pkg.raise_for_status()
                content_disposition = _pkg.headers['Content-Disposition']
                filename = (
                    content_disposition.split('filename=')[1].strip()
                    if content_disposition and 'filename=' in content_disposition
                    else self.download_url.split("/")[-1].strip()
                )

                destination = path_join(self.destination, filename)
                with open(destination, "wb") as file:
                    chunk_size = (
                        None if content_disposition == 'chunked'
                        else 8192
                    )

                    for chunk in _pkg.iter_content(chunk_size=chunk_size):
                        if content_disposition == 'chunked':
                            if chunk:
                                file.write(chunk)
                        else:
                            file.write(chunk)

            self.location = destination

        except requests_ConnectionError as connection_error:
            raise requests_ConnectionError() from connection_error

    def copy_to_path(self):
        """
        Copies the extracted binary to the binary destination (binary_dest).
        """
        try:
            if self.extracted_path is None:
                raise RuntimeError("Extraction path is not set.")

            if hasattr(self, "binary_name"):
                full_path_src = str(
                    path_join(self.destination, self.extracted_path, self.binary_name)
                )
                full_path_dest = str(path_join(self.binary_dest, self.binary_name))

            else:
                full_path_src = str(
                    path_join(self.destination, self.extracted_path, self.package_name)
                )
                full_path_dest = str(path_join(self.binary_dest, self.package_name))

            move(full_path_src, full_path_dest)
            make_executable(full_path_dest)

        except (FileNotFoundError, NotADirectoryError) as exception:
            try:
                full_path_bin = str(path_join(self.destination, self.extracted_path))
                if isfile(full_path_bin) and which(full_path_bin):
                    move(full_path_bin, str(path_join(self.binary_dest, self.extracted_path)))

                elif isfile(full_path_bin):
                    raise PathNotExecutableError(
                        f"{full_path_bin} is not an executable file."
                    ) from exception

                else:
                    raise PathNotFileError(f"{full_path_bin} is not a file.") from exception

            except OSError as os_error:
                raise os_error

        except OSError as os_error:
            raise os_error

        except RuntimeError as runtime_error:
            raise runtime_error from runtime_error

        except PathNotFileError as path_not_file_error:
            raise path_not_file_error from path_not_file_error

        except PathNotExecutableError as path_not_executable_error:
            raise path_not_executable_error from path_not_executable_error

    def extract_tar(self):
        """
        Extracts tar archives.
        """
        try:
            with tar_open(self.location, mode="r:*") as tar:
                self.extracted_path = min(tar.getnames(), key=len)
                tar.extractall(self.destination, filter='data')

        except TarError as tar_error:
            raise tar_error

    def extract_zip(self):
        """
        Extracts zip archives.
        """
        try:
            with ZipFile(self.location, mode="r") as zip_ref:
                zip_ref.extractall(self.destination)
            self.extracted_path = basename(self.location).replace('.zip', '')

        except BadZipfile as zip_error:
            raise zip_error

    def extract(self, location=None):
        """
        Analyze downloaded file and extract it using one of the
        extract_ methods.
        """
        try:
            file_extension = (
                get_file_extension(location) if location is not None
                else get_file_extension(self.location)
            )

            if "tar" in file_extension:
                self.extract_tar()

            elif "zip" in file_extension:
                self.extract_zip()

        except AttributeError as attr_err:
            raise attr_err from attr_err

        except TypeError as type_err:
            raise type_err from type_err

        except TarError as tar_error:
            raise tar_error from tar_error

        except BadZipfile as bad_zip_error:
            raise bad_zip_error from bad_zip_error

        except OSError as os_error:
            raise os_error from os_error

        except PathNotFileError as path_not_file_error:
            raise path_not_file_error from path_not_file_error

        except PathNotExecutableError as path_not_executable_error:
            raise path_not_executable_error from path_not_executable_error


def run_module():
    """
    Runs the module.
    """
    # define available arguments/parameters a user can pass to the module
    module_args = {
        "name": {"type": 'str', "required": True},
        "url": {"type": 'str', "required": True},
        "destination": {"type": 'str', "required": False, "default": '/tmp'},
        "timeout": {"type": 'int', "required": False, "default": 5},
        "unpack": {"type": 'bool', "required": False, "default": False},
        "copy_binary": {"type": 'bool', "required": False, "default": False},
        "binary_dest": {"type": 'str', "required": False, "default": '/usr/local/bin'},
        "binary_name": {"type": 'str', "required": False, "default": None},
    }

    result = {
        "changed": False,
        "message": ''
    }

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    # If the user is working with this module only in check mode,
    # no changes will be made to the environment.
    if module.check_mode:
        module.exit_json(**result)

    # Initialize ExternalPkgConfig and ExternalPkg classes with the provided module arguments
    try:
        pkg_config = ExternalPkgConfig({
            "package_name": module.params['name'],
            "download_url": module.params['url'],
            "destination": module.params['destination'],
            "timeout": module.params['timeout'],
            "unpack": module.params['unpack'],
            "copy_binary": module.params['copy_binary'],
            "binary_dest": module.params['binary_dest'],
            "binary_name": module.params['binary_name']
            if module.params['binary_name'] is not None else module.params['name'],
        })

        pkg = ExternalPkg(pkg_config)

        try:
            # Download the package
            pkg.download()

        except requests_ConnectionError:
            module.fail_json(msg=f"Failed to download {pkg_config.package_name}.", **result)

        try:
            # Extract and copy to binary destination
            if pkg.unpack:
                pkg.extract()

                try:
                    if pkg.copy_binary:
                        pkg.copy_to_path()

                except (
                    OSError, RuntimeError, PathNotFileError, PathNotExecutableError
                ):
                    module.fail_json(
                        msg=f"Failed to copy {pkg_config.package_name} "
                            f"to {pkg.config.binary_dest}.",
                        **result
                    )

        except (
            AttributeError, TypeError, TarError, BadZipfile,
            OSError, PathNotFileError, PathNotExecutableError
        ):
            module.fail_json(msg=f"Failed to unpack archive {pkg.location}.", **result)

        result['changed'] = True
        result['message'] = 'Package installation successful'

    except Exception as exception:
        module.fail_json(msg=f"Failed to install package: {str(exception)}", **result)

    # in the event of a successful module execution, you will want to
    # simple AnsibleModule.exit_json(), passing the key/value results
    module.exit_json(**result)


def main():
    """
    Entry point for module execution.
    """
    run_module()


if __name__ == '__main__':
    main()

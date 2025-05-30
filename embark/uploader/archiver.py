__copyright__ = 'Copyright 2021-2025 Siemens Energy AG, Copyright 2021 The AMOS Projects'
__author__ = 'Benedikt Kuehne, Maximilian Wagner, m-1-k-3'
__license__ = 'MIT'

import builtins
import gzip
import logging
import os
from pathlib import Path
import re
import shutil
import zipfile

logger = logging.getLogger(__name__)


class Archiver:
    """
       Class unpacker
       This class use shutil function to unpack files
    """

    def __init__(self):
        # default formats: zip, tar, gztar, bztar, xztar

        # register additional formats ( gz )
        shutil.register_unpack_format('gz', ['.gz', ], self.gunzip_file)
        # pass

    @staticmethod
    def gunzip_file(file_name, work_dir):
        """
            special unzip function for .gz files

            :param file_name: file name of the gz file
            :param work_dir: directory where the archive is located

            :return:
        """

        # see warning about filename
        filename = os.path.split(file_name)[-1]
        filename = re.sub(r"\.gz$", "", filename, flags=re.IGNORECASE)

        # extract .gz file
        with gzip.open(file_name, 'rb') as f_in:
            with open(os.path.join(work_dir, filename), 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)

    @staticmethod
    def pack(base_name, archive_format, root_dir, base_dir=None):
        """
            pack function

            :param base_name: name of the file to create, excluding format-specific extension
            :param archive_format: archive format used to pack the directory
            :param root_dir: directory acting as root directory of the archive,
                             all paths in the archive will be relative to it
            :param base_dir: directory archiving is started from, relative to root_dir

            :return: name of archive on success
        """

        # TODO: check location
        return shutil.make_archive(base_name, archive_format, root_dir, base_dir)
        # alternative if single files be zipped:
        # with tarfile

    @staticmethod
    def make_zipfile(output_filename, source_dir):
        relroot = os.path.abspath(os.path.join(source_dir, os.pardir))
        with zipfile.ZipFile(output_filename, "w", zipfile.ZIP_DEFLATED) as zip_:
            for root, _dirs, files in os.walk(source_dir):
                # add directory (needed for empty dirs)
                zip_.write(root, os.path.relpath(root, relroot))
                for file in files:
                    filename = os.path.join(root, file)
                    if os.path.isfile(filename):  # regular files only
                        arcname = os.path.join(os.path.relpath(root, relroot), file)
                        zip_.write(filename, arcname)
        return output_filename

    @staticmethod
    def unpack(file_location, extract_dir=None):
        """
            unpack function
            names non unique, since db takes care of that issue

            :param file_location: file location of the archive
            :param extract_dir: output directory where the archive contents are saved

            :return: True on success, Value error on wrong format, Exception otherwise
        """

        try:
            if extract_dir:
                shutil.unpack_archive(file_location, extract_dir)
            else:
                shutil.unpack_archive(file_location)
            logger.info("Unpacked file successful: %s", file_location)
            return True
        except shutil.ReadError as rerr:
            # logging.error(f"Format {file_location.split('.', 1)[1]} is not supported")
            logging.error("Format %s is not supported", file_location.split('.', 1)[1])
            raise ValueError from rerr
        except builtins.Exception as error:
            logging.error("Undefined Error during unpacking file: %s", file_location)
            logging.error(error)
            raise error

    @staticmethod
    def get_supported_formats():
        """
            lists all supported formats for unpacking

            :return: enumeration of supported formats as list of strings
        """

        return [name for (name, extensions, description) in shutil.get_unpack_formats()]

    @staticmethod
    def get_supported_extensions():
        """
            list all supported extensions for unpacking

            :return: enumeration of supported extensions as list of strings
        """

        extensions_list = [extensions for (name, extensions, description) in shutil.get_unpack_formats()]
        flat_list = [item for sublist in extensions_list for item in sublist]

        return flat_list

    @classmethod
    def check_extensions(cls, file_name):
        """
            checks file for extension integrity

            :param file_name: file to be checked

            :return: True if extension is supported, ValueError otherwise
        """

        for ext in cls.get_supported_extensions():
            if file_name.endswith(ext):
                return True

        logger.info("Format for %s is not supported by archiver", file_name)
        return False

    @classmethod
    def copy(cls, src, dst):
        """
        copy file from src to dst

            :param src: src file to be copied
            :param dst: location to be copied to

            :return: path on success
        """
        logger.debug("copping file %s to %s", src, dst)
        try:
            path = Path(dst)
            path.mkdir(parents=True, exist_ok=False)
            return shutil.copy(src, dst)
        except builtins.Exception as error:
            logger.error("Error copping firmware to active dir: %s", error)
        return None

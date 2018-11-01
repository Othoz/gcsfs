"""A PyFilesystem interface to Google Cloud Storage

See the PyFilesystem documentation here: https://docs.pyfilesystem.org/en/latest/index.html

To e.g. write and read a Pandas DataFrame via this module do:
> import pandas as pd
> df = pd.DataFrame(123)
> fs = open_fs("gs://bucket-name")
> with fs.open("foo.csv", "w") as f:
>     df.to_csv(f)
> with fs.open("foo.csv", "r") as f:
>     assert df == pd.read_csv(f)
"""

import itertools

from typing import Optional

import io
import os
import tempfile

from fs import ResourceType, errors, tools
from fs.base import FS
from fs.info import Info
from fs.mode import Mode
from fs.subfs import SubFS
from fs.path import basename, dirname, forcedir, normpath, relpath, join
from fs.time import datetime_to_epoch

import google
from google.auth.credentials import Credentials
from google.cloud.storage import Client
from google.cloud.storage.blob import Blob

__all__ = ["GCSFS"]

# TODO Type annotations for all functions


class GCSFS(FS):
    """A GCS filesystem for `PyFilesystem <https://pyfilesystem.org>`_

    This implementation is based on `S3FS <https://github.com/PyFilesystem/s3fs>`_

    Args:
        bucket_name: The GCS bucket name.
        root_path: The root directory within the GCS Bucket
        project: Google Cloud Platform project. If not passed, falls back to the default inferred from the locally configured gcloud environment.
        credentials: The OAuth2 Credentials to use for the client. If not passed, falls back to the default inferred from the locally configured gcloud
            environment.
        region: Google Cloud Platform region. If not passed, falls back to the default inferred from the locally configured gcloud environment.
        delimiter: The delimiter to separate folders
        strict: When ``True`` (default) GCSFS will follow the PyFilesystem specification exactly. Set to ``False`` to disable validation of destination paths
            which may speed up uploads / downloads.
    """

    _meta = {  # Used by https://docs.pyfilesystem.org/en/latest/reference/base.html#fs.base.FS.getmeta
        "case_insensitive": False,
        "invalid_path_chars": "\0",
        "network": True,
        "read_only": False,
        "thread_safe": False,
        "unicode_paths": True,
        "virtual": False,
    }

    STANDARD_DELIMITER = "/"

    def __init__(self,
                 bucket_name: str,
                 root_path: str = None,
                 project: str = None,
                 credentials: Credentials = None,
                 region: str = None,
                 delimiter: str = STANDARD_DELIMITER,
                 strict: bool = True):
        self._bucket_name = bucket_name
        if not root_path:
            root_path = self.STANDARD_DELIMITER
        self.root_path = root_path
        self._prefix = relpath(normpath(root_path)).rstrip(delimiter)
        self.project = project
        self.credentials = credentials
        self.region = region
        self.delimiter = delimiter
        self.strict = strict

        self.client = Client(project=self.project, credentials=self.credentials)
        self.bucket = self.client.get_bucket(self._bucket_name)
        super(GCSFS, self).__init__()

    def __repr__(self):
        return _make_repr(
            self.__class__.__name__,
            self._bucket_name,
            root_path=(self.root_path, self.STANDARD_DELIMITER),
            region=(self.region, None),
            delimiter=(self.delimiter, self.STANDARD_DELIMITER)
        )

    def __str__(self):
        return "<gcsfs '{}'>".format(
            join(self._bucket_name, relpath(self.root_path))
        )

    def _path_to_key(self, path):  # Do we need this?
        """Converts an fs path to a GCS key."""
        path = relpath(normpath(path))
        return self.delimiter.join([self._prefix, path]).lstrip("/").replace("/", self.delimiter)

    def _path_to_dir_key(self, path):  # Do we need this?
        """Converts an fs path to a GCS dict key."""
        return forcedir(self._path_to_key(path))

    def _get_blob(self, key) -> Optional[Blob]:
        """Returns blob if exists or None otherwise"""
        key = key.rstrip(self.delimiter)
        return self.bucket.get_blob(key)

    def getinfo(self, path, namespaces=None, check_parent_dir=True):
        if check_parent_dir:
            self.check()
        namespaces = namespaces or ()

        _path = self.validatepath(path)
        key = self._path_to_key(_path)

        if check_parent_dir:
            dir_path = dirname(_path)
            if dir_path != "/" and not self._check_and_fix_dir(dir_path):
                raise errors.ResourceNotFound(path)

        if _path == "/":
            return self._dir_info("")

        obj = self.bucket.get_blob(key)

        if not obj:
            if self._check_and_fix_dir(_path):
                return self._dir_info(path)
            else:
                raise errors.ResourceNotFound(path)
        return self._info_from_object(obj, namespaces)

    def _check_and_fix_dir(self, path: str):
        """Checks if a path points to a GCS "directory" and makes sure the directory is marked according to fs-gcsfs standards.

        As GCS is no real file system there is also no concept of folders. S3FS and GCSFS overcome this by adding empty files with the name "<path>/" every
        time a directory is created, see https://fs-s3fs.readthedocs.io/en/latest/#limitations

        This may lead to problems when working on data which was not created via GCSFS. This function tries to make the filesystem more robust by automatically
        adding the missing file in case a directory is detected.
        """
        dir_key = self._path_to_dir_key(path)
        if not self.bucket.get_blob(dir_key):
            if next(self.bucket.list_blobs(prefix=dir_key).pages).num_items > 0:
                # Apparently there are blobs under "path" but it is not yet marked as a directory
                blob = self.bucket.blob(dir_key)
                blob.upload_from_string(b"")
                return True
            else:
                return False
        else:
            return True

    def _info_from_object(self, obj, namespaces) -> Info:  # TODO
        """Make an info dict from a GCS object."""
        path = obj.name
        name = basename(path.rstrip("/"))
        is_dir = path.endswith(self.delimiter)
        info = {
            "basic": {
                "name": name,
                "is_dir": is_dir
            }
        }
        if "details" in namespaces:
            if is_dir:
                _type = int(ResourceType.directory)
            else:
                _type = int(ResourceType.file)

            info["details"] = {
                "accessed": None,
                "modified": datetime_to_epoch(obj.updated),
                "size": obj.size,
                "type": _type
            }
        # TODO missing namespaces: urls, gcs
        return Info(info)

    def _dir_info(self, name: str) -> Info:
        return Info({
            "basic": {
                "name": name.rstrip(self.delimiter),
                "is_dir": True
            },
            "details": {
                "type": int(ResourceType.directory)
            }
        })

    def _scandir(self, path, return_info=False, namespaces=None):
        namespaces = namespaces or ()
        _path = self.validatepath(path)

        if namespaces and not return_info:
            raise ValueError("The provided namespaces are only considered if info=True")

        info = self.getinfo(_path)
        if not info.is_dir:
            raise errors.DirectoryExpected(_path)

        dir_key = self._path_to_dir_key(_path)

        if dir_key == "/":
            # In case we want to list the root directory, no prefix is necessary
            prefix = ""
        else:
            prefix = dir_key
        prefix_len = len(prefix)

        # Build set of root level directories
        page_iterator = self.bucket.list_blobs(prefix=prefix, delimiter="/")
        prefixes = set()
        for page in page_iterator.pages:
            prefixes.update(page.prefixes)

        # Loop over all root level directories
        for prefix in prefixes:
            _name = prefix[prefix_len:]
            if return_info:
                yield self._dir_info(_name)
            else:
                yield _name.rstrip(self.delimiter)

        # Loop over all root level blobs
        item_iterator = self.bucket.list_blobs(prefix=dir_key, delimiter="/")
        for blob in list(item_iterator):
            if blob.name == dir_key:  # Don't return root directory
                continue
            if return_info:
                yield self._info_from_object(blob, namespaces=namespaces)
            else:
                yield blob.name[prefix_len:]

    def listdir(self, path):
        result = list(self._scandir(path))
        if not result:
            if not self.getinfo(path).is_dir:
                raise errors.DirectoryExpected(path)
        return result

    def scandir(self, path, namespaces=None, page=None):
        iter_info = self._scandir(path, return_info=True, namespaces=namespaces)
        if page is not None:
            start, end = page
            iter_info = itertools.islice(iter_info, start, end)
        return iter_info

    def makedir(self, path, permissions=None, recreate=False):
        """Make a directory.

        Note:
            As GCS is not a real filesystem but a key-value store that does not have any concept of directories, we write empty blobs as a work around.
            See: https://fs-s3fs.readthedocs.io/en/latest/#limitations

            This implementation currently ignores the `permissions` argument, the empty blobs are written with default permissions.
        """
        self.check()
        _path = self.validatepath(path)
        _key = self._path_to_dir_key(_path)

        if not self.isdir(dirname(_path)):
            raise errors.ResourceNotFound(path)

        try:
            self.getinfo(path)
        except errors.ResourceNotFound:
            pass
        else:
            if recreate:
                return self.opendir(_path)
            else:
                raise errors.DirectoryExists(path)

        blob = self.bucket.blob(_key)
        blob.upload_from_string(b"")

        return SubFS(self, path)

    def makedirs(self, path, permissions=None, recreate=False) -> SubFS[FS]:
        """Make a directory, and any missing intermediate directories.

        Note:
            We overwrite the default FS implementation to make it idempotent.

            `tools.get_intermediate_dirs()` returns all non-existing directories in the path. If one of those directories was created by another process or
            service before `self.makedir()` was called, `self.makedir()` will raise a `DirectoryExists` exception in the default implementation.

            To overcome this we call `self.makedir()` with `recreate=True` for every intermediate directory.
        """
        self.check()
        dir_paths = tools.get_intermediate_dirs(self, path)
        for dir_path in dir_paths:
            self.makedir(dir_path, permissions=permissions, recreate=True)

        try:
            self.makedir(path)
        except errors.DirectoryExists:
            if not recreate:
                raise
        return self.opendir(path)

    def openbin(self, path, mode="r", buffering=-1, **options):
        _mode = Mode(mode)
        _mode.validate_bin()
        self.check()
        _path = self.validatepath(path)
        _key = self._path_to_key(_path)

        def on_close(gcs_file):
            if _mode.create or _mode.writing:
                gcs_file.raw.seek(0)
                blob = self._get_blob(_key)
                if not blob:
                    blob = self.bucket.blob(_key)
                blob.upload_from_file(gcs_file.raw)
            gcs_file.raw.close()

        if _mode.create:
            dir_path = dirname(_path)
            if dir_path != "/":
                _dir_key = self._path_to_dir_key(dir_path)
                if not self.bucket.get_blob(_dir_key):
                    raise errors.ResourceNotFound(path)

            try:
                info = self.getinfo(path)
            except errors.ResourceNotFound:
                pass
            else:
                if _mode.exclusive:
                    raise errors.FileExists(path)
                if info.is_dir:
                    raise errors.FileExpected(path)

            gcs_file = GCSFile.factory(path, _mode, on_close=on_close)

            if _mode.appending:
                blob = self._get_blob(_key)
                if blob:  # in case there is an existing blob in GCS, we download it and seek until the end of the stream
                    gcs_file.seek(0, os.SEEK_END)
                    blob.download_to_file(gcs_file.raw)

            return gcs_file

        if self.strict:
            info = self.getinfo(path)
            if info.is_dir:
                raise errors.FileExpected(path)

        gcs_file = GCSFile.factory(path, _mode, on_close=on_close)
        blob = self._get_blob(_key)
        if not blob:
            raise errors.ResourceNotFound

        blob.download_to_file(gcs_file.raw)
        gcs_file.seek(0)
        return gcs_file

    def remove(self, path):
        self.check()
        _path = self.validatepath(path)
        _key = self._path_to_key(_path)
        if self.strict:
            info = self.getinfo(path)
            if info.is_dir:
                raise errors.FileExpected(path)
        try:
            self.bucket.delete_blob(_key)
        except google.cloud.exceptions.NotFound:
            raise errors.ResourceNotFound(path)

    def removedir(self, path):
        self.check()
        _path = self.validatepath(path)
        if _path == "/":
            raise errors.RemoveRootError()
        info = self.getinfo(_path)
        if not info.is_dir:
            raise errors.DirectoryExpected(path)
        if not self.isempty(path):
            raise errors.DirectoryNotEmpty(path)
        _key = self._path_to_dir_key(_path)

        try:
            self.bucket.delete_blob(_key)
        except google.cloud.exceptions.NotFound:
            raise errors.ResourceNotFound(path)

    def setinfo(self, path, info):  # TODO Copied from S3FS but I don't get it
        self.getinfo(path)

    def copy(self, src_path, dst_path, overwrite=False):
        if not overwrite and self.exists(dst_path):
            raise errors.DestinationExists(dst_path)
        _src_path = self.validatepath(src_path)
        _dst_path = self.validatepath(dst_path)
        if self.strict:
            if not self.isdir(dirname(_dst_path)):
                raise errors.ResourceNotFound(dst_path)
        _src_key = self._path_to_key(_src_path)
        _dst_key = self._path_to_key(_dst_path)

        blob = self.bucket.get_blob(_src_key)
        if not blob:
            if self.exists(src_path):
                raise errors.FileExpected(src_path)
            raise errors.ResourceNotFound(_src_key)
        self.bucket.copy_blob(blob, self.bucket, new_name=_dst_key)

    def move(self, src_path, dst_path, overwrite=False):
        self.copy(src_path, dst_path, overwrite=overwrite)
        self.remove(src_path)

    def exists(self, path):
        self.check()
        _path = self.validatepath(path)
        if _path == "/":
            return True

        blob = self.bucket.get_blob(self._path_to_key(path))
        if blob:
            return True
        else:
            return self.isdir(path)

    def geturl(self, path, purpose="download"):  # See https://fs-s3fs.readthedocs.io/en/latest/index.html#urls
        _path = self.validatepath(path)
        _key = self._path_to_key(_path)
        if purpose == "download":
            return "gs://" + self.delimiter.join([self._bucket_name, _key])
        else:
            raise errors.NoURL(path, purpose)

    def isdir(self, path):
        _path = self.validatepath(path)
        try:
            return self.getinfo(_path, check_parent_dir=False).is_dir
        except errors.ResourceNotFound:
            return False

    def opendir(self, path, factory=None) -> SubFS[FS]:
        # Implemented to support skipping the directory check if strict=False
        _factory = factory or SubFS

        if self.strict and not self.getbasic(path).is_dir:
            raise errors.DirectoryExpected(path=path)

        return _factory(self, path)

    # ----- Functions which are implemented in S3FS but not in GCSFS (potential performance improvements) -----
    # def isempty(self, path):
    # def getbytes(self, path):
    # def getfile(self, path, file, chunk_size=None, **options):
    # def setbytes(self, path, contents):
    # def setbinfile(self, path, file):


class GCSFile(io.IOBase):  # Identical to s3file
    """Proxy for a GCS file.

    Note:
        Instead of performing all operations directly on the cloud (which is in some cases not even possible) everything is “buffered“ in a local file and only
        written on close.
    """

    @classmethod
    def factory(cls, filename, mode, on_close):
        """Create a GCSFile backed with a temporary file."""
        _temp_file = tempfile.TemporaryFile()
        proxy = cls(_temp_file, filename, mode, on_close=on_close)
        return proxy

    def __repr__(self):
        return _make_repr(
            self.__class__.__name__,
            self.__filename,
            self.__mode
        )

    def __init__(self, f, filename, mode, on_close=None):
        self._f = f
        self.__filename = filename
        self.__mode = mode
        self._on_close = on_close

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    @property
    def raw(self):
        return self._f

    def close(self):
        if self._on_close is not None:
            self._on_close(self)

    @property
    def closed(self):
        return self._f.closed

    def fileno(self):
        return self._f.fileno()

    def flush(self):
        return self._f.flush()

    def isatty(self):
        return self._f.asatty()

    def readable(self):
        return self.__mode.reading

    def readline(self, limit=-1):
        return self._f.readline(limit)

    def readlines(self, hint=-1):
        if hint == -1:
            return self._f.readlines(hint)
        else:
            size = 0
            lines = []
            for line in iter(self._f.readline, b""):
                lines.append(line)
                size += len(line)
                if size > hint:
                    break
            return lines

    def seek(self, offset, whence=os.SEEK_SET):
        if whence not in (os.SEEK_CUR, os.SEEK_END, os.SEEK_SET):
            raise ValueError("invalid value for 'whence'")
        self._f.seek(offset, whence)
        return self._f.tell()

    def seekable(self):
        return True

    def tell(self):
        return self._f.tell()

    def writable(self):
        return self.__mode.writing

    def writelines(self, lines):
        return self._f.writelines(lines)

    def read(self, n=-1):
        if not self.__mode.reading:
            raise IOError("not open for reading")
        return self._f.read(n)

    def readall(self):
        return self._f.readall()

    def readinto(self, b):
        return self._f.readinto()

    def write(self, b):
        if not self.__mode.writing:
            raise IOError("not open for reading")
        self._f.write(b)
        return len(b)

    def truncate(self, size=None):
        if size is None:
            size = self._f.tell()
        self._f.truncate(size)
        return size


def _make_repr(class_name, *args, **kwargs):  # Identical to S3FS implementation
    """
    Generate a repr string.

    Positional arguments should be the positional arguments used to
    construct the class. Keyword arguments should consist of tuples of
    the attribute value and default. If the value is the default, then
    it won't be rendered in the output.

    Here's an example::

        def __repr__(self):
            return make_repr('MyClass', 'foo', name=(self.name, None))

    The output of this would be something line ``MyClass('foo',
    name='Will')``.

    """
    arguments = [repr(arg) for arg in args]
    arguments.extend(
        "{}={!r}".format(name, value)
        for name, (value, default) in sorted(kwargs.items())
        if value != default
    )
    return "{}({})".format(class_name, ", ".join(arguments))

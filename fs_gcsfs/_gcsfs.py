"""A PyFilesystem interface to Google Cloud Storage"""

import io
import itertools
import logging
import os
import tempfile
import mimetypes
from typing import Optional, List, Union, Tuple, Iterator, MutableMapping, Any

import google
from fs import ResourceType, errors, tools
from fs.base import FS
from fs.info import Info
from fs.mode import Mode
from fs.path import basename, dirname, forcedir, normpath, relpath, join
from fs.permissions import Permissions
from fs.subfs import SubFS
from fs.time import datetime_to_epoch
from google.cloud.storage import Client
from google.cloud.storage.blob import Blob
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


__all__ = ["GCSFS"]

logger = logging.getLogger()


class GCSFS(FS):
    """A Google Cloud Storage filesystem for `PyFilesystem <https://pyfilesystem.org>`_.

    This implementation is based on `S3FS <https://github.com/PyFilesystem/s3fs>`_.

    Args:
        bucket_name: The GCS bucket name.
        root_path: The root directory within the GCS Bucket.
        create: Whether to create ``root_path`` on initialization or not. If ``root_path`` does not yet exist and ``create=False`` a ``CreateFailed``
            exception will be raised. To disable ``root_path`` validation entirely set ``strict=False``.
        client: A :class:`google.storage.Client` exposing the google storage API.
        strict: When ``True`` (default) GCSFS will follow the PyFilesystem specification exactly. Set to ``False`` to disable validation of destination paths
            which may speed up some operations.
    """

    _meta = {
        "case_insensitive": False,
        "invalid_path_chars": "\0",
        "network": True,
        "read_only": False,
        "thread_safe": False,
        "unicode_paths": True,
        "virtual": False,
    }

    DELIMITER = "/"

    def __init__(self,
                 bucket_name: str,
                 root_path: str = None,
                 create: bool = False,
                 client: Client = None,
                 retry: int = 5,
                 strict: bool = True):
        super().__init__()
        self._bucket_name = bucket_name
        if not root_path:
            root_path = ""
        self.root_path = root_path
        self._prefix = relpath(normpath(root_path)).rstrip(self.DELIMITER)

        self.strict = strict

        self.client = client
        if self.client is None:
            self.client = Client()
            if retry:
                adapter = HTTPAdapter(max_retries=Retry(total=retry,
                                                        status_forcelist=[429, 502, 503, 504],
                                                        method_whitelist=False,  # retry on any HTTP method
                                                        backoff_factor=0.5))
                self.client._http.mount("https://", adapter)

        self.bucket = self.client.bucket(self._bucket_name)

        if self._prefix != "":
            if create:
                root_marker = self._get_blob(self._prefix + GCSFS.DELIMITER)
                if root_marker is None:
                    blob = self.bucket.blob(self._prefix + GCSFS.DELIMITER)
                    blob.upload_from_string(b"")
            elif strict and self._get_blob(self._prefix + GCSFS.DELIMITER) is None:
                raise errors.CreateFailed("Root path \"{}\" does not exist".format(root_path))

    def __repr__(self) -> str:
        return _make_repr(
            self.__class__.__name__,
            self._bucket_name,
            root_path=(self.root_path, self.DELIMITER)
        )

    def __str__(self) -> str:
        return "<gcsfs '{}'>".format(
            join(self._bucket_name, relpath(self.root_path))
        )

    def _path_to_key(self, path: str) -> str:
        """Converts an fs path to a GCS key."""
        _path = relpath(normpath(path))
        return self.DELIMITER.join([self._prefix, _path]).lstrip(self.DELIMITER).rstrip(self.DELIMITER)

    def _path_to_dir_key(self, path: str) -> str:
        """Converts an fs path to a GCS dict key."""
        return self._path_to_key(path) + GCSFS.DELIMITER

    def _get_blob(self, key: str) -> Optional[Blob]:
        """Returns blob if exists or None otherwise"""
        return self.bucket.get_blob(key)

    def getinfo(self, path: str, namespaces: Optional[List[str]] = None, check_parent_dir: bool = True) -> Info:
        if check_parent_dir:
            self.check()
        namespaces = namespaces or ()

        _path = self.validatepath(path)

        if check_parent_dir:
            parent_dir = dirname(_path)
            parent_dir_key = self._path_to_dir_key(parent_dir)
            if parent_dir != "/" and not self._get_blob(parent_dir_key):
                raise errors.ResourceNotFound(path)

        if _path == "/":
            return self._dir_info("")

        key = self._path_to_key(_path)
        dir_key = self._path_to_dir_key(_path)

        blob = self._get_blob(key)
        if blob:
            # Check if there exists a blob at the provided path, return the corresponding object Info
            return self._info_from_blob(blob, namespaces)
        elif self._get_blob(dir_key):
            # Check if there exists a blob with a slash at the end, return the corresponding directory Info
            return self._dir_info(path)
        else:
            raise errors.ResourceNotFound(path)

    @staticmethod
    def _info_from_blob(blob: Blob, namespaces: Optional[List[str]] = None) -> Info:
        """Make an info dict from a GCS object."""
        path = blob.name
        name = basename(path.rstrip("/"))
        info = {
            "basic": {
                "name": name,
                "is_dir": False
            }
        }

        if "details" in namespaces:
            info["details"] = {
                "accessed": None,
                "modified": datetime_to_epoch(blob.updated),
                "size": blob.size,
                "type": int(ResourceType.file)
            }
        # TODO more namespaces: basic, urls, gcs, ...

        return Info(info)

    def _dir_info(self, name: str) -> Info:
        return Info({
            "basic": {
                "name": name.rstrip(self.DELIMITER),
                "is_dir": True
            },
            "details": {
                "type": int(ResourceType.directory)
            }
        })

    def _scandir(self, path: str, return_info: bool = False, namespaces: List[str] = None) -> Union[Iterator[str], Iterator[Info]]:
        """Returns all the resources in a directory

        Args:
            path: Path to the directory on the filesystem which shall be scanned
            return_info: If `True` instances of the type fs.info.Info are being returned. If `False` only the names of the resources are being returned.
            namespaces: A list of namespaces to include in the resource information. Only considered if `return_info=True`.

        Returns:
            Either an iterator of Info instances for each resource in the directory or an iterator of string names for each resource in the directory
        """
        namespaces = namespaces or ()
        _path = self.validatepath(path)

        if namespaces and not return_info:
            raise ValueError("The provided namespaces are only considered if return_info=True")

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
        page_iterator = self.bucket.list_blobs(prefix=prefix, delimiter=self.DELIMITER)
        dir_prefixes = set()
        for page in page_iterator.pages:
            dir_prefixes.update(page.prefixes)

        # Loop over all root level directories
        for dir_prefix in dir_prefixes:
            _name = dir_prefix[prefix_len:]
            if return_info:
                yield self._dir_info(_name)
            else:
                yield _name.rstrip(self.DELIMITER)

        # Loop over all root level blobs
        item_iterator = self.bucket.list_blobs(prefix=prefix, delimiter=self.DELIMITER)
        for blob in list(item_iterator):
            if blob.name == dir_key:  # Don't return root directory
                continue
            if return_info:
                yield self._info_from_blob(blob, namespaces=namespaces)
            else:
                yield blob.name[prefix_len:]

    def listdir(self, path: str) -> List[str]:
        result = list(self._scandir(path))
        if not result:
            if not self.getinfo(path).is_dir:
                raise errors.DirectoryExpected(path)
        return result

    def scandir(self, path: str, namespaces: Optional[List[str]] = None, page: Optional[Tuple[int, int]] = None) -> Iterator[Info]:
        iter_info = self._scandir(path, return_info=True, namespaces=namespaces)
        if page is not None:
            start, end = page
            iter_info = itertools.islice(iter_info, start, end)
        return iter_info

    def makedir(self, path: str, permissions: Optional[Permissions] = None, recreate: bool = False) -> SubFS[FS]:
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

    def makedirs(self, path: str, permissions: Optional[Permissions] = None, recreate: bool = False) -> SubFS[FS]:
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

    def openbin(self, path: str, mode: str = "r", buffering: int = -1, **options) -> "GCSFile":
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
                mime_type, encoding = mimetypes.guess_type(path)
                if encoding is not None:
                    mime_type = None
                blob.upload_from_file(gcs_file.raw, content_type=mime_type)
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
            raise errors.ResourceNotFound(path)

        blob.download_to_file(gcs_file.raw)
        gcs_file.seek(0)
        return gcs_file

    def remove(self, path: str) -> None:
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

    def removedir(self, path: str) -> None:
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

    def setinfo(self, path, info):
        self.getinfo(path)

    def copy(self, src_path: str, dst_path: str, overwrite: bool = False) -> None:
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

    def move(self, src_path: str, dst_path: str, overwrite: bool = False) -> None:
        self.copy(src_path, dst_path, overwrite=overwrite)
        self.remove(src_path)

    def exists(self, path: str) -> bool:
        self.check()
        _path = self.validatepath(path)
        if _path == "/":
            return True

        blob = self.bucket.get_blob(self._path_to_key(path))
        if blob:
            return True
        else:
            return self.isdir(path)

    def geturl(self, path: str, purpose: str = "download"):
        # TODO This does currently not have the same functionality as S3FS.geturl() (returning a public URL) which may be confusing to users
        _path = self.validatepath(path)
        _key = self._path_to_key(_path)
        if purpose == "download":
            return "gs://" + self.DELIMITER.join([self._bucket_name, _key])
        else:
            raise errors.NoURL(path, purpose)

    def isdir(self, path: str) -> bool:
        _path = self.validatepath(path)
        try:
            return self.getinfo(_path, check_parent_dir=False).is_dir
        except errors.ResourceNotFound:
            return False

    def opendir(self, path: str, factory=None) -> SubFS[FS]:
        # Implemented to support skipping the directory check if strict=False
        _factory = factory or SubFS

        if self.strict and not self.getbasic(path).is_dir:
            raise errors.DirectoryExpected(path=path)

        return _factory(self, path)

    def get_mapper(self) -> "GCSMap":
        """Returns a ``MutableMapping`` that represents the filesystem.

        The keys of the mapping become files and the values (which must be bytes) the contents of those files.
        This is particularly useful to be used with libraries such as `xarray <http://xarray.pydata.org/>`_ or `zarr <https://zarr.readthedocs.io/>`_.
        """
        return GCSMap(self)

    def fix_storage(self) -> None:  # TODO test
        """Utility function that walks the entire `root_path` and makes sure that all intermediate directories are correctly marked with empty blobs.

        As GCS is no real file system but only a key-value store, there is also no concept of folders. S3FS and GCSFS overcome this limitation by adding
        empty files with the name "<path>/" every time a directory is created, see https://fs-gcsfs.readthedocs.io/en/latest/#limitations.
        """
        names = [blob.name for blob in self.bucket.list_blobs(prefix=self.root_path)]
        marked_dirs = set()
        all_dirs = set()

        for name in names:
            # If a blob ends with a slash, it's a directory marker
            if name.endswith("/"):
                marked_dirs.add(dirname(name))

            name = dirname(name)
            while name != self.root_path:
                all_dirs.add(name)
                name = dirname(name)

        if forcedir(self.root_path) != "/":
            all_dirs.add(self.root_path)

        unmarked_dirs = all_dirs.difference(marked_dirs)
        logger.info("{} directories in total".format(len(all_dirs)))

        if len(unmarked_dirs) > 0:
            logger.info("{} directories are not yet marked correctly".format(len(unmarked_dirs)))
            for unmarked_dir in unmarked_dirs:
                dir_name = forcedir(unmarked_dir)
                logger.debug("Creating directory marker " + dir_name)
                blob = self.bucket.blob(dir_name)
                blob.upload_from_string(b"")
            logger.info("Successfully created {} directory markers".format(len(unmarked_dirs)))
        else:
            logger.info("All directories are correctly marked")

    # ----- Functions which are implemented in S3FS but not in GCSFS (potential performance improvements) -----
    # def isempty(self, path):
    # def getbytes(self, path):
    # def getfile(self, path, file, chunk_size=None, **options):
    # def setbytes(self, path, contents):
    # def setbinfile(self, path, file):


class GCSFile(io.IOBase):
    """Proxy for a GCS blob.

    Identical to S3File from https://github.com/PyFilesystem/s3fs.

    Note:
        Instead of performing all operations directly on the cloud (which is in some cases not even possible)
        everything is “buffered“ in a local file and only written on close.
    """

    def __init__(self, f, filename, mode, on_close=None):
        self._f = f
        self.__filename = filename
        self.__mode = mode
        self._on_close = on_close

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
            raise IOError("not open for writing")
        self._f.write(b)
        return len(b)

    def truncate(self, size=None):
        if size is None:
            size = self._f.tell()
        self._f.truncate(size)
        return size


class GCSMap(MutableMapping):
    """Wraps a ``class:GCSFS`` as a ``MutableMapping``.

    The keys of the mapping become files and the values (which must be bytes) the contents of those files.
    This is particularly useful to be used with libraries such as `xarray <http://xarray.pydata.org/>`_ or `zarr <https://zarr.readthedocs.io/>`_.

    Args:
        gcsfs: The ``class:GCSFS`` to wrap.
    """

    def __init__(self, gcsfs: GCSFS):
        self.gcsfs = gcsfs

    def __getitem__(self, key: Any) -> bytes:
        try:
            return self.gcsfs.getbytes(str(key))
        except errors.ResourceNotFound:
            raise KeyError(key)

    def __setitem__(self, key: Any, value: Any) -> None:
        self.gcsfs.makedirs(dirname(str(key)), recreate=True)
        self.gcsfs.setbytes(str(key), bytes(value))

    def __delitem__(self, key) -> None:
        self.gcsfs.remove(str(key))

    def __iter__(self) -> Iterator[str]:
        return self.keys()

    def __len__(self) -> int:
        return sum(1 for _ in self.keys())

    def __contains__(self, key: Any) -> bool:
        return self.gcsfs.exists(str(key))

    def keys(self) -> Iterator[str]:
        for path, dirs, files in self.gcsfs.walk("."):
            for file in files:
                if file.name != "/":  # Skip directory markers
                    yield file.name  # join(path, file.name)


def _make_repr(class_name, *args, **kwargs):
    """Generate a repr string. Identical to S3FS implementation

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
    arguments.extend("{}={!r}".format(name, value) for name, (value, default) in sorted(kwargs.items()) if value != default)
    return "{}({})".format(class_name, ", ".join(arguments))

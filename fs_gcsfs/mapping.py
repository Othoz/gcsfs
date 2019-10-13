# coding: utf-8
# borrowed and adapted from S3FS:
# https://s3fs.readthedocs.io/en/latest/_modules/s3fs/mapping.html#S3Map
from collections.abc import MutableMapping
from ._gcsfs import GCSFS

def split_path(path):
    """
    Normalise GCSFS path string into bucket and key.
    """
    if path.startswith('gs://'):
        path = path[5:]
    path = path.rstrip('/').lstrip('/')
    if '/' not in path:
        return path, ""
    else:
        return path.split('/', 1)

class GCSFSMap(MutableMapping):
    """Wrap a Google Cloud filesystem (GCSFS) as a mutable wrapping.

    The keys of the mapping become files under the given root, and the
    values (which must be bytes) the contents of those files.

    Parameters
    ----------
    root : string
        prefix for all the files (perhaps just a bucket name)
    gcfs : GCSFS
        Google Cloud Storage filesystem
    check : bool (=False)
        performs a touch at the location, to check writeability.
    create : bool (=False)
        creates bucket if it does not yet exist
    """

    def __init__(self, root: str, gcfs: GCSFS, check=False, create=False):
        self.gcfs = gcfs
        self.root = root
        if check:
            self.gcfs.touch(root+'/a')
            self.gcfs.rm(root+'/a')
        else:
            bucket = split_path(root)[0]
            if create:
                self.gcfs.mkdir(bucket)
            elif not self.gcfs.exists(bucket):
                raise ValueError("Bucket %s does not exist."
                        " Create bucket with the ``create=True`` keyword" %
                        bucket)

    def clear(self):
        """Remove all keys below root - empties out mapping
        """
        try:
            self.gcfs.rm(self.root, recursive=True)
        except (IOError, OSError):
            # ignore non-existence of root
            pass

    def _key_to_str(self, key):
        if isinstance(key, (tuple, list)):
            key = str(tuple(key))
        else:
            key = str(key)
        return '/'.join([self.root, key])

    def __getitem__(self, key):
        key = self._key_to_str(key)
        try:
            with self.gcfs.open(key, 'rb') as f:
                result = f.read()
        except (IOError, OSError):
            raise KeyError(key)
        return result

    def __setitem__(self, key, value):
        key = self._key_to_str(key)
        with self.gcfs.open(key, 'wb') as f:
            f.write(value)

    def keys(self):
        return (x[len(self.root) + 1:] for x in self.gcfs.walk(self.root))

    def __iter__(self):
        return self.keys()

    def __delitem__(self, key):
        self.gcfs.rm(self._key_to_str(key))

    def __contains__(self, key):
        return self.gcfs.exists(self._key_to_str(key))

    def __len__(self):
        return sum(1 for _ in self.keys())

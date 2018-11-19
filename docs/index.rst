.. include:: ../README.rst


Limitations
===========

A filesystem built on top of an object store like GCS suffers from the same limitations as the ones
`mentioned in S3FS <https://fs-s3fs.readthedocs.io/en/latest/#limitations>`__.

GCS does not offer true directories which is why GCSFS (as well as S3FS) will simulate the existence
of a directory called ``foo`` by adding an empty blob called ``foo/``. Any filesystem content that was not created
via GCSFS will lack these directory markers which may lead to wrong behaviour. For example ``gcsfs.isdir("bar")``
will return ``False`` if the marker blob ``bar/`` does not exist, even though there might exist a blob called ``bar/baz.txt``.


To overcome this you can call the utility method :func:`~fs_gcsfs.GCSFS.fix_storage()` on your GCSFS instance
which will walk the entire filesystem (i.e. the entire ``bucket`` or the "subdirectory" you specified via ``root_path``) and add all missing directory markers.

.. warning::
    Listing and fixing large buckets may take some time!


Reference
=========

For a full reference of all available methods of GCSFS visit the documentation of
`fs.base.FS <https://pyfilesystem2.readthedocs.io/en/latest/reference/base.html>`__!


.. autoclass:: fs_gcsfs.GCSFS

    .. automethod:: fs_gcsfs.GCSFS.fix_storage


Powered By
==========

This PyFilesystem extension was created by `Othoz GmbH <http://othoz.com/>`__
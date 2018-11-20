GCSFS
=====

A Python filesystem abstraction of Google Cloud Storage (GCS) implemented as a `PyFilesystem2 <https://github.com/PyFilesystem/pyfilesystem2>`__ extension.


.. image:: https://img.shields.io/pypi/v/fs-gcsfs.svg
    :target: https://pypi.org/project/fs-gcsfs/

.. image:: https://img.shields.io/pypi/pyversions/fs-gcsfs.svg
    :target: https://pypi.org/project/fs-gcsfs/

.. image:: https://travis-ci.org/Othoz/gcsfs.svg?branch=master
    :target: https://travis-ci.org/Othoz/gcsfs

.. image:: https://readthedocs.org/projects/fs-gcsfs/badge/?version=latest
    :target: https://fs-gcsfs.readthedocs.io/en/latest/?badge=latest

.. image:: https://api.codacy.com/project/badge/Coverage/6377a6e321cd4ccf94dfd6f09456d9ce
    :target: https://www.codacy.com/app/Othoz/gcsfs?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=Othoz/gcsfs&amp;utm_campaign=Badge_Coverage

.. image:: https://api.codacy.com/project/badge/Grade/6377a6e321cd4ccf94dfd6f09456d9ce
    :target: https://www.codacy.com/app/Othoz/gcsfs?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=Othoz/gcsfs&amp;utm_campaign=Badge_Grade


With GCSFS, you can interact with `Google Cloud Storage <https://cloud.google.com/storage/>`__ as if it was a regular filesystem.

Apart from the nicer interface, this will highly decouple your code from the underlying storage mechanism: Exchanging the storage backend with an
`in-memory filesystem <https://pyfilesystem2.readthedocs.io/en/latest/reference/memoryfs.html>`__ for testing or any other
filesystem like `S3FS <https://github.com/pyfilesystem/s3fs>`__ becomes as easy as replacing ``gs://bucket_name`` with ``mem://`` or ``s3://bucket_name``.

For a full reference on all the PyFilesystem possibilities, take a look at the
`PyFilesystem Docs <https://pyfilesystem2.readthedocs.io/en/latest/index.html>`__!


Documentation
-------------

-  `GCSFS Documentation <http://fs-gcsfs.readthedocs.io/en/latest/>`__
-  `PyFilesystem Wiki <https://www.pyfilesystem.org>`__
-  `PyFilesystem Reference <https://docs.pyfilesystem.org/en/latest/reference/base.html>`__


Installing
----------

Install the latest GCSFS version by running::

    $ pip install fs-gcsfs

Or in case you are using conda::

    $ conda install -c conda-forge fs-gcsfs


Examples
--------

Instantiating a filesystem on Google Cloud Storage (for a full reference visit the
`Documentation <http://fs-gcsfs.readthedocs.io/en/latest/index.html#reference>`__):

.. code-block:: python

    from fs_gcsfs import GCSFS
    gcsfs = GCSFS(bucket_name="mybucket")


Alternatively you can use a `FS URL <https://pyfilesystem2.readthedocs.io/en/latest/openers.html>`__ to open up a filesystem:

.. code-block:: python

    from fs import open_fs
    gcsfs = open_fs("gs://mybucket/root_path?strict=False")

You can use GCSFS like your local filesystem:

.. code-block:: python

    >>> from fs_gcsfs import GCSFS
    >>> gcsfs = GCSFS(bucket_name="mybucket")
    >>> gcsfs.tree()
    ├── foo
    │   ├── bar
    │   │   ├── file1.txt
    │   │   └── file2.csv
    │   └── baz
    │       └── file3.txt
    └── file4.json
    >>> gcsfs.listdir("foo")
    ["bar", "baz"]
    >>> gcsfs.isdir("foo/bar")
    True


Uploading a file is as easy as:

.. code-block:: python

    from fs_gcsfs import GCSFS
    gcsfs = GCSFS(bucket_name="mybucket")
    with open("local/path/image.jpg", "rb") as local_file:
        with gcsfs.open("path/on/bucket/image.jpg", "wb") as gcs_file:
            gcs_file.write(local_file.read())


You can even sync an entire bucket on your local filesystem by using PyFilesystem's utility methods:

.. code-block:: python

    from fs_gcsfs import GCSFS
    from fs.osfs import OSFS
    from fs.copy import copy_fs

    gcsfs = GCSFS(bucket_name="mybucket")
    local_fs = OSFS("local/path")

    copy_fs(gcsfs, local_fs)


For exploring all the possibilities of GCSFS and other filesystems implementing the PyFilesystem interface, we recommend visiting the official
`PyFilesystem Docs <https://pyfilesystem2.readthedocs.io/en/latest/index.html>`__!


Development
-----------

To develop on this project make sure you have `pipenv <https://pipenv.readthedocs.io/en/latest/>`__ installed
and run the following from the root directory of the project::

    $ pipenv install --dev --three

This will create a virtualenv with all packages and dev-packages installed.


Tests
-----
All CI tests run against an actual GCS bucket provided by `Othoz <http://othoz.com/>`__. In order to run the tests against your own bucket,
make sure to set up a `Service Account <https://cloud.google.com/iam/docs/service-accounts>`__ with all necessary permissions:

- storage.buckets.get
- storage.objects.get
- storage.objects.list
- storage.objects.create
- storage.objects.update
- storage.objects.delete

Expose your bucket name as an environment variable ``$TEST_BUCKET`` and run the tests via::

    $ pipenv run pytest

Note that the tests mostly wait for I/O, therefore it makes sense to highly parallelize them with `xdist <https://github.com/pytest-dev/pytest-xdist>`__.


Credits
-------

Credits go to `S3FS <https://github.com/PyFilesystem/s3fs>`__ which was the main source of inspiration and shares a lot of code with GCSFS.
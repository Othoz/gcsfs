GCSFS
=====

A Python filesystem abstraction of Google Cloud Storage (GCS) implemented as a `PyFilesystem2 <https://github.com/PyFilesystem/pyfilesystem2>`_ extension.


.. image:: https://img.shields.io/pypi/v/fs-gcsfs.svg
    :target: https://pypi.org/project/fs-gcsfs/

.. image:: https://img.shields.io/pypi/pyversions/fs-gcsfs.svg
    :target: https://pypi.org/project/fs-gcsfs/

.. image:: https://travis-ci.org/Othoz/gcsfs.svg?branch=master
    :target: https://travis-ci.org/Othoz/gcsfs

.. image:: https://api.codacy.com/project/badge/Coverage/6377a6e321cd4ccf94dfd6f09456d9ce
    :target: https://www.codacy.com/app/Othoz/gcsfs?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=Othoz/gcsfs&amp;utm_campaign=Badge_Coverage

.. image:: https://api.codacy.com/project/badge/Grade/6377a6e321cd4ccf94dfd6f09456d9ce
    :target: https://www.codacy.com/app/Othoz/gcsfs?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=Othoz/gcsfs&amp;utm_campaign=Badge_Grade

.. image:: https://img.shields.io/github/license/Othoz/gcsfs.svg
    :target: https://github.com/PyFilesystem/pyfilesystem2/blob/master/LICENSE


GCSFS lets you interact with `Google Cloud Storage <https://cloud.google.com/storage/>`_ like it wasn't an object store but a regular filesystem.
As it implements the common PyFilesystem interface, it is easy to exchange the underlying storage mechanism.
You do not need to change any of your code to instead use e.g. `S3FS <https://github.com/pyfilesystem/s3fs>`_ or a simple `in-memory filesystem <https://pyfilesystem2.readthedocs.io/en/latest/reference/memoryfs.html>`_ for testing.

For a full reference on all the PyFilesystem possibilities, take a look at the `PyFilesystem Docs <https://pyfilesystem2.readthedocs.io/en/latest/index.html>`_!


Installing
----------

Install the latest GCSFS version by running::

    $ pip install fs-gcsfs

A conda-forge release is planned for the near future!


How To Use
----------

Instantiating a GCS filesystem and working with it is as easy as:

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


Alternatively you can use an `opener <https://pyfilesystem2.readthedocs.io/en/latest/openers.html>`_ URL:

.. code-block:: python

    >>> from fs import open_fs
    >>> gcsfs = open_fs("gs://mybucket")
    >>> gcsfs.listdir("foo")
    ["bar", "baz"]


Uploading files is as easy as moving them on your local filesystem:

.. code-block:: python

    from fs_gcsfs import GCSFS
    gcsfs = GCSFS(bucket_name="mybucket")

    with open("image.jpg", "rb") as local_file:
        with gcsfs.open("image.jpg", "wb") as gcs_file:
            gcs_file.write(local_file.read())

For more information on the usage of PyFilesystem and its extensions see the official `Reference <https://pyfilesystem2.readthedocs.io/en/latest/reference/base.html>`_



Limitations
-----------

A filesystem built on top of an object store like GCS suffers from the same limitations as the ones
`mentioned in S3FS <https://fs-s3fs.readthedocs.io/en/latest/#limitations>`_.

GCS does not offer true directories which is why GCSFS (as well as S3FS) will simulate the existence
of a directory called ``foo`` by adding an empty blob called ``foo/``. Any filesystem content that was not created
via GCSFS will lack these directory markers which may lead to wrong behaviour. For example ``gcsfs.isdir("bar")``
will return ``False`` if the marker blob ``bar/`` does not exist, even though there might exist a blob called ``bar/baz.txt``.

*TODO: Finish and document the "fix storage feature"*


Development
-----------

To further improve this project install `pipenv <https://pipenv.readthedocs.io/en/latest/>`_
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

Credits go to `S3FS <https://github.com/PyFilesystem/s3fs>`_ which was the main source of inspiration and shares a lot of code with GCSFS.


Documentation
-------------

-  `PyFilesystem Wiki <https://www.pyfilesystem.org>`_
-  `PyFilesystem Reference <https://docs.pyfilesystem.org/en/latest/reference/base.html>`_

.. TODO `GCS Reference <http://fs-gcsfs.readthedocs.io/en/latest/>`_
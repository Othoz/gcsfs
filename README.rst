GCSFS
=====

A Google Cloud Storage (GCS) filesystem for `PyFilesystem2 <https://github.com/PyFilesystem/pyfilesystem2>`_.

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

GCSFS can be used like any other PyFilesystem implementation, see the
`FS reference <https://pyfilesystem2.readthedocs.io/en/latest/reference/base.html>`_:

.. code-block:: python

    from fs_gcsfs import GCSFS
    gcsfs = GCSFS(bucket_name="mybucket")

    with gcsfs.open("foo/bar.txt", "w") as f:
        f.write("Some text")


Alternatively you can an `opener <https://pyfilesystem2.readthedocs.io/en/latest/openers.html>`_ URL:

.. code-block:: python

    from fs import open_fs
    gcsfs = open_fs("gs://mybucket")


Limitations
-----------

A filesystem built on top of an object store like GCS suffers from the same limitations as the ones
`mentioned in S3FS <https://fs-s3fs.readthedocs.io/en/latest/#limitations>`_.

GCS does not offer the concept of directories which is why GCSFS (as well as S3FS) will simulate the existence
of a directory called ``foo`` by adding an empty blob called ``foo/``. Any filesystem content that was no created
via GCSFS will lack these directory markers which may lead to wrong behaviour in some cases.

*TODO: Finish and document the "fix storage feature"*


Development
-----------

To develop on this project make sure you have `pipenv <https://pipenv.readthedocs.io/en/latest/>`_ installed
and run the following from the root directory of the project::

    $ pipenv install --dev --three

This will create a virtualenv with all packages and dev-packages installed. Now you can for example
run all tests via::

    $ pipenv run pytest


Credits
-------

Credits go to `S3FS <https://github.com/PyFilesystem/s3fs>`_ which was the main source of inspiration and shares a lot of code with GCSFS.


Documentation
-------------

-  `PyFilesystem Wiki <https://www.pyfilesystem.org>`_
-  `PyFilesystem Reference <https://docs.pyfilesystem.org/en/latest/reference/base.html>`_

.. TODO `GCS Reference <http://fs-gcsfs.readthedocs.io/en/latest/>`_
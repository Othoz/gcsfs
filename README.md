Overview
========

A PyFilesystem interface to Google Cloud Storage.


How to publish on PyPy
----------------------

As we need ``fs-gcsfs`` to be installable as a pip package for Google Cloud ML 
Engine, we currently have a _manual_ way to publish it to PyPy.
This will be replaced by an automated solution once we open source this repository.

To publish the repository you need the PyPy test credentials of wiesner@othoz.com
and setup your ``.pypirc`` according to
https://blog.jetbrains.com/pycharm/2017/05/how-to-publish-your-package-on-pypi/.
You also need to install `twine <https://pypi.org/project/twine/>`_ for publishing
the package.

Make sure your git HEAD is on a tagged commit in order to make versioneer
produce a clean version tag and run:

    python setup.py sdist

To create the pip-installable tar under ``./dist``. Then run:

    twine upload dist/*

to publish the package to PyPy
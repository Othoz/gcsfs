Versions
========

The format is based on `Keep a Changelog <http://keepachangelog.com/en/1.0.0/>`_
and this project adheres to `Semantic Versioning <http://semver.org/spec/v2.0.0.html>`_.

All release versions should be documented here with release date and types of changes.
Unreleased changes and pre-releases (i.e. alpha/beta versions) can be documented under the section `Unreleased`.

Possible types of changes are:

- `Added` for new features
- `Changed` for changes in existing functionality
- `Deprecated` for soon-to-be removed features
- `Removed` for now removed features
- `Fixed` for any bug fixes
- `Security` in case of vulnerabilities


Unreleased
----------


0.1.6 - 30.10.2018
------------------

Fixed
'''''
- ``GCSFS.makedirs()`` is now suitable for multiprocessing


0.1.5 - 08.10.2018
------------------

Changed
'''''''
- The ``bucket`` and ``client`` properties of ``GCSFS`` are now only computed once on instance initialization (performance improvement)


0.1.4 - 08.10.2018
------------------

Fixed
'''''
- ``GCSFS.exists()`` now correctly handles existing directories that are not marked with an empty file


0.1.3 - 04.10.2018
------------------

Changed
'''''''
- Added a custom implementation of ``FS.opendir()`` in order to be able to skip the directory check if strict=False (performance improvement)


0.1.2 - 20.09.2018
------------------

Fixed
'''''
- Fixed a bug where ``listdir``/``scandir`` on the root level of a bucket would always return an empty result

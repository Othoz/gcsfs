# coding: utf-8
"""Defines the GCSFSOpener."""

__all__ = ['GCSFSOpener']

from fs.opener import Opener
from fs.opener.errors import OpenerError
from fs.path import iteratepath, join

from ._gcsfs import GCSFS


class GCSFSOpener(Opener):
    protocols = ['gs']

    def open_fs(self, fs_url, parse_result, writeable, create, cwd):  # pylint: disable=no-self-use
        path_parts = iteratepath(parse_result.resource)

        bucket_name = path_parts[0]
        root_path = join(*path_parts[1:])

        if not bucket_name:
            raise OpenerError("invalid bucket name in '{}'".format(fs_url))

        if parse_result.params.get("strict") == "False":
            strict = False
        else:
            strict = True

        return GCSFS(bucket_name, root_path=root_path, create=create, strict=strict)

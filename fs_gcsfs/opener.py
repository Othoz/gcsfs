# coding: utf-8
"""Defines the GCSFSOpener."""

__all__ = ['GCSFSOpener']

from google.cloud.storage import Client
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

        client = Client()
        project = parse_result.params.get("project")
        if project:
            client.project = project
        api_endpoint = parse_result.params.get("api_endpoint")
        if api_endpoint:
            client.client_options = {"api_endpoint": api_endpoint}

        return GCSFS(bucket_name, root_path=root_path, create=create, client=client, strict=strict)

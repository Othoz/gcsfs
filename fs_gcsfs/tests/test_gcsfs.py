import unittest
import uuid
import os

import pytest
from fs.test import FSTestCases
from google.cloud.storage import Client

from fs_gcsfs import GCSFS

TEST_BUCKET = os.environ['TEST_BUCKET']


class TestGCSFSPyFileSystem(FSTestCases, unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = Client()
        cls.bucket = cls.client.get_bucket(TEST_BUCKET)
        super().setUpClass()

    def setUp(self):
        self.root_path = "gcsfs/" + str(uuid.uuid4())
        super().setUp()

    def tearDown(self):
        super().destroy_fs(self.fs)
        for blob in self.bucket.list_blobs(prefix=self.root_path):
            blob.delete()

    def make_fs(self):
        return GCSFS(bucket_name=TEST_BUCKET, root_path=self.root_path, client=self.client)


@pytest.fixture(scope="module")
def client():
    return Client()


@pytest.fixture(scope="module")
def bucket(client):
    return client.get_bucket(TEST_BUCKET)


@pytest.fixture(scope="function")
def tmp_gcsfs(bucket, client):
    """Yield a temporary `GCSFS` at a unique 'root-blob' within the test bucket."""
    path = "gcsfs/" + str(uuid.uuid4())
    fs = GCSFS(bucket_name=bucket.name, root_path=path, client=client)
    yield fs

    fs.close()
    for blob in bucket.list_blobs(prefix=path):
        blob.delete()


class TestGCSFS:

    @pytest.mark.skip("There is still a bug in the scandir implementaion. Root level blobs (which are not directories) are not listed")
    def test_scandir_works_on_bucket_as_root_directory(self, client):
        gcs_fs = GCSFS(bucket_name=TEST_BUCKET, client=client)
        path = str(uuid.uuid4())
        with gcs_fs.open(path, "wb") as f:
            f.write(b"Hallo")
        result = gcs_fs.listdir("")
        # Manual clean-up of the file created on the root directory
        gcs_fs.remove(path)
        gcs_fs.close()
        assert path in result

    def test_path_to_key_for_root_returns_root_path(self, tmp_gcsfs):
        assert tmp_gcsfs._path_to_key("/") == tmp_gcsfs.root_path

    def test_path_to_key_for_empty_string_returns_root_path(self, tmp_gcsfs):
        assert tmp_gcsfs._path_to_key("") == tmp_gcsfs.root_path

    def test_fix_storage_adds_binary_blobs_with_empty_string_as_directory_marker(self, bucket, tmp_gcsfs):
        # Creating a 'nested' hierarchy of blobs without directory marker
        for path in ["foo/test", "foo/bar/test", "foo/baz/test", "foo/bar/egg/test"]:
            key = tmp_gcsfs._path_to_key(path)
            blob = bucket.blob(key)
            blob.upload_from_string(b"Is this a test? It has to be. Otherwise I can't go on.")
        tmp_gcsfs.fix_storage()

        for path in ["", "foo", "foo/bar", "foo/baz", "foo/bar/egg"]:
            assert tmp_gcsfs.isdir(path)

    def test_fix_storage_does_not_overwrite_existing_directory_markers_with_custom_content(self, bucket, tmp_gcsfs):
        for path in ["foo/test"]:
            key = tmp_gcsfs._path_to_key(path)
            blob = bucket.blob(key)
            blob.upload_from_string(b"Is this a test? It has to be. Otherwise I can't go on.")

        # Manual creation of 'directory marker' with custom content
        key = tmp_gcsfs._path_to_dir_key("foo/")
        blob = bucket.blob(key)
        content = b"CUSTOM_DIRECTORY_MARKER_CONTENT"
        blob.upload_from_string(content)

        tmp_gcsfs.fix_storage()

        assert blob.download_as_string() == content

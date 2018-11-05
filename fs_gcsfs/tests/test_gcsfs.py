import unittest
import uuid

from fs.test import FSTestCases

from fs_gcsfs import GCSFS


class TestGCSFS(FSTestCases, unittest.TestCase):

    def make_fs(self):
        return GCSFS(bucket_name="othoz-test", root_path="gcsfs-tests/" + str(uuid.uuid4()))

    def test_scandir_works_on_root_directory(self):
        gcs_fs = GCSFS(bucket_name="othoz-test")
        with gcs_fs.open(str(uuid.uuid4()) + ".test", "wb") as f:
            f.write(b"")
        assert len(gcs_fs.listdir("")) > 0

    # TODO Add unit tests for handling the case that the underlying Storage does not contain the required empty files to mark directories.
    # This situation should to be handled correctly (and if possible even fixed) by functions like isdir(), exists(), listdir(), ...
    # See: https://fs-s3fs.readthedocs.io/en/latest/#limitations

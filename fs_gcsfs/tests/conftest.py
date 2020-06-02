import os
import uuid

import pytest
from google.cloud.storage import Client

from fs_gcsfs import GCSFS


@pytest.fixture(scope="module")
def client():
    return Client()


@pytest.fixture(scope="module")
def bucket(client):
    return client.bucket(os.environ['TEST_BUCKET'])


@pytest.fixture(scope="function")
def gcsfs(bucket, client):
    """Yield a temporary `GCSFS` at a unique 'root-blob' within the test bucket."""
    path = "gcsfs/" + str(uuid.uuid4())
    yield GCSFS(bucket_name=bucket.name, root_path=path, client=client, create=True)
    for blob in bucket.list_blobs(prefix=path):
        blob.delete()

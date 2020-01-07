# These tests have been partially copied and adopted from the S3Map implementation of https://github.com/dask/s3fs


def test_empty_mapping(gcsfs):
    d = gcsfs.get_mapper()
    assert not d
    assert list(d) == list(d.keys()) == []
    assert list(d.values()) == []
    assert list(d.items()) == []


def test_reading_and_writing_to_mapping(gcsfs):
    d = gcsfs.get_mapper()
    d["x"] = b"123"
    assert d["x"] == b"123"
    assert list(d) == list(d.keys()) == ["x"]
    assert list(d.values()) == [b"123"]
    assert list(d.items()) == [("x", b"123")]
    assert bool(d)

    d["x"] = b"000"
    assert d["x"] == b"000"

    d["y"] = b"456"
    assert d["y"] == b"456"
    assert set(d) == {"x", "y"}


def test_reading_and_writing_complex_keys(gcsfs):
    d = gcsfs.get_mapper()
    d[1] = b"hello"
    assert d[1] == b"hello"
    del d[1]

    d[1, 2] = b"world"
    assert d[1, 2] == b"world"
    del d[1, 2]

    d["x", 1, 2] = b"hello world"
    assert d["x", 1, 2] == b"hello world"
    assert ("x", 1, 2) in d


def test_writing_array(gcsfs):
    from array import array
    d = gcsfs.get_mapper()
    d["x"] = array("B", [65] * 1000)
    assert d["x"] == b"A" * 1000


def test_writing_bytearray(gcsfs):
    d = gcsfs.get_mapper()
    d["x"] = bytearray(b"123")
    assert d["x"] == b"123"

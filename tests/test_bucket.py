from pathlib import Path

import pytest

from anemiaiaback.capture.infrastructure.storage.local_image_bucket import LocalImageBucket
from anemiaiaback.capture.domain.errors import ConfigurationError, StorageError


PNG = b"\x89PNG\r\n\x1a\nencoded"


def test_rejects_absolute_bucket_before_creating_it(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    outside = tmp_path / "outside"
    with pytest.raises(ConfigurationError):
        LocalImageBucket(outside, project)
    assert not outside.exists()


def test_rejects_traversal_bucket_before_creating_it(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    outside = tmp_path / "outside"
    with pytest.raises(ConfigurationError):
        LocalImageBucket(Path("../outside"), project)
    assert not outside.exists()


def test_saves_relative_key_and_deletes_png(tmp_path):
    bucket = LocalImageBucket(Path("local_bucket"), tmp_path)
    key = bucket.save_png(PNG)
    assert key.startswith("local_bucket/") and key.endswith(".png")
    assert (tmp_path / key).read_bytes() == PNG
    bucket.delete(key)
    assert not (tmp_path / key).exists()


def test_rejects_non_png_payload(tmp_path):
    bucket = LocalImageBucket(Path("local_bucket"), tmp_path)
    with pytest.raises(StorageError):
        bucket.save_png(b"not png")
    assert list((tmp_path / "local_bucket").iterdir()) == []

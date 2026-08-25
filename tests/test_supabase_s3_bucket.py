import pytest
from botocore.exceptions import ClientError

from anemiaiaback.capture.domain.errors import StorageError
from anemiaiaback.capture.infrastructure.storage.supabase_s3_image_bucket import (
    SupabaseS3ImageBucket,
)


PNG = b"\x89PNG\r\n\x1a\nencoded"


class FakeS3Client:
    def __init__(self, fail_put: bool = False) -> None:
        self.fail_put = fail_put
        self.put = None
        self.deleted = None

    def put_object(self, **kwargs):
        if self.fail_put:
            raise ClientError(
                {"Error": {"Code": "Denied", "Message": "internal"}},
                "PutObject",
            )
        self.put = kwargs

    def delete_object(self, **kwargs):
        self.deleted = kwargs


def make_bucket(client):
    return SupabaseS3ImageBucket(
        endpoint_url="https://example.test/storage/v1/s3",
        region="us-west-2",
        bucket="ImagesProcesed",
        access_key_id="access",
        secret_access_key="secret",
        client=client,
    )


def test_builds_boto_client_with_path_style_addressing(monkeypatch):
    from anemiaiaback.capture.infrastructure.storage import (
        supabase_s3_image_bucket as module,
    )

    captured = {}

    def client_factory(service, **kwargs):
        captured["service"] = service
        captured.update(kwargs)
        return FakeS3Client()

    monkeypatch.setattr(module.boto3, "client", client_factory)
    make_bucket(None)
    assert captured["service"] == "s3"
    assert captured["endpoint_url"] == "https://example.test/storage/v1/s3"
    assert captured["region_name"] == "us-west-2"
    assert captured["config"].s3 == {"addressing_style": "path"}


def test_puts_png_and_returns_stable_s3_reference():
    client = FakeS3Client()
    reference = make_bucket(client).save_png(PNG)
    assert reference.startswith("s3://ImagesProcesed/") and reference.endswith(".png")
    key = reference.removeprefix("s3://ImagesProcesed/")
    assert client.put == {
        "Bucket": "ImagesProcesed",
        "Key": key,
        "Body": PNG,
        "ContentType": "image/png",
    }


def test_delete_uses_bucket_and_key_from_reference():
    client = FakeS3Client()
    bucket = make_bucket(client)
    bucket.delete("s3://ImagesProcesed/a.png")
    assert client.deleted == {"Bucket": "ImagesProcesed", "Key": "a.png"}


def test_rejects_reference_for_another_bucket():
    with pytest.raises(StorageError):
        make_bucket(FakeS3Client()).delete("s3://other/a.png")


def test_sdk_failure_is_wrapped_without_internal_message():
    with pytest.raises(StorageError) as caught:
        make_bucket(FakeS3Client(fail_put=True)).save_png(PNG)
    assert "internal" not in str(caught.value)

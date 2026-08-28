from datetime import datetime
from urllib.parse import urlparse
from uuid import uuid4

import boto3
from botocore.client import Config
from botocore.exceptions import BotoCoreError, ClientError

from anemiaiaback.capture.domain.errors import ConfigurationError, StorageError


class SupabaseS3ImageBucket:
    """Store segmented PNGs through Supabase's S3-compatible endpoint."""

    def __init__(
        self,
        *,
        endpoint_url: str,
        region: str,
        bucket: str,
        access_key_id: str,
        secret_access_key: str,
        client=None,
    ) -> None:
        if not endpoint_url.startswith("https://"):
            raise ConfigurationError("S3 endpoint must use HTTPS")
        if not all((region.strip(), bucket.strip(), access_key_id, secret_access_key)):
            raise ConfigurationError("S3 configuration is incomplete")
        self._bucket = bucket
        if client is not None:
            self._client = client
            return
        try:
            self._client = boto3.client(
                "s3",
                endpoint_url=endpoint_url,
                region_name=region,
                aws_access_key_id=access_key_id,
                aws_secret_access_key=secret_access_key,
                config=Config(s3={"addressing_style": "path"}),
            )
        except (BotoCoreError, ClientError, OSError) as exc:
            raise StorageError("Could not initialize image storage") from exc

    def save_png(self, image: bytes) -> str:
        if not image.startswith(b"\x89PNG\r\n\x1a\n"):
            raise StorageError("Image storage accepts encoded PNG data only")
        # Generar nombre con formato: aa-(dia-hora-minuto-segundo)
        now = datetime.now()
        key = f"aa-{now.strftime('%d-%H-%M-%S')}.png"
        try:
            self._client.put_object(
                Bucket=self._bucket,
                Key=key,
                Body=image,
                ContentType="image/png",
            )
        except (BotoCoreError, ClientError, OSError) as exc:
            raise StorageError("Could not store segmented image") from exc
        return f"s3://{self._bucket}/{key}"

    def delete(self, storage_reference: str) -> None:
        bucket, key = self._parse_reference(storage_reference)
        try:
            self._client.delete_object(Bucket=bucket, Key=key)
        except (BotoCoreError, ClientError, OSError) as exc:
            raise StorageError("Could not delete segmented image") from exc

    def _parse_reference(self, storage_reference: str) -> tuple[str, str]:
        parsed = urlparse(storage_reference)
        key = parsed.path.lstrip("/")
        if parsed.scheme != "s3" or parsed.netloc != self._bucket or not key:
            raise StorageError("Invalid image storage reference")
        return parsed.netloc, key

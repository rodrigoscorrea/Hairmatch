import mimetypes
from urllib.parse import quote

import boto3
from botocore.exceptions import ClientError
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import Storage
from django.utils.deconstruct import deconstructible

# Python before 3.13 has no built-in .webp entry, and the upload would go out as octet-stream.
mimetypes.add_type('image/webp', '.webp')


@deconstructible
class S3MediaStorage(Storage):
    """
    Stores media files in a public S3 bucket using boto3.

    Endpoint, region and credentials come from the standard AWS_* env vars read
    by boto3. URLs returned to clients use S3_PUBLIC_ENDPOINT_URL when set
    (LocalStack), since the backend may reach S3 through a different host.
    """

    def __init__(self):
        self._client = None

    @property
    def client(self):
        if self._client is None:
            self._client = boto3.client('s3')
        return self._client

    @property
    def bucket(self):
        return settings.S3_BUCKET_NAME

    def _open(self, name, mode='rb'):
        response = self.client.get_object(Bucket=self.bucket, Key=name)
        return ContentFile(response['Body'].read(), name=name)

    def _save(self, name, content):
        content.seek(0)
        content_type = mimetypes.guess_type(name)[0] or 'application/octet-stream'
        self.client.upload_fileobj(
            content, self.bucket, name, ExtraArgs={'ContentType': content_type}
        )
        return name

    def exists(self, name):
        try:
            self.client.head_object(Bucket=self.bucket, Key=name)
        except ClientError as e:
            if e.response.get('Error', {}).get('Code') in ('404', 'NoSuchKey', 'NotFound'):
                return False
            raise
        return True

    def delete(self, name):
        self.client.delete_object(Bucket=self.bucket, Key=name)

    def size(self, name):
        return self.client.head_object(Bucket=self.bucket, Key=name)['ContentLength']

    def url(self, name):
        key = quote(name)
        public_endpoint = settings.S3_PUBLIC_ENDPOINT_URL
        if public_endpoint:
            return f"{public_endpoint.rstrip('/')}/{self.bucket}/{key}"
        region = self.client.meta.region_name
        return f"https://{self.bucket}.s3.{region}.amazonaws.com/{key}"

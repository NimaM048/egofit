import logging
from pathlib import Path
from urllib.parse import quote

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.utils.encoding import filepath_to_uri
from storages.backends.s3 import S3Storage

logger = logging.getLogger(__name__)


def liara_storage_enabled():
    return all(
        [
            getattr(settings, "AWS_S3_ENDPOINT_URL", ""),
            getattr(settings, "AWS_STORAGE_BUCKET_NAME", ""),
            getattr(settings, "AWS_ACCESS_KEY_ID", ""),
            getattr(settings, "AWS_SECRET_ACCESS_KEY", ""),
        ]
    )


class LiaraMediaStorage(S3Storage):
    querystring_auth = False

    def url(self, name, parameters=None, expire=None, http_method=None):
        if not name:
            return ""

        base_url = (getattr(settings, "LIARA_PUBLIC_BASE_URL", "") or settings.AWS_S3_ENDPOINT_URL or "").rstrip("/")
        bucket_name = (settings.AWS_STORAGE_BUCKET_NAME or "").strip("/")
        object_name = filepath_to_uri(name.lstrip("/"))
        return f"{base_url}/{bucket_name}/{object_name}"


class ResilientMediaStorage(FileSystemStorage):
    """
    Local-first storage with best-effort Liara mirroring.
    New uploads are always persisted locally. If Liara is configured,
    the same object is mirrored to S3-compatible storage without
    breaking the request on cloud failures.
    """

    def __init__(self, *args, **kwargs):
        location = kwargs.pop("location", settings.MEDIA_ROOT)
        base_url = kwargs.pop("base_url", settings.MEDIA_URL)
        super().__init__(location=location, base_url=base_url, *args, **kwargs)
        self._remote_storage = None

    @property
    def remote_storage(self):
        if self._remote_storage is None and liara_storage_enabled():
            self._remote_storage = LiaraMediaStorage()
        return self._remote_storage

    def _proxy_url(self, name):
        base_url = (getattr(settings, "RESILIENT_MEDIA_URL", "/media-files/") or "/media-files/").rstrip("/")
        return f"{base_url}/{quote(name.lstrip('/'))}"

    def url(self, name):
        if not name:
            return ""
        return self._proxy_url(str(name))

    def remote_url(self, name):
        if not name:
            return ""
        return self._proxy_url(str(name))

    def save(self, name, content, max_length=None):
        saved_name = super().save(name, content, max_length=max_length)
        self._mirror_to_remote(saved_name)
        return saved_name

    def exists(self, name):
        if super().exists(name):
            return True
        if self.remote_storage:
            try:
                return self.remote_storage.exists(name)
            except Exception as exc:
                logger.debug("Remote media exists check failed for %s: %s", name, exc)
                return False
        return False

    def delete(self, name):
        if super().exists(name):
            super().delete(name)
        if self.remote_storage:
            try:
                self.remote_storage.delete(name)
            except Exception as exc:
                logger.debug("Remote media delete failed for %s: %s", name, exc)

    def size(self, name):
        if super().exists(name):
            return super().size(name)
        if self.remote_storage:
            try:
                return self.remote_storage.size(name)
            except Exception as exc:
                logger.debug("Remote media size lookup failed for %s: %s", name, exc)
                return 0
        return 0

    def fetch_remote_to_local(self, name):
        if super().exists(name) or not self.remote_storage:
            return super().exists(name)

        try:
            remote_file = self.remote_storage.open(name, "rb")
        except Exception as exc:
            logger.warning("Remote media fetch failed for %s: %s", name, exc)
            return False

        try:
            local_path = Path(self.path(name))
            local_path.parent.mkdir(parents=True, exist_ok=True)
            with local_path.open("wb") as local_file:
                for chunk in remote_file.chunks():
                    local_file.write(chunk)
        finally:
            remote_file.close()
        return True

    def _mirror_to_remote(self, name):
        if not self.remote_storage:
            return

        try:
            with super().open(name, "rb") as local_file:
                self.remote_storage.save(name, local_file)
        except Exception as exc:
            # Cloud storage is optional at runtime; local media remains authoritative.
            logger.info("Remote media mirror skipped for %s: %s", name, exc)
            return

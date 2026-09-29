import time

from django.core.files.uploadhandler import FileUploadHandler, StopUpload


class BoundedUploadHandler(FileUploadHandler):
    """Reject oversized multipart bodies while streaming, before temporary disk grows unbounded."""

    max_bytes = 536870912

    def __init__(self, request=None):
        super().__init__(request)
        self.total = 0
        self.last_check = 0.0

    def receive_data_chunk(self, raw_data, start):
        from django.utils import timezone

        from backend.core.models import UploadAdmission
        from backend.core.security import admission_id

        # Absolute upload deadline; a stalled request cannot resurrect its reservation.
        if self.request and self.request.path.startswith("/api/") and not admission_id.get():
            raise StopUpload(connection_reset=True)
        if admission_id.get() and time.monotonic() - self.last_check >= 0.5:
            self.last_check = time.monotonic()
            if not UploadAdmission.objects.filter(
                pk=admission_id.get(), expires_at__gt=timezone.now()
            ).exists():
                raise StopUpload(connection_reset=True)
        self.total += len(raw_data)
        if self.total > self.max_bytes:
            raise StopUpload(connection_reset=True)
        return raw_data

    def file_complete(self, file_size):
        return None

from django.core.files.uploadhandler import FileUploadHandler, StopUpload


class BoundedUploadHandler(FileUploadHandler):
    """Reject oversized multipart bodies while streaming, before temporary disk grows unbounded."""

    max_bytes = 536870912

    def __init__(self, request=None):
        super().__init__(request)
        self.total = 0

    def receive_data_chunk(self, raw_data, start):
        self.total += len(raw_data)
        if self.total > self.max_bytes:
            raise StopUpload(connection_reset=True)
        return raw_data

    def file_complete(self, file_size):
        return None

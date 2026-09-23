"""Private, bounded single-range playback for timeline seeking."""

import re

from django.http import FileResponse, HttpResponse, StreamingHttpResponse


def video_response(path, range_header):
    size = path.stat().st_size
    if not range_header:
        response = FileResponse(path.open("rb"), content_type="video/mp4")
    else:
        match = re.fullmatch(r"bytes=(\d*)-(\d*)", range_header)
        start, end = 0, size - 1
        valid = match is not None and size > 0
        if match:
            first, last = match.groups()
            if not first:
                valid = valid and bool(last) and int(last or 0) > 0
                start = max(0, size - int(last or 0))
            else:
                start = int(first)
                end = min(int(last), size - 1) if last else size - 1
            valid = valid and 0 <= start <= end < size
        if not valid:
            response = HttpResponse(status=416)
            response["Content-Range"] = f"bytes */{size}"
        else:

            def chunks():
                with path.open("rb") as source:
                    source.seek(start)
                    remaining = end - start + 1
                    while remaining:
                        block = source.read(min(65536, remaining))
                        if not block:
                            break
                        remaining -= len(block)
                        yield block

            response = StreamingHttpResponse(chunks(), status=206, content_type="video/mp4")
            response["Content-Range"] = f"bytes {start}-{end}/{size}"
            response["Content-Length"] = str(end - start + 1)
    response["Accept-Ranges"] = "bytes"
    response["Cache-Control"] = "private, no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response

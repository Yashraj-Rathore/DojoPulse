"""Bound non-multipart bodies independently of framework parser implementation."""

from io import BytesIO

from django.conf import settings
from rest_framework.exceptions import ParseError
from rest_framework.parsers import FormParser, JSONParser


class BoundedBody:
    def parse(self, stream, media_type=None, parser_context=None):
        body = stream.read(settings.DATA_UPLOAD_MAX_MEMORY_SIZE + 1)
        if len(body) > settings.DATA_UPLOAD_MAX_MEMORY_SIZE:
            raise ParseError("Request body exceeds the configured limit")
        try:
            return super().parse(BytesIO(body), media_type, parser_context)
        except (RecursionError, ValueError) as error:
            raise ParseError("Invalid request body") from error


class BoundedJSONParser(BoundedBody, JSONParser):
    pass


class BoundedFormParser(BoundedBody, FormParser):
    pass

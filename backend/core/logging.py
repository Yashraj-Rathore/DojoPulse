"""Safe before Django app initialization; framework request details never reach log handlers."""

import logging


class RedactedRequestLogFilter(logging.Filter):
    def filter(self, record):
        record.msg = (
            '{"event":"http","reason":"SERVER_ERROR"}'
            if record.levelno >= logging.ERROR
            else '{"event":"http","reason":"REQUEST_REJECTED"}'
        )
        record.args = ()
        record.exc_info = record.exc_text = record.stack_info = None
        return True

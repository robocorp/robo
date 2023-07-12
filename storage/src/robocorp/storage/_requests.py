import json
import logging
import os
import random
import time
import urllib.parse
from typing import Callable, Optional

import requests
from requests.exceptions import HTTPError as _HTTPError
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_random_exponential,
)

LOGGER = logging.getLogger(__name__)
DEBUG = bool(os.getenv("RPA_DEBUG_API"))


def _needs_retry(exc: BaseException) -> bool:
    # Don't retry on some specific error codes or messages.

    # https://www.restapitutorial.com/httpstatuscodes.html
    # 400 - payload is bad and needs to be changed
    # 401 - missing auth bearer token
    # 403 - auth is in place, but not allowed (insufficient privileges)
    # 404 - resource does not exist
    # 409 - payload not good for the affected resource
    no_retry_codes = [400, 401, 403, 404, 409]

    if isinstance(exc, HTTPError):
        if exc.status_code in no_retry_codes:
            return False

        if exc.status_code == 429:
            # We hit the rate limiter, so sleep extra before retrying.
            seconds = round(random.uniform(1, 3), 2)
            LOGGER.warning("Rate limit hit, sleeping %.2fs...", seconds)
            time.sleep(seconds)

    return True


def _before_sleep_log():
    log_method = LOGGER.log

    def extensive_log(level, msg, *args, **kwargs):
        log_method(level, msg, *args, **kwargs)
        if DEBUG:
            LOGGER.debug(msg, *args)

    # Monkeypatch inner logging function so it produces an exhaustive log when
    # used under the before-sleep logging utility in `tenacity`.
    LOGGER.log = extensive_log
    return before_sleep_log(LOGGER, logging.DEBUG, exc_info=True)


# Exported for ease-of-use
Response = requests.Response


class HTTPError(_HTTPError):
    """Custom `requests` HTTP error with status code and reason"""

    def __init__(self, message: str, status_code: int, reason: str):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.reason = reason

    def __str__(self):
        return f"{self.status_code} {self.reason} - {self.message}"


class Requests:
    """Wrapper over `requests` 3rd-party with error handling and retrying support."""

    def __init__(self, route_prefix: str = "", default_headers: Optional[dict] = None):
        self._route_prefix = route_prefix
        self._default_headers = default_headers

    def handle_error(self, response: requests.Response):
        http_status = f"{response.status_code} {response.reason!r}"
        if 500 <= response.status_code < 600:
            LOGGER.critical("Server error: %s", http_status)
        elif 400 <= response.status_code < 500:
            LOGGER.info("Client error: %s", http_status)
        else:
            LOGGER.debug("Response: %s", http_status)

        if response.ok:
            return

        # Fallback values
        status_code = response.status_code
        reason = response.reason
        message = response.text

        try:
            fields = response.json()

            # For some reason we might still get a string from the deserialized
            # JSON payload, possible due to some double encoding bug in CR
            while not isinstance(fields, dict):
                fields = json.loads(fields)

            if "status" in fields:
                status_code = int(fields["status"])

            if "code" in fields:
                reason = fields["code"]
            elif "error" in fields and "code" in fields["error"]:
                reason = fields["error"]["code"]

            if "message" in fields:
                message = fields["message"]
            elif "error" in fields and "message" in fields["error"]:
                message = fields["error"]["message"]
        except Exception as exc:
            LOGGER.critical("Failed to parse error response: %r", exc)

        raise HTTPError(message, status_code=status_code, reason=reason)

    @retry(
        # Retry until either succeed or trying for the fifth time and still failing.
        # So sleep and retry for 4 times at most.
        stop=stop_after_attempt(5),
        # If the exception is no worth retrying or the number of tries is depleted,
        # then re-raise the last raised exception.
        reraise=True,
        # Decide if the raised exception needs retrying or not.
        retry=retry_if_exception(_needs_retry),
        # Produce debugging logging prior to each time we sleep & re-try.
        before_sleep=_before_sleep_log(),
        # Sleep between the tries with a random float amount of seconds like so:
        # 1. [0, 2]
        # 2. [0, 4]
        # 3. [0, 5]
        # 4. [0, 5]
        wait=wait_random_exponential(multiplier=2, max=5),
    )
    def _request(
        self,
        verb: Callable[..., requests.Response],
        url: str,
        *args,
        _handle_error: Optional[Callable[[requests.Response], None]] = None,
        _sensitive: bool = False,
        headers: Optional[dict] = None,
        **kwargs,
    ) -> requests.Response:
        # Absolute URLs override the prefix, so they are safe to be sent
        # as they'll be the same after joining.
        url = urllib.parse.urljoin(self._route_prefix, url)
        headers = headers if headers is not None else self._default_headers
        handle_error = _handle_error or self.handle_error

        log_url = url
        if _sensitive:
            # Omit query from the URL since might contain sensitive info.
            split = urllib.parse.urlsplit(log_url)
            split = split._replace(query="")
            log_url = urllib.parse.urlunsplit(split)

        LOGGER.debug("%s %r", verb.__name__.upper(), log_url)
        response = verb(url, *args, headers=headers, **kwargs)
        handle_error(response)
        return response

    def post(self, *args, **kwargs) -> requests.Response:
        return self._request(requests.post, *args, **kwargs)

    def get(self, *args, **kwargs) -> requests.Response:
        return self._request(requests.get, *args, **kwargs)

    def put(self, *args, **kwargs) -> requests.Response:
        return self._request(requests.put, *args, **kwargs)

    def delete(self, *args, **kwargs) -> requests.Response:
        return self._request(requests.delete, *args, **kwargs)

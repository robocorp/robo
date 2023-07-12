import logging
import os
from urllib.parse import urlsplit, urlunsplit

from ._utils import url_join

LOGGER = logging.getLogger(__name__)


def get_workspace() -> str:
    try:
        return os.environ["RC_WORKSPACE_ID"]
    except KeyError as err:
        raise RuntimeError("Missing environment variable 'RC_WORKSPACE_ID'") from err


def get_endpoint() -> str:
    if endpoint := os.getenv("RC_API_URL_V1"):
        return endpoint

    # Note (2023-06-28):
    # While Control Room does set RC_API_URL_V1, this is not currently supported
    # in local development. We can use as fallback the Vault endpoint, but we
    # need to replace some parts to get the correct value. Examples:
    #   api.eu1.robocloud.eu -> api.eu1.robocorp.com/v1
    #   api.ci.robocloud.dev -> api.ci.robocorp.dev/v1
    #   api.eu2.robocorp.com -> api.eu2.robocorp.com/v1
    #   api.us1.robocorp.com -> api.us1.robocorp.com/v1
    LOGGER.info("Missing environment variable 'RC_API_URL_V1', attempting fallback")
    endpoint = os.getenv("RC_API_SECRET_HOST")
    if endpoint is None:
        raise RuntimeError("Missing environment variable 'RC_API_URL_V1'")

    url = urlsplit(endpoint)

    # Replace hostname to match correct API
    netloc = url.netloc
    if url.hostname and url.hostname.endswith("robocloud.eu"):
        netloc = netloc.replace("robocloud.eu", "robocorp.com")
    elif url.hostname and url.hostname.endswith("robocloud.dev"):
        netloc = netloc.replace("robocloud.dev", "robocorp.dev")
    url = url._replace(netloc=netloc)

    # Append /v1/ to path if not already there
    if not url.path.rstrip("/").endswith("v1"):
        path = url_join(url.path, "v1")
        url = url._replace(path=path)

    result = urlunsplit(url)
    LOGGER.info("Adapted endpoint: %s -> %s", endpoint, result)
    return result


def get_token() -> str:
    if token := os.getenv("RC_API_TOKEN_V1"):
        return token

    # Note (2023-06-28):
    # While Control Room does set RC_API_TOKEN_V1, this is not currently
    # supported in local development. We can use as fallback the Vault token
    # which is identical.
    LOGGER.info("Missing environment variable 'RC_API_TOKEN_V1', attempting fallback")
    if token := os.getenv("RC_API_SECRET_TOKEN"):
        return token

    raise RuntimeError("Missing environment variable 'RC_API_TOKEN_V1'")

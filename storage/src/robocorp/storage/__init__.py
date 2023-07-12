import json
import logging
import mimetypes
import os
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Optional, Union

from ._client import AssetNotFound, AssetUploadFailed

if TYPE_CHECKING:
    from ._client import AssetsClient
    from ._requests import Response

__version__ = "0.2.0"
version_info = [int(x) for x in __version__.split(".")]

JSON = Union[dict[str, "JSON"], list["JSON"], str, int, float, bool, None]

LOGGER = logging.getLogger(__name__)

# Known (additional) mimetypes from file extensions
KNOWN_MIMETYPES = [
    ("text/x-yaml", ".yml"),
    ("text/x-yaml", ".yaml"),
]


@lru_cache(maxsize=1)
def _get_client() -> "AssetsClient":
    """
    Creates and returns an Asset Storage API client based on the injected
    environment variables from Control Room (or RCC).
    """
    from ._client import AssetsClient
    from ._environment import get_endpoint, get_token, get_workspace

    workspace = get_workspace()
    endpoint = get_endpoint()
    token = get_token()

    return AssetsClient(workspace, endpoint, token)


def list_assets() -> list[str]:
    """List all the existing assets.

    Returns:
        A list of available assets' names
    """
    return [asset["name"] for asset in _get_client().list_assets()]


def delete_asset(name: str):
    """Delete an asset by providing its `name`.

    This operation cannot be undone.

    Args:
        name: Asset to delete

    Raises:
        AssetNotFound: Asset with the given name does not exist
    """
    LOGGER.info("Deleting asset: %s", name)
    client = _get_client()
    client.delete_asset(asset_id=f"name:{name}")


def _get_asset(name: str) -> "Response":
    """Get an asset's payload URL."""
    from ._requests import Requests

    client = _get_client()
    details = client.get_asset(asset_id=f"name:{name}")
    payload = details["payload"]

    if payload["type"] == "url":
        url = payload["url"]
        return Requests().get(url)
    if payload["type"] == "empty":
        raise ValueError(
            f"Asset {details['name']!r} is empty."
            + " It could mean an upload is still pending"
            + " or has previously failed."
        )
    else:
        # Note (2023-07-04):
        # The 'data' payload type should only be used when uploading,
        # and it should never be in the response when getting an asset.
        raise RuntimeError(f"Unsupported payload type: {payload['type']}")


def get_text(name: str) -> str:
    """Return the given asset as text.

    Arguments:
        name: Name of asset

    Returns:
        Asset content as text

    Raises:
        AssetNotFound: No asset defined with given name
    """
    response = _get_asset(name)
    return response.text


def get_json(name: str, **kwargs) -> JSON:
    """Return the given asset as a deserialized JSON object.

    Arguments:
        name: Name of asset
        **kwargs: Additional parameters for `json.loads`

    Returns:
        Asset content as a Python object (dict, list etc.)

    Raises:
        AssetNotFound: No asset defined with given name
        JSONDecodeError: Asset was not valid JSON
    """
    response = _get_asset(name)
    return response.json(**kwargs)


def get_file(name: str, path: Union[os.PathLike, str], exist_ok=False) -> Path:
    """Fetch the given asset and store it in a file.

    Arguments:
        name: Name of asset
        path: Destination path for downloaded file
        exist_ok: Overwrite file if it already exists

    Returns:
        Path to created file

    Raises:
        AssetNotFound: No asset defined with given name
        FileExistsError: Destination already exists
    """
    response = _get_asset(name)

    path = Path(path).absolute()
    if path.exists() and not exist_ok:
        raise FileExistsError(f"File already exists: {path}")

    path.write_bytes(response.content)

    return path


def get_bytes(name: str) -> bytes:
    """Return the given asset as bytes.

    Arguments:
        name: Name of asset

    Returns:
        Asset content as bytes

    Raises:
        AssetNotFound: No asset defined with given name
    """
    response = _get_asset(name)
    return response.content


def _set_asset(name: str, content: bytes, content_type: str, wait: bool):
    """Upload asset content, and create asset if it doesn't already exist."""
    client = _get_client()

    try:
        details = client.get_asset(asset_id=f"name:{name}")
        LOGGER.debug("Updating existing asset with id: %s", details["id"])
    except AssetNotFound:
        details = client.create_asset(name=name)
        LOGGER.debug("Created new asset with id: %s", details["id"])

    LOGGER.info("Uploading asset (content-type: %s)", name, content_type)
    client.upload_asset(details["id"], content, content_type, wait)


def set_text(name: str, text: str, wait: bool = True):
    """Create or update an asset to contain the given string.

    Arguments:
        name: Name of asset
        text: Text content for asset
        wait: Wait for asset to update
    """
    content = text.encode("utf-8")
    content_type = "text/plain"
    _set_asset(name, content, content_type, wait)


def set_json(name: str, value: JSON, wait: bool = True, **kwargs):
    """Create or update an asset to contain the given object, serialized as JSON.

    Arguments:
        name: Name of asset
        value: Value for asset, e.g. dict or list
        wait: Wait for asset to update
        **kwargs: Additional arguments for `json.dumps`
    """
    content = json.dumps(value, **kwargs).encode("utf-8")
    content_type = "application/json"
    _set_asset(name, content, content_type, wait)


def set_file(
    name: str,
    path: Union[os.PathLike, str],
    content_type: Optional[str] = None,
    wait: bool = True,
):
    """Create or update an asset to contain the contents of the given file.

    Arguments:
        name: Name of asset
        path: Path to file
        content_type: Content type (or mimetype) of file, detected automatically
          from file extension if not defined
        wait: Wait for asset to update
    """
    if content_type is None:
        for type_, ext in KNOWN_MIMETYPES:
            mimetypes.add_type(type_, ext)

        content_type, _ = mimetypes.guess_type(path)
        if content_type is not None:
            LOGGER.info("Detected content type %r", content_type)
        else:
            content_type = "application/octet-stream"
            LOGGER.info("Unable to detect content type, using %r", content_type)

    content = path.read_bytes()

    _set_asset(name, content, content_type, wait)


def set_bytes(
    name: str,
    data: bytes,
    content_type="application/octet-stream",
    wait: bool = True,
):
    """Create or update an asset to contain the given bytes.

    Arguments:
        name: Name of asset
        data: Raw content
        content_type: Content type (or mimetype) of asset
        wait: Wait for asset to update
    """
    _set_asset(name, data, content_type, wait)


__all__ = [
    "AssetNotFound",
    "AssetUploadFailed",
    "list_assets",
    "delete_asset",
    "get_text",
    "get_json",
    "get_file",
    "get_bytes",
    "set_text",
    "set_json",
    "set_file",
    "set_bytes",
]

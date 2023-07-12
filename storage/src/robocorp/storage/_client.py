import base64
import logging
import math
import time
from typing import Optional, cast
from urllib.parse import quote_plus

from ._requests import HTTPError, Requests, Response
from ._types import (
    Asset,
    AssetDetails,
    AssetUploadResponse,
    AssetUploadState,
    ContentType,
)
from ._utils import url_join

LOGGER = logging.getLogger(__name__)

# Assets under `DATA_LIMIT` can be uploaded directly through the POST request,
# instead of requesting a separate upload url
DATA_LIMIT = 5 * 10**6  # 5MB


def _estimate_base64_size(size: int) -> int:
    """Return guess for content length after being base64 encoded."""
    return math.ceil(size / 3) * 4


class AssetNotFound(HTTPError):
    """No asset with given name/id found."""


class AssetUploadFailed(RuntimeError):
    """There was an unexpected error while uploading an asset."""


class AssetsClient:
    def __init__(self, workspace: str, endpoint: str, token: str):
        self._endpoint = endpoint
        self._workspace = workspace
        self._token = token

        route_prefix = url_join(self._endpoint, "workspaces", self._workspace, "assets")
        default_headers = {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }

        self._client = Requests(route_prefix, default_headers=default_headers)

    def _handle_asset_not_found(self, asset_id: str):
        """Create an error handler that raises `AssetNotFound` for 404 status codes."""

        def _handle_error(response: Response):
            try:
                self._client.handle_error(response)
            except HTTPError as exc:
                if exc.status_code == 404:
                    # NOTE(cmin764): Any `404 Not Found` error won't be retried
                    #  and will bubble-up from the first request.
                    raise AssetNotFound(
                        f"Asset with id {asset_id!r} not found",
                        status_code=exc.status_code,
                        reason=exc.reason,
                    ) from exc
                raise

        return _handle_error

    def list_assets(self) -> list[Asset]:
        """Retrieve list of assets."""
        return self._client.get("").json()

    def create_asset(self, name: str) -> AssetDetails:
        """Create a new asset."""
        payload = {"name": name}
        response = self._client.post("", json=payload)
        return cast(AssetDetails, response.json())

    def get_asset(self, asset_id: str) -> AssetDetails:
        """Returns the details of a single asset, including its payload."""
        path = quote_plus(asset_id)
        handler = self._handle_asset_not_found(asset_id)
        response = self._client.get(path, _handle_error=handler)
        return cast(AssetDetails, response.json())

    def delete_asset(self, asset_id: str):
        """Delete the given asset."""
        path = quote_plus(asset_id)
        handler = self._handle_asset_not_found(asset_id)
        self._client.delete(path, _handle_error=handler)

    def upload_asset(
        self,
        asset_id: str,
        content: bytes,
        content_type: Optional[ContentType] = None,
        wait=True,
        poll_interval=0.5,
    ):
        """Upload an asset payload, and optionally wait for it to finish."""
        if _estimate_base64_size(len(content)) < DATA_LIMIT:
            LOGGER.info("Content size under data limit, uploading directly")
            data_content = base64.b64encode(content).decode("ascii")
            assert len(data_content) < DATA_LIMIT, "Unexpected data size"
            response = self._create_upload(
                asset_id,
                content_type=content_type,
                data=data_content,
            )
        else:
            LOGGER.info("Content size over data limit, requesting upload URL")
            response = self._create_upload(asset_id, content_type=content_type)
            self._client.put(response["upload_url"], data=content, headers={})

        # NOTE (2023-07-04):
        # The asset upload should be done if the response says so,
        # but in reality it sometimes takes a while for the value to propagate

        # if response["status"] == "completed":
        #    return

        if not wait:
            return

        LOGGER.info("Waiting for asset upload to complete")
        while True:
            state = self._get_upload(asset_id, response["id"])
            status = state["status"]

            if status == "pending":
                time.sleep(poll_interval)
                continue
            elif status == "completed":
                break
            elif status == "failed":
                reason = state.get("reason", "unknown")
                raise AssetUploadFailed(f"Asset upload failed: {reason}")
            else:
                raise AssetUploadFailed(f"Asset upload invalid status: {status}")

    def _create_upload(
        self,
        asset_id: str,
        content_type: Optional[ContentType] = None,
        data: Optional[str] = None,
    ) -> AssetUploadResponse:
        """Create an upload for an existing asset.

        For payloads of less than 5MB you can upload the contents directly on
        upload creation. For larger payloads you can create the upload and use
        the returned upload URL for delivering the content.
        """
        payload = {}
        if content_type is not None:
            payload["content_type"] = content_type
        if data is not None:
            payload["data"] = data

        path = url_join(quote_plus(asset_id), "upload")
        handler = self._handle_asset_not_found(asset_id)
        response = self._client.post(path, json=payload, _handle_error=handler)
        return cast(AssetUploadResponse, response.json())

    def _get_upload(self, asset_id: str, upload_id: str) -> AssetUploadState:
        """Return the details of a single asset upload."""
        path = url_join(quote_plus(asset_id), "uploads", upload_id)
        response = self._client.get(path)
        return cast(AssetUploadState, response.json())

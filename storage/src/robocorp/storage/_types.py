import sys
from typing import Literal, Optional, Union

if sys.version_info >= (3, 8):
    from typing import TypedDict
else:
    from typing_extensions import TypedDict


ContentType = str

Asset = TypedDict(
    "Asset",
    {
        "id": str,
        "name": str,
    },
)

AssetUploadRequest = TypedDict(
    "AssetUploadRequest",
    {
        "content_type": ContentType,
        "data": Optional[str],
    },
)

AssetUploadResponse = TypedDict(
    "AssetUploadResponse",
    {
        "id": str,
        "status": Union[Literal["pending"], Literal["completed"]],
        "content_type": ContentType,
        "upload_url": Optional[str],
    },
)

AssetUploadPending = TypedDict(
    "AssetUploadPending",
    {
        "id": str,
        "status": Literal["pending"],
        "content_type": ContentType,
    },
)

AssetUploadCompleted = TypedDict(
    "AssetUploadCompleted",
    {
        "id": str,
        "status": Literal["completed"],
        "content_type": ContentType,
    },
)

AssetUploadFailed = TypedDict(
    "AssetUploadFailed",
    {
        "id": str,
        "status": Literal["failed"],
        "content_type": ContentType,
        "reason": Optional[str],
    },
)

AssetUploadState = Union[
    AssetUploadPending,
    AssetUploadCompleted,
    AssetUploadFailed,
]

AssetPayloadEmpty = TypedDict(
    "AssetPayloadEmpty",
    {
        "type": Literal["empty"],
    },
)

AssetPayloadData = TypedDict(
    "AssetPayloadData",
    {
        "type": Literal["data"],
        "content_type": ContentType,
        "data": str,
    },
)

AssetPayloadUrl = TypedDict(
    "AssetPayloadUrl",
    {
        "type": Literal["url"],
        "content_type": ContentType,
        "url": str,
    },
)

AssetDetails = TypedDict(
    "AssetDetails",
    {
        "id": str,
        "name": str,
        "payload": Union[AssetPayloadEmpty, AssetPayloadData, AssetPayloadUrl],
    },
)

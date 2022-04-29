from typing import Dict
from requests_cache import (
    CachedResponse,
    SerializerPipeline,
    Stage,
    json_serializer,
)


class DiscardContentStage(Stage):
    """
    Only track whether a request would be cached; discard content.
    """

    def __init__(self):
        pass

    def dumps(self, value: CachedResponse) -> Dict:
        if isinstance(value, CachedResponse):
            value._content = b""
        return value

    def loads(self, value: Dict) -> CachedResponse:
        return value


discard_serializer = SerializerPipeline(
    [
        DiscardContentStage(),
        json_serializer,
    ],
    is_binary=True,
)

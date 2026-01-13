from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class PingRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class PingResponse(_message.Message):
    __slots__ = ("status",)
    STATUS_FIELD_NUMBER: _ClassVar[int]
    status: str
    def __init__(self, status: _Optional[str] = ...) -> None: ...

class MetricsRequest(_message.Message):
    __slots__ = ("provider_ids", "client_id")
    PROVIDER_IDS_FIELD_NUMBER: _ClassVar[int]
    CLIENT_ID_FIELD_NUMBER: _ClassVar[int]
    provider_ids: _containers.RepeatedScalarFieldContainer[str]
    client_id: str
    def __init__(self, provider_ids: _Optional[_Iterable[str]] = ..., client_id: _Optional[str] = ...) -> None: ...

class MetricsResponse(_message.Message):
    __slots__ = ("metrics",)
    METRICS_FIELD_NUMBER: _ClassVar[int]
    metrics: _containers.RepeatedCompositeFieldContainer[ProviderMetric]
    def __init__(self, metrics: _Optional[_Iterable[_Union[ProviderMetric, _Mapping]]] = ...) -> None: ...

class ProviderMetric(_message.Message):
    __slots__ = ("provider_id", "provider_name", "provider_type", "currency", "available_cents", "ledger_cents", "as_of_unix_ms")
    PROVIDER_ID_FIELD_NUMBER: _ClassVar[int]
    PROVIDER_NAME_FIELD_NUMBER: _ClassVar[int]
    PROVIDER_TYPE_FIELD_NUMBER: _ClassVar[int]
    CURRENCY_FIELD_NUMBER: _ClassVar[int]
    AVAILABLE_CENTS_FIELD_NUMBER: _ClassVar[int]
    LEDGER_CENTS_FIELD_NUMBER: _ClassVar[int]
    AS_OF_UNIX_MS_FIELD_NUMBER: _ClassVar[int]
    provider_id: str
    provider_name: str
    provider_type: str
    currency: str
    available_cents: int
    ledger_cents: int
    as_of_unix_ms: int
    def __init__(self, provider_id: _Optional[str] = ..., provider_name: _Optional[str] = ..., provider_type: _Optional[str] = ..., currency: _Optional[str] = ..., available_cents: _Optional[int] = ..., ledger_cents: _Optional[int] = ..., as_of_unix_ms: _Optional[int] = ...) -> None: ...

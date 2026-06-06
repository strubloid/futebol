from futebol.domain.enums.stream_status import StreamStatus
from futebol.domain.models.stream import Stream
from futebol.infrastructure.http.http_client import HttpClient
from futebol.validators.stream_url_validator import StreamUrlValidator


class StreamValidatorService:
    def __init__(
        self, http_client: HttpClient | None = None, url_validator: StreamUrlValidator | None = None
    ) -> None:
        self._http_client = http_client or HttpClient()
        self._url_validator = url_validator or StreamUrlValidator()

    def validate(self, stream: Stream) -> Stream:
        if not self._url_validator.is_valid(stream.url):
            return stream.with_status(StreamStatus.BROKEN, error="invalid stream URL")
        try:
            response = self._http_client.probe(stream.url)
        except Exception as exc:
            return stream.with_status(StreamStatus.UNREACHABLE, error=str(exc))
        status = StreamStatus.ALIVE if 200 <= response.status_code < 400 else StreamStatus.BROKEN
        return stream.with_status(
            status, status_code=response.status_code, content_type=response.content_type
        )

    def validate_many(self, streams: list[Stream]) -> list[Stream]:
        return [self.validate(stream) for stream in streams]

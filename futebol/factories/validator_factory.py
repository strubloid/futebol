from futebol.validators.legal_source_validator import LegalSourceValidator
from futebol.validators.m3u_format_validator import M3uFormatValidator
from futebol.validators.stream_url_validator import StreamUrlValidator
from futebol.validators.url_validator import UrlValidator


class ValidatorFactory:
    def url(self) -> UrlValidator:
        return UrlValidator()

    def stream_url(self) -> StreamUrlValidator:
        return StreamUrlValidator()

    def legal_source(self) -> LegalSourceValidator:
        return LegalSourceValidator()

    def m3u_format(self) -> M3uFormatValidator:
        return M3uFormatValidator()

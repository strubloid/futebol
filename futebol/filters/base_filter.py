from abc import ABC, abstractmethod

from futebol.domain.models.channel import Channel


class BaseFilter(ABC):
    @abstractmethod
    def apply(self, channels: list[Channel]) -> list[Channel]:
        raise NotImplementedError

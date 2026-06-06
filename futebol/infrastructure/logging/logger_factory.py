import logging


class LoggerFactory:
    def create(self, name: str) -> logging.Logger:
        logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
        return logging.getLogger(name)

import logging
from typing import Optional

log_formatter = logging.Formatter("%(asctime)s [%(levelname)-5.5s]  %(message)s")


class SimpleLogger:

    def __init__(self, file_path: str = "", file_log_level: int = logging.ERROR, console_log_level: int = logging.DEBUG):
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(log_formatter)
        self.console_logger: logging.Logger = logging.getLogger("tqueue_console")
        self.console_logger.setLevel(console_log_level)
        self.console_logger.addHandler(console_handler)

        self.file_logger: Optional[logging.Logger] = None
        if file_path:
            file_handler = logging.FileHandler(file_path)
            file_handler.setFormatter(log_formatter)

            self.file_logger = logging.getLogger("tqueue_file")
            self.file_logger.setLevel(file_log_level)
            self.file_logger.addHandler(file_handler)

    def debug(self, msg: str = ""):
        self.console_logger.debug(msg)
        if self.file_logger:
            self.file_logger.debug(msg)

    def info(self, msg: str = ""):
        self.console_logger.info(msg)
        if self.file_logger:
            self.file_logger.info(msg)

    def warning(self, msg: str = ""):
        self.console_logger.warning(msg)
        if self.file_logger:
            self.file_logger.warning(msg)

    def error(self, msg: str = ""):
        self.console_logger.error(msg)
        if self.file_logger:
            self.file_logger.error(msg)

    def exception(self, msg: str = ""):
        self.console_logger.exception(msg)
        if self.file_logger:
            self.file_logger.exception(msg)

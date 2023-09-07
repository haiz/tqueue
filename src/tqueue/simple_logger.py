import os
import traceback
from datetime import datetime


class SimpleLogger:
    ALL = 0
    DEBUG = 1
    INFO = 2
    WARN = 3
    ERROR = 4

    def __init__(self, file_path: str = "", file_log_level: int = 4, std_out_log_level: int = 1):
        self.file_path = ""
        self.file_log_level = file_log_level
        self.std_out_log_level = std_out_log_level
        if file_path:
            try:
                file_dir = os.path.dirname(file_path)
                os.makedirs(file_dir, exist_ok=True)
                self.file_path = file_path
            except Exception as ex:
                print(self.format(self.ERROR, str(ex)))

    def get_level_name(self, level: int) -> str:
        levels = ["ALL", "DEBUG", "INFO", "WARN", "ERROR"]
        return levels[level]

    def format(self, level: int, msg: str) -> str:
        now_str = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        level_str = self.get_level_name(level).upper()
        return f"{now_str} {level_str} {msg}"

    def _log(self, msg: str = "", level: int = 1, *, exception: Exception = None):
        if exception:
            level = self.ERROR
        if not msg and exception:
            msg = str(exception)

        log_str = self.format(level, msg)

        if self.file_path and (level == self.ERROR or level == self.file_log_level):
            try:
                with open(self.file_path, "a") as f:
                    f.write(log_str + "\n")
                    if exception:
                        traceback.print_exception(exception, file=f)
            except Exception as e:
                print(self.format(self.ERROR, str(e)))

        if level >= self.std_out_log_level:
            print(log_str)
            if exception:
                traceback.print_exception(exception)

    def debug(self, msg: str = "", *, exception: Exception = None):
        self._log(msg, self.DEBUG, exception=exception)

    def info(self, msg: str = "", *, exception: Exception = None):
        self._log(msg, self.INFO, exception=exception)

    def warn(self, msg: str = "", *, exception: Exception = None):
        self._log(msg, self.WARN, exception=exception)

    def error(self, msg: str = "", *, exception: Exception = None):
        self._log(msg, self.ERROR, exception=exception)

from abc import ABC, abstractmethod
import datetime  # 用于记录当前时间
import ctypes

log_status = {'debug': 1, 'info': 2, 'error': 3}
log_level = log_status['info']
FOREGROUND_RED = 0x0c  # 红色
FOREGROUND_WHITE = 0x0f  # 白色

STD_INPUT_HANDLE = -10
STD_OUTPUT_HANDLE = -11
STD_ERROR_HANDLE = -12
std_out_handle = ctypes.windll.kernel32.GetStdHandle(STD_OUTPUT_HANDLE)

class LoggerHandlerBase(ABC):
    """
    具体处理者角色是抽象处理者角色的子类
    """
    _next_logger = None
    level = None

    def set_next_logger(self, next_logger):
        """
        设置下一个日志类
        :param next_logger: 下一个日志类
        """
        self._next_logger = next_logger

    @abstractmethod
    def write(self, message: str):
        pass

    def log_message(self, level: int, message: str):
        if level >= self.level >= log_level:
            self.write(message)
        if self._next_logger:
            return self._next_logger.log_message(level, message)


class ConsoleLogger(LoggerHandlerBase):
    def __init__(self, level: int):
        self.level = level

    def write(self, message: str):
        ctypes.windll.kernel32.SetConsoleTextAttribute(std_out_handle, FOREGROUND_WHITE)
        print(f'[{datetime.datetime.now()}] {message}')


class ErrorLogger(LoggerHandlerBase):
    def __init__(self, level: int):
        self.level = level

    def write(self, message: str):
        ctypes.windll.kernel32.SetConsoleTextAttribute(std_out_handle, FOREGROUND_RED)
        print(f'[{datetime.datetime.now()}] Error: {message}')
        ctypes.windll.kernel32.SetConsoleTextAttribute(std_out_handle, FOREGROUND_WHITE)


def get_logger():
    info_logger = ConsoleLogger(log_status['info'])
    error_logger = ErrorLogger(log_status['error'])
    error_logger.set_next_logger(info_logger)
    return error_logger


def set_log_level(level: int):
    global log_level
    log_level = level


def get_log_level():
    global log_level
    return log_level


if __name__ == '__main__':
    logger = get_logger()
    logger.log_message(log_status['info'], 'This is an information.')
    print('--')
    logger.log_message(log_status['error'], 'This is an error information.')

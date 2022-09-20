from abc import ABC, abstractmethod
import datetime  # 用于记录当前时间

log_status = {'debug': 1, 'info': 2, 'error': 3}
log_level = log_status['info']


class LoggerHandlerBase(ABC):
    """
    具体处理者角色是抽象处理者角色的子类
    """
    _next_logger = None
    level = None

    def set_next_logger(self, next_logger):
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
        print(f'[{datetime.datetime.now()}] {message}')


class ErrorLogger(LoggerHandlerBase):
    def __init__(self, level: int):
        self.level = level

    def write(self, message: str):
        print(f'[{datetime.datetime.now()}] {message}')


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

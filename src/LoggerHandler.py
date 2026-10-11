import yaml  # 用于加载配置
from Utils import get_resource, get_config  # 用于获取静态资源
from abc import ABC, abstractmethod
import datetime  # 用于记录当前时间
import os  # 用于拼接日志路径
import sys  # 用于判断是否为打包后的 exe
from termcolor import cprint  # 用于使输出的字符附带颜色的样式

config = get_config()
log_status = {'debug': 1, 'info': 2, 'error': 3}
log_level = log_status[config['log_level']]


class LoggerHandlerBase(ABC):
    """
    具体处理者角色是抽象处理者角色的子类
    """
    _next_logger = None
    level = None
    done = None

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
            self.done = True
        if not self.done and self._next_logger:
            return self._next_logger.log_message(level, message)


class DebugLogger(LoggerHandlerBase):
    def __init__(self, level: int):
        self.level = level

    def write(self, message: str):
        cprint(f'[{"{:%Y-%m-%d %H:%M:%S}".format(datetime.datetime.now())}] {message}', 'dark_grey')


class ConsoleLogger(LoggerHandlerBase):
    def __init__(self, level: int):
        self.level = level

    def write(self, message: str):
        cprint(f'[{"{:%Y-%m-%d %H:%M:%S}".format(datetime.datetime.now())}] {message}')


class ErrorLogger(LoggerHandlerBase):
    def __init__(self, level: int):
        self.level = level

    def write(self, message: str):
        cprint(f'[{"{:%Y-%m-%d %H:%M:%S}".format(datetime.datetime.now())}] {message}', 'red')


def get_logger():
    debug_logger = DebugLogger(log_status['debug'])
    info_logger = ConsoleLogger(log_status['info'])
    error_logger = ErrorLogger(log_status['error'])
    error_logger.set_next_logger(info_logger)
    info_logger.set_next_logger(debug_logger)
    return error_logger


def set_log_level(level: int):
    global log_level
    log_level = level


def get_log_level():
    global log_level
    return log_level


# ── 文件日志（本地留证据，离线失败时用它排查）────────────────────
_LOG_PATH = None


def _log_path():
    global _LOG_PATH
    if _LOG_PATH is None:
        try:
            if getattr(sys, 'frozen', False):
                # 打包成 exe 后 __file__ 在临时解压目录里，日志要跟着 exe 走
                root = os.path.dirname(os.path.abspath(sys.executable))
            else:
                root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            d = os.path.join(root, 'logs')
            os.makedirs(d, exist_ok=True)
            _LOG_PATH = os.path.join(d, 'connector-{:%Y-%m-%d}.log'.format(datetime.datetime.now()))
        except Exception:
            _LOG_PATH = ''
    return _LOG_PATH


def _write_file(message: str, status: int):
    if status < log_level:
        return
    path = _log_path()
    if not path:
        return
    try:
        ts = '{:%Y-%m-%d %H:%M:%S}'.format(datetime.datetime.now())
        with open(path, 'a', encoding='utf-8') as f:
            f.write(f'[{ts}] {message}\n')
    except Exception:
        pass


def log(message: str, status: int, printable: bool = True):
    """日志记录

    :param message: 消息
    :param status: 输入日志的级别
    :param printable: 是否打印输出
    :return: 包含时间头的消息
    """
    _write_file(message, status)
    logger = get_logger()
    if printable:
        logger.log_message(status, message)
        return f'[{"{:%Y-%m-%d %H:%M:%S}".format(datetime.datetime.now())}] {message}'
    else:
        return f'[{"{:%Y-%m-%d %H:%M:%S}".format(datetime.datetime.now())}] {message}'


def debug(message: str, printable: bool = True):
    """调试日志记录

    :param printable: 是否打印输出
    :param message: 消息
    :return: 包含时间头的消息
    """
    return log(message, log_status['debug'], printable)


def info(message: str, printable: bool = True):
    """日志记录

    :param printable: 是否打印输出
    :param message: 消息
    :return: 包含时间头的消息
    """
    return log(message, log_status['info'], printable)


def error(message: str, printable: bool = True):
    """错误日志记录

    :param printable: 是否打印输出
    :param message: 消息
    :return: 包含时间头的消息
    """
    return log(message, log_status['error'], printable)

import os  # 用于系统查看等操作
import sys  # 用于系统查看等操作


def get_resource(relative_path: str):
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

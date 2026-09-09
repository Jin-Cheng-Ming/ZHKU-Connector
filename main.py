# main.py - 打包入口文件
import sys
import os

# 判断是否被打包
if getattr(sys, 'frozen', False):
    # 打包后，exe 会解压到 _MEIPASS 临时目录
    base_path = sys._MEIPASS
else:
    # 开发环境
    base_path = os.path.dirname(os.path.abspath(__file__))

# 添加 src 目录到模块搜索路径
src_path = os.path.join(base_path, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# 添加根目录
if base_path not in sys.path:
    sys.path.insert(0, base_path)

from Connector import Connector

if __name__ == '__main__':
    connector = Connector()
    connector.run()
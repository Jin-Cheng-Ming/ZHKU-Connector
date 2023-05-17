import os  # 用于系统查看等操作
import sys  # 用于系统查看等操作
import pickle  # 用户持久化文件

network_credentials_file_name = 'network_credentials.pkl'
network_credentials_file_path = os.path.expanduser('~') + os.sep + network_credentials_file_name
try:
    with open(network_credentials_file_path, 'rb') as f:
        credentials = pickle.load(f)
except:
    credentials = None


def get_resource(relative_path: str):
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def remember(i_user: dict, i_setting: dict):
    """
    保存登录信息，包括用户ID和密码，还有登录的功能设置
    """
    try:
        with open(network_credentials_file_path, 'wb') as f:
            pickle.dump({'login_info': i_user, 'setting_info': i_setting}, f)
            return True
    except:
        return False


def remove():
    """
    保存登录信息，包括用户ID和密码，还有登录的功能设置
    """
    try:
        # 删除保存的信息，没有的
        resource = get_resource(network_credentials_file_name)
        os.remove(resource)
        return True
    except:
        return False


def get_remembered_credentials():
    return credentials

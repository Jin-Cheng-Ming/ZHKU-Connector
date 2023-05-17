import os  # 用于系统查看等操作
import sys  # 用于系统查看等操作
import pickle  # 用户持久化文件
import yaml  # 用于加载配置

network_credentials_file_name = 'network_credentials.pkl'
network_credentials_file_path = os.path.expanduser('~') + os.sep + network_credentials_file_name


def get_resource(relative_path: str):
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def remember_login(i_user: dict, i_setting: dict):
    """
    保存登录信息，包括用户ID和密码，还有登录的功能设置
    """
    try:
        with open(network_credentials_file_path, 'wb') as f:
            pickle.dump({'login_info': i_user, 'setting_info': i_setting}, f)
            return True
    except:
        return False


def remove_remembered_credentials():
    """
    保存登录信息，包括用户ID和密码，还有登录的功能设置
    """
    try:
        # 删除保存的信息，没有的
        os.remove(network_credentials_file_path)
        return True
    except:
        return False


def get_remembered_credentials():
    """
    删除已经保存的登录信息
    """
    try:
        with open(network_credentials_file_path, 'rb') as f:
            credentials = pickle.load(f)
            return credentials
    except:
        return None


def get_config():
    """
    获取配置信息
    """
    try:
        with open(get_resource('config.yml'), 'r', encoding='utf-8') as f:
            config = yaml.load(f.read(), Loader=yaml.FullLoader)
            return config
    except:
        return None

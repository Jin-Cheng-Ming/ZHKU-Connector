import os
import sys
import pickle
import yaml

network_credentials_file_name = 'network_credentials.pkl'
network_credentials_file_path = os.path.expanduser('~') + os.sep + network_credentials_file_name


def get_resource(relative_path: str):
    """获取资源文件路径（兼容打包和开发环境）"""
    if getattr(sys, 'frozen', False):
        # 打包后，资源在 _MEIPASS 目录
        base_path = sys._MEIPASS
    else:
        # 开发环境，在项目根目录
        base_path = os.path.dirname(os.path.abspath(__file__))
        # 如果当前在 src 目录，回到根目录
        if os.path.basename(base_path) == 'src':
            base_path = os.path.dirname(base_path)
    return os.path.join(base_path, relative_path)


def remember_login(i_user: dict, i_setting: dict):
    """
    保存登录信息，包括用户ID和密码，还有登录的功能设置
    """
    try:
        if 'user_id' in i_user and isinstance(i_user['user_id'], tuple):
            i_user['user_id'] = i_user['user_id'][0]
        with open(network_credentials_file_path, 'wb') as f:
            pickle.dump({'login_info': i_user, 'setting_info': i_setting}, f)
            return True
    except:
        return False


def remove_remembered_credentials():
    """
    删除已经保存的登录信息
    """
    try:
        os.remove(network_credentials_file_path)
        return True
    except:
        return False


def get_remembered_credentials():
    """
    获取已保存的登录信息
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
        config_path = get_resource('config.yml')
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.load(f.read(), Loader=yaml.FullLoader)
            return config
    except Exception as e:
        print(f"加载配置文件失败: {e}")
        return None
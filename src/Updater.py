import yaml  # 用于加载配置
from Utils import get_resource, get_config  # 用于获取静态资源
from github import Github  # 从GitHub仓库中获取更新
from github import AppAuthentication  # 从GitHub仓库中获取更新

# 当前版本
config = get_config()
current_version = config['current_version']


def set_current_version(version: str):
    global current_version
    current_version = version


def fetch():
    print('\r正在检查更新...', end='')
    try:
        with open(get_resource('zhku-connector.private-key.pem')) as private_key_file:
            private_key = private_key_file.read()
        # 创建一个实例
        authentication = AppAuthentication(app_id=config['app_id'],
                                           private_key=private_key,
                                           installation_id=config['installation_id'])
        instance = Github(app_auth=authentication)
        repo = instance.get_repo("Jin-Cheng-Ming/ZHKU-Connector")
        # 获取项目仓库:
        if repo.get_latest_release().tag_name > current_version:
            print('\r有可用的更新：{}'.format(current_version, repo.get_latest_release().tag_name))
            print('更新内容({})：\n{}'.format(
                "{:%Y-%m-%d}".format(repo.get_latest_release().published_at), repo.get_latest_release().body))
            print('附件：')
            for item in repo.get_latest_release().assets:
                print('{} : {}'.format(item.name, item.browser_download_url))
        else:
            print('\r已是最新版本！   ')
    except:
        print('\r获取更新失败！   ')

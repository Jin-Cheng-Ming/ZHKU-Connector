import yaml  # 用于加载配置
from github import Github  # 从GitHub仓库中获取更新
from github import AppAuthentication  # 从GitHub仓库中获取更新

with open('config.yml', 'r', encoding='utf-8') as f:
    config = yaml.load(f.read(), Loader=yaml.FullLoader)
with open('zhku-connector.private-key.pem') as private_key_file:
    private_key = private_key_file.read()

# 当前版本
current_version = config['current_version']


def set_current_version(version: str):
    global current_version
    current_version = version


# d36ec0f16038514850c0b13d62b66388cd259b96

def update():
    print('正在检查更新...')
    try:
        # 创建一个实例
        authentication = AppAuthentication(app_id=config['app_id'],
                                           private_key=private_key,
                                           installation_id=config['installation_id'])
        instance = Github(app_auth=authentication)
        repo = instance.get_repo("Jin-Cheng-Ming/ZHKU-Connector")
        # 获取项目仓库:
        if repo.get_latest_release().tag_name > current_version:
            print('有可用的更新：{} => {}'.format(current_version, repo.get_latest_release().tag_name))
            print('更新内容({})：\n{}'.format(
                "{:%Y-%m-%d}".format(repo.get_latest_release().published_at),
                repo.get_latest_release().body
            ))
            print('附件：')
            for item in repo.get_latest_release().assets:
                print('{} : {}'.format(item.name, item.browser_download_url))
        else:
            print('当前已是最新版本')
    except:
        print('获取更新失败')


if __name__ == '__main__':
    update()

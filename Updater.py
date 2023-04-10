from github import Github  # 从GitHub仓库中获取更新

# 当前版本
current_version = ''
# 仓库所有者的GitHub访问令牌
access_token = "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"


def set_current_version(version: str):
    global current_version
    current_version = version


def update():
    print('正在检查更新...')
    try:
        # 创建一个实例
        instance = Github(access_token)
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

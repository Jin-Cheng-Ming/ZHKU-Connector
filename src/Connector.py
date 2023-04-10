# Distributed under the MIT license, see LICENSE
import yaml  # 用于加载配置
import requests  # 用于向网页发送post请求
import subprocess  # 用于在程序中执行cmd命令
from pyquery import PyQuery  # 用于解析数据
import time  # 用于设置延时
import getpass  # 用于避免密码的直接输出
import random  # 用于计算随机数
import platform  # 用于查看系统属于哪个平台
from progress.spinner import Spinner  # 用于说明检测状态
import os  # 用于暂停程序
from Utils import get_resource  # 用于获取静态资源
from termcolor import cprint  # 用于使输出的字符附带颜色的样式
from LoggerHandler import debug, info, error  # 日志
import Updater  # 用于获取程序更新信息

with open(get_resource('config.yml'), 'r', encoding='utf-8') as f:
    config = yaml.load(f.read(), Loader=yaml.FullLoader)
printable = config['printable']
current_version = config['current_version']


def welcome():
    """ 启动横幅

    :return: 包含字符画的横幅
    """
    cprint(f'''
      _________  ____  ____  ___  _____/ /_____  _____
     / ___/ __ \/ __ \/ __ \/ _ \/ ___/ __/ __ \/ ___/
    / /__/ /_/ / / / / / / /  __/ /__/ /_/ /_/ / /    
    \___/\____/_/ /_/_/ /_/\___/\___/\__/\____/_/     
    ::ZHKU connector::            [version {current_version}]    
    ''', 'green')
    cprint(f'''
    - github: https://github.com/Jin-Cheng-Ming/ZHKU-Connector
    - last update: 2023-04
    ''', 'dark_grey')


def info_input():
    """ 设置登录相关信息
    包括登录地址，账号和密码

    :return: 登录相关信息。hostname：登录地址；user_id：账号；password：密码；
    """
    hostname = input(info('请输入登录地址：', printable))
    if len(hostname) > 0:
        if 'http' in hostname:
            hostname = hostname[hostname.index('://') + 3:]
    else:
        info('使用默认登录地址：1.1.1.1')
        hostname = '1.1.1.1'
    user_id = input(info('请输入账号：', printable)),
    password = getpass.getpass(info('请输入密码：', printable))
    login_info_dist = {
        'hostname': hostname,
        'user_id': user_id,
        'password': password
    }
    return login_info_dist


def setting_input():
    agent_input = input(info('请设置登录的用户代理方式  1）PC-默认  2）Mobile：', printable))
    if len(agent_input) == 0:
        agent = 'pc'
        info('使用默认用户代理登录：PC')
    else:
        while len(agent_input) > 1 or not agent_input.isdigit():
            agent_input = input(info('设置代理有误，请重新选择  1）PC-默认  2）Mobile：', printable))
        if agent_input == '2':
            info('使用移动端代理登录')
            agent = 'mobile'
        else:
            info('使用PC端代理登录')
            agent = 'pc'

    auto_login_input = input(info('是否开启账号自动登录（Y-默认/N）：', printable))
    if len(auto_login_input) > 0 and any(res in auto_login_input for res in ['n', 'N']):
        auto = False
    else:
        auto = True

    internet_quick_test_input = input(info('是否开启快速互联网连通测试（Y-默认/N）：', printable))
    if len(internet_quick_test_input) > 0 and any(res in internet_quick_test_input for res in ['n', 'N']):
        quick = False
    else:
        quick = True

    setting_info_dist = {
        'user_agent': agent,
        'auto_login': auto,
        'internet_quick_test': quick,
    }
    return setting_info_dist


def get_redirect_url(url: str):
    """ 返回指定URL请求后重定向的URL

    :param url: 指定URL
    :return: 重定向后的地址
    """
    # 请求网页
    try:
        debug('获取真实的登录地址')
        response = requests.get(url)
        debug('检测是否发生重定向')
        if response.url == url:
            debug('登录地址未重定向')
        else:
            debug('登录地址已重定向')
            debug(f'登录地址重定向地址为：{response.url}')
        # 返回重定向后的网址
        return response.url
    except:
        error('登录请求失败')
        return None


def get_connect_status(url: str):
    """ 返回连接状态

    :return: 连接状态
    """
    # 请求网页
    response = requests.get(url)
    return response.status_code


def connect_status_test(host_name: str):
    """ 检测能否ping通网络

    :param host_name: 主机名
    :return: 连接状态：为0时，网络连接正常；为1时，网络连接失败
    """
    command = ''
    debug('执行检测连接命令……')
    if platform.system() == 'Windows':
        command = 'ping -n 2 %s' % host_name
    elif platform.system() == 'Linux':
        command = 'ping -c 2 %s' % host_name
    debug(f'> {command}')
    network_state = subprocess.run(command, stdout=subprocess.PIPE, shell=True).returncode
    if network_state == 0:
        debug('执行结果：连接正常')
        return True
    else:
        debug('执行结果：连接失败')
        return False


def internet_connect_status_test(internet_quick_test: bool = True):
    """ 从备选的互联网列表中测试连接状态

    :param: internet_quick_test: 是否快速互联网连接测试
    :return: 是否有互联网连接
    """
    internet_host_list = ['www.zhku.edu.cn', 'baidu.com', 'douyin.com']

    debug('检测是否有互联网连接……')
    if internet_quick_test:
        host = random.choice(internet_host_list)
        if connect_status_test(host):
            debug('检测互联网连接完毕：互联网连接正常')
            return True
    else:
        for host in internet_host_list:
            # 连接正常
            if connect_status_test(host):
                debug('检测互联网连接完毕：互联网连接正常')
                return True
    debug('检测互联网连接完毕：无互联网连接')
    return False


def login_address_connect_status_test(url: str):
    """ 检测登录地址是否连接正常

    :param url: 登录地址
    :return: 是否登录地址连接正常
    """
    debug(f'当前设置的登录地址为：{url}')
    debug('检测登录地址是否连接正常……')
    host = url[url.index('://') + 3:]
    if connect_status_test(host):
        debug('登录地址连接正常')
        return True
    else:
        debug('登录地址连接失败')
        return False


def login(user_id, password, url, user_agent='pc'):
    """ 登录

    :param user_id: 账号
    :param password:  密码
    :param url: 登录地址
    :param user_agent: 用户代理，可以选择pc或者mobile
    :return: 是否登录成功
    """
    # 请求数据
    data = {
        "auth_type": "0",
        "isBindMac1": "0",
        "pageid": "1",
        "templatetype": "1",
        "listbindmac": "0",
        "recordmac": "0",
        "isRemind": "0",
        "loginTimes": "",
        "groupId": "",
        "distoken": "",
        "echostr": "",
        "url": url,
        "isautoauth": "",
        "notice_pic_float": "/portal/uploads/pc/hb_pay/images/rrs_bg.jpg",
        "userId": user_id,
        "passwd": password,
        "remInfo": "on"
    }
    # 添加请求头
    agent_header = {
        'pc': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/110.0'
        },
        'mobile': {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 11_0 like Mac OS X) '
                          'AppleWebKit/604.1.38 (KHTML, like Gecko) Version/11.0 Mobile/15A372 Safari/604.1'
        }
    }
    # 设置登录状态
    login_result_status = False
    info('正在登录中……')
    login_address = get_redirect_url(url)
    try:
        # 对校园网登录网址发送请求(执行登录操作) 并获取请求到的页面数据
        res = requests.post(login_address, data=data, headers=agent_header[user_agent]).text
        # 使用pyquery初始化数据
        doc = PyQuery(res)
        # 获取登录结果状态
        for act in doc('#act').items():
            if act.attr('value') == 'LOGINSUCC':
                login_result_status = True
        # 获取登录结果信息
        for error_msg in doc('#errMessage').items():
            # 通过value属性取出错误信息
            info(error_msg.attr('value'))
        return login_result_status
    except:
        error('网络连接失败')
        return False


def auto_login(user_id, password, url, user_agent='pc'):
    spinner = Spinner(info('持续监测中 ', printable))
    while True:
        internet_connect = internet_connect_status_test(setting_info['internet_quick_test'])
        # 互联网连接异常
        if not internet_connect:
            print('')
            error('互联网无法连接，执行自动登录操作')
            # 执行登录校园网方法 获取登录状态
            login_status = login(user_id, password, url, user_agent)
            if is_login(login_status):
                info('自动登录成功')
            else:
                error('自动登录失败')
            spinner = Spinner(info('持续监测中 ', printable))
        # 间隔5秒执行监测
        for i in range(5):
            spinner.next()
            time.sleep(1)


def is_login(login_status: bool):
    """
    根据登录返回的结果检查登录是否成功
    """
    return login_status is True


def exit_with_confirmation():
    """
    退出程序，退出前暂停一下，按任意键关闭后将关闭程序
    """
    if platform.system() == 'Windows':
        os.system("pause")
    exit(0)


if __name__ == '__main__':
    welcome()
    # 获取更新
    Updater.update()
    login_info = info_input()
    setting_info = setting_input()

    info('网络链路检测......')
    login_url = f"http://{login_info['hostname']}"
    login_connect = login_address_connect_status_test(login_url)
    internet_connect = internet_connect_status_test(setting_info['internet_quick_test'])
    info(
        f'网络链路检测完毕：'
        f'登录地址{"访问正常" if login_connect else "无法连接"}，互联网{"访问正常" if internet_connect else "无法连接"}'
    )

    if login_connect:
        # 登录地址正常访问，检测账号是否可以正常登录，并检测互联网连接
        info('登录地址访问正常，检测账号能否正常登录……')
        # fixme 之前已经认证登录了，再使用不正确的账号密码会提示账号登录正常的错误
        # 设置账号登录状态
        login_status = login(login_info['user_id'], login_info['password'], login_url, setting_info['user_agent'])
        if is_login(login_status):
            if setting_info['auto_login']:
                # 后台持续监测
                info('账号登录正常，该账号将用于自动登录')
                input(info("持续监测互联网连接状态，请按任意键确认...", printable))
                auto_login(login_info['user_id'], login_info['password'], login_url, setting_info['user_agent'])
            else:
                error('该设备已登录')
        else:
            error('登录失败，请检查账号信息是否正确，再重启程序试试？')
    else:
        # 登录地址无法连接，提示接入校园网
        error('登录地址访问失败，请检查校园网连接状态并输入正确的登录地址')

    exit_with_confirmation()

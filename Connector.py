# Distributed under the MIT license, see LICENSE
import requests  # 用于向网页发送post请求
import subprocess  # 用于在程序中执行cmd命令
import datetime  # 用于记录当前时间
from pyquery import PyQuery  # 用于解析数据
import time  # 用于设置延时

internet_host_list = ['www.baidu.com', 'www.jd.com', 'www.taobao.com', 'www.douyin.com', 'www.ele.me']


def welcome(version: str):
    """ 启动横幅

    :param version: 版本号
    :return: 包含字符画的横幅
    """
    print(f'''
      _________  ____  ____  ___  _____/ /_____  _____
     / ___/ __ \/ __ \/ __ \/ _ \/ ___/ __/ __ \/ ___/
    / /__/ /_/ / / / / / / /  __/ /__/ /_/ /_/ / /    
    \___/\____/_/ /_/_/ /_/\___/\___/\__/\____/_/     
    ::ZHKU connector::              version {version}              
    ''')


def get_redirect_url(url: str):
    """ 返回指定URL请求后重定向的URL

    :param url: 指定URL
    :return: 重定向后的地址
    """
    # 请求网页
    response = requests.get(url)
    log('检测是否发生重定向')
    if response.url == url:
        log('登录地址未重定向')
    else:
        log(f'登录地址已重定向')
        log(f'登录地址重定向地址为：{response.url}')

    # 返回重定向后的网址
    return response.url


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
    log('执行检测连接命令……')
    # 向指定的地址发送2个指定的 ECHO 数据包（默认值为 4）
    command = 'ping -n 2 %s' % host_name
    log('cmd> ' + command)
    network_state = subprocess.run(command, stdout=subprocess.PIPE, shell=True).returncode
    if network_state == 0:
        log('执行结果：连接正常')
        return True
    else:
        log('执行结果：连接失败')
        return False


def internet_connect_status_test():
    """ 从备选的互联网列表中测试连接状态

    :return: 是否有互联网连接
    """
    global internet_host_list
    log('检测是否有互联网连接……')
    for host in internet_host_list:
        # 连接正常
        if connect_status_test(host):
            log('检测互联网连接完毕：互联网连接正常')
            return True
    log('检测互联网连接完毕：无互联网连接')
    return False


def login_address_connect_status_test(url: str):
    """ 检测登录地址是否连接正常

    :param url: 登录地址
    :return: 是否登录地址连接正常
    """
    log('当前设置的登录地址为：' + url)
    log('检测登录地址是否连接正常……')
    host = url[url.index('://') + 3:]
    if connect_status_test(host):
        log('登录地址连接正常')
        return True
    else:
        log('登录地址连接失败')
        return False


def log(message: str, printed: bool = True):
    """日志记录

    :param printed: 是否打印输出
    :param message: 消息
    :return: 包含时间头的消息
    """
    if printed:
        print(f'[{datetime.datetime.now()}]: {message}')
        return f'[{datetime.datetime.now()}]: {message}'
    else:
        return f'[{datetime.datetime.now()}]: {message}'


def login(user_id, password, url):
    """ 登录

    :param user_id: 账号
    :param password:  密码
    :param url: 登录地址
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
    # 设置登录状态
    login_result_status = False
    log('正在登录中……')
    log('获取真实的登录地址')
    login_address = get_redirect_url(url)
    try:
        # 对校园网登录网址发送请求(执行登录操作) 并获取请求到的页面数据
        res = requests.post(login_address, data=data).text
        # 使用pyquery初始化数据
        doc = PyQuery(res)
        # 获取登录结果状态
        for act in doc('#act').items():
            if act.attr('value') == 'LOGINSUCC':
                login_result_status = True
        # 获取登录结果信息
        for error_msg in doc('#errMessage').items():
            # 通过value属性取出错误信息
            log(error_msg.attr('value'))
        return login_result_status
    except:
        log('网络连接失败')
        return False


def info_input():
    """ 设置登录相关信息
    包括登录地址，账号和密码

    :return: 登录相关信息。hostname：登录地址；user_id：账号；password：密码；
    """
    info = {'hostname': input(log('请输入登录地址： ', False)),
            'user_id': input(log('请输入账号： ', False)),
            'password': input(log('请输入密码： ', False))
            }
    return info


if __name__ == '__main__':
    welcome('1.0')
    info = info_input()
    protocol = 'http://'
    login_url = protocol + info['hostname']
    login_connect = login_address_connect_status_test(login_url)
    internet_connect = internet_connect_status_test()
    # 后台持续监测
    log(f'网络链路检测完毕：登录地址{"访问正常" if login_connect else "无法连接"}，互联网{"访问正常" if internet_connect else "无法连接"}')
    # 设置账号登录状态
    login_status = False
    if not login_connect:
        # 登录地址无法连接，提示接入校园网
        log('登录地址访问失败，请检查校园网连接状态并输入正确的登录地址')
        exit(0)
    else:
        # 登录地址正常访问，检测账号是否可以正常登录，并检测互联网连接
        log('登录地址访问正常，检测账号能否正常登录……')
        login_status = login(info['user_id'], info['password'], login_url)
        if login_status:
            log('账号登录正常，该账号将用于自动登录')
            log('1分钟后持续将持续监测互联网连接状态')
            time.sleep(60)
            while True:
                internet_connect = internet_connect_status_test()
                # 互联网连接异常
                if not internet_connect:
                    log('互联网无法连接，执行自动登录操作')
                    log('正在登录中……')
                    # 执行登录校园网方法 获取登录状态
                    login(info['user_id'], info['password'], login_url)
                # 间隔15秒执行监测
                time.sleep(15)
        else:
            log('账号登录失败，检查账号信息是否正确，再试试？')
            exit(0)

# Distributed under the MIT license, see LICENSE
import os # 用于程序暂停
import requests  # 用于向网页发送post请求
from pyquery import PyQuery  # 用于解析数据
import time  # 用于设置延时
import getpass  # 用于避免密码的直接输出
from progress.spinner import Spinner  # 用于说明检测状态
from Utils import *  # 用于获取或保存静态资源
from termcolor import cprint, colored  # 用于使输出的字符附带颜色的样式
from LoggerHandler import debug, info, error  # 日志
import Updater  # 用于获取程序更新信息
import func_timeout  # 用户等待用户输入


class Connector:
    config = get_config()
    agent_header = {
        'pc': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/110.0'
        },
        'mobile': {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 11_0 like Mac OS X) '
                          'AppleWebKit/604.1.38 (KHTML, like Gecko) Version/11.0 Mobile/15A372 Safari/604.1'
        }
    }

    def __init__(self):
        self.printable = Connector.config['printable']
        self.detect_captive_portal_url = Connector.config['detect_captive_portal_url']
        self.captive_portal = Connector.config['login_page']
        self.agent = 'pc'
        self.is_auto_login = True
        self.user_id = ''
        self.password = ''
        self.remember = ''

    @staticmethod
    def print_welcome_banner():
        """ 启动横幅

        :return: 包含字符画的横幅
        """
        cprint(f'''
          _________  ____  ____  ___  _____/ /_____  _____
         / ___/ __ \/ __ \/ __ \/ _ \/ ___/ __/ __ \/ ___/
        / /__/ /_/ / / / / / / /  __/ /__/ /_/ /_/ / /    
        \___/\____/_/ /_/_/ /_/\___/\___/\__/\____/_/     
        ::ZHKU connector::            [version {Connector.config['current_version']}]    
        ''', 'green')
        cprint(f'''
        - github: {Connector.config['home_page']}
        - last update: {Connector.config['last_update']}
        ''', 'dark_grey')

    def detect_captive_portal(self):
        """
        尝试访问一个不会返回实际内容的URL，如果网络正常，应该返回204 No Content。
        如果返回其他状态码或者重定向，可能意味着存在Captive Portal。
        """
        try:
            response = requests.get(self.detect_captive_portal_url, allow_redirects=False)

            if response.status_code == 204:
                # 正常情况，没有Captive Portal
                return False
            elif response.is_redirect:
                # 检测到重定向，可能是Captive Portal
                self.captive_portal = response.headers.get('Location')
                return True
            else:
                # 其他未知情况
                return None
        except requests.RequestException as e:
            # 网络错误或其他异常
            print(f"Request error: {e}")
            return None

    def setting_input(self):
        agent_input = input(info('请设置登录的浏览器设备  1）个人电脑-默认  2）移动设备：', self.printable))
        if len(agent_input) == 0:
            self.agent = 'pc'
            info('默认以个人电脑端登录')
        else:
            while len(agent_input) > 1 or not agent_input.isdigit():
                agent_input = input(info('设置代理有误，请重新选择  1）个人电脑-默认  2）移动设备：', self.printable))
            if agent_input == '2':
                info('将使用移动设备端登录')
                self.agent = 'mobile'
            else:
                info('将使用个人电脑端登录')
                self.agent = 'pc'

    def account_input(self):
        """ 设置登录相关信息
        包括登录地址，账号和密码

        :return: 登录相关信息。hostname：登录地址；user_id：账号；password：密码；
        """
        self.user_id = input(info('请输入账号：', self.printable)),
        self.password = getpass.getpass(info('请输入密码：', self.printable))

    def login_info_input(self):
        """
        输入用户ID和密码，还有登录的功能设置
        """
        self.account_input()
        self.setting_input()
        i_user = {
            'hostname': self.captive_portal,
            'user_id': self.user_id,
            'password': self.password
        }
        i_setting = {
            'user_agent': self.agent,
            'auto_login': self.is_auto_login,
        }
        return i_user, i_setting

    def login_address_connect_status_test(self):
        """ 检测登录地址是否连接正常

        :return: 是否登录地址连接正常
        """
        debug('检测登录地址是否连接正常……')
        portal = self.detect_captive_portal()
        if portal is True or portal is None:
            debug('登录地址获取成功')
            debug(f'强制登录页为：{self.captive_portal}')
            return True
        else:
            debug('登录地址获取失败')
            return False

    def login(self):
        """ 登录

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
            "url": self.captive_portal,
            "isautoauth": "",
            "notice_pic_float": "/portal/uploads/pc/hb_pay/images/rrs_bg.jpg",
            "userId": self.user_id,
            "passwd": self.password,
            "remInfo": "on"
        }
        # 设置登录状态
        login_result_status = False
        info(colored(f'[{self.user_id[0]}]', 'light_cyan') + '正在登录中……')
        login_address = self.captive_portal
        try:
            # 对校园网登录网址发送请求(执行登录操作) 并获取请求到的页面数据
            res = requests.post(login_address, data=data, headers=Connector.agent_header[self.agent]).text
            # 使用pyquery初始化数据
            doc = PyQuery(res)
            # 获取登录结果状态
            for act in doc('#act').items():
                if act.attr('value') == 'LOGINSUCC':
                    login_result_status = True
            # 获取登录结果信息
            for error_msg in doc('#errMessage').items():
                # 通过value属性取出错误信息
                info(colored(error_msg.attr('value'), on_color="on_dark_grey"))
            return login_result_status
        except:
            error('登录请求出错，请检查网络环境是否正确')
            return None

    def remember_me(self):
        info('保存登录信息，下次启动程序可以自动登录。')
        is_remember_input = input(
            info('记住登录信息吗？ Y）同意-默认  N）不同意/清除：', self.printable))
        is_remember_login = len(is_remember_input) == 0 or any(res in is_remember_input for res in ['y', 'Y'])
        if is_remember_login:
            login_info = {
                'hostname': self.captive_portal,
                'user_id': self.user_id,
                'password': self.password
            }
            setting_info = {
                'user_agent': self.agent,
                'auto_login': self.is_auto_login,
            }
            if remember_login(login_info, setting_info):
                info('登录信息已保存在本地')
            else:
                error('保存失败，请稍后重试')

    def auto_login(self):
        spinner = Spinner(info('持续监测中 ', self.printable))
        while True:
            # 互联网连接异常
            captive = self.detect_captive_portal()
            if captive or captive is None:
                spinner = Spinner('\r')
                error('强制主页，登录以继续，将执行自动登录')
                # 执行登录校园网方法 获取登录状态
                login_status = self.login()
                if login_status is True:
                    info('自动登录成功')
                else:
                    error('自动登录失败')
                spinner = Spinner(info('持续监测中 ', self.printable))
            # 间隔5秒执行监测
            for i in range(5):
                spinner.next()
                time.sleep(1)

    @func_timeout.func_set_timeout(5)
    def ask_is_edit_login_info(self, credentials):
        """
        设置5秒内没有输入的话加载配置
        """

        return input('保存有登录信息'
                     + colored(f'[{credentials["login_info"]["user_id"][0]}]', 'light_cyan')
                     + '，5秒后加载这个配置（回车清除记录）')

    def run(self):
        # 欢迎
        self.print_welcome_banner()
        try:
            code = requests.get(self.detect_captive_portal_url, allow_redirects=False).status_code
        except:
            error('无网络连接，请检查网络连接状态后重试')
            os.system("pause")
            return
        # 获取本地记录，如果有则在等待一定时间过后自动使用
        credentials = get_remembered_credentials()
        if credentials:
            try:
                self.remember = self.ask_is_edit_login_info(credentials)
            except:
                # 回车中断，使用新的自定义登录
                print('\n没有输入，默认使用上次的登录配置')
                self.remember = 'use_last'
            if self.remember != 'use_last':
                remove_remembered_credentials()
                info('本地记录已清除，请重新输入登录信息')
                login_info, setting_info = self.login_info_input()
            else:
                login_info, setting_info = credentials['login_info'], credentials['setting_info']
        else:
            login_info, setting_info = self.login_info_input()
        self.user_id = login_info['user_id']
        self.password = login_info['password']
        self.agent = setting_info['user_agent']

        # 网络情况检查
        if code is not None and code != 204:
            info("未连接到互联网，检测登录主页中......")
            login_address_connect = self.login_address_connect_status_test()
            while not login_address_connect:
                # 登录地址无法连接，提示接入校园网
                error('登录主页访问失败，请检查网络环境是否正确')
                login_address_connect = self.login_address_connect_status_test()
                time.sleep(10)

        while self.login() is not True:
            error('登录失败，请检查登录信息是否正确并重新输入')
            self.account_input()

        info('账号登录正常')
        if self.remember != 'use_last':
            self.remember_me()
        # 更新
        Updater.fetch()

        self.auto_login()


if __name__ == '__main__':
    connector = Connector()
    connector.run()

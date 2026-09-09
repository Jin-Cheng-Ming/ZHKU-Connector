# Distributed under the MIT license, see LICENSE
import os
import requests
import json
import re
import socket
import time
import getpass

# 兼容打包环境的 spinner 导入
try:
    from progress.spinner import Spinner
except (ImportError, ModuleNotFoundError):
    # 简单的 spinner 替代实现
    class Spinner:
        def __init__(self, message, **kwargs):
            self.message = message
            self.index = 0
            self.chars = ['|', '/', '-', '\\']
            self._printed = False
            
        def next(self):
            self.index = (self.index + 1) % len(self.chars)
            print(f'\r{self.message}{self.chars[self.index]}', end='', flush=True)
            self._printed = True
            
        def __del__(self):
            if self._printed:
                print()

from Utils import *
from termcolor import cprint, colored
from LoggerHandler import debug, info, error
import Updater
import func_timeout


def _is_private_ip(ip: str) -> bool:
    """判断是否为内网 IP（校园网通常为 10./172.16-31./192.168.）"""
    if not ip:
        return False
    parts = ip.split('.')
    if len(parts) != 4:
        return False
    try:
        a, b = int(parts[0]), int(parts[1])
    except ValueError:
        return False
    if a == 10:
        return True
    if a == 172 and 16 <= b <= 31:
        return True
    if a == 192 and b == 168:
        return True
    return False


def _is_virtual_ip(ip: str) -> bool:
    """判断是否为代理/虚拟网卡等不可用于校园网认证的 IP"""
    if not ip:
        return True
    parts = ip.split('.')
    try:
        a, b = int(parts[0]), int(parts[1])
    except (ValueError, IndexError):
        return True
    if a == 127 or a == 169 or a == 198 or a == 100:
        return True
    return False


def _detect_private_ip_from_ifconfig() -> str:
    """通过 ipconfig/ifconfig 枚举网卡，返回第一个内网且非虚拟的 IP"""
    import subprocess
    if os.name == 'nt':
        output = subprocess.check_output('ipconfig', encoding='gbk', errors='ignore')
        ips = re.findall(r'IPv4 地址[ .]+: (\d+\.\d+\.\d+\.\d+)', output)
        for ip in ips:
            if _is_private_ip(ip) and not _is_virtual_ip(ip):
                return ip
    else:
        output = subprocess.check_output('ifconfig', encoding='utf-8', errors='ignore')
        ips = re.findall(r'inet (\d+\.\d+\.\d+\.\d+)', output)
        for ip in ips:
            if _is_private_ip(ip) and not _is_virtual_ip(ip):
                return ip
    return None


class Connector:
    config = get_config()
    agent_header = {
        'pc': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/110.0',
        'mobile': 'Mozilla/5.0 (iPhone; CPU iPhone OS 11_0 like Mac OS X) '
                  'AppleWebKit/604.1.38 (KHTML, like Gecko) Version/11.0 Mobile/15A372 Safari/604.1'
    }

    def __init__(self):
        self.printable = Connector.config['printable']
        self.detect_captive_portal_url = Connector.config['detect_captive_portal_url']
        # Dr.COM 认证服务器地址
        self.drcom_base_url = "http://211.97.5.4:801"
        self.drcom_login_url = f"{self.drcom_base_url}/eportal/portal/login"
        self.drcom_logout_url = f"{self.drcom_base_url}/eportal/portal/logout"
        self.drcom_query_url = f"{self.drcom_base_url}/eportal/portal/query"
        # 固定参数（从抓包中获取）
        self.wlan_ac_ip = "172.30.1.1"
        self.login_method = "1"
        self.jsVersion = "4.2"
        self.terminal_type = "1"
        self.wlan_user_mac = "000000000000"
        self.callback = "dr1003"
        self.v = "10406"
        self.agent = 'pc'
        self.is_auto_login = True
        self.user_id = ''
        self.password = ''
        self.remember = ''
        self.local_ip = None

    @staticmethod
    def print_welcome_banner():
        """ 启动横幅 """
        cprint(r'''
          _________  ____  ____  ___  _____/ /_____  _____
         / ___/ __ \/ __ \/ __ \/ _ \/ ___/ __/ __ \/ ___/
        / /__/ /_/ / / / / / / /  __/ /__/ /_/ /_/ / /    
        \___/\____/_/ /_/_/ /_/\___/\___/\__/\____/_/     
        ::ZHKU connector::            [version 2.0.0]    
        ''', 'green')
        cprint(f'''
        - github: https://github.com/jared955/ZHKU-Connector
        - last update: 2026-09
        ''', 'dark_grey')

    def get_local_ip(self):
        """获取本机用于校园网认证的内网 IP"""
        ac_host = None
        try:
            ac_host = self.drcom_base_url.split('://')[1].split(':')[0]
        except Exception:
            pass

        def _can_reach(src_ip: str, dst_host: str, dst_port: int) -> bool:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.bind((src_ip, 0))
                s.settimeout(2)
                s.connect((dst_host, dst_port))
                s.close()
                return True
            except Exception:
                return False

        candidates = []
        try:
            hostname = socket.gethostname()
            for info in socket.getaddrinfo(hostname, None, socket.AF_INET):
                ip = info[4][0]
                if ip and _is_private_ip(ip) and not _is_virtual_ip(ip) and ip not in candidates:
                    candidates.append(ip)
        except Exception:
            pass
        try:
            ip = _detect_private_ip_from_ifconfig()
            if ip and ip not in candidates:
                candidates.append(ip)
        except Exception:
            pass

        if ac_host:
            for ip in candidates:
                if _can_reach(ip, ac_host, 801):
                    return ip
            for ip in candidates:
                if _can_reach(ip, ac_host, 80):
                    return ip

        for ip in candidates:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.bind((ip, 0))
                s.settimeout(2)
                s.connect(('8.8.8.8', 80))
                s.close()
                return ip
            except Exception:
                continue

        return candidates[0] if candidates else None

    def detect_captive_portal(self):
        """检测是否需要认证"""
        try:
            response = requests.get(self.detect_captive_portal_url, allow_redirects=False, timeout=5)
            if response.status_code == 204:
                return False
            else:
                return True
        except requests.RequestException:
            return True

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
        """输入账号和密码"""
        self.user_id = input(info('请输入账号：', self.printable))
        self.password = getpass.getpass(info('请输入密码：', self.printable))

    def login_info_input(self):
        """输入登录信息"""
        self.account_input()
        self.setting_input()
        i_user = {
            'user_id': self.user_id,
            'password': self.password
        }
        i_setting = {
            'user_agent': self.agent,
            'auto_login': self.is_auto_login,
        }
        return i_user, i_setting

    def login_address_connect_status_test(self):
        """检测登录地址是否连接正常"""
        debug('检测登录地址是否连接正常……')
        try:
            response = requests.get(self.drcom_base_url, timeout=5)
            if response.status_code == 200:
                debug('登录地址获取成功')
                return True
            else:
                debug('登录地址获取失败')
                return False
        except:
            debug('登录地址获取失败')
            return False

    def _account_prefix(self) -> str:
        """返回 Dr.COM 账号前缀"""
        return ",1," if self.agent == 'mobile' else ",0,"

    def drcom_logout(self):
        """Dr.COM 注销"""
        if not self.local_ip:
            self.local_ip = self.get_local_ip()
        if not self.local_ip:
            error('无法获取本机 IP')
            return False
        
        params = {
            "callback": self.callback,
            "user_account": f"{self._account_prefix()}{self.user_id}",
            "wlan_user_ip": self.local_ip
        }
        headers = {
            "User-Agent": Connector.agent_header[self.agent],
            "Referer": self.drcom_base_url + "/",
            "Host": "211.97.5.4:801"
        }
        
        try:
            response = requests.get(self.drcom_logout_url, params=params, headers=headers, timeout=10)
            debug(f'注销响应: {response.text}')
            if "注销成功" in response.text:
                return True
            return False
        except Exception as e:
            error(f'注销请求失败: {e}')
            return False

    def login(self):
        """Dr.COM GET 方式登录"""
        if not self.local_ip:
            self.local_ip = self.get_local_ip()
        if not self.local_ip:
            error('无法获取本机 IP，请检查网络连接')
            return False

        info(colored(f'[{self.user_id}]', 'light_cyan') + '正在登录中……')
        
        terminal_type = "2" if self.agent == 'mobile' else "1"
        
        params = {
            "callback": self.callback,
            "login_method": self.login_method,
            "user_account": f"{self._account_prefix()}{self.user_id}",
            "user_password": self.password,
            "wlan_user_ip": self.local_ip,
            "wlan_user_ipv6": "",
            "wlan_user_mac": self.wlan_user_mac,
            "wlan_ac_ip": self.wlan_ac_ip,
            "wlan_ac_name": "",
            "jsVersion": self.jsVersion,
            "terminal_type": terminal_type,
            "lang": "zh-cn",
            "v": self.v
        }
        
        headers = {
            "User-Agent": Connector.agent_header[self.agent],
            "Referer": self.drcom_base_url + "/",
            "Host": "211.97.5.4:801",
            "Accept": "*/*",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Connection": "keep-alive"
        }
        
        try:
            response = requests.get(self.drcom_login_url, params=params, headers=headers, timeout=10)
            debug(f'登录响应: {response.text}')
            
            jsonp_match = re.search(r'\{.*\}', response.text)
            if jsonp_match:
                try:
                    data = json.loads(jsonp_match.group())
                    debug(f'解析结果: {data}')
                    
                    if data.get('result') == 1:
                        info('认证成功')
                        return True
                    elif data.get('ret_code') == 2 and "已经在线" in data.get('msg', ''):
                        info('账号已在线，登录成功')
                        return True
                    else:
                        error(data.get('msg', '登录失败，未知错误'))
                        return False
                except json.JSONDecodeError:
                    error('解析响应失败')
                    return False
            else:
                error('响应格式异常')
                return False
                
        except requests.exceptions.Timeout:
            error('登录请求超时，请检查网络连接')
            return False
        except Exception as e:
            error(f'登录请求出错: {e}')
            return False

    def remember_me(self):
        info('保存登录信息，下次启动程序可以自动登录。')
        is_remember_input = input(
            info('记住登录信息吗？ Y）同意-默认  N）不同意/清除：', self.printable))
        is_remember_login = len(is_remember_input) == 0 or any(res in is_remember_input for res in ['y', 'Y'])
        if is_remember_login:
            login_info = {
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
            captive = self.detect_captive_portal()
            if captive:
                spinner = Spinner('\r')
                error('强制主页，登录以继续，将执行自动登录')
                self.drcom_logout()
                time.sleep(1)
                if self.login():
                    info('自动登录成功')
                else:
                    error('自动登录失败')
                spinner = Spinner(info('持续监测中 ', self.printable))
            for i in range(5):
                spinner.next()
                time.sleep(1)

    @func_timeout.func_set_timeout(5)
    def ask_is_edit_login_info(self, credentials):
        return input('保存有登录信息'
                     + colored(f'[{credentials["login_info"]["user_id"]}]', 'light_cyan')
                     + '，5秒后加载这个配置（回车清除记录）')

    def run(self):
        self.print_welcome_banner()
        
        self.local_ip = self.get_local_ip()
        if self.local_ip:
            debug(f'本机 IP: {self.local_ip}')
        else:
            error('无法获取本机 IP，请检查网络连接')
            os.system("pause")
            return
        
        try:
            code = requests.get(self.detect_captive_portal_url, allow_redirects=False, timeout=5).status_code
        except:
            code = None
        
        credentials = get_remembered_credentials()
        if credentials:
            try:
                self.remember = self.ask_is_edit_login_info(credentials)
            except:
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

        if code is not None and code != 204:
            info("未连接到互联网，检测登录主页中......")
            login_address_connect = self.login_address_connect_status_test()
            while not login_address_connect:
                error('登录主页访问失败，请检查网络环境是否正确')
                login_address_connect = self.login_address_connect_status_test()
                time.sleep(10)

        login_success = False
        while not login_success:
            self.drcom_logout()
            time.sleep(1)
            if self.login():
                login_success = True
            else:
                error('登录失败，请检查登录信息是否正确并重新输入')
                self.account_input()

        info('账号登录正常')
        if self.remember != 'use_last':
            self.remember_me()
        
        #Updater.fetch()

        self.auto_login()


if __name__ == '__main__':
    connector = Connector()
    connector.run()
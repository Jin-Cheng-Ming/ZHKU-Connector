# Distributed under the MIT license, see LICENSE
import os # 用于程序暂停
import json  # 用于解析 Dr.COM 认证接口的返回
import random  # 用于给认证请求加随机参数
import re  # 用于从门户页面里解析字段
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
    # 默认登录表单字段（海珠/白云同为石斧系统）。可被 config.yml 的 portal_fields 覆盖。
    DEFAULT_PORTAL_FIELDS = {
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
        "isautoauth": "",
        "notice_pic_float": "/portal/uploads/pc/hb_pay/images/rrs_bg.jpg",
        "remInfo": "on",
    }
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
        # 多探针：任一返回 204 即视为"网络正常、没被劫持"
        _urls = Connector.config.get('detect_captive_portal_urls') or []
        if not _urls:
            _urls = [Connector.config['detect_captive_portal_url']]
        self.detect_captive_portal_urls = list(_urls)
        self.detect_captive_portal_url = self.detect_captive_portal_urls[0]
        # 直连，不走系统代理：校园网门户是本地的，本机代理一关就全超时
        self.session = requests.Session()
        self.session.trust_env = False
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
        cprint(rf'''
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
        errors = []
        for url in self.detect_captive_portal_urls:
            try:
                response = self.session.get(url, allow_redirects=False, timeout=6)
            except requests.RequestException as e:
                errors.append(f'{url} → {e}')
                continue

            if self._probe_is_normal(url, response):
                return False

            # 不是"正常"的响应 —— 对这批探针来说，这就是被强制门户替换了：
            #   generate_204 正常必须 204，返回 200/302 说明内容被换掉了；
            #   connecttest.txt 正常是那句固定的英文，内容不对同理。
            hijack_url = response.headers.get('Location') or self._extract_redirect(response.text)
            if hijack_url:
                self.captive_portal = hijack_url
            return True

        # 所有探针都连不上（异常，不是"内容被替换"）：这才是"探不明白"。
        # 此时不登录 —— 网络抖动时反复 POST 会被学校判定为共享而冻结账号。
        if errors:
            print('探针均不可达：' + ' | '.join(errors[:3]))
            print('（本程序已忽略系统代理直连。若仍失败，请确认 Wi-Fi 已连接；'
                  '若日志里出现 127.0.0.1 端口，说明请求仍被代理拦下）')
        return None

    def _probe_is_normal(self, url: str, response) -> bool:
        """这个探针的响应是否说明"网络正常"。"""
        if 'generate_204' in url:
            return response.status_code == 204
        if 'connecttest' in url:
            return response.status_code == 200 and 'Microsoft Connect Test' in (response.text or '')
        return response.status_code in (200, 204)

    @staticmethod
    def _extract_redirect(html: str):
        """从被劫持返回的 HTML 里尽量挖出真正的门户地址。

        学校门户有两种呈现方式：302 跳转（有 Location 头），或者直接返回一个
        带 <meta refresh> / JS 跳转的页面。后者没有 Location，只能从正文里找。
        """
        if not html:
            return None
        patterns = [
            r'<meta[^>]+http-equiv=["\']?refresh["\']?[^>]+url=([^"\'>\s]+)',
            r'location\.(?:href|replace)\s*[=(]\s*["\']([^"\']+)["\']',
            r'top\.location\s*=\s*["\']([^"\']+)["\']',
        ]
        for p in patterns:
            m = re.search(p, html, re.I)
            if m:
                url = m.group(1).strip()
                if url.startswith('http'):
                    return url
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
        self.user_id = input(info('请输入账号：', self.printable)).strip()
        if Connector.config.get('password_echo'):
            # 兼容模式：个别终端里 getpass 读不到按键（表现为"打不了字"），
            # 这时把 config.yml 的 password_echo 改成 true，改用可见输入。
            info('（已启用可见输入：密码会显示在屏幕上）', self.printable)
            self.password = input(info('请输入密码：', self.printable))
        else:
            # 默认：不回显。注意敲密码时屏幕上不会有任何字符，这是正常的。
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
        portal_type = (Connector.config.get('portal_type') or 'form').lower()
        if portal_type in ('drcom', 'drcom_eportal'):
            # 白云校区：Dr.COM（城市热点）eportal，JSON 接口，不是表单 POST
            info(colored(f'[{self.user_id}]', 'light_cyan') + '正在登录中……（Dr.COM eportal）')
            return self._login_drcom()

        # 请求数据：字段表放在 config.yml 的 portal_fields 里，换校区/换学校只改配置
        data = dict(Connector.DEFAULT_PORTAL_FIELDS)
        data.update(Connector.config.get('portal_fields') or {})
        data["url"] = self.captive_portal
        data["userId"] = self.user_id
        data["passwd"] = self.password
        info(colored(f'登录地址：{self.captive_portal}', 'light_grey'))
        self._dump_portal_form()
        # 设置登录状态
        login_result_status = False
        info(colored(f'[{self.user_id}]', 'light_cyan') + '正在登录中……')
        login_address = self.captive_portal
        try:
            # 对校园网登录网址发送请求(执行登录操作) 并获取请求到的页面数据
            res = self.session.post(login_address, data=data, headers=Connector.agent_header[self.agent]).text
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
            if not login_result_status:
                return False
            # HTML 说成功不代表真的通了：再探一次确认，避免"假成功"后一直被踢
            if self.verify_login():
                return True
            error('登录接口报成功，但网络仍未恢复（可能账号被限制/需在 portal 里补资料）')
            return False
        except:
            error('登录请求出错，请检查网络环境是否正确')
            return None

    def _local_ip(self) -> str:
        """本机在校园网里的 IP：优先读认证页里的 v46ip（最准），否则用 UDP 技巧拿出口地址。"""
        try:
            r = self.session.get(self.captive_portal, timeout=6,
                                 headers=Connector.agent_header[self.agent])
            m = re.search(r"v46ip\s*=\s*'([0-9.]+)'", r.content.decode('gbk', 'replace'))
            if m:
                return m.group(1)
        except Exception:
            pass
        try:
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('10.255.254.254', 801))   # 只用于取本机出口地址，不发任何数据
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return ''

    def _login_drcom(self) -> bool:
        """Dr.COM（城市热点）eportal 登录。

        白云校区实测（2026-10）：
            GET http://10.255.254.254:801/eportal/portal/login
                ?callback=dr1003&login_method=1&user_account=,0,<账号>
                &user_password=<密码>&wlan_user_ip=<本机IP>&...
            → dr1003({"result":1,"msg":"..."})           登录成功
            → dr1003({"result":0,"ret_code":2,"msg":"...已经在线！"})  本来就在线，也算成功
        """
        cfg = Connector.config.get('drcom') or {}
        ip = cfg.get('portal_ip') or '10.255.254.254'
        port = cfg.get('port') or 801
        path = cfg.get('login_path') or '/eportal/portal/login'
        js_version = cfg.get('js_version') or '4.1.3'
        my_ip = self._local_ip()

        params = {
            'callback': 'dr1003',
            'login_method': '1',
            'user_account': ',0,' + str(self.user_id),
            'user_password': self.password,
            'wlan_user_ip': my_ip,
            'wlan_user_ipv6': '',
            'wlan_user_mac': '000000000000',
            'wlan_ac_ip': '',
            'wlan_ac_name': '',
            'jsVersion': js_version,
            'v': str(random.randint(1000, 9999)),
            'lang': 'zh',
        }
        url = f'http://{ip}:{port}{path}'
        info(colored(f'登录地址：{url}', 'light_grey'))
        info(colored(f'本机 IP：{my_ip or "(未识别)"}', 'light_grey'))

        try:
            r = self.session.get(url, params=params, timeout=10,
                                 headers=Connector.agent_header[self.agent])
        except requests.RequestException as e:
            error(f'登录请求出错：{e}')
            return False

        m = re.search(r'\{.*\}', r.text, re.S)
        if not m:
            error(f'认证接口返回异常（HTTP {r.status_code}）：{r.text[:120]}')
            return False
        try:
            obj = json.loads(m.group(0))
        except Exception as e:
            error(f'认证结果解析失败：{e}')
            return False

        result, ret_code, msg = obj.get('result'), obj.get('ret_code'), str(obj.get('msg', ''))
        info(colored(f'认证返回：result={result} ret_code={ret_code} msg={msg}', 'light_grey'))
        if result == 1 or ret_code == 2:
            # 1=登录成功；2=本来就在线（都算"有网了"）
            return True
        error(f'登录失败：{msg or "（接口没给出原因）"}')
        return False

    def _dump_portal_form(self):
        """把门户登录页的 form/input 字段写进日志。

        目的：万一 config.yml 里的 portal_fields 跟学校对不上，日志里就留着
        真实字段名，改配置时不用再猜。只在"检测到劫持"时才跑，不会频繁请求。
        """
        try:
            r = self.session.get(self.captive_portal, timeout=8,
                                 headers=Connector.agent_header[self.agent])
            html = r.text or ''
            info(colored(f'门户页面 HTTP {r.status_code}，长度 {len(html)}', 'light_grey'))
            forms = re.findall(r'<form[^>]*>', html, re.I)
            for f in forms[:3]:
                info('  form: ' + re.sub(r'\s+', ' ', f)[:150])
            for m in re.finditer(r'<input[^>]*>', html, re.I):
                tag = re.sub(r'\s+', ' ', m.group(0))
                name = re.search(r'name=["\']([^"\']*)', tag, re.I)
                typ = re.search(r'type=["\']([^"\']*)', tag, re.I)
                info(f"  input: name={name.group(1) if name else '-'} "
                     f"type={typ.group(1) if typ else '-'}")
            if not forms and not re.search(r'<input', html, re.I):
                info('  （页面里没有内联表单，可能是 JS 动态渲染）')
        except Exception as e:
            info(f'  （抓取门户页面失败：{e}）')

    def verify_login(self, tries=3, gap=1.5):
        """登录后确认：探针返回 204 才算真的通了。"""
        for _ in range(tries):
            if self.detect_captive_portal() is False:
                return True
            time.sleep(gap)
        return False

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
        interval = 5          # 正常情况每 5 秒探一次
        while True:
            captive = self.detect_captive_portal()
            if captive is True:
                spinner = Spinner('\r')
                error('检测到强制门户，执行自动登录')
                if self.login() is True:
                    info('自动登录成功')
                    interval = 5
                else:
                    # 失败就退避：越试越慢，别把登录接口打爆（学校会判定共享并冻结）
                    interval = min(interval * 2, 60)
                    error(f'自动登录失败，{interval} 秒后重试')
                spinner = Spinner(info('持续监测中 ', self.printable))
            elif captive is None:
                # 探不明白：保持安静，不发登录请求
                interval = min(interval * 2, 60)
            else:
                interval = 5
            for i in range(interval):
                spinner.next()
                time.sleep(1)

    @func_timeout.func_set_timeout(5)
    def ask_is_edit_login_info(self, credentials):
        """
        设置5秒内没有输入的话加载配置
        """

        _uid = credentials["login_info"]["user_id"]
        if isinstance(_uid, (tuple, list)):
            _uid = str(_uid[0]) if _uid else ''
        return input('保存有登录信息'
                     + colored(f'[{_uid}]', 'light_cyan')
                     + '，5秒后加载这个配置（回车清除记录）')

    def run(self):
        # 欢迎
        self.print_welcome_banner()
        try:
            code = self.session.get(self.detect_captive_portal_url,
                                allow_redirects=False, timeout=6).status_code
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
        if isinstance(self.user_id, (tuple, list)):   # 旧版本存成了元组
            self.user_id = str(self.user_id[0]) if self.user_id else ''
        self.user_id = str(self.user_id).strip()
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

        # 只有"确实被劫持"才登录；网络正常就跳过。
        # 对开机自启尤其重要：每次开机都发一次登录请求既没必要，
        # 也容易被学校判定为账号共享。
        for attempt in range(3):
            if self.detect_captive_portal() is not True:
                info('当前网络正常，无需登录，直接进入监测模式')
                break
            if self.login() is True:
                break
            error(f'登录失败（第 {attempt + 1} 次），请检查账号密码')
            if attempt < 2:
                self.account_input()
        else:
            error('连续 3 次登录失败：请确认账号是否已审核通过/是否需要先在 portal 里补资料')
            error('程序将进入监测模式，不再频繁重试（避免账号被判定为共享而冻结）')

        info('账号登录正常')
        if self.remember != 'use_last':
            self.remember_me()
        # 更新检查：失败不该影响上网
        try:
            Updater.fetch()
        except Exception as e:
            error(f'更新检查失败（不影响使用）：{e}')

        self.auto_login()


def _another_instance_running():
    """同一台机器上是否已有实例在跑。

    多开 = 同一账号重复登录 = 学校判定为共享并冻结，所以必须拦住。
    用临时目录里的锁文件记 PID，再用 OpenProcess 判断它还活着（跨平台均可）。
    """
    import tempfile
    lock = os.path.join(tempfile.gettempdir(), 'zhku-connector.lock')
    try:
        if os.path.exists(lock):
            try:
                with open(lock, 'r') as f:
                    old = int((f.read() or '0').strip() or 0)
            except Exception:
                old = 0
            if old and old != os.getpid():
                alive = False
                try:
                    import ctypes
                    h = ctypes.windll.kernel32.OpenProcess(0x1000, False, old)
                    if h:
                        alive = True
                        ctypes.windll.kernel32.CloseHandle(h)
                except Exception:
                    alive = os.path.exists('/proc/%d' % old)
                if alive:
                    return old
        with open(lock, 'w') as f:
            f.write(str(os.getpid()))
    except Exception:
        pass
    return None


if __name__ == '__main__':
    other = _another_instance_running()
    if other:
        print(f'已经有一个 ZHKU-Connector 在运行（PID {other}），本次不启动。')
        print('同一账号同时登录会被学校判定为共享并冻结 —— 请先关掉那一个再运行。')
        time.sleep(5)
        sys.exit(0)
    connector = Connector()
    connector.run()

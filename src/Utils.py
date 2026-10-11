"""配置读取与凭据存储。

凭据支持三种存储方式，由 config.yml 的 credential_encryption 决定：

    passphrase（默认）  口令加密：AES-256-GCM，密钥由口令经 PBKDF2-SHA256 派生。
                        口令本身可用 Windows 数据保护接口加密后存到本机
                        （network_credentials.key），因此开机自启仍能无人值守；
                        把加密后的凭据文件拷到别的电脑时，输入一次该口令即可解开。
    dpapi               直接用 Windows 数据保护接口加密（换机器 / 换账户都解不开）。
    plain               明文保存（不推荐）。

文件格式自描述，向后兼容：
    ZHKUENC2\\n + salt(16) + nonce(12) + 密文    ← 口令加密（本版本）
    ZHKUENC1\\n + base64(DPAPI 密文)             ← 早期 DPAPI 直加密
    其它                                         ← 更早的明文 pickle
"""
import base64  # 用于编码加密后的凭据
import ctypes  # 用于调用 Windows 数据保护接口
import getpass  # 用于口令输入（不回显）
import hashlib  # 用于 PBKDF2 派生密钥
import os  # 用于系统查看等操作
import pickle  # 用户持久化文件
import sys  # 用于系统查看等操作

import yaml  # 用于加载配置

network_credentials_file_name = 'network_credentials.pkl'
network_credentials_file_path = os.path.expanduser('~') + os.sep + network_credentials_file_name

# 加密文件的两个版本头
_ENC_MAGIC = b'ZHKUENC1\n'      # 早期：DPAPI 直加密
_ENC_MAGIC_V2 = b'ZHKUENC2\n'   # 本版本：口令加密（AES-256-GCM）

_pass_file_name = 'network_credentials.key'   # 本机保存的口令（DPAPI 保护）
_pass_file_path = os.path.expanduser('~') + os.sep + _pass_file_name
_PBKDF2_ROUNDS = 300000


class _DataBlob(ctypes.Structure):
    _fields_ = [('cbData', ctypes.c_ulong), ('pbData', ctypes.POINTER(ctypes.c_char))]


def _dpapi(protect: bool, data: bytes) -> bytes:
    """调用 Windows 的 CryptProtectData / CryptUnprotectData。

    加密结果与「当前用户 + 当前这台电脑」绑定：拷到别的机器或别的账户下都解不开。
    既保证开机自动登录无需输入口令，又不怕文件被复制走。
    """
    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    buf_in = ctypes.create_string_buffer(data, len(data))
    blob_in = _DataBlob(len(data), ctypes.cast(buf_in, ctypes.POINTER(ctypes.c_char)))
    blob_out = _DataBlob()
    fn = crypt32.CryptProtectData if protect else crypt32.CryptUnprotectData
    if not fn(ctypes.byref(blob_in), None, None, None, None, 0, ctypes.byref(blob_out)):
        raise OSError('Windows 数据保护接口调用失败')
    try:
        return ctypes.string_at(blob_out.pbData, blob_out.cbData)
    finally:
        kernel32.LocalFree(blob_out.pbData)


def _derive_key(passphrase: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac('sha256', passphrase.encode('utf-8'), salt,
                               _PBKDF2_ROUNDS, dklen=32)


def _aes_encrypt(passphrase: str, payload: bytes) -> bytes:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    salt, nonce = os.urandom(16), os.urandom(12)
    ct = AESGCM(_derive_key(passphrase, salt)).encrypt(nonce, payload, None)
    return _ENC_MAGIC_V2 + salt + nonce + ct


def _aes_decrypt(passphrase: str, raw: bytes) -> bytes:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    body = raw[len(_ENC_MAGIC_V2):]
    salt, nonce, ct = body[:16], body[16:28], body[28:]
    return AESGCM(_derive_key(passphrase, salt)).decrypt(nonce, ct, None)


# ── 口令的取得与保管 ────────────────────────────────────────────

def save_passphrase_locally(passphrase: str) -> bool:
    """把口令用 Windows 数据保护接口加密后存到本机，供开机自启自动使用。"""
    try:
        with open(_pass_file_path, 'wb') as f:
            f.write(_dpapi(True, passphrase.encode('utf-8')))
        return True
    except Exception:
        return False


def load_passphrase():
    """取口令：环境变量 ZHKU_PASSPHRASE → 本机保存的 → 返回 None。"""
    env = os.environ.get('ZHKU_PASSPHRASE')
    if env:
        return env
    try:
        with open(_pass_file_path, 'rb') as f:
            return _dpapi(False, f.read()).decode('utf-8')
    except Exception:
        return None


def ask_passphrase(confirm: bool = False):
    """交互输入口令（不回显）；confirm=True 时要求二次确认。"""
    try:
        p = getpass.getpass('请输入凭据口令（用于加密保存账号密码）：')
        if confirm and p != getpass.getpass('请再输入一次确认：'):
            print('两次输入不一致，请重来。')
            return None
        return p or None
    except Exception:
        return None


def forget_local_passphrase() -> bool:
    """删除本机保存的口令（下次启动会重新询问）。"""
    try:
        os.remove(_pass_file_path)
        return True
    except Exception:
        return False


# ── 编解码 ─────────────────────────────────────────────────────

def _config() -> dict:
    try:
        return get_config() or {}
    except Exception:
        return {}


def _encode_credentials(payload: bytes) -> bytes:
    """保存时加密。口令优先取本机保存的那份，没有就问一次并询问是否存本机。"""
    mode = str(_config().get('credential_encryption') or 'passphrase').lower()

    if mode in ('passphrase', 'password'):
        passphrase = load_passphrase()
        if not passphrase:
            passphrase = ask_passphrase(confirm=True)
            if not passphrase:
                print('未设置口令，将改用系统加密（Windows 数据保护接口，仅本机本账户可解）。')
            if passphrase:
                try:
                    ans = input('是否把口令保存在本机（以便开机自动登录）？Y）是-默认 N）否：').strip()
                except Exception:
                    ans = 'y'
                if ans == '' or ans.lower().startswith('y'):
                    if save_passphrase_locally(passphrase):
                        print('口令已加密保存在本机（仅本机本账户可解）。')
        if passphrase:
            try:
                return _aes_encrypt(passphrase, payload)
            except Exception as e:
                print(f'口令加密失败（{e}），改用系统加密。')

    if mode != 'plain':
        try:
            return _ENC_MAGIC + base64.b64encode(_dpapi(True, payload))
        except Exception:
            pass
    return payload


def _decode_credentials(raw: bytes) -> bytes:
    if raw.startswith(_ENC_MAGIC_V2):
        passphrase = load_passphrase()
        for _ in range(3):
            if not passphrase:
                passphrase = ask_passphrase()
            if not passphrase:
                break
            try:
                return _aes_decrypt(passphrase, raw)
            except Exception:
                print('口令不正确，请重试。')
                passphrase = None
        raise ValueError('无法用口令解开凭据文件')
    if raw.startswith(_ENC_MAGIC):
        return _dpapi(False, base64.b64decode(raw[len(_ENC_MAGIC):]))
    return raw          # 更早的明文 pickle


def credentials_encrypted() -> bool:
    """当前凭据是否为加密状态。"""
    try:
        with open(network_credentials_file_path, 'rb') as f:
            head = f.read(len(_ENC_MAGIC_V2))
        return head == _ENC_MAGIC_V2 or head[:len(_ENC_MAGIC)] == _ENC_MAGIC
    except Exception:
        return False


def upgrade_credentials_to_encrypted() -> bool:
    """把旧的明文 / DPAPI 凭据迁移为口令加密。成功返回 True。

    安全兜底：先确认写进去的能解回来，再覆盖原文件；解不回来就原样不动。
    """
    try:
        if not os.path.exists(network_credentials_file_path):
            return False
        with open(network_credentials_file_path, 'rb') as f:
            raw = f.read()
        if raw.startswith(_ENC_MAGIC_V2):
            return False                       # 已是口令加密
        payload = _decode_credentials(raw)
        enc = _encode_credentials(payload)
        if enc == raw:
            return False                       # 没有变化，无需写回
        # 自检：按实际采用的方案解一遍，确认能解回来再覆盖原文件
        if enc.startswith(_ENC_MAGIC_V2):
            if _aes_decrypt(load_passphrase() or '', enc) != payload:
                return False
        elif enc.startswith(_ENC_MAGIC):
            if _dpapi(False, base64.b64decode(enc[len(_ENC_MAGIC):])) != payload:
                return False
        else:
            return False                       # 明文就不迁移了
        with open(network_credentials_file_path, 'wb') as f:
            f.write(enc)
        return True
    except Exception:
        return False


# ── 资源与配置 ─────────────────────────────────────────────────

def get_resource(relative_path: str):
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath('.')
    return os.path.join(base_path, relative_path)


def get_config():
    """获取配置信息"""
    try:
        with open(get_resource('config.yml'), 'r', encoding='utf-8') as f:
            config = yaml.load(f.read(), Loader=yaml.FullLoader)
            return config
    except Exception:
        return None


# ── 凭据读写（对外接口保持不变）────────────────────────────────

def remember_login(i_user: dict, i_setting: dict):
    """保存登录信息：账号、密码与功能设置（默认口令加密）。"""
    try:
        payload = pickle.dumps({'login_info': i_user, 'setting_info': i_setting})
        with open(network_credentials_file_path, 'wb') as f:
            f.write(_encode_credentials(payload))
        return True
    except Exception:
        return False


def remove_remembered_credentials():
    """删除已保存的登录信息"""
    try:
        os.remove(network_credentials_file_path)
        return True
    except Exception:
        return False


def get_remembered_credentials():
    """读取已保存的登录信息。

    自动兼容「口令加密 / DPAPI 加密 / 旧版明文」三种格式；
    若读到的是旧格式，会顺手迁移成口令加密（迁移失败也不影响本次使用）。
    """
    try:
        with open(network_credentials_file_path, 'rb') as f:
            raw = f.read()
        credentials = pickle.loads(_decode_credentials(raw))
        if not raw.startswith(_ENC_MAGIC_V2):
            try:
                upgrade_credentials_to_encrypted()
            except Exception:
                pass
        return credentials
    except Exception:
        return None

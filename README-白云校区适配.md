# ZHKU-Connector · 校园网自动登录助手（白云校区适配版）

> 基于 [Jin-Cheng-Ming/ZHKU-Connector](https://github.com/Jin-Cheng-Ming/ZHKU-Connector)（MIT）二次开发。
> 在**连上校园 Wi-Fi 的前提下**，一旦认证掉线（休眠唤醒、会话超时被踢、重连 Wi-Fi），
> 自动用保存的账号重新认证，几秒内把网接回来。平时不干扰正常上网。

---

## ⚠️ 测试范围声明（务必先读）

| 校区 / 场景 | 测试状态 |
|---|---|
| **仲恺农业工程学院 · 白云校区** | ✅ **已实测通过**：连续 3 次断线后自动重登成功（认证返回 `result=1`、「Portal协议认证成功！」） |
| **仲恺农业工程学院 · 海珠校区** | ❌ **未测试**。海珠是**另一套认证系统**（石斧 zaxsoft，见 §3 对比表），本版本的改动**没有在海珠验证过**，也没有海珠的账号与网络环境可用 |
| **其他学校** | ❌ **未测试**。本项目可作为**模板**改造，方法见 [§7](#7-改造成你自己学校的模板指南) |
| 教师账号 / 运营商其他套餐账号 | ❌ 未测试 |
| 白云校区的其他接入方式（有线网、其他 SSID） | ❌ 未测试，仅验证了 `ZK-WIFI` |

> 换句话说：**只有「仲恺白云 + ZK-WIFI + 学生账号」这一条路径是被真实跑通的**，其余都是推断或模板。

---

## 1. 它解决什么问题

校园网属于「Web Portal 认证」型：连上 Wi-Fi 后要在网页里输账号密码，认证通过才能上网。而这个认证会因以下原因失效：

- 笔记本合盖休眠 / 唤醒
- 认证会话超时（学校侧主动踢下线）
- 断开 Wi-Fi 再重连（学校规定「断开 WIFI 后账号自动下线」）
- 更换网络环境（教学楼 ↔ 宿舍）

失效后的表现：**Wi-Fi 显示已连接，但所有网页都跳转到认证页**（强制门户 / Captive Portal）。

本程序做的事：每隔几秒探测一次「现在上网正常，还是被强制门户劫持了」，
一旦发现被劫持，就用保存的账号自动完成认证，无需人工干预。

---

## 2. 工作原理

```
        ┌───────────────────────────────────────────────┐
        │  每 5 秒循环一次（失败会退避到 10/20/40/60 秒）│
        └───────────────────────────────────────────────┘
                            │
              ┌─────────────▼──────────────┐
              │  探测：访问 generate_204    │
              └─────────────┬──────────────┘
                            │
        ┌───────────────────┼────────────────────┐
        │                   │                    │
   返回 204            返回 200/302         全部请求失败
  （正常联网）      （内容被替换＝被劫持）   （探不明白）
        │                   │                    │
   什么都不做          执行认证登录          什么都不做
   继续监测         ＋ 登录后二次确认      （绝不盲目登录）
```

三个关键设计（都是踩坑之后加的）：

1. **返回 200 就是被劫持**：`generate_204` 这类探针正常必须返回 `204 No Content`；
   返回 `200`（内容被门户页面替换）就是被劫持 —— 这恰恰是最常见的失败场景。
2. **「探不明白」不等于「断网」**：所有探针都连不上说明网络本身有问题，这时**不发认证请求**。
   因为学校明令「账号被检测到共享会冻结」，网络抖动时反复登录非常危险。
3. **登录后二次确认**：认证接口说成功不算数，必须再探一次、确认真的能上网（返回 204）才算成功。

---

## 3. 两套认证系统的差异（本项目最重要的发现）

| | **白云校区**（本项目实测） | **海珠校区**（原作者那套，未测试） |
|---|---|---|
| 认证系统 | **Dr.COM（城市热点）eportal v4** | **石斧 zaxsoft** |
| 认证页 | `http://10.255.254.254/a79.htm`（标题「上网登录页」，GBK 编码） | `http://1.1.1.1`（学校文档写明） |
| 登录方式 | **JSON 接口（GET + JSONP）** | 表单 POST |
| 登录地址 | `http://10.255.254.254:801/eportal/portal/login` | `http://1.1.1.1:8888/webauth.do?wlanacname=zax_hzoffice` |
| 账号字段 | `user_account`（值为 `,0,<账号>`） | `userId` |
| 密码字段 | `user_password` | `passwd` |
| 其他字段 | `wlan_user_ip`、`jsVersion`、`callback=dr1003` 等 | `auth_type`、`pageid`、`templatetype`… |
| 成功判定 | JSONP 里 `result=1`；`ret_code=2`（已在线）也算成功 | 返回 HTML 中 `#act` 的值为 `LOGINSUCC` |
| 识别特征 | 页面注释 `<!--Dr.COMWebLoginID_0.htm-->`、`authloginport=801`、`authuserfield='DDDDD'` | `wlanacname=zax_*`、`/webauth.do`、端口 8888 |

**结论：拿海珠版直接用在白云（或反过来）都是登不上的。**
本项目用 `config.yml` 的 `portal_type` 区分这两套逻辑。

---

## 4. 白云校区（Dr.COM）完整接口规格

> 本节是实测记录。其他学校若也是 Dr.COM eportal，可直接参考。

**认证页**（`http://10.255.254.254/a79.htm`）源码里自带全部参数：

```javascript
<!--Dr.COMWebLoginID_0.htm-->
v4serip='10.255.254.254'   // 认证服务器
authloginport=801          // 登录端口
authloginpath='/eportal/?c=ACSetting&a=Login'
authuserfield='DDDDD'      // 账号字段名（老式表单接口）
authpassfield='upass'      // 密码字段名（老式表单接口）
authsuccess='Dr.COMWebLoginID_3.htm'
authfail='Dr.COMWebLoginID_2.htm'
authlogoutpath='/eportal/?c=ACSetting&a=Logout&ver=1.0'
```

**实际可用的登录请求**（新版 eportal 走 JSON 接口，而非上面那个老表单接口）：

```http
GET http://10.255.254.254:801/eportal/portal/login
    ?callback=dr1003
    &login_method=1
    &user_account=,0,<账号>
    &user_password=<密码>
    &wlan_user_ip=<本机在校园网的IP>
    &wlan_user_ipv6=
    &wlan_user_mac=000000000000
    &wlan_ac_ip=
    &wlan_ac_name=
    &jsVersion=4.1.3
    &v=<随机四位数>
    &lang=zh
```

**返回**（JSONP）：

```javascript
dr1003({"result":1,"msg":"Portal协议认证成功！"});                    // 登录成功
dr1003({"result":0,"ret_code":2,"msg":"IP: 10.46.x.x 已经在线！"});  // 本来就在线，也算成功
dr1003({"result":0,"msg":"..."});                                    // 失败，msg 是可读原因
```

**本机 IP 从哪来**：优先读认证页里的 `v46ip='10.46.227.101'`；读不到时退回 UDP socket 技巧
（连一下认证服务器取本地出口地址，不发任何数据）。

---

## 5. 快速开始

### 方式 A：用部署包（推荐，对方电脑无需装 Python）

```
① 安装-双击我.bat        ← 双击即可（复制程序、导入登录信息、建快捷方式+开机自启、启动）
ZHKU-Connector\          ← 独立程序本体（PyInstaller onedir，免解压）
network_credentials.pkl  ← 登录信息（同账号）
使用说明.txt              ← 给最终用户看的简明说明
README.md                ← 本文档（技术细节与改造指南）
```

### 方式 B：从源码运行

```powershell
cd ZHKU-Connector-baiyun
pip install -r requirements.txt
python .\src\Connector.py
```

首次运行会依次询问：账号 → 密码（默认不回显）→ 登录设备（选 **1 个人电脑**）→ 是否记住登录信息（选 **Y**）。
之后启动会在 5 秒后自动读取已保存的配置，无需再输入。

**首次还会让你设置一个凭据口令**（用于加密保存账号密码）：

```
请输入凭据口令（用于加密保存账号密码）：      ← 自己定一个，输入时不回显
请再输入一次确认：
是否把口令保存在本机（以便开机自动登录）？Y）是-默认 N）否：
```

选 **Y（回车）** → 口令用 Windows 数据保护接口加密后存本机，只有你这台电脑的当前账户能解开，
**开机自启依旧无人值守** ✓；凭据文件本身则变成 AES-256-GCM 密文，被拷走也读不出账号密码 ✓。
（选 N 则每次启动都要手输一次口令。忘记口令：删掉 `%USERPROFILE%\network_credentials.pkl`
与 `network_credentials.key`，重新运行输入账号即可。）

**辅助脚本**：

| 文件 | 用途 |
|---|---|
| `启动-自动登录.cmd` | 双击启动（带单实例守卫与日志） |
| `诊断-portal.cmd` | **未登录时**双击，抓取真实认证页地址与表单字段，结果存 `logs\diagnose-last.txt` |
| `tools\run-connector.ps1` | 启动器本体（单实例守卫、定位 Python、日志提示） |
| `diagnose.py` | 诊断脚本本体（只做 GET 探测，**不提交任何账号信息**） |

---

## 6. 配置说明（`config.yml`）

```yaml
# 探针：任一返回"正常"即视为网络正常
detect_captive_portal_urls:
  - http://connect.rom.miui.com/generate_204        # 期望 204
  - http://www.gstatic.com/generate_204             # 期望 204
  - http://www.msftconnecttest.com/connecttest.txt  # 期望 200 且含 "Microsoft Connect Test"

# 认证页（兜底值；正常情况下会从"被劫持时的 302 跳转"自动取到真实地址）
login_page: http://10.255.254.254/a79.htm

# 认证系统类型：drcom_eportal = 白云（JSON 接口） / form = 海珠那套（表单 POST）
portal_type: drcom_eportal

drcom:                     # portal_type = drcom_eportal 时生效
  portal_ip: 10.255.254.254
  port: 801
  login_path: /eportal/portal/login
  js_version: 4.1.3

portal_fields:             # portal_type = form 时生效（表单字段表）
  auth_type: "0"
  pageid: "1"
  # …（其余字段见文件内注释）

# 凭据存储方式：
#   passphrase（默认）= 口令加密（AES-256-GCM，PBKDF2-SHA256 派生密钥）。
#                       口令可用 Windows 数据保护接口加密后存本机，
#                       因此开机自启仍可无人值守；跨机器时输入一次该口令即可。
#   dpapi             = 直接用 Windows 数据保护接口（换机器 / 换账户解不开）。
#   plain             = 明文保存（不推荐）。
credential_encryption: passphrase

password_echo: false       # true = 密码可见输入（终端无法输入密码时启用）
log_level: info
```

---

## 7. 改造成你自己学校的模板指南

> 目标：让本项目适配**任意一所学校**的 Web Portal 认证。通常 30 分钟以内可完成。

### 第 1 步：拿到你学校的认证页

1. 连上校园 Wi-Fi，**先不要登录**
2. 浏览器访问一个 **http** 网站（例如 `http://neverssl.com`；**不要用 https**，https 不会跳转）
3. 被拦下后跳转到的页面就是认证页 → **记下 URL**

或者直接双击 `诊断-portal.cmd`，它会自动抓取并保存到 `logs\diagnose-last.txt`。

### 第 2 步：判断认证系统类型

打开认证页源码（F12），对照下表：

| 特征 | 系统 | 改造方式 |
|---|---|---|
| `Dr.COMWebLoginID`、`authloginport=801`、`authuserfield='DDDDD'` | **Dr.COM（城市热点）** | 很可能直接可用：把 `drcom.portal_ip` 改成你的认证服务器 IP |
| `zax`、`wlanacname=zax_*`、`/webauth.do`、端口 8888 | **石斧 zaxsoft** | `portal_type: form`，换 `login_page`，核对 `portal_fields` |
| `srun`、`/cgi-bin/srun_portal`、`ac_id` | **深澜 Srun** | 需新增一种 `portal_type`（见第 3 步情形 C） |
| 表单里有 `username`/`password`/`userId`/`passwd` | 通用表单型 | `portal_type: form`，按 F12 里看到的字段名改 `portal_fields` |
| 页面纯 JS 渲染、看不到表单 | 需抓接口 | F12 → Network → 手动登录一次 → 看那个请求的 URL 与参数 |

`诊断-portal.cmd` 会把页面里所有 `<form>`、`<input name=...>` 打印出来，是判断的主要依据。

### 第 3 步：改配置（多数情况就够了）

**情形 A：Dr.COM 系（含白云）** —— 只改地址：

```yaml
portal_type: drcom_eportal
drcom:
  portal_ip: <你学校认证服务器IP>     # 从认证页源码里的 v4serip 找
  port: 801
  login_path: /eportal/portal/login
```

**情形 B：表单 POST 型** —— 改 `portal_fields`：字段名照抄 F12 里登录请求的参数；
账号与密码字段由代码自动注入，不必写进配置。

**情形 C：两者都不是** —— 改代码（一个小函数）：

1. 打开 `src\Connector.py`，找到 `login()` 方法
2. 其中有一段按 `portal_type` 分发的逻辑；仿照 `_login_drcom()` 写一个新方法，例如 `_login_srun()`
3. 在 `config.yml` 加对应的 `portal_type` 值与参数段
4. **成功判定**：用返回内容里能区分成功/失败的标志（状态码 / JSON 字段 / HTML 关键字）
5. 返回 `True`/`False` 即可 —— 外层会自动做「登录后二次确认」与退避重试

### 第 4 步：实测

1. 在认证状态下点「离线」（或断开 Wi-Fi 重连，**不要手动登录**）
2. 看程序窗口 / `logs\connector-<日期>.log`：
   - 成功：`检测到强制门户，执行自动登录` → `认证返回：result=1` → `自动登录成功`
   - 失败：日志里有认证接口的**原话**（如「账号或密码错误」），照它改配置
3. ⚠️ 测试时手机流量/热点开着作后备 —— 万一登录失败你就暂时没网了

### 第 5 步：换成你自己的账号 / 打包分发

- 删除 `%USERPROFILE%\network_credentials.pkl`（或启动时按提示清除），重新运行并输入
- 打包给别人：改 `config.yml` → 重新执行 PyInstaller 打包（记得 `--add-data "config.yml;."`）
- 建议用 `--onedir`：`--onefile` 需要自解压到 `%TEMP%`，部分环境会被安全策略拦住

### 常见坑（都是真实踩过的）

| 现象 | 原因与处理 |
|---|---|
| 程序一直显示「探针均不可达」，不动手 | 网络本身不通（不是被劫持）→ 按设计**不会**登录；先确认 Wi-Fi 是否真的连上 |
| 日志里出现 `127.0.0.1:10808 ... Read timed out` | 本机装了代理/VPN 客户端（v2rayN 等），而它已关闭；`requests` 默认会自动使用系统代理。**本版本已改为直连（忽略系统代理）**，若仍出现请升级到最新版 |
| 探针返回 `HTTP 200` 却不登录 | 旧版本会误判成"探不明白"；本版本已修正为「200 = 被劫持」 |
| 用 https 网站测试没跳转 | 强制门户只劫持 http；请用 `http://neverssl.com` 之类 |
| 反复登录导致账号被冻结 | 学校禁止账号共享，短时间大量登录会被判异常。本程序已内置退避（最长 60 秒）与防多开 |
| 终端里"输不进密码" | `getpass` **本来就不回显**（屏幕上不会有任何字符）。确实无法输入时把 `password_echo` 改成 `true` |
| 打包成 exe 后找不到日志 | 已修正为「日志跟随 exe 所在目录」；并建议使用 `--onedir` |

---

## 8. 相对上游版本的改动清单

原项目只测试过海珠校区。以下是本项目在其基础上做的改动：

**适配类**

1. 新增 **Dr.COM eportal** 登录方式（`portal_type: drcom_eportal` + `drcom` 配置段）—— 白云校区据此可用
2. 登录表单字段从代码搬进 `config.yml` 的 `portal_fields`，换校区/换学校只改配置
3. 探针支持多个 URL，并各自定义「正常」的判定标准

**修 bug 类**

4. **探针返回 200 被误判成「探不明白」** → 明明被劫持却拒绝登录（白云实测复现并修复）
5. 「探针全部失败」不再触发登录 —— 避免网络抖动时反复 POST 导致账号被判共享冻结
6. 新增**登录后二次确认**：认证接口报成功后再探一次，204 才算真成功
7. 登录尝试加上限（3 次）并改为退避重试（5→10→20→40→60 秒），替代原来的无限重试
8. 修复账号变量因 `input()` 尾逗号成为**单元素元组**的问题，并兼容读取旧版保存的凭据
9. `Updater.fetch()` 加上异常处理 —— 更新检查失败不再导致程序直接退出
10. 修掉横幅字符串的 `SyntaxWarning`

**可运维性**

11. **文件日志**：所有输出同时写入 `logs\connector-<日期>.log`（**不含密码**），断网失败也有据可查
12. **单实例守卫**：同机第二个实例自动退出（写进程序本体，打包成 exe 后依然有效）
13. `password_echo` 开关：终端无法输入密码时可切换为可见输入
14. 打包适配：日志目录跟随 exe；附 `启动-自动登录.cmd`、`诊断-portal.cmd` 与 PyInstaller 打包流程

**网络健壮性**

16. **探测与认证改为直连（忽略系统代理）**：本机代理客户端关闭时，
    `requests` 会自动把请求发给已失效的本地代理导致全部超时，
    程序会误判为"网络不明"而不登录。现改用 `trust_env=False` 的会话直连，
    实测在 `HTTP_PROXY` 指向已关闭代理时仍能正确判断网络状态。

**安全性**

15. **凭据加密存储**：默认改为口令加密（AES-256-GCM + PBKDF2-SHA256，30 万次迭代）；
    口令本身用 Windows 数据保护接口加密后存本机，因此开机自启依然无人值守；
    兼容并自动迁移早期的明文 pickle 与 DPAPI 格式。
    加密后的文件被拷到别的电脑/账户下无法解开（实测：明文不再出现在文件字节流中）

---

## 9. 文件结构

```
ZHKU-Connector-baiyun/
├── src/
│   ├── Connector.py          # 主程序：探测、认证、监测循环（含 Dr.COM 与表单两套登录）
│   ├── LoggerHandler.py      # 日志（控制台 + 文件）
│   ├── Updater.py            # 版本检查（失败不影响使用）
│   └── Utils.py              # 配置读写、凭据存取
├── diagnose.py               # 只读诊断：抓认证页地址与表单字段
├── config.yml                # 全部可配置项（探针、认证方式、字段、密码输入方式）
├── 启动-自动登录.cmd          # 双击启动
├── 诊断-portal.cmd            # 双击诊断（未登录时最有价值）
├── tools/run-connector.ps1   # 启动器（单实例守卫等）
├── logs/                     # 运行日志（自动生成）
├── requirements.txt
├── README.md                 # 本文档
├── README-原作者.md          # 上游项目原始 README（保留备查）
└── LICENSE                   # MIT（上游）
```

---

## 10. 已知限制与未验证项

- **海珠校区未测试**，且其认证系统与白云不同（石斧 vs Dr.COM），本版本中的海珠路径仅作兼容保留
- **其他学校未测试**，仅提供模板化改造路径
- Dr.COM 存在多个版本/部署变体，参数名可能不同（如 `jsVersion`、是否需要 `wlan_user_mac`）；
  请以你自己认证页里的 `auth*` 变量为准
- 不处理：账号欠费/被冻结、需要验证码或短信二次认证、**802.1X / PPPoE 型认证**
  （那类没有 Web 认证页，本项目不适用）
- 不含「下线/注销」功能（如需，Dr.COM 的注销路径为 `/eportal/?c=ACSetting&a=Logout&ver=1.0`）
- 凭据默认以**口令加密**（AES-256-GCM）存于 `%USERPROFILE%\network_credentials.pkl`；
  口令可选保存在 `network_credentials.key`（同样经 Windows 数据保护接口加密，仅本机本账户可解）。
  若把 `credential_encryption` 设为 `plain` 则退回明文 —— 不建议。
  注意：**已解密的凭据在程序运行时仍存在于内存中**，且加密保护的是文件而非进程；
  如机器本身被他人物理使用，请改用不保存凭据的方式（每次手输）

---

## 11. 使用规范与免责声明

- ⚠️ **账号共享限制**：学校规定「每个账号只能同时使用一台电脑 + 一台移动终端，
  检测到共享会冻结账号」。部署到多台设备前**请先取得学校同意**；程序已内置防多开，请勿绕过
- ⚠️ 请遵守你所在学校的网络使用规定；本程序只做「自动填写认证表单」，不绕过任何认证机制
- ⚠️ 配置与凭据文件含敏感信息，请勿上传到公开仓库或公开网盘
- 本项目按 MIT 许可分发，作者不对使用后果负责

---

## 12. 上游与许可

- 上游项目：[Jin-Cheng-Ming/ZHKU-Connector](https://github.com/Jin-Cheng-Ming/ZHKU-Connector)（MIT License）
- 本适配版同样遵循 MIT；上游原始 `README.md` 保留为 `README-原作者.md`
- 白云校区适配与全部改动完成于 2026-10（实测连续 3 次断线自动重登成功）

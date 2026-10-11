"""白云校区 portal 诊断脚本 —— 请在「未登录」状态下运行。

它做什么：
  1. 用多个探针判断当前是否被强制门户劫持，并把跳转地址（Location）打印出来
     —— 那个地址就是白云真实的登录页，里面带着真正的 wlanacname；
  2. 抓取登录页与它引用的 JS，列出所有表单字段（name/value）与页面里出现的
     关键参数，用来核对 config.yml 里的 portal_fields 是否需要改；
  3. 把原始 HTML 存到 diagnose_out/ 方便进一步对照。

它不做什么：
  * 不提交账号密码，不改变你的登录状态，只发普通 GET 请求。

用法：
    1. 连上 ZK-WIFI，但**先别登录**（已登录的话，在 portal 里点「离线」或断开重连）
    2. 在项目根目录运行：  python diagnose.py
    3. 看输出，或把 diagnose_out/ 里的文件发我
"""
import re
import sys
from pathlib import Path

import requests

PROBES = [
    "http://connect.rom.miui.com/generate_204",
    "http://www.gstatic.com/generate_204",
    "http://www.msftconnecttest.com/connecttest.txt",
]
FALLBACK_LOGIN = "http://112.94.15.85:8888/webauth.do"   # 白云 portal 兜底地址
OUT = Path(__file__).resolve().parent / "diagnose_out"


def show(title):
    print("\n" + "=" * 64)
    print(title)
    print("=" * 64)


_SESSION = requests.Session()
_SESSION.trust_env = False      # 直连，不走系统代理（校园网门户是本地的）


def fetch(url, allow_redirects=False, timeout=8):
    try:
        return _SESSION.get(url, allow_redirects=allow_redirects, timeout=timeout,
                            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    except requests.RequestException as e:
        print(f"  请求失败：{url} → {e}")
        return None


def inputs_of(html: str):
    """列出页面里所有 input 的 name/value，以及 form 的 action。"""
    out = []
    for m in re.finditer(r"<form[^>]*>", html, re.I):
        out.append("  form: " + re.sub(r"\s+", " ", m.group(0))[:160])
    for m in re.finditer(r"<input[^>]*>", html, re.I):
        tag = m.group(0)
        name = re.search(r'name=["\']([^"\']*)', tag, re.I)
        value = re.search(r'value=["\']([^"\']*)', tag, re.I)
        typ = re.search(r'type=["\']([^"\']*)', tag, re.I)
        out.append(f"  input: name={name.group(1) if name else '-':<24} "
                   f"type={typ.group(1) if typ else '-':<10} "
                   f"value={(value.group(1)[:40] if value else '-')}")
    return out


def main():
    OUT.mkdir(exist_ok=True)
    print("白云校区 portal 诊断（只读探测，不提交任何账号信息）")

    # ── 1) 探针 ────────────────────────────────────────────────
    show("1) 探针：判断是否被强制门户劫持")
    hijacked_url = None
    for url in PROBES:
        r = fetch(url)
        if r is None:
            continue
        loc = r.headers.get("Location", "")
        print(f"  {url}\n     → HTTP {r.status_code}" + (f"  Location: {loc}" if loc else ""))
        if r.is_redirect and loc and not hijacked_url:
            hijacked_url = loc
    if hijacked_url:
        print(f"\n  ✅ 被劫持，真实登录页 = {hijacked_url}")
        print("     ↑ 请把这一行发给我：里面的 wlanacname 就是白云校区要用的值")
    else:
        print("\n  ⚠️ 没有被劫持：你可能已经在线（或不在校园网内）。")
        print("     请先在 portal 里点「离线」/断开 ZK-WIFI 重连后不要登录，再跑一次本脚本。")

    # ── 2) 登录页 ─────────────────────────────────────────────
    for label, url in (("劫持跳转的登录页", hijacked_url), ("白云兜底登录页", FALLBACK_LOGIN)):
        if not url:
            continue
        show(f"2) {label}：{url}")
        r = fetch(url, allow_redirects=True)
        if r is None or not r.ok:
            continue
        r.encoding = r.apparent_encoding or "utf-8"
        html = r.text
        save = OUT / f"{label}.html"
        save.write_text(html, encoding="utf-8", errors="replace")
        print(f"  HTTP {r.status_code}  长度 {len(html)}  → 已存 {save.name}")
        title = re.search(r"<title>(.*?)</title>", html, re.I | re.S)
        if title:
            print(f"  标题：{title.group(1).strip()[:80]}")
        rows = inputs_of(html)
        if rows:
            print("  表单字段：")
            for x in rows[:30]:
                print(x)
        else:
            print("  页面里没有内联表单（多半是 JS 动态渲染）")
        for kw in ("wlanacname", "nasip", "auth_type", "pageid", "LOGINSUCC", "errMessage"):
            hits = re.findall(rf".{{0,50}}{kw}.{{0,50}}", html, re.I)
            if hits:
                print(f"  含 {kw}：{re.sub(chr(10), ' ', hits[0])[:150]}")
        # 页面引用的 JS 也抓下来找线索
        js_list = re.findall(r'src=["\']([^"\']+\.js[^"\']*)["\']', html, re.I)[:6]
        for js in js_list:
            js_url = js if js.startswith("http") else url.rsplit("/", 1)[0] + "/" + js.lstrip("/")
            jr = fetch(js_url, allow_redirects=True)
            if jr is None or not jr.ok:
                continue
            jr.encoding = jr.apparent_encoding or "utf-8"
            (OUT / f"js_{Path(js).name}").write_text(jr.text, encoding="utf-8", errors="replace")
            for kw in ("webauth", "userId", "passwd", "wlanacname"):
                if re.search(kw, jr.text, re.I):
                    print(f"    [{Path(js).name}] 含 {kw}")

    show("完成")
    print(f"  原始文件都在：{OUT}")
    print("  如果上面打印出了「真实登录页」和表单字段，把它们发我，我就能把 config.yml 定死。")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(1)

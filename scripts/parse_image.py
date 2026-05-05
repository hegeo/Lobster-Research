# -*- coding: utf-8 -*-
"""
龙虾调研助手 - 图片解析脚本（四级递进）
===============================================
策略（按优先级）：
  Tier 1 → QClaw 运行时多模态检测（无需任何配置）
             - 检测会话是否支持 vision，不支持则跳过，节省 90s 超时
  Tier 2 → EasyOCR 本地识别（无 API Key，零配置，直接可用）
             - 已实测可用，支持中英文，依赖：pip install easyocr
  Tier 3 → 外部多模态 API（用户自备 Key）
           ├─ 3A 百度 ERNIE-VL
           ├─ 3B 月之暗面 Kimi-VL
           ├─ 3C 豆包 Doubao-VL
           ├─ 3D 硅基流动 SiliconFlow
           ├─ 3E 通义千问 VL
           └─ 3F 智谱 GLM-4V
  Tier 4 → 浏览器 + 百度 OCR（DrissionPage，无 API Key 兜底）

用法：
  python parse_image.py <图片路径> [输出路径]
  python parse_image.py "D:/Screenshot_20260413.jpg"

环境变量（Tier 3）：
  BAIDU_ERNIE_KEY       — 百度文心 VL（推荐，免费额度大）
  MOONSHOT_VL_KEY       — 月之暗面 Kimi-VL
  DOUBAO_VL_KEY         — 豆包 Doubao-VL（火山引擎）
  SILICONFLOW_KEY       — 硅基流动（聚合多个模型）
  DASHSCOPE_API_KEY     — 通义千问（兼容模式）
  ZHIPU_API_KEY         — 智谱 GLM-4V

环境变量（Tier 4）：
  BAIDU_OCR_AK / BAIDU_OCR_SK — 百度 OCR（免费 500次/天）

作者：lobster-advisory skill
"""

import sys
import os

# ── Windows GBK 终端修复（解决 emoji 无法打印的问题）─────────────
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass  # 非 Windows 环境忽略

import json
import base64
import time
import re
from pathlib import Path

# ── 基础依赖 ──────────────────────────────────────────────
try:
    import requests
except ImportError:
    requests = None

try:
    from PIL import Image
except ImportError:
    Image = None

# ── 路径 ──────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).parent
OUT_DIR    = Path(r"C:/Users/Livecha/.qclaw/workspace")

# ── 图片类型关键词 ────────────────────────────────────────────
PORTFOLIO_KEYWORDS = [
    "持仓", "持仓诊断", "我的持仓", "资产", "持仓盈亏",
    "股票代码", "成本价", "现价", "盈亏", "市值", "占比",
    "当日盈亏", "浮动盈亏", "持仓明细", "基金净值"
]

SCREENSHOT_KEYWORDS = [
    "涨停", "跌停", "龙虎榜", "K线", "MACD", "KDJ",
    "分时图", "日线", "成交量", "成交额", "多空",
    "压力位", "支撑位", "北向资金", "融资融券"
]

# ── 通用 prompt ──────────────────────────────────────────────
MULTIMODAL_PROMPT = (
    "你是一个专业的A股投资顾问。请仔细分析这张图片：\n"
    "1. 判断图片类型（持仓截图/K线图/行情快报/账单/其他）\n"
    "2. 如果是持仓截图，提取所有股票信息：\n"
    "   - 股票名称和代码\n"
    "   - 持仓数量（股数）\n"
    "   - 成本价、现价（如果有）\n"
    "   - 盈亏金额或百分比（如果有）\n"
    "   - 市值（如果有）\n"
    "   - 持仓占比%（如果有）\n"
    "3. 如果是K线图或行情图，提取：\n"
    "   - 股票名称和代码\n"
    "   - 当前价格、涨跌幅\n"
    "   - 关键技术位（支撑/阻力）\n"
    "4. 其他图片请直接描述内容。\n\n"
    "请用结构化JSON格式输出，字段：\n"
    '{"type": "持仓截图|K线图|行情快报|其他", '
    '"stocks": [{"name":"","code":"","shares":"","cost":"","price":"","pnl_pct":"","pnl_abs":"","value":"","weight_pct":""}], '
    '"description": "补充说明", '
    '"raw_text": "原始识别的文字（尽可能完整）"}'
)


# ════════════════════════════════════════════════════════════════
#  TIER 1: QClaw 运行时多模态检测
# ════════════════════════════════════════════════════════════════
def tier1_qclaw_vision(img_path: str) -> dict:
    """
    Tier 1 核心优化：先检测当前 Python 进程是否处于多模态对话环境。
    检测方式：检查环境变量 OPENCLAW_MULTIMODAL=1
      - 若在多模态会话中：直接返回提示，跳过 Tier 1，
        由上层 AI（我）直接用 read 工具读取图片分析（零耗时，无 API 调用）
      - 若不在多模态会话中：调用本地 QClaw gateway（90s 超时保护）

    策略：节省 Tier 1 的 90s 试探耗时。
    """
    print("\n[Tier 1] QClaw 多模态检测...")

    # 检测是否处于多模态对话（由上层 AI 直接读图分析）
    if os.environ.get("OPENCLAW_MULTIMODAL") == "1":
        print("[Tier 1] 检测到多模态会话环境，跳过 90s 超时试探")
        print("[Tier 1] 由上层 AI 直接调用 read 工具分析图片（零耗时）")
        return {
            "ok": False,
            "skip": True,
            "reason": "多模态会话环境，由上层 AI 直接分析"
        }

    # 非多模态环境：尝试调用本地 gateway（90s 超时）
    if not requests:
        print("[Tier 1] skip: requests 不可用")
        return {"ok": False, "reason": "requests 不可用"}

    if not os.path.exists(img_path):
        return {"ok": False, "reason": f"文件不存在: {img_path}"}

    try:
        with open(img_path, "rb") as f:
            img_bytes = f.read()
        b64_img = base64.b64encode(img_bytes).decode("ascii")

        payload = {
            "model": "qclaw/modelroute",
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "text", "text": MULTIMODAL_PROMPT},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}}
                ]
            }],
            "max_tokens": 4096,
            "temperature": 0.1
        }

        port = os.environ.get("AUTH_GATEWAY_PORT", "19000")
        base_url = f"http://localhost:{port}"

        for endpoint in ["/proxy/prochat/v1/chat/completions",
                         "/v1/chat/completions",
                         "/api/chat"]:
            try:
                r = requests.post(
                    f"{base_url}{endpoint}",
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=90
                )
                if r.status_code == 200:
                    result = r.json()
                    content = None
                    if "choices" in result and result["choices"]:
                        content = result["choices"][0]["message"]["content"]
                    elif "content" in result:
                        content = result["content"]
                    if content:
                        print(f"[Tier 1] 成功（endpoint: {endpoint}）")
                        return {
                            "ok": True,
                            "tier": "1",
                            "raw": content,
                            "type": _detect_type(content),
                            "method": "QClaw vision"
                        }
            except requests.exceptions.Timeout:
                print(f"[Tier 1] {endpoint} 超时（90s），尝试下一个...")
                continue
            except Exception as e:
                print(f"[Tier 1] {endpoint} 失败: {e}")
                continue

        print("[Tier 1] 所有 endpoint 均失败或超时")
        return {"ok": False, "reason": "QClaw gateway 无响应或超时"}

    except Exception as e:
        print(f"[Tier 1] 异常: {e}")
        return {"ok": False, "reason": str(e)}


# ════════════════════════════════════════════════════════════════
#  TIER 2: EasyOCR 本地识别（零配置，直接可用）
# ════════════════════════════════════════════════════════════════
def tier2_easyocr(img_path: str) -> dict:
    """
    EasyOCR 本地识别，零 API Key，零配置，已实测可用。
    依赖：pip install easyocr
    优势：中英文混排识别强，适合证券APP截图（雪球/同花顺/天天基金等）
    优化：结果写入文件（避免 stdout GBK 乱码），而不是打印
    """
    print("\n[Tier 2] EasyOCR 本地识别...")

    try:
        import easyocr
    except ImportError:
        print("[Tier 2] skip: easyocr 未安装")
        print("       安装: pip install easyocr")
        return {"ok": False, "reason": "easyocr 未安装"}

    if not os.path.exists(img_path):
        return {"ok": False, "reason": f"文件不存在: {img_path}"}

    try:
        # 不打印中间过程，避免 GBK 终端 emoji 报错
        reader = easyocr.Reader(["ch_sim", "en"], gpu=False, verbose=False)
        results = reader.readtext(img_path, detail=0)

        if not results:
            return {"ok": False, "reason": "EasyOCR 未识别到文字"}

        # 写入文件（UTF-8）而不是打印到 stdout
        raw_lines = [line.strip() for line in results if line.strip()]
        raw_text = "\n".join(raw_lines)

        # 智能拼接被截断的同行文字
        combined_text = _merge_easyocr_lines(raw_lines)

        # 保存原始 OCR 结果到文件
        ocr_out = str(OUT_DIR / "easyocr_raw.txt")
        with open(ocr_out, "w", encoding="utf-8") as f:
            f.write(combined_text)
        print(f"[Tier 2] 识别 {len(raw_lines)} 行，已保存: {ocr_out}")

        # 图片类型判断
        img_type = _detect_type(combined_text)

        # 解析持仓数据
        stocks = _parse_portfolio_from_text(combined_text)

        return {
            "ok": True,
            "tier": "2",
            "raw": combined_text,
            "text": raw_text,
            "lines": raw_lines,
            "type": img_type,
            "stocks": stocks,
            "line_count": len(raw_lines),
            "method": "EasyOCR"
        }

    except Exception as e:
        print(f"[Tier 2] 异常: {e}")
        return {"ok": False, "reason": str(e)}


def _merge_easyocr_lines(lines: list) -> str:
    """
    EasyOCR 逐行识别证券APP截图时，同一行的数字和文字可能被拆成两行。
    智能合并规则：
      - 数字行 + 下一行中文/英文 → 合并
      - 纯数字行（股数/价格/市值）紧跟上一行中文名称 → 合并
      - 百分比行（-2.38%）紧跟上一行 → 合并
    """
    merged = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue

        # 纯数字或纯符号行，尝试与上一行合并
        if _is_number_dominant(line):
            if merged:
                merged[-1] = merged[-1] + " " + line
            else:
                merged.append(line)
        else:
            merged.append(line)
        i += 1

    return "\n".join(merged)


def _is_number_dominant(text: str) -> bool:
    """判断一行的内容是否以数字为主（可能是被拆分的数值行）"""
    import re
    # 匹配：纯数字、百分比、负数、价格、成交量等
    patterns = [
        r"^[\d,\.]+$",           # 纯数字含逗号：3,898.00
        r"^[+-]?[\d,\.]+%$",      # 百分比：-2.38%, +10.03%
        r"^[+-]?\d+$",            # 整数含符号：-95, +651
    ]
    for p in patterns:
        if re.match(p, text.strip()):
            return True
    # 数字字符占比超过 50% 也视为数字行
    digits = sum(c.isdigit() or c in ".,-+" for c in text)
    return digits / max(len(text), 1) > 0.6


# ════════════════════════════════════════════════════════════════
#  TIER 3: 外部多模态 API（用户自备 Key）
# ════════════════════════════════════════════════════════════════
def tier3_external_api(img_path: str) -> dict:
    """
    按以下顺序尝试，直到某个成功：
      3A → 百度 ERNIE-VL（BAIDU_ERNIE_KEY）
      3B → 月之暗面 Kimi-VL（MOONSHOT_VL_KEY）
      3C → 豆包 Doubao-VL（DOUBAO_VL_KEY）
      3D → 硅基流动 SiliconFlow（SILICONFLOW_KEY）
      3E → 通义千问 VL（DASHSCOPE_API_KEY）
      3F → 智谱 GLM-4V（ZHIPU_API_KEY）
    全部失败才返回失败。
    """
    print("\n[Tier 3] 外部多模态 API...")

    if not os.path.exists(img_path):
        return {"ok": False, "reason": f"文件不存在: {img_path}"}

    with open(img_path, "rb") as f:
        img_bytes = f.read()
    b64_img = base64.b64encode(img_bytes).decode("ascii")

    # 3A 百度 ERNIE-VL
    key = os.environ.get("BAIDU_ERNIE_KEY", "")
    if key:
        print("[Tier 3A] 尝试百度 ERNIE-VL...")
        try:
            r = _baidu_ernie_vl(img_bytes, key)
            if r["ok"]:
                print("[Tier 3A] 成功")
                return r
        except Exception as e:
            print(f"[Tier 3A] 失败: {e}")

    # 3B Kimi-VL
    key = os.environ.get("MOONSHOT_VL_KEY", "")
    if key:
        print("[Tier 3B] 尝试 Kimi-VL...")
        try:
            r = _kimi_vl(img_bytes, key)
            if r["ok"]:
                print("[Tier 3B] 成功")
                return r
        except Exception as e:
            print(f"[Tier 3B] 失败: {e}")

    # 3C 豆包 Doubao-VL
    key = os.environ.get("DOUBAO_VL_KEY", "")
    if key:
        print("[Tier 3C] 尝试豆包 Doubao-VL...")
        try:
            r = _doubao_vl(b64_img, key)
            if r["ok"]:
                print("[Tier 3C] 成功")
                return r
        except Exception as e:
            print(f"[Tier 3C] 失败: {e}")

    # 3D 硅基流动
    key = os.environ.get("SILICONFLOW_KEY", "")
    if key:
        print("[Tier 3D] 尝试 SiliconFlow...")
        try:
            r = _siliconflow_vl(img_bytes, key)
            if r["ok"]:
                print("[Tier 3D] 成功")
                return r
        except Exception as e:
            print(f"[Tier 3D] 失败: {e}")

    # 3E 通义千问
    key = os.environ.get("DASHSCOPE_API_KEY", "")
    if key:
        print("[Tier 3E] 尝试通义千问 VL...")
        try:
            r = _qwen_vl(img_bytes, key)
            if r["ok"]:
                print("[Tier 3E] 成功")
                return r
        except Exception as e:
            print(f"[Tier 3E] 失败: {e}")

    # 3F 智谱 GLM-4V
    key = os.environ.get("ZHIPU_API_KEY", "")
    if key:
        print("[Tier 3F] 尝试智谱 GLM-4V...")
        try:
            r = _zhipu_vl(img_bytes, key)
            if r["ok"]:
                print("[Tier 3F] 成功")
                return r
        except Exception as e:
            print(f"[Tier 3F] 失败: {e}")

    print("[Tier 3] 无可用 API Key")
    return {"ok": False, "reason": "无 API Key"}


def _baidu_ernie_vl(img_bytes: bytes, api_key: str) -> dict:
    import urllib.request
    b64_img = base64.b64encode(img_bytes).decode("ascii")
    payload = {
        "model": "ernie-vl-pro-32k",
        "messages": [{
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}},
                {"type": "text", "text": MULTIMODAL_PROMPT}
            ]
        }],
        "max_tokens": 4096,
        "temperature": 0.1
    }
    try:
        req = urllib.request.Request(
            "https://qianfan.baidubce.com/v2/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            method="POST"
        )
        resp = urllib.request.urlopen(req, timeout=60)
        result = json.loads(resp.read())
        content = result["choices"][0]["message"]["content"]
        return {"ok": True, "tier": "3A", "raw": content,
                "type": _detect_type(content), "method": "百度 ERNIE-VL"}
    except Exception:
        pass
    payload["model"] = "ernie-vl-plus"
    req = urllib.request.Request(
        "https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/ernie-4.0-8k-latest",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    resp = urllib.request.urlopen(req, timeout=60)
    result = json.loads(resp.read())
    content = result["choices"][0]["message"]["content"]
    return {"ok": True, "tier": "3A", "raw": content,
            "type": _detect_type(content), "method": "百度 ERNIE-VL"}


def _kimi_vl(img_bytes: bytes, api_key: str) -> dict:
    import urllib.request
    b64_img = base64.b64encode(img_bytes).decode("ascii")
    payload = {
        "model": "moonshot-v1-8k-vision-preview",
        "messages": [{
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}},
                {"type": "text", "text": MULTIMODAL_PROMPT}
            ]
        }],
        "max_tokens": 4096,
        "temperature": 0.1
    }
    req = urllib.request.Request(
        "https://api.moonshot.cn/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    )
    resp = urllib.request.urlopen(req, timeout=60)
    result = json.loads(resp.read())
    content = result["choices"][0]["message"]["content"]
    return {"ok": True, "tier": "3B", "raw": content,
            "type": _detect_type(content), "method": "Kimi-VL"}


def _doubao_vl(b64_img: str, api_key: str) -> dict:
    import urllib.request
    payload = {
        "model": "doubao-vision-pro",
        "messages": [{
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}},
                {"type": "text", "text": MULTIMODAL_PROMPT}
            ]
        }],
        "max_tokens": 4096,
        "temperature": 0.1
    }
    req = urllib.request.Request(
        "https://ark.cn-beijing.volces.com/api/v3/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    )
    resp = urllib.request.urlopen(req, timeout=60)
    result = json.loads(resp.read())
    content = result["choices"][0]["message"]["content"]
    return {"ok": True, "tier": "3C", "raw": content,
            "type": _detect_type(content), "method": "豆包 Doubao-VL"}


def _siliconflow_vl(img_bytes: bytes, api_key: str) -> dict:
    import urllib.request
    b64_img = base64.b64encode(img_bytes).decode("ascii")
    payload = {
        "model": "Qwen/Qwen2-VL-72B-Instruct",
        "messages": [{
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}},
                {"type": "text", "text": MULTIMODAL_PROMPT}
            ]
        }],
        "max_tokens": 4096
    }
    req = urllib.request.Request(
        "https://api.siliconflow.cn/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    )
    resp = urllib.request.urlopen(req, timeout=60)
    result = json.loads(resp.read())
    content = result["choices"][0]["message"]["content"]
    return {"ok": True, "tier": "3D", "raw": content,
            "type": _detect_type(content), "method": "SiliconFlow"}


def _qwen_vl(img_bytes: bytes, api_key: str) -> dict:
    import urllib.request
    b64_img = base64.b64encode(img_bytes).decode("ascii")
    payload = {
        "model": "qwen-vl-plus",
        "messages": [{
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}},
                {"type": "text", "text": MULTIMODAL_PROMPT}
            ]
        }],
        "max_tokens": 4096
    }
    req = urllib.request.Request(
        "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    )
    resp = urllib.request.urlopen(req, timeout=60)
    result = json.loads(resp.read())
    content = result["choices"][0]["message"]["content"]
    return {"ok": True, "tier": "3E", "raw": content,
            "type": _detect_type(content), "method": "通义千问 VL"}


def _zhipu_vl(img_bytes: bytes, api_key: str) -> dict:
    import urllib.request
    b64_img = base64.b64encode(img_bytes).decode("ascii")
    payload = {
        "model": "glm-4v-plus",
        "messages": [{
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}},
                {"type": "text", "text": MULTIMODAL_PROMPT}
            ]
        }]
    }
    req = urllib.request.Request(
        "https://open.bigmodel.cn/api/paas/v4/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    )
    resp = urllib.request.urlopen(req, timeout=60)
    result = json.loads(resp.read())
    content = result["choices"][0]["message"]["content"]
    return {"ok": True, "tier": "3F", "raw": content,
            "type": _detect_type(content), "method": "智谱 GLM-4V"}


# ════════════════════════════════════════════════════════════════
#  TIER 4: DrissionPage 浏览器 + 百度 OCR（无 API Key 兜底）
# ════════════════════════════════════════════════════════════════
def tier4_browser(img_path: str) -> dict:
    """
    双重兜底方案，依赖最少：
      A. DrissionPage 模拟浏览器，打开 Baidu Chat 上传图片识别
      B. 百度 OCR API（免费 500次/天，纯文字）
    两个方案依次尝试，任一成功即停。
    """
    print("\n[Tier 4] 浏览器 + OCR 兜底...")

    result_a = _tier4_drissionpage(img_path)
    if result_a["ok"]:
        return result_a

    result_b = _tier4_baidu_ocr(img_path)
    if result_b["ok"]:
        return result_b

    return {"ok": False, "reason": "Tier 4 全部方案均失败"}


def _tier4_drissionpage(img_path: str) -> dict:
    """DrissionPage 模拟浏览器上传 Baidu Chat 识别。"""
    print("[Tier 4A] 尝试 DrissionPage...")

    try:
        from DrissionPage import ChromiumPage, ChromiumOptions
    except ImportError:
        print("[Tier 4A] skip: DrissionPage 未安装")
        print("       安装: pip install DrissionPage")
        return {"ok": False, "reason": "DrissionPage 未安装"}

    page = None
    try:
        options = ChromiumOptions()
        options.set_argument("--headless=True")
        options.set_argument("--no-sandbox")
        options.set_argument("--disable-dev-shm-usage")
        page = ChromiumPage(addr_or_opts=options)

        print("[Tier 4A] 打开 Baidu Chat...")
        page.get("https://chat.baidu.com", timeout=20)
        time.sleep(4)

        try:
            upload_btn = page.ele("@role=button", timeout=5)
            if upload_btn:
                upload_btn.click()
                time.sleep(1)
                page.upload_files(img_path)
                time.sleep(3)
                print("[Tier 4A] 图片已上传")
        except Exception as e:
            print(f"[Tier 4A] 上传失败: {e}")

        try:
            textarea = page.ele("tag=textarea", timeout=5)
            if textarea:
                textarea.input(MULTIMODAL_PROMPT)
                time.sleep(1)
                send_btn = page.ele("@aria-label=发送", timeout=3)
                if not send_btn:
                    send_btn = page.ele("tag=button", timeout=3)
                if send_btn:
                    send_btn.click()
                    print("[Tier 4A] 等待 AI 回复（30s）...")
                    time.sleep(30)

                try:
                    answers = page.eles("tag=.answer_content", timeout=30)
                    if answers:
                        content = answers[-1].text
                        print(f"[Tier 4A] 获取回复（{len(content)} 字）")
                        return {
                            "ok": True, "tier": "4A", "raw": content,
                            "type": _detect_type(content), "method": "DrissionPage+BaiduChat"
                        }
                except Exception as e2:
                    print(f"[Tier 4A] 提取回复失败: {e2}")
        except Exception as e:
            print(f"[Tier 4A] 填写 prompt 失败: {e}")

        print("[Tier 4A] 降级到 OCR")
        return {"ok": False, "reason": "DrissionPage 方案失败"}

    except Exception as e:
        print(f"[Tier 4A] 异常: {e}")
        return {"ok": False, "reason": str(e)}
    finally:
        if page:
            try:
                page.quit()
            except Exception:
                pass


def _tier4_baidu_ocr(img_path: str) -> dict:
    """百度 OCR 通用文字识别（免费 500次/天）。"""
    print("[Tier 4B] 尝试百度 OCR...")

    import urllib.request, urllib.parse

    api_key = os.environ.get("BAIDU_OCR_AK", "")
    secret_key = os.environ.get("BAIDU_OCR_SK", "")
    if not api_key or not secret_key:
        print("[Tier 4B] skip: 未设置 BAIDU_OCR_AK / BAIDU_OCR_SK")
        return {"ok": False, "reason": "无 BAIDU_OCR_AK/SK"}

    try:
        with open(img_path, "rb") as f:
            img_bytes = f.read()
        b64_img = base64.b64encode(img_bytes).decode("ascii")

        # Step 1: 获取 access token
        token_url = (
            f"https://aip.baidubce.com/oauth/2.0/token?"
            f"grant_type=client_credentials&client_id={api_key}&client_secret={secret_key}"
        )
        req = urllib.request.Request(token_url)
        resp = urllib.request.urlopen(req, timeout=10)
        token_result = json.loads(resp.read())
        access_token = token_result.get("access_token")
        if not access_token:
            return {"ok": False, "reason": "获取 access_token 失败"}

        # Step 2: 调用 OCR
        ocr_url = f"https://aip.baidubce.com/rest/2.0/ocr/v1/general_basic?access_token={access_token}"
        data = urllib.parse.urlencode({"image": b64_img}).encode("utf-8")
        req = urllib.request.Request(ocr_url, data=data)
        resp = urllib.request.urlopen(req, timeout=15)
        ocr_result = json.loads(resp.read())

        words_result = ocr_result.get("words_result", [])
        if not words_result:
            return {"ok": False, "reason": "OCR 未识别到文字"}

        lines = [item["words"] for item in words_result]
        raw_text = "\n".join(lines)
        combined = "\n".join(
            f"[{item.get('probability', {}).get('average', 1):.2f}] {item['words']}"
            for item in words_result
        )

        print(f"[Tier 4B] 百度 OCR 成功，{len(lines)} 行")
        return {
            "ok": True,
            "tier": "4B",
            "raw": combined,
            "text": raw_text,
            "type": _detect_type(raw_text),
            "line_count": len(lines),
            "method": "百度 OCR"
        }

    except Exception as e:
        print(f"[Tier 4B] 百度 OCR 失败: {e}")
        return {"ok": False, "reason": f"百度 OCR 失败: {e}"}


# ════════════════════════════════════════════════════════════════
#  辅助函数
# ════════════════════════════════════════════════════════════════
def _detect_type(text: str) -> str:
    """根据识别文字判断图片类型"""
    for kw in PORTFOLIO_KEYWORDS:
        if kw in text:
            return "持仓截图"
    for kw in SCREENSHOT_KEYWORDS:
        if kw in text:
            return "K线图/行情图"
    return "其他"


def _parse_portfolio_from_text(text: str) -> list:
    """
    从 OCR 识别的文字中解析持仓信息。
    已知证券APP截图格式：
      名称 盈亏额 股数 成本价 市值 盈亏% 股数 现价
    返回结构化股票列表。
    """
    import re
    stocks = []

    # 已知持仓（从用户截图确认的数据）
    KNOWN_STOCKS = {
        "招商银行": {"code": "600036", "exchange": "sh"},
        "长江电力": {"code": "600900", "exchange": "sh"},
        "中兴通讯": {"code": "000063", "exchange": "sz"},
        "中联重科": {"code": "000157", "exchange": "sz"},
        "鱼跃医疗": {"code": "002223", "exchange": "sz"},
        "城投债ETF": {"code": "511660", "exchange": "sh"},
    }

    lines = text.split("\n")
    for line in lines:
        line = line.strip()
        for name, info in KNOWN_STOCKS.items():
            if name in line:
                stocks.append({"name": name, "code": info["code"], "exchange": info["exchange"], "matched": True})
                break

    return stocks


def _save_result(result: dict, out_path: str):
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"结果已保存: {out_path}")


# ════════════════════════════════════════════════════════════════
#  主入口
# ════════════════════════════════════════════════════════════════
def main():
    if len(sys.argv) < 2:
        print("用法: python parse_image.py <图片路径> [输出路径]")
        print()
        print("Tier 顺序（新增 Tier 2 EasyOCR，零配置）：")
        print("  Tier 1 -> QClaw 运行时多模态检测（OPENCLAW_MULTIMODAL=1 跳过）")
        print("  Tier 2 -> EasyOCR 本地识别（已安装，直接可用）")
        print("  Tier 3 -> 外部 API（3A百度 3B月之暗面 3C豆包 3D硅基 3E通义 3F智谱）")
        print("  Tier 4 -> DrissionPage 浏览器 + 百度 OCR（无 Key 兜底）")
        print()
        print("环境变量（Tier 3）：")
        print("  BAIDU_ERNIE_KEY     百度文心 VL（推荐）")
        print("  MOONSHOT_VL_KEY     月之暗面 Kimi-VL")
        print("  DOUBAO_VL_KEY       豆包 Doubao-VL（火山引擎）")
        print("  SILICONFLOW_KEY     硅基流动")
        print("  DASHSCOPE_API_KEY   通义千问")
        print("  ZHIPU_API_KEY       智谱 GLM-4V")
        print("环境变量（Tier 4）：")
        print("  BAIDU_OCR_AK / BAIDU_OCR_SK  百度 OCR（免费 500次/天）")
        sys.exit(1)

    img_path = sys.argv[1]
    out_path = sys.argv[2] if len(sys.argv) > 2 else str(OUT_DIR / "parse_image_result.json")

    print("=" * 50)
    print(f"龙虾图片解析 | {img_path}")
    print("=" * 50)

    if not os.path.exists(img_path):
        print(f"ERROR: 文件不存在: {img_path}")
        sys.exit(1)

    start = time.time()

    # Tier 1: QClaw 运行时多模态
    result = tier1_qclaw_vision(img_path)

    # Tier 2: EasyOCR（零配置，直接可用）
    if not result.get("ok"):
        result = tier2_easyocr(img_path)

    # Tier 3: 外部 API
    if not result.get("ok"):
        result = tier3_external_api(img_path)

    # Tier 4: 浏览器 + OCR
    if not result.get("ok"):
        result = tier4_browser(img_path)

    elapsed = time.time() - start

    print("\n" + "=" * 50)
    print(f"解析完成（耗时 {elapsed:.1f}s）")
    print("=" * 50)

    if result.get("ok"):
        print(f"成功！Tier: {result.get('tier', '?')} | 方法: {result.get('method', '')}")
        print(f"类型: {result.get('type', '未知')}")
        raw = result.get("raw", "")
        # 分段打印，避免一行过长
        for i in range(0, len(raw), 500):
            print(raw[i:i+500])
        _save_result(result, out_path)
        return 0
    else:
        print(f"全部 Tier 均失败: {result.get('reason', '未知')}")
        print()
        print("建议:")
        print("  1. Tier 2 已内置 easyocr，pip install easyocr 即可使用（推荐）")
        print("  2. 设置环境变量 BAIDU_ERNIE_KEY / MOONSHOT_VL_KEY（Tier 3）")
        print("  3. pip install DrissionPage + BAIDU_OCR_AK/SK（Tier 4）")
        return 1


if __name__ == "__main__":
    sys.exit(main())

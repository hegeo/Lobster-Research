#!/usr/bin/env python3
"""
Prompt Manager - 提示词JSON管理脚本
用于查看、创建、修改龙虾研究提示词模板

用法:
  python prompt_manager.py list                      - 列出所有提示词
  python prompt_manager.py get <名称>                 - 查看详细
  python prompt_manager.py cat <名称> <字段>         - 查看指定字段内容
  python prompt_manager.py create <名称> <类型>      - 创建新模板
  python prompt_manager.py update <名称> <字段> <值>  - 修改字段
  python prompt_manager.py update <名称> --json <json> - 完整替换
  python prompt_manager.py fields <名称>              - 查看所有字段
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime

# 配置路径
JSON_DIR = Path(__file__).parent / "json"

# 所有支持的类型
ALL_TYPES = ["快报", "研报", "白皮书", "专家研报"]

# 研究类型到颜色的映射
STYLE_MAP = {
    # 快报类 - 橙色
    "快报": "orange",
    # 金融投资类 - 绿色
    "研报-大盘行情": "green", "研报-持仓诊断": "green", "研报-选股研究": "green", "研报-跨资产研究": "green",
    # 农业食品/资源工业类 - 黄色
    "研报-农业与食品": "yellow", "研报-资源源与工业": "yellow",
    # 生物医疗/消费潮流类 - 粉色
    "研报-生物与医疗": "pink", "研报-消费与潮流": "pink",
    # 科技技术类 - 紫色
    "研报-技术发展": "purple", "研报-科技风向": "purple", "研报-游戏与娱乐": "purple",
    # 通讯物流航运 - 橙色
    "研报-通讯与物流航运": "orange",
    # 社会文化类 - 青色
    "研报-社会发展": "cyan", "研报-文化与艺术": "cyan",
    # 企业财经类 - 蓝色
    "研报-企业发展": "blue", "研报-社会金融": "blue",
    # 期货方向 - 棕色
    "研报-期货方向": "brown",
    # 宇宙地理/行业发展 - 靛蓝
    "研报-宇宙与地理前沿研究": "indigo", "研报-行业发展": "indigo",
    # 战争军事/政治影响力 - 红色
    "研报-战争与军事": "red", "研报-政治与影响力": "red",
}


def get_all_json_files():
    """获取所有JSON文件"""
    if not JSON_DIR.exists():
        JSON_DIR.mkdir(parents=True)
    return sorted(JSON_DIR.glob("*.json"))


def load_json(filename):
    """加载JSON文件"""
    filepath = JSON_DIR / filename
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json(filename, data):
    """保存JSON文件"""
    filepath = JSON_DIR / filename
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write('\n')


def get_style_for_template(name):
    """根据模板名称获取对应的样式颜色"""
    # 先精确匹配
    if name in STYLE_MAP:
        return STYLE_MAP[name]
    # 再模糊匹配快报
    if "快报" in name:
        return STYLE_MAP["快报"]
    # 模糊匹配研报
    if "研报" in name:
        # 尝试匹配具体类型
        for key, value in STYLE_MAP.items():
            if key.startswith("研报-") and key.replace("研报-", "") in name:
                return value
        # 默认研报用蓝色
        return "blue"
    return "blue"  # 默认蓝色


def create_empty_template(name, template_type):
    """创建空的提示词模板"""
    style = get_style_for_template(name)
    template = {
        "name": name,
        "type": template_type,
        "style": style,
        "updateTime": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "author": "lobster-research",
        "parameters": {
            "stockAndMarket": "**，**，**",
            "observationCycle": "季度",
            "observationMode": "国家，地区"
        },
        "recommendedKeywords": ["**", "**", "**"],
        "recommendedDataSources": ["***", "***", "**"],
        "dataRequirements": "实时行情数据、龙虎榜、实时个股数据...",
        "coreIdea": "*********",
        "promptBody": "*************************************************"
    }
    return template


def cmd_list():
    """列出所有提示词"""
    files = get_all_json_files()
    
    print("\n" + "=" * 80)
    print(f"[LIST] 提示词模板列表 (共 {len(files)} 个)")
    print("=" * 80 + "\n")
    
    print(f"{'文件名':<30} {'类型':<12} {'更新时间':<20} {'作者':<20}")
    print("-" * 80)
    
    for f in files:
        try:
            data = load_json(f.name)
            name = data.get('name', f.stem)
            ptype = data.get('type', '未知')
            update_time = data.get('updateTime', '未知')
            author = data.get('author', '未知')
            print(f"{name:<30} {ptype:<12} {update_time:<20} {author:<20}")
        except Exception as e:
            print(f"{f.stem:<30} {'[加载失败]':<12} {str(e)}")
    
    print("-" * 80)
    print("\n[TIP] 使用说明:")
    print("   python prompt_manager.py list                    - 列出所有")
    print("   python prompt_manager.py get <名称>              - 查看详细")
    print("   python prompt_manager.py create <名称> <类型>    - 创建新模板")
    print("   python prompt_manager.py update <名称> <字段> <值> - 修改字段")
    print("   python prompt_manager.py update <名称> --json <json> - 完整替换")
    print("   python prompt_manager.py fields <名称>           - 查看所有字段")
    print("\n[INFO] 支持的类型: " + ", ".join(ALL_TYPES))


def get_matched_file(name):
    """获取匹配的文件，返回(文件, 数据)元组"""
    files = get_all_json_files()
    matches = [f for f in files if name in f.stem]
    
    if not matches:
        return None, None
    if len(matches) > 1:
        print(f"[WARN] 找到多个匹配:")
        for m in matches:
            print(f"   - {m.stem}")
        return None, None
    
    data = load_json(matches[0].name)
    return matches[0], data


def cmd_get(name):
    """查看指定提示词详情"""
    filepath, data = get_matched_file(name)
    
    if filepath is None:
        print(f"[ERROR] 未找到包含 '{name}' 的提示词")
        return
    
    print("\n" + "=" * 80)
    print(f"[DOC] {data.get('name', filepath.stem)}")
    print("=" * 80 + "\n")
    
    print(f"[TYPE]   类型: {data.get('type', '未知')}")
    print(f"[STYLE]  样式: {data.get('style', '未知')}")
    print(f"[TIME]   更新时间: {data.get('updateTime', '未知')}")
    print(f"[AUTHOR] 作者: {data.get('author', '未知')}")
    
    print("\n[PARAMS] 参数:")
    params = data.get('parameters', {})
    for key, value in params.items():
        print(f"   * {key}: {value}")
    
    print("\n[KEYWORDS] 推荐关键词:")
    for kw in data.get('recommendedKeywords', []):
        print(f"   - {kw}")
    
    print("\n[DATASOURCES] 推荐数据源:")
    for ds in data.get('recommendedDataSources', []):
        print(f"   - {ds}")
    
    print(f"\n[DATA_REQUIREMENTS] 数据需求: {data.get('dataRequirements', '无')}")
    print(f"\n[CORE_IDEA] 核心思路: {data.get('coreIdea', '无')}")
    
    prompt_body = data.get('promptBody', '无')
    print(f"\n[PROMPT_BODY] 提示词本体 ({len(prompt_body)} 字符):")
    print("-" * 80)
    print(prompt_body)
    print("-" * 80)


def cmd_cat(name, field):
    """查看指定提示词的指定字段内容"""
    filepath, data = get_matched_file(name)
    
    if filepath is None:
        print(f"[ERROR] 未找到包含 '{name}' 的提示词")
        return
    
    # 支持嵌套字段，如 parameters.stockAndMarket
    if '.' in field:
        parts = field.split('.')
        current = data
        for p in parts:
            if isinstance(current, dict) and p in current:
                current = current[p]
            else:
                print(f"[ERROR] 字段不存在: {field}")
                return
        result = current
    else:
        if field not in data:
            print(f"[ERROR] 字段不存在: {field}")
            print(f"[INFO] 可用字段: {', '.join(data.keys())}")
            return
        result = data[field]
    
    # 根据内容类型格式化输出
    print(f"\n[CAT] {filepath.stem} -> {field}")
    print("=" * 80)
    
    if isinstance(result, (dict, list)):
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(result)
    
    print("=" * 80)


def cmd_create(name, template_type):
    """创建新的提示词模板"""
    if template_type not in ALL_TYPES:
        print(f"[ERROR] 不支持的类型: {template_type}")
        print(f"   支持的类型: {', '.join(ALL_TYPES)}")
        return
    
    # 生成文件名
    filename = f"{name}.json"
    filepath = JSON_DIR / filename
    
    if filepath.exists():
        print(f"[ERROR] 文件已存在: {filename}")
        return
    
    template = create_empty_template(name, template_type)
    save_json(filename, template)
    
    print(f"[OK] 已创建: {filename}")
    print(f"   类型: {template_type}")
    print(f"   路径: {filepath}")


def cmd_update(name, field=None, value=None, json_str=None):
    """更新提示词字段"""
    filepath, data = get_matched_file(name)
    
    if filepath is None:
        return
    
    if json_str:
        # 完整JSON替换
        try:
            new_data = json.loads(json_str)
            save_json(filepath.name, new_data)
            print(f"[OK] 已更新: {filepath.name}")
            print("   完整内容已替换")
        except json.JSONDecodeError as e:
            print(f"[ERROR] JSON格式错误: {e}")
        return
    
    if not field:
        print("[ERROR] 请指定要修改的字段")
        print("   可用字段: name, type, updateTime, author, parameters, recommendedKeywords, recommendedDataSources, dataRequirements, coreIdea, promptBody")
        return
    
    # 处理嵌套字段
    if '.' in field:
        parts = field.split('.')
        current = data
        for p in parts[:-1]:
            if p not in current:
                current[p] = {}
            current = current[p]
        current[parts[-1]] = value
        print(f"[OK] 已更新: {filepath.name}")
        print(f"   {field} -> {value}")
    else:
        # 处理特殊字段
        if field == 'recommendedKeywords' or field == 'recommendedDataSources':
            # 数组字段，支持逗号分隔
            if isinstance(value, str):
                value = [v.strip() for v in value.split(',')]
        elif field == 'parameters':
            # parameters是对象，value应该是JSON字符串
            if isinstance(value, str):
                try:
                    value = json.loads(value)
                except:
                    pass
        
        data[field] = value
        print(f"[OK] 已更新: {filepath.name}")
        val_display = str(value) if len(str(value)) < 100 else str(value)[:100] + '...'
        print(f"   {field} -> {val_display}")
    
    save_json(filepath.name, data)


def cmd_fields(name):
    """查看指定提示词的所有可用字段"""
    filepath, data = get_matched_file(name)
    
    if filepath is None:
        return
    
    print(f"\n[FIELDS] {filepath.stem} 的可用字段:\n")
    
    def print_fields(obj, prefix=""):
        if isinstance(obj, dict):
            for key, value in obj.items():
                path = f"{prefix}.{key}" if prefix else key
                if isinstance(value, (dict, list)):
                    print(f"   {path:<40} ({type(value).__name__})")
                    print_fields(value, path)
                else:
                    val_str = str(value)[:50] + "..." if len(str(value)) > 50 else str(value)
                    print(f"   {path:<40} = {val_str}")
        elif isinstance(obj, list):
            print(f"   {prefix:<40} (list, {len(obj)} items)")
    
    print_fields(data)


def main():
    if len(sys.argv) < 2:
        cmd_list()
        return
    
    cmd = sys.argv[1].lower()
    
    if cmd == 'list' or cmd == 'ls' or cmd == 'l':
        cmd_list()
    elif cmd == 'get' or cmd == 'show':
        if len(sys.argv) < 3:
            print("[ERROR] 请指定要查看的提示词名称")
            print("   用法: python prompt_manager.py get <名称>")
            return
        cmd_get(sys.argv[2])
    elif cmd == 'cat':
        # cat 命令: python prompt_manager.py cat <名称> <字段>
        if len(sys.argv) < 3:
            print("[ERROR] 请指定要查看的提示词名称")
            print("   用法: python prompt_manager.py cat <名称> <字段>")
            print("   示例: python prompt_manager.py cat 快报-持仓 promptBody")
            return
        name = sys.argv[2]
        field = sys.argv[3] if len(sys.argv) > 3 else None
        if not field:
            print("[ERROR] 请指定要查看的字段")
            print("   示例: python prompt_manager.py cat 快报-持仓 promptBody")
            return
        cmd_cat(name, field)
    elif cmd == 'create' or cmd == 'new':
        if len(sys.argv) < 4:
            print("[ERROR] 请指定名称和类型")
            print("   用法: python prompt_manager.py create <名称> <类型>")
            print(f"   类型: {', '.join(ALL_TYPES)}")
            return
        cmd_create(sys.argv[2], sys.argv[3])
    elif cmd == 'update' or cmd == 'set' or cmd == 'edit':
        if len(sys.argv) < 3:
            print("[ERROR] 请指定要修改的提示词")
            print("   用法: python prompt_manager.py update <名称> <字段> <值>")
            print("   或: python prompt_manager.py update <名称> --json '<json>'")
            return
        
        name = sys.argv[2]
        
        if len(sys.argv) > 3 and sys.argv[3] == '--json':
            if len(sys.argv) < 5:
                print("[ERROR] 请提供JSON内容")
                return
            cmd_update(name, json_str=sys.argv[4])
        elif len(sys.argv) > 3:
            cmd_update(name, sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else "")
        else:
            cmd_update(name)
    elif cmd == 'fields' or cmd == 'schema':
        if len(sys.argv) < 3:
            print("[ERROR] 请指定要查看的提示词名称")
            return
        cmd_fields(sys.argv[2])
    else:
        print(f"[ERROR] 未知命令: {cmd}")
        print("\n[TIP] 使用说明:")
        print("   python prompt_manager.py list                       - 列出所有")
        print("   python prompt_manager.py get <名称>                   - 查看详细")
        print("   python prompt_manager.py cat <名称> <字段>            - 查看指定字段")
        print("   python prompt_manager.py create <名称> <类型>         - 创建新模板")
        print("   python prompt_manager.py update <名称> <字段> <值>    - 修改字段")
        print("   python prompt_manager.py update <名称> --json <json>  - 完整替换")
        print("   python prompt_manager.py fields <名称>                - 查看所有字段")
        print("\n   颜色方案: orange, green, yellow, pink, purple, blue, cyan, brown, indigo, red")


if __name__ == '__main__':
    main()

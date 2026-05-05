# PowerShell 执行规范

> ⚡ Windows 环境下的强制规范

---

## 黄金法则

1. **每次 exec 必须加 timeout**
2. **中文输出必须处理编码**
3. **禁止并行 exec，按顺序执行**
4. **Windows 命令行限制 8000 字节**

---

## 基础模板

### 标准执行模板

```powershell
# 每次执行必须加 timeout
python scripts/ticktime.py 2>&1

# 多个命令按顺序执行（禁止并行！）
python scripts/ticktime.py 2>&1      # 等完成
python scripts/websearch_pro.py "关键词" 2>&1    # 再执行
```

### 中文编码处理

```powershell
# 当输出出现乱码时，加编码设置
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
python scripts/websearch_pro.py "关键词" 2>&1
```

### 临时文件写法

```powershell
# PowerShell 不支持 Heredoc，用 Write-Output
Write-Output @"
import json
data = {"key": "value"}
print(json.dumps(data))
"@ > temp_script.py

python temp_script.py
```

---

## 常见错误对照

| 错误 | 错误示例 | 正确做法 |
|:---|:---|:---|
| `&&` 语法 | `python a.py && python b.py` | 分两行或改用 `;` |
| Heredoc | `python <<EOF` | 用 `Write-Output` 写临时文件 |
| 超长命令 | 命令 > 8000 字节 | 先写 `.py` 文件再执行 |
| 并行执行 | 同时发起多个 exec | 等待上一个完成 |
| 中文乱码 | 输出显示为 ??? | 加编码设置 |
| 无 timeout | 命令卡死 | 始终加 `2>&1` 和 timeout |

---

## 复杂任务处理

### 超过 8000 字节的命令

```powershell
# ❌ 错误：直接写超长命令行
python -c "import ...; 很长的代码..."

# ✅ 正确：先写文件再执行
Write-Output @"
import sys
sys.path.insert(0, '.')
from modules.expert_workflow import ExpertReportGenerator

generator = ExpertReportGenerator('000063', '中兴通讯')
result = generator.collect_all_data().build_report().generate()
print(result['pdf_path'])
"@ > run_report.py

python run_report.py
```

### 传递 JSON 数据

```powershell
# 复杂数据写成临时 JSON 文件
$data = @'
{
    "title": "大盘日报",
    "date": "2026-04-22",
    "sections": [{"title": "市场行情", "content": "..."}]
}
'@
$data | Out-File -Encoding UTF8 temp_data.json

python scripts/generate_report.py --data-file temp_data.json
```

---

## 调试技巧

### 查看详细输出

```powershell
# 加上 -v 或 --verbose（如果脚本支持）
python scripts/ticktime.py --verbose 2>&1

# 捕获输出到变量
$output = python scripts/ticktime.py 2>&1
Write-Output $output
```

### 检查 Python 环境

```powershell
# 确认 Python 可用
python --version

# 确认依赖安装
pip list | findstr easyocr
pip list | findstr requests
```

---

## 快速参考卡

```powershell
# 最简单的调用
python scripts/ticktime.py 2>&1

# 带编码设置
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
python scripts/websearch_pro.py "关键词" 2>&1

# 复杂任务先写文件
Write-Output "代码" > script.py
python script.py 2>&1

# 顺序执行多个脚本
python script1.py 2>&1
python script2.py 2>&1
python script3.py 2>&1
```

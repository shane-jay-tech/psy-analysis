# 安装与故障排除指南

**适用版本**: v5.4+

---

## 系统要求

| 组件 | 要求 | 必需 |
|------|------|------|
| Python | 3.10 或更高 | 是 |
| 操作系统 | Windows 10/11 | 是 |
| 内存 | ≥ 4GB | 是 |
| 磁盘空间 | ≥ 500MB | 是 |
| 网络 | 可选（AI 功能需要） | 否 |

---

## 快速安装

### 方式一：使用启动脚本

1. 双击 `run.bat`
2. 等待浏览器自动打开
3. 如果浏览器没有打开，手动访问 `http://localhost:8501`

### 方式二：手动启动

```bash
# 1. 创建虚拟环境
python -m venv .venv

# 2. 激活虚拟环境
.venv\Scripts\activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 启动应用
streamlit run app.py
```

---

## 常见问题

### Python 未安装或版本过低

**现象**: `python` 命令无法识别，或提示版本低于 3.10

**解决**:
1. 从 https://python.org 下载 Python 3.10+
2. 安装时勾选 "Add Python to PATH"
3. 重启终端后验证：`python --version`

### 依赖安装失败

**现象**: `pip install` 报错

**解决**:
- 升级 pip：`python -m pip install --upgrade pip`
- 如果某个包编译失败，尝试安装预编译版本：`pip install --only-binary :all: <包名>`
- 网络问题可用清华镜像：`pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple`

### 端口被占用

**现象**: 启动时提示 "Address already in use" 或 8501 端口冲突

**解决**:
- 关闭其他 Streamlit 实例
- 使用其他端口：`streamlit run app.py --server.port 8502`
- Windows 查看端口占用：`netstat -ano | findstr 8501`

### 中文字体缺失

**现象**: 图表中中文显示为方框

**解决**:
- 安装 SimHei 字体（Windows 通常已有）
- 或安装 Microsoft YaHei
- 重启应用后生效

### Word 导出失败

**现象**: 导出 Word 时报错

**解决**:
- 确认已安装 python-docx：`pip install python-docx`
- Word 文件本身不需要安装 Microsoft Word
- 如果需要 PDF，则需要 Word 或 LibreOffice

### PDF 转换不可用

**现象**: 导出 ZIP 时无 PDF 文件

**说明**: PDF 转换是可选功能
- 安装 Microsoft Word 或 LibreOffice 即可自动转换
- 没有也不影响 Word 和 ZIP 导出
- 可以手动在 Word 中"另存为 PDF"

### LLM API 无法连接

**现象**: AI 辅助功能不可用

**说明**: AI 功能是可选的
- 没有 API Key 时，统计分析、表格生成、导出功能正常
- 只有方法推荐、论文段落润色等 AI 功能不可用
- 配置方法见系统诊断页面

### 系统诊断页面

如果遇到问题，可以：
1. 进入"🔧 系统诊断"页面
2. 点击"运行诊断"
3. 根据结果定位具体问题

---

## 离线可用的功能

即使没有网络和 AI，以下功能完全可用：

- 数据上传和预处理
- 所有统计分析方法
- APA 格式表格生成
- APA 格式图表生成
- 结果卡片和解释
- 一致性检查
- Word/ZIP 交付包导出
- 项目模板使用
- 环境诊断

---

## 需要网络/AI 的功能

- 方法推荐（需要 LLM API Key）
- 论文段落生成（需要 LLM API Key）
- 智能解释增强（需要 LLM API Key）

---

## 获取帮助

如果以上方法无法解决问题：
1. 检查系统诊断页面的详细信息
2. 截图错误提示
3. 联系技术支持并附上截图

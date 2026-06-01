"""Windows 中文字体注册，确保 Plotly 图表中文正常显示"""

import os
import glob


def find_chinese_font() -> str:
    """
    在 Windows 系统上查找可用的中文字体。
    优先级：微软雅黑 > SimHei > SimSun > KaiTi
    """
    font_dir = os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts")

    candidates = [
        "msyh.ttc",        # 微软雅黑
        "msyhbd.ttc",      # 微软雅黑粗体
        "simhei.ttf",      # 黑体
        "simsun.ttc",      # 宋体
        "simkai.ttf",      # 楷体
        "msjh.ttc",        # 微软正黑体（繁体）
        "Deng.ttf",        # DengXian等线
        "Dengb.ttf",       # DengXian等线粗体
    ]

    for font_file in candidates:
        full_path = os.path.join(font_dir, font_file)
        if os.path.exists(full_path):
            return full_path

    # 通配符搜索
    for pattern in ["msyh*", "simhei*", "simsun*"]:
        matches = glob.glob(os.path.join(font_dir, pattern))
        if matches:
            return matches[0]

    return None


def get_font_family() -> str:
    """获取第一个可用的中文字体名称"""
    font_path = find_chinese_font()
    if font_path and "msyh" in font_path.lower():
        return "Microsoft YaHei"
    elif font_path and "simhei" in font_path.lower():
        return "SimHei"
    elif font_path and "simsun" in font_path.lower():
        return "SimSun"
    elif font_path and "simkai" in font_path.lower():
        return "KaiTi"
    else:
        return "sans-serif"


# 缓存
_FONT_FAMILY = None


def get_chinese_font() -> str:
    """获取中文字体名称（带缓存）"""
    global _FONT_FAMILY
    if _FONT_FAMILY is None:
        _FONT_FAMILY = get_font_family()
    return _FONT_FAMILY

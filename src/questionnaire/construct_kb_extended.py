"""知识库扩展存储：由自主学习引擎填充的构念条目

此文件与 construct_kb.py 分离，避免覆盖内置核心条目。
格式与 CONSTRUCTS 完全一致，会在设计引擎中被优先查找。
"""
# 初始为空，扩展条目会在 design_engine 中被优先查找；目前作为预留扩展点
EXTENDED_CONSTRUCTS = {}

"""量表格式建议：Likert点数选择、锚定标签、题量、反向题比例"""


def recommend_scale_points(construct: dict) -> int:
    """
    根据构念特征推荐 Likert 点数。

    5点：大多数情境最适用，被试容易理解，数据质量好
    7点：构念有较宽泛的个体差异范围，如幸福感、态度
    4点：临床筛查场景，去掉"不确定"中点迫使被试倾向性回答
    """
    domain = construct.get("domain", "")
    name = construct.get("name_zh", "")

    # 临床量表多用4点（避免中间倾向）+ 或按典型量表建议
    if domain == "临床与健康":
        if any(kw in name for kw in ["焦虑", "抑郁"]):
            return 4
        return 5

    # 人格量表多用5点
    if domain == "人格":
        return 5

    # 幸福感、态度等宽泛构念用7点
    if any(kw in name for kw in ["幸福", "满意度", "态度"]):
        return 7

    # 认知频率用5点
    if domain == "认知":
        return 5

    # 教育/组织默认5点
    return 5


def get_anchor_labels(points: int, scale_type: str = "agreement") -> list:
    """获取 Likert 锚定标签"""
    anchors = {
        4: {
            "agreement": ["1=完全不同意", "2=不太同意", "3=比较同意", "4=完全同意"],
            "frequency": ["1=从不", "2=偶尔", "3=经常", "4=总是"],
            "satisfaction": ["1=非常不满意", "2=不太满意", "3=比较满意", "4=非常满意"],
        },
        5: {
            "agreement": ["1=完全不同意", "2=不太同意", "3=不确定", "4=比较同意", "5=完全同意"],
            "frequency": ["1=从不", "2=很少", "3=有时", "4=经常", "5=总是"],
            "satisfaction": ["1=非常不满意", "2=不太满意", "3=一般", "4=比较满意", "5=非常满意"],
            "importance": ["1=完全不重要", "2=不太重要", "3=一般", "4=比较重要", "5=非常重要"],
        },
        7: {
            "agreement": [
                "1=完全不同意", "2=不同意", "3=有点不同意",
                "4=不确定", "5=有点同意", "6=同意", "7=完全同意",
            ],
            "frequency": [
                "1=从不", "2=几乎不", "3=偶尔",
                "4=有时", "5=经常", "6=很频繁", "7=总是",
            ],
        },
    }
    return anchors.get(points, {}).get(scale_type, anchors[5]["agreement"])


def recommend_scoring(construct: dict, n_items: int, reverse_items: int) -> str:
    """生成计分说明"""
    points = recommend_scale_points(construct)
    total_range = f"{n_items}~{n_items * points}"

    return (
        f"采用{points}点 Likert 量表计分（1-{points}分）。\n"
        f"正向题：选择1计1分，选择{points}计{points}分。\n"
        f"反向题（共{reverse_items}题）：反向计分（选择1计{points}分，选择{points}计1分）。\n"
        f"总分范围：{total_range}分。"
        f"总分越高表示{construct['name_zh']}水平越高。"
    )


def recommend_item_count(construct: dict) -> dict:
    """基于构念维度结构推荐总题量和每维度题量"""
    dimensions = construct.get("dimensions", [])
    n_dims = len(dimensions)

    if n_dims == 0:
        return {"total": 12, "per_dim": []}

    # 每维度4-8题
    per_dim_counts = [d.get("item_count", min(6, 8 if n_dims <= 2 else 5)) for d in dimensions]
    total = sum(per_dim_counts)

    return {"total": total, "per_dim": per_dim_counts, "dimensions": n_dims}


def reverse_item_ratio(total_items: int) -> dict:
    """推荐反向题数量和比例"""
    # 目标：20%-30% 是反向题
    ratio = 0.25
    n_reverse = max(1, round(total_items * ratio))
    n_reverse = min(n_reverse, total_items // 2)
    return {
        "ratio": round(ratio * 100),
        "n_reverse": n_reverse,
        "rationale": (
            f"建议设置 {n_reverse} 道反向题（约占{round(ratio*100)}%）。"
            "反向题的作用：\n"
            "1) 减少默认反应偏差（被试不看题就选同意的倾向）\n"
            "2) 检测随意作答（正向和反向题答案矛盾说明被试不认真）\n"
            "3) 增加题目变异度"
        ),
    }

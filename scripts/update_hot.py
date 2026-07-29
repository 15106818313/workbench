#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动更新热榜数据 -> hotdata.json
数据源: https://uapis.cn/api/v1/misc/hotboard (免费, 无需 Key)
平台: 抖音(douyin) + 小红书(xiaohongshu), 各取 TOP5
由 GitHub Actions 定时触发 (北京时间 10/15/18/22 点)
"""
import json
import sys
import urllib.request
import urllib.error
from datetime import datetime
from zoneinfo import ZoneInfo

API = "https://uapis.cn/api/v1/misc/hotboard?type={type}"
OUT = "hotdata.json"
BEIJING = ZoneInfo("Asia/Shanghai")

PLAT_MAP = {
    "douyin":      {"plat": "dy",  "platName": "抖音",  "rankPrefix": "DY-",  "medal": "🏆"},
    "xiaohongshu": {"plat": "xhs", "platName": "小红书", "rankPrefix": "XHS-", "medal": "🥈"},
}


def fetch(platform):
    url = API.format(type=platform)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def to_num(v):
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip()
    for suf, mul in (("亿", 1e8), ("w", 1e4), ("万", 1e4)):
        if s.endswith(suf):
            try:
                return float(s[:-len(suf)]) * mul
            except ValueError:
                return 0.0
    try:
        return float(s)
    except ValueError:
        return 0.0


def fmt_heat(v):
    n = to_num(v)
    if n >= 1e8:
        return f"{n/1e8:.1f}亿"
    if n >= 1e4:
        return f"{n/1e4:.1f}w"
    return str(int(n)) if n else str(v)


def classify(title):
    t = title
    if any(k in t for k in ["美食", "菜", "教程", "做法", "配方", "烘焙", "食谱"]):
        return "food"
    if any(k in t for k in ["拍照", "出片", "机位", "旅行", "风景", "日照金山", "海鸥",
                            "雪山", "湖", "日落", "穿搭", "妆", "美甲", "拍照姿势"]):
        return "visual"
    if any(k in t for k in ["足球", "绝平", "比赛", "赛事", "夺冠", "输", "赢", "联赛", "NBA", "球"]):
        return "sports"
    if any(k in t for k in ["古诗", "诗词", "汉服", "文化", "非遗", "历史", "传统", "中国", "河南", "古籍"]):
        return "culture"
    if any(k in t for k in ["AI", "科技", "芯片", "大模型", "手机", "发布", "数码", "算法"]):
        return "tech"
    return "general"


TPL = {
    "food": {
        "why": "美食教程类流量大,易模仿,收藏率高",
        "plan": "开头:成品诱惑镜头 → 4 步流程每步 15 秒 → 食材清单 → 替代食材与翻车提醒",
        "voice": "快节奏剪辑,ASMR 收音,字幕清晰",
    },
    "visual": {
        "why": "画面感强,教程/治愈类内容完播率高",
        "plan": "开头:一张成片 → 拆解机位/姿势/光线 → 取景范围 → 手机参数 → 注意事项",
        "voice": "配氛围 BGM,慢镜头,纪录片感",
    },
    "sports": {
        "why": "赛事情绪爆发点,评论区互动强",
        "plan": "开头:高光瞬间回放 → 关键节点卡片 → 情绪转折解读 → 球迷反应集锦",
        "voice": "激情叙述,赛事原声配合",
    },
    "culture": {
        "why": "文化类正能量,易获推荐与转发",
        "plan": "开头:一句钩子 → 选 3 个知识点对应 3 个场景 → 每点讲背后故事 → 互动号召",
        "voice": "沉稳叙述,配古风/舒缓 BGM",
    },
    "tech": {
        "why": "科技热点讨论度高,理工受众黏性强",
        "plan": "开头:一句话结论 → 3 个核心看点 → 对比旧方案 → 适用人群提醒",
        "voice": "理性克制,数据图表配合",
    },
    "general": {
        "why": "话题热度高,讨论空间大,适合二创切入",
        "plan": "开头:抛出话题钩子 → 3 个角度拆解 → 你的观点 → 结尾互动提问",
        "voice": "真人出镜,自然叙述,中文字幕",
    },
}


def build():
    inspiration, hot = [], []
    now = datetime.now(BEIJING)
    update_time = now.strftime("%Y-%m-%d %H:%M")
    slot = now.strftime("%H:00")

    for platform, meta in PLAT_MAP.items():
        try:
            data = fetch(platform)
        except (urllib.error.URLError, urllib.error.HTTPError, ValueError) as e:
            print(f"[WARN] 拉取 {meta['platName']} 失败: {e}", file=sys.stderr)
            continue

        items = (data.get("list") or [])[:5]
        if not items:
            print(f"[WARN] {meta['platName']} 返回空数据,跳过", file=sys.stderr)
            continue

        for i, it in enumerate(items, start=1):
            title = (it.get("title") or "").strip()
            if not title:
                continue
            heat_raw = it.get("hot_value", it.get("hot", 0))
            heat = fmt_heat(heat_raw)
            likes_num = to_num(heat_raw)
            favs_num = likes_num * 0.3
            favs = fmt_heat(favs_num) if favs_num else fmt_heat(likes_num * 0.3)
            cat = classify(title)
            tpl = TPL[cat]
            score = max(85, 96 - (i - 1) * 2)
            rank_code = f"{meta['rankPrefix']}{i:02d}"
            medal = meta["medal"]

            inspiration.append({
                "id": f"insp-{meta['plat']}-{i:02d}",
                "rank": rank_code,
                "title": title,
                "plat": meta["plat"],
                "platName": meta["platName"],
                "heat": f"🔥 热度 {heat}",
                "growth": f"📈 {meta['platName']} TOP{i:02d}",
                "summary": f"来源:{update_time} {meta['platName']}热搜 TOP{i:02d}。热度 {heat},真实上榜话题。",
            })

            rank_class = "gold" if i == 1 else ("silver" if i == 2 else "")
            hot.append({
                "id": f"hot-{meta['plat']}-{i:02d}",
                "rank": f"{medal} {rank_code}",
                "rankClass": rank_class,
                "title": title,
                "plat": meta["plat"],
                "platName": meta["platName"],
                "likes": f"👍 {heat}",
                "favs": f"⭐ {favs}",
                "score": score,
                "why": tpl["why"],
                "plan": tpl["plan"],
                "voice": tpl["voice"],
            })

    if not inspiration or not hot:
        print("[ERROR] 未获取到任何热榜数据,不覆盖原文件。", file=sys.stderr)
        sys.exit(1)

    out = {
        "updateTime": update_time,
        "platforms": ["抖音", "小红书"],
        "inspiration": inspiration,
        "hot": hot,
        "lastSlot": f"北京时间 {slot}",
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"[OK] 已生成 {OUT}: 抖音 {sum(1 for x in inspiration if x['plat']=='dy')} 条, "
          f"小红书 {sum(1 for x in inspiration if x['plat']=='xhs')} 条 | 更新时间 {update_time}")


if __name__ == "__main__":
    build()

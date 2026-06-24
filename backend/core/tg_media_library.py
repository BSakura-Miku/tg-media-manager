#!/usr/bin/env python3
from __future__ import annotations

from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
import argparse
import csv
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import time
from io import StringIO

try:
    from PIL import Image
except Exception:
    Image = None


DEFAULT_ROOT = "/media"
VIDEO_EXT = {".mp4", ".mov", ".m4v", ".mkv", ".avi", ".webm"}
PHOTO_EXT = {".jpg", ".jpeg", ".png", ".webp", ".heic"}
ORGANIZED_TOPS = {"_MANIFESTS", "_REVIEW", "Actors", "Mixed", "_DUPLICATES"}
HASH_CHUNK = 1024 * 1024

AD_PATTERNS = [
    r"电报\s*搜",
    r"telegram",
    r"\btg\b",
    r"频道",
    r"推广",
    r"完整资源",
    r"置顶",
    r"复制口令",
    r"迷路",
    r"订阅",
    r"更多",
    r"资源",
    r"@[\w_]{3,}",
    r"www\.",
    r"https?",
]

AGE_REVIEW_PATTERNS = [
    r"未成年",
    r"未满",
    r"高中",
    r"初中",
    r"中学生",
    r"小学生",
    r"幼",
    r"萝莉",
    r"\bjk\b",
    r"jk",
    r"校服",
    r"学生",
    r"1[2-7]\s*岁",
]

GENERIC_WORDS = {
    "推特",
    "twitter",
    "x",
    "onlyfans",
    "of",
    "fc2",
    "stripchat",
    "telegram",
    "tg",
    "电报",
    "视频",
    "图片",
    "合集",
    "精选",
    "原创",
    "国产",
    "日本",
    "番号",
    "有码",
    "无码",
    "高清",
    "流出",
    "偷拍",
    "自拍",
    "露脸",
    "网红",
    "抖音",
    "b站",
    "糖心",
    "草莓视频",
    "document",
    "new",
    "processed",
    "tweeload",
    "chinese",
    "img",
    "vid",
    "video",
    "mp4",
    "mov",
    "jpg",
    "jpeg",
    "png",
    "ds",
    "agad",
    "batch",
    "date",
}

DESCRIPTOR_WORDS = {
    "颜值",
    "高颜值",
    "可爱",
    "清纯",
    "纯欲",
    "美少女",
    "少女",
    "女神",
    "御姐",
    "学妹",
    "学姐",
    "学生",
    "高中生",
    "日本jk",
    "jk",
    "萝莉",
    "福利姬",
    "反差",
    "反差婊",
    "母狗",
    "女友",
    "情侣",
    "老婆",
    "女大",
    "小女友",
    "女上",
    "女仆",
    "大学生",
    "女骑士",
    "骑乘",
    "后入",
    "口交",
    "足交",
    "自慰",
    "掰穴",
    "露出",
    "啪啪啪",
    "啪啪",
    "做爱",
    "中出",
    "内射",
    "无套",
    "调教",
    "捆绑",
    "榨精",
    "白虎",
    "极品",
    "炮机",
    "嫩穴",
    "嫩逼",
    "嫩鲍",
    "美乳",
    "美臀",
    "大奶",
    "巨乳",
    "贫乳",
    "黑丝",
    "白丝",
    "丝袜",
    "双马尾",
    "足控",
    "蜜桃臀",
    "大白奶子",
    "震动棒",
    "写真",
    "眼镜妹",
    "白袜",
    "颜射",
    "户外",
    "原神",
    "瑜伽裤",
    "意淫自己妹妹",
    "喷水",
    "美穴",
    "汉服",
    "调教女友口交",
    "泄密反差婊",
    "紧急企划",
    "小恶魔",
    "擦边",
    "cos",
    "cosplay",
    "原创",
    "定制",
    "新档",
    "寄快递",
    "逛街",
    "露出",
    "反差婊",
    "网黄",
    "蜂腰",
    "美腿",
    "妹妹",
    "兄妹",
    "乱伦",
    "飞机杯",
    "姿势",
    "肉棒",
    "小穴",
    "骚",
    "操",
    "肏",
    "射",
    "插",
    "喷",
    "口",
    "逼",
    "穴",
    "坐骑",
    "停车场",
    "楼梯间",
    "面试",
    "会员群",
    "格式原因",
    "完整版",
    "鉴赏",
    "痒",
    "不射",
    "中出",
    "口",
    "修理工",
    "强迫",
    "半个月",
    "危险",
    "可恶",
    "教学",
    "艹",
    "援交",
    "掐脖子",
    "核弹",
    "喷射",
    "白丝",
    "自拍",
    "社区",
    "学院",
    "爸爸",
    "点个赞",
}

PROMO_ACCOUNTS = {
    "rewudingzh",
    "aifcb",
    "nvyoupd",
    "tgbalin",
    "dashen1256",
    "ssck999",
    "ssck666",
    "ysjzyhj",
    "fulidashu888",
}

KEYWORD_CATEGORIES = [
    ("JK学生", ["jk", "学生", "校服", "高中", "学妹", "学姐", "学生装"]),
    ("水手服制服", ["水手服", "水手", "制服", "学院风", "百褶裙", "领结"]),
    ("死库水泳装", ["死库水", "泳装", "泳衣", "竞泳", "比基尼", "school swimsuit"]),
    ("COS角色", ["cos", "cosplay", "原神", "王者荣耀", "角色", "女仆", "巫女", "汉服", "洛丽塔"]),
    ("黑丝白丝", ["黑丝", "白丝", "丝袜", "网袜", "吊带袜", "裤袜"]),
    ("自拍露脸", ["自拍", "露脸", "反差"]),
    ("室外户外", ["户外", "室外", "街拍", "停车场", "公园", "海边", "楼梯"]),
    ("室内居家", ["室内", "居家", "卧室", "浴室", "客厅", "酒店", "宿舍", "教室"]),
    ("足交足控", ["足交", "足控", "美足", "足底"]),
    ("调教捆绑", ["调教", "捆绑", "狗链", "乳夹", "项圈"]),
    ("口交", ["口交", "深喉"]),
    ("内射中出", ["内射", "中出"]),
    ("道具自慰", ["道具", "自慰", "跳蛋", "震动棒", "假阳具"]),
]

CONTROL_RE = re.compile(r"[\x00-\x1f\x7f]")


@dataclass
class Config:
    root: Path
    output_root: Path | None = None
    source_dirs: list[str] | None = None
    fast: bool = True

    @property
    def library_root(self) -> Path:
        return self.output_root or self.root

    @property
    def manifests(self) -> Path:
        return self.library_root / "_MANIFESTS"

    @property
    def review(self) -> Path:
        return self.library_root / "_REVIEW"


def media_type(ext: str) -> str:
    if ext in VIDEO_EXT:
        return "video"
    if ext in PHOTO_EXT:
        return "photo"
    return "other"


def safe_component(value: str, fallback: str = "Unknown") -> str:
    value = CONTROL_RE.sub("", value)
    value = value.replace("/", "_").replace(":", "_").replace("\\", "_")
    value = re.sub(r"\s+", " ", value).strip(" ._-")
    return (value or fallback)[:80]


def rel(root: Path, path: Path) -> str:
    return str(path.relative_to(root))


def partial_hash(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        size = path.stat().st_size
        with path.open("rb") as handle:
            digest.update(handle.read(HASH_CHUNK))
            if size > HASH_CHUNK * 2:
                handle.seek(max(0, size - HASH_CHUNK))
                digest.update(handle.read(HASH_CHUNK))
        digest.update(str(size).encode())
        return digest.hexdigest()
    except Exception as exc:
        return "ERR_" + type(exc).__name__


def md5_hash(path: Path) -> str:
    digest = hashlib.md5()
    try:
        with path.open("rb") as handle:
            while True:
                chunk = handle.read(HASH_CHUNK)
                if not chunk:
                    break
                digest.update(chunk)
        return digest.hexdigest()
    except Exception as exc:
        return "ERR_" + type(exc).__name__


def ffprobe_info(path: Path, fast: bool) -> tuple[str, str, str, str, str]:
    if fast:
        return "", "", "", "", ""
    try:
        cmd = [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height,duration:format=duration:format_tags=creation_time",
            "-of",
            "json",
            str(path),
        ]
        out = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=12)
        if out.returncode != 0:
            return "", "", "", "", "ffprobe_error"
        data = json.loads(out.stdout or "{}")
        stream = (data.get("streams") or [{}])[0]
        fmt = data.get("format") or {}
        return (
            str(stream.get("duration") or fmt.get("duration") or ""),
            str(stream.get("width") or ""),
            str(stream.get("height") or ""),
            str((fmt.get("tags") or {}).get("creation_time", "")),
            "",
        )
    except Exception as exc:
        return "", "", "", "", type(exc).__name__


def image_info(path: Path, fast: bool) -> tuple[str, str, str, str, str]:
    if fast:
        return "", "", "", "", ""
    if Image is None:
        return "", "", "", "", "pil_unavailable"
    try:
        with Image.open(path) as img:
            exif_date = ""
            try:
                exif = img.getexif()
                exif_date = exif.get(36867) or exif.get(306) or ""
            except Exception:
                pass
            return "", str(img.size[0]), str(img.size[1]), str(exif_date), ""
    except Exception as exc:
        return "", "", "", "", type(exc).__name__


def normalize_date(mtime: float, creation: str) -> tuple[str, str]:
    if creation:
        match = re.search(r"(20\d\d)[-:]?(\d\d)[-:]?(\d\d)[T _:]?(\d\d)?[:]?(\d\d)?[:]?(\d\d)?", creation)
        if match:
            year, month, day, hour, minute, second = match.groups()
            return f"{year}{month}{day}_{hour or '00'}{minute or '00'}{second or '00'}", "metadata"
    return time.strftime("%Y%m%d_%H%M%S", time.localtime(mtime)), "mtime"


def duration_slug(duration: str) -> str:
    try:
        seconds = int(float(duration))
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        if hours:
            return f"{hours}h{minutes:02d}m{secs:02d}s"
        if minutes:
            return f"{minutes}m{secs:02d}s"
        return f"{secs}s"
    except Exception:
        return "durNA"


def resolution_slug(width: str, height: str) -> str:
    return f"{width}x{height}" if width and height else "resNA"


def compact_token(token: str) -> str:
    return re.sub(r"[\s_\-·・.。:：/\\|]+", "", token.lower())


def has_cjk_or_kana(token: str) -> bool:
    return bool(re.search(r"[\u3400-\u9fff\u3040-\u30ff]", token))


def looks_like_random_or_batch_name(token: str) -> bool:
    low = token.lower()
    compact = compact_token(token)
    if re.fullmatch(r"[0-9a-f]{8,64}", low):
        return True
    if re.search(r"\d", token) and not has_cjk_or_kana(token):
        return True
    if re.fullmatch(r"[a-z0-9]{12,64}", low) and not has_cjk_or_kana(token):
        return True
    if re.fullmatch(r"[A-Z]{2,8}\d{2,6}", token):
        return True
    if re.fullmatch(r"\d+\.mp4", low):
        return True
    if re.fullmatch(r"[A-Z]{5,16}", token):
        return True
    if re.fullmatch(r"[A-Za-z0-9]{8,64}", token) and re.search(r"[A-Z]", token) and re.search(r"[a-z]", token):
        return True
    if re.fullmatch(r"[A-Za-z]{5,16}", token) and re.search(r"[A-Z]", token) and re.search(r"[a-z]", token) and not re.fullmatch(r"[A-Z][a-z]{4,15}", token):
        return True
    if re.fullmatch(r"[A-Za-z0-9]{5,64}", token) and re.search(r"\d", token) and re.search(r"[A-Z]", token) and not has_cjk_or_kana(token):
        return True
    if re.fullmatch(r"\d+(\(\d+\))?", token):
        return True
    if re.match(r"^\d{1,2}月\d{1,2}日", token):
        return True
    if re.match(r"^\d{2,4}", token) and has_cjk_or_kana(token):
        return True
    if "(" in token or ")" in token or "（" in token or "）" in token:
        return True
    if has_cjk_or_kana(token) and len(token) > 6:
        return True
    if any(ch in token for ch in "[]【】「」"):
        return True
    if re.search(r"[，。！？、,.!?😍🤤]", token):
        return True
    if re.search(r"(原创|定制|新档|露出|妹妹|兄妹|乱伦|反差|网黄|万粉|嫩穴|激情|销魂|不射|中出|修理工|强迫|危险|教学|艹|援交|掐脖子|核弹|喷射|白丝|自拍|社区|学院|爸爸|点个赞|痒)", compact):
        return True
    return False


def is_ad_or_description(token: str) -> bool:
    low = token.lower()
    compact = compact_token(token)
    if not token or len(token) < 2 or len(token) > 32:
        return True
    if "@" in token or low.startswith("tg"):
        return True
    if low in PROMO_ACCOUNTS:
        return True
    if compact in {compact_token(x) for x in GENERIC_WORDS | DESCRIPTOR_WORDS}:
        return True
    if any(re.search(pattern, low, re.I) for pattern in AD_PATTERNS):
        return True
    if re.search(r"\b[a-z0-9-]+\.(cc|com|net|org|la|tv)\b", low):
        return True
    if re.fullmatch(r"\d+", token):
        return True
    if re.fullmatch(r"\d+月\d+日", token):
        return True
    if re.fullmatch(r"(20)?\d{2}[-_.]?\d{1,2}[-_.]?\d{1,2}", token):
        return True
    if re.fullmatch(r"agad[a-z0-9_\\-]+", low):
        return True
    if re.fullmatch(r"[a-z]{1,4}", low):
        return True
    if looks_like_random_or_batch_name(token):
        return True
    if re.search(r"(女上|女仆|啪啪啪|啪啪|颜值|日本jk|电报搜|资源|频道|合集|精选|高清|极品|炮机|大学生|嫩逼|震动棒|写真|眼镜妹|白袜|颜射|户外|原神|瑜伽裤|自己妹妹|喷水|美穴|汉服)", compact):
        return True
    return False


def clean_actor_token(token: str) -> str:
    token = token.strip().strip("#@[]()（）【】,，.。:：;；!！?？'\"“” ")
    token = re.sub(r"^(推特|twitter|x|onlyfans|of|fc2|coser|福利姬)[-_ ]*", "", token, flags=re.I)
    token = safe_component(token, "")
    if is_ad_or_description(token):
        return ""
    return token


def actor_candidates(name: str) -> list[str]:
    stem = Path(name).stem
    candidates: list[str] = []

    for match in re.finditer(r"#([^#@\s_\-，,。:：;；【】\[\]()（）]+)", stem):
        token = clean_actor_token(match.group(1))
        if token:
            candidates.append(token)

    # Prefix-based names are useful for "#actor_..." dumps, but reject Telegram media ids first.
    prefix = re.split(r"[_\- ]", stem, maxsplit=1)[0]
    if not prefix.startswith("#") and not re.fullmatch(r"AgAD[A-Za-z0-9_-]+", prefix):
        token = clean_actor_token(prefix)
        if token:
            candidates.append(token)

    # Bare @ handles are usually promo channels in this dataset, so do not use them as actor names.
    seen: list[str] = []
    for candidate in candidates:
        if candidate not in seen:
            seen.append(candidate)
    return seen[:5]


def flags_for(name: str) -> str:
    low = name.lower()
    flags = []
    if any(re.search(pattern, low, re.I) for pattern in AD_PATTERNS):
        flags.append("ad_or_promo")
    if any(re.search(pattern, low, re.I) for pattern in AGE_REVIEW_PATTERNS):
        flags.append("needs_age_review")
    if len(name) > 180:
        flags.append("very_long_name")
    return ";".join(flags)


def keyword_category(text: str) -> str:
    compact = compact_token(text)
    low = text.lower()
    for category, keywords in KEYWORD_CATEGORIES:
        for keyword in keywords:
            if keyword.lower() in low or compact_token(keyword) in compact:
                return category
    return ""


def ensure_dirs(config: Config) -> None:
    for directory in [
        config.manifests,
        config.review / "UnknownActor",
        config.review / "NeedsManualCheck",
        config.review / "Duplicates",
        config.library_root / "Actors",
        config.library_root / "Mixed",
    ]:
        directory.mkdir(parents=True, exist_ok=True)


def iter_source_files(config: Config):
    sources = [config.root / item.strip().strip("/") for item in (config.source_dirs or []) if item.strip()]
    if not sources:
        sources = [config.root]
    for source in sources:
        if not source.exists():
            continue
        for dirpath, dirnames, filenames in os.walk(source):
            current = Path(dirpath)
            dirnames[:] = [d for d in dirnames if not (current == config.root and d in ORGANIZED_TOPS)]
            for filename in filenames:
                path = current / filename
                if path.is_file():
                    yield path


def build_rows(config: Config) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    scanned = 0
    for path in iter_source_files(config):
        try:
            stat = path.stat()
        except Exception:
            continue
        ext = path.suffix.lower() or "[none]"
        kind = media_type(ext)
        digest = partial_hash(path)
        duration = width = height = creation = media_error = ""
        if kind == "video":
            duration, width, height, creation, media_error = ffprobe_info(path, config.fast)
        elif kind == "photo":
            duration, width, height, creation, media_error = image_info(path, config.fast)
        date_key, date_source = normalize_date(stat.st_mtime, creation)
        year_month = f"{date_key[:4]}-{date_key[4:6]}" if re.match(r"20\d{6}_", date_key) else time.strftime("%Y-%m", time.localtime(stat.st_mtime))
        actors = actor_candidates(path.name)
        flags = flags_for(path.name)
        if media_error:
            flags = (flags + ";" if flags else "") + "media_probe_error"
        rows.append(
            {
                "original_path": rel(config.root, path),
                "original_name": path.name,
                "extension": ext,
                "type": kind,
                "size_bytes": str(stat.st_size),
                "mtime": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat.st_mtime)),
                "hash": digest,
                "hash8": digest[:8] if not digest.startswith("ERR_") else digest,
                "duration": duration,
                "width": width,
                "height": height,
                "creation_time": creation,
                "date_key": date_key,
                "date_source": date_source,
                "year_month": year_month,
                "actor_candidates": "|".join(actors),
                "canonical_actor": actors[0] if len(actors) == 1 else "",
                "flags": flags,
                "media_error": media_error,
            }
        )
        scanned += 1
        if scanned % 1000 == 0:
            print(f"scanned {scanned} files", flush=True)
    return rows


def mark_duplicates(rows: list[dict[str, str]]) -> None:
    groups: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        groups[(row["type"], row["size_bytes"], row["hash"])].append(row)
    for key, members in groups.items():
        if len(members) > 1 and not str(key[2]).startswith("ERR_"):
            for index, row in enumerate(sorted(members, key=lambda item: item["original_path"])):
                extra = "duplicate_keep" if index == 0 else "duplicate_candidate"
                row["flags"] = (row["flags"] + ";" if row["flags"] else "") + extra


def planned_path(config: Config, row: dict[str, str], used_paths: Counter) -> str:
    ext = row["extension"] if row["extension"] != "[none]" else ""
    kind = row["type"]
    flags = set(filter(None, row["flags"].split(";")))
    if kind not in {"video", "photo"}:
        base_dir = config.review / "NeedsManualCheck"
        prefix = "FILE"
    elif "duplicate_candidate" in flags:
        base_dir = config.review / "Duplicates" / kind.capitalize()
        prefix = "VID" if kind == "video" else "IMG"
    elif "needs_age_review" in flags:
        base_dir = config.review / "NeedsManualCheck" / "AgeReview" / kind.capitalize()
        prefix = "VID" if kind == "video" else "IMG"
    elif "media_probe_error" in flags:
        base_dir = config.review / "NeedsManualCheck" / kind.capitalize()
        prefix = "VID" if kind == "video" else "IMG"
    elif not row["canonical_actor"]:
        category = keyword_category(row["original_name"])
        if category:
            media_folder = "Videos" if kind == "video" else "Photos"
            base_dir = config.review / "Keywords" / category / media_folder
        else:
            base_dir = config.review / "UnknownActor" / kind.capitalize() / row["year_month"]
        prefix = "VID" if kind == "video" else "IMG"
    else:
        media_folder = "Videos" if kind == "video" else "Photos"
        base_dir = config.library_root / "Actors" / safe_component(row["canonical_actor"]) / media_folder
        prefix = "VID" if kind == "video" else "IMG"

    if kind == "video":
        filename = f"{prefix}_{row['date_key']}_{duration_slug(row['duration'])}_{resolution_slug(row['width'], row['height'])}_{row['hash8']}{ext}"
    elif kind == "photo":
        filename = f"{prefix}_{row['date_key']}_{resolution_slug(row['width'], row['height'])}_{row['hash8']}{ext}"
    else:
        filename = f"{prefix}_{row['date_key']}_{row['hash8']}_{safe_component(row['original_name'], 'file')}"
    candidate = rel(config.library_root, base_dir / filename)
    used_paths[candidate] += 1
    if used_paths[candidate] > 1:
        p = Path(candidate)
        candidate = str(p.with_name(f"{p.stem}_{used_paths[candidate]:03d}{p.suffix}"))
    return candidate


def write_scan_outputs(config: Config, rows: list[dict[str, str]]) -> None:
    mark_duplicates(rows)
    actor_counts = Counter()
    for row in rows:
        for actor in row["actor_candidates"].split("|") if row["actor_candidates"] else []:
            actor_counts[actor] += 1

    manifest_fields = [
        "original_path",
        "original_name",
        "extension",
        "type",
        "size_bytes",
        "mtime",
        "hash",
        "hash8",
        "duration",
        "width",
        "height",
        "creation_time",
        "date_key",
        "date_source",
        "year_month",
        "actor_candidates",
        "canonical_actor",
        "flags",
        "media_error",
    ]
    with (config.manifests / "manifest_all.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=manifest_fields)
        writer.writeheader()
        writer.writerows(rows)

    with (config.manifests / "actor_aliases.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=["canonical_name", "alias", "confidence", "count", "note"])
        writer.writeheader()
        for actor, count in actor_counts.most_common():
            if count >= 2:
                writer.writerow({"canonical_name": actor, "alias": actor, "confidence": "auto", "count": count, "note": "auto extracted from filenames"})

    used_paths: Counter = Counter()
    move_rows = []
    for row in rows:
        target = planned_path(config, row, used_paths)
        move_rows.append(
            {
                "action": "keep" if row["original_path"] == target else "move",
                "original_path": row["original_path"],
                "planned_path": target,
                "type": row["type"],
                "canonical_actor": row["canonical_actor"],
                "actor_candidates": row["actor_candidates"],
                "flags": row["flags"],
                "hash": row["hash"],
                "size_bytes": row["size_bytes"],
            }
        )

    move_fields = ["action", "original_path", "planned_path", "type", "canonical_actor", "actor_candidates", "flags", "hash", "size_bytes"]
    with (config.manifests / "move_plan.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=move_fields)
        writer.writeheader()
        writer.writerows(move_rows)

    plan_by_original = {row["original_path"]: row["planned_path"] for row in move_rows}
    groups: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        groups[(row["type"], row["size_bytes"], row["hash"])].append(row)
    with (config.manifests / "duplicates.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        fields = ["group_key", "original_path", "planned_path", "keep_or_candidate", "hash", "size_bytes"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for key, members in groups.items():
            if len(members) > 1 and not str(key[2]).startswith("ERR_"):
                for index, row in enumerate(sorted(members, key=lambda item: item["original_path"])):
                    writer.writerow(
                        {
                            "group_key": f"{key[0]}:{key[1]}:{key[2][:16]}",
                            "original_path": row["original_path"],
                            "planned_path": plan_by_original.get(row["original_path"], ""),
                            "keep_or_candidate": "keep" if index == 0 else "candidate",
                            "hash": row["hash"],
                            "size_bytes": row["size_bytes"],
                        }
                    )

    summary = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "root": str(config.root),
        "output_root": str(config.library_root),
        "output_root": str(config.library_root),
        "files": len(rows),
        "by_type": dict(Counter(row["type"] for row in rows)),
        "move_actions": dict(Counter(row["action"] for row in move_rows)),
        "known_actor_files": sum(1 for row in rows if row["canonical_actor"]),
        "unknown_actor_files": sum(1 for row in rows if row["type"] in {"video", "photo"} and not row["canonical_actor"]),
        "needs_manual_check_files": sum(1 for row in rows if "needs_age_review" in row["flags"] or "media_probe_error" in row["flags"]),
        "duplicate_candidate_files": sum(1 for row in rows if "duplicate_candidate" in row["flags"]),
        "top_actors": actor_counts.most_common(40),
    }
    with (config.manifests / "summary.json").open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, ensure_ascii=False, indent=2)
    print(json.dumps(summary, ensure_ascii=False))


def dict_rows_from_csv(path: Path):
    # Some Telegram filenames can carry embedded NULs through SMB; csv rejects them.
    text = path.read_text(encoding="utf-8-sig", errors="replace").replace("\x00", "")
    return csv.DictReader(StringIO(text))


def scan(config: Config) -> None:
    ensure_dirs(config)
    rows = build_rows(config)
    if not rows and (config.manifests / "manifest_all.csv").exists():
        print("scan found no source download files; keeping existing manifests")
        refresh_state(config)
        return
    write_scan_outputs(config, rows)


def count_tree_files(path: Path) -> int:
    if not path.exists():
        return 0
    total = 0
    for _, _, filenames in os.walk(path):
        total += len(filenames)
    return total


def child_file_counts(path: Path, limit: int | None = None) -> list[dict[str, int | str]]:
    if not path.exists():
        return []
    rows = []
    for child in sorted([item for item in path.iterdir() if item.is_dir()], key=lambda item: item.name):
        rows.append({"name": child.name, "files": count_tree_files(child)})
    rows.sort(key=lambda item: (-int(item["files"]), str(item["name"])))
    return rows[:limit] if limit else rows


def refresh_state(config: Config) -> None:
    ensure_dirs(config)
    state = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "root": str(config.root),
        "top": {
            "actors": count_tree_files(config.library_root / "Actors"),
            "keywords": count_tree_files(config.review / "Keywords"),
            "unknown": count_tree_files(config.review / "UnknownActor"),
            "faces": count_tree_files(config.review / "Faces"),
            "duplicates": count_tree_files(config.review / "Duplicates"),
            "needs_manual_check": count_tree_files(config.review / "NeedsManualCheck"),
        },
        "source_leftovers": {
            name: count_tree_files(config.root / name)
            for name in (config.source_dirs or ["photos", "photos2", "videos", "videos2"])
        },
        "keywords": child_file_counts(config.review / "Keywords"),
        "actors_sample": child_file_counts(config.library_root / "Actors", 80),
    }
    path = config.manifests / "library_state.json"
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(state, ensure_ascii=False))


def apply_plan(config: Config, limit: int | None, include_review: bool) -> None:
    plan = config.manifests / "move_plan.csv"
    applied = config.manifests / "applied_moves.csv"
    rows = []
    for row in dict_rows_from_csv(plan):
            if row["action"] != "move":
                continue
            if not include_review and row["planned_path"].startswith("_REVIEW/NeedsManualCheck"):
                continue
            src = config.root / row["original_path"]
            dst = config.library_root / row["planned_path"]
            if not src.exists() or dst.exists():
                continue
            rows.append(row)
            if limit and len(rows) >= limit:
                break

    new_file = not applied.exists()
    moved = 0
    with applied.open("a", encoding="utf-8-sig", newline="") as handle:
        fields = ["applied_at", "original_path", "new_path", "type", "canonical_actor", "size_bytes", "hash_before", "hash_after", "status"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        if new_file:
            writer.writeheader()
        for row in rows:
            src = config.root / row["original_path"]
            dst = config.library_root / row["planned_path"]
            dst.parent.mkdir(parents=True, exist_ok=True)
            before = partial_hash(src)
            shutil.move(str(src), str(dst))
            after = partial_hash(dst)
            if before == after == row["hash"]:
                status = "moved"
            elif before == after:
                status = "moved_plan_hash_mismatch"
            else:
                status = "moved_content_hash_mismatch"
            writer.writerow(
                {
                    "applied_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "original_path": row["original_path"],
                    "new_path": row["planned_path"],
                    "type": row["type"],
                    "canonical_actor": row["canonical_actor"],
                    "size_bytes": row["size_bytes"],
                    "hash_before": before,
                    "hash_after": after,
                    "status": status,
                }
            )
            moved += 1
    print(f"moved {moved} files")
    if moved:
        refresh_state(config)


def rollback(config: Config, limit: int | None) -> None:
    applied = config.manifests / "applied_moves.csv"
    if not applied.exists():
        print("no applied_moves.csv")
        return
    rows = list(dict_rows_from_csv(applied))
    moved = 0
    for row in reversed(rows):
        if row.get("status") != "moved":
            continue
        src = config.library_root / row["new_path"]
        dst = config.root / row["original_path"]
        if not src.exists() or dst.exists():
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
        moved += 1
        if limit and moved >= limit:
            break
    print(f"rolled back {moved} files")


def clean_empty_dirs(config: Config) -> None:
    removed = 0
    for top in [config.library_root / "Actors", config.library_root / "Mixed", config.review]:
        if not top.exists():
            continue
        for dirpath, dirnames, filenames in os.walk(top, topdown=False):
            path = Path(dirpath)
            if path == top:
                continue
            try:
                if not any(path.iterdir()):
                    path.rmdir()
                    removed += 1
            except OSError:
                pass
    print(f"removed {removed} empty dirs")


def date_from_media_filename(path: Path) -> str:
    match = re.search(r"_(20\d{6})_", path.name)
    if match:
        value = match.group(1)
        return f"{value[:4]}-{value[4:6]}"
    try:
        return time.strftime("%Y-%m", time.localtime(path.stat().st_mtime))
    except Exception:
        return "UnknownDate"


def unique_destination(path: Path) -> Path:
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    index = 2
    while True:
        candidate = path.with_name(f"{stem}_{index:03d}{suffix}")
        if not candidate.exists():
            return candidate
        index += 1


def hash8_from_media_name(path: Path) -> str:
    match = re.search(r"_([0-9a-fA-F]{8})(?:_\d{3})?\.[^.]+$", path.name)
    return match.group(1).lower() if match else ""


def original_text_index(config: Config) -> dict[str, str]:
    index: dict[str, str] = {}
    log = config.manifests / "applied_moves.csv"
    if log.exists():
        for row in dict_rows_from_csv(log):
            original = row.get("original_path", "")
            for key in [row.get("hash_before", "")[:8], row.get("hash_after", "")[:8]]:
                if key:
                    index[key.lower()] = original
    manifest = config.manifests / "manifest_all.csv"
    if manifest.exists():
        for row in dict_rows_from_csv(manifest):
            original = row.get("original_name") or row.get("original_path", "")
            key = row.get("hash8", "")
            if key:
                index[key.lower()] = original
    return index


def classify_keywords(config: Config) -> None:
    index = original_text_index(config)
    moved = Counter()
    roots = [config.review / "UnknownActor", config.review / "NeedsManualCheck"]
    for source_root in roots:
        if not source_root.exists():
            continue
        for file_path in sorted([p for p in source_root.rglob("*") if p.is_file()]):
            if not file_path.exists():
                continue
            key = hash8_from_media_name(file_path)
            original = index.get(key, file_path.name)
            category = keyword_category(original)
            if not category:
                continue
            kind = "Videos" if file_path.suffix.lower() in VIDEO_EXT else "Photos"
            dest = config.review / "Keywords" / category / kind / file_path.name
            dest = unique_destination(dest)
            dest.parent.mkdir(parents=True, exist_ok=True)
            try:
                shutil.move(str(file_path), str(dest))
                moved[category] += 1
            except FileNotFoundError:
                continue
    clean_empty_dirs(config)
    print("keyword_moved", dict(moved))
    if moved:
        refresh_state(config)


def analyze_filenames(config: Config, min_count: int) -> None:
    log = config.manifests / "applied_moves.csv"
    manifest = config.manifests / "manifest_all.csv"
    texts = []
    if log.exists():
        texts.extend(row.get("original_path", "") for row in dict_rows_from_csv(log))
    if manifest.exists():
        texts.extend((row.get("original_path") or row.get("original_name") or "") for row in dict_rows_from_csv(manifest))
    tag_counts = Counter()
    word_counts = Counter()
    suggestions = []
    for text in texts:
        base = Path(text).name
        for match in re.finditer(r"#([^#@\s_\-，,。:：;；【】\[\]()（）]+)", base):
            token = match.group(1).strip()
            cleaned = clean_actor_token(token)
            category = keyword_category(token)
            if cleaned:
                kind = "actor_candidate"
                value = cleaned
            elif category:
                kind = "keyword_candidate"
                value = category
            else:
                kind = "ignore_or_noise"
                value = token
            tag_counts[(token, kind, value)] += 1
        for token in re.findall(r"[A-Za-z][A-Za-z0-9_]{2,}|[\u4e00-\u9fff]{2,}", base):
            if token.lower() in {"jpg", "jpeg", "png", "mp4", "mov", "telegram"}:
                continue
            word_counts[token] += 1

    analysis_path = config.manifests / "filename_analysis.csv"
    with analysis_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=["token", "kind", "suggested_value", "count"])
        writer.writeheader()
        for (token, kind, value), count in tag_counts.most_common():
            if count >= min_count:
                writer.writerow({"token": token, "kind": kind, "suggested_value": value, "count": count})

    words_path = config.manifests / "filename_words.csv"
    with words_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=["word", "count", "keyword_category", "actor_candidate"])
        writer.writeheader()
        for word, count in word_counts.most_common():
            if count < min_count:
                continue
            writer.writerow({
                "word": word,
                "count": count,
                "keyword_category": keyword_category(word),
                "actor_candidate": clean_actor_token(word),
            })
    print(f"filename_analysis {analysis_path} words {words_path}")


def all_organized_media_files(config: Config):
    roots = [
        config.library_root / "Actors",
        config.review / "Keywords",
        config.review / "UnknownActor",
        config.review / "NeedsManualCheck",
        config.review / "Duplicates",
        config.review / "Faces",
    ]
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.is_file() and path.suffix.lower() in VIDEO_EXT | PHOTO_EXT:
                yield path


def media_kind(path: Path) -> str:
    return "video" if path.suffix.lower() in VIDEO_EXT else "photo"


def media_cache_key(path: Path) -> str:
    key = hash8_from_media_name(path)
    if key:
        return key
    digest = partial_hash(path)
    return digest[:12] if not digest.startswith("ERR_") else hashlib.sha1(str(path).encode()).hexdigest()[:12]


def frame_cache_dir(config: Config) -> Path:
    return config.manifests / "vision_cache"


def cancel_requested() -> bool:
    cancel_file = os.environ.get("TGMM_CANCEL_FILE", "")
    return bool(cancel_file and Path(cancel_file).exists())


def progress_event(stage: str, processed: int, total: int, **extra) -> None:
    payload = {
        "stage": stage,
        "processed": processed,
        "total": total,
        "progress": int((processed / total) * 100) if total else 0,
        **extra,
    }
    print("TGMM_PROGRESS " + json.dumps(payload, ensure_ascii=False), flush=True)


def valid_cache_file(path: Path) -> bool:
    try:
        return path.exists() and path.stat().st_size > 1024
    except OSError:
        return False


def ffmpeg_hw_prefix() -> list[str]:
    mode = os.environ.get("FFMPEG_HWACCEL", "").strip().lower()
    if mode in {"", "none", "false", "0", "off"}:
        return []
    device = os.environ.get("FFMPEG_HW_DEVICE", "/dev/dri/renderD128")
    if mode in {"vaapi", "auto"} and Path(device).exists():
        return ["-hwaccel", "vaapi", "-hwaccel_device", device]
    if mode == "qsv":
        return ["-hwaccel", "qsv"]
    return []


def run_ffmpeg_with_fallback(base_cmd: list[str], out: Path, timeout: int) -> bool:
    prefixes = []
    hw = ffmpeg_hw_prefix()
    if hw:
        prefixes.append(hw)
    prefixes.append([])
    for prefix in prefixes:
        tmp = out.with_name(f".{out.stem}.tmp{out.suffix}")
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass
        cmd = ["ffmpeg", "-y", *prefix, *base_cmd[:-1], "-update", "1", str(tmp)]
        try:
            proc = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=timeout)
        except (subprocess.SubprocessError, OSError):
            continue
        if proc.returncode == 0 and valid_cache_file(tmp):
            tmp.replace(out)
            return True
        try:
            tmp.unlink()
        except OSError:
            pass
    return False


def extract_video_frames(src: Path, out_dir: Path, frames: int) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    outputs = []
    for i in range(frames):
        out = out_dir / f"frame_{i + 1:02d}.jpg"
        if valid_cache_file(out):
            outputs.append(out)
            continue
        if out.exists():
            try:
                out.unlink()
            except OSError:
                pass
        # fps expression samples across the duration without needing metadata parsing.
        vf = "thumbnail,scale=min(640\\,iw):-2"
        ss = "0" if i == 0 else str(max(0, i * 7 + 1))
        base_cmd = ["-ss", ss, "-i", str(src), "-frames:v", "1", "-vf", vf, "-q:v", "4", str(out)]
        if run_ffmpeg_with_fallback(base_cmd, out, 30):
            outputs.append(out)
    return outputs


def extract_image_thumb(src: Path, out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "frame_01.jpg"
    if valid_cache_file(out):
        return [out]
    if out.exists():
        try:
            out.unlink()
        except OSError:
            pass
    if Image is not None:
        tmp = out.with_name(f".{out.stem}.tmp{out.suffix}")
        try:
            with Image.open(src) as img:
                img = img.convert("RGB")
                width, height = img.size
                if width > 640:
                    height = max(1, int(height * (640 / width)))
                    width = 640
                    img = img.resize((width, height))
                img.save(tmp, "JPEG", quality=82)
            if valid_cache_file(tmp):
                tmp.replace(out)
                return [out]
        except Exception:
            try:
                tmp.unlink()
            except OSError:
                pass
    base_cmd = ["-i", str(src), "-frames:v", "1", "-vf", "scale=min(640\\,iw):-2", "-q:v", "4", str(out)]
    run_ffmpeg_with_fallback(base_cmd, out, 20)
    return [out] if valid_cache_file(out) else []


def write_frame_index(config: Config, rows: list[dict]) -> None:
    out = config.manifests / "frame_index.csv"
    with out.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=["media_path", "cache_key", "kind", "frames", "error"])
        writer.writeheader()
        writer.writerows(rows)


def extract_one_media_frame_job(config: Config, path: Path, frames: int) -> dict:
    key = media_cache_key(path)
    out_dir = frame_cache_dir(config) / key
    error = ""
    try:
        outputs = extract_video_frames(path, out_dir, frames) if media_kind(path) == "video" else extract_image_thumb(path, out_dir)
        if not outputs:
            error = "no_frames"
    except Exception as exc:
        outputs = []
        error = type(exc).__name__
    return {
        "media_path": rel(config.library_root, path),
        "cache_key": key,
        "kind": media_kind(path),
        "frames": "|".join(str(p.relative_to(config.library_root)) for p in outputs),
        "error": error,
    }


def extract_frames(config: Config, limit: int | None, frames: int, workers: int, checkpoint_every: int, retry_failed: bool) -> None:
    cache = frame_cache_dir(config)
    cache.mkdir(parents=True, exist_ok=True)
    rows = []
    errors = []
    if retry_failed and (config.manifests / "frame_errors.csv").exists():
        retry_paths = []
        for row in dict_rows_from_csv(config.manifests / "frame_errors.csv"):
            media_path = row.get("media_path", "")
            if media_path:
                path = config.library_root / media_path
                if path.exists():
                    retry_paths.append(path)
        paths = retry_paths
    else:
        paths = list(all_organized_media_files(config))
    if limit:
        paths = paths[:limit]
    total = len(paths)
    workers = max(1, min(16, workers))
    checkpoint_every = max(10, checkpoint_every)
    processed = skipped = failed = 0
    progress_event("extract-frames", 0, total, workers=workers, frames_per_video=frames, message="starting")
    executor = ThreadPoolExecutor(max_workers=workers)
    fast_cancel = False
    try:
        futures = {executor.submit(extract_one_media_frame_job, config, path, frames): path for path in paths}
        for future in as_completed(futures):
            path = futures[future]
            if cancel_requested():
                progress_event("extract-frames", processed, total, message="cancel requested")
                fast_cancel = True
                executor.shutdown(wait=False, cancel_futures=True)
                write_frame_index(config, rows)
                return
            try:
                row = future.result()
            except Exception as exc:
                row = {
                    "media_path": rel(config.library_root, path),
                    "cache_key": media_cache_key(path),
                    "kind": media_kind(path),
                    "frames": "",
                    "error": type(exc).__name__,
                }
            rows.append(row)
            processed += 1
            if row.get("error"):
                failed += 1
                errors.append(row)
            else:
                frame_paths = [item for item in row.get("frames", "").split("|") if item]
                if frame_paths and all(valid_cache_file(config.library_root / item) for item in frame_paths):
                    skipped += 1
            if processed % checkpoint_every == 0 or processed == total:
                write_frame_index(config, rows)
                progress_event(
                    "extract-frames",
                    processed,
                    total,
                    failed=failed,
                    cached_or_done=skipped,
                    current=str(path.relative_to(config.library_root)) if path.is_relative_to(config.library_root) else str(path),
                )
    finally:
        if not fast_cancel:
            executor.shutdown(wait=True, cancel_futures=False)
    write_frame_index(config, rows)
    if errors:
        error_out = config.manifests / "frame_errors.csv"
        with error_out.open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(handle, fieldnames=["media_path", "cache_key", "kind", "frames", "error"])
            writer.writeheader()
            writer.writerows(errors)
    print(f"frame_index {len(rows)} rows")
    if errors:
        print(f"frame_errors {len(errors)} rows", flush=True)


def face_setup() -> None:
    print("Face backends are optional and local-only.")
    print("Docker vision image recommendation: install insightface, onnxruntime-openvino, opencv-python-headless, numpy, pillow.")
    print("OpenCLIP image classification requires torch and open-clip-torch.")
    print(f"FACE_PROVIDERS={os.environ.get('FACE_PROVIDERS', 'CPUExecutionProvider')}")
    print(f"OPENVINO_DEVICE={os.environ.get('OPENVINO_DEVICE', 'CPU')}")
    try:
        import onnxruntime as ort  # type: ignore
        print("ONNXRuntime providers: " + ", ".join(ort.get_available_providers()))
    except Exception as exc:
        print(f"ONNXRuntime unavailable: {type(exc).__name__}")
    print("No face data is uploaded by this script.")


VISION_PROMPTS = [
    ("JK学生", ["student uniform", "Japanese school uniform", "JK style uniform"]),
    ("水手服制服", ["sailor uniform", "Japanese sailor school uniform", "pleated skirt uniform"]),
    ("死库水泳装", ["school swimsuit", "one piece swimsuit", "competition swimsuit"]),
    ("COS角色", ["cosplay costume", "anime cosplay", "game character cosplay", "maid costume"]),
    ("黑丝白丝", ["black stockings", "white stockings", "pantyhose", "thigh high socks"]),
    ("自拍露脸", ["selfie portrait", "face selfie", "mirror selfie"]),
    ("室外户外", ["outdoor scene", "street outdoor photo", "park beach outdoor scene"]),
    ("室内居家", ["indoor bedroom scene", "indoor room photo", "hotel room indoor scene"]),
    ("足交足控", ["feet close up", "bare feet close up", "stocking feet close up"]),
    ("调教捆绑", ["bondage accessories", "collar restraint", "rope restraint"]),
    ("道具自慰", ["adult toy", "vibrator", "toy in hand"]),
]


def load_open_clip_backend(strong: bool = False):
    try:
        import torch  # type: ignore
        import open_clip  # type: ignore
        from PIL import Image as PILImage  # type: ignore
    except Exception as exc:
        raise RuntimeError("OpenCLIP backend unavailable. Install torch, open-clip-torch, and pillow.") from exc
    model_name = os.environ.get("OPENCLIP_STRONG_MODEL" if strong else "OPENCLIP_MODEL", "ViT-H-14" if strong else "ViT-L-14")
    pretrained = os.environ.get("OPENCLIP_STRONG_PRETRAINED" if strong else "OPENCLIP_PRETRAINED", "laion2b_s32b_b79k" if strong else "laion2b_s32b_b82k")
    model, _, preprocess = open_clip.create_model_and_transforms(model_name, pretrained=pretrained, device="cpu")
    tokenizer = open_clip.get_tokenizer(model_name)
    model.eval()
    labels = []
    prompts = []
    for category, variants in VISION_PROMPTS:
        for variant in variants:
            labels.append(category)
            prompts.append(variant)
    with torch.no_grad():
        text = tokenizer(prompts)
        text_features = model.encode_text(text)
        text_features /= text_features.norm(dim=-1, keepdim=True)
    return torch, PILImage, model, preprocess, labels, text_features, {"model": model_name, "pretrained": pretrained}


def vision_scan(config: Config, limit: int | None) -> None:
    frame_index = config.manifests / "frame_index.csv"
    if not frame_index.exists():
        raise SystemExit("frame_index.csv not found. Run extract-frames first.")
    frame_rows = list(dict_rows_from_csv(frame_index))
    total = min(limit or len(frame_rows), len(frame_rows))
    progress_event("vision-scan", 0, total, message="loading OpenCLIP model")
    strong_mode = os.environ.get("OPENCLIP_STRONG_MODE", "").lower() in {"1", "true", "yes", "on"}
    low_confidence_only = strong_mode and os.environ.get("OPENCLIP_STRONG_LOW_CONF_ONLY", "true").lower() not in {"0", "false", "no", "off"}
    try:
        low_confidence_threshold = float(os.environ.get("OPENCLIP_STRONG_THRESHOLD", "0.62"))
    except ValueError:
        low_confidence_threshold = 0.62
    existing_labels = {}
    preserved_rows = []
    preserved_embedding_rows = []
    if low_confidence_only:
        for row in dict_rows_from_csv(config.manifests / "vision_labels.csv"):
            try:
                score = float(row.get("score") or 0)
            except ValueError:
                score = 0.0
            existing_labels[row.get("media_path", "")] = score
            if score >= low_confidence_threshold:
                preserved_rows.append(row)
        preserved_paths = {row.get("media_path", "") for row in preserved_rows}
        embeddings_path = config.manifests / "vision_embeddings.jsonl"
        if embeddings_path.exists():
            with embeddings_path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    try:
                        row = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if row.get("media_path") in preserved_paths:
                        preserved_embedding_rows.append(row)
    try:
        torch, PILImage, model, preprocess, labels, text_features, model_info = load_open_clip_backend(strong=strong_mode)
    except RuntimeError as exc:
        raise SystemExit(str(exc))
    rows = list(preserved_rows)
    embedding_rows = list(preserved_embedding_rows)
    scanned = 0
    for frame_row in frame_rows:
        if cancel_requested():
            progress_event("vision-scan", scanned, total, message="cancel requested")
            break
        frame_paths = [p for p in frame_row.get("frames", "").split("|") if p]
        if low_confidence_only and existing_labels.get(frame_row.get("media_path", ""), 0.0) >= low_confidence_threshold:
            continue
        label_scores: dict[str, list[float]] = defaultdict(list)
        label_best: dict[str, tuple[float, str, list[float]]] = {}
        for frame_rel in frame_paths:
            frame_path = config.library_root / frame_rel
            if not frame_path.exists():
                continue
            try:
                image = preprocess(PILImage.open(frame_path).convert("RGB")).unsqueeze(0)
                with torch.no_grad():
                    image_features = model.encode_image(image)
                    image_features /= image_features.norm(dim=-1, keepdim=True)
                    probs = (100.0 * image_features @ text_features.T).softmax(dim=-1)[0]
                top_k = min(4, len(labels))
                scores, indices = torch.topk(probs, k=top_k)
                vector = [round(float(x), 7) for x in image_features[0].detach().cpu().tolist()]
                for score, idx in zip(scores, indices):
                    category = labels[int(idx)]
                    value = float(score)
                    label_scores[category].append(value)
                    current = label_best.get(category)
                    if current is None or value > current[0]:
                        label_best[category] = (value, frame_rel, vector)
            except Exception:
                continue
        best = ("", 0.0, "", [])
        for category, values in label_scores.items():
            stability = min(1.0, len(values) / max(1, min(3, len(frame_paths))))
            score = (sum(values) / len(values)) * (0.75 + 0.25 * stability)
            if score > best[1] and category in label_best:
                frame_score, frame_rel, vector = label_best[category]
                best = (category, float(score), frame_rel, vector)
        rows.append({
            "media_path": frame_row["media_path"],
            "category": best[0],
            "score": f"{best[1]:.6f}",
            "representative_frame": best[2],
        })
        if best[3]:
            embedding_rows.append({
                "media_path": frame_row["media_path"],
                "representative_frame": best[2],
                "model": model_info["model"],
                "pretrained": model_info["pretrained"],
                "mode": "strong" if strong_mode else "default",
                "embedding": best[3],
            })
        scanned += 1
        if scanned % 25 == 0 or scanned == total:
            progress_event("vision-scan", scanned, total, current=frame_row.get("media_path", ""), label=best[0], score=round(best[1], 4), message=f"vision scanned {scanned}/{total}")
        if scanned % 100 == 0:
            print(f"vision scanned {scanned} media", flush=True)
        if limit and scanned >= limit:
            break
    out = config.manifests / "vision_labels.csv"
    with out.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=["media_path", "category", "score", "representative_frame"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"vision_labels {len(rows)} rows")
    embeddings_out = config.manifests / "vision_embeddings.jsonl"
    with embeddings_out.open("w", encoding="utf-8") as handle:
        for row in embedding_rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
    print(f"vision_embeddings {len(embedding_rows)} rows")


def load_face_backend():
    try:
        import face_recognition  # type: ignore
        return "face_recognition", face_recognition
    except Exception:
        pass
    try:
        import cv2  # type: ignore
        import onnxruntime as ort  # type: ignore
        from insightface.app import FaceAnalysis  # type: ignore
        model_root = Path(os.environ["INSIGHTFACE_HOME"]) if os.environ.get("INSIGHTFACE_HOME") else Path(os.environ.get("MODEL_ROOT", "/models")) / "insightface"
        requested = [item.strip() for item in os.environ.get("FACE_PROVIDERS", "CPUExecutionProvider").split(",") if item.strip()]
        available = set(ort.get_available_providers())
        providers = [provider for provider in requested if provider in available]
        if not providers:
            providers = ["CPUExecutionProvider"]
        provider_options = []
        for provider in providers:
            if provider == "OpenVINOExecutionProvider":
                provider_options.append({"device_type": os.environ.get("OPENVINO_DEVICE", "GPU")})
            else:
                provider_options.append({})
        app = FaceAnalysis(
            name=os.environ.get("INSIGHTFACE_MODEL", "buffalo_l"),
            root=str(model_root),
            providers=providers,
            provider_options=provider_options,
        )
        ctx_id = 0 if providers and providers[0] == "OpenVINOExecutionProvider" else -1
        try:
            app.prepare(ctx_id=ctx_id, det_size=(640, 640))
        except Exception:
            if providers == ["CPUExecutionProvider"]:
                raise
            app = FaceAnalysis(
                name=os.environ.get("INSIGHTFACE_MODEL", "buffalo_l"),
                root=str(model_root),
                providers=["CPUExecutionProvider"],
            )
            app.prepare(ctx_id=-1, det_size=(640, 640))
            providers = ["CPUExecutionProvider"]
        print(f"face backend insightface providers={','.join(providers)}", flush=True)
        return "insightface", (app, cv2)
    except Exception as exc:
        raise RuntimeError(
            "No local face backend available. Install insightface+onnxruntime+opencv-python-headless or face_recognition."
        ) from exc


def detect_faces(frame: Path, backend_name: str, backend) -> list[dict]:
    if backend_name == "face_recognition":
        image = backend.load_image_file(str(frame))
        boxes = backend.face_locations(image, model="hog")
        encodings = backend.face_encodings(image, boxes)
        faces = []
        for idx, (box, enc) in enumerate(zip(boxes, encodings)):
            top, right, bottom, left = box
            area = max(0, right - left) * max(0, bottom - top)
            faces.append({
                "face_index": idx,
                "bbox": [left, top, right, bottom],
                "area": area,
                "det_score": "",
                "embedding": [float(x) for x in enc],
            })
        return faces
    app, cv2 = backend
    img = cv2.imread(str(frame))
    if img is None:
        return []
    detections = app.get(img)
    faces = []
    for idx, face in enumerate(detections):
        x1, y1, x2, y2 = [int(v) for v in face.bbox]
        area = max(0, x2 - x1) * max(0, y2 - y1)
        faces.append({
            "face_index": idx,
            "bbox": [x1, y1, x2, y2],
            "area": area,
            "det_score": float(getattr(face, "det_score", 0.0)),
            "embedding": [float(x) for x in face.embedding],
        })
    return faces


def face_scan(config: Config, limit: int | None) -> None:
    frame_index = config.manifests / "frame_index.csv"
    if not frame_index.exists():
        raise SystemExit("frame_index.csv not found. Run extract-frames first.")
    try:
        backend_name, backend = load_face_backend()
    except RuntimeError as exc:
        raise SystemExit(str(exc))
    frame_rows = list(dict_rows_from_csv(frame_index))
    total_frames = sum(len([p for p in row.get("frames", "").split("|") if p]) for row in frame_rows)
    total = min(limit or total_frames, total_frames)
    progress_event("face-scan", 0, total, backend=backend_name, message="starting")
    rows = []
    scanned = 0
    for frame_row in frame_rows:
        frame_paths = [p for p in frame_row.get("frames", "").split("|") if p]
        for frame_rel in frame_paths:
            if cancel_requested():
                progress_event("face-scan", scanned, total, message="cancel requested")
                break
            frame_path = config.library_root / frame_rel
            if not frame_path.exists():
                continue
            try:
                faces = detect_faces(frame_path, backend_name, backend)
            except Exception as exc:
                rows.append({
                    "media_path": frame_row["media_path"],
                    "frame_path": frame_rel,
                    "face_index": "",
                    "bbox": "",
                    "area": "",
                    "det_score": "",
                    "embedding": "",
                    "backend": backend_name,
                    "error": type(exc).__name__,
                })
                continue
            for face in faces:
                rows.append({
                    "media_path": frame_row["media_path"],
                    "frame_path": frame_rel,
                    "face_index": face["face_index"],
                    "bbox": json.dumps(face["bbox"]),
                    "area": face["area"],
                    "det_score": face["det_score"],
                    "embedding": json.dumps(face["embedding"]),
                    "backend": backend_name,
                    "error": "",
                })
            scanned += 1
            if scanned % 25 == 0 or scanned == total:
                progress_event("face-scan", scanned, total, current=frame_row.get("media_path", ""), faces=len(faces), message=f"face scanned {scanned}/{total}")
            if scanned % 100 == 0:
                print(f"face scanned {scanned} frames", flush=True)
            if limit and scanned >= limit:
                break
        if cancel_requested():
            break
        if limit and scanned >= limit:
            break
    out = config.manifests / "face_index.csv"
    with out.open("w", newline="", encoding="utf-8-sig") as handle:
        fields = ["media_path", "frame_path", "face_index", "bbox", "area", "det_score", "embedding", "backend", "error"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(f"face_index {len(rows)} rows")


def normalize_vector(vec: list[float]) -> list[float]:
    norm = math.sqrt(sum(x * x for x in vec))
    if not norm:
        return vec
    return [x / norm for x in vec]


def vector_distance(a: list[float], b: list[float]) -> float:
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def face_cluster(config: Config, threshold: float) -> None:
    face_index = config.manifests / "face_index.csv"
    if not face_index.exists():
        raise SystemExit("face_index.csv not found. Run face-scan first.")
    items = []
    for row in dict_rows_from_csv(face_index):
        if row.get("error") or not row.get("embedding"):
            continue
        try:
            emb = [float(x) for x in json.loads(row["embedding"])]
        except Exception:
            continue
        items.append({**row, "embedding_vec": normalize_vector(emb)})
    parent = list(range(len(items)))

    def find(idx: int) -> int:
        while parent[idx] != idx:
            parent[idx] = parent[parent[idx]]
            idx = parent[idx]
        return idx

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            if vector_distance(items[i]["embedding_vec"], items[j]["embedding_vec"]) <= threshold:
                union(i, j)
    buckets: dict[int, list[dict]] = defaultdict(list)
    for idx, item in enumerate(items):
        buckets[find(idx)].append(item)
    groups = list(buckets.values())
    rows = []
    for idx, group in enumerate(groups, start=1):
        gid = f"FaceGroup_{idx:06d}"
        media = sorted({g["media_path"] for g in group})
        representative = max(group, key=lambda g: int(float(g.get("area") or 0)))
        for g in group:
            rows.append({
                "face_group": gid,
                "media_path": g["media_path"],
                "frame_path": g["frame_path"],
                "bbox": g["bbox"],
                "area": g["area"],
                "det_score": g["det_score"],
                "representative_frame": representative["frame_path"],
                "group_face_count": len(group),
                "group_media_count": len(media),
            })
    out = config.manifests / "face_groups.csv"
    with out.open("w", newline="", encoding="utf-8-sig") as handle:
        fields = ["face_group", "media_path", "frame_path", "bbox", "area", "det_score", "representative_frame", "group_face_count", "group_media_count"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(f"face_groups {len(groups)} groups {len(rows)} rows")


def read_face_aliases(config: Config) -> dict[str, str]:
    path = config.manifests / "face_aliases.csv"
    if not path.exists():
        with path.open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(handle, fieldnames=["face_group", "actor_name", "note"])
            writer.writeheader()
        return {}
    aliases = {}
    for row in dict_rows_from_csv(path):
        if row.get("face_group") and row.get("actor_name"):
            aliases[row["face_group"]] = row["actor_name"]
    return aliases


def write_face_move_plan(config: Config, apply: bool) -> None:
    groups_path = config.manifests / "face_groups.csv"
    if not groups_path.exists():
        raise SystemExit("face_groups.csv not found. Run face-cluster first.")
    aliases = read_face_aliases(config)
    seen_media = {}
    for row in dict_rows_from_csv(groups_path):
        media = row["media_path"]
        group = row["face_group"]
        size = int(row.get("group_face_count") or 0)
        if media not in seen_media or size > seen_media[media][1]:
            seen_media[media] = (group, size)
    rows = []
    moved = 0
    for media, (group, _size) in sorted(seen_media.items()):
        src = config.library_root / media
        if not src.exists():
            continue
        actor = aliases.get(group, "")
        kind = "Videos" if src.suffix.lower() in VIDEO_EXT else "Photos"
        if actor:
            dest = config.library_root / "Actors" / safe_component(actor) / kind / src.name
        else:
            dest = config.review / "Faces" / group / kind / src.name
        dest = unique_destination(dest)
        rows.append({"action": "move", "face_group": group, "actor_name": actor, "source": media, "destination": rel(config.library_root, dest)})
        if apply:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dest))
            moved += 1
    out = config.manifests / "face_move_plan.csv"
    with out.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=["action", "face_group", "actor_name", "source", "destination"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"face_move_plan {len(rows)} rows apply={apply} moved={moved}")
    if moved:
        refresh_state(config)


def name_face_group(config: Config, face_group: str, actor_name: str) -> None:
    path = config.manifests / "face_aliases.csv"
    rows = []
    found = False
    if path.exists():
        rows = list(dict_rows_from_csv(path))
    for row in rows:
        if row.get("face_group") == face_group:
            row["actor_name"] = actor_name
            found = True
    if not found:
        rows.append({"face_group": face_group, "actor_name": actor_name, "note": "manual"})
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=["face_group", "actor_name", "note"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"named {face_group} => {actor_name}")
    merge_named_face_groups(config, actor_name)


def merge_face_groups(config: Config, source_group: str, target_group: str) -> None:
    if source_group == target_group:
        raise SystemExit("source and target face groups are the same")
    groups_path = config.manifests / "face_groups.csv"
    if not groups_path.exists():
        raise SystemExit("face_groups.csv not found. Run face-cluster first.")
    rows = list(dict_rows_from_csv(groups_path))
    source_seen = any(row.get("face_group") == source_group for row in rows)
    target_seen = any(row.get("face_group") == target_group for row in rows)
    if not source_seen:
        raise SystemExit(f"{source_group} not found")
    if not target_seen:
        raise SystemExit(f"{target_group} not found")
    for row in rows:
        if row.get("face_group") == source_group:
            row["face_group"] = target_group
    with groups_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=["face_group", "media_path", "frame_path", "bbox", "area", "det_score", "representative_frame", "group_face_count", "group_media_count"])
        writer.writeheader()
        writer.writerows(rows)

    aliases_path = config.manifests / "face_aliases.csv"
    alias_rows = list(dict_rows_from_csv(aliases_path)) if aliases_path.exists() else []
    source_actor = ""
    target_actor = ""
    kept_aliases = []
    for row in alias_rows:
        if row.get("face_group") == source_group:
            source_actor = row.get("actor_name", "")
            continue
        if row.get("face_group") == target_group:
            target_actor = row.get("actor_name", "")
        kept_aliases.append(row)
    if source_actor and not target_actor:
        kept_aliases.append({"face_group": target_group, "actor_name": source_actor, "note": f"merged from {source_group}"})
    with aliases_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=["face_group", "actor_name", "note"])
        writer.writeheader()
        writer.writerows(kept_aliases)

    face_cluster_report(config)
    write_face_merge_suggestions(config)
    print(f"merged {source_group} => {target_group}")


def merge_named_face_groups(config: Config, actor_name: str | None = None) -> None:
    groups_path = config.manifests / "face_groups.csv"
    aliases_path = config.manifests / "face_aliases.csv"
    if not groups_path.exists():
        raise SystemExit("face_groups.csv not found. Run face-cluster first.")
    if not aliases_path.exists():
        print("face_aliases.csv not found; nothing to merge")
        return

    alias_rows = list(dict_rows_from_csv(aliases_path))
    actor_to_groups: dict[str, set[str]] = defaultdict(set)
    for row in alias_rows:
        actor = (row.get("actor_name") or "").strip()
        group = (row.get("face_group") or "").strip()
        if not actor or not group:
            continue
        if actor_name and actor != actor_name:
            continue
        actor_to_groups[actor].add(group)

    group_rows = list(dict_rows_from_csv(groups_path))
    group_counts = Counter(row.get("face_group", "") for row in group_rows)
    remap: dict[str, str] = {}
    merged_notes = []
    for actor, groups in sorted(actor_to_groups.items()):
        existing = [group for group in groups if group_counts.get(group, 0)]
        if len(existing) < 2:
            continue
        target = sorted(existing, key=lambda group: (-group_counts[group], group))[0]
        for group in existing:
            if group != target:
                remap[group] = target
        merged_notes.append(f"{actor}: {', '.join(sorted(existing))} => {target}")

    if not remap:
        print("named face groups already merged")
        return

    for row in group_rows:
        group = row.get("face_group", "")
        if group in remap:
            row["face_group"] = remap[group]
    with groups_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=["face_group", "media_path", "frame_path", "bbox", "area", "det_score", "representative_frame", "group_face_count", "group_media_count"])
        writer.writeheader()
        writer.writerows(group_rows)

    kept_aliases = []
    seen_aliases = set()
    for row in alias_rows:
        group = row.get("face_group", "")
        actor = row.get("actor_name", "")
        target = remap.get(group, group)
        key = (target, actor)
        if key in seen_aliases:
            continue
        seen_aliases.add(key)
        kept_aliases.append({"face_group": target, "actor_name": actor, "note": row.get("note", "manual")})
    with aliases_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=["face_group", "actor_name", "note"])
        writer.writeheader()
        writer.writerows(kept_aliases)

    face_cluster_report(config)
    write_face_merge_suggestions(config)
    print("merged named face groups")
    for note in merged_notes:
        print(note)


def update_face_alias_actor(config: Config, old_actor: str, new_actor: str | None) -> int:
    aliases_path = config.manifests / "face_aliases.csv"
    if not aliases_path.exists():
        return 0
    rows = list(dict_rows_from_csv(aliases_path))
    changed = 0
    kept = []
    for row in rows:
        if row.get("actor_name") == old_actor:
            changed += 1
            if new_actor:
                row["actor_name"] = new_actor
                row["note"] = f"renamed from {old_actor}"
                kept.append(row)
            continue
        kept.append(row)
    with aliases_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=["face_group", "actor_name", "note"])
        writer.writeheader()
        writer.writerows(kept)
    return changed


def move_actor_media(config: Config, old_actor: str, new_actor: str | None) -> int:
    old_dir = config.library_root / "Actors" / safe_component(old_actor)
    if not old_dir.exists():
        raise SystemExit(f"actor not found: {old_actor}")
    if new_actor:
        base_dest = config.library_root / "Actors" / safe_component(new_actor)
    else:
        base_dest = config.review / "UnknownActor" / "ExcludedAuthor" / safe_component(old_actor)
    moved = 0
    for media_dir_name in ["Photos", "Videos"]:
        media_dir = old_dir / media_dir_name
        if not media_dir.exists():
            continue
        for src in sorted([path for path in media_dir.rglob("*") if path.is_file()]):
            dest = unique_destination(base_dest / media_dir_name / src.name)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dest))
            moved += 1
    clean_empty_dirs(config)
    return moved


def rename_actor(config: Config, old_actor: str, new_actor: str) -> None:
    old_actor = old_actor.strip()
    new_actor = new_actor.strip()
    if not old_actor or not new_actor:
        raise SystemExit("old and new actor names are required")
    if safe_component(old_actor) == safe_component(new_actor):
        print("actor name unchanged")
        return
    moved = move_actor_media(config, old_actor, new_actor)
    aliases = update_face_alias_actor(config, old_actor, new_actor)
    refresh_state(config)
    print(f"renamed actor {old_actor} => {new_actor}")
    print(f"moved {moved} files")
    print(f"updated {aliases} face aliases")


def exclude_actor(config: Config, actor_name: str) -> None:
    actor_name = actor_name.strip()
    if not actor_name:
        raise SystemExit("actor name is required")
    moved = move_actor_media(config, actor_name, None)
    aliases = update_face_alias_actor(config, actor_name, None)
    refresh_state(config)
    print(f"excluded actor {actor_name}")
    print(f"moved {moved} files")
    print(f"removed {aliases} face aliases")


def sync_authors(config: Config) -> None:
    normalize_organized(config)
    merge_named_face_groups(config)
    write_face_move_plan(config, apply=False)
    refresh_state(config)
    print("authors synced")


def face_cluster_report(config: Config) -> None:
    path = config.manifests / "face_groups.csv"
    if not path.exists():
        raise SystemExit("face_groups.csv not found. Run face-cluster first.")
    groups = defaultdict(lambda: {"faces": 0, "media": set(), "rep": ""})
    for row in dict_rows_from_csv(path):
        g = groups[row["face_group"]]
        g["faces"] += 1
        g["media"].add(row["media_path"])
        g["rep"] = g["rep"] or row.get("representative_frame", "")
    rows = []
    for group, data in groups.items():
        rows.append({"face_group": group, "faces": data["faces"], "media": len(data["media"]), "representative_frame": data["rep"]})
    rows.sort(key=lambda r: (r["media"], r["faces"]), reverse=True)
    out = config.manifests / "face_cluster_report.csv"
    with out.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=["face_group", "faces", "media", "representative_frame"])
        writer.writeheader()
        writer.writerows(rows)
    write_face_merge_suggestions(config)
    print(json.dumps({"groups": len(rows), "top": rows[:10]}, ensure_ascii=False))


def write_face_merge_suggestions(config: Config, limit: int = 300) -> None:
    groups_path = config.manifests / "face_groups.csv"
    if not groups_path.exists():
        return
    representatives = {}
    for row in dict_rows_from_csv(groups_path):
        group = row.get("face_group", "")
        if not group or group in representatives or not row.get("representative_frame"):
            continue
        representatives[group] = row
    face_index = {}
    face_index_by_frame = {}
    index_path = config.manifests / "face_index.csv"
    if index_path.exists():
        for row in dict_rows_from_csv(index_path):
            if row.get("embedding"):
                face_index[(row.get("media_path", ""), row.get("frame_path", ""))] = row
                face_index_by_frame.setdefault(row.get("frame_path", ""), row)
    rows = []
    keys = sorted(representatives)
    for i, left in enumerate(keys):
        left_row = representatives[left]
        left_idx = face_index.get((left_row.get("media_path", ""), left_row.get("representative_frame", ""))) or face_index_by_frame.get(left_row.get("representative_frame", ""))
        if not left_idx:
            continue
        left_vec = normalize_vector([float(x) for x in json.loads(left_idx["embedding"])])
        for right in keys[i + 1:]:
            right_row = representatives[right]
            right_idx = face_index.get((right_row.get("media_path", ""), right_row.get("representative_frame", ""))) or face_index_by_frame.get(right_row.get("representative_frame", ""))
            if not right_idx:
                continue
            right_vec = normalize_vector([float(x) for x in json.loads(right_idx["embedding"])])
            dist = vector_distance(left_vec, right_vec)
            if dist <= 0.95:
                rows.append({
                    "left_group": left,
                    "right_group": right,
                    "distance": f"{dist:.6f}",
                    "left_media": left_row.get("media_path", ""),
                    "right_media": right_row.get("media_path", ""),
                    "left_frame": left_row.get("representative_frame", ""),
                    "right_frame": right_row.get("representative_frame", ""),
                })
    rows.sort(key=lambda row: float(row["distance"]))
    out = config.manifests / "face_merge_suggestions.csv"
    with out.open("w", newline="", encoding="utf-8-sig") as handle:
        fields = ["left_group", "right_group", "distance", "left_media", "right_media", "left_frame", "right_frame"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows[:limit])


def apply_vision_labels(config: Config, min_score: float, apply: bool) -> None:
    path = config.manifests / "vision_labels.csv"
    if not path.exists():
        raise SystemExit("vision_labels.csv not found. Run vision-scan first.")
    rows = []
    moved = 0
    for row in dict_rows_from_csv(path):
        category = row.get("category", "")
        try:
            score = float(row.get("score") or 0)
        except Exception:
            score = 0.0
        if not category or score < min_score:
            continue
        src = config.library_root / row.get("media_path", "")
        if not src.exists() or not (config.review / "UnknownActor") in src.parents and not (config.review / "NeedsManualCheck") in src.parents:
            continue
        kind = "Videos" if src.suffix.lower() in VIDEO_EXT else "Photos"
        dest = unique_destination(config.review / "Keywords" / category / kind / src.name)
        rows.append({
            "action": "move",
            "category": category,
            "score": f"{score:.6f}",
            "source": rel(config.library_root, src),
            "destination": rel(config.library_root, dest),
            "representative_frame": row.get("representative_frame", ""),
        })
        if apply:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dest))
            moved += 1
    out = config.manifests / "vision_move_plan.csv"
    with out.open("w", newline="", encoding="utf-8-sig") as handle:
        fields = ["action", "category", "score", "source", "destination", "representative_frame"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(f"vision_move_plan {len(rows)} rows apply={apply} moved={moved}")
    if moved:
        clean_empty_dirs(config)
        refresh_state(config)


def dedupe_organized(config: Config, apply: bool) -> None:
    candidates = defaultdict(list)
    for path in all_organized_media_files(config):
        try:
            stat = path.stat()
        except Exception:
            continue
        normalized_name = re.sub(r"_[0-9a-fA-F]{8}(_\d{3})?(\.[^.]+)$", r"_HASH\2", path.name.lower())
        candidates[(normalized_name, stat.st_size)].append(path)
    rows = []
    moved = 0
    for (_name, _size), members in candidates.items():
        if len(members) < 2:
            continue
        by_md5 = defaultdict(list)
        for path in members:
            by_md5[md5_hash(path)].append(path)
        for digest, dupes in by_md5.items():
            if len(dupes) < 2 or digest.startswith("ERR_"):
                continue
            keep = sorted(dupes, key=lambda p: str(p))[0]
            for duplicate in sorted(dupes, key=lambda p: str(p))[1:]:
                kind = "Videos" if duplicate.suffix.lower() in VIDEO_EXT else "Photos"
                dest = unique_destination(config.review / "Duplicates" / "Exact" / kind / duplicate.name)
                rows.append({
                    "action": "move",
                    "keep": rel(config.library_root, keep),
                    "duplicate": rel(config.library_root, duplicate),
                    "destination": rel(config.library_root, dest),
                    "md5": digest,
                    "size_bytes": str(duplicate.stat().st_size),
                })
                if apply:
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(duplicate), str(dest))
                    moved += 1
    out = config.manifests / "organized_duplicates.csv"
    with out.open("w", newline="", encoding="utf-8-sig") as handle:
        fields = ["action", "keep", "duplicate", "destination", "md5", "size_bytes"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(f"organized_duplicates {len(rows)} rows apply={apply} moved={moved}")
    if moved:
        clean_empty_dirs(config)
        refresh_state(config)


def organize_review(config: Config) -> None:
    non_media = 0
    needs = config.review / "NeedsManualCheck"
    if needs.exists():
        for path in sorted([p for p in needs.rglob("*") if p.is_file()]):
            if path.suffix.lower() not in VIDEO_EXT | PHOTO_EXT:
                dest = unique_destination(config.review / "NonMedia" / path.name)
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(path), str(dest))
                non_media += 1
    classify_keywords(config)
    dedupe_organized(config, apply=True)
    clean_empty_dirs(config)
    refresh_state(config)
    print(f"non_media_moved {non_media}")


def normalize_organized(config: Config) -> None:
    actors_root = config.library_root / "Actors"
    moved_to_unknown = 0
    flattened = 0
    if not actors_root.exists():
        print("Actors directory does not exist")
        return

    for actor_dir in sorted([p for p in actors_root.iterdir() if p.is_dir()]):
        actor_name = actor_dir.name
        invalid_actor = is_ad_or_description(actor_name) or looks_like_random_or_batch_name(actor_name)
        for media_dir_name, unknown_kind in [("Photos", "Photo"), ("Videos", "Video")]:
            media_dir = actor_dir / media_dir_name
            if not media_dir.exists():
                continue
            for file_path in sorted([p for p in media_dir.rglob("*") if p.is_file()]):
                if invalid_actor:
                    ym = date_from_media_filename(file_path)
                    dest = config.review / "UnknownActor" / unknown_kind / ym / file_path.name
                    dest = unique_destination(dest)
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(file_path), str(dest))
                    moved_to_unknown += 1
                else:
                    dest = media_dir / file_path.name
                    if file_path.parent == media_dir:
                        continue
                    dest = unique_destination(dest)
                    shutil.move(str(file_path), str(dest))
                    flattened += 1
    clean_empty_dirs(config)
    print(f"moved_to_unknown {moved_to_unknown}")
    print(f"flattened_actor_files {flattened}")
    if moved_to_unknown or flattened:
        refresh_state(config)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Organize Telegram-downloaded media into manifests, actor folders, review folders, and duplicate staging.")
    parser.add_argument("--root", default=os.environ.get("TG_MEDIA_ROOT", DEFAULT_ROOT))
    parser.add_argument("--output-root", default=os.environ.get("TG_MEDIA_OUTPUT_ROOT", ""))
    parser.add_argument("--source-dirs", default=os.environ.get("TG_MEDIA_SOURCE_DIRS", ""))
    sub = parser.add_subparsers(dest="command", required=True)

    scan_cmd = sub.add_parser("scan")
    scan_cmd.add_argument("--full-media-probe", action="store_true", help="Use ffprobe/PIL for duration and dimensions; slower.")

    apply_cmd = sub.add_parser("apply")
    apply_cmd.add_argument("--limit", type=int)
    apply_cmd.add_argument("--include-review", action="store_true", help="Also move NeedsManualCheck files. Defaults to false.")

    rollback_cmd = sub.add_parser("rollback")
    rollback_cmd.add_argument("--limit", type=int)

    frames_cmd = sub.add_parser("extract-frames")
    frames_cmd.add_argument("--limit", type=int)
    frames_cmd.add_argument("--frames", type=int, default=3)
    frames_cmd.add_argument("--workers", type=int, default=int(os.environ.get("FRAME_WORKERS", "1")))
    frames_cmd.add_argument("--checkpoint-every", type=int, default=int(os.environ.get("FRAME_CHECKPOINT_EVERY", "100")))
    frames_cmd.add_argument("--retry-failed", action="store_true", help="Reserved for retrying rows listed in frame_errors.csv.")

    face_scan_cmd = sub.add_parser("face-scan")
    face_scan_cmd.add_argument("--limit", type=int)

    vision_scan_cmd = sub.add_parser("vision-scan")
    vision_scan_cmd.add_argument("--limit", type=int)

    face_cluster_cmd = sub.add_parser("face-cluster")
    face_cluster_cmd.add_argument("--threshold", type=float, default=0.80)

    face_apply_cmd = sub.add_parser("apply-face-groups")
    face_apply_cmd.add_argument("--apply", action="store_true", help="Actually move files. Defaults to dry-run face_move_plan.csv only.")

    vision_apply_cmd = sub.add_parser("apply-vision-labels")
    vision_apply_cmd.add_argument("--min-score", type=float, default=0.36)
    vision_apply_cmd.add_argument("--apply", action="store_true", help="Actually move Unknown/NeedsManualCheck files by vision label. Defaults to dry-run.")

    dedupe_cmd = sub.add_parser("dedupe-organized")
    dedupe_cmd.add_argument("--apply", action="store_true", help="Move exact duplicate organized media to _REVIEW/Duplicates/Exact.")

    name_cmd = sub.add_parser("name-face-group")
    name_cmd.add_argument("face_group")
    name_cmd.add_argument("actor_name")
    merge_cmd = sub.add_parser("merge-face-groups")
    merge_cmd.add_argument("source_group")
    merge_cmd.add_argument("target_group")
    merge_named_cmd = sub.add_parser("merge-named-face-groups")
    merge_named_cmd.add_argument("actor_name", nargs="?")
    rename_actor_cmd = sub.add_parser("rename-actor")
    rename_actor_cmd.add_argument("old_actor")
    rename_actor_cmd.add_argument("new_actor")
    exclude_actor_cmd = sub.add_parser("exclude-actor")
    exclude_actor_cmd.add_argument("actor_name")

    analyze_cmd = sub.add_parser("analyze-filenames")
    analyze_cmd.add_argument("--min-count", type=int, default=5)

    sub.add_parser("face-setup")
    sub.add_parser("face-cluster-report")
    sub.add_parser("clean-empty-dirs")
    sub.add_parser("normalize-organized")
    sub.add_parser("classify-keywords")
    sub.add_parser("organize-review")
    sub.add_parser("refresh-state")
    sub.add_parser("sync-authors")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_root = Path(args.output_root) if args.output_root else None
    source_dirs = [item.strip() for item in args.source_dirs.split(",") if item.strip()] if args.source_dirs else None
    config = Config(root=Path(args.root), output_root=output_root, source_dirs=source_dirs, fast=not getattr(args, "full_media_probe", False))
    if args.command == "scan":
        scan(config)
    elif args.command == "apply":
        apply_plan(config, args.limit, args.include_review)
    elif args.command == "rollback":
        rollback(config, args.limit)
    elif args.command == "clean-empty-dirs":
        clean_empty_dirs(config)
    elif args.command == "normalize-organized":
        normalize_organized(config)
    elif args.command == "classify-keywords":
        classify_keywords(config)
    elif args.command == "refresh-state":
        refresh_state(config)
    elif args.command == "extract-frames":
        extract_frames(config, args.limit, args.frames, args.workers, args.checkpoint_every, args.retry_failed)
    elif args.command == "face-setup":
        face_setup()
    elif args.command == "face-scan":
        face_scan(config, args.limit)
    elif args.command == "vision-scan":
        vision_scan(config, args.limit)
    elif args.command == "face-cluster":
        face_cluster(config, args.threshold)
    elif args.command == "face-cluster-report":
        face_cluster_report(config)
    elif args.command == "apply-face-groups":
        write_face_move_plan(config, args.apply)
    elif args.command == "apply-vision-labels":
        apply_vision_labels(config, args.min_score, args.apply)
    elif args.command == "dedupe-organized":
        dedupe_organized(config, args.apply)
    elif args.command == "name-face-group":
        name_face_group(config, args.face_group, args.actor_name)
    elif args.command == "merge-face-groups":
        merge_face_groups(config, args.source_group, args.target_group)
    elif args.command == "merge-named-face-groups":
        merge_named_face_groups(config, args.actor_name)
    elif args.command == "rename-actor":
        rename_actor(config, args.old_actor, args.new_actor)
    elif args.command == "exclude-actor":
        exclude_actor(config, args.actor_name)
    elif args.command == "sync-authors":
        sync_authors(config)
    elif args.command == "analyze-filenames":
        analyze_filenames(config, args.min_count)
    elif args.command == "organize-review":
        organize_review(config)


if __name__ == "__main__":
    main()

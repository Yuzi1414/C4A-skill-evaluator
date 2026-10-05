#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
C4A 技能提交自动评审器（C4 Skill Submission Evaluator）
======================================================
纯 Python 标准库实现，零第三方依赖。

流水线：文件采集 → 作者识别 → 完整性检查（5 必交文件）→ 质量评审（四条件）→ 报告生成

用法：
    python skill_evaluator.py <文件夹路径> [--out 输出目录] [--format md,csv]

示例：
    python skill_evaluator.py "D:/C4提交收集" --out "./reports"
"""

import argparse
import csv
import datetime
import json
import os
import re
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUBRIC_PATH = HERE / "references" / "c4_rubric.json"

TEXT_EXT = {".md", ".txt", ".py", ".skill", ".json", ".yaml", ".yml",
            ".csv", ".html", ".js", ".sh", ".xml"}
MEDIA_EXT = {".mp4", ".mov", ".webm", ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff"}


def load_rubric():
    with open(RUBRIC_PATH, encoding="utf-8") as f:
        return json.load(f)


def read_text(path):
    """尽力读取文本内容；.docx 用 zipfile 抽 document.xml；媒体/PDF 返回空串（仅文件名匹配）。"""
    p = Path(path)
    ext = p.suffix.lower()
    if ext in MEDIA_EXT:
        return ""
    if ext == ".docx":
        try:
            with zipfile.ZipFile(path) as z:
                xml = z.read("word/document.xml").decode("utf-8", errors="ignore")
            return re.sub(r"<[^>]+>", " ", xml)
        except Exception:
            return ""
    if ext in (".pdf", ".pptx", ".xlsx"):
        return ""
    try:
        raw = p.read_bytes()
    except Exception:
        return ""
    for enc in ("utf-8", "gbk", "utf-16"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="ignore")


def iter_files(folder):
    """递归列出文件夹内所有文件，跳过隐藏目录/文件。"""
    out = []
    for root, dirs, files in os.walk(folder):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for name in files:
            if name.startswith("."):
                continue
            out.append(Path(root) / name)
    return out


def is_c4_file(filename):
    """是否 C4/C4A 相关提交文件：文件名含 _C4_ 或 _C4A_ 标记。"""
    return bool(re.search(r"_C4[AB]?_", filename, re.IGNORECASE))


def extract_author(filename):
    """从文件名提取作者：取第一个 `_C4_` 标记之前的前缀；无标记返回 None。"""
    m = re.search(r"^(.*?)_C4[AB]?_", filename, re.IGNORECASE)
    if m:
        author = m.group(1).strip(" _-")
        return author if author else None
    return None


def classify(files):
    """把文件清单划分为「C4 相关」与「非 C4 文件」，并尝试提取作者。"""
    c4_files, other = [], []
    for f in files:
        if is_c4_file(f.name):
            c4_files.append(f)
        else:
            other.append(f)
    return c4_files, other


def group_by_author(c4_files):
    """按作者分组。作者提取链：文件名前缀 → 父目录名 → Unknown。"""
    groups = {}
    for f in c4_files:
        author = extract_author(f.name)
        if not author:
            author = f.parent.name
        if not author or author.lower() in ("files", "filesync", "wechat"):
            author = "Unknown"
        groups.setdefault(author, []).append(f)
    return groups


def filename_matches(path, spec):
    """仅按文件名模式匹配（高优先级）。"""
    name = Path(path).name
    return any(p.lower() in name.lower() for p in spec.get("filename_patterns", []))


def content_matches(path, spec):
    """仅按内容信号匹配（兜底）。"""
    text = read_text(path)
    if not text:
        return False
    low = text.lower()
    return any(sig.lower() in low for sig in spec.get("content_signals", []))

def check_completeness(files, rubric):
    """两遍匹配：先文件名（高优先级），再用内容信号兜底，避免内容信号重叠导致误配。"""
    required = rubric["required_deliverables"]
    results = {}
    assigned = set()
    # 第一遍：文件名优先
    for key, spec in required.items():
        match = None
        for f in files:
            if str(f) in assigned:
                continue
            if filename_matches(f, spec):
                match = f
                break
        results[key] = {
            "label": spec["label_cn"],
            "status": match is not None,
            "match": match.name if match else None,
        }
        if match:
            assigned.add(str(match))
    # 第二遍：内容信号兜底（仅对仍未匹配的槽位）
    for key, spec in required.items():
        if results[key]["status"]:
            continue
        match = None
        for f in files:
            if str(f) in assigned:
                continue
            if content_matches(f, spec):
                match = f
                break
        if match:
            results[key]["status"] = True
            results[key]["match"] = match.name
            assigned.add(str(match))
    return results


def score_criterion(text, spec):
    """按正向/负向信号打分。返回 (等级 2/1/0, 命中正向信号, 命中负向信号)。"""
    low = text.lower()
    pos_hits = [s for s in spec.get("positive_signals", []) if s.lower() in low]
    neg_hits = [s for s in spec.get("negative_signals", []) if s.lower() in low]
    min_pos = spec.get("min_positive", 2)
    if len(pos_hits) >= min_pos:
        level = 2
    elif len(pos_hits) >= 1:
        level = 1
    else:
        level = 0
    if neg_hits:
        level = max(0, level - 1)  # 硬编码路径/密钥等负面信号降一档
    return level, pos_hits, neg_hits


def evaluate_quality(files, rubric):
    """对作者的全部文件内容做四条件质量评审。"""
    text = "\n".join(read_text(f) for f in files)
    criteria = rubric["quality_criteria"]
    out = {}
    for key, spec in criteria.items():
        level, pos, neg = score_criterion(text, spec)
        out[key] = {
            "label": spec["label_cn"],
            "level": level,          # 2=✅, 1=⚠️, 0=❌
            "pos_hits": pos,
            "neg_hits": neg,
        }
    return out


LEVEL_SYMBOL = {2: "✅", 1: "⚠️", 0: "❌"}
LEVEL_VALUE = {2: 1.0, 1: 0.5, 0: 0.0}


def latest_version_index(files):
    """返回每个作者最高版本号（识别 _v2/_v3...），用于版本追踪。"""
    ver = 1
    for f in files:
        m = re.search(r"_v(\d+)", f.name, re.IGNORECASE)
        if m:
            ver = max(ver, int(m.group(1)))
    return ver


def evaluate(folder, rubric):
    """主流水线：扫描→分类→分组→逐作者完整性+质量评审。返回结构化结果。"""
    all_files = iter_files(folder)
    c4_files, other = classify(all_files)
    groups = group_by_author(c4_files)
    authors = {}
    for author, files in groups.items():
        completeness = check_completeness(files, rubric)
        quality = evaluate_quality(files, rubric)
        n_present = sum(1 for v in completeness.values() if v["status"])
        completeness_score = n_present / 5.0
        quality_score = sum(LEVEL_VALUE[q["level"]] for q in quality.values()) / 4.0
        composite = completeness_score * 0.4 + quality_score * 0.6
        authors[author] = {
            "files": sorted(f.name for f in files),
            "n_files": len(files),
            "version": latest_version_index(files),
            "completeness": completeness,
            "n_present": n_present,
            "completeness_score": completeness_score,
            "quality": quality,
            "quality_score": quality_score,
            "composite": composite,
        }
    return {
        "folder": str(folder),
        "n_authors": len(authors),
        "n_c4_files": len(c4_files),
        "n_other_files": len(other),
        "other_files": sorted(f.name for f in other),
        "authors": authors,
    }


def build_report(result, rubric, scanned_at):
    """生成 Markdown 评审报告。"""
    authors = result["authors"]
    n = len(authors)
    if n == 0:
        n_complete = n_partial = n_insufficient = 0
        avg = 0.0
    else:
        n_complete = sum(1 for a in authors.values() if a["n_present"] == 5)
        n_partial = sum(1 for a in authors.values() if 3 <= a["n_present"] < 5)
        n_insufficient = sum(1 for a in authors.values() if a["n_present"] < 3)
        avg = sum(a["composite"] for a in authors.values()) / n

    lines = []
    lines.append("# C4 提交自动评审报告\n")
    lines.append(f"生成时间：{scanned_at}")
    lines.append(f"扫描路径：{result['folder']}")
    lines.append(f"识别提交：{n} 位作者，{result['n_c4_files']} 个 C4 文件，"
                 f"{result['n_other_files']} 个非 C4 文件\n")
    lines.append("## 一、班级总览\n")
    lines.append("| 指标 | 数值 |")
    lines.append("|------|------|")
    lines.append(f"| 总提交人数 | {n} |")
    lines.append(f"| 完整提交（5/5） | {n_complete} |")
    lines.append(f"| 部分提交（3-4/5） | {n_partial} |")
    lines.append(f"| 严重缺失（<3/5） | {n_insufficient} |")
    lines.append(f"| 平均综合分 | {avg:.3f} |\n")

    if result["other_files"]:
        lines.append("> ⚠️ 以下文件不符合 `_C4_` 命名规范，已从评审中剔除："
                     + "、".join(result["other_files"]) + "\n")

    # 排名表
    ranked = sorted(authors.items(), key=lambda kv: -kv[1]["composite"])
    lines.append("## 二、排名\n")
    lines.append("| 排名 | 作者 | 版本 | 完整性 | 质量分 | 综合分 |")
    lines.append("|------|------|------|--------|--------|--------|")
    for i, (author, a) in enumerate(ranked, 1):
        lines.append(f"| {i} | {author} | v{a['version']} | "
                     f"{a['n_present']}/5 | {a['quality_score']:.2f}/1 | "
                     f"{a['composite']*100:.0f} |")
    lines.append("")

    # 作者详情
    lines.append("## 三、作者详情\n")
    for author, a in ranked:
        lines.append(f"### {author}（v{a['version']}）\n")
        lines.append("**完整性检查：**\n")
        lines.append("| 必交文件 | 状态 | 匹配文件 |")
        lines.append("|----------|------|----------|")
        for key, spec in rubric["required_deliverables"].items():
            c = a["completeness"][key]
            sym = "✅" if c["status"] else "❌"
            lines.append(f"| {spec['label_cn']} | {sym} | {c['match'] or '—'} |")
        lines.append("")
        lines.append("**质量评审：**\n")
        lines.append("| 条件 | 评级 | 依据 |")
        lines.append("|------|------|------|")
        for key, spec in rubric["quality_criteria"].items():
            q = a["quality"][key]
            if q["neg_hits"]:
                basis = "命中负面信号：" + "、".join(q["neg_hits"])
            elif q["pos_hits"]:
                basis = "命中：" + "、".join(q["pos_hits"][:4])
            else:
                basis = "未命中任何正向信号"
            lines.append(f"| {spec['label_cn']} | {LEVEL_SYMBOL[q['level']]} | {basis} |")
        lines.append("")
        # 改进建议
        tips = []
        for key, spec in rubric["required_deliverables"].items():
            if not a["completeness"][key]["status"]:
                tips.append(f"补充缺失文件「{spec['label_cn']}」")
        for key, spec in rubric["quality_criteria"].items():
            if a["quality"][key]["level"] < 2:
                tips.append(f"强化「{spec['label_cn']}」：{'; '.join(spec['check_items'])}")
        if tips:
            lines.append("**改进建议：**")
            for t in tips:
                lines.append(f"- {t}")
        lines.append("\n---\n")
    return "\n".join(lines)


def build_csv(result):
    """生成 CSV 详表。"""
    rows = []
    for author, a in sorted(result["authors"].items(), key=lambda kv: -kv[1]["composite"]):
        row = {
            "作者": author,
            "版本": f"v{a['version']}",
            "文件数": a["n_files"],
            "完整性(5分)": a["n_present"],
            "质量分": round(a["quality_score"], 3),
            "综合分": round(a["composite"], 3),
        }
        for key, q in a["quality"].items():
            row[q["label"]] = LEVEL_SYMBOL[q["level"]]
        rows.append(row)
    return rows


def main(argv=None):
    parser = argparse.ArgumentParser(description="C4 技能提交自动评审器")
    parser.add_argument("folder", help="包含 C4 提交文件的本地文件夹路径")
    parser.add_argument("--out", default=".", help="报告输出目录（默认当前目录）")
    parser.add_argument("--format", default="md,csv",
                        help="输出格式，逗号分隔：md,csv（默认 md,csv）")
    args = parser.parse_args(argv)

    folder = Path(args.folder)
    if not folder.is_dir():
        print(f"[错误] 不是有效文件夹：{folder}", file=sys.stderr)
        return 1

    rubric = load_rubric()
    result = evaluate(folder, rubric)
    scanned_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []

    if "md" in args.format:
        md = build_report(result, rubric, scanned_at)
        md_path = out_dir / "评审报告.md"
        md_path.write_text(md, encoding="utf-8")
        written.append(str(md_path))

    if "csv" in args.format:
        rows = build_csv(result)
        csv_path = out_dir / "评审详表.csv"
        with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
            if rows:
                w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
                w.writeheader()
                w.writerows(rows)
        written.append(str(csv_path))

    print(f"[完成] 扫描 {result['n_authors']} 位作者，"
          f"{result['n_c4_files']} 个 C4 文件")
    for w in written:
        print(f"[输出] {w}")
    return 0


if __name__ == "__main__":
    sys.exit(main())


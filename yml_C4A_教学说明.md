# C4A skill-evaluator 教学说明（上手指南）

> 一个零依赖的「C4 技能提交自动评审器」：扫描提交文件夹 → 识别作者 → 检查 5 类必交文件 → 按四条件评质量 → 输出 MD + CSV 评审报告。

## 1. 它能做什么

把「帮老师手动检查几十份技能提交」这件事自动化：

1. **扫描识别**：递归扫描文件夹，按 `_C4_` 命名规范识别提交文件与作者（前缀 → 父目录 → Unknown）。
2. **完整性检查**：检查 5 类必交文件是否齐全（Skill 说明 / 可执行内容 / Demo / 教学说明 / AI 日志）。
3. **质量评审**：按四条件打分（可复用 / 可执行 / 可验证 / IO 明确），并检测硬编码路径等负面信号。
4. **生成报告**：输出班级总览、排名、逐作者详情与改进建议（Markdown + CSV）。

## 2. 环境要求

- Python 3.8+
- **零第三方依赖**（只用标准库 os / re / json / csv / zipfile / argparse），无需 pip install
- 跨平台（Windows / macOS / Linux 均可）

## 3. 安装与准备

无需安装。把 `yml_C4A_skill-evaluator/` 目录拷到本地即可，其中：

- `SKILL.md` —— 技能门面（name: c4-skill-evaluator）
- `skill_evaluator.py` —— 主程序
- `references/c4_rubric.json` —— 信号库（5 必交文件信号 + 四质量维度 + 阈值），可热更新

## 4. 使用方法

```bash
python skill_evaluator.py <文件夹路径> [--out 输出目录] [--format md,csv]
```

**输入**：一个包含学生 C4 提交的文件夹，文件须符合 `作者_C4_xxx` 命名（如 `yml_C4_skill说明.md`、`zhangsan_C4_demo.mp4`）。

**输出**：`评审报告.md`（可读版）+ `评审详表.csv`（utf-8-sig，可进 Excel）。

示例：

```bash
# 评审合成样本
python skill_evaluator.py test_fixtures --out reports_fixtures

# 评审真实提交
python skill_evaluator.py "C4_技能分享与传播" --out reports_self
```

## 5. 常见坑与 FAQ

- **文件没被识别？** 确认文件名含 `_C4_`（区分大小写不敏感）。课程说明文件（CHALLENGE.md、README.md 等）会被自动剔除，属正常。
- **为什么某文件被判「可复用 ⚠️」？** 「可复用」要求 ≥2 个正向信号（安装/环境要求/兼容/跨平台等）且无负面信号（硬编码绝对路径、`api_key=` 等）。
- **评分怎么算的？** `综合分 = 完整性 × 0.4 + 质量 × 0.6`；完整性 = 命中文件数 / 5；质量 = 四条件平均（✅=1 / ⚠️=0.5 / ❌=0）。

## 6. 限制（诚实声明）

- 规则评审是「信号级」判定，不能完全替代人工语义判断。
- PDF / PPTX 正文不解析（纯标准库限制），仅按文件名匹配；`.docx` 用 zipfile 抽取正文。
- `--llm` 深审扩展点仅预留未接入，当前为纯规则结果。

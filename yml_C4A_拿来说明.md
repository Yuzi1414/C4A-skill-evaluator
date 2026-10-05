# C4A 拿来说明（参考 / 拿了 / 改了）

> 说明：C4A 挑战要求站在「前人技能」肩膀上，注明从哪来、拿了什么、改了什么。下表逐项登记。

## 1. 起点技能的可获得性核查

挑战正文指定了两个起点技能：`wechat-doc-mapper.skill`（扫描/归档）与 `skill-explainer.skill`（解读）。我检索了工作区与 C4/C4A 材料目录，**这两个原始 `.skill` 均未随包实际下发**。实际拿到的是平台 starter `c4a-skill-evaluator-starter`，其 `SKILL.md` 自述为「wechat-doc-mapper 的 C4 聚焦版」。因此本项目的拿来主义基座是 **starter 而非原始 wechat-doc-mapper**，此差异如实登记，避免虚标来源。

## 2. 逐项登记

| # | 来源 | 内容 | 状态 | 说明 / 改动 |
|---|------|------|------|-------------|
| 1 | starter SKILL.md | 工作流骨架：采集→识别→完整性→质量→报告 | 拿了 | 落成可运行 Python 流水线 `skill_evaluator.py` |
| 2 | starter SKILL.md | 作者提取优先级：文件名前缀→子目录→元数据 | 改了 | 元数据提取因纯 stdlib 限制改为「文件名前缀→父目录名→Unknown」，PDF/DOCX 元数据未做（诚实标注） |
| 3 | starter c4_rubric.yaml | 5 必交文件的文件名/内容信号 | 拿了 | 转成 `c4_rubric.json`，stdLib `json` 读取，保留原信号 |
| 4 | starter c4_rubric.yaml | 四质量维度（可复用/可执行/可验证/IO 明确） | 改了 | 每维度新增 `min_positive` 阈值与负面信号（硬编码路径/密钥），使评分可计算 |
| 5 | C4 评分规则 | completeness×0.4 + quality×0.6 | 拿了 | 公式不变，✅/⚠️/❌→1.0/0.5/0.0 |
| 6 | 自研 | 文件名优先级两遍匹配 | 加了 | 修复内容信号重叠导致的误配（skill说明 被错配到 AI日志.md） |
| 7 | 自研 | 版本追踪 `_v2/_v3` | 加了 | 报告显示每位作者最高版本 |
| 8 | 自研 | CSV 详表 + 排名 + 改进建议 | 加了 | L4 班级总览能力 |

## 3. 明确未拿 / 未做的项（诚实边界）

- 原始 `wechat-doc-mapper.skill` 与 `skill-explainer.skill`：未随包下发，**未拿到**，改用 starter。
- PDF / PPTX 正文解析：纯标准库不做二进制文档解析，回退文件名匹配。
- LLM 深审（L3）：仅预留扩展点，未接入真实 LLM（避免凭空声称）。
- 微信文档在线抓取：改为「本地文件夹」输入（微信文件需先下载到本地再评审）。

## 4. 合规自检

- 所有外部来源均已登记来源、状态（参考/拿了/改了/加了）。
- 未伪造「已使用原始 wechat-doc-mapper」的说法。
- 未声称未运行的 LLM 深审结果。

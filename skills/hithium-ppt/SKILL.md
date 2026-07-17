---
name: hithium-ppt
description: 把电池仿真结果做成海辰储能(HiThium)企业模板的 PPTX 汇报:品牌配色/logo、封面-摘要-方法-工况-结果-结论骨架、matplotlib 图嵌入与裁剪、中文字体。不做仿真计算本身,结论文字交给 sim-conclusion。
---

# 海辰仿真报告 PPTX 生成器

## 何时用 / 不用
- **用**:已有仿真结果(matplotlib 图、CSV、关键数值),要做成公司模板的汇报 PPT。
- **不用**:跑仿真本身(那是 PyBaMM/COMSOL 的活)、写结论文字(调 `/sim-conclusion`)、非海辰模板的通用 PPT(用公共 `pptx` skill 即可)。

## 生成引擎(二选一,本 skill 不重复造轮子)
- 默认沿用历史可跑通的 **PptxGenJS**(Node)管线;或
- 用公共 `pptx` skill 的 python-pptx 管线。
本 skill 只规定"长什么样、放什么、怎么嵌图",引擎细节交给上面任一个。

## 已提取企业模板
- `references/report_ppt_template_20240910.md`: 从 `E:\Downloads\报告作图要求&PPT模版.pptx` 提取的人读版模板规范。
- `references/report_ppt_template_20240910_spec.json`: 机器可读版式/坐标/色板规范。
- `references/report_ppt_template_20240910_assets.json`: 关键 logo/背景图的 base64 资产。工作区 PNG 可能被 DLP 加密,生成 PPT 时优先从该 JSON 解码到临时目录。
- `references/report_ppt_template_20240910_image_usages.json`: 原 PPT 中母版和正文页图片位置清单,用于核对图片来源。

---

## 品牌 Token(⚠️ 下列 hex 为合理默认值,首次使用请替换成公司官方色值后存档)

| Token | 用途 | 默认值 |
|---|---|---|
| `navy` | 主色 / 封面 / 结论条底色 | `#0B2447` |
| `red` | 强调 / 数字圆点 / 关键提示 | `#C8102E` |
| `gray` | 正文卡片底 / 次级信息 | `#6B7280` |
| `blue` | 第三栏卡片 / 流程节点 | `#2E6CC4` |
| `amber` | 结论条上的高亮词 | `#F5A623` |
| `cardBg` | 卡片背景 | `#F4F6F9` |
| `textDark` | 正文 | `#1F2937` |

**版式标识(固定)**
- 右上角:HITHIUM 六边形 logo
- 封面/页眉区:CCC 三角 logo
- 三栏卡片布局(navy / red·gray / blue 区分层级)
- 红色数字圆点(①②③)做要点编号
- 底部深 navy 结论条,关键词用 `amber` 高亮

字体:正文 **微软雅黑**,缺字回退 **Noto Sans CJK**;西文数字可用同族无衬线。

---

## 标准报告骨架(深色封面+深色结论"三明治")

1. **封面** — navy 满底,标题 + 副标题 + 项目号/日期 + logo。
2. **执行摘要** — 3 张 stat card(如 容量保持率/RRMSE/成本节省),一句话核心结论。
3. **背景与目标** — 为什么做、要回答什么问题。
4. **方法流程** — PyBaMM/COMSOL/P2D 建模链路图(节点用 `blue`)。
5. **工况定义** — 把测试 protocol 重排版;多步序列用箭头记法压缩(如 `0.55P→3.55V ⇒ 静置 ⇒ …`)。
6. **结果页(1~N 页)** — 每页:左图(嵌入 matplotlib)+ 右侧要点;**结论文字调 `/sim-conclusion` 生成**。
7. **结论页** — navy 满底,要点 + amber 高亮,呼应执行摘要。

> 单页/少页场景(如调频寿命单页)按需裁剪,但封面色/字体/logo/红点规范保持一致。

---

## 出图与嵌图规则(踩过的坑,务必遵守)
1. **图先于排版生成**:matplotlib 出图设 `dpi≥200`,中文用 `Microsoft YaHei`/`Noto`,避免方块。
2. **裁剪用 PIL**:源图带多余标注/边框时,先 `PIL.Image.crop` 再嵌入,别整张塞。
3. **能用原生表就别截图**:对比类数据(如三组循环寿命)用 PPT **原生表格**替换标注图,清晰且可改。
4. **图比例**:结果页左图占 ~55% 宽,右侧留要点;别让图溢出页边。
5. **数值一致性自检**:stat card / 表格 / 结论里的同一数,必须三处一致(历史上出过 5μm/6μm 读串)。

---

## 交付前 Checklist
- [ ] 配色/logo/字体符合品牌 Token
- [ ] 封面、结论页均为深色三明治
- [ ] 每张图清晰、已裁剪、无中文方块
- [ ] 关键数值三处一致
- [ ] 结论文字已由 `/sim-conclusion` 产出(机制链风格、无套话)
- [ ] 文件名:`{项目号}_{主题}_仿真报告_{日期}.pptx`

## 用法
```
/hithium-ppt 主题:587Ah 负载/过载工况对循环寿命影响;素材:3张matplotlib图+工况protocol;要9页
```

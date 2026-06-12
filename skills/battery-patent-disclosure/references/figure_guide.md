# 附图绘制指南（黑白专利风格）

每份交底书配 **5 张**黑白线条图。用 `assets/fig_helpers.py` 的 `setup_cjk()` 与辅助函数。**每张生成后必须 `view` 检查并修正**。

## 标准 5 图
1. **结构示意图** — 截面或俯视，带数字标号（如 1 集流体、2 涂层、2a/2b/2c 子层、3 隔膜、4 焊印、5 通道、H 厚度）。结构类必备。
2. **对比曲线** — 现有=虚线(`--`)，本发明=实线(`-`)。常配次坐标或上下分栏展示"分布剖面"。
3. **机理图** — 机理示意，或"机理 ↔ 可观测特征映射表"（行=机理，列=容量/DCR/dV/dQ/EIS/弛豫，单元 ●强/△中/○弱）。
4. **流程图（S1–S5）**（结构类：设计与制造流程）**或 系统架构图**（软件/方法类：模块 1–6 + 子单元 + 闭环）。
5. **技术效果/外推曲线** — 如 DCR break-in 收敛、容量拐点外推（带置信区间）、温升/析锂裕度均匀化等。

## 黑白约定
- 仅黑/白/灰；填充用灰阶（`'0.78'`/`'0.85'`/`'0.6'`）；线宽 1–2.2；实线=本发明、虚线=现有、点线/点划线=第三条或辅助量。
- 标题居中、`pad=8` 左右；图题以斜体在文档里单独成行（由 docx 的 `cap()` 出）。

## 必避的坑（都踩过）
1. **缺字形**：Noto CJK 缺 **Unicode 上标减号 `⁻`**（U+207B）和**上/下标数字**（如 `⁻¹`、`₀`）。
   - 写 `dV/dQ`，不要写 `dV·dQ⁻¹`。
   - 下标用 mathtext：`'j$_0$(x)'`、`'W$_{max}$'`、`'A·mm$^{-2}$'`（mathtext 的上下标可渲染；直接用 Unicode 上下标会变豆腐块）。
2. **箭头方向画反**：`ax.annotate('', xy=(箭头尖端), xytext=(箭尾))` —— 箭头从 `xytext` 指向 `xy`。流程图向下时，尾在上(box 底)、尖在下(下一 box 顶)。用 `fig_helpers.arrow(ax, x0,y0, x1,y1)`（从 (x0,y0) 指向 (x1,y1)）避免混淆。
3. **标注/图例重叠**：
   - 标题被高图形顶到 → 压低图形高度、抬高标题(`pad`/`ylim`/`suptitle y`)。
   - 图例与标注挤在一起 → 把标注移到空白区，或把图例换角；曲线本身挤（如电流密度 + 宽度剖面）→ **改上下分栏**(`subplots(2,1,sharex=True, gridspec_kw={'height_ratios':[...]})`)。
   - 文字压在曲线上 → 沿空白处放，必要时加白色 `bbox`。
4. **颗粒密度/梯度方向别画反**：如"隔膜侧高孔隙=颗粒稀疏、集流体侧低孔隙=颗粒密集"，核对后再定。
5. **示意但要自洽**：如"等面积"论证（梯度孔隙率两曲线下面积相等 ⇒ 平均不变）要真的画成面积相等。

## 字体注册（fig_helpers 已封装）
```python
from matplotlib import font_manager
fp='/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
font_manager.fontManager.addfont(fp)
plt.rcParams['font.family']=font_manager.FontProperties(fname=fp).get_name()
plt.rcParams['axes.unicode_minus']=False   # 负号正常显示
```
注意 `get_name()` 可能返回 'Noto Sans CJK JP'（同一 pan-CJK 字库，简体字照常显示，可忽略）。

## 保存与尺寸
- `plt.savefig(path, dpi=180, bbox_inches='tight', facecolor='white')`。
- 用 PIL 读 PNG 像素尺寸算宽高比，在 docx 里按比例设 `transformation`（正文宽 ≈ 480–490 px 横图；竖版流程图 ~360 px 宽）。

`fig_helpers.py` 末尾带一个 `__main__` 自检：直接 `python3 fig_helpers.py` 会生成一张样例图，确认字体与辅助函数可用。

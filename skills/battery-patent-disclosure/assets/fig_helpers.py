# -*- coding: utf-8 -*-
"""
fig_helpers.py — 电池交底书黑白附图辅助库。

用法：
    from fig_helpers import setup_cjk, box, arrow, flowchart, BLK, FILL
    setup_cjk()
    fig, ax = plt.subplots(...)
    ...
每张图生成后务必 view 检查并修正（见 references/figure_guide.md 的踩坑清单）。
直接运行  python3 fig_helpers.py  会生成 _selftest.png 自检字体与辅助函数。
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mp

BLK = 'black'
FILL = '0.80'        # 浅灰填充
FILL2 = '0.86'       # 更浅
LINE_GRAY = '0.45'

def setup_cjk(font_path='/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'):
    """注册中文字体并设置 rcParams。返回解析到的字体名。"""
    from matplotlib import font_manager
    font_manager.fontManager.addfont(font_path)
    name = font_manager.FontProperties(fname=font_path).get_name()
    plt.rcParams['font.family'] = name
    plt.rcParams['axes.unicode_minus'] = False   # 负号正常
    plt.rcParams['svg.fonttype'] = 'none'
    return name

def arrow(ax, x0, y0, x1, y1, lw=1.6, ms=13, ls='-', color=BLK):
    """从 (x0,y0) 指向 (x1,y1) 的箭头。流程图向下时：尾在上、尖在下。"""
    ax.annotate('', xy=(x1, y1), xytext=(x0, y0),
                arrowprops=dict(arrowstyle='-|>', lw=lw, color=color, ls=ls, mutation_scale=ms))

def dblarrow(ax, x0, y0, x1, y1, lw=1.6, ms=13, color=BLK):
    """双向箭头（如 仿真引擎 <-> Agent）。"""
    ax.annotate('', xy=(x1, y1), xytext=(x0, y0),
                arrowprops=dict(arrowstyle='<|-|>', lw=lw, color=color, mutation_scale=ms))

def dim(ax, x0, y0, x1, y1, lw=1.1, color=BLK):
    """尺寸标注（双箭头细线），用于 W_min/W_max/H 等。"""
    ax.annotate('', xy=(x1, y1), xytext=(x0, y0),
                arrowprops=dict(arrowstyle='<->', lw=lw, color=color))

def box(ax, x, y, w, h, title='', lines=None, lw=1.6, fc='none',
        fs_t=10.5, fs_l=8.6, rounded=True, title_bold=True):
    """画一个（圆角）矩形框，顶部标题 + 可选多行说明。坐标为左下角。"""
    if rounded:
        ax.add_patch(mp.FancyBboxPatch((x, y), w, h,
            boxstyle="round,pad=0.02,rounding_size=0.10", facecolor=fc, edgecolor=BLK, lw=lw))
    else:
        ax.add_patch(mp.Rectangle((x, y), w, h, facecolor=fc, edgecolor=BLK, lw=lw))
    if title:
        ax.text(x + w/2, y + h - 0.30, title, fontsize=fs_t,
                fontweight='bold' if title_bold else 'normal', ha='center', va='top')
    if lines:
        for i, ln in enumerate(lines):
            ax.text(x + 0.18, y + h - 0.72 - i*0.42, ln, fontsize=fs_l, ha='left', va='top')

def flowchart(ax, steps, x=1.0, w=8.0, top=9.4, bh=1.3, gap=None, title_fs=11.5):
    """竖直流程图。steps = [(编号, 文本), ...]，文本可含 \\n。箭头自动向下。
    画在 ax 上；调用方先设 set_xlim(0,10)/set_ylim(0,~10)/axis('off')。"""
    n = len(steps)
    if gap is None:
        gap = max(0.25, (top - 0.4 - n*bh) / max(1, n-1))
    y = top
    for i, (sid, txt) in enumerate(steps):
        yb = y - bh
        box(ax, x, yb, w, bh, '', None)
        ax.text(x + 0.5, y - bh/2, sid, fontsize=11.5, fontweight='bold', va='center')
        ax.text(x + 1.65, y - bh/2, txt, fontsize=8.4, va='center')
        if i < n - 1:
            arrow(ax, x + w/2, yb - 0.02, x + w/2, yb - gap + 0.02, lw=1.5, ms=13)  # 向下
        y = yb - gap

def matrix(ax, rows, cols, M, x0=3.4, y0=6.0, cw=1.66, rh=1.0,
           sym={2: '●', 1: '△', 0: '○'}):
    """机理↔特征映射表。rows=机理名, cols=信号名, M=二维强度(2/1/0)。"""
    for j, s in enumerate(cols):
        ax.text(x0 + cw*(j+0.5), y0 + 0.55, s, fontsize=8.4, ha='center', va='center', fontweight='bold')
    for i, m in enumerate(rows):
        yy = y0 - rh*i
        ax.text(x0 - 0.15, yy, m, fontsize=8.8, ha='right', va='center', fontweight='bold')
        for j in range(len(cols)):
            ax.text(x0 + cw*(j+0.5), yy, sym[M[i][j]], fontsize=13, ha='center', va='center')
    for j in range(len(cols)+1):
        ax.plot([x0+cw*j, x0+cw*j], [y0-rh*(len(rows)-1)-0.5, y0+0.25], color='0.7', lw=0.7)
    for i in range(len(rows)+1):
        ax.plot([x0-0.05, x0+cw*len(cols)], [y0+0.25-rh*i, y0+0.25-rh*i], color='0.7', lw=0.7)

def save(fig, path, dpi=180):
    fig.savefig(path, dpi=dpi, bbox_inches='tight', facecolor='white')
    plt.close(fig)


if __name__ == '__main__':
    # 自检：字体 + 框 + 箭头 + 流程图 + 映射表
    name = setup_cjk()
    print('CJK font:', name)
    fig, axs = plt.subplots(1, 2, figsize=(10, 4))
    a = axs[0]; a.set_xlim(0, 10); a.set_ylim(0, 10); a.axis('off')
    flowchart(a, [('S1', '建立模型'), ('S2', '求解分布'), ('S3', '反演剖面 w(x)'), ('S4', '生成程序')],
              top=9.0, bh=1.4)
    a.set_title('流程图自检', fontsize=11.5)
    b = axs[1]; b.set_xlim(0, 12); b.set_ylim(0, 8); b.axis('off')
    box(b, 0.5, 5.5, 3.0, 1.6, '1 模块A', ['说明一行'])
    box(b, 7.0, 5.5, 3.0, 1.6, '2 模块B', ['说明一行'])
    arrow(b, 3.5, 6.3, 7.0, 6.3)
    matrix(b, ['SEI', '析锂', 'LAM'], ['容量', 'DCR', 'dV/dQ'],
           [[2, 1, 2], [2, 1, 1], [2, 0, 2]], x0=1.0, y0=4.0, cw=1.5, rh=0.9)
    b.text(6.0, 0.3, '映射表自检（dV/dQ、$_0$ 等无缺字形）', fontsize=9, ha='center')
    b.set_title('框/箭头/映射表自检', fontsize=11.5)
    save(fig, '_selftest.png')
    print('wrote _selftest.png')

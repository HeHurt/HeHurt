---
mode: ask
description: 对比两个 COMSOL .java 模型,按物理意义解读差异
---

# Task: 对比两个 COMSOL .java 模型

## 用户输入
- v1 文件: ${file:v1File:models/java/}
- v2 文件: ${file:v2File:models/java/}

## 执行步骤

### Step 1: 加载两个文件

请用 `#file:` 把两个文件内容都加载到context。

### Step 2: 生成结构化diff

不需要原始diff,而是**按5类分类**,每类列出v1→v2的具体改动:

#### 1. 参数变化 (`model.param().set`)
| 参数名 | v1值 | v2值 | 单位 | 注释 |
|---|---|---|---|---|

#### 2. 物理场变化
- 新增的 `physics().create(...)` 或 `feature().create(...)` 节点
- 删除的节点
- 修改属性的节点 (列出 `.set(prop, val)` 的属性名 + 新旧值)

#### 3. 几何变化
- `geom(...)` 下新增/修改/删除的 feature
- 选区 (Selection) 的变化

#### 4. Study/Solver 变化
- `study(...)` 下的Step类型变化
- `feature("time").set("tlist", ...)` 时间范围变化
- 新增/删除的Parametric sweep
- Stop Condition 变化
- `sol(...)` 下的求解器配置变化 (如有)

#### 5. 后处理变化
- 新增/修改的 `result().numerical/export/plot`
- 新Table、新Dataset

### Step 3: 物理意义解读

基于以上结构化变化,**推断**改动的工程目的(明确标注"AI推测"):

> "AI推测: 该改动看起来是把 v1 的 X 改为 v2 的 Y,目的可能是为了 Z。
> 例如: '把 Crate 从 1 提高到 3' + '加入 Stop Condition' →
> 推测在做高倍率放电测试,担心低压发散。"

涉及LFP/Gr特有的物理量变化时,引用 `references/liion_lfp_reference.md` 的参数表帮助解读:
- 比如 `Ds_pos` 从 1e-16 → 5e-17 → "LFP固相扩散变慢,可能模拟低温或老化"
- 比如 `V_min` 从 2.5 → 2.0 → "深放电测试,但 LFP 通常 2.5V 已截止,可能在测过放风险"

### Step 4: 给出审阅建议

- v1→v2 的改动看起来**物理自洽**吗? (例: 改了几何但选区未更新 → 不自洽)
- 是否有**潜在风险**? (例: CP工况但未加 Stop Condition)
- 是否需要**对应更新文档**? (例: 加了新参数但 changelog 未提)

## 输出模板示例

```markdown
# v1 vs v2 差异审阅

## 1. 参数变化 (3项)
| 参数 | v1 | v2 | 单位 | 备注 |
|---|---|---|---|---|
| rp_pos | 1e-6 | 5e-7 | m | LFP颗粒半径减半 |
| T_amb | 298.15 | 313.15 | K | +15K (夏季工况?) |
| Crate | 1 | 3 | - | 高倍率 |

## 2. 物理场变化 (1项)
- 新增 Stop Condition: `(E_cell<V_min)||(E_cell>V_max)`

## 3-5. ...

## 物理意义解读 (AI推测)

该改动同时:
- 颗粒细化 (提升倍率性能,需新参数)
- 高倍率 (从1C到3C)
- 高温 (+15K,夏季)
- 加Stop Condition (防止高倍率下电压塌陷)

推测在测试 **高温 + 高倍率工况下的颗粒细化效果**,
为夏季储能项目的快充工况优化做准备。

## 审阅建议
✅ 改动物理自洽 (颗粒细化与高倍率配套合理)
⚠️ 未看到对应的网格细化 — 颗粒r半径减半,固相离散网格是否还够?
   建议检查 mesh 设置;LFP小颗粒对网格密度敏感
⚠️ 未看到 changelog 注释 — 建议按 team_workflow.md 加修改记录块
```

参考 `references/team_workflow.md` "对比两个 .java 找差异"章节。

---
mode: agent
description: 在现有CC Study上加C倍率参数扫描 + 自动CSV导出
---

# Task: C倍率扫描

为当前 .java 加一组C倍率扫描 + 关键指标CSV导出。

## 用户输入
- C倍率列表 (无量纲): ${input:crateList:0.2 0.5 1 2 3}
- 1C参考电流 (A,通常为电芯容量数值): ${input:I1C:280}
- 关键输出指标: ${input:metrics:min(liion.E_cell), max(T), max(T)-min(T)}
- 导出CSV路径: ${input:csvPath:D:\\sweep_out\\crate_results.csv}

## 执行步骤

### Step 2: grep 心智地图
- `model.param().set` → 确认 `Crate` / `I_1C` / `I_app` 是否已定义
- `model.study(.*).create` → 当前的Study tag
- `feature("param")` → 是否已有扫描 (决定 .create 还是直接 .set)
- `result().numerical` → 后处理命名风格

### Step 3: 计划修改

1. **改什么**: 仅Study层加扫描 + Results加导出,不动物理场
2. **保留什么**: 所有物理场、几何、网格、参数定义
3. **新增什么**:
   - param: `Crate` (如未定义)
   - study.param: 扫 `Crate`
   - result.table: tblN (扫描结果表)
   - result.numerical: gevN (全局评估)
   - result.export: tblexpN (CSV导出)
4. **副作用**: 求解时间 × 扫描点数

### Step 4: 生成代码片段

**片段A**: 确认参数定义 (如未定义)

```java
// 仅当 grep 未找到 Crate/I_app 时加
model.param().set("I_1C", "{I1C}[A]", "1C reference current");
model.param().set("Crate", "1", "C-rate (dimensionless)");
model.param().set("I_app", "Crate*I_1C", "Applied current");
```

**片段B**: 在 Study 加扫描

```java
// 如 grep 未找到 feature("param")
model.study("std1").create("param", "Parametric");

// 总是设置 (即使feature已存在)
model.study("std1").feature("param").set("pname",    new String[]{"Crate"});
model.study("std1").feature("param").set("plistarr", new String[]{"{crateList}"});
model.study("std1").feature("param").set("punit",    new String[]{""});
```

**片段C**: 加后处理 + CSV导出

```java
// Table容器
model.result().table().create("tbl_crate", "Table");

// Global Evaluation (每个扫描点产出一行)
model.result().numerical().create("gev_crate", "EvalGlobal");
model.result().numerical("gev_crate").set("data", "dset2");  // ⚠️ 用扫描产生的Dataset,通常是dset2
model.result().numerical("gev_crate").set("expr", new String[]{
  "{metrics_split_by_comma}"
});
model.result().numerical("gev_crate").set("descr", new String[]{
  "min cell voltage", "max temperature", "max delta T"
});
model.result().numerical("gev_crate").set("table", "tbl_crate");
model.result().numerical("gev_crate").setResult();

// CSV导出
model.result().export().create("tblexp_crate", "Table");
model.result().export("tblexp_crate").set("table", "tbl_crate");
model.result().export("tblexp_crate").set("filename", "{csvPath}");
model.result().export("tblexp_crate").set("header", true);
model.result().export("tblexp_crate").run();
```

⚠️ **重要风险点**: `data` 属性必须是扫描产生的 Dataset (通常是 `dset2`,而非原始 `dset1`)。grep `result().dataset().create` 找扫描产生的Dataset的实际tag,**不要假设是 dset2**。

### Step 5: 提示用户

- 在COMSOL Desktop里编译并跑Study,确认CSV正确导出
- 用 Python/MATLAB 读CSV做后处理: 
  ```python
  import pandas as pd
  df = pd.read_csv('{csvPath}', encoding='gbk')  # Windows默认GBK
  df.plot(x='Crate', y='min cell voltage (V)')
  ```

参考 `references/parameter_sweep_patterns.md` "模式1: 单参数 CC扫描" 和 "后处理: 扫描结果导出CSV"。

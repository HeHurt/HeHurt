---
mode: agent
description: 在现有CC模型上加CP恒功率工况 + 功率扫描 (Hithium储能场景)
---

# Task: 加CP恒功率工况

请按 `.github/instructions/comsol.instructions.md` 的5步工作流,在当前打开的 .java 文件上加CP工况。

## 用户输入
- 功率列表 (W): ${input:powerList:280 560 1120}
- 截止上限电压 (V): ${input:vMax:3.65}
- 截止下限电压 (V): ${input:vMin:2.5}

## 执行步骤

### Step 1: 不需要 (用户已导出.java)

### Step 2: 建立心智地图
- grep `ecs1` 或 `ElectrodeCurrent` 确认当前的电流边界条件配置
- grep `ge` / `GlobalEquations` 确认是否已有CP配置 (避免重复创建)
- grep `usestopcond` 确认是否已有Stop Condition
- grep `model.param().set` 确认是否已有 `P_app`/`V_max`/`V_min` 参数

### Step 3: 计划修改
列出4清单给用户确认:
1. **改什么**: `ecs1.I_el` 从常数 `I_app` → Global未知量 `I_app_var`
2. **保留什么**: 所有几何/材料/网格/初始条件不变
3. **新增什么**:
   - param: `P_app`, `V_max`, `V_min` (如未定义)
   - physics: `ge` (GlobalEquations) + `ge1` feature
   - study: time step 加 stopcond
   - study: 加 parametric sweep 扫 `P_app`
4. **副作用**: CC模式失效 (除非保留原 `I_app` 参数,只改 ecs1 引用)

### Step 4: 生成3段代码片段

每段都必须有 4段header (插入位置/新建tags/依赖项/风险点) + ```java代码``` + 粘贴说明。

**片段A**: 在 `model.param()` 段加参数 (如未定义)
```java
model.param().set("P_app", "560[W]", "Applied power for CP mode");
model.param().set("V_max", "{vMax}[V]", "Cutoff voltage high (LFP)");
model.param().set("V_min", "{vMin}[V]", "Cutoff voltage low (LFP)");
```

**片段B**: 在 physics段后加 Global Equations 节点
参考 `references/liion_lfp_reference.md` "恒功率(CP)实现" 章节模板。

**片段C**: 修改 ecs1.I_el 引用 + 加Stop Condition + 加扫描
```java
// 修改电流边界条件
model.component("comp1").physics("liion").feature("ecs1").set("I_el", "I_app_var");

// 加 Stop Condition (防止低压发散)
model.study("std1").feature("time").set("usestopcond", true);
model.study("std1").feature("time").set("stopcond",
  "(comp1.liion.E_cell<V_min)||(comp1.liion.E_cell>V_max)");
model.study("std1").feature("time").set("stopcondterminateon", "anytrue");

// 加扫描
model.study("std1").create("param", "Parametric");  // 或直接 .feature("param").set 如已存在
model.study("std1").feature("param").set("pname",    new String[]{"P_app"});
model.study("std1").feature("param").set("plistarr", new String[]{"{powerList}"});
model.study("std1").feature("param").set("punit",    new String[]{"W"});
```

### Step 5: 提示用户

- 建议先单点测试 (P_app=560W,1P),确认收敛
- 再开扫描
- 用 `comsolcompile` 检查Java语法
- 在COMSOL Desktop里 `File → Compile Java File` 编译为 .mph
- 跑 std1,检查 I_app_var 的时变曲线: 平台期接近常数,接近 V_min 时电流上升

## 不要做

❌ 用 `ElectromagneticHeating` 做热耦合 (如果模型还要加热场)
❌ 跳过 Stop Condition (CP不加Stop Condition会发散)
❌ 把 `P_app` 写成 `P_app*1[W]` (单位已在param里)
❌ 在Step 4之前直接生成代码 (必须Step 2-3完成,用户确认计划)

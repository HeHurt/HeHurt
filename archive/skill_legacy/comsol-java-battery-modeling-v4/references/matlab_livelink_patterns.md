# MATLAB LiveLink 驱动COMSOL — 参数扫描模式

本文档面向使用**MATLAB LiveLink for COMSOL**驱动电池模型扫描的场景。LiveLink让MATLAB可以直接读写COMSOL模型，**不需要重新编译.java**，适合：

- 外层循环复杂（条件分支、收敛判断、动态调整参数）
- 与现有MATLAB后处理脚本无缝衔接
- 反复试错调试 — Java编译慢，MATLAB热重载快
- 与机器学习/优化工具链结合（如`fmincon`/`bayesopt`/`ga`驱动COMSOL参数优化）

**和.java粘贴路径的本质区别**：LiveLink里你不修改`.mph`文件本身，每次MATLAB运行时在内存里加载、修改、求解。要持久化改动需手动`mphsave`。

## 启动LiveLink会话

```matlab
% 方式1: 通过COMSOL Multiphysics Server启动
% 命令行先开服务器: comsolmphserver
% MATLAB中连接
import com.comsol.model.*
import com.comsol.model.util.*
mphstart  % 默认localhost:2036
% 或 mphstart(2036) 指定端口

% 方式2: 直接从MATLAB启动COMSOL with MATLAB
% (从开始菜单选 "COMSOL Multiphysics 6.4 with MATLAB",会自动开服务器+MATLAB)
```

## 加载模型 + 基本操作

```matlab
% 加载.mph
model = mphload('D:\models\battery_p2d_thermal.mph');

% 查看所有参数
mphgetexpressions(model.param)

% 读取/修改单个参数
val = model.param.get('I_app');           % 读
model.param.set('I_app', '280[A]');       % 写 (字符串,带单位)
model.param.set('Crate', '1.5');          % 无单位

% 查看所有study
mphtags(model.study)                       % 返回 {'std1'} 等

% 运行study
model.study('std1').run();

% 取结果(端电压随时间)
data = mpheval(model, 'liion.E_cell', 'edim', 'point', 'selection', 1);
%   返回结构体, data.p=时间, data.d1=电压

% 保存修改后的mph (如需要持久化)
mphsave(model, 'battery_modified.mph');
```

## LFP/Gr参数扫描 — 标准循环模式

### 模式①: 单参数扫描 (C倍率)

```matlab
% === 配置 ===
C_rates = [0.2 0.5 1 2 3];     % 5个C倍率
I_1C = 280;                     % A

% === 加载模型 ===
model = mphload('battery_p2d_thermal.mph');

% === 准备结果容器 ===
results = struct();

% === 循环 ===
for k = 1:length(C_rates)
    fprintf('Running Crate = %.2f ...\n', C_rates(k));
    
    % 设参数
    model.param.set('Crate', sprintf('%.4f', C_rates(k)));
    model.param.set('I_app', sprintf('%.4f[A]', C_rates(k)*I_1C));
    
    % 求解
    tic;
    model.study('std1').run();
    elapsed = toc;
    fprintf('  Solved in %.1fs\n', elapsed);
    
    % 提取结果
    Ecell = mpheval(model, 'liion.E_cell', 'edim','point', 'selection',1);
    Tmax  = mpheval(model, 'maxop1(T)',    'edim','point', 'selection',1);
    
    % 存储
    results(k).Crate = C_rates(k);
    results(k).t     = Ecell.p(1,:)';
    results(k).Ecell = Ecell.d1';
    results(k).Tmax  = Tmax.d1';
    
    % (可选) 中间保存,防止崩溃丢数据
    save('sweep_results.mat', 'results');
end

fprintf('Done. Saved %d cases.\n', length(results));
```

### 模式②: CP扫描 (储能场景)

```matlab
% 扫描功率 (假设源.mph已配置好CP的Global Equation)
P_targets = [140, 280, 560, 840, 1120];  % W

model = mphload('battery_p2d_cp.mph');

results_cp = struct();
for k = 1:length(P_targets)
    model.param.set('P_app', sprintf('%.2f[W]', P_targets(k)));
    
    try
        model.study('std1').run();
        
        % 提取CP核心指标
        Ecell = mpheval(model, 'liion.E_cell', 'edim','point','selection',1);
        Iapp  = mpheval(model, 'I_app_var',    'edim','point','selection',1);
        % I_app_var 是CP模式下Global Equation的未知量
        
        results_cp(k).P_app = P_targets(k);
        results_cp(k).t     = Ecell.p(1,:)';
        results_cp(k).Ecell = Ecell.d1';
        results_cp(k).Iapp  = Iapp.d1';
        results_cp(k).converged = true;
        
    catch ME
        warning('Case P=%dW failed: %s', P_targets(k), ME.message);
        results_cp(k).P_app = P_targets(k);
        results_cp(k).converged = false;
    end
end
```

### 模式③: 二维网格 (CP × 温度)

```matlab
P_list = [280, 560, 1120];
T_list = [263.15, 298.15, 318.15];

[P_grid, T_grid] = ndgrid(P_list, T_list);
n_cases = numel(P_grid);

model = mphload('battery_p2d_cp.mph');

% 用struct array,索引对应到P_grid/T_grid
results_2d(n_cases) = struct('P',[],'T',[],'discharge_time',[]);

for k = 1:n_cases
    model.param.set('P_app', sprintf('%.2f[W]', P_grid(k)));
    model.param.set('T_amb', sprintf('%.2f[K]', T_grid(k)));
    
    try
        model.study('std1').run();
        Ecell = mpheval(model, 'liion.E_cell', 'edim','point','selection',1);
        
        % 计算放电截止时间
        idx_cutoff = find(Ecell.d1' < 2.5, 1);
        if isempty(idx_cutoff)
            t_cutoff = Ecell.p(1,end);
        else
            t_cutoff = Ecell.p(1, idx_cutoff);
        end
        
        results_2d(k).P = P_grid(k);
        results_2d(k).T = T_grid(k);
        results_2d(k).discharge_time = t_cutoff;
        results_2d(k).Ecell = Ecell.d1';
        results_2d(k).t     = Ecell.p(1,:)';
    catch ME
        warning('Case (P=%dW, T=%dK) failed: %s', P_grid(k), T_grid(k), ME.message);
    end
end

% 重整成二维矩阵便于绘图
discharge_time_matrix = reshape([results_2d.discharge_time], size(P_grid));
contourf(P_list, T_list-273.15, discharge_time_matrix'/60);
xlabel('Power (W)'); ylabel('Temperature (°C)'); colorbar;
title('Discharge time (min) on P-T plane');
```

### 模式④: 与优化器结合 (反演极片厚度)

让`fmincon`找出使容量最大的极片厚度组合（在固定厚度预算下）：

```matlab
model = mphload('battery_p2d_thermal.mph');

% 目标函数: 给定(L_neg, L_pos),求负的1C容量(因为fmincon最小化)
function neg_capacity = obj(x, model)
    L_neg = x(1);
    L_pos = x(2);
    
    model.param.set('L_neg', sprintf('%g[m]', L_neg));
    model.param.set('L_pos', sprintf('%g[m]', L_pos));
    
    try
        model.study('std1').run();
        % 容量 = 电流 × 放电截止时间
        Ecell = mpheval(model,'liion.E_cell','edim','point','selection',1);
        idx = find(Ecell.d1' < 2.5, 1);
        if isempty(idx), t_end = Ecell.p(1,end); else, t_end = Ecell.p(1,idx); end
        I_val = str2double(regexprep(char(model.param.get('I_app')), '\[A\]', ''));
        neg_capacity = -I_val * t_end / 3600;  % Ah,取负
    catch
        neg_capacity = 0;  % 失败case
    end
end

% 优化: L_neg in [60µm, 120µm], L_pos in [60µm, 120µm], 总厚度<=200µm
x0 = [80e-6, 90e-6];
lb = [60e-6, 60e-6];
ub = [120e-6, 120e-6];
A = [1 1]; b = 200e-6;   % L_neg + L_pos <= 200µm

x_opt = fmincon(@(x) obj(x, model), x0, A, b, [], [], lb, ub);
fprintf('Optimal: L_neg=%.1fµm, L_pos=%.1fµm\n', x_opt(1)*1e6, x_opt(2)*1e6);
```

---

## LiveLink vs .java 选哪个

| 场景 | 推荐 |
|---|---|
| 一次性扫描，结果持久化到`.mph`供其他人用 | `.java`粘贴 |
| 反复调试，参数频繁改 | LiveLink |
| 外层有复杂逻辑（条件分支、收敛判断、优化算法） | LiveLink |
| 团队协作，标准化跑库 | `.java`粘贴（版本控制友好） |
| 与MATLAB/Python后处理深度集成 | LiveLink |
| 集群批量(`comsolbatch`) | `.java`粘贴 + `.mph`提交 |
| 单机交互式探索 | LiveLink |

---

## LiveLink常见坑

| 现象 | 原因 | 修正 |
|---|---|---|
| `Undefined function 'mphload'` | LiveLink路径没加 | MATLAB启动时用"COMSOL with MATLAB"快捷方式,或手动`addpath(comsolroot)` |
| 设参数报"unit mismatch" | 数值没带单位字符串 | `set('I_app','280[A]')` 而不是 `set('I_app',280)` |
| `mphload`失败 — 找不到文件 | 相对路径 | 用绝对路径 |
| 大量循环MATLAB内存涨 | 求解结果累积 | 每次循环后 `model.sol('sol1').clearSolutionData;` 或定期`mphsave`+`mphload`重置 |
| 服务器连接断开 | LiveLink进程崩溃 | 重启comsolmphserver,加try-catch自动重连 |
| 跨组件引用失败 | 多组件模型语法差异 | 用`comp1.liion.E_cell`而不是`liion.E_cell` |

---

## 与本Skill的Java片段路径如何配合

LiveLink和Java片段**不是二选一**，可以组合：

1. **首次建模**：用`.java`片段粘贴 → 编译出干净的`.mph`基线
2. **日常扫描**：LiveLink加载基线`.mph`，循环跑各种参数组合
3. **新增物理场/边界条件**（结构性改动）：回到`.java`片段路径
4. **持久化设置**（如调好的求解器容差）：LiveLink里改完用`mphsave`保存

这种"Java管结构、LiveLink管参数"的分工，是Hithium这类既有团队规范又有探索性研究的场景最实用的组合。

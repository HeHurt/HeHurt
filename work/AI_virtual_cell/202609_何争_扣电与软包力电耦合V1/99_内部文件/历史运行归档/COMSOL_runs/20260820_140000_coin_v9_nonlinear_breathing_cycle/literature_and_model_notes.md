# V9 非线性嵌锂呼吸模型说明

## 文献依据与数据尺度

1. 石墨负极采用 Rieger 等人的电化学膨胀测量曲线形状。该曲线随 `Li_xC6` 嵌锂比例呈明显 staging 非线性，在 `LiC12 → LiC6` 区域斜率再次增大。公开图中全嵌锂电极厚度变化约 7%，论文同时报告商业电芯工作窗口内石墨电极厚度变化约 5.2%。本模型把图形近似数字化为内嵌插值表，并设置 `eps_sw_neg_lit=0.07`。
2. LFP 正极依据 Zhang 等人的复合电极原位应变研究：Li+ 嵌入 FePO4 时复合电极首圈应变约 0.60%，应变导数在相变区出现单峰。模型据此采用 S 形归一化函数和 `eps_sw_pos_lit=0.006`。充电时 LFP 脱锂，因此本征应变为负值（收缩）；放电嵌锂时恢复膨胀。
3. 两条关系均为“典型、文献约束的代表曲线”，不是作者原始数据文件。石墨曲线是公开图近似数字化；LFP 曲线用论文报告的幅值与相变区单峰特征构造。幅值和曲线形状在模型中分开参数化，便于后续用本项目实测膨胀数据替换。

## 模型表达式

石墨：

`eps_breath_neg_lit_v9 = eps_sw_neg_lit*(sw_gr_v9(theta_neg_v8)-sw_gr_v9(theta_neg_ref))`

LFP：

`eps_breath_pos_lit_v9 = eps_sw_pos_lit*(sw_lfp_v9(theta_pos_v8)-sw_lfp_v9(theta_pos_ref))`

模式开关：

- `breathing_mode=0`：关闭材料呼吸；
- `breathing_mode=1`：保留 V8 旧线性探索式（石墨 20%、LFP 1%）；
- `breathing_mode=2`：文献非线性关系，推荐。

局部反馈链保持为：

`SOC/嵌锂比例 → External Strain → solid.sz → p_comp → epsl → 电解液传输与电化学响应`

## 完整循环协议

- 外力：100 N；
- 倍率：0.5C；
- 初始 SOC：0.01；
- 充电截止：加载端电压 3.65 V；
- 静置：600 s；
- 放电截止：加载端电压 2.50 V；
- 计算总时间：18,000 s；放电截止后保持零电流。

V8 的 Events 节点仍绑定到旧 `std1/time`，导致 `std_breath` 到达上截止后只归零、未继续放电。V9 将 `ds1/is1/impl2/impl3/impl5/impl6` 全部重新绑定到 `std_v9/time`，并禁用放电后再次启动充电，从而得到单个完整充放电循环。

## 参考文献

- B. Rieger et al., *Multi-scale investigation of thickness changes in a commercial pouch type lithium-ion battery*, Journal of Energy Storage 6 (2016) 213–221. DOI: 10.1016/j.est.2016.01.006.
- Y. Zhang et al., *Electrochemical strain evolution in iron phosphate composite cathodes during lithium and sodium ion intercalation*, Electrochimica Acta 353 (2020) 136594. DOI: 10.1016/j.electacta.2020.136594.
- H. Liu et al., *Irreversible phase transition between LiFePO4 and FePO4 during high-rate charge-discharge reaction by operando X-ray diffraction*, Journal of Power Sources 309 (2016) 122–126. DOI: 10.1016/j.jpowsour.2016.01.077.

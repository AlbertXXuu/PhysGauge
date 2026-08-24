# R2 实验协议：learned-dynamics validation

协议 ID：`physgauge-learned-dynamics-r2-v1`

状态：**已冻结，尚未训练。** 本文件在模型实现和结果产生前固定。观察结果后若改变数据、
模型、阈值或决策门，必须升级协议 ID、说明偏离原因并保留原结果，不能静默覆盖。

## 0. 研究问题与边界

研究问题：在解析双圆盘世界中，一个确实经过训练的 dynamics predictor 是否会产生
PhysGauge 状态检查能发现、但某个视觉指标相对不敏感的误差？

- 只训练直接预测状态的模型，不接视频生成器或视觉跟踪器。
- 因此本实验隔离的是模型学习与自回归误差，不混入检测、身份保持、遮挡恢复、速度估计或
  坐标标定误差。
- 所有数据来自当前 `make_case` 分布。这是**同分布未见配置（IID holdout）**，不是 OOD
  泛化实验，也不能外推到真实视频或其他物理系统。
- R2 验证的是 learned-model 用例，不重新定义已经发布的 Software v1。

## 1. 冻结数据清单

配置以 `(base_seed, case_index)` 唯一标识；同一配置的所有相邻状态只属于一个 split。

| split | `base_seed` | `case_index` | 配置数 | 用途 |
|---|---:|---:|---:|---|
| train | `20260825` | `0..1023` | 1024 | 参数拟合与归一化统计 |
| validation | `20260826` | `0..127` | 128 | 早停与 checkpoint 选择 |
| test | `20260827` | `0..255` | 256 | 一次性最终评估 |

实现必须在训练前生成 `split-manifest.json`，逐项记录 split、base seed、case index、完整
`WorldConfig` 和清单 SHA-256。三个 split 的标识必须互斥；归一化统计只能来自 train。

每个轨迹产生 `(s_t, s_{t+1})` 相邻状态对。为避免约 1 个碰撞转换被大量自由运动样本淹没，
训练与验证目标固定为：首次接触转换前后各 2 步构成 collision window，其余为 free-motion；
两组 loss 各占 50%。test 仍按完整自然轨迹评估，不重加权。

## 2. 冻结模型与训练配置

状态顺序沿用 v1：

```text
[p1_x, p1_y, v1_x, v1_y, p2_x, p2_y, v2_x, v2_y]
```

- 输入：`[s_t, radius]`，共 9 维。半径决定接触距离，不能从单帧八维状态唯一推出。
  `dt=0.001`、世界边界与质量在本协议中固定，因此不作为可变输入。
- 输出：八维增量 `Δs_t`，下一状态为 `s_t + Δs_t`。
- 归一化：对输入和目标增量分别使用 train split 的逐维均值/标准差；标准差为零时用 1。
- 模型：`Linear(9,128) → SiLU → Linear(128,128) → SiLU → Linear(128,8)`，float32。
- loss：标准化增量的 MSE，collision-window 与 free-motion 各占 50%。
- 优化器：AdamW，learning rate `1e-3`，weight decay `1e-5`，batch size `256`。
- 训练：最多 200 epochs；validation 加权 loss 连续 20 epochs 没有至少 `1e-6` 的改善则
  早停，并恢复最低 validation loss 的 checkpoint。
- 模型随机种子：`11`、`29`、`47`。每个种子控制初始化与 batch 顺序；启用框架可用的
  deterministic 模式并记录框架、依赖、CPU/GPU 与运行时间。
- 不做架构或超参数搜索。只有确认实现错误时允许修复后重跑，并在结果中保留错误及修复记录。

## 3. 自回归评估合同

模型从每个 test 配置的精确 `s_0` 开始，连续预测到 `cfg.n_steps`：

1. 每一步只读取自己的上一预测和该配置的 radius；
2. 不使用 teacher forcing，不读取未来 oracle 状态；
3. 不裁剪位置、速度，不注入解析碰撞或其他物理后处理；
4. 非有限输出直接判为该 seed 的无效运行，不能删掉失败 case；
5. 使用同一 `WorldConfig` 把完整预测与 oracle 各渲染 48 帧，再调用
   `evaluate_trajectory`。

统计单位是**配置**，不是帧。每个训练种子分别报告 256 个配置的结果，再报告三种子的
均值与标准差；比例同时给出以配置为单位的 95% Wilson 区间。

## 4. 三个固定基线

三个基线在相同 256 个 test 配置上完整 rollout：

1. `persistence`：位置和记录速度都保持上一状态不变，`s_{t+1}=s_t`。这不是“把速度设零”。
2. `linear-extrapolation`：分别执行
   `p1_{t+1}=p1_t+v1_t·dt`、`p2_{t+1}=p2_t+v2_t·dt`，速度保持不变；不处理碰撞。
3. `analytic-oracle`：当前 `step`/`simulate` 解析实现，用于验证评估链路上界，不参与训练。

每个 case 的视觉 low-sensitivity 分母使用与 v1 相同分布的确定性 random trajectory：随机
种子为 `20260827 + case_index * 1009 + 9`，位置在合法边界内均匀采样，四个速度分量在
`[-1,1]` 均匀采样。实现必须用独立 RNG，不得消费训练 RNG 状态。

## 5. 预定义判定

### 5.1 状态抓住

同一 test case 上，以下任一条件成立即为 `state_failure=True`：

| metric | 阈值 | 来源/理由 |
|---|---:|---|
| `position_rmse` | `> 0.05` | v1 state-error 阈值 |
| `velocity_rmse` | `> 0.05` | R2 预注册工程容差，不宣称继承自 v1 |
| `energy_drift` | `> 1e-4` | v1 energy 阈值 |
| `momentum_drift` | `> 1e-4` | v1 momentum 阈值 |
| `collision_event_error` | `> 0.5` | v1 二元碰撞事件阈值 |
| `kinematic_residual` | `> 0.05` | 256 个冻结 test oracle 的最大值约 `0.0454` |

`initial_condition_error` 必须不超过 `1e-6`，否则违反“从精确初态 rollout”的实现合同，
该运行无效而不是 learned-model 结果。所有连续指标仍完整报告，不能只报告触发项。

### 5.2 视觉放过与分歧

对每个视觉指标 `m ∈ {mse, ssim_error, pixel_frechet, temporal_gradient_mse}` 单独计算：

```text
ratio_m = learned_metric_m / max(random_metric_m, 1e-12)
visual_low_sensitivity_m = ratio_m < 0.25
disagreement_m = state_failure and visual_low_sensitivity_m
```

四个指标必须逐项报告，不能用“任一指标”合并后挑选最好看的结果。另行报告
`metric_m <= 1e-10` 的 exact miss，但决策门使用上面的 low-sensitivity 定义。

## 6. 有效性与决策门

先依次执行，前一门未通过时不得解释后一门：

1. **实验有效性**：split 清单互斥且哈希可复核；analytic-oracle 全部通过；无数据泄漏、
   非有限输出或初态违约；实现测试与结果包校验通过。失败则修实现，不解释研究结果。
2. **模型充分性**：至少 2/3 个训练种子的 test median `position_rmse` **和** median
   `velocity_rmse` 都低于 linear-extrapolation。否则标记 R2 `inconclusive-model`；只允许一次
   有记录的实现审计/修复，不把“模型没学会”当成 PhysGauge 的正面证据。
3. **continue → R3**：模型充分，且同一个预先列出的视觉指标在至少 2/3 个训练种子上有
   `disagreement_rate >= 5%`（256 cases 中至少 13 个）。这只是进入 R3 论文决策的工程门，
   不是统计显著性或论文结论。
4. **expand**：未达到 continue，但至少 2/3 个种子同时满足 test P95
   `position_rmse <= 0.01`、P95 `velocity_rmse <= 0.05`、碰撞事件正确率 `>=99%`。此时记录
   “当前世界对该模型过易”，再由 R3 决定是否扩展；不得自动开新场景。
5. **stop-current-line**：模型充分但既不满足 continue 也不满足 expand。诚实记录“本次
   learned predictor 未观察到预注册分歧”，停止对这一模型追加调参；这不证明工具普遍无效。

采用信号与市场需求是独立维度，不作为 R2 实验结果的替代或否决条件。

## 7. 必需产物与验收

R2 实现阶段只新增当前结果必需的文件：

- 可复现的数据/训练/评估入口与自动化测试；
- `split-manifest.json`、完整冻结配置、三个模型种子的 checkpoint 哈希；
- 每 case 的状态与视觉指标、三基线、聚合表和决策门结果；
- `docs/evidence/r2/` 下带 SHA-256 manifest 的机器可读结果与简洁报告。

R2.0 的完成标准是本协议在训练前精确定义上述内容。R2.1/R2.2 只有在代码、三种子结果、
证据包复核与决策门全部完成后才能勾选；README、ROADMAP 或论文叙事不能替代实验结果。

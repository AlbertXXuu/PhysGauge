# PhysGauge 路线图 · 里程碑 · 验收（修订版 2026-08-24）

> 本文件是研究计划与进度来源。事实来源仍是 protocol、evidence、测试和 Release；本文件只负责计划与进度追踪，不是证据。
> 软件版本、研究成熟度、市场影响力是三件不同的事，分开记。

---

## 0. 里程碑定义

| 里程碑 | 定义 | 状态 |
|---|---|---|
| **Software v1** | 校准工具软件发布：24 cases、severity sweep、hash 验证 evidence、CLI/稳定 API、测试全绿 | ✅ **完成** |
| **R1** | theoretical clarification：精确表述"逐帧排列不变距离"的能力边界 | ✅ **完成** |
| **R2.0** | 在训练前精确定义并冻结 learned-model 实验协议 | ✅ **完成** |
| **R2.1–R2.2** | learned-model implementation + validation | ⬜ 未开始 |
| **R3** | paper decision gate：据 R2 结果决定写论文 / 扩展场景 / 停止 | ⬜ 未开始 |
| 采用信号 | 记录真实使用与非作者反馈，不把单条反馈等同于市场需求 | ⬜ 尚无信号 |

不再使用"真正的 v1""完成论文才是真 v1"等说法。软件 v1 已经完成，研究里程碑 R1–R3 是
独立的下一步，两者不互相否定。

---

## 1. R1 — theoretical clarification（最高优先）

### 1.1 正名：这不是物理时间反演

- `time-reverse` 是历史候选 ID，已进入公开证据与 schema，**保留为 legacy ID，不改名**；
  文档与代码注释解释其真实含义（frame-order reversal）。
- 当前 `time-reverse` 实现是 `simulate(cfg)[::-1]`（只把状态序列倒序）。
- 真正的物理时间反演要求 **位置倒序 + 速度取反**：`q'(t)=q(T-t), v'(t)=-v(T-t)`。
- 当前实现**保留了原速度**，导致位置差分方向与记录的速度字段矛盾——`kinematic_residual`
  检测的正是这个不一致。
- **结论**：它不是"合法牛顿解"，也不是"只错在初始条件和因果"。它是对抗性测试里的
  **frame-order reversal / trajectory-order reversal corruption**（因果顺序反例）。
  价值不变，但不得描述成合法时间反演轨迹。

### 1.2 命题强度：permutation-invariance 的直接推论，不是新定理

严谨陈述（限定条件）：

> 任何建立在**逐帧独立特征的经验分布**上、且**对帧排列不变**的距离，都无法区分一个序列
> 与其任意排列（包括完整倒序）。

- 这属于 permutation invariance 的直接结果，定位为**工具的能力边界陈述**，不宣称是
  "论文级新发现"或"定理"。
- 不笼统声称"所有 FID/MMD/FVD 都无法检测时间反转"，边界如下：

| 指标类别 | 是否受此限制 |
|---|---|
| 逐帧 FID、当前 `pixel_frechet`（逐帧独立特征） | 是，不含顺序 |
| 使用时序视频特征的 Fréchet 距离 | 否，可能含顺序 |
| FVD | 不能简单归入"必然失明" |
| MMD | 理论分布距离为零，但不同有限样本估计式需区分 |

### 1.3 措辞修正：identical-by-construction，不是"逐位零"

- 实测：24 cases 中 `pixel_frechet` 13 个为浮点 `0.0`，最大约 `5.76e-15`，全部低于
  `1e-10` 验收阈值。
- 正确表述：

  > The underlying empirical feature distributions are identical by construction;
  > computed distances range from 0 to \(5.76\times10^{-15}\), below the
  > \(10^{-10}\) exact-miss tolerance.

- **不原地修改** `docs/evidence/v1.0.0/report.md`（其哈希已写入 manifest，改动会破坏已发布证据）；改为新增 `docs/ERRATA.md` 说明，并更新 `report.py` 中未来报告的措辞。

### 1.4 R1 验收指标（全部勾掉才算完成）

- [x] 新增 `docs/ERRATA.md`，不改动 `docs/evidence/v1.0.0/` 下任何文件。
- [x] 保留 `time-reverse` 机器 ID；代码注释与未来报告措辞改用 frame-order reversal。
- [x] `report.py` 的 `_markdown` 从运行结果动态计算数值范围与 exact-miss tolerance。
- [x] `protocol.md` 与中英文 README 链接 ERRATA。
- [x] 全部单元测试全绿；`verify_bundle` 对 v1.0.0 原哈希仍通过。

---

## 2. R2 — learned-model validation

**R2.0 已完成：实验协议（`docs/r2-protocol.md`）已在训练前冻结。** 它精确定义了数据清单、
无泄漏规则、模型接口、自回归 rollout、三个训练种子、三种基线、逐指标分歧判定与
continue / expand / stop 决策门。后续实现若改变这些定义，必须先记录协议修订，不能根据
观察到的结果倒推阈值。

### 2.1 第一步不是视频模型，是小型 learned dynamics predictor

- 用**同一个两球世界**训练一个小型 learned dynamics predictor，以状态与圆盘半径为输入，
  直接预测八维状态增量；步长在本协议固定，评估时从真实初始状态进行自回归 rollout。
- **为什么先做这个**：视频模型只输出像素，所谓 adapter 实际包含圆盘检测、身份保持、
  遮挡处理、位置跟踪、速度估计、坐标与时间标定——会把视觉跟踪误差和模型误差混在一起。
  先做直接输出状态的模型，隔离"模型学习误差"这**单一变量**，验证 PhysGauge 能否发现
  **真实学习误差**（而非注入的合成误差）。
- 通过之后，再评估是否值得接纯视频世界模型（此时才需要处理跟踪误差的分离问题）。

### 2.2 R2 验收指标

- [ ] 训练脚本 + 模型落地，输出八维状态，可被 `evaluate_trajectory` 直接消费。
- [ ] 在 PhysGauge 上跑出该 learned model 的视觉指标 vs 状态指标对比。
- [ ] 明确回答：PhysGauge 是否发现了"真实学习误差"（不是注入误差）。
- [ ] 记录本次实验**未混入**视觉跟踪误差（因为模型直接输出状态）。

---

## 3. R3 — paper decision gate

- **根据 R2 结果三选一**，不预设"必须写论文"：
  1. **写论文**：若 learned model 出现有意义的"视觉放过 + 物理抓住"分歧。
  2. **扩展场景**：若本世界太简单、learned model 全对，换更难物理（遮挡/多体/长时序）。
  3. **停止**：若 PhysGauge 作为工具本身没有被使用的需求（结合外部验证信号）。
- [ ] 明确记录决策 + 理由（一页内）。

---

## 4. 采用信号（可选穿插，不阻塞 R1–R2）

- 一条反馈不能证明市场需求，只作为**采用信号**。
- 发布渠道不设为硬性验收（HN 或 Reddit 择一即可）。
- [ ] 记录非作者反馈（有则记，无则不阻塞）。

---

## 5. 负面清单（修订）

- ❌ **继续增加没有当前需求的治理层**。注意：已有的 `CITATION.cff`、`SECURITY.md`、
  双语 README、CI、Dependabot 是公开软件的**正常卫生**，成本低，**保留**，不删除。
- ❌ 提前扩展物理场景（除非 R2 触发"扩展场景"分支）。
- ❌ 开新方向 / 再列方向地图。
- ❌ 把 R1 的 permutation-invariance 推论包装成"新定理 / 论文核心发现"。

---

## 6. 速查表 + 进度 checklist

| 编号 | 任务 | 一句话验收 | 状态 |
|---|---|---|---|
| R1.1 | 勘误 | 新增 docs/ERRATA.md + 保留 time-reverse ID | ✅ |
| R1.2 | 命题 | 写清 permutation-invariance 能力边界（1.2 表格） | ✅ |
| R1.3 | 措辞 | report.py 动态输出 identical-by-construction 数值范围 | ✅ |
| R2.0 | 协议 | 冻结 R2 实验协议（docs/r2-protocol.md） | ✅ |
| R2.1 | 训练 | learned dynamics predictor 输出八维状态 | ⬜ |
| R2.2 | 验证 | PhysGauge 发现真实学习误差（或诚实记录未发现） | ⬜ |
| R3 | 决策 | 写论文/扩展/停止 三选一 + 理由 | ⬜ |
| 采用 | 信号 | 非作者反馈（有则记，不硬性） | ⬜ |

**闭环完成标准**：R1 全部 + R2.0 协议冻结 + R2.2 落地 = 研究验证闭环闭合。R3 落地 = 有了明确的
下一步决策。三者都不是"更漂亮的 repo"，而是可证伪的里程碑。

---

*更新规则：每完成一项，勾掉对应 checkbox、把速查表状态改成 ✅，并在 git commit 里引用
编号（如 "R1.3: identical-by-construction wording fixed"）。*

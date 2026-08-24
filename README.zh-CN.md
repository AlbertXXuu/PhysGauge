<p align="center">
  <img src="docs/assets/alvenx-wordmark.svg" width="320" alt="AlvenX">
</p>

# PhysGauge

[English](README.md) · [协议说明](docs/protocol.md) · [勘误](docs/ERRATA.md) ·
[路线图](docs/ROADMAP.md) · [学习模型实验协议（R2）](docs/r2-protocol.md) ·
[v1 证据](docs/evidence/v1.0.0/report.md) · [学习模型证据](docs/evidence/r2/report.md)

PhysGauge 是一个本地、确定性的视频评测指标压力测试工具。它在经过解析验证的二维双圆盘
碰撞世界中注入已知错误，再检查评测指标是否发现错误，以及错误变严重时指标是否单调响应。

它是**指标校准工具**，不是另一个世界模型排行榜。

## v1 已经证明什么

- 24 个固定种子的 oracle 轨迹全部守恒能量和动量，并且都发生可观测碰撞。
- 状态真值指标能抓住所有注入的能量、动量、碰撞事件、初始条件和随机状态错误。
- MSE、SSIM error、Pixel Fréchet 和时序梯度 MSE 对非弹性与动量扰动的三级强度均单调响应。
- 不保留帧顺序的 Pixel Fréchet 存在帧顺序盲点：只倒序状态序列而不反转速度时
  （这是帧顺序反转，不是物理时间反演），计算距离为 0 至约 `5.76e-15`，但运动学残差很大。
  具体含义与适用边界见[勘误](docs/ERRATA.md)。

这些结论由测试和带 SHA-256 校验的
[`v1.0.0` 证据包](docs/evidence/v1.0.0/manifest.json)共同约束。它们不代表所有视觉指标或公开
排行榜都会失败，也不是对真实世界模型的评测结果。

## 学习模型研究结果

预注册的研究里程碑 R2 实验在 oracle / persistence / linear 管线 dry-run 通过后，训练并评估了三个小型
状态动力学预测器。三个种子都被分类为 `too-weak`：碰撞后 partial-error 比例为
91.8%–99.6%，因此冻结结果是 `inconclusive-model`。部分视觉指标虽出现分歧，但模型能力门
先失败，不能把这些数值解释为 learned-model 视觉盲点的证据。详见
[学习模型报告](docs/evidence/r2/report.md)和[实验协议](docs/r2-protocol.md)。这里的 `R2` 是
**研究里程碑 2**，不是 PhysGauge 2.0。

## 快速开始

支持 Python 3.11–3.13。

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e .
physgauge studio

physgauge doctor
physgauge run --output runs\my-calibration
physgauge verify --bundle docs\evidence\v1.0.0
```

一次运行会输出完整 JSON、扁平 CSV、Markdown 报告、SVG 灵敏度矩阵和 SHA-256 清单。
不需要 API Key、网络、GPU、模型权重或训练。

## Python API

```python
from physgauge import SuiteConfig, run_suite, write_bundle

result = run_suite(SuiteConfig(cases=24, frames=48, seed=20260824))
write_bundle(result, "runs/example")
```

如果模型或模拟器能提供相同的八维状态，可直接调用 `physgauge.evaluate_trajectory(...)`。
状态布局、指标定义、阈值和结论边界见[协议说明](docs/protocol.md)。

## 项目边界

- v1 只覆盖等质量、二维刚性圆盘碰撞。
- `pixel_frechet` 使用低维灰度像素特征，不是 Inception FID 或 FVD。
- 物理定律诊断依赖状态真值；只有视频帧时只能使用视觉指标，不能获得逐定律保证。
- 随机基线只用于标定尺度，不代表任何真实模型。

Apache-2.0 许可证。PhysGauge 是 [AlvenX](https://alvenx.com) 开源项目。

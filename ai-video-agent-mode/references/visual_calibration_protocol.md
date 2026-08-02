# 真实成片视觉校准协议

本协议只在用户已提供同一镜头的真实 before/after 成片，并明确要求校准视觉策略时使用。
它是离线证据侧车，不属于生产工作流，不由 `route_task.py`、supervisor、dispatch 或标准回归加载，
也不会自动修改提示词合同或策略。

## 证据边界

- before/after 必须使用相同剧本目标；生成模型与主要参数应可比。
- `strategy_spec` 写清本次唯一增量策略及版本；同一 `strategy_id` 的所有案例必须绑定同一 SHA。
- `generation_fingerprint` 记录模型、关键参数和 seed 组的稳定指纹；准入至少覆盖两个不同指纹。
- 盲评者只接触 `blind_review.json` 和中性 A/B 视频，不接触 `sealed_mapping.json`、源文件名或策略说明。
- 文件 SHA 与完整性摘要用于发现意外替换或编辑，不是密码学签名；不能防止可同时改写文件和摘要的攻击者。
- 当前环境没有统一转码器，中性副本不消除时长、码率和文件大小线索。盲评者不得预先接触源视频。

## 1. 准备盲评包

```bash
python3 scripts/calibration/visual_calibration_lab.py prepare \
  --before-video <before.mp4> \
  --after-video <after.mp4> \
  --before-prompt <before_prompt.txt> \
  --after-prompt <after_prompt.txt> \
  --strategy-spec <strategy_v1.md> \
  --out-dir <case_dir> \
  --case-id <unique_case_id> \
  --strategy-id <stable_strategy_id> \
  --scene-type <scene_type> \
  --generation-fingerprint <model_params_seed_fingerprint> \
  --target-dimension light_color_quality \
  --target-dimension material_realism \
  --target-dimension motion_liveness
```

工具随机生成 A/B 映射，将视频复制为中性文件，分别输出可交给盲评者的
`blind_review.json` 和必须隔离保存的 `sealed_mapping.json`。不要覆盖旧 case 目录。

盲评者为 A/B 的八个维度填写 1–10 分，填写 `reviewer_id`、`winner=a|b|tie`，完成后把
`blind_confirmed` 改为 `true`。评分时不得查看封存映射。

## 2. 完成单例报告

```bash
python3 scripts/calibration/visual_calibration_lab.py finalize \
  --review <case_dir/blind_review.json> \
  --sealed <case_dir/sealed_mapping.json> \
  --out <case_dir/calibration_report.json> \
  --samples 18
```

工具先验证视频、提示词、策略规格和封存映射 SHA，再用 macOS AVFoundation 均匀取帧。
报告记录主观 before/after 差值、亮度/高光/暗部/红蓝平衡/细节/帧差，以及水平强边缘位置漂移
代理值。客观指标只用于发现技术退化：不能识别人脸、骨骼、真实地平线，也不能单独证明审美、
材质真实性或灵动性。

## 3. 聚合策略证据

```bash
python3 scripts/calibration/visual_calibration_lab.py promote \
  --report <case_01/calibration_report.json> \
  --report <case_02/calibration_report.json> \
  --report <case_03/calibration_report.json> \
  --report <case_04/calibration_report.json> \
  --out <visual_strategy_registry.json> \
  --strategy-id <stable_strategy_id>
```

只有同时满足以下条件的策略进入 `validated_strategies`：至少 4 个案例、2 种场景、2 个生成
指纹、after 胜率不低于 0.65、每个目标维度平均提升不低于 0.5、人物物理/瑕疵控制/连续性/
提示词忠实度的平均回退均不超过 0.25，并且没有严重客观退化标记。其余只进入
`rejected_candidates` 并列出原因。

注册表明确标记 `auto_consumed_by_production=false`。人工复核通过后，另开技能修改任务，将
已验证策略以最小改动写入相应知识合同并运行生产回归；禁止让生产流程动态读取实验注册表。

## 独立自测

```bash
python3 scripts/calibration/test_visual_calibration_lab.py
```

该测试包含 Swift 指标内存自测、封存映射、评分缺失、候选篡改、报告篡改、成功准入和低胜率
拒绝。它故意不加入 `run_regression_suite.py`，因此生产回归时没有 Swift 编译或视频分析成本。

# 50 Main-Shot Benchmark Protocol

Run six real, completed 50-main-shot projects: dialogue, multi-character interaction and action, each once at 0% injected failure and once at 10%. Each run must retain its actual pipeline state, provenance, performance report and project configuration.

For each completed run, first write the per-run performance artifact:

```bash
python3 scripts/performance_budget.py <completed_50_shot_run_dir>
```

Then summarize all six evidence directories:

```bash
python3 scripts/benchmark_core_pipeline.py \
  --out <benchmark_report.json> \
  <dialogue_0_run_dir> <dialogue_10_run_dir> \
  <action_0_run_dir> <action_10_run_dir> \
  <mixed_0_run_dir> <mixed_10_run_dir>
```

The benchmark passes only if every scenario has both 0% and 10% failure-injection runs, every run contains exactly 50 main shots, and measured P95 is at most 55 minutes. Do not infer or simulate latency from configured batch sizes.

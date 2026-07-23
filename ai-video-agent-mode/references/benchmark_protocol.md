# 50 Main-Shot Benchmark Protocol

Run six real, completed 50-main-shot projects: dialogue, multi-character interaction and action, each once at 0% injected failure and once at 10%. Each run must retain its actual pipeline state, provenance, performance report and project configuration. Run `benchmark_core_pipeline.py` on all six directories. It passes only if every scenario has both runs and measured P95 is at most 55 minutes.

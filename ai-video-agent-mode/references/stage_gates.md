# Current Pipeline Gates

| Phase | Input | Output | Gate |
|---|---|---|---|
| Scene Lock | shot plan | `scene_locks.json` | one immutable record per scene; space, positions, props, wardrobe, light source/direction/temperature and audio policy complete |
| Master Production | shot plan + scene locks | master-shot `shots[]` | one T2V task per main shot; 1–3 continuous internal beats; all three contracts and five Jimeng sections pass |
| Editor Pass 2 | prompt package | scene-window reviews | every window includes previous/current/next main-shot summaries; all blocking issues are resolved by field-scoped main-shot patches |
| Validate | final package | reports | deterministic, semantic, export and token-budget gates pass |

No previous analysis, Director or Composer phase is valid in this contract.

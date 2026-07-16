# Scene Analysis Agent (Phase 2b)

## 技能加载
子Agent启动时通过 items 加载 frames-analysis 技能。

## 角色定义
你是场景分析Agent，分析每镜空间布局和灯光设计，产出结构化JSON。

## 参考示例
执行前加载 references/examples/scene_example.json。

## 输出格式

{
  "subshot_id": "S1-01-01",
  "space_type": "indoor/outdoor/hallway/stairwell/doorway",
  "space_name": "玄关/餐厅/卧室/走廊",
  "char_positions": ["秦展-画面中央推门入画"],
  "char_wardrobes": ["秦展-深色机能风外套，短发"],
  "bg_foreground": "餐桌居中，酒瓶散落",
  "bg_midground": "墙面挂钟，家庭照片",
  "bg_background": "窗外城市夜景",
  "light_type": "暖黄吊灯顶光/冷白管灯/混合光",
  "light_temp": 3200,
  "light_direction": "正顶光向下/侧前方45度",
  "light_hardness": "soft/hard/mixed",
  "light_effect_primary_char": "冷蓝光从头顶偏后打下",
  "light_effect_other_chars": "暖色钨丝灯从侧方照亮餐桌",
  "color_contrast_desc": "冷蓝秦展 vs 暖色餐桌区",
  "mood_atmosphere": "压抑紧张/暖黄温馨/冷清疏离",
  "bgm_style": "极简电子pad长音/钢琴独奏/弦乐铺垫/低频sub-bass/无",
  "ambient_sound": "走廊管灯低频嗡鸣/窗外城市霓虹/室内静默/楼道回声",
  "sfx_timing": "脚步声每步0.35s/拍桌声+共振余韵0.3s/关门声轻响",
  "audio_foreground": "秦展靴子踩木地板硬底声/碗筷碰撞声/脚步声",
  "audio_midground": "外套布料摩擦沙沙声/桌椅挪动声",
  "audio_background": "窗外城市低频电气嗡鸣/远处电轨刹车声/室内钟摆滴答"
}

items 数组顺序与 shot_plan 的 subshots 一致。

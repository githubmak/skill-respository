#!/usr/bin/env python3
"""Derive reusable scene-level moving-image texture contracts."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


PLAN_VERSION = "scene-texture-plan-v1"
GENERIC_LOOKS = {
    "general_cinematic": "统一克制电影化动态影像基调",
    "chinese_wuxia_game_cinematic": "统一东方武侠游戏过场式电影动态基调，空间和材质保持写实重量",
    "grounded_historical_wuxia": "统一写实历史武侠电影动态基调，旧损材质与自然光保持克制",
    "painterly_elegant_wuxia": "统一写意古风电影动态基调，山水层次和服装轮廓清楚不过度辉光",
    "period_court_cinematic": "统一古装宫廷关系戏电影动态基调，礼制空间和华饰保持克制",
    "modern_natural_drama": "统一现代生活流电影动态基调，现实光源和自然表演优先",
    "modern_cinematic_variant": "统一都市电影动态基调，玻璃金属布料反光彼此分离",
    "rural_lived_in_naturalism": "统一乡村生活写实电影动态基调，地域材质和天气痕迹可读",
}


def build(run_dir: str, scene_lock_path: str, output_path: str | None = None) -> tuple[dict[str, Any], str]:
    run_path = Path(run_dir).expanduser().resolve()
    config = _load(run_path / "project_config.json")
    locks = _load(Path(scene_lock_path))
    receipt = ((config.get("source_rules") or {}).get("style_evidence") or {})
    report_path = str((config.get("source_rules") or {}).get("source_gate_report", "") or "")
    source_report = _load(Path(report_path)) if report_path else {}
    full_receipt = source_report.get("style_evidence", {}) if isinstance(source_report, dict) else {}
    if isinstance(full_receipt, dict) and full_receipt:
        receipt = {**receipt, **full_receipt}
    project_profile = str(receipt.get("base_profile", "") or "general_cinematic")
    scene_receipts = {
        str(item.get("scene", "")): item
        for item in receipt.get("scene_receipts", [])
        if isinstance(item, dict) and str(item.get("scene", ""))
    }
    scenes = []
    for lock in locks.get("scenes", []) if isinstance(locks.get("scenes"), list) else []:
        if not isinstance(lock, dict):
            continue
        scene = str(lock.get("scene", "") or "__default__")
        local_receipt = _scene_receipt(scene_receipts, scene)
        profile = str(local_receipt.get("base_profile", "") or project_profile)
        contract = _contract(config, lock, profile)
        scenes.append({
            "scene": scene,
            "base_profile": profile,
            "profile_confidence": str(local_receipt.get("confidence", "") or receipt.get("confidence", "low")),
            "video_texture_contract": contract,
        })
    result = {"plan_version": PLAN_VERSION, "scenes": scenes}
    destination = Path(output_path) if output_path else run_path / ".cache" / "analysis" / "scene_texture_plan.json"
    _write(destination, result)
    return result, str(destination)


def contract_for_scene(plan: dict[str, Any], scene: str) -> dict[str, str]:
    for item in plan.get("scenes", []) if isinstance(plan, dict) else []:
        if str(item.get("scene", "")) == str(scene):
            contract = item.get("video_texture_contract", {})
            return dict(contract) if isinstance(contract, dict) else {}
    return {}


def _scene_receipt(receipts: dict[str, dict[str, Any]], scene: str) -> dict[str, Any]:
    if scene in receipts:
        return receipts[scene]
    normalized = str(scene or "").strip()
    for name, receipt in receipts.items():
        candidate = str(name or "").strip()
        if normalized and candidate and (normalized in candidate or candidate in normalized):
            return receipt
    return {}


def _contract(config: dict[str, Any], lock: dict[str, Any], profile: str) -> dict[str, str]:
    look = GENERIC_LOOKS.get(profile, GENERIC_LOOKS["general_cinematic"])
    visual_style = str(config.get("visual_style", "") or "").strip()
    source = str(lock.get("light_source", "") or "现实动机光")
    direction = str(lock.get("light_direction", "") or "固定方向")
    temperature = str(lock.get("light_temperature", "") or "场景既定色温")
    material = str(lock.get("lived_in_detail", "") or lock.get("prop_state", "") or "剧情相关材质保留粗糙与不均匀响应")
    atmosphere = str(lock.get("natural_motion_system", "") or "空气层保持低幅稳定")
    tone = str(lock.get("tone_palette", "") or lock.get("genre_visual_signature", "") or "场景色彩职责保持统一")
    return {
        "look_profile": _compact("；".join(part for part in (look, visual_style) if part)),
        "exposure_policy": _compact(f"{source}从{direction}以{temperature}持续受光；人物脸与手曝光可读，高光不过曝、黑位保留暗部层次"),
        "material_motion_policy": _compact(f"{material}；衣料、皮肤、玻璃、金属或道具材质只随真实接触和机位变化产生不均匀反光"),
        "atmosphere_motion_policy": _compact(f"{atmosphere}；雨雾尘或空气颗粒只在有动力源的景深层低幅流动并自行减弱"),
        "camera_stability_policy": "同一镜头只使用固定机位或一条有动机的低幅镜头路径，起止锚点稳定且不叠加变焦",
        "continuity_carryover": _compact(f"跨镜继承同一光源方向、曝光基准、{tone}与材质反光逻辑，不跳色、不重置空气方向"),
        "risk_controls": "人物、台词、道具交接或支撑变化复杂时先取消镜头运动，再删除第二环境响应，保留稳定终态",
    }


def _compact(value: str, limit: int = 176) -> str:
    text = " ".join(str(value or "").split())
    return text[:limit].rstrip("，；; ")


def _load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
        return value if isinstance(value, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temp, path)

#!/usr/bin/env python3
"""Apply narrow Editor-requested repairs to one Master retry packet.

This is intentionally conservative: it copies the currently verified main-shot
task from the merged package, patches only the named continuity/aspect/costume
fields, and writes the packet batch output.  It does not merge public output.
"""

import copy
import json
import os
import sys


def main(packet_path):
    packet_path = os.path.abspath(packet_path)
    with open(packet_path, encoding="utf-8-sig") as handle:
        packet = json.load(handle)
    out_path = packet["_batch_output_path"]
    shot_ids = [
        str(item.get("shot_id", "") or item.get("subshot_id", "")).strip()
        for item in packet.get("items", [])
        if isinstance(item, dict)
    ]
    shot_ids = [shot_id for shot_id in shot_ids if shot_id]
    if len(shot_ids) != 1:
        raise SystemExit("expected exactly one target shot in retry packet")
    shot_id = shot_ids[0]
    merged_path = packet.get("output_path") or os.path.join(packet["run_dir"], ".cache", "composer", "merged.prompt_package.json")
    with open(merged_path, encoding="utf-8-sig") as handle:
        merged = json.load(handle)
    source = None
    for shot in merged.get("shots", []):
        if shot.get("shot_id") == shot_id:
            source = shot
            break
    if not source:
        raise SystemExit("shot not found in merged package: %s" % shot_id)
    shot = copy.deepcopy(source)
    changed = _repair(shot_id, shot)
    if not changed:
        raise SystemExit("no targeted repair rule for %s" % shot_id)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as handle:
        json.dump({"shots": [shot]}, handle, ensure_ascii=False, indent=2)
    print(out_path)


def _repair(shot_id, shot):
    if shot_id == "S1-03":
        _replace_deep(shot, "屏幕朝上但起幅为暗屏", "屏幕朝上且起幅已经亮屏，只显示无可读文字的模糊通知块")
        _replace_deep(shot, "触发来自画面左前手机亮屏，林夏伸手确认", "触发来自画面左前手机已经亮屏后的信息压力，林夏伸手确认")
        _replace_deep(shot, "手机起幅平放柜面暗屏，中段被手指接触并拿起", "手机起幅平放柜面且已经亮屏，中段被手指接触并拿起")
        _replace_deep(shot, "手机屏幕亮起一块无具体可读文字的新消息光块", "林夏注意到既有亮屏上的无具体可读文字通知光块")
        _replace_deep(shot, "手机屏幕亮起", "手机已亮屏")
        _replace_deep(shot, "一块无具体可读文字的新消息光块", "一块无具体可读文字的既有通知光块")
        _replace_deep(shot, "一次短促电子提示音", "手指触碰手机边缘的轻声")
        _replace_deep(shot, "暗屏", "已亮屏")
        qa = shot.setdefault("qa_metadata", {})
        qa["start_state"] = "林夏坐在病床左侧床沿，手机平放在画面左前床头柜，屏幕已经亮起但没有可读文字。"
        qa["end_state"] = "林夏仍坐在病床左侧床沿，手机亮屏停在她右手中，拇指悬在屏幕边缘，没有点开。"
        _set_basemap(qa, "state_prop_basis", "手机从起幅开始就是已亮屏状态，只作为无可读文字的信息压力；林夏拿起后拇指悬停不点开。")
        pc = qa.setdefault("performance_contract", {})
        if isinstance(pc, dict):
            pc["trigger_event"] = "林夏指尖接触已亮屏手机边缘，并注意到既有不可读通知光块带来的信息压力"
            pc["trigger_time"] = "1.0秒指尖接触手机侧边，视线落到既有亮屏通知光块"
            pc["reaction_delay"] = "接触已亮屏手机后呼吸短暂停半拍再拿起"
            pc["primary_expression"] = "视线从手机边缘落到屏幕亮光"
            pc["eye_focus"] = "视线从手机边缘落到屏幕亮光"
        return True
    if shot_id == "S1-04":
        phone_anchor = "画面左侧林夏右手仍握着已亮屏手机，拇指悬在屏幕边缘，手机只作轻度虚焦继承道具，不抢焦、不显示可读文字、不被触碰。"
        _inject_after(shot, "主体与空间锁定：", phone_anchor)
        _inject_after(shot, "主镜头连续规则：", "起幅可见事实包含林夏右手中的亮屏手机仍在画面左侧轻虚焦保留，系统电子音和监护仪是主焦点，手机不复位、不消失。")
        _inject_after(shot, "子镜头组：", "起幅左侧边缘保留林夏右手亮屏手机的轻虚焦轮廓，拇指仍停在屏幕边缘但不点开；")
        qa = shot.setdefault("qa_metadata", {})
        qa["start_state"] = "病房夜间压低的静止状态，监护仪固定在病床右侧；林夏右手仍握亮屏手机，拇指悬在屏幕边缘。"
        qa["end_state"] = "落幅仍留在监护仪边缘，系统音消失但低频监护声保留；林夏右手亮屏手机仍在画面左侧轻虚焦保留，没有复位或消失。"
        _set_basemap(qa, "state_prop_basis", "S1-03 落幅手机亮屏在林夏右手中；S1-04 继续以轻虚焦继承，不显示可读文字，不抢占监护仪主焦点。")
        return True
    if shot_id == "S1-06":
        _replace_deep(shot, "门缝开启到护士停在画面右侧", "护士已经停稳在画面右侧门口")
        _replace_deep(shot, "说完后护士停半拍，把紧张压在停步和文件袋上", "说完后护士停半拍，把紧张压在静止姿态和文件袋上")
        _replace_deep(shot, "停步", "静止姿态")
        qa = shot.setdefault("qa_metadata", {})
        qa["start_state"] = "护士已经停稳在门口/画面右侧，文件袋贴在胸前，不再进入。"
        qa["end_state"] = "护士说完后停半拍，文件袋仍贴在胸前并保留在画面右侧。"
        cc = qa.setdefault("continuity_contract", {})
        if isinstance(cc, dict):
            cc["state_change"] = False
            cc["position_continuity"] = "承接上一镜护士已在门口/画面右侧，不再进入；文件袋持续贴在胸前，为 S1-07 文件袋递入做承接。"
            cc["state_transitions"] = []
        pc = qa.setdefault("performance_contract", {})
        if isinstance(pc, dict):
            pc["visual_progression"] = "护士已经停稳在画面右侧，右手文件袋贴在胸前，起句前0.3秒短吸气，说完后护士停半拍。"
        return True
    if shot_id == "S1-07":
        _replace_deep(shot, "横屏短剧镜头", "9:16竖屏短剧镜头")
        _replace_deep(shot, "深色外套和内搭", "深灰衬衫，袖口卷到前臂，胸前无装饰")
        _replace_deep(shot, "深色外套", "深灰衬衫，袖口卷到前臂，胸前无装饰")
        _replace_deep(shot, "周屿穿深色外套", "周屿穿深灰衬衫，袖口卷到前臂，胸前无装饰")
        _replace_deep(shot, "屏幕亮起只显示无可读文字的模糊通知块", "屏幕保持已亮状态，只显示无可读文字的模糊通知块")
        _replace_deep(shot, "通知只作为屏幕亮块和轻微电子提示存在", "通知只作为既有屏幕亮块存在，不新增手机声音")
        _replace_deep(shot, "约1.8秒手机右侧边缘保留一块无文字通知亮块和一次很轻的电子提示", "约1.8秒手机右侧边缘只保留既有无文字通知亮块，不新增手机声音")
        _replace_deep(shot, "手机一次短促提示音", "手机不新增声音")
        _replace_deep(shot, "一次很轻的电子提示", "既有无文字通知亮块")
        _replace_deep(shot, "轻微电子提示", "低弱电子底噪")
        return True
    if shot_id == "S1-09":
        _replace_deep(shot, "横屏短剧镜头", "9:16竖屏短剧镜头")
        _replace_deep(shot, "深色外套和内搭", "深灰衬衫，袖口卷到前臂，胸前无装饰")
        _replace_deep(shot, "深色外套", "深灰衬衫，袖口卷到前臂，胸前无装饰")
        _replace_deep(shot, "周屿穿深色外套", "周屿穿深灰衬衫，袖口卷到前臂，胸前无装饰")
        _replace_deep(shot, "屏幕亮起只显示无可读文字的模糊通知块", "屏幕保持已亮状态，只显示无可读文字的模糊通知块")
        _replace_deep(shot, "通知只作为屏幕亮块和轻微电子提示存在", "通知只作为既有屏幕亮块存在，不新增手机声音")
        _replace_deep(shot, "约1.8秒手机右侧边缘保留一块无文字通知亮块和一次很轻的电子提示", "约1.8秒手机右侧边缘只保留既有无文字通知亮块，不新增手机声音")
        _replace_deep(shot, "手机一次短促提示音", "手机不新增声音")
        _replace_deep(shot, "一次很轻的电子提示", "既有无文字通知亮块")
        _replace_deep(shot, "轻微电子提示", "低弱电子底噪")
        _replace_deep(
            shot,
            "身体朝画面右侧，视线压向周屿手中的文件袋",
            "身体朝画面右侧，起幅视线先停向画面右侧监护仪方向，随后被周屿手中文件袋的轻微移动触发，低幅转向文件袋",
        )
        _replace_deep(
            shot,
            "起幅林夏在病床左侧或床沿近景，身体朝画面右侧，脸色疲惫，视线先停在周屿双",
            "起幅林夏在病床左侧或床沿近景，身体朝画面右侧，脸色疲惫，视线先停在画面右侧监护仪方向；周屿手中文件袋轻微压低后，林夏视线才低幅转向周屿双",
        )
        qa = shot.setdefault("qa_metadata", {})
        qa["start_state"] = "林夏在病床左侧或床沿近景，先闭口看向画面右侧监护仪方向；周屿在病床右侧双手握着未打开的文件袋。"
        qa["end_state"] = "文件袋仍在周屿双手且未打开，周屿视线避开林夏；林夏的视线已由监护仪方向低幅转向文件袋。"
        pc = qa.setdefault("performance_contract", {})
        if isinstance(pc, dict):
            pc["voice_or_breath_control"] = "手机右侧边缘只保留既有无文字通知亮块"
        _set_basemap(qa, "character_orientation_basis", "林夏先承接 S1-08 的右向监护仪视线，再因周屿手中文件袋轻微移动转向文件袋；周屿服装锁定为深灰衬衫、袖口卷到前臂、胸前无装饰。")
        return True
    return False


def _replace_deep(value, old, new):
    if isinstance(value, dict):
        for key, child in list(value.items()):
            if isinstance(child, str):
                value[key] = child.replace(old, new)
            else:
                _replace_deep(child, old, new)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            if isinstance(child, str):
                value[index] = child.replace(old, new)
            else:
                _replace_deep(child, old, new)


def _inject_after(shot, marker, insertion):
    prompt = shot.get("full_prompt", "")
    if insertion in prompt or marker not in prompt:
        return
    shot["full_prompt"] = prompt.replace(marker, marker + insertion + " ", 1)


def _set_basemap(qa, key, value):
    basemap = qa.setdefault("source_constraint_basemap", {})
    if isinstance(basemap, dict):
        basemap[key] = value


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: apply_targeted_master_repair.py <packet.json>")
    main(sys.argv[1])

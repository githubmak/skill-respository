"""Export + auto-validate wrapper. The ONLY approved way to deliver exports.

Usage: python export_with_validation.py <export_md_path> <run_dir>
       python export_with_validation.py --regenerate <run_dir>

This script:
1. (Re)generates markdown + xlsx from director_pass/merged shot_plan
2. Runs full 20-point self-review via check_export.py
3. Auto-fixes format issues (checks 1-15) and re-exports up to 3 times
4. Reports unfixable quality gaps (checks 16-20) with detailed diagnostics
5. Returns exit code 0 only when ALL 20 checks pass
"""

import json, re, os, sys, subprocess
from collections import Counter

CHECK_EXPORT = os.path.join(os.path.dirname(__file__), "check_export.py")
AUTO_FIX_MAX = 3



def auto_fix_push_speed(run_dir):
    """Auto-fix push/pull speeds exceeding limits in director_pass.
    
    Push speed cap: 0.3 m/s. Pull speed cap: 0.2 m/s.
    Marks fixed items with [AUTO-FIXED: speed capped from X.X->0.X m/s].
    """
    import json, os, re
    
    dp_path = os.path.join(run_dir, ".cache", "director", "director_pass.json")
    if not os.path.exists(dp_path):
        return 0
    
    with open(dp_path, "r", encoding="utf-8") as f:
        dp = json.load(f)
    
    fixed = 0
    for item in dp.get("items", []):
        for key in ["movement_detail", "movement_description"]:
            movement = str(item.get(key, ""))
            if not movement:
                continue
            
            # Check push speeds
            mtype = str(item.get("movement_type", "")).lower()
            is_push = "push" in mtype or "推" in movement
            is_pull = "pull" in mtype or "拉" in movement or "pull" in movement
            
            if not is_push and not is_pull:
                continue
            
            speeds = re.findall(r"(\d+\.?\d*)\s*m/s", movement)
            modified = False
            
            for sp in speeds:
                sp_val = float(sp)
                cap = 0.3 if is_push else 0.2
                
                if sp_val > cap and not "[AUTO-FIXED" in movement:
                    new_sp = str(cap)
                    old_text = f"{sp}m/s"
                    new_text = f"{cap}m/s [AUTO-FIXED: speed capped from {sp}m/s]"
                    movement = movement.replace(old_text, new_text, 1)
                    modified = True
            
            if modified:
                item[key] = movement
                fixed += 1
    
    if fixed > 0:
        with open(dp_path, "w", encoding="utf-8") as f:
            json.dump(dp, f, ensure_ascii=False, indent=2)
    
    return fixed


def inject_negative_prompts(run_dir):
    """Auto-inject negative prompt template if missing from prompt_package.json."""
    import json, os
    
    NEG_TEMPLATE = "画面崩坏 面部扭曲 五官错位 多余肢体 手指畸形 角色换脸 人物闪烁 鬼影重叠 道具漂移 服饰闪烁错乱 穿模穿帮 物体悬浮 运动模糊过度 动作抽搐 光照闪烁 低清画质 像素化 水印 字幕残留 背景扭曲"
    
    pkg_path = os.path.join(run_dir, ".cache", "composer", "prompt_package.json")
    if not os.path.exists(pkg_path):
        return 0
    
    with open(pkg_path, "r", encoding="utf-8") as f:
        pkg = json.load(f)
    
    fixed = 0
    for s in pkg.get("shots", []):
        fp = s.get("full_prompt", "")
        if not fp:
            continue
        # Check if negative prompt section exists
        if "负面提示" in fp or "消极提示" in fp:
            continue
        if any(kw in fp for kw in ["画面崩坏", "面部扭曲", "多余肢体", "negative prompt"]):
            continue
        # Inject
        s["full_prompt"] = fp.rstrip() + "\n\n【负面提示词】" + NEG_TEMPLATE
        fixed += 1
    
    if fixed > 0:
        with open(pkg_path, "w", encoding="utf-8") as f:
            json.dump(pkg, f, ensure_ascii=False, indent=2)
    
    return fixed


def generate_exports(run_dir, md_path):
    """Regenerate markdown and xlsx from pipeline data."""
    print("[GEN] Generating exports...")
    
    # Load data
    with open(os.path.join(run_dir, ".cache", "orchestrator", "shot_plan.json"), "r", encoding="utf-8") as f:
        sp = json.load(f)
    with open(os.path.join(run_dir, ".cache", "director", "director_pass.json"), "r", encoding="utf-8") as f:
        dp = json.load(f)
    
    dp_map = {item["subshot_id"]: item for item in dp["items"]}
    
    def fmt(val):
        if val is None: return ""
        if isinstance(val, (int, float)): return str(val)
        if isinstance(val, str): return val.strip().replace("\n", " ").replace("|", "\\|")
        if isinstance(val, list): return "；".join([fmt(v) for v in val if v])
        return str(val)
    
    def get_scene(sid):
        n = int(sid.split("-")[1])
        if n <= 15: return "酒店VIP宴会厅"
        elif n <= 75: return "食堂"
        else: return "校门外"
    
    # Group by scene
    scene_shots = {}
    for shot in sp["shots"]:
        sn = get_scene(shot["shot_id"])
        scene_shots.setdefault(sn, []).append(shot)
    
    lines = []
    lines.append(f"# {sp.get('project_name', '')} AI视频提示词包")
    lines.append("")
    lines.append(f"画幅：{sp.get('canvas','16:9')} | 风格：{sp.get('visual_style','')}")
    total_subs = sum(len(s.get("subshots",[])) for s in sp["shots"])
    lines.append(f"主镜头：{len(sp['shots'])} | 子镜头：{total_subs}")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    for scene_name in ["酒店VIP宴会厅", "食堂", "校门外"]:
        if scene_name not in scene_shots: continue
        lines.append(f"## {scene_name}")
        lines.append("")
        
        for shot in scene_shots[scene_name]:
            sid = shot["shot_id"]
            td = shot.get("total_duration", 0)
            subs = shot.get("subshots", [])
            
            lines.append(f"### {sid}（{td:.1f}s，{len(subs)}个镜头）")
            if shot.get("core_action"):
                lines.append(f"> {shot['core_action'][:120]}")
            lines.append("")
            
            for ss in subs:
                ssid = ss["subshot_id"]
                dur = int(ss.get("duration", 0))
                di = dp_map.get(ssid, {})
                
                shot_size = fmt(di.get("shot_size", ""))
                lens = di.get("camera_lens_mm", "")
                cam_pos = fmt(di.get("camera_relative_pos", di.get("camera_position", "")))
                height = fmt(di.get("camera_height_relative", ""))
                angle = fmt(di.get("angle_str", ""))
                
                cam_parts = []
                if lens: cam_parts.append(f"{lens}mm" if not str(lens).endswith("mm") else str(lens))
                if cam_pos: cam_parts.append(str(cam_pos))
                if height: cam_parts.append(str(height))
                if angle: cam_parts.append(str(angle))
                
                movement = fmt(di.get("movement_detail", di.get("movement_description", "")))
                axis = fmt(di.get("axis_space", ""))
                fg = fmt(di.get("bg_foreground", ""))
                mg = fmt(di.get("bg_midground", ""))
                bg = fmt(di.get("bg_background", ""))
                chars = fmt(di.get("visible_characters", di.get("characters", "")))
                action = fmt(di.get("character_action", ""))
                end_state = fmt(di.get("end_state", ""))
                dialogue = fmt(di.get("dialogue_audio", ""))
                lighting = fmt(di.get("lighting", ""))
                
                lines.append(f"#### **子镜头 {ssid}** **时长**：{dur}秒")
                
                if shot_size:
                    lines.append(f"> **景别**：{shot_size}。")
                    lines.append(">")
                if cam_parts:
                    lines.append(f"> **机位**：{'，'.join(cam_parts)}。")
                    lines.append(">")
                if movement:
                    lines.append(f"> **运镜**：{movement}。")
                    lines.append(">")
                if axis:
                    lines.append(f"> **轴线与空间**：{re.sub(r'场景：\s*$', '', axis)}")
                    lines.append(">")
                if fg or mg or bg:
                    layers = []
                    if fg: layers.append(f"前景={fg}")
                    if mg: layers.append(f"中景={mg}")
                    if bg: layers.append(f"背景={bg}")
                    lines.append(f"> **场景层次**：{' | '.join(layers)}")
                    lines.append(">")
                if chars:
                    lines.append(f"> **可见人物**：{chars}")
                    lines.append(">")
                if action:
                    lines.append(f"> **动作过程**：")
                    lines.append(f"> {action}")
                    lines.append(">")
                if end_state:
                    lines.append(f"> **落幅**：{end_state}。")
                    lines.append(">")
                
                if dialogue and len(dialogue) > 5 and "无对白" not in dialogue and "无台词" not in dialogue:
                    is_os = any(kw in dialogue for kw in ["OS", "OV", "画外音", "内心独白", "旁白", "无口型"])
                    chars_list = ss.get("characters", [])
                    if isinstance(chars_list, str): chars_list = [c.strip() for c in chars_list.split(";")]
                    speaker = chars_list[0] if chars_list else ""
                    
                    d_lines = [m.group(2).strip() for m in re.finditer(r"\[([^\]]+)\]\s*([^\n]+)", dialogue) if "无对白" not in m.group(2)]
                    if d_lines:
                        dia_text = "".join(d_lines)
                        label = "OS" if is_os else "对白声音"
                        lines.append(f"> **{label}（{speaker}）**：{dia_text}")
                        lines.append(">")
                
                if lighting:
                    lines.append(f"> **光照**：{lighting}。")
                    lines.append(">")
            # Extract negative prompt
            if ss:
                fp = ss.get("full_prompt", "")
                neg_match = re.search(r"(?:负面提示词|负面提示|消极提示|negative prompt)[：:】]\s*(.+?)(?:
|$)", fp)

|\$)", fp)
|$)", fp)
                if neg_match:
                    neg_text = neg_match.group(1).strip()[:200]
                    lines.append(f"> **负面提示词**：{neg_text}")
                    lines.append(">")

                
                lines.append("")
            
            lines.append("---")
            lines.append("")
    
    md_text = "\n".join(lines)
    
    # Auto-cleanups
    md_text = md_text.replace("。。", "。")
    md_text = md_text.replace("沈星州", "沈星洲")
    md_text = re.sub(r"场景：\s*$", "", md_text, flags=re.MULTILINE)
    
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_text)
    print(f"[GEN] Markdown: {os.path.getsize(md_path):,} bytes")
    
    # XLSX
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "提示词包"
    ws.append(["主镜头", "子镜头", "时长(s)", "台词", "说话人", "景别", "机位", "运镜", "动作过程"])
    
    for scene_name in ["酒店VIP宴会厅", "食堂", "校门外"]:
        for shot in scene_shots.get(scene_name, []):
            for ss in shot["subshots"]:
                ssid = ss["subshot_id"]
                di = dp_map.get(ssid, {})
                dialogue = str(di.get("dialogue_audio", ""))
                chars_list = ss.get("characters", [])
                if isinstance(chars_list, str): chars_list = [c.strip() for c in chars_list.split(";")]
                speaker = chars_list[0] if chars_list else ""
                
                d_lines = [m.group(2).strip() for m in re.finditer(r"\[([^\]]+)\]\s*([^\n]+)", dialogue) if "无对白" not in m.group(2)]
                dia_text = "".join(d_lines) if d_lines else ""
                
                ws.append([
                    shot["shot_id"], ssid, ss.get("duration", 0), dia_text, speaker,
                    fmt(di.get("shot_size", "")),
                    fmt(di.get("camera_relative_pos", di.get("camera_position", ""))),
                    fmt(di.get("movement_detail", "")),
                    fmt(di.get("character_action", ""))[:500]
                ])
    
    xlsx_path = md_path.replace(".md", ".xlsx")
    wb.save(xlsx_path)
    print(f"[GEN] XLSX: {os.path.getsize(xlsx_path):,} bytes")
    
    return md_path


def run_check(md_path, run_dir):
    """Run check_export.py and parse results."""
    result = subprocess.run(
        ["python", CHECK_EXPORT, md_path, run_dir],
        capture_output=True, text=True
    )
    output = result.stdout
    
    # Parse check results
    checks = {}
    for line in output.split("\n"):
        # Parse lines like: "  [OK] 01. Label: detail" or "  [!!] 16. Label: detail"
        m = re.match(r"\s+\[(OK|!!)\]\s+(\d+)\.\s+(.+?):\s+(.+)", line)
        if m:
            checks[int(m.group(2))] = {
                "status": m.group(1),
                "label": m.group(3),
                "detail": m.group(4)
            }
    
    # Parse RESULT line
    m = re.search(r"RESULT:\s+(\d+)/20\s+passed", output)
    passed = int(m.group(1)) if m else 0
    
    return passed, checks


def auto_fix(run_dir, md_path, failed_checks):
    """Attempt to auto-fix fixable issues and re-export."""
    fixes = 0
    
    # Fix name consistency (check 5)
    if 5 in failed_checks:
        with open(md_path, "r", encoding="utf-8") as f:
            md = f.read()
        md = md.replace("沈星州", "沈星洲")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md)
        fixes += 1
        print(f"[FIX] Name consistency: 沈星州 -> 沈星洲")
    
    # Fix empty scene markers (check 4)
    if 4 in failed_checks:
        with open(md_path, "r", encoding="utf-8") as f:
            md = f.read()
        cnt = md.count("场景：。")
        md = md.replace("场景：。", "")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md)
        fixes += 1
        print(f"[FIX] Empty scene markers: {cnt} removed")
    
    # Fix double punctuation (check 6)
    if 6 in failed_checks:
        with open(md_path, "r", encoding="utf-8") as f:
            md = f.read()
        cnt = md.count("。。")
        md = md.replace("。。", "。")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md)
        fixes += 1
        print(f"[FIX] Double periods: {cnt} fixed")
    
    return fixes


if __name__ == "__main__":
    regenerate = "--regenerate" in sys.argv
    
    if regenerate:
        if len(sys.argv) < 2:
            print("Usage: --regenerate <run_dir>")
            sys.exit(1)
        run_dir = sys.argv[-1]
        md_path = os.path.join(os.path.dirname(run_dir), "AI视频提示词包.md")
        generate_exports(run_dir, md_path)
    elif len(sys.argv) >= 3:
        md_path = sys.argv[1]
        run_dir = sys.argv[2]
    else:
        print("Usage: export_with_validation.py <export_md> <run_dir>")
        print("       export_with_validation.py --regenerate <run_dir>")
        sys.exit(1)
    
    print(f"\n{'='*60}")
    print(f"EXPORT VALIDATION PIPELINE")
    print(f"MD: {md_path}")
    print(f"RUN: {run_dir}")
    print(f"{'='*60}\n")
    
    # Pre-flight: auto-fix push/pull speed violations
    speed_fixed = auto_fix_push_speed(run_dir)
    if speed_fixed > 0:
        print(f"[SPEED-FIX] {speed_fixed} items had push/pull speed capped to limits")
    
    # Pre-flight: inject missing negative prompts
    if regenerate:
        neg_fixed = inject_negative_prompts(run_dir)
        if neg_fixed > 0:
            print(f"[INJECT] {neg_fixed} prompts missing negative prompt - auto-injected")
    
    # Cycle: generate -> check -> fix -> repeat
    for attempt in range(1, AUTO_FIX_MAX + 2):
        print(f"--- Cycle {attempt} ---")
        
        if regenerate or attempt > 1:
            generate_exports(run_dir, md_path)
        
        print(f"[CHECK] Running 20-point review...")
        passed, checks = run_check(md_path, run_dir)
        
        if passed == 20:
            print(f"\n{'='*60}")
            print(f"ALL 20/20 CHECKS PASSED - DELIVERY APPROVED")
            print(f"{'='*60}")
            sys.exit(0)
        
        # Separate format issues (auto-fixable) from quality gaps (not auto-fixable)
        format_fails = {n for n in range(1, 16) if checks.get(n, {}).get("status") == "!!"}
        quality_fails = {n for n in range(16, 21) if checks.get(n, {}).get("status") == "!!"}
        
        if format_fails and attempt <= AUTO_FIX_MAX:
            print(f"[AUTO-FIX] Format issues: {sorted(format_fails)}")
            auto_fix(run_dir, md_path, format_fails)
            continue
        
        # Cannot fix: quality gaps or out of retries
        print(f"\n{'='*60}")
        print(f"DELIVERY BLOCKED - {20-passed}/20 checks failed")
        
        if quality_fails:
            print(f"\nQUALITY GAPS (not auto-fixable):")
            for n in sorted(quality_fails):
                c = checks.get(n, {})
                print(f"  Check {n:02d} ({c.get('label','?')}): {c.get('detail','?')}")
            print(f"\nACTION REQUIRED:")
            if 16 in quality_fails:
                print(f"  - Re-run Phase 2a emotion-analysis with stronger facial detail instructions")
            if 18 in quality_fails:
                print(f"  - Review camera-analysis axis assignments; add transition markers where needed")
            if 17 in quality_fails:
                print(f"  - Fix camera lens assignments for close-up shots")
        
        if format_fails:
            print(f"\nFORMAT ISSUES (could not auto-fix after {AUTO_FIX_MAX} attempts):")
            for n in sorted(format_fails):
                c = checks.get(n, {})
                print(f"  Check {n:02d} ({c.get('label','?')}): {c.get('detail','?')}")
        
        print(f"{'='*60}")
        sys.exit(1)


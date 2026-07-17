"""Generate prompts from director data."""
import json, os, sys

if not os.environ.get("PYTHONPYCACHEPREFIX") and not getattr(sys, "pycache_prefix", None):
    sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(__file__))
from pycache_policy import block_source_pycache_until_run_dir

block_source_pycache_until_run_dir()
from shot_semantics import is_true_non_action_subshot, render_anchor
def generate_shot(shot_id,entry,dir_items,sl=None):
    items=[]; dm={}
    for di in dir_items:
        if isinstance(di,dict): dm[di.get("subshot_id","")]=di
    for ss in entry.get("subshots",[]):
        ssid=ss["subshot_id"]; di=dm.get(ssid,{}); dur=ss["duration"]
        ch="、".join(ss.get("characters",[])); sz=di.get("shot_size",""); cp=di.get("camera_position","")
        ca=di.get("camera",{}); ct=ca.get("movement","") if isinstance(ca,dict) else str(ca or "")
        ax=di.get("axis_space",""); ac=di.get("character_action",ss.get("base_action","")) or ""
        if not ac and is_true_non_action_subshot(ss):
            ac = "无人物动作；%s。" % (render_anchor(ss) or "非动作画面")
        lt=di.get("lighting",""); ad=di.get("audio_design",""); ma=di.get("micro_actions","")
        da=di.get("dialogue_audio",{}); dr=da.get("raw_text","") if isinstance(da,dict) else str(da or "")
        fp=f"【{ssid}】\n景别:{sz}\n动作:{ac}\n"
        items.append({"shot_id":shot_id,"subshot_id":ssid,"duration":dur,"shot_size":sz,"camera_position":cp,"camera":ct,"axis_space":ax,"character_action":ac,"lighting":lt,"full_prompt":fp})
    return items,dm

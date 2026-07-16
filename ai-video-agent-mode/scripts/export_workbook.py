"""Excel workbook export."""
import json, os, sys, openpyxl
def export(pkg_path,plan_path,out):
    with open(pkg_path,"r",encoding="utf-8-sig") as f: pp=json.load(f)
    with open(plan_path,"r",encoding="utf-8-sig") as f: sp=json.load(f)
    items=pp.get("items",[]); merged=pp.get("merged_full_prompts",[])
    wb=openpyxl.Workbook()
    ws=wb.active; ws.title="分镜总表"
    ws.append(["镜头编号","子镜头编号","场景","时长","景别"])
    for item in items: ws.append([item["shot_id"],item["subshot_id"],"",item.get("duration",""),item.get("shot_size","")])
    ws2=wb.create_sheet("完整提示词")
    ws2.append(["镜头编号","完整提示词"])
    for m in merged: ws2.append([m["shot_id"],m.get("full_prompt","")])
    wb.save(out)
    print(f"Exported: {out}")
if __name__=="__main__":
    if len(sys.argv)<4: print("usage: ..."); sys.exit(1)
    export(sys.argv[1],sys.argv[2],sys.argv[3])

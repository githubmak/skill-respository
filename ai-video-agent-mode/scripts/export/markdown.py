"""Markdown export."""
import json, os
def export(pkg_path,plan_path,md_dir,bn="production"):
    with open(pkg_path,"r",encoding="utf-8-sig") as f: pp=json.load(f)
    with open(plan_path,"r",encoding="utf-8-sig") as f: sp=json.load(f)
    merged=pp.get("merged_full_prompts",[]); os.makedirs(md_dir,exist_ok=True)
    for m in merged:
        sid=m["shot_id"]; dur=m.get("duration",""); fp=m.get("full_prompt","")
        path=os.path.join(md_dir,f"{sid}.md")
        with open(path,"w",encoding="utf-8") as f:
            f.write(f"# {sid}\n\n**Duration**: {dur}s\n\n{fp}\n")
    return len(merged)
if __name__=="__main__":
    import sys
    if len(sys.argv)<4: print("usage: ..."); sys.exit(1)
    print(f"Exported: {export(sys.argv[1],sys.argv[2],sys.argv[3])} files")

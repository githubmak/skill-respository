# merge_agent_outputs.py — 合并多个 Agent 输出文件，去重 (by subshot_id)，验证完整性
# Usage: python merge_agent_outputs.py <output.json> <input1.json> <input2.json> ...
# Every agent writes its own file. This script merges them safely.

import json, sys

def merge_agent_outputs(output_path, *input_paths):
    """Merge multiple agent JSON outputs into one, deduplicating by subshot_id."""
    seen = {}
    all_items = []
    stats = {'files': 0, 'total_from_files': 0, 'duplicates': 0, 'merged': 0}

    for path in input_paths:
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            print('[WARN] Skipping {}: {}'.format(path, e))
            continue

        items = data.get('items', data.get('shots', []))
        stats['files'] += 1
        stats['total_from_files'] += len(items)

        for item in items:
            sid = item.get('subshot_id', '')
            if not sid:
                all_items.append(item)
                continue
            if sid in seen:
                stats['duplicates'] += 1
                continue
            seen[sid] = True
            all_items.append(item)

    stats['merged'] = len(all_items)

    # Determine output wrapper key
    wrapper_key = 'items'
    for path in input_paths:
        try:
            with open(path, 'r', encoding='utf-8') as f:
                d = json.load(f)
            if 'shots' in d:
                wrapper_key = 'shots'
            break
        except:
            continue

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump({wrapper_key: all_items}, f, ensure_ascii=False, indent=2)

    print('[MERGE] {} files -> {} items ({} duplicates removed)'.format(
        stats['files'], stats['merged'], stats['duplicates']))
    return stats

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print('Usage: python merge_agent_outputs.py <output.json> <input1.json> [input2.json ...]')
        sys.exit(1)
    merge_agent_outputs(sys.argv[1], *sys.argv[2:])

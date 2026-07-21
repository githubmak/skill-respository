# merge_agent_outputs.py — 合并多个 Agent 输出文件，去重 (by subshot_id)，验证完整性
# Usage: python3 merge_agent_outputs.py <output.json> <input1.json> <input2.json> ...
# Every agent writes its own file. This script merges them safely.

import hashlib, json, os, sys, time

sys.path.insert(0, os.path.dirname(__file__))
from record_batch_provenance import verify as verify_provenance

def merge_agent_outputs(output_path, *input_paths, require_provenance=False):
    """Merge multiple agent JSON outputs into one, deduplicating by subshot_id."""
    seen = {}
    all_items = []
    stats = {'files': 0, 'total_from_files': 0, 'duplicates': 0, 'merged': 0, 'invalid_provenance': 0}
    source_manifests = []

    for path in input_paths:
        if require_provenance:
            verified, reason, manifest = verify_provenance(path)
            if not verified:
                stats['invalid_provenance'] += 1
                print('[BLOCK] Skipping unverified Agent batch {}: {}'.format(path, reason))
                continue
            source_manifests.append(manifest)
        try:
            with open(path, 'r', encoding='utf-8-sig') as f:
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

    if require_provenance and stats['invalid_provenance']:
        print('[MERGE] BLOCKED: provenance verification failed; public output was not written')
        return stats

    is_prompt_package = output_path.endswith('.prompt_package.json') or any(
        str(path).endswith('.prompt_package.json') for path in input_paths
    )

    result = _build_prompt_package(all_items) if is_prompt_package else {'items': all_items}

    out_dir = os.path.dirname(output_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    if require_provenance:
        merge_manifest = {
            'contract_version': 'modec-v4',
            'output_path': os.path.abspath(output_path),
            'output_sha256': _sha256(output_path),
            'source_batches': source_manifests,
            'created_at': time.time(),
        }
        with open(output_path + '.merge_provenance.json', 'w', encoding='utf-8') as f:
            json.dump(merge_manifest, f, ensure_ascii=False, indent=2)

    print('[MERGE] {} files -> {} items ({} duplicates removed)'.format(
        stats['files'], stats['merged'], stats['duplicates']))
    return stats


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def _build_prompt_package(items):
    """Build the merged Phase 6/7 package with canonical double keys."""
    normalized = []
    for item in items:
        copied = dict(item)
        copied.setdefault('duration', copied.get('duration_sec', 0))
        normalized.append(copied)

    shot_map = {}
    for item in normalized:
        sid = item.get('shot_id', '')
        shot_map.setdefault(sid, []).append(item)

    merged_full_prompts = []
    for sid in sorted(shot_map):
        subshots = sorted(shot_map[sid], key=lambda x: x.get('subshot_id', ''))
        total_dur = sum(float(ss.get('duration', 0) or 0) for ss in subshots)
        combined = '\n\n---\n\n'.join(ss.get('full_prompt', '') for ss in subshots)
        merged_full_prompts.append({
            'shot_id': sid,
            'duration': total_dur,
            'duration_sec': total_dur,
            'full_prompt': combined,
            'negative_prompt': ' | '.join(dict.fromkeys(
                ss.get('negative_prompt', '') for ss in subshots if ss.get('negative_prompt', '')
            )),
        })

    return {
        'contract_version': 'modec-v4',
        'items': normalized,
        'shots': normalized,
        'merged_full_prompts': merged_full_prompts,
    }

if __name__ == '__main__':
    args = sys.argv[1:]
    require_provenance = '--require-provenance' in args
    args = [arg for arg in args if arg != '--require-provenance']
    if len(args) < 2:
        print('Usage: python3 merge_agent_outputs.py [--require-provenance] <output.json> <input1.json> [input2.json ...]')
        sys.exit(1)
    stats = merge_agent_outputs(args[0], *args[1:], require_provenance=require_provenance)
    if require_provenance and stats.get('invalid_provenance'):
        sys.exit(2)

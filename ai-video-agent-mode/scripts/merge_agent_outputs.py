# merge_agent_outputs.py — 合并多个 Agent 输出文件，去重 (by subshot_id)，验证完整性
# Usage: python3 merge_agent_outputs.py <output.json> <input1.json> <input2.json> ...
# Every agent writes its own file. This script merges them safely.

import hashlib, json, os, sys, time

sys.path.insert(0, os.path.dirname(__file__))
from record_batch_provenance import verify as verify_provenance
from pipeline_runtime import patch_only

def merge_agent_outputs(output_path, *input_paths, require_provenance=False):
    """Merge multiple agent JSON outputs into one, deduplicating by subshot_id."""
    seen = {}
    all_items = []
    stats = {
        'files': 0, 'total_from_files': 0, 'duplicates': 0, 'merged': 0,
        'invalid_provenance': 0, 'partial_subshots_excluded': 0,
    }
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
        if require_provenance and manifest.get('validation_mode') == 'partial':
            # A partial batch is evidence only for the records that passed its
            # validator. Failed records remain in the worker file for audit,
            # but must wait for their unique retry batch before public merge.
            allowed_subshots = set(manifest.get('validated_subshot_ids', []))
            original_count = len(items)
            items = [
                item for item in items
                if not isinstance(item, dict) or item.get('subshot_id') in allowed_subshots
            ]
            stats['partial_subshots_excluded'] += original_count - len(items)
        stats['files'] += 1
        stats['total_from_files'] += len(items)

        fields_by_main_shot = _patch_fields_for_batch(path, source_manifests[-1] if source_manifests else None)
        for item in items:
            sid = item.get('subshot_id', '')
            if not sid:
                all_items.append(item)
                continue
            if sid in seen:
                # Retry packets are appended after their original batch.  Keep the
                # verified replacement, rather than silently restoring stale work.
                stats['duplicates'] += 1
                fields = fields_by_main_shot.get(str(item.get('shot_id') or sid))
                all_items[seen[sid]] = patch_only(all_items[seen[sid]], item, fields) if fields else item
                continue
            seen[sid] = len(all_items)
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
            'contract_version': 'jimeng-t2v-v1',
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


def _patch_fields_for_batch(batch_path, manifest):
    """Read the immutable retry context associated with this verified batch."""
    packet_path = (manifest or {}).get('packet_path')
    if not packet_path or not os.path.exists(packet_path):
        return {}
    try:
        with open(packet_path, encoding='utf-8-sig') as handle:
            packet = json.load(handle)
        context_path = packet.get('retry_context_path')
        if not context_path or not os.path.exists(context_path):
            return {}
        with open(context_path, encoding='utf-8-sig') as handle:
            context = json.load(handle)
        return context.get('fields_by_main_shot', {}) if context.get('mode') == 'field_patch' else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def _build_prompt_package(items):
    """Build the merged Phase 6/7 package with one canonical shots array."""
    normalized = []
    for item in items:
        copied = dict(item)
        normalized.append(copied)

    return {
        'contract_version': 'jimeng-t2v-v1',
        'shots': normalized,
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

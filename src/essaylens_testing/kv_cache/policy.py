from __future__ import annotations

from essaylens_testing.config.schema import KVCacheConfig


def summarize_kv_cache(config: KVCacheConfig) -> dict[str, object]:
    return {
        "prompt_cache": config.prompt_cache,
        "cache_reuse": config.cache_reuse,
        "type_k": config.type_k,
        "type_v": config.type_v,
        "kv_offload": config.kv_offload,
        "slot_save_path": config.slot_save_path,
    }

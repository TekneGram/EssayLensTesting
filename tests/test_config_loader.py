from __future__ import annotations

import unittest

from essaylens_testing.config import parse_cli_overrides, resolve_profile


class ConfigLoaderTests(unittest.TestCase):
    def test_profile_resolution_applies_presets_in_order(self) -> None:
        resolved = resolve_profile(
            "essay-feedback",
            preset_names=["ctx-32k", "kv-turbo3"],
        )
        self.assertEqual(resolved.server.ctx_size, 32768)
        self.assertEqual(resolved.server.cache_type_k, "turbo3")
        self.assertEqual(resolved.server.cache_type_v, "turbo3")
        self.assertEqual(resolved.request.temperature, 0.0)

    def test_cli_overrides_take_final_precedence(self) -> None:
        overrides = parse_cli_overrides(
            [
                "server.ctx_size=4096",
                "request.temperature=0.6",
                "request.stop=END,STOP",
            ]
        )
        resolved = resolve_profile(
            "essay-feedback",
            preset_names=["ctx-32k"],
            cli_overrides=overrides,
        )
        self.assertEqual(resolved.server.ctx_size, 4096)
        self.assertEqual(resolved.request.temperature, 0.6)
        self.assertEqual(resolved.request.stop, ("END", "STOP"))


if __name__ == "__main__":
    unittest.main()

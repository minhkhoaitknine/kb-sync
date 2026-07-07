import os
import unittest
from unittest.mock import patch

from src.config import env_setting, provider_api_key


class ConfigTests(unittest.TestCase):
    def test_env_setting_treats_placeholders_as_missing(self) -> None:
        with patch.dict(os.environ, {"GEMINI_API_KEY": "your_gemini_api_key_here"}):
            self.assertIsNone(env_setting("GEMINI_API_KEY"))

        with patch.dict(os.environ, {"GEMINI_API_KEY": "..."}, clear=False):
            self.assertIsNone(env_setting("GEMINI_API_KEY"))

    def test_provider_api_key_uses_generic_api_key_for_active_provider(self) -> None:
        with patch.dict(os.environ, {"API_KEY": "real-key"}, clear=False):
            self.assertEqual(provider_api_key("gemini", "gemini"), "real-key")
            self.assertIsNone(provider_api_key("openai", "gemini"))


if __name__ == "__main__":
    unittest.main()

"""Keep tests isolated from the live display and user configuration."""

import os
import tempfile


_TEST_CONFIG = tempfile.TemporaryDirectory(prefix="night-light-by-ht-tests-")
os.environ["NIGHT_LIGHT_BY_HT_DISABLE_DISPLAY_BACKEND"] = "1"
os.environ["NIGHT_LIGHT_BY_HT_CONFIG_DIR"] = _TEST_CONFIG.name

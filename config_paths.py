"""Configuration location without creating files or importing the application."""
import os
from pathlib import Path


def config_directory():
    override=os.environ.get('NIGHT_LIGHT_BY_HT_CONFIG_DIR')
    if override:return Path(override)
    appdata=os.environ.get('APPDATA')
    return Path(appdata)/'NightLightWidget' if appdata else Path.home()/'.NightLightWidget'

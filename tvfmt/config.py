from configparser import ConfigParser
from enum import Enum
from pathlib import Path

import xdg.BaseDirectory as BaseDir
from tvfmt.globals import APP_NAME, console


class CliConfigKey(Enum):
    TRAKT_API_KEY = "trakt_api_key"
    AUTO = "auto"
    CONFIRM = "confirm"


class CliConfig:
    def __init__(self, config_name):
        self.config_dir = BaseDir.save_config_path(APP_NAME)
        self.config_name = config_name
        self.config_file = Path(self.config_dir) / config_name
        self._setup()
        self.parser = ConfigParser()
        self.parser.read(self.config_file)

    def _setup(self):
        if not self.config_file.exists():
            self.config_file.touch()
            parser = ConfigParser()
            parser.add_section(APP_NAME)
            parser.set(APP_NAME, "trakt_api_key", "")
            parser.set(APP_NAME, "auto", "False")
            parser.set(APP_NAME, "confirm", "True")
            with open(self.config_file, "w+") as f:
                parser.write(f)

    def get(self, key: CliConfigKey):
        return self.parser.get(APP_NAME, key.value)

    def set(self, key: CliConfigKey, value) -> bool:
        if key in [CliConfigKey.AUTO, CliConfigKey.CONFIRM]:
            if value.lower() not in ["true", "false"]:
                console.print(f"Config key '{key.value}' must be a boolean.")
                return False
        self.parser.set(APP_NAME, key.value, value)
        with open(self.config_file, "w+") as f:
            self.parser.write(f)
        return True

    def get_dir(self):
        return self.config_dir

    def get_file(self):
        return self.config_file

    def __str__(self):
        return f"trakt_api_key: {self.get(CliConfigKey.TRAKT_API_KEY)}\nconfirm: {self.get(CliConfigKey.CONFIRM)}\nauto: {self.get(CliConfigKey.AUTO)}"


cli_config = CliConfig("config.ini")

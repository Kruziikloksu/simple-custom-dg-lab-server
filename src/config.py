import os
import socket
import logging
import sys
import tomllib

default_config = """
[Misc]
PORT = 4503
RUN_TEMP_CLIENT = true
HEARTBEAT_INTERVAL = 30
LOG_TO_FILE = false
"""


def ensure_config():
    config_path = get_config_path()
    if not os.path.exists(config_path):
        with open(config_path, "w") as f:
            f.write(default_config)
        print(f"Create config file: {config_path}")


def get_config_path():
    base_path = get_base_path()
    return os.path.join(base_path, 'config.toml')


def get_base_path():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))


def load_toml_config():
    config_path = get_config_path()
    with open(config_path, "rb") as f:
        return tomllib.load(f)


ensure_config()
toml_config = load_toml_config().get("Misc", {})
RUN_TEMP_CLIENT = toml_config.get("RUN_TEMP_CLIENT", True)
WS_SERVER_HOST = "0.0.0.0"
WS_CLIENT_HOST = socket.gethostbyname(socket.gethostname())
WS_SERVER_PORT = toml_config.get("PORT", 4503)
HEARTBEAT_INTERVAL = toml_config.get("HEARTBEAT_INTERVAL", 30)
LOG_LEVEL = logging.DEBUG
LOG_TO_FILE = toml_config.get("LOG_TO_FILE", False)

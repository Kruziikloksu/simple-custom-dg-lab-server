import socket
import logging

RUN_TEMP_CLIENT = True
WS_SERVER_HOST = "0.0.0.0"
WS_CLIENT_HOST = socket.gethostbyname(socket.gethostname())
WS_SERVER_PORT = 4503
HEARTBEAT_INTERVAL = 30
LOG_LEVEL = logging.DEBUG
LOG_TO_FILE = True
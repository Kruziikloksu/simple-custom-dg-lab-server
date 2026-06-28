import logging
import os
import config
from datetime import datetime

try:
    import colorlog
except ImportError:
    colorlog = None


logger = logging.getLogger("custom_logger")
logger.setLevel(config.LOG_LEVEL)
logger.propagate = False

console_handler = logging.StreamHandler()
console_handler.setLevel(config.LOG_LEVEL)

log_format = '[%(levelname)s](%(asctime)s) %(message)s'
log_formatter = logging.Formatter(log_format)
if colorlog is not None:
    colorlog_format = '%(log_color)s' + log_format
    console_handler.setFormatter(colorlog.ColoredFormatter(
        fmt=colorlog_format,
        reset=True,
        log_colors={
            'DEBUG': 'blue',
            'INFO': 'white',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'bold_red',
        }
    ))
else:
    console_handler.setFormatter(log_formatter)

if not logger.handlers:
    logger.addHandler(console_handler)

if config.LOG_TO_FILE:
    base_path = config.get_base_path()
    log_directory = os.path.join(base_path, "logs")
    if not os.path.exists(log_directory):
        os.makedirs(log_directory)
    log_file_path = os.path.join(log_directory, f"{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log")
    file_handler = logging.FileHandler(log_file_path, encoding="utf-8")
    file_handler.setLevel(config.LOG_LEVEL)
    file_handler.setFormatter(logging.Formatter(log_format))
    logger.addHandler(file_handler)


def debug(msg): logger.debug(msg)
def info(msg): logger.info(msg)
def warning(msg): logger.warning(msg)
def error(msg): logger.error(msg)
def critical(msg): logger.critical(msg)

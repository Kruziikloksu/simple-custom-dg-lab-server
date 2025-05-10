import logging
import colorlog
import os
import config
from datetime import datetime


logger = logging.getLogger("custom_logger")
logger.setLevel(config.LOG_LEVEL)

console_handler = logging.StreamHandler()
console_handler.setLevel(config.LOG_LEVEL)

log_format = '[%(levelname)s](%(asctime)s) %(message)s'
log_formatter = logging.Formatter(log_format)
colorlog_format = '%(log_color)s' + log_format
color_formatter = colorlog.ColoredFormatter(
    fmt=colorlog_format,
    reset=True,
    log_colors={
        'DEBUG': 'blue',
        'INFO': 'white',
        'WARNING': 'yellow',
        'ERROR': 'red',
        'CRITICAL': 'bold_red',
    }
)
console_handler.setFormatter(color_formatter)
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

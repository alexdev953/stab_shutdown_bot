import logging
from logging.handlers import TimedRotatingFileHandler


LOGGER_NAME = 'Stab Shutdown'
LOGGER_FMT = '%(asctime)s [%(process)d] %(name)s - %(levelname)s - %(module)s.%(funcName)s - %(message)s'
LOGGER_TIME_FMT = '[%d-%m-%Y %H:%M:%S]'
LOGGER_FILE_NAME = 'logger.log'

LOGGER_LEVEL = logging.INFO

logger = logging.getLogger(LOGGER_NAME)
logger.setLevel(LOGGER_LEVEL)
formatter = logging.Formatter(LOGGER_FMT, LOGGER_TIME_FMT)

console_log = logging.StreamHandler()
console_log.setFormatter(formatter)
logger.addHandler(console_log)

file_log = TimedRotatingFileHandler(LOGGER_FILE_NAME, when='d', backupCount=10, encoding='utf-8')
file_log.setFormatter(formatter)
logger.addHandler(file_log)

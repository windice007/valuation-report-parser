# coding=utf-8

"""
日志默认输出到程序运行当前目录下的 log 目录，系统自动创建目录结构
日志分为四个级别进行记录，分别是 info, error, warn, debug

"""

import sys
import logging


def init_logger():
    default_logger = logging.getLogger()
    if default_logger.hasHandlers():
        return default_logger

    instance = logging.Logger("User")
    instance.setLevel(logging.INFO)
    fmt = logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s")
    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(fmt)
    instance.addHandler(handler)

    # logDate = datetime.datetime.now().strftime('%Y%m%d')
    # logPath = 'logs'

    # if (not os.path.exists(logPath)):
    #     os.makedirs(logPath)

    # fileHandler = logging.handlers.RotatingFileHandler('%s/log_%s.log' % (
    #     logPath, logDate), mode='a', maxBytes=1024 * 1024 * 50, backupCount=100, encoding='utf-8', delay=0)
    # fileHandler.setFormatter(fmt)
    # instance.addHandler(fileHandler)
    return instance


logger = init_logger()

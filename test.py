import logging
import os
import sys

formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')


def setup_logger(name, log_file, level=logging.INFO):

    def decorate_emit(fn):
        def new(*args):
            levelno = args[0].levelno
            if(levelno >= logging.CRITICAL):
                color = '\x1b[31;1m'
            elif(levelno >= logging.ERROR):
                color = '\x1b[31;1m'
            elif(levelno >= logging.WARNING):
                color = '\x1b[33;1m'
            elif(levelno >= logging.INFO):
                color = '\x1b[32;1m'
            elif(levelno >= logging.DEBUG):
                color = '\x1b[35;1m'
            else:
                color = '\x1b[0m'
            # add colored *** in the beginning of the message
            args[0].msg = "{0}***\x1b[0m {1}".format(color, args[0].msg)

            # new feature i like: bolder each args of message
            args[0].args = tuple('\x1b[1m' + arg + '\x1b[0m' for arg in args[0].args)
            return fn(*args)
        return new

    """To setup as many loggers as you want"""
    logFormatter = logging.Formatter("[%(asctime)s] [%(process)-s-%(processName)-s] [%(levelname)-s]  %(message)s")
    handler = logging.FileHandler(log_file)
    handler.setFormatter(logFormatter)
    consoleHandler = logging.StreamHandler(sys.stdout)
    consoleHandler.setFormatter(logFormatter)
    consoleHandler.emit = decorate_emit(consoleHandler.emit)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)
    logger.addHandler(consoleHandler)

    return logger

# first file logger
logger = setup_logger('first_logger', 'first_logfile.log')
logger.info("This is just info message")

# second file logger
super_logger = setup_logger('second_logger', 'second_logfile.log')
super_logger.error('This is an error message')

def another_method():
   # using logger defined above also works here
   logger.info('Inside method')
# # import logging
# # import os
# # import sys
# #
# # formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
# #
# #
# # def setup_logger(name, log_file, level=logging.INFO):
# #
# #     def decorate_emit(fn):
# #         def new(*args):
# #             levelno = args[0].levelno
# #             if(levelno >= logging.CRITICAL):
# #                 color = '\x1b[31;1m'
# #             elif(levelno >= logging.ERROR):
# #                 color = '\x1b[31;1m'
# #             elif(levelno >= logging.WARNING):
# #                 color = '\x1b[33;1m'
# #             elif(levelno >= logging.INFO):
# #                 color = '\x1b[32;1m'
# #             elif(levelno >= logging.DEBUG):
# #                 color = '\x1b[35;1m'
# #             else:
# #                 color = '\x1b[0m'
# #             # add colored *** in the beginning of the message
# #             args[0].msg = "{0}***\x1b[0m {1}".format(color, args[0].msg)
# #
# #             # new feature i like: bolder each args of message
# #             args[0].args = tuple('\x1b[1m' + arg + '\x1b[0m' for arg in args[0].args)
# #             return fn(*args)
# #         return new
# #
# #     """To setup as many loggers as you want"""
# #     logFormatter = logging.Formatter("[%(asctime)s] [%(process)-s-%(processName)-s] [%(levelname)-s]  %(message)s")
# #     handler = logging.FileHandler(log_file)
# #     handler.setFormatter(logFormatter)
# #     consoleHandler = logging.StreamHandler(sys.stdout)
# #     consoleHandler.setFormatter(logFormatter)
# #     consoleHandler.emit = decorate_emit(consoleHandler.emit)
# #
# #     logger = logging.getLogger(name)
# #     logger.setLevel(level)
# #     logger.addHandler(handler)
# #     logger.addHandler(consoleHandler)
# #
# #     return logger
# #
# # # first file logger
# # logger = setup_logger('first_logger', 'first_logfile.log')
# # logger.info("This is just info message")
# #
# # # second file logger
# # super_logger = setup_logger('second_logger', 'second_logfile.log')
# # super_logger.error('This is an error message')
# #
# # def another_method():
# #    # using logger defined above also works here
# #    logger.info('Inside method')
#
# # =========================================================================================
#
# import threading
#
#
# results = []
# def adder(res: list):
#     res.append('5')
#
# def creator(a, threads, results):
#     for i in range(a):
#         results.append(0)
#         t = threading.Thread(target=adder, args=(a, results, i))
#         threads.append(t)
#         t.start()
#     for t in threads:
#         t.join()
#
# # threads = []
#
#
# # mainThread = threading.Thread(target=creator, args=(5, threads, results))
# # mainThread.start()
# # mainThread.join()
# # for i in range(len(results)):
# #     print(results[i])
# #     print(threads[i])
#
#     # ==============================
# threads = []
# for i in range(5):
#     t = threading.Thread(target=adder, args=(results,))
#     threads.append(t)
# for i in threads:
#     i.start()
# for i in threads:
#     i.join()
# print(results)
# from concurrent.futures import ThreadPoolExecutor
# from itertools import repeat
#
# def worker_process(i):
#     return i * i # square the argument
#
# def process_result(future):
#     print(future.result())
import requests


def main():
    # def step(index, i):
    #     print(f"I am inside process new step {index};;;{i}")
    #
    # def process_new_task(task):
    #     print(f"kek {str(range(1, 3))}")
    #     #     now we need to find if this fuse supports needed task
    #     # change status of task with unique name to in progress
    #     with ThreadPoolExecutor() as executor:
    #         # [executor.map(step, [i, i+1]) for i in range(1, 3)]
    #         # executor.map(step, (range(1, 3)))
    #         for result in executor.map(step, repeat(5), range(1, 3)):
    #             pass
    #     for n in range(3):
    #         print(f"below print {n}")
    #
    #
    # process_new_task(None)
    d = {'key' : 'value'}
    v = None.update(d)
    print(v)

    # print(x)

if __name__ == '__main__':
    main()
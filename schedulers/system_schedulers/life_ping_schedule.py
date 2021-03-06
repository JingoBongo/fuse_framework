import __init__
import schedule
import time
import utils.general_utils as g
from utils import constants as c
import os
import requests
from utils import logger_utils as log

from utils import db_utils

# DO NOT IMPORT. (his file) !@!!!!!!

root_path = c.root_path
config = g.config

SYS_SERVICES_TABLE_NAME = c.sys_services_table_name
BUSINESS_SERVICES_TABLE_NAME = c.business_services_table_name
cur_file_name = os.path.basename(__file__)
log.get_log(c.life_ping_schedule_name)
# c.current_subprocess_logger = log






# def print_c(text):
#     # print(f"[{cur_file_name}] {str(text)}")
#     c.current_subprocess_logger.info(f"[{cur_file_name}] {str(text)}")

# TODO, implement gevent here. or grequests? for now i understand gevent better
def ping_one(port):
    try:
        r = requests.patch(f"http://localhost:{port}{c.life_ping_endpoint_context}").status_code
        if r:
            return 'alive'
    except Exception as e:
        # print_c(e)
        log.info(e)
        return 'dead'


def process_one_service(n):
    # n['status'] = 'dead'
    if n['status'] == 'dead':
        # define if is sys service
        # do other things anyway
        g.get_rid_of_service_by_pid(n['pid'])
        # print_c(f"before life ping init start services")

        if n['name'] in config['services']['system'].keys():
            g.init_start_service_procedure(n['name'], sys=True)
            return
            # for key in config['services']['system'].keys():
            #     if key == n['name']:
            #         g.init_start_service_procedure(key, sys=True)
            #         return
            #     break
        if n['name'] in config['services']['business'].keys():
            g.init_start_service_procedure(n['name'], sys=False)
            return
            # for key in config['services']['business'].keys():
            #     if key == n['name']:
            #         g.init_start_service_procedure(key, sys=False)
            #         return
        # print_c(f"before life ping init start services")
        log.error(f"Tried to revive '{n['name']}' but it was not found in config services lists")


def process_service_statuses(services_and_statuses):
    for n in services_and_statuses:
        try:
            process_one_service(n)
        except Exception as e:
            log.error(f"Failed to properly process service {n['name']}, pid {n['pid']}, port {n['port']}, status {n['status']}")
            log.error(e)


def job():
    log.info("Scheduled life_ping task started..")
    services = g.db_utils.select_from_table(SYS_SERVICES_TABLE_NAME) + g.db_utils.select_from_table(
        BUSINESS_SERVICES_TABLE_NAME)
    services_and_statuses = []
    for i in services:
        service_status = ping_one(i.port)
        # print('PID ' + str(i.pid))
        services_and_statuses.append({'name': i.name, 'port': i.port, 'pid': i.pid, 'status': service_status})
        if not i.status == service_status:
            db_utils.change_service_status_by_pid(i.pid, service_status)
        short_name = i.name.split('\\')[-1]
        log.info(f"Endpoint {short_name} (localhost:{i.port}) is {service_status}")
    process_service_statuses(services_and_statuses)
    log.info("Scheduled life_ping task finished")


# schedule.every(15).seconds.do(job)
schedule.every(1).minute.do(job)

try:
    while True:
        schedule.run_pending()
        time.sleep(1)
except:
    log.error(f"{c.life_ping_schedule_name} loop exited")

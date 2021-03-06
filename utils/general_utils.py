import logging

import __init__
import shutil
import socket

import json
import os
import psutil
import utils.read_from_yaml as yaml_utils
import sys
import utils.subprocess_utils as custom_subprocess
from utils import db_utils as db_utils
from utils import constants as c
from utils import logger_utils as log

db_name = 'main_db.db'
cur_file_name = os.path.basename(__file__)
config = yaml_utils.read_from_yaml(c.root_path + c.conf_path)
busy_ports_json_path = c.root_path + config['general']['busy_ports_json_file']
tasks_json_path = c.root_path + config['general']['tasks_json_file']
debug = config['general']['debug']
host = config['general']['host']
sql_engine_path = c.sql_engine_path


# def print_c(text):
#     # print(f"[{cur_file_name}] {str(text)}")
#     c.current_subprocess_logger.info(f"[{cur_file_name}] {str(text)}")


def run_cmd_command(command):
    # print_c(f'triggering command :{command}')
    log.info(f'triggering command :{command}')
    returned_value = os.system(command)
    # print_c(f'returned value: {returned_value}')
    log.info(f'returned value: {returned_value}')


def read_from_json(path):
    try:
        with open(path) as json_file:
            return json.load(json_file)
    except Exception as e:
        # print_c(f'Something went horribly wrong when attempted to read from file "{path}"')
        # print_c(e)
        log.exception(f'Something went horribly wrong when attempted to read from file "{path}"')
        log.exception(e)
        return {}


def write_to_json(path, text):
    try:
        with open(path, 'w') as outfile:
            json.dump(text, outfile)
    except Exception as e:
        # print_c(f'Something went horribly wrong when attempted to write into file "{path}" this specific text "{text}"')
        # print_c(e)
        log.exception(
            f'Something went horribly wrong when attempted to write into file "{path}" this specific text "{text}"')
        log.exception(e)


def clear_busy_ports():
    new_json = {"busy_ports": []}
    write_to_json(busy_ports_json_path, new_json)
    log.info('Busy ports file cleared')

def clear_tasks_file():
    new_json = {"tasks": []}
    write_tasks_to_json_file(new_json)
    log.info('Tasks file cleared')


def reserve_ports_from_config():
    busy_ports_json = read_from_json(busy_ports_json_path)
    # busy_ports_json['busy_ports'].append(str(port))
    for service in config['services']['system']:
        if 'port' in config['services']['system'][service].keys():
            busy_ports_json['busy_ports'].append(str(config['services']['system'][service]['port']))
    for service in config['services']['business']:
        if 'port' in config['services']['business'][service].keys():
            busy_ports_json['busy_ports'].append(str(config['services']['business'][service]['port']))
    write_to_json(busy_ports_json_path, busy_ports_json)
    log.info('Ports from config were reserved')


def delete_port_from_list(port):
    new_json = read_from_json(busy_ports_json_path)
    new_json['busy_ports'].remove(str(port))
    write_to_json(busy_ports_json_path, new_json)
    log.info(f"Port {port} was deleted from ports file")

def read_from_tasks_json_file():
    new_json = read_from_json(tasks_json_path)
    return new_json

def write_tasks_to_json_file(body):
    write_to_json(tasks_json_path, body)
    log.info(f"Updated tasks file")


def set_port_busy(port):
    busy_ports_json = read_from_json(busy_ports_json_path)
    if not str(port) in busy_ports_json['busy_ports']:
        busy_ports_json['busy_ports'].append(str(port))
        write_to_json(busy_ports_json_path, busy_ports_json)
        log.info(f"Set port {port} as busy")
    else:
        log.info(f"Did not set port {port} as busy")


#         TODO for some reason for predefined ports it says that it didnt set them busy, but  it does it
#               maybe it does it before


def set_environment_variable(param, param1):
    os.environ[param] = str(param1)


def kill_process(pid):
    try:
        p = psutil.Process(int(pid))
        p.terminate()  # or p.kill()
    except:
        # print_c(f"Tried to kill process {pid}, it appears to be dead already")
        log.info(f"Tried to kill process {pid}, it appears to be dead already")


def get_rid_of_service_by_pid(pid):
    try:
        kill_process(pid)
        port_to_delete = db_utils.get_service_port_by_pid(pid)
        db_utils.delete_process_from_tables_by_pid(pid)
        delete_port_from_list(port_to_delete)
        # print_c(f"Got rid of service with pid {pid} on port {port_to_delete}")
        log.info(f"Got rid of service with pid {pid} on port {port_to_delete}")
        return 'removed service'
    except Exception as e:
        # print_c(e)
        log.exception(e)
        return 'failed to remove service'


def get_rid_of_service_by_pid_and_port_dirty(pid):
    try:
        kill_process(pid)
        # print_c(f"Got rid of service with pid {pid} dirty")
        log.info(f"Got rid of service with pid {pid} dirty")
        return 'removed service'
    except Exception as e:
        # print_c(e)
        log.exception(e)
        return 'failed to remove service dirty'


def start_service(service_short_name, service_full_path, port, local=False, host=host):
    local_part = ['-local', str(local)]
    port_part = ['-port', str(port)]
    local_process = custom_subprocess.start_service_subprocess(service_full_path, local_part, port_part,
                                                               service_short_name)
    # print_c(f"fuse added service to pool: {service_short_name}")
    # print_c(f"added path: {service_full_path}")
    log.info(f"fuse added service to pool: {service_short_name}")
    log.info(f"added path: {service_full_path}")
    return local_process


def check_port_is_in_use(port):
    # Check if this works at all.
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = False
    try:
        sock.bind(("0.0.0.0", port))
        result = True
    except:
        # print_c(f"{port} Port is in use")
        pass
    sock.close()
    return result


def get_free_port():
    port_start_ind = config['fuse']['first_port']
    port_end_ind = config['fuse']['last_port']
    busy_ports_json = read_from_json(busy_ports_json_path)

    for i in range(port_start_ind, port_end_ind + 1):
        str_port = str(i)
        if not (str_port in busy_ports_json['busy_ports']) and not check_port_is_in_use(str_port):
            log.info(f"Got new free port: {str_port}")
            return str_port


def check_file_exists(service_full_path):
    return os.path.exists(service_full_path)


def init_start_service_procedure(service, sys=False):
    # TODO. HERE must be checker if file path exists
    type = 'business'
    if sys:
        type = 'system'
    service_full_path = c.root_path + config['services'][type][service]['path']
    if not check_file_exists(service_full_path):
        log.error(f"Service '{service}' has no existing file in path '{service_full_path}")
        return

    if 'port' in config['services'][type][service].keys() and isinstance(config['services'][type][service]['port'],
                                                                         int) and config['services'][type][service][
        'port'] > 0:
        port = config['services'][type][service]['port']
    else:
        port = get_free_port()
    set_port_busy(port)

    if 'local' in config['services'][type][service].keys():
        local = config['services'][type][service]['local']
    else:
        local = None

    if 'mono' in config['services'][type][service].keys():
        spawn_type = config['services'][type][service]['mono']
    else:
        spawn_type = None

    if spawn_type != "multi":
        if local:
            new_process = start_service(service, service_full_path, port, local=local)
        else:
            new_process = start_service(service, service_full_path, port)
    else:
        raise Exception('Implement multi endpoint stuff')
    if sys:
        db_utils.insert_into_sys_services(service, service_full_path, port, new_process.pid)
    else:
        db_utils.insert_into_business_services(service, service_full_path, port, new_process.pid)


def process_start_service(service_name):
    try:
        if len(config['services']['system']) > 0:
            if service_name in config['services']['system']:
                init_start_service_procedure(service_name, sys=True)
        # fire user endpoints
        if len(config['services']['business']) > 0:
            if service_name in config['services']['business']:
                init_start_service_procedure(service_name, sys=False)
        return 'service started'
    except Exception as e:
        # print_c(e)
        log.exception(e)
        return 'service failed to start'


def check_fuse_logger_file_is_current_logger(filepath):
    fuse_name = 'abobacadabra99912299939993999499959'
    for key in logging.root.manager.loggerDict.keys():
        if 'fuse-' + str(os.getpid()) in key:
            fuse_name = key
    if fuse_name == filepath:
        return True
    return False


def remove_folder_contents(folder):
    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)
        try:

            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
            log.info(f"Cleared contents of '{folder}' folder")
        except Exception as e:
        # print('Failed to delete %s. Reason: %s' % (file_path, e))
            log.exception('Failed to delete %s. Reason: %s' % (file_path, e))


def clear_log_folder():
    log_folder_name = c.root_path + 'resources//' + c.logs_folder_name
    remove_folder_contents(log_folder_name)


def recreate_log_foler_if_not_exists():
    log_folder_name = c.root_path + 'resources//' + c.logs_folder_name
    isExist = os.path.exists(log_folder_name)

    if not isExist:
        # Create a new directory because it does not exist
        os.makedirs(log_folder_name)
        # log.info(f"Recreated log folder")
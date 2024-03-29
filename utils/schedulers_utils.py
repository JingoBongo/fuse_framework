import __init__
import os
import re

from utils import db_utils, yaml_utils
from utils.dataclasses.module_metadata import ModuleMetadata
from utils.docstring_utils import get_docstring_from_readlines, parse_key_value_string
from utils.subprocess_utils import start_generic_subprocess
from utils import constants as c
from utils import logger_utils as log
from utils.taskmaster_utils import task_is_in_tasks

SYS_SERVICES_TABLE_NAME = c.sys_services_table_name
BUSINESS_SERVICES_TABLE_NAME = c.business_services_table_name


def launch_scheduler_if_not_exists(process_name, process_full_path):
    table_results = db_utils.select_from_table('Schedulers')
    table_results_names = [x['name'] for x in table_results]
    # TODO mention somewhere that schedulers are designed as singletones
    if process_name not in table_results_names:
        local_process = start_generic_subprocess(process_name, process_full_path)
        db_utils.insert_into_schedulers(process_name, process_full_path, local_process.pid)
        dic = {'pid': local_process.pid, 'pyfile_path': process_full_path, 'pyfile_name': process_name}
        db_utils.insert_into_table(c.all_processes_table_name, dic)
        log.info(f"Started '{process_name}' scheduler at pid '{local_process.pid}'")
    else:
        # TODO: if debug == true in config this happens, investigate
        log.warn(f"While launching endpoint with scheduler an attempt to add duplicate '{process_name}' was refused")


def launch_taskmaster_scheduler_if_not_exists():
    process_name = c.taskmaster_schedule_name
    process_full_path = f"{c.root_path}//{c.schedulers_folder_name}//{c.system_schedulers_folder_name}//{c.taskmaster_schedule_pyfile_name}"
    launch_scheduler_if_not_exists(process_name, process_full_path)


def launch_life_ping_scheduler_if_not_exists():
    process_name = c.life_ping_schedule_name
    process_full_path = f"{c.root_path}//{c.schedulers_folder_name}//{c.system_schedulers_folder_name}//{c.life_ping_schedule_pyfile_name}"
    launch_scheduler_if_not_exists(process_name, process_full_path)


def launch_route_harvester_scheduler_if_not_exists():
    process_name = c.route_harvester_schedule_name
    process_full_path = f"{c.root_path}//{c.schedulers_folder_name}//{c.system_schedulers_folder_name}//{c.route_harvester_schedule_pyfile_name}"
    launch_scheduler_if_not_exists(process_name, process_full_path)


def route_is_in_routes(route, routs_from_db):
    #     route and function_name, service_name, route
    for rroute in routs_from_db:
        if route['route'] == rroute['route'] and route['service_name'] == rroute['service_name'] \
                and route['function_name'] == rroute['function_name']:
            return True
    #           here we purely assume that duplicates do not exist in harvested route table
    # upd: they shouldn't, given all schedulers are singletons and must be designed as most robust code pieces of
    # the framework
    return False


def taskmaster_job_body():
    log.info(f"Scheduled {c.taskmaster_schedule_name} task started..")
    # TODO: This note is  of 11m/12d/2022. Tasks are saved in the corresponding table.
    #  We could catch the ones from old epoch there
    # This scheduler has 1 job for sure and second if I feel bored.
    # First is to catch all locally available task schemas, done
    # Second is to try to revive tasks from previous Fuse launch, not done

    # we need a list of supported tasks
    directory_to_iterate = c.root_path + yaml_utils.get_config()['general']['tasks_folder']
    supported_tasks = []
    for filename in os.listdir(directory_to_iterate):
        f = os.path.join(directory_to_iterate, filename)
        # checking if it is a file
        if os.path.isfile(f):
            supported_tasks.append({'task_full_path': f, 'task_name': f.split('/')[-1].split('\\')[-1].split('.')[0]})
    tasks_from_db = db_utils.select_from_table(c.taskmaster_tasks_types_table_name)

    # if there are tasks in db that are not valid, delete them from db
    for task in tasks_from_db:
        try:
            # if not route in routs_from_all_routes:
            if not task_is_in_tasks(task, supported_tasks):
                # delete rows with such tasks from db
                db_utils.delete_task_from_taskmaster_tasks_by_task_name(task['task_name'])
        except Exception as e:
            log.exception(f"Something went wrong while processing task(from db) {task}")
            log.exception(e)
    # 2. if route is in all_routes but not in db, add it (instead of add all below)
    for task in supported_tasks:
        try:
            if not task_is_in_tasks(task, tasks_from_db):
                # add to db
                db_utils.insert_into_table(c.taskmaster_tasks_types_table_name, task)
        except Exception as e:
            log.exception(f"Something went wrong while processing task(from files) {task}")
            log.exception(e)
    log.info(f"Taskmaster Tasks harvester finished job")


def module_metadata_harvester():
    # log.info("Scheduled module_metadata_harvester task started..")

    #     this task aims to update two tables, of local modules and of modules from repositories
    # scan local modules and update table
    endpoints_path = c.endpoints_path
    local_modules = []
    for root, dirs, files in os.walk(endpoints_path):
        for file in files:
            file_full_path = os.path.join(root, file)
            if file.endswith(".py"):
                with open(file_full_path, encoding='utf-8') as f:
                    docstring = get_docstring_from_readlines(f.readlines())
                    if not docstring or 'MDL_' not in docstring:
                        continue
                    metadata_dict = parse_key_value_string(docstring)
                    local_module = ModuleMetadata(metadata_dict, file_full_path)
                    local_modules.append(local_module)
    local_db_modules = db_utils.get_module_metadata_modules_objects_list(c.local_modules_table_name)
    for newly_found_module in local_modules:
        if not check_module_metadata_is_in_list(newly_found_module, local_db_modules):
            db_utils.insert_metadata_module_object(c.local_modules_table_name, newly_found_module)
    for existing_module in local_db_modules:
        if not check_module_metadata_is_in_list(existing_module, local_modules):
            db_utils.delete_rows_from_table_by_column(c.local_modules_table_name, 'py_file_name', 'String',
                                                      existing_module.module_file_name)



def check_module_metadata_is_in_list(module: ModuleMetadata, llist: list):
    for mod in llist:
        if module.module_file_name == mod.module_file_name:
            return True
    return False


# module_metadata_harvester()

# get repositories modules (with 1 new method for each repo preferably)
# and update local table

def route_harvester_job_body():
    log.info("Scheduled route_harvester task started..")
    services = db_utils.select_from_table(SYS_SERVICES_TABLE_NAME) + db_utils.select_from_table(
        BUSINESS_SERVICES_TABLE_NAME)
    # so we still get services from tables.
    # we need to update corresponding table tho.
    # so, table 'harvested route' with columns
    # service_name, function name, harvested route
    # for service_name, service_path from services work with file
    all_routes = []
    for service in services:
        try:
            service_path = service['path']
            service_name = service['name']
            log.debug(f"Harvesting {service_name} - {service_path}")
            with open(service_path) as py_file:
                lines = py_file.readlines()
                temp_routes = []
                for line in lines:
                    if line.startswith('@') and '.route(' in line:
                        try:
                            t_route = line.split("'")[1][1:]
                        except:
                            log.debug(f"While getting temp route, double quotes were found and managed")
                            t_route = line.split('"')[1][1:]

                        t_route = re.sub(r'<.+>', '<*>', t_route)
                        temp_routes.append(t_route)
                    if line.startswith('def'):
                        #  we caught all routes for func, add to all routes
                        function_name = line.split(' ')[1].split('(')[0]
                        for route in temp_routes:
                            try:
                                all_routes.append(
                                    {'service_name': service_name, 'function_name': function_name, 'route': route})
                            except:
                                log.exception(f"Tried to add {route} to all routes, it seems to be a ???")
                                log.exception(f"All routes until that exception: {all_routes}")
                        temp_routes = []
        except Exception as e:
            log.exception(f"What went wrong during processing {service['name']}?")
            log.exception(e)

    # insert harvested routes into db
    # 1. if route is in db but is not in all_routes, delete it
    harvested_routes_from_db = db_utils.select_from_table(c.harvested_routes_table_name)
    for route in harvested_routes_from_db:
        try:
            # if not route in routs_from_all_routes:
            if not route_is_in_routes(route, all_routes):
                # delete rows with such routes from db
                db_utils.delete_route_from_harvested_routes_by_route(route['route'])
        except Exception as e:
            log.exception(f"Something went wrong while processing route(from db) {route}")
            log.exception(e)
    # 2. if route is in all_routes but not in db, add it (instead of add all below)
    for route in all_routes:
        try:
            if not route_is_in_routes(route, harvested_routes_from_db):
                # add to db
                db_utils.insert_into_table(c.harvested_routes_table_name, route)
        except Exception as e:
            log.exception(f"Something went wrong while processing route(from pyfiles) {route}")
            log.exception(e)
    log.info(f"Route Harvester finished job")

import __init__
from itertools import repeat
import time
from pathlib import Path

from concurrent.futures import ThreadPoolExecutor
from utils import constants as c
from utils import logger_utils as log
from utils import db_utils as db
from utils.dataclasses.input_task import InputTask
from utils.dataclasses.task_from_file import TaskFromFile
from utils.dataclasses.task_step_from_file import TaskStepFromFile
from utils.general_utils import kill_process, init_start_function_process, init_start_function_thread, get_thread_result
from utils.pickle_utils import save_to_pickle, read_from_pickle
from utils import client_utils


def task_is_in_tasks(task, tasks_from_db):
    #     route and function_name, service_name, route
    for ttask in tasks_from_db:
        if task['task_full_path'] == ttask['task_full_path'] and task['task_name'] == ttask['task_name']:
            return True
    #           here we purely assume that duplicates do not exist in taskmaster_tasks_types_table_name table
    return False


def end_task_procedure(task: TaskFromFile, error_reason):
    is_thread = task.is_threaded
    log.error(f"Starting end task procedure for task {task.task_unique_name}")
    log.error(error_reason)

    Path(task.task_folder_path).mkdir(parents=True, exist_ok=True)
    log.debug(f"Created folder '{task.task_folder_path}' for the task")

    task.status = c.tasks_status_errored

    task_from_db = db.select_from_table_by_one_column(c.tasks_table_name, 'task_unique_name', task.task_unique_name,
                                                      'String')[0]
    # TODO: once again, instead of this select-delete-insert i'd like to have update. but it is janky now
    task_from_db = dict(task_from_db)
    task_from_db['status'] = c.tasks_status_errored
    db.delete_task_from_tasks_table_by_unique_task_name(task.task_unique_name)
    db.insert_into_table(c.tasks_table_name, task_from_db)

    task.error_logs = error_reason
    log.error(f"Exiting task {task.task_unique_name}, saving task fallback object")
    #     save pickle with task
    save_to_pickle(task.task_folder_path + c.double_forward_slash + c.tasks_errored_fallback_file_name, task)
    if not is_thread:
        # get pid of current process, first find it in db
        process_from_db = db.select_from_table_by_one_column(c.all_processes_table_name, 'function_name',
                                                             c.taskmaster_main_process_name + c.tasks_name_delimiter + task.task_unique_name,
                                                             'String')
        if not process_from_db or len(process_from_db) != 1:
            log.error(
                f"There were somehow more or none processes with this unique taskname {c.taskmaster_main_process_name + c.tasks_name_delimiter + task.task_unique_name}, aborting killing it by PID")
            return
        process_from_db = process_from_db[0]
        db.delete_process_from_tables_by_pid(process_from_db['pid'])
        kill_process(process_from_db['pid'])


def prepare_data_for_post_request(task, needed_keys):
    if needed_keys and len(needed_keys) > 0:
        provided_keys_from_init_requires = task['init_requires']
        for key in needed_keys:
            # also, I assume keys are both from init_requires and global_provides, not just from first?
            # if key not in provided_keys_from_init_requires.keys():
            if key not in provided_keys_from_init_requires.keys() or key not in task.global_provides.keys():
                end_task_procedure(task,
                                   f"Task {task['task_unique_name']} ended early as required {key} was not provided")
        needed_data = {}
        for key in needed_keys:
            # i think here we should update with new dict, not just value
            needed_data.update({key: task.global_provides[key]})
        return needed_data


def required_steps_arent_finished(required_steps, task: TaskFromFile):
    for step in required_steps:
        if step not in task.finished_steps:
            return True
    return False


def process_step(task: TaskFromFile, index):
    try:
        log.debug(f"I am inside process_step {index}")
        local_step: TaskStepFromFile = task.steps[index - 1]

        # sleep until needed steps are finished
        if local_step.requires_steps and isinstance(local_step.requires_steps, list):
            while required_steps_arent_finished(local_step.requires_steps, task):
                time.sleep(0.2)

        # grand note here. we don't need additional data and even check for it if we have a GET request
        # TO-DO: I forgot to implement "step getting data from requires or from provides" ;;;UPD: or I did not?
        # == prepare_data_for_post_request()
        data_for_post = None
        data_type = None
        if local_step.request_type == c.request_type_post:
            # needed_keys = local_step['requires'] try out how it works with below version
            needed_keys = local_step.requires
            data_for_post = prepare_data_for_post_request(task, needed_keys)
            data_type = {'Content-Type': 'application/json'}

        # we should be able to send request now. if we use post request, add content type json
        resp = client_utils.init_send_request(service=local_step.service, context=local_step.route,
                                              #   request_type=local_step.request_type, headers=headers, where to get headers?
                                              request_type=local_step.request_type,
                                              data=data_for_post, claimed_data_type=data_type)
        if len(local_step.needs_to_provide) > 0:
            local_dict = {}
            content_to_save = None
            if 'application/json' in resp.headers.get('Content-Type'):
                # major overlook here: I plan to specify step index in provides from taskmaster, so no need to modify keys
                for key in local_step.needs_to_provide:
                    content_to_save = {key: resp.json()[key]}
                    local_dict.update(content_to_save)

            elif isinstance(resp.content, dict):
                for key in local_step.needs_to_provide:
                    content_to_save = {key: resp.content[key]}
                    local_dict.update(content_to_save)

            elif isinstance(resp.content, str):
                if len(local_step.needs_to_provide) == 1:
                    key = local_step.needs_to_provide[0]
                    content_to_save = {key: resp.content}
                else:
                    end_task_procedure(task,
                                       "If response content type is string, step should only provide one key-value pair set in schema file")
            else:
                end_task_procedure(task, "Response body is not JSON, dict or string, what is that?")
            task.global_provides.update(content_to_save)
            save_to_pickle(
                task.task_folder_path + c.double_forward_slash + local_step.step_number + c.tasks_step_provides_delimiter + 'response',
                local_dict)
        task.finished_steps.append(local_step.step_number)
    except Exception as e:
        log.exception(f"Something went horribly wrong while trying to finish step {index}, aborting task.")
        end_task_procedure(task, e)


def change_db_task_status_to_in_progress(task_unique_name):
    # TODO: Thing is, I wanted to replace delete+ insert with update, but update isnt tested
    task_from_db = db.select_from_table_by_one_column(c.tasks_table_name, 'task_unique_name', task_unique_name,
                                                      'String')[0]
    task_from_db = dict(task_from_db)
    task_from_db['status'] = c.tasks_status_in_progress
    db.delete_task_from_tasks_table_by_unique_task_name(task_unique_name)
    db.insert_into_table(c.tasks_table_name, task_from_db)


def save_task_results_in_folder(task: TaskFromFile):
    Path(task.task_folder_path).mkdir(parents=True, exist_ok=True)
    log.debug(f"Created folder '{task.task_folder_path}' for the task")
    save_to_pickle(task.task_folder_path + c.double_forward_slash + c.tasks_global_provides_file_name,
                   task.global_provides)


def process_new_task(task: TaskFromFile):
    log.debug(f"Inside process_new_task (new thread/process)")
    is_thread = task.is_threaded

    init_start_function_thread(change_db_task_status_to_in_progress, task.task_unique_name)

    task.status = c.tasks_status_in_progress
    task.task_folder_path = c.temporary_files_folder_full_path + c.double_forward_slash + str(task.task_unique_name)

    with ThreadPoolExecutor(max_workers=len(task.steps)) as executor:
        for result in executor.map(process_step, repeat(task), range(1, len(task.steps) + 1)):
            pass
    save_to_folder_thread = None
    if len(task.global_provides) > 0:
        save_to_folder_thread = init_start_function_thread(save_task_results_in_folder, task)

    # we have all pickles we need, now update task status
    if task.status != c.tasks_status_errored and task.status != c.tasks_status_does_not_exist_locally:
        task.status = c.tasks_status_completed

    task_from_db = db.select_from_table_by_one_column(c.tasks_table_name, 'task_unique_name', task.task_unique_name,
                                                      'String')[0]
    task_from_db = dict(task_from_db)
    task_from_db['status'] = task.status
    task_from_db['task_folder_path'] = task.task_folder_path
    # TODO: third time, instead of dumb select-delete-insert i'd like to have update, but that method is janky and untested
    db.delete_task_from_tasks_table_by_unique_task_name(task.task_unique_name)
    db.insert_into_table(c.tasks_table_name, task_from_db)
    if len(task.global_provides) > 0:
        get_thread_result(save_to_folder_thread)
    log.info(f"Task {task.task_unique_name} finished execution with status {task.status}")

    if not is_thread:
        process_from_db = db.select_from_table_by_one_column(c.all_processes_table_name, 'function_name',
                                                             c.taskmaster_main_process_name + c.tasks_name_delimiter + task.task_unique_name,
                                                             'String')
        if not process_from_db or len(process_from_db) != 1:
            log.error(
                f"There were somehow more or none processes with this unique taskname "
                f"{c.taskmaster_main_process_name + c.tasks_name_delimiter + task.task_unique_name}, aborting killing it by PID")
            return
        process_from_db = process_from_db[0]
        db.delete_process_from_tables_by_pid(process_from_db['pid'])
#         Here, unlike end_task_procedure process isn't killed because the code to be executed finished anywah


def generate_task(task_type_from_db, task_obj, data) -> TaskFromFile:
    task_type_from_db = task_type_from_db[0]
    task: TaskFromFile = TaskFromFile(task_type_from_db['task_full_path'], task_obj.task_unique_name, data)
    return task


def generate_and_use_new_dict_task(task_obj) -> dict:
    c.on_start_unique_fuse_id = db.select_from_table_by_one_column(c.common_strings_table_name, 'key',
                                                                   c.on_start_unique_fuse_id_name,
                                                                   'String')[0]['value']
    new_dict_task: dict = {"task_name": task_obj.task_name, "task_unique_name": task_obj.task_unique_name,
                           c.on_start_unique_fuse_id_name: c.on_start_unique_fuse_id,
                           "status": c.tasks_status_new}

    db.insert_into_table(c.tasks_table_name, new_dict_task)
    return new_dict_task


def do_the_task(task_obj: InputTask, data):
    try:

        task_type_from_db = db.select_from_table_by_one_column(c.taskmaster_tasks_types_table_name,
                                                               "task_name",
                                                               task_obj.task_name,
                                                               "String")
        if len(task_type_from_db) == 1:
            # task_type_from_db = task_type_from_db[0]
            # task = TaskFromFile(task_type_from_db['task_full_path'], task_obj.task_unique_name, data)
            generate_task_thread = init_start_function_thread(generate_task, task_type_from_db, task_obj, data)

            # c.on_start_unique_fuse_id = db.select_from_table_by_one_column(c.common_strings_table_name, 'key',
            #                                                                c.on_start_unique_fuse_id_name,
            #                                                                'String')[0]['value']
            # new_dict_task = {"task_name": task_obj.task_name, "task_unique_name": task_obj.task_unique_name,
            #                  c.on_start_unique_fuse_id_name: c.on_start_unique_fuse_id,
            #                  "status": c.tasks_status_new}
            #
            # db.insert_into_table(c.tasks_table_name, new_dict_task)
            generate_and_use_new_dict_task_thread = init_start_function_thread(generate_and_use_new_dict_task, task_obj)

            task: TaskFromFile = get_thread_result(generate_task_thread)
            get_thread_result(generate_and_use_new_dict_task_thread)
            if not task.is_threaded:
                func_name = c.taskmaster_main_process_name + c.tasks_name_delimiter + task_obj.task_unique_name
                init_start_function_process(process_new_task, task,
                                            function_name=func_name)
                return
            init_start_function_thread(process_new_task, task)


        else:
            log.error(f"There are no such tasks (or too many somehow) supported by this Fuse.")
            log.error(f"Supported tasks: {db.select_from_table(c.taskmaster_tasks_types_table_name)}")
    except Exception as e:
        log.exception(f"Something went horribly wrong while trying to work with {task_obj.task_unique_name}")
        log.exception(e)

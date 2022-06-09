import __init__
from flask import Flask
from flasgger import Swagger
from utils import general_utils as g
from argparse import ArgumentParser

from utils.general_utils import get_rid_of_service_by_pid, process_start_service, \
    get_rid_of_service_by_pid_and_port_dirty
from utils.subprocess_utils import start_generic_subprocess

app = Flask(__name__)
swagger = Swagger(app)

@app.route('/schedulers/statuses')
def get_shedulers_list():
    """Shows list of schedulers. No arguments needed.
        ---
    responses:
      200:
           description: 99% caution
        """
    return str(g.db_utils.select_from_table('schedulers'))

@app.route('/services/statuses')
def get_services_list():
    """Shows list of services. No arguments needed.
        ---
    responses:
      200:
        description: 99% caution
        """
    return str(g.db_utils.select_from_table('Business_services') + g.db_utils.select_from_table('Sys_services'))


@app.route(f"{g.LIFE_PING_ENDPOINT_CONTEXT}", methods=['PATCH'])
def life_ping():
    return '{"status":"alive"}'


@app.route('/services/remove/<int:pid>')
def get_rid_of_service(pid):
    """Removes a service. provide with pid
    Be aware that this kills ANY process by PID, not only fuse's one
        ---
    responses:
      200:
        description: 99% caution
    """
    if isinstance(pid, int) and pid > 0:
        return get_rid_of_service_by_pid(pid)
    else:
        return "Input valid pid, please be aware that you can kill actual windows process"


@app.route('/services/remove-dirty/<int:pid>')
def remove_service_wrong(pid):
    """Removes a service 'dirty' to trigger life ping revival. provide with pid
        Be aware that this kills ANY process by PID, not only fuse's one
        ---
    responses:
      200:
        description: 99% caution
    """
    if isinstance(pid, int) and pid > 0:
        return get_rid_of_service_by_pid_and_port_dirty(pid)
    else:
        return "Input valid pid, please be aware that you can kill actual windows process"


@app.route('/services/start/<service_name>')
def start_service(service_name):
    """Starts a service. provide with service name from config..
            ---
        responses:
          200:
            description: 99% caution
        """
    return process_start_service(service_name)

def launch_life_ping_scheduler_if_not_exists(process_name, process_full_path):
    table_results = g.db_utils.select_from_table('Schedulers')
    table_results_names = [x['name'] for x in table_results]
    # if isinstance(table_results, list):
    if not process_name in table_results_names:
        local_process = start_generic_subprocess(process_name, process_full_path)
        g.db_utils.insert_into_schedulers(process_name, process_full_path, local_process.pid)
        print(f"Started '{process_name}' scheduler at pid '{local_process.pid}'")
    else:
        print(f"While launching life ping endpoint an attempt to add duplicate '{process_name}' was refused")
    # else:
    #     local_process = start_generic_subprocess(process_name, process_full_path)
    #     g.db_utils.insert_into_schedulers(process_name, process_full_path, local_process.pid)


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument('-port')
    parser.add_argument('-local')
    args = parser.parse_args()
    endpoint_port = args.port
    if args.local == "True":
        host = "127.0.0.1"
    else:
        host = g.host

    # TODO add logic with adding to schedulers db and checking if there is only one life ping
    process_name = "life_ping_schedule"
    process_full_path = f"{g.root_path}//schedulers//system_schedulers//life_ping_schedule.py"
    launch_life_ping_scheduler_if_not_exists(process_name, process_full_path)
    app.run(debug=g.debug, host=host, port=endpoint_port)

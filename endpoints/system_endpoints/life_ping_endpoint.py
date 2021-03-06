import __init__
from utils import general_utils as g
from argparse import ArgumentParser

from utils.flask_child import FuseNode
from utils.general_utils import get_rid_of_service_by_pid, process_start_service, \
    get_rid_of_service_by_pid_and_port_dirty
from utils.schedulers_utils import launch_scheduler_if_not_exists, launch_life_ping_scheduler_if_not_exists
from utils.subprocess_utils import start_generic_subprocess
from utils import constants as c
from utils import logger_utils as log

parser = ArgumentParser()
app = FuseNode(__name__, template_folder=c.root_path + c.templates_folder_name, arg_parser=parser)


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




if __name__ == "__main__":
    launch_life_ping_scheduler_if_not_exists()
    app.run()

import json

import __init__
from argparse import ArgumentParser

from utils.decorators.cors import crossdomain
from utils.flask_child import FuseNode
from utils import constants as c
from utils import logger_utils as log
from utils import db_utils

parser = ArgumentParser()
app = FuseNode(__name__, arg_parser=parser)


@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response


@crossdomain(origin='*')
@app.route('/select/<string:table_name>')
def select_from_table(table_name):
    """Select from given table, argument - table_name
        ---
    responses:
      200:
           description: 99% caution
        """
    try:
        return str(db_utils.select_from_table(table_name))
    except Exception as e:
        return {'msg': 'Something went horribly wrong while trying to select from ' + table_name,
                'status': 'error', 'exception': e}


def dict2htmltable(data):
    html = ''.join('<th>' + x + '</th>' for x in data[0].keys())
    for d in data:
        html += '<tr>' + ''.join('<td>' + x + '</td>' for x in d._mapping.values()) + '</tr>'
    return '<table border=1 class="stocktable" id="table1">' + html + '</table>'


@crossdomain(origin='*')
@app.route('/select_dict/<string:table_name>')
def select_from_table_return_dict(table_name):
    """Select from given table, argument - table_name
        ---
    responses:
      200:
           description: 99% caution
        """
    try:
        # return str(db_utils.select_from_table_ret_dict(table_name))
        return json.dumps(db_utils.select_from_table_ret_dict(table_name))
    except Exception as e:
        return {'msg': 'Something went horribly wrong while trying to select from ' + table_name,
                'status': 'error', 'exception': e}


@app.route('/clear/<string:table_name>')
def clear_table_from_contents(table_name):
    """Clear contents of a table, argument - table_name
        ---
    responses:
      200:
        description: 99% caution
        """
    try:
        db_utils.clear_table(table_name)
        return {'msg': 'success', 'status': 'ok'}
    except Exception as e:
        return {'msg': 'Something went horribly wrong while trying to clear ' + table_name,
                'status': 'error', 'exception': e}


if __name__ == "__main__":
    app.run()

from xNMS.controller import controller
from xNMS.custom import CustomApp  # noqa: F401
from xNMS.database import db
from xNMS.environment import env
from xNMS.forms import form_factory
from xNMS.server import server
from xNMS.variables import vs


def initialize():
    server.register_plugins()
    first_init = db._initialize(env)
    if env.detect_cli():
        return
    form_factory._initialize()
    controller._initialize(first_init)
    vs.set_template_context()


initialize()

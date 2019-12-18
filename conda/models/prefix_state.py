from logging import getLogger
from os.path import join
from json import loads
from collections import OrderedDict

from ..base.constants import PREFIX_STATE_FILE


log = getLogger(__name__)


class PrefixState(object):
    def __init__(self, prefix):
        state_file = join(prefix, PREFIX_STATE_FILE)
        with open(state_file, 'r') as f:
            prefix_state = loads(f.read(), object_pairs_hook=OrderedDict)
        self.env_vars = prefix_state.get('env_vars', {})
        self.isolate_env = prefix_state.get('isolate_env', False)

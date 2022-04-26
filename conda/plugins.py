from collections.abc import Iterable
from typing import Callable, List, NamedTuple, Optional, Tuple

import pluggy


_hookspec = pluggy.HookspecMarker('conda')
hookimp = pluggy.HookimplMarker('conda')

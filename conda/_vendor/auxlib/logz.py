# -*- coding: utf-8 -*-
from json import JSONEncoder
from logging import getLogger, INFO, Handler, Formatter, StreamHandler, DEBUG
from sys import stderr

log = getLogger(__name__)
root_log = getLogger()

DEBUG_FORMATTER = Formatter(
    "[%(levelname)s] [%(asctime)s.%(msecs)03d] %(process)d %(name)s:%(funcName)s(%(lineno)d):\n"
    "%(message)s\n",
    "%Y-%m-%d %H:%M:%S")

INFO_FORMATTER = Formatter(
    "[%(levelname)s] [%(asctime)s.%(msecs)03d] %(process)d %(name)s(%(lineno)d): %(message)s\n",
    "%Y-%m-%d %H:%M:%S")


def set_root_level(level=INFO):
    root_log.setLevel(level)


def attach_stderr(level=INFO):
    has_stderr_handler = any(handler.name == 'stderr' for handler in root_log.handlers)
    if not has_stderr_handler:
        handler = StreamHandler(stderr)
        handler.name = 'stderr'
        if level is not None:
            handler.setLevel(level)
        handler.setFormatter(DEBUG_FORMATTER if level == DEBUG else INFO_FORMATTER)
        root_log.addHandler(handler)
        return True
    else:
        return False


def detach_stderr():
    for handler in root_log.handlers:
        if handler.name == 'stderr':
            root_log.removeHandler(handler)
            return True
    return False


def initialize_logging(level=INFO):
    attach_stderr(level)


class NullHandler(Handler):
    def emit(self, record):
        pass


class DumpEncoder(JSONEncoder):
    def default(self, obj):
        if hasattr(obj, 'dump'):
            return obj.dump()
        # Let the base class default method raise the TypeError
        return super(DumpEncoder, self).default(obj)
_DUMPS = DumpEncoder(indent=2, ensure_ascii=False, sort_keys=True).encode


def jsondumps(obj):
    return _DUMPS(obj)


def fullname(obj):
    return obj.__module__ + "." + obj.__class__.__name__


def stringify(obj):
    name = fullname(obj)
    if name.startswith('bottle.'):
        builder = list()
        builder.append("{0} {1}{2} {3}".format(obj.method,
                                               obj.path,
                                               obj.environ.get('QUERY_STRING', ''),
                                               obj.get('SERVER_PROTOCOL')))
        builder += ["{0}: {1}".format(key, value) for key, value in obj.headers.items()]
        builder.append('')
        body = obj.body.read().strip()
        if body:
            builder.append(body)
            builder.append('')
        return "\n".join(builder)
    elif name == 'requests.models.PreparedRequest':
        builder = list()
        builder.append("{0} {1} {2}".format(obj.method, obj.path_url,
                                            obj.url.split(':')[0]))
        builder += ["{0}: {1}".format(key, value) for key, value in obj.headers.items()]
        builder.append('')
        if obj.body:
            builder.append(obj.body)
            builder.append('')
        return "\n".join(builder)

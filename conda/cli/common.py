from __future__ import absolute_import, division, print_function, unicode_literals

from contextlib import contextmanager
from functools import partial
from os.path import basename
import re
import sys

from ..base.constants import CONDA_TARBALL_EXTENSION, ROOT_ENV_NAME
from ..base.context import context, get_prefix as context_get_prefix
from ..common.compat import itervalues
from ..models.match_spec import MatchSpec

get_prefix = partial(context_get_prefix, context)


def ensure_use_local(args):
    if not args.use_local:
        return


def ensure_override_channels_requires_channel(args, dashc=True):
    if args.override_channels and not (args.channel or args.use_local):
        from ..exceptions import CondaValueError
        if dashc:
            raise CondaValueError('--override-channels requires -c/--channel'
                                  ' or --use-local')
        else:
            raise CondaValueError('--override-channels requires --channel'
                                  'or --use-local')


def confirm(args, message="Proceed", choices=('yes', 'no'), default='yes'):
    assert default in choices, default
    if args.dry_run:
        from ..exceptions import DryRunExit
        raise DryRunExit()

    options = []
    for option in choices:
        if option == default:
            options.append('[%s]' % option[0])
        else:
            options.append(option[0])
    message = "%s (%s)? " % (message, '/'.join(options))
    choices = {alt: choice
               for choice in choices
               for alt in [choice, choice[0]]}
    choices[''] = default
    while True:
        # raw_input has a bug and prints to stderr, not desirable
        sys.stdout.write(message)
        sys.stdout.flush()
        user_choice = sys.stdin.readline().strip().lower()
        if user_choice not in choices:
            print("Invalid choice: %s" % user_choice)
        else:
            sys.stdout.write("\n")
            sys.stdout.flush()
            return choices[user_choice]


def confirm_yn(args, message="Proceed", default='yes', exit_no=True):
    if args.dry_run:
        from ..exceptions import DryRunExit
        raise DryRunExit()
    if context.always_yes:
        return True
    try:
        choice = confirm(args, message=message, choices=('yes', 'no'),
                         default=default)
    except KeyboardInterrupt as e:
        from ..exceptions import CondaSystemExit
        raise CondaSystemExit("\nOperation aborted.  Exiting.", e)
    if choice == 'yes':
        return True
    if exit_no:
        raise SystemExit('Exiting\n')
    return False


def ensure_name_or_prefix(args, command):
    if not (args.name or args.prefix):
        from ..exceptions import CondaValueError
        raise CondaValueError('either -n NAME or -p PREFIX option required,\n'
                              'try "conda %s -h" for more details' % command)


def arg2spec(arg, json=False, update=False):
    try:
        # spec_from_line can return None, especially for the case of a .tar.bz2 extension and
        #   a space in the path
        _arg = spec_from_line(arg)
        if _arg is None:
            if arg.endswith(CONDA_TARBALL_EXTENSION):
                _arg = arg
            else:
                from ..exceptions import CondaValueError
                raise CondaValueError("Cannot construct MatchSpec from: %r" % None)
        spec = MatchSpec(_arg, normalize=True)
    except:
        from ..exceptions import CondaValueError
        raise CondaValueError('invalid package specification: %s' % arg)

    name = spec.name
    if not spec.is_simple() and update:
        from ..exceptions import CondaValueError
        raise CondaValueError("""version specifications not allowed with 'update'; use
    conda update  %s%s  or
    conda install %s""" % (name, ' ' * (len(arg) - len(name)), arg))

    return str(spec)


def specs_from_args(args, json=False):
    return [arg2spec(arg, json=json) for arg in args]


spec_pat = re.compile(r'''
(?P<name>[^=<>!\s]+)               # package name
\s*                                # ignore spaces
(
  (?P<cc>=[^=]+(=[^=]+)?)          # conda constraint
  |
  (?P<pc>(?:[=!]=|[><]=?).+)       # new (pip-style) constraint(s)
)?
$                                  # end-of-line
''', re.VERBOSE)


def strip_comment(line):
    return line.split('#')[0].rstrip()


def spec_from_line(line):
    m = spec_pat.match(strip_comment(line))
    if m is None:
        return None
    name, cc, pc = (m.group('name').lower(), m.group('cc'), m.group('pc'))
    if cc:
        return name + cc.replace('=', ' ')
    elif pc:
        return name + ' ' + pc.replace(' ', '')
    else:
        return name


def specs_from_url(url, json=False):
    from ..fetch import TmpDownload

    explicit = False
    with TmpDownload(url, verbose=False) as path:
        specs = []
        try:
            for line in open(path):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if line == '@EXPLICIT':
                    explicit = True
                if explicit:
                    specs.append(line)
                    continue
                spec = spec_from_line(line)
                if spec is None:
                    from ..exceptions import CondaValueError
                    raise CondaValueError("could not parse '%s' in: %s" %
                                          (line, url))
                specs.append(spec)
        except IOError as e:
            from ..exceptions import CondaFileIOError
            raise CondaFileIOError(path, e)
    return specs


def names_in_specs(names, specs):
    return any(spec.split()[0] in names for spec in specs)


def disp_features(features):
    if features:
        return '[%s]' % ' '.join(features)
    else:
        return ''


def stdout_json(d):
    import json
    from .._vendor.auxlib.entity import EntityEncoder
    json.dump(d, sys.stdout, indent=2, sort_keys=True, cls=EntityEncoder)
    sys.stdout.write('\n')


@contextmanager
def json_progress_bars(json=False):
    if json:
        from ..console import json_progress_bars
        with json_progress_bars():
            yield
    else:
        yield


def stdout_json_success(success=True, **kwargs):
    result = {'success': success}

    # this code reverts json output for plan back to previous behavior
    #   relied on by Anaconda Navigator and nb_conda
    unlink_link_transaction = kwargs.get('unlink_link_transaction')
    if unlink_link_transaction:
        from .._vendor.toolz.itertoolz import concat
        actions = kwargs.setdefault('actions', {})
        actions['LINK'] = tuple(str(d) for d in concat(
            stp.link_dists for stp in itervalues(unlink_link_transaction.prefix_setups)
        ))
        actions['UNLINK'] = tuple(str(d) for d in concat(
            stp.unlink_dists for stp in itervalues(unlink_link_transaction.prefix_setups)
        ))
    result.update(kwargs)
    stdout_json(result)


def handle_envs_list(acc, output=True):
    from .. import misc

    if output:
        print("# conda environments:")
        print("#")

    def disp_env(prefix):
        fmt = '%-20s  %s  %s'
        default = '*' if prefix == context.default_prefix else ' '
        name = (ROOT_ENV_NAME if prefix == context.root_prefix else
                basename(prefix))
        if output:
            print(fmt % (name, default, prefix))

    for prefix in misc.list_prefixes():
        disp_env(prefix)
        if prefix != context.root_prefix:
            acc.append(prefix)

    if output:
        print()

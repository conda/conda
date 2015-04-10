# (c) 2012-2015 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.
"""
Functions modifying conda configuration files (.condarc)
"""
from __future__ import print_function, division, absolute_import

import re
import os
from copy import deepcopy

import conda.config as config
from conda.utils import memoized

class CondaConfigError(Exception):
    pass

class CouldntParse(NotImplementedError, CondaConfigError):
    def __init__(self, reason):
        self.args = ["""Could not parse the yaml file. Use -f to use the
yaml parser (this will remove any structure or comments from the existing
.condarc file). Reason: %s""" % reason]


class ConfigValueError(ValueError, CondaConfigError):
    pass

class ConfigTypeError(TypeError, CondaConfigError):
    pass

class ConfigKeyError(TypeError, CondaConfigError):
    pass


def write_config(rc_path, add=(), get=None, set_=(), remove=(),
    remove_key=(), force=False, dry_run=False):
    # conda.cli.main_config imports yaml and gives an error to the user if it
    # is not installed, so keep this import inside the function.
    import yaml

    json_result = {'warnings': [], 'get': {}, 'result': []}

    # Create the file if it doesn't exist
    if not os.path.exists(rc_path):
        if add and 'channels' in list(zip(*add))[0] and not ['channels', 'defaults'] in add:
            # If someone adds a channel and their .condarc doesn't exist, make
            # sure it includes the defaults channel, or else they will end up
            # with a broken conda.
            rc_text = """\
channels:
  - defaults
"""
        else:
            rc_text = ""
    else:
        with open(rc_path, 'r') as rc:
            rc_text = rc.read()
    rc_config = yaml.load(rc_text)
    if rc_config is None:
        rc_config = {}

    # Get
    if get is not None:
        if not get:
            get = sorted(rc_config.keys())
        for key in get:
            if key not in config.rc_list_keys + config.rc_bool_keys:
                if key not in config.rc_other:
                    message = "unknown key %s" % key
                    json_result['warnings'].append(message)
                continue
            if key not in rc_config:
                continue

            json_result['get'][key] = rc_config[key]

            if isinstance(rc_config[key], bool):
                json_result['result'].append(' '.join(["--set", str(key), repr(rc_config[key])]))
            else:
                # Note, since conda config --add prepends, these are printed in
                # the reverse order so that entering them in this order will
                # recreate the same file
                for item in reversed(rc_config.get(key, [])):
                    # Use repr so that it can be pasted back in to conda config --add
                    json_result['result'].append(' '.join(["--add", str(key), repr(item)]))

            continue

    # PyYaml does not support round tripping, so if we use yaml.dump, it
    # will clear all comments and structure from the configuration file.
    # There are no yaml parsers that do this.  Our best bet is to do a
    # simple parsing of the file ourselves.  We can check the result at
    # the end to see if we did it right.

    # First, do it the pyyaml way
    new_rc_config = deepcopy(rc_config)

    # Add
    for key, item in add:
        if key not in config.rc_list_keys:
            raise ConfigValueError("key must be one of %s, not %r" %
                                  (config.rc_list_keys, key))
        if not isinstance(rc_config.get(key, []), list):
            raise CouldntParse("key %r should be a list, not %s." % (key,
                rc_config[key].__class__.__name__))
        if item in rc_config.get(key, []):
            # Right now, all list keys should not contain duplicates
            message = "Skipping %s: %s, item already exists" % (key, item)
            json_result['warnings'].append(message)
            continue
        new_rc_config.setdefault(key, []).insert(0, item)

    # Set
    for key, item in set_:
        yamlitem = yaml.load(item)
        if not isinstance(yamlitem, bool):
            raise ConfigTypeError("%r is not a boolean" % item)

        new_rc_config[key] = yamlitem

    # Remove
    for key, item in remove:
        if key not in new_rc_config:
            raise ConfigKeyError("key %r is not in the config file" % key)
        if item not in new_rc_config[key]:
            raise ConfigKeyError("%r is not in the %r key of the config file" % (item, key))
        new_rc_config[key] = [i for i in new_rc_config[key] if i != item]

    # Remove Key
    for key, in remove_key:
        if key not in new_rc_config:
            raise ConfigKeyError("key %r is not in the config file" % key)
        del new_rc_config[key]

    if force:
        # Note, force will also remove any checking that the keys are in
        # config.rc_keys
        if not dry_run:
            with open(rc_path, 'w') as rc:
                rc.write(yaml.dump(new_rc_config, default_flow_style=False))

        return json_result

    # Now, try to parse the condarc file.

    new_rc_text = rc_text[:].split("\n")

    for key, item in add:
        add_defaults = (key == 'channels' and ['channels', 'defaults'] not in
            add and 'channels' not in rc_config and 'defaults' not in
            new_rc_config['channels'])
        add_rc_key(key, item, new_rc_text, rc_config, add_defaults=add_defaults)
        if add_defaults:
            new_rc_config['channels'].append('defaults')

    for key, item in set_:
        set_rc_key(key, item, new_rc_text, rc_config)

    # These error messages propagate up to the conda config command, so we use
    # the command flags in the messages.
    for key, item in remove:
        raise NotImplementedError("--remove without --force is not implemented "
            "yet")

    for key, in remove_key:
        raise NotImplementedError("--remove-key without --force is not "
            "implemented yet")

    if add or set_:
        # Verify that the new rc text parses to the same thing as if we had
        # used yaml.
        try:
            parsed_new_rc_text = yaml.load('\n'.join(new_rc_text).strip('\n'))
        except yaml.parser.ParserError:
            raise CouldntParse("couldn't parse modified yaml")
        else:
            if not parsed_new_rc_text == new_rc_config:
                raise CouldntParse("modified yaml doesn't match what it "
                                   "should be")

    if add or set_:
        if not dry_run:
            with open(rc_path, 'w') as rc:
                rc.write('\n'.join(new_rc_text).strip('\n'))
                rc.write('\n')

    return json_result


@memoized
def listkeyregex(key):
    # Just support "   key:  " for now
    return re.compile(r"( *)%s *" % key)

@memoized
def setkeyregex(key):
    return re.compile(r"( *)%s( *):( *)" % key)

def add_rc_key(key, item, new_rc_text, rc_config, add_defaults=False):
    """
    Add

    key:
      - item

    to new_rc_text. new_rc_text should be a list of lines of the new rc
    file. It is modified in place. rc_config should be a yaml.load()
    dictionary of the base config. If add_defaults is True, the key 'defaults'
    will be appended to the key (it is recommended to set this if the key is
    'channels' and is being added for the first time).

    """
    if key not in config.rc_list_keys:
        raise ConfigValueError("key must be one of %s, not %s" %
                              (config.rc_list_keys, key))

    if item in rc_config.get(key, []):
        # Skip duplicates. See above
        return
    added = False
    for pos, line in enumerate(new_rc_text[:]):
        matched = listkeyregex(key).match(line)
        if matched:
            leading_space = matched.group(1)
            # TODO: Try to guess how much farther to indent the
            # item. Right now, it is fixed at 2 spaces.
            new_rc_text.insert(pos + 1, "%s  - %s" % (leading_space, item))
            added = True
    if not added:
        if key in rc_config:
            # We should have found it above
            raise CouldntParse("existing list key couldn't be found")
        # TODO: Try to guess the correct amount of leading space for the
        # key. Right now it is zero.
        new_rc_text += ['%s:' % key, '  - %s' % item]
        if add_defaults:
            new_rc_text += ['  - defaults']

def set_rc_key(key, item, new_rc_text, rc_config):
    """
    Set key: item in new_rc_text

    new_rc_text should be a list of lines of the new rc file. It is modified
    in place. rc_config should be a yaml.load() dictionary of the base
    config.
    """
    if key not in config.rc_bool_keys:
        raise ConfigValueError("Error key must be one of %s, not %s" %
                              (config.rc_bool_keys, key))
    added = False
    for pos, line in enumerate(new_rc_text[:]):
        matched = setkeyregex(key).match(line)
        if matched:
            leading_space = matched.group(1)
            precol_space = matched.group(2)
            postcol_space = matched.group(3)
            new_rc_text[pos] = '%s%s%s:%s%s' % (leading_space, key,
                precol_space, postcol_space, item)
            added = True
    if not added:
        if key in rc_config:
            raise CouldntParse("existing bool key couldn't be found")
        new_rc_text += ['%s: %s' % (key, item)]

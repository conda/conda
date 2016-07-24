# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from os import environ
from os import mkdir
from os.path import join
from pytest import raises
from shutil import rmtree
from tempfile import mkdtemp
from unittest import TestCase

from conda._vendor.auxlib.ish import dals
from conda.common.compat import (string_types, odict)
from conda.common.configuration import (Configuration, SequenceParameter, PrimitiveParameter,
                                        MapParameter, YamlRawParameter, load_raw_configs,
                                        ParameterFlag, ValidationError)
from conda.common.yaml import yaml_load

test_yaml_raw = {
    'file1': dals("""
        always_yes: no

        proxy_servers:
          http: taz
          https: sly
          s3: pepé

        channels_altname:
          - bugs
          - daffy
          - tweety
    """),
    'file2': dals("""
        always_yes: yes
        changeps1: no

        proxy_servers:
          http: marv
          https: sam

        channels:
          - porky
          - bugs
          - elmer
    """),
    'file3': dals("""
        always_yes_altname2: yes  #!important

        proxy_servers:
          http: foghorn  #!important
          https: elmer
          s3: porky

        channels:
          - wile   #!important
          - daffy
          - foghorn
    """),
    'file4': dals("""
        always_yes: yes  #!important
        changeps1: no  #!important

        proxy_servers:  #!important
          http: bugs
          https: daffy

        channels:  #!important
          - pepé
          - marv
          - sam
    """),
    'bad_boolean': "always_yes: yeah",
    'too_many_aliases': dals("""
        always_yes: yes
        always_yes_altname2: yes
    """),
    'not_an_int': "always_an_int: nope",
    'good_boolean_map': dals("""
        boolean_map:
          a_true: true
          a_yes: yes
          a_1: 1
          a_false: False
          a_no: no
          a_0: 0
    """),
    'bad_boolean_map': dals("""
        boolean_map:
          a_string: not true
          an_int: 2
          a_float: 1.2
          a_complex: 1+2j
    """),


}


class TestConfiguration(Configuration):
    always_yes = PrimitiveParameter(False, aliases=('always_yes_altname1', 'always_yes_altname2'))
    changeps1 = PrimitiveParameter(True)
    proxy_servers = MapParameter(string_types)
    channels = SequenceParameter(string_types, aliases=('channels_altname', ))

    always_an_int = PrimitiveParameter(0)
    boolean_map = MapParameter(bool)



def load_from_string_data(*seq):
    return odict((f, YamlRawParameter.make_raw_parameters(yaml_load(test_yaml_raw[f])))
                 for f in seq)


class ConfigurationTests(TestCase):

    def test_simple_merges_and_caching(self):
        config = TestConfiguration(load_from_string_data('file1', 'file2'))
        assert config.changeps1 is False
        assert config.always_yes is True
        assert config.channels == ('porky', 'bugs', 'elmer', 'daffy', 'tweety')
        assert config.proxy_servers == {'http': 'marv', 'https': 'sam', 's3': 'pepé'}

        config = TestConfiguration(load_from_string_data('file2', 'file1'))
        assert len(config._cache) == 0
        assert config.changeps1 is False
        assert len(config._cache) == 1
        assert config.always_yes is False
        assert len(config._cache) == 2
        assert config.always_yes is False
        assert config._cache['always_yes'] is False
        assert config.channels == ('bugs', 'daffy', 'tweety', 'porky', 'elmer')
        assert config.proxy_servers == {'http': 'taz', 'https': 'sly', 's3': 'pepé'}

    def test_default_values(self):
        config = TestConfiguration()
        assert config.channels == ()
        assert config.always_yes is False
        assert config.proxy_servers == {}
        assert config.changeps1 is True

    def test_env_var_config(self):
        def make_key(appname, key):
            return "{0}_{1}".format(appname.upper(), key.upper())
        appname = "myapp"
        test_dict = {}
        test_dict[make_key(appname, 'always_yes')] = 'yes'
        test_dict[make_key(appname, 'changeps1')] = 'false'

        try:
            environ.update(test_dict)
            assert 'MYAPP_ALWAYS_YES' in environ
            config = TestConfiguration(load_from_string_data('file1', 'file2'), appname)
            assert config.changeps1 is False
            assert config.always_yes is True
        finally:
            [environ.pop(key) for key in test_dict]

    def test_load_raw_configs(self):
        try:
            tempdir = mkdtemp()
            condarc = join(tempdir, '.condarc')
            condarcd = join(tempdir, 'condarc.d')
            f1 = join(condarcd, 'file1.yml')
            f2 = join(condarcd, 'file2.yml')
            not_a_file = join(tempdir, 'not_a_file')

            mkdir(condarcd)

            with open(f1, 'wb') as fh:
                fh.write(test_yaml_raw['file1'].encode('utf-8'))
            with open(f2, 'wb') as fh:
                fh.write(test_yaml_raw['file2'].encode('utf-8'))
            with open(condarc, 'wb') as fh:
                fh.write(test_yaml_raw['file3'].encode('utf-8'))
            search_path = [condarc, not_a_file, condarcd]

            raw_data = load_raw_configs(search_path)
            assert not_a_file not in raw_data
            assert 'valueflags' in repr(raw_data[f1])

            assert raw_data[condarc]['channels'].value[0] == "wile"
            assert raw_data[f1]['always_yes'].value == "no"
            assert raw_data[f2]['proxy_servers'].value['http'] == "marv"

            config = TestConfiguration.from_search_path(search_path)
            assert config.channels == ('wile', 'porky', 'bugs', 'elmer', 'daffy',
                                       'tweety', 'foghorn')

        finally:
            rmtree(tempdir, ignore_errors=True)

    def test_important_primitive_map_merges(self):
        config = TestConfiguration(load_from_string_data('file1', 'file3', 'file2'))
        assert config.changeps1 is False
        assert config.always_yes is True
        assert config.channels == ('wile', 'porky', 'bugs', 'elmer', 'daffy', 'foghorn', 'tweety')
        assert config.proxy_servers == {'http': 'marv', 'https': 'sam', 's3': 'porky'}

        config = TestConfiguration(load_from_string_data('file3', 'file2', 'file1'))
        assert config.changeps1 is False
        assert config.always_yes is True
        assert config.channels == ('wile', 'bugs', 'daffy', 'tweety', 'porky', 'elmer', 'foghorn')
        assert config.proxy_servers == {'http': 'taz', 'https': 'sly', 's3': 'pepé'}

        config = TestConfiguration(load_from_string_data('file4', 'file3', 'file1'))
        assert config.changeps1 is False
        assert config.always_yes is True
        assert config.proxy_servers == {'https': 'daffy', 'http': 'bugs'}

        config = TestConfiguration(load_from_string_data('file1', 'file4', 'file3', 'file2'))
        assert config.changeps1 is False
        assert config.always_yes is True
        assert config.proxy_servers == {'http': 'marv', 'https': 'sam', 's3': 'porky'}

        config = TestConfiguration(load_from_string_data('file1', 'file2', 'file3', 'file4'))
        assert config.changeps1 is False
        assert config.always_yes is True
        assert config.proxy_servers == {'https': 'daffy', 'http': 'bugs', 's3': 'porky'}

        config = TestConfiguration(load_from_string_data('file3', 'file1'))
        assert config.changeps1 is True
        assert config.always_yes is True
        assert config.proxy_servers == {'https': 'sly', 'http': 'taz', 's3': 'pepé'}

    def test_list_merges(self):
        pass

    def test_validation(self):
        config = TestConfiguration(load_from_string_data('bad_boolean'))
        raises(ValidationError, lambda: config.always_yes)

        config = TestConfiguration(load_from_string_data('too_many_aliases'))
        raises(ValidationError, lambda: config.always_yes)

        config = TestConfiguration(load_from_string_data('not_an_int'))
        raises(ValidationError, lambda: config.always_an_int)

        config = TestConfiguration(load_from_string_data('bad_boolean_map'))
        raises(ValidationError, lambda: config.boolean_map)

        config = TestConfiguration(load_from_string_data('good_boolean_map'))
        assert config.boolean_map['a_true'] is True
        assert config.boolean_map['a_yes'] is True
        assert config.boolean_map['a_1'] is True
        assert config.boolean_map['a_false'] is False
        assert config.boolean_map['a_no'] is False
        assert config.boolean_map['a_0'] is False

    def test_parameter(self):
        assert ParameterFlag.from_name('top') is ParameterFlag.top

    def test_validate_all(self):
        config = TestConfiguration(load_from_string_data('file1'))
        config.validate_all()

        config = TestConfiguration(load_from_string_data('bad_boolean_map'))
        raises(ValidationError, config.validate_all)

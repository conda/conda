# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function

from auxlib.ish import dals
from os import environ
from os import mkdir
from os.path import join
from shutil import rmtree
from tempfile import mkdtemp
from unittest import TestCase

from conda.utils import yaml_load
from condalib.common.compat import (string_types, odict)
from condalib.common.configuration import (Configuration, SequenceParameter, PrimitiveParameter,
                                           MapParameter, YamlRawParameter, load_raw_configs)
test_yaml_raw = {
    'file1': dals("""
        always_yes: no
        always_yes_altname1: yes

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
}


class TestConfiguration(Configuration):
    channels = SequenceParameter(string_types, aliases=('channels_altname', ))
    always_yes = PrimitiveParameter(False, aliases=('always_yes_altname1', 'always_yes_altname2'))
    proxy_servers = MapParameter(string_types)
    changeps1 = PrimitiveParameter(True)


# @contextmanager
# def load_from_string_data(*seq):
#     directory_name = mkdtemp()
#     def make_file_from_string(string):
#         # with NamedTemporaryFile() as fh:
#         #     fh.write(string.encode('utf-8'))
#         # fh = NamedTemporaryFile()
#         fh = mkstemp()
#         fh.write(string.encode('utf-8'))
#         # fh.seek(0)
#         # with open(fh.name, 'r') as f:
#         #     print(f.read())
#         return fh
#     return odict((f, YamlRawParameter.build(make_file_from_string(test_yaml_raw[f]))) for f in seq)

def load_from_string_data(*seq):
    return odict((f, YamlRawParameter.make_raw_parameters(yaml_load(test_yaml_raw[f])))
                 for f in seq)


class ConfigurationTests(TestCase):

    def test_simple_merges(self):
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

            mkdir(condarcd)

            with open(f1, 'w') as fh:
                fh.write(test_yaml_raw['file1'])
            with open(f2, 'w') as fh:
                fh.write(test_yaml_raw['file2'])
            with open(condarc, 'w') as fh:
                fh.write(test_yaml_raw['file3'])
            search_path = [condarc, condarcd]

            raw_data = load_raw_configs(search_path)

            assert raw_data[condarc]['channels'].value[0] == "wile"
            assert raw_data[f1]['always_yes'].value == "no"
            assert raw_data[f2]['proxy_servers'].value['http'] == "marv"

            config = TestConfiguration.from_search_path(search_path)
            assert config.channels == ('wile', 'porky', 'bugs', 'elmer', 'daffy',
                                       'tweety', 'foghorn')

        finally:
            rmtree(tempdir, ignore_errors=True)

    def test_important_merges(self):
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

    def test_list_merges(self):
        pass

    def test_validation(self):
        pass

    def test_validation(self):
        pass




#!/bin/bash

#module load anaconda conda-env

inotify-hookable \
    --watch-directories /home/jillian/projects/python/conda-env \
    --on-modify-command "python setup.py install"

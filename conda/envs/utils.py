import os


def prepend_env_path(env_path=None, excluded=None):
    paths = []
    if env_path:
        paths.append(env_path)
    if not excluded:
        excluded = [env_path, ]
    for path in os.getenv('PATH').split(os.pathsep):
        if not path in excluded:
            paths.append(path)
    return paths


def path_string(env_path=None, excluded=None):
    return os.pathsep.join(prepend_env_path(env_path=env_path,
                                            excluded=excluded))

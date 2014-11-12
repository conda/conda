import os


def prepend_env_path(env_path):
    paths = [env_path]
    for path in os.getenv('PATH').split(os.pathsep):
        if path != env_path:
            paths.append(path)
    return paths


def path_string(env_path):
    return os.pathsep.join(prepend_env_path(env_path))

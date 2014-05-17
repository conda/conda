HOST = "127.0.0.1"
PORT = 5007

def launch(notebook, server=None, env=None, args=None):
    """ launch the app view of the specified notebook, using a server.
        If the server is not specified, assume localhsot and (try to)
        start it.
    """

    import webbrowser
    from urllib import pathname2url
    from os.path import abspath, exists

    import ipyapp

    if not server:
        ipyapp.start_local_server(port=PORT)
        server = "http://{host}:{port}".format(host=HOST, port=PORT)

    if exists(notebook): # path to local file
        nbpath = "nbfile=" + pathname2url(abspath(notebook))
    elif notebook.isdigit(): # just digits, assume gist 
        nbpath = "gist=" + notebook
    else:
        nbpath = "nbapp=" + pathname2url(notebook)

    if args:
        args_str = "&" + "&".join(args)
    else:
        args_str = ""

    if env:
        env_str = "&" + env
    else:
        env_str = ""

    if channels:
        channels_str = "&" + ",".join(channels)
    else:
        channels_str = ""

    webbrowser.open("{prefix}/?{nbpath}{args_str}{env_str}{channels_str}".format(
        prefix=server,
        nbpath=nbpath,
        args_str=args_str,
        env_str=env_str,
        channels_str=channels_str
    )

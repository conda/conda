HOST = "127.0.0.1"
PORT = 5007

def launch(notebook,
        args=None,
        server=None,
        env=None,
        channels=None,
        output=None,
        view=False,
        mode="open",
        format=None):
    """ Launch the app view of the specified notebook, using a server.
        If the server is not specified, assume localhsot and (try to)
        start it.

        :param notebook: a notebook identifier (path, gist, name)
        :param args: input arguments to pass to the notebook
        :param server: (protocol, host, port) string specifying server
        :param env: environment to use for notebook app invocation
        :param channels: list of channels for server to use to find apps and deps
        :param output: specify a particular artifact to return from executed app
        :param view: view mode only (don't execute notebook, just render and return)
        :param mode: open (default) opens browser, fetch returns result on STDOUT
        :param format: allows specification of result format: html (default), pdf
    """

    from os.path import abspath, exists
    from urllib import urlencode
    import webbrowser
    import requests

    import ipyapp

    if not server:
        ipyapp.start_local_server(port=PORT)
        server = "http://{host}:{port}".format(host=HOST, port=PORT)

    urlargs = []

    if exists(notebook): # path to local file
        urlargs.append(('nbfile',abspath(notebook)))
    elif notebook.isdigit(): # just digits, assume gist 
        urlargs.append(('gist',notebook))
    else:
        urlargs.append(('nbapp',notebook))

    if args:
        urlargs.extend(arg.split("=") for arg in args)

    if env:
        urlargs.append(('env',env))

    if channels:
        urlargs.append(('channels',",".join(channels)))

    if view:
        urlargs.append(('view','t'))

    if output:
        urlargs.append(('output', output))

    if format:
        urlargs.append(('format', format))

    try:
        urlargs_str = urlencode(urlargs).replace("%2F","/")
    except ValueError:
        raise ValueError("launch arguments must be valid pairs, such as 'a=7'")

    url = "{prefix}/?{urlargs_str}".format(urlargs_str=urlargs_str)
    if mode == 'open':
        webbrowser.open(url)
    elif mode == 'fetch':
        r = requests.get(url)
        if r.status_code == 200:
            return r.text
        else:
            r.raise_for_status()

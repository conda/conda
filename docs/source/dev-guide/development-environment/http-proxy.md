(development_environment_http_proxy)=
# Setting up an HTTP Proxy

Conda supports usage of HTTP proxy servers via the [requests](https://docs.python-requests.org)
library. The following guide shows you how to set up an HTTP proxy server locally using
[docker](https://www.docker.com/) and [squid](http://www.squid-cache.org/).

## Requirements

Before following this guide, make sure that you have Docker and the `htpasswd` command
line tool installed.


## Creating our project files

First, we need to create a directory that will hold the files we are going to create:
`Dockerfile`, `squid.conf` and `htpasswd`.

```commandline
mkdir squid-proxy
```

After that, we create `squid.conf` in this folder with the following contents:

```
auth_param basic program /usr/lib/squid/digest_pw_auth /etc/squid/passwords
auth_param basic realm proxy
acl authenticated proxy_auth REQUIRED
http_access allow authenticated

# This can be any port you like; we have chosen 8118 for this guide
http_port 8118
```

Once that is created, we need to create our `passwords` file. We do that by using
`htpasswd`:

```commandline
htpassword -c passwords <username>
```

```{admonition} Note
`<username>` can be whatever username you would like to select.
```

The last step is creating the `Dockerfile` that will use the two files we have just created:

```dockerfile
FROM ubuntu/squid:latest

COPY squid.conf /etc/squid/squid.conf
COPY passwords /etc/squid/passwords
```

## Running the proxy server

Before running the container, we need to build it. That can be done with the following command:

```commandline
docker build . --tag squid-proxy
```

Note that we have added the tag `squid-proxy`, which we will use in the next command

Now that the container is built, we can run our proxy server with the following docker command:

```commandline
docker run --rm --publish 8118:8118 squid-proxy
```

The command above references the `squid-proxy` server tag that we used in the previous command
and also exposes the proxy to run on port 8118 which matches the values that we placed in the
`squid.conf` file.

## Using the proxy server

If everything worked correctly, you now have a proxy server running on port 8118. You can configure
conda to use this server by adding the following to your `.condarc`:

```yaml
proxy_servers:
  http: http://<username>:<password>@localhost:8118
  https: http://<username>:<passeword>@localhost:8118
```

Replace `<username>` and `<password>` with the values you selected while creating the `passwords` file.

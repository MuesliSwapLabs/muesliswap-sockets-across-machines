import os
import re
from urllib.parse import urlparse

from .types import LocalPath, SshPath, UrlPath


def parse_url_path_arg(arg):
    print(" |> Checking if arg is SSH-like")
    # Try to detect an SSH style URL
    pattern = "((?P<username>[^@]*)@)?(?P<hostname>[^:]*)(?P<port>[0-9]{1,7})?:(?P<path>.*)"
    if match := re.match(pattern, arg):
        return SshPath(
                user=match.group("username"),
                hostname=match.group("hostname"),
                path=match.group("path"),
                port=int(match.group("port")) if match.group("port") else 22
            )


    print(" |> Checking if arg is URL-like")
    # Try to detect an URL
    url = urlparse(arg)
    if url.netloc and not url.path:
        if not url.scheme:
            url = urlparse(f"http://{arg}")
        return UrlPath(
                hostname=url.hostname,
                port=url.port,
                path=url.path
            )

    print(" |> Falling back to path")
    # Fallback case: Local path to file
    return LocalPath(path=arg)

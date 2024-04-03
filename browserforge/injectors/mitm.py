import argparse
import base64
import re
import sys

import mitmproxy.http
from mitmproxy import ctx
from mitmproxy.tools.main import mitmdump


class Injector:
    """
    Injects a custom bootstrap script into responses.
    Works in javascript blobs within text/html responses and prepends to application/javascript.
    """

    def __init__(self, bootstrap) -> None:
        self.bootstrap = bootstrap
        ctx.log.info(f'Bootstrap loaded: {self.bootstrap}')

    def response(self, flow: mitmproxy.http.HTTPFlow) -> None:
        if flow.response is None:
            return
        if flow.response.content is None:
            return

        # Injecting into javascript blob
        if flow.response.headers.get('Content-Type', '').startswith('text/html'):
            html = flow.response.content.decode('utf-8', errors='replace')
            html = re.sub(
                r'(data:application/javascript;base64,)([\w+/=]+)', self.inject_bootstrap, html
            )
            flow.response.content = html.encode('utf-8')
        # Injecting into script
        elif flow.response.headers.get('Content-Type', '').startswith(
            'application/javascript'
        ) or flow.response.headers.get('Content-Type', '').startswith('text/javascript'):
            script = flow.response.content.decode('utf-8', errors='replace')
            script = f'{self.bootstrap}{script}'
            flow.response.content = script.encode('utf-8')

    def inject_bootstrap(self, match):
        """
        Injects the javascript code into a base64 encoded script
        """
        prefix = match.group(1)
        encoded_script = match.group(2)
        decoded_script = base64.b64decode(encoded_script).decode('utf-8', errors='replace')
        decoded_script = f'{self.bootstrap}{decoded_script}'
        encoded_script = base64.b64encode(decoded_script.encode('utf-8')).decode('utf-8')
        return prefix + encoded_script


def parse_args(args):
    # Create the argument parser
    parser = argparse.ArgumentParser(description='Start mitmproxy with custom bootstrap script.')
    # Define expected command-line arguments
    parser.add_argument('--bootstrap', required=True, help='Bootstrap code to inject')
    parser.add_argument('--port', type=int, required=True, help='Port number for mitmproxy')
    return parser.parse_args(args)


args = parse_args(sys.argv[1:])

if __name__ == '__main__':
    # Launch mitmdump on the curret file
    mitmdump(
        [
            '-p',
            str(args.port),
            '-s',
            __file__,
            '-q',
        ]
    )
else:
    # Add the injector addon
    addons = [Injector(base64.b64decode(args.bootstrap).decode())]

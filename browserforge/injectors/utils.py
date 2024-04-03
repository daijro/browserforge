import lzma
import socket
import subprocess
import sys
from base64 import b64encode
from pathlib import Path
from random import randrange
from typing import Dict, Optional, Set

import orjson

from browserforge.fingerprints import Fingerprint, FingerprintGenerator

UTILS_JS: Path = Path(__file__).parent / 'data/utils.js.xz'

request_headers: Set[str] = {
    'accept-encoding',
    'accept',
    'cache-control',
    'pragma',
    'sec-fetch-dest',
    'sec-fetch-mode',
    'sec-fetch-site',
    'sec-fetch-user',
    'upgrade-insecure-requests',
}


def only_injectable_headers(headers: Dict[str, str], browser_name: str) -> Dict[str, str]:
    """
    Some HTTP headers depend on the request (for example Accept (with values application/json, image/png) etc.).
    This function filters out those headers and leaves only the browser-wide ones.
    """
    filtered_headers = {k: v for k, v in headers.items() if k.lower() not in request_headers}

    # Chromium-based controlled browsers do not support `te` header.
    # Remove the `te` header if the browser is not Firefox
    if browser_name and 'firefox' not in browser_name.lower():
        if 'te' in filtered_headers:
            del filtered_headers['te']
        if 'Te' in filtered_headers:
            del filtered_headers['Te']

    return filtered_headers


def InjectFunction(fingerprint: Fingerprint) -> str:
    return InjectFunctionData(orjson.dumps(fingerprint).decode())


def InjectFunctionData(fingerprint: str) -> str:
    return f"""
    (()=>{{
        {utils_js()}

        const fp = {fingerprint};
        const {{
            battery,
            navigator: {{
                userAgentData,
                webdriver,
                ...navigatorProps
            }},
            screen: allScreenProps,
            videoCard,
            audioCodecs,
            videoCodecs,
            mockWebRTC,
        }} = fp;

        slim = fp.slim;
        const historyLength = {randrange(1, 6)};
        
        const {{
            outerHeight,
            outerWidth,
            devicePixelRatio,
            innerWidth,
            innerHeight,
            screenX,
            pageXOffset,
            pageYOffset,
            clientWidth,
            clientHeight,
            hasHDR,
            ...newScreen
        }} = allScreenProps;

        const windowScreenProps = {{
            innerHeight,
            outerHeight,
            outerWidth,
            innerWidth,
            screenX,
            pageXOffset,
            pageYOffset,
            devicePixelRatio,
        }};

        const documentScreenProps = {{
            clientHeight,
            clientWidth,
        }};

        runHeadlessFixes();
        if (mockWebRTC) blockWebRTC();
        if (slim) {{
            window['slim'] = true;
        }}
        overrideIntlAPI(navigatorProps.language);
        overrideStatic();
        if (userAgentData) {{
            overrideUserAgentData(userAgentData);
        }}
        if (window.navigator.webdriver) {{
            navigatorProps.webdriver = false;
        }}
        overrideInstancePrototype(window.navigator, navigatorProps);
        overrideInstancePrototype(window.screen, newScreen);
        overrideWindowDimensionsProps(windowScreenProps);
        overrideDocumentDimensionsProps(documentScreenProps);
        overrideInstancePrototype(window.history, {{ length: historyLength }});
        overrideWebGl(videoCard);
        overrideCodecs(audioCodecs, videoCodecs);
        overrideBattery(battery);
    }})()
    """


def utils_js() -> str:
    """
    Opens and uncompresses the utils.js file and returns it as a string
    """
    with lzma.open(UTILS_JS, 'rt') as f:
        return f.read()


def _fingerprint(
    fingerprint: Optional[Fingerprint] = None, fingerprint_options: Optional[Dict] = None
) -> Fingerprint:
    """
    Generates a fingerprint if one doesnt exist
    """
    if fingerprint:
        return fingerprint
    generator = FingerprintGenerator()
    return generator.generate(**(fingerprint_options or {}))


def NewPort() -> str:
    tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp.bind(('', 0))
    return str(tcp.getsockname()[1])


def WorkerBootstrap(data: str, browser_name: str) -> str:
    """
    Builds the bootstrap script for service workers
    """
    return f"""
    if (typeof WorkerGlobalScope !== 'undefined' && typeof self.navigator !== 'undefined') {{
        let navigatorData = {data};
        Object.keys(navigatorData).forEach(function(key) {{
            // Firefox does not support "deviceMemory"
            if (key === 'deviceMemory' && "{browser_name}" !== "chromium") {{ return; }}
            Object.defineProperty(self.navigator, key, {{ get: () => navigatorData[key] }});
        }});
    }};
    """


class MitmProxy:
    def __init__(
        self,
        fingerprint: Fingerprint,
        upstream_proxy: Optional[Dict[str, str]] = None,
        browser_name: str = 'chromium',
    ):
        if upstream_proxy:
            raise NotImplementedError('Proxies are not supported yet')
        self.fingerprint = fingerprint
        self.browser_name = browser_name
        self.process: Optional[subprocess.Popen] = None
        self._server: Optional[str] = None

    @property
    def server(self):
        if self._server is None:
            self.launch()
        return self._server

    def __enter__(self):
        self.launch()
        return self

    def __exit__(self):
        self.close()

    def close(self) -> None:
        if self.process is not None:
            self.process.kill()

    def launch(self) -> str:
        """
        Launches the mitm server
        """
        bootstrap = WorkerBootstrap(
            data=orjson.dumps(self.fingerprint.navigator).decode(),
            browser_name=self.browser_name,
        )
        port = NewPort()
        # Launch mitm.py with the bootstrap payload and new server port
        # trunk-ignore(bandit/B603)
        self.process = subprocess.Popen(
            [
                sys.executable,
                str(Path(__file__).parent / 'mitm.py'),
                '--port',
                port,
                '--bootstrap',
                b64encode(bootstrap.encode()).decode(),
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self._server = f'http://localhost:{port}'
        return self._server


def NotInstalled(*module_names):
    """
    Checks if any passed module name is not installed
    """
    import importlib.util

    return any(importlib.util.find_spec(name) is None for name in module_names)

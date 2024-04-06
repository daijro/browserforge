import lzma
from pathlib import Path
from random import randrange
from typing import Dict, Optional, Set

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
    return f"""
    (()=>{{
        {utils_js()}

        const fp = {fingerprint.dumps()};
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


def CheckIfInstalled(module_name: str):
    """
    Checks if a module is installed
    """
    import importlib.util

    return importlib.util.find_spec(module_name) is not None

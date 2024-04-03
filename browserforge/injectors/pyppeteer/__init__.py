from browserforge.injectors.utils import NotInstalled

if NotInstalled('pyppeteer', 'mitmproxy'):
    raise ImportError(
        'Please install all injection dependencies: `pip install browserforge[pyppeteer]`'
    )

from .injector import NewPage, launch

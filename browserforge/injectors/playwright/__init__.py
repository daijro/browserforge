from browserforge.injectors.utils import NotInstalled

if NotInstalled('playwright', 'mitmproxy'):
    raise ImportError(
        'Please install all injection dependencies: `pip install browserforge[playwright]`'
    )

from .async_api import AsyncInjectedBrowser, AsyncInjectedContext, AsyncInjector, AsyncNewContext
from .sync_api import NewContext, SyncInjectedBrowser, SyncInjectedContext, SyncInjector

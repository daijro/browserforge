from typing import Dict, Optional

from playwright.sync_api import Browser, BrowserContext, BrowserType

from browserforge.fingerprints import Fingerprint
from browserforge.injectors.utils import (
    InjectFunction,
    MitmProxy,
    _fingerprint,
    only_injectable_headers,
)

from .utils import _context_options

"""
All sync_api injectors
"""


class SyncInjectedContext:
    """Wrapper around Playwright's context that closes the mitm proxy as well"""

    def __init__(self, context: BrowserContext, mitm: MitmProxy):
        self.context = context
        self.mitm = mitm

    def close(self):
        # Close the context and mitm proxy
        self.context.close()
        self.mitm.close()

    def __getattr__(self, name):
        # Forwards to self.context
        return getattr(self.context, name)


class SyncInjectedBrowser:
    """
    Wrapper around Playwright's Browser that spawns injected contexts
    """

    def __init__(self, browser: Browser, upstream_proxy: Optional[Dict[str, str]]):
        self.browser = browser
        self.upstream_proxy = upstream_proxy

    def new_context(
        self,
        *args,
        fingerprint: Optional[Fingerprint] = None,
        fingerprint_options: Optional[Dict] = None,
        **kwargs,
    ):
        """
        Launches a new injected context
        """

        # Generate fingerprint
        fingerprint = _fingerprint(fingerprint, fingerprint_options)

        # Launch the mitm proxy
        mitm = MitmProxy(
            fingerprint=fingerprint,
            upstream_proxy=kwargs.pop('proxy', None) or self.upstream_proxy,
            browser_name=self.browser.browser_type.name,
        )
        server = mitm.launch()

        # Launch the new context with the mitm proxy
        context = NewContext(
            *args,
            **kwargs,
            browser=self.browser,
            fingerprint=fingerprint,
            proxy={'server': server},
            ignore_https_errors=True,
        )

        # Return the wrapped context
        return SyncInjectedContext(context=context, mitm=mitm)

    def __getattr__(self, name):
        # Forwards to self.browser
        return getattr(self.browser, name)


class SyncInjector:
    """
    Wrapper around Playwright's BrowserType class that injects a MitmProxy.

    Usage:
    >>> with sync_playwright() as p:
    ...     browser = SyncInjector(p.chromium).launch()
    ...     context = browser.new_context()
    """

    def __init__(self, browser_type: BrowserType) -> None:
        """
        Parameters:
            browser_type (BrowserType): The browser type to use. This can be firefox, chromium, or webkit.
        """
        self.browser_type = browser_type

    def launch(self, *args, **kwargs) -> SyncInjectedBrowser:
        """
        Launches a new injected browser.
        """

        # If a proxy was passed, save it for use as an upstream proxy in mitmproxy
        upstream_proxy: Optional[Dict[str, str]] = kwargs.pop('proxy', None)
        if upstream_proxy and upstream_proxy['server'] == 'http://per-context':
            upstream_proxy = None

        # Create the new Browser instance, replacing the proxy with http://per-context
        browser = self.browser_type.launch(*args, **kwargs, proxy={'server': 'http://per-context'})

        # Return a browser wrapper
        return SyncInjectedBrowser(browser=browser, upstream_proxy=upstream_proxy)

    def launch_persistent_context(self, *args, **kwargs) -> SyncInjectedContext:
        """
        Launches a new injected persistent context
        """
        raise NotImplementedError("Persistent contexts are not yet supported by the injector.")

    def __getattr__(self, name):
        # Forwards to self.browser_type
        return getattr(self.browser_type, name)


def NewContext(
    browser: Browser,
    fingerprint: Optional[Fingerprint] = None,
    fingerprint_options: Optional[Dict] = None,
    **context_options,
) -> BrowserContext:
    """
    Injects a sync_api Playwright context with a Fingerprint.

    Parameters:
        browser (Browser): The browser to create the context in
        fingerprint (Optional[Fingerprint]): The fingerprint to inject. If None, one will be generated
        fingerprint_options (Optional[Dict]): Options for the Fingerprint generator if `fingerprint` is not passed
        **context_options: Other options for the new context
    """
    fingerprint = _fingerprint(fingerprint, fingerprint_options)
    function = InjectFunction(fingerprint)

    # Build new context
    context = browser.new_context(**_context_options(fingerprint, context_options))

    # Set headers
    context.set_extra_http_headers(
        only_injectable_headers(fingerprint.headers, browser.browser_type.name)
    )

    # Dark mode
    context.on("page", lambda page: page.emulate_media(color_scheme='dark'))

    # Inject function
    context.add_init_script(function)

    return context

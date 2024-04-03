from typing import Dict, Optional

from playwright.async_api import Browser as AsyncBrowser
from playwright.async_api import BrowserContext as AsyncBrowserContext
from playwright.async_api import BrowserType as AsyncBrowserType

from browserforge.fingerprints import Fingerprint
from browserforge.injectors.utils import (
    InjectFunction,
    MitmProxy,
    _fingerprint,
    only_injectable_headers,
)

from .utils import _context_options

"""
All async_api injectors
"""


class AsyncInjectedContext:
    """Wrapper around Playwright's async context that closes the mitm proxy as well"""

    def __init__(self, context: AsyncBrowserContext, mitm: MitmProxy):
        self.context = context
        self.mitm = mitm

    async def close(self):
        # Close the context and mitm proxy
        await self.context.close()
        self.mitm.close()

    def __getattr__(self, name):
        # Forwards to self.context
        return getattr(self.context, name)


class AsyncInjectedBrowser:
    """Wrapper around Playwright's async Browser that spawns injected contexts"""

    def __init__(self, browser: AsyncBrowser, upstream_proxy: Optional[Dict[str, str]]):
        self.browser = browser
        self.upstream_proxy = upstream_proxy

    async def new_context(
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
        context = await AsyncNewContext(
            *args,
            **kwargs,
            browser=self.browser,
            fingerprint=fingerprint,
            proxy={'server': server},
            ignore_https_errors=True,
        )

        # Return the wrapped context
        return AsyncInjectedContext(context=context, mitm=mitm)

    def __getattr__(self, name):
        # Forwards to self.browser
        return getattr(self.browser, name)


class AsyncInjector:
    """
    Wrapper around Playwright's async BrowserType class that injects a MitmProxy.

    Usage:
    >>> async with async_playwright() as p:
    ...     browser = await AsyncInjector(p.chromium).launch()
    ...     context = await browser.new_context()
    """

    def __init__(self, browser_type: AsyncBrowserType) -> None:
        """
        Parameters:
            browser_type (AsyncBrowserType): The browser type to use. This can be firefox, chromium, or webkit.
        """
        self.browser_type = browser_type

    async def launch(self, *args, **kwargs) -> AsyncInjectedBrowser:
        """
        Launches a new injected browser.
        """

        # If a proxy was passed, save it for use as an upstream proxy in mitmproxy
        upstream_proxy: Optional[Dict[str, str]] = kwargs.pop('proxy', None)
        if upstream_proxy and upstream_proxy['server'] == 'http://per-context':
            upstream_proxy = None

        # Create the new Browser instance, replacing the proxy with http://per-context
        browser = await self.browser_type.launch(
            *args, **kwargs, proxy={'server': 'http://per-context'}
        )

        # Return a browser wrapper
        return AsyncInjectedBrowser(browser=browser, upstream_proxy=upstream_proxy)

    async def launch_persistent_context(self, *args, **kwargs) -> AsyncInjectedContext:
        """
        Launches a new injected persistent context
        """
        raise NotImplementedError("Persistent contexts are not yet supported by the injector.")

    def __getattr__(self, name):
        # Forwards to self.browser_type
        return getattr(self.browser_type, name)


async def AsyncNewContext(
    browser: AsyncBrowser,
    fingerprint: Optional[Fingerprint] = None,
    fingerprint_options: Optional[Dict] = None,
    **context_options,
) -> AsyncBrowserContext:
    """
    Injects an async_api Playwright context with a Fingerprint.

    Parameters:
        browser (AsyncBrowser): The browser to create the context in
        fingerprint (Optional[Fingerprint]): The fingerprint to inject. If None, one will be generated
        fingerprint_options (Optional[Dict]): Options for the Fingerprint generator if `fingerprint` is not passed
        **context_options: Other options for the new context
    """
    fingerprint = _fingerprint(fingerprint, fingerprint_options)
    function = InjectFunction(fingerprint)

    # Build new context
    context = await browser.new_context(**_context_options(fingerprint, context_options))

    # Set headers
    await context.set_extra_http_headers(
        only_injectable_headers(fingerprint.headers, browser.browser_type.name)
    )

    # Since there are no async lambdas, define a new async function for emulating dark scheme
    async def on_page(page):
        await page.emulate_media(color_scheme='dark')  # Dark mode

    context.on("page", on_page)

    # Inject function
    await context.add_init_script(function)

    return context

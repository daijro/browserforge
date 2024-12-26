from typing import Dict, Optional

from undetected_playwright.async_api import Browser as AsyncBrowser
from undetected_playwright.async_api import \
    BrowserContext as AsyncBrowserContext
from undetected_playwright.sync_api import Browser, BrowserContext

from browserforge.fingerprints import Fingerprint
from browserforge.injectors.utils import (InjectFunction, _fingerprint,
                                          only_injectable_headers)


async def AsyncNewContext(
    browser: AsyncBrowser,
    fingerprint: Optional[Fingerprint] = None,
    fingerprint_options: Optional[Dict] = None,
    **context_options,
) -> AsyncBrowserContext:
    """Injects an async_api Undetected-Playwright context with a Fingerprint.

    Parameters:
        browser (Browser): The browser to create the context in
        fingerprint (Optional[Fingerprint]): The fingerprint to inject. If None, one will be generated
        fingerprint_options (Optional[Dict]): Options for the Fingerprint generator if `fingerprint` is not passed
        **context_options: Other options for the new context
    """
    fingerprint = _fingerprint(fingerprint, fingerprint_options)
    function = InjectFunction(fingerprint)
    # Build new context
    context = await browser.new_context(**_context_options(fingerprint, context_options))
    # Set headers
    await context.set_extra_http_headers(only_injectable_headers(fingerprint.headers, browser.browser_type.name))

    # Since there are no async lambdas, define a new async function for emulating dark scheme
    async def on_page(page):
        await page.emulate_media(color_scheme='dark')

    # Dark mode
    context.on("page", on_page)

    # Inject function
    await context.add_init_script(function)

    return context


def NewContext(
    browser: Browser,
    fingerprint: Optional[Fingerprint] = None,
    fingerprint_options: Optional[Dict] = None,
    **context_options,
) -> BrowserContext:
    """Injects a sync_api Undetected-Playwright context with a Fingerprint.

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
    context.set_extra_http_headers(only_injectable_headers(fingerprint.headers, browser.browser_type.name))
    # Dark mode
    context.on("page", lambda page: page.emulate_media(color_scheme='dark'))

    # Inject function
    context.add_init_script(function)

    return context


def _context_options(
    fingerprint: Fingerprint,
    options: Dict,
):
    """Builds options for new context."""
    return {
        'user_agent': fingerprint.navigator.userAgent,
        'color_scheme': 'dark',
        'viewport': {
            'width': fingerprint.screen.width,
            'height': fingerprint.screen.height,
            **options.pop('viewport', {}),
        },
        'extra_http_headers': {
            'accept-language': fingerprint.headers['Accept-Language'],
            **options.pop('extra_http_headers', {}),
        },
        **options,
    }

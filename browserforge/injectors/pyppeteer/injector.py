import re
from typing import Dict, Optional

from pyppeteer.browser import Browser
from pyppeteer.page import Page

from browserforge.fingerprints import Fingerprint
from browserforge.injectors.utils import InjectFunction, _fingerprint, only_injectable_headers


async def NewPage(
    browser: Browser,
    fingerprint: Optional[Fingerprint] = None,
    fingerprint_options: Optional[Dict] = None,
) -> Page:
    """
    Injects a Pyppeteer browser object with a Fingerprint.

    Parameters:
        browser (Browser): The browser to create the context in
        fingerprint (Optional[Fingerprint]): The fingerprint to inject. If None, one will be generated
        fingerprint_options (Optional[Dict]): Options for the Fingerprint generator if `fingerprint` is not passed
    """
    fingerprint = _fingerprint(fingerprint, fingerprint_options)
    function = InjectFunction(fingerprint)
    # create a new page
    page = await browser.newPage()

    await page.setUserAgent(fingerprint.navigator.userAgent)

    # Pyppeteer does not support firefox, so we can ignore checks
    cdp_sess = await page.target.createCDPSession()
    await cdp_sess.send(
        'Page.setDeviceMetricsOverride',
        {
            'screenHeight': fingerprint.screen.height,
            'screenWidth': fingerprint.screen.width,
            'width': fingerprint.screen.width,
            'height': fingerprint.screen.height,
            'mobile': any(
                name in fingerprint.navigator.userAgent for name in ('phone', 'android', 'mobile')
            ),
            'screenOrientation': (
                {'angle': 0, 'type': 'portraitPrimary'}
                if fingerprint.screen.height > fingerprint.screen.width
                else {'angle': 90, 'type': 'landscapePrimary'}
            ),
            'deviceScaleFactor': fingerprint.screen.devicePixelRatio,
        },
    )
    await page.setExtraHTTPHeaders(only_injectable_headers(fingerprint.headers, 'chrome'))

    # Only set to dark mode if the Chrome version >= 76
    version = re.search('.*?/(\d+)[\d\.]+?', await browser.version())
    if version and int(version[1]) >= 76:
        await page._client.send(
            'Emulation.setEmulatedMedia',
            {'features': [{'name': 'prefers-color-scheme', 'value': 'dark'}]},
        )

    # Inject function
    await page.evaluateOnNewDocument(function)
    return page

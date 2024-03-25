import re
from dataclasses import dataclass
from typing import Dict, Optional, Union

from pyppeteer import launch as plaunch
from pyppeteer.browser import Browser as PBrowser
from pyppeteer.browser import BrowserContext as PBrowserContext
from pyppeteer.page import Page as PPage

from browserforge.fingerprints import Fingerprint
from browserforge.injectors.utils import (
    InjectFunction,
    MitmProxy,
    _fingerprint,
    only_injectable_headers,
)


async def launch(
    *args,
    fingerprint: Optional[Fingerprint] = None,
    fingerprint_options: Optional[Dict] = None,
    **kwargs,
):
    """
    Parameters:
        fingerprint (Optional[Fingerprint]): The fingerprint to inject. If None, one will be generated
        fingerprint_options (Optional[Dict]): Options for the Fingerprint generator if `fingerprint` is not passed
        *args: Arguments to pass to `pyppeteer.launch`
        **kwargs: Keyword arguments to pass to `pyppeteer.launch`
    """
    fingerprint = _fingerprint(fingerprint, fingerprint_options)
    mitm = MitmProxy(fingerprint)
    mitm.launch()

    browser = await plaunch(
        *args,
        **kwargs,
        args=(*kwargs.get('args', []), f'--proxy-server={mitm.server}'),
        ignoreHTTPSErrors=True,
    )
    return PyppeteerObject(browser, fingerprint, mitm)


@dataclass
class PyppeteerObject:
    obj: Union[PBrowser, PBrowserContext]
    fingerprint: Fingerprint
    mitm: Optional[MitmProxy] = None

    async def createIncognitoBrowserContext(self) -> PBrowserContext:
        """
        Creates a new incognito browser context with an injected MITM proxy
        """
        context = await self.obj.createIncognitoBrowserContext()
        return PyppeteerObject(context, self.fingerprint)

    async def newPage(
        self,
    ) -> PPage:
        """
        Creates a new page with an injected MITM proxy
        """
        return await NewPage(self.obj, self.fingerprint)

    async def close(self):
        """
        Closes the browser
        """
        await self.obj.close()
        if self.mitm:
            self.mitm.close()

    def __getattr__(self, name):
        # Forward to the object
        return getattr(self.obj, name)


async def NewPage(
    obj: Union[PBrowser, PBrowserContext],
    fingerprint: Optional[Fingerprint] = None,
    fingerprint_options: Optional[Dict] = None,
) -> PPage:
    """
    Injects a Pyppeteer browser object with a Fingerprint.

    Parameters:
        obj (Union[Browser, BrowserContext]): The browser/context to create the page in
        fingerprint (Optional[Fingerprint]): The fingerprint to inject. If None, one will be generated
        fingerprint_options (Optional[Dict]): Options for the Fingerprint generator if `fingerprint` is not passed
    """
    fingerprint = _fingerprint(fingerprint, fingerprint_options)
    function = InjectFunction(fingerprint)

    # Create a new page
    page = await obj.newPage()

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
    await page.setExtraHTTPHeaders(only_injectable_headers(fingerprint.headers, 'chromium'))

    # Only set to dark mode if the Chrome version >= 76
    if isinstance(obj, PBrowser):
        ver = await obj.version()
    else:
        ver = await obj.browser.version()

    version = re.search('.*?/(\d+)[\d\.]+?', ver)
    if version and int(version[1]) >= 76:
        await page._client.send(
            'Emulation.setEmulatedMedia',
            {'features': [{'name': 'prefers-color-scheme', 'value': 'dark'}]},
        )

    # Inject function
    await page.evaluateOnNewDocument(function)
    return page

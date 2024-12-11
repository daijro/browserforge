<h1 align="center">
    BrowserForge
</h1>

<p align="center">
    <a href="https://github.com/daijro/browserforge/blob/main/LICENSE">
        <img src="https://img.shields.io/github/license/daijro/browserforge.svg?color=yellow">
    </a>
    <a href="https://python.org/">
        <img src="https://img.shields.io/badge/python-3.8&#8208;3.12-blue">
    </a>
    <a href="https://pypi.org/project/browserforge/">
        <img alt="PyPI" src="https://img.shields.io/pypi/v/browserforge.svg?color=orange">
    </a>
    <a href="https://pepy.tech/project/browserforge">
        <img alt="PyPI" src="https://static.pepy.tech/badge/browserforge">
    </a>
    <a href="https://github.com/ambv/black">
        <img src="https://img.shields.io/badge/code%20style-black-black.svg">
    </a>
    <a href="https://github.com/PyCQA/isort">
        <img src="https://img.shields.io/badge/imports-isort-yellow.svg">
    </a>
    <a href="http://mypy-lang.org">
        <img src="http://www.mypy-lang.org/static/mypy_badge.svg">
    </a>
</p>

<h4 align="center">
    🎭 Intelligent browser header & fingerprint generator
</h4>

---

## What is it?

BrowserForge is a browser header and fingerprint generator that mimics the frequency of different browsers, operating systems, and devices found in the wild.

It is a reimplementation of [Apify's fingerprint-suite](https://github.com/apify/fingerprint-suite) in Python.

## Features

- Uses a Bayesian generative network to mimic actual web traffic
- Extremely fast runtime (0.1-0.2 miliseconds)
- Easy and simple for humans to use
- Extensive customization options for browsers, operating systems, devices, locales, and HTTP version
- Written with type safety

## Installation

```
pip install browserforge[all]
python -m browserforge update
```

The `[all]` extra will include optional libraries like orjson.

Use `python -m browserforge update` to fetch necessary model files. If the command is not run, files will be downloaded on the first import.

<hr width=50>

## Important Notice

> [!WARNING]
> As of BrowserForge 1.2.1, the model files are frozen to v2.1.58. Newer model files have been contaminated with SQL and CLI injection attacks.
> Please update to the latest version of BrowserForge.

<hr width=50>

## Usage

## Generating Headers

### Simple usage

```py
>>> from browserforge.headers import HeaderGenerator
>>> headers = HeaderGenerator()
>>> headers.generate()
{'sec-ch-ua': '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"', 'Sec-Ch-Ua-Mobile': '?0', 'Sec-Ch-Ua-Platform': '"Windows"', 'Upgrade-Insecure-Requests': '1', 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36', 'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7', 'Sec-Fetch-Site': '?1', 'Sec-Fetch-Mode': 'same-site', 'Sec-Fetch-User': 'document', 'Sec-Fetch-Dest': 'navigate', 'Accept-Encoding': 'gzip, deflate, br, zstd', 'Accept-Language': 'en-US;q=1.0'}
```

### Using with requests

Headers can be added to a session in [requests](https://github.com/psf/requests) (or similar libraries) by assigning them to the `headers` attribute:

```py
import requests
session = requests.Session()
# Set the session headers
session.headers = headers.generate()
```

<details>
<summary>Parameters for HeaderGenerator</summary>

```
Parameters:
    browser (Union[ListOrString, Iterable[Browser]], optional): Browser(s) or Browser object(s).
    os (ListOrString, optional): Operating system(s) to generate headers for.
    device (ListOrString, optional): Device(s) to generate the headers for.
    locale (ListOrString, optional): List of at most 10 languages for the Accept-Language header. Default is 'en-US'.
    http_version (Literal[1, 2], optional): Http version to be used to generate headers. Defaults to 2.
    strict (bool, optional): Throws an error if it cannot generate headers based on the input. Defaults to False.
```

</details>

<details>
<summary>Parameters for HeaderGenerator.generate</summary>

```
Generates headers using the default options and their possible overrides.

Parameters:
    browser (Optional[Iterable[Union[str, Browser]]], optional): Browser(s) to generate the headers for.
    os (Optional[ListOrString], optional): Operating system(s) to generate the headers for.
    device (Optional[ListOrString], optional): Device(s) to generate the headers for.
    locale (Optional[ListOrString], optional): Language(s) to include in the Accept-Language header.
    http_version (Optional[Literal[1, 2]], optional): HTTP version to be used to generate headers.
    user_agent (Optional[ListOrString], optional): User-Agent(s) to use.
    request_dependent_headers (Optional[Dict[str, str]], optional): Known values of request-dependent headers.
    strict (Optional[bool], optional): If true, throws an error if it cannot generate headers based on the input.
```

</details>

### Constraining headers

#### Single constraint

Set constraints for browsers by passing the optional strings below:

```py
headers = HeaderGenerator(
    browser='chrome',
    os='windows',
    device='desktop',
    locale='en-US',
    http_version=2
)
```

#### Multiple constraints

Set multiple constraints to select from. Options are selected based on their actual frequency in the wild:

```py
headers = HeaderGenerator(
    browser=('chrome', 'firefox', 'safari', 'edge'),
    os=('windows', 'macos', 'linux', 'android', 'ios'),
    device=('desktop', 'mobile'),
    locale=('en-US', 'en', 'de'),
    http_version=2
)
```

#### Browser specifications

Set specificiations for browsers, including version ranges and HTTP version:

```py
from browserforge.headers import Browser

browsers = [
    Browser(name='chrome', min_version=100, max_version=110),
    Browser(name='firefox', max_version=80, http_version=1),
    Browser(name='edge', min_version=95),
]
headers = HeaderGenerator(browser=browsers)
```

Note that all constraints passed into the `HeaderGenerator` constructor can be overridden by passing them into the `generate` method.

#### Generate headers given User-Agent

Headers can be generated given an existing user agent:

```py
>>> headers.generate(user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36')
```

Select from multiple User-Agents based on their frequency in the wild:

```py
>>> headers.generate(user_agent=(
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0'
))
```

<hr width=50>

## Generating Fingerprints

### Simple usage

Initialize FingerprintGenerator:

```py
from browserforge.fingerprints import FingerprintGenerator
fingerprints = FingerprintGenerator()
fingerprints.generate()
```

<details>
<summary>Parameters for FingerprintGenerator</summary>

```
Parameters:
    screen (Screen, optional): Screen constraints for the generated fingerprint.
    strict (bool, optional): Whether to raise an exception if the constraints are too strict. Default is False.
    mock_webrtc (bool, optional): Whether to mock WebRTC when injecting the fingerprint. Default is False.
    slim (bool, optional): Disables performance-heavy evasions when injecting the fingerprint. Default is False.
    **header_kwargs: Header generation options for HeaderGenerator
```

</details>

<details>
<summary>Parameters for FingerprintGenerator.generate</summary>

```
Generates a fingerprint and a matching set of ordered headers using a combination of the default options specified in the constructor and their possible overrides provided here.

Parameters:
    screen (Screen, optional): Screen constraints for the generated fingerprint.
    strict (bool, optional): Whether to raise an exception if the constraints are too strict.
    mock_webrtc (bool, optional): Whether to mock WebRTC when injecting the fingerprint. Default is False.
    slim (bool, optional): Disables performance-heavy evasions when injecting the fingerprint. Default is False.
    **header_kwargs: Additional header generation options for HeaderGenerator.generate
```

</details>

<details>
<summary>Example response</summary>

```
Fingerprint(screen=ScreenFingerprint(availHeight=784,
                                     availWidth=1440,
                                     availTop=25,
                                     availLeft=0,
                                     colorDepth=30,
                                     height=900,
                                     pixelDepth=30,
                                     width=1440,
                                     devicePixelRatio=2,
                                     pageXOffset=0,
                                     pageYOffset=0,
                                     innerHeight=0,
                                     outerHeight=718,
                                     outerWidth=1440,
                                     innerWidth=0,
                                     screenX=0,
                                     clientWidth=0,
                                     clientHeight=19,
                                     hasHDR=True),
            navigator=NavigatorFingerprint(userAgent='Mozilla/5.0 (Macintosh; '
                                                     'Intel Mac OS X 10_15_7) '
                                                     'AppleWebKit/537.36 '
                                                     '(KHTML, like Gecko) '
                                                     'Chrome/121.0.0.0 '
                                                     'Safari/537.36',
                                           userAgentData={'architecture': 'arm',
                                                          'bitness': '64',
                                                          'brands': [{'brand': 'Not '
                                                                               'A(Brand',
                                                                      'version': '99'},
                                                                     {'brand': 'Google '
                                                                               'Chrome',
                                                                      'version': '121'},
                                                                     {'brand': 'Chromium',
                                                                      'version': '121'}],
                                                          'fullVersionList': [{'brand': 'Not '
                                                                                        'A(Brand',
                                                                               'version': '99.0.0.0'},
                                                                              {'brand': 'Google '
                                                                                        'Chrome',
                                                                               'version': '121.0.6167.160'},
                                                                              {'brand': 'Chromium',
                                                                               'version': '121.0.6167.160'}],
                                                          'mobile': False,
                                                          'model': '',
                                                          'platform': 'macOS',
                                                          'platformVersion': '13.6.1',
                                                          'uaFullVersion': '121.0.6167.160'},
                                           doNotTrack=None,
                                           appCodeName='Mozilla',
                                           appName='Netscape',
                                           appVersion='5.0 (Macintosh; Intel '
                                                      'Mac OS X 10_15_7) '
                                                      'AppleWebKit/537.36 '
                                                      '(KHTML, like Gecko) '
                                                      'Chrome/121.0.0.0 '
                                                      'Safari/537.36',
                                           oscpu=None,
                                           webdriver=False,
                                           language='en-US',
                                           languages=['en-US'],
                                           platform='MacIntel',
                                           deviceMemory=8,
                                           hardwareConcurrency=10,
                                           product='Gecko',
                                           productSub='20030107',
                                           vendor='Google Inc.',
                                           vendorSub=None,
                                           maxTouchPoints=0,
                                           extraProperties={'globalPrivacyControl': None,
                                                            'installedApps': [],
                                                            'isBluetoothSupported': False,
                                                            'pdfViewerEnabled': True,
                                                            'vendorFlavors': ['chrome']}),
            headers={'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                     'Accept-Encoding': 'gzip, deflate, br',
                     'Accept-Language': 'en-US;q=1.0',
                     'Sec-Fetch-Dest': 'navigate',
                     'Sec-Fetch-Mode': 'same-site',
                     'Sec-Fetch-Site': '?1',
                     'Sec-Fetch-User': 'document',
                     'Upgrade-Insecure-Requests': '1',
                     'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X '
                                   '10_15_7) AppleWebKit/537.36 (KHTML, like '
                                   'Gecko) Chrome/121.0.0.0 Safari/537.36',
                     'sec-ch-ua': '"Not A(Brand";v="99", "Google '
                                  'Chrome";v="121", "Chromium";v="121"',
                     'sec-ch-ua-mobile': '?0',
                     'sec-ch-ua-platform': '"macOS"'},
            videoCodecs={'h264': 'probably', 'ogg': '', 'webm': 'probably'},
            audioCodecs={'aac': 'probably',
                         'm4a': 'maybe',
                         'mp3': 'probably',
                         'ogg': 'probably',
                         'wav': 'probably'},
            pluginsData={'mimeTypes': ['Portable Document '
                                       'Format~~application/pdf~~pdf',
                                       'Portable Document '
                                       'Format~~text/pdf~~pdf'],
                         'plugins': [{'description': 'Portable Document Format',
                                      'filename': 'internal-pdf-viewer',
                                      'mimeTypes': [{'description': 'Portable '
                                                                    'Document '
                                                                    'Format',
                                                     'enabledPlugin': 'PDF '
                                                                      'Viewer',
                                                     'suffixes': 'pdf',
                                                     'type': 'application/pdf'},
                                                    {'description': 'Portable '
                                                                    'Document '
                                                                    'Format',
                                                     'enabledPlugin': 'PDF '
                                                                      'Viewer',
                                                     'suffixes': 'pdf',
                                                     'type': 'text/pdf'}],
                                      'name': 'PDF Viewer'},
                                     {'description': 'Portable Document Format',
                                      'filename': 'internal-pdf-viewer',
                                      'mimeTypes': [{'description': 'Portable '
                                                                    'Document '
                                                                    'Format',
                                                     'enabledPlugin': 'Chrome '
                                                                      'PDF '
                                                                      'Viewer',
                                                     'suffixes': 'pdf',
                                                     'type': 'application/pdf'},
                                                    {'description': 'Portable '
                                                                    'Document '
                                                                    'Format',
                                                     'enabledPlugin': 'Chrome '
                                                                      'PDF '
                                                                      'Viewer',
                                                     'suffixes': 'pdf',
                                                     'type': 'text/pdf'}],
                                      'name': 'Chrome PDF Viewer'},
                                     {'description': 'Portable Document Format',
                                      'filename': 'internal-pdf-viewer',
                                      'mimeTypes': [{'description': 'Portable '
                                                                    'Document '
                                                                    'Format',
                                                     'enabledPlugin': 'Chromium '
                                                                      'PDF '
                                                                      'Viewer',
                                                     'suffixes': 'pdf',
                                                     'type': 'application/pdf'},
                                                    {'description': 'Portable '
                                                                    'Document '
                                                                    'Format',
                                                     'enabledPlugin': 'Chromium '
                                                                      'PDF '
                                                                      'Viewer',
                                                     'suffixes': 'pdf',
                                                     'type': 'text/pdf'}],
                                      'name': 'Chromium PDF Viewer'},
                                     {'description': 'Portable Document Format',
                                      'filename': 'internal-pdf-viewer',
                                      'mimeTypes': [{'description': 'Portable '
                                                                    'Document '
                                                                    'Format',
                                                     'enabledPlugin': 'Microsoft '
                                                                      'Edge '
                                                                      'PDF '
                                                                      'Viewer',
                                                     'suffixes': 'pdf',
                                                     'type': 'application/pdf'},
                                                                    'Document '
                                                                    'Format',
                                                     'enabledPlugin': 'Microsoft '
                                                                      'Edge '
                                                                      'PDF '
                                                                      'Viewer',
                                                     'suffixes': 'pdf',
                                                     'type': 'text/pdf'}],
                                      'name': 'Microsoft Edge PDF Viewer'},
                                     {'description': 'Portable Document Format',
                                      'filename': 'internal-pdf-viewer',
                                      'mimeTypes': [{'description': 'Portable '
                                                                    'Document '
                                                                    'Format',
                                                     'enabledPlugin': 'WebKit '
                                                                      'built-in '
                                                                      'PDF',
                                                     'suffixes': 'pdf',
                                                     'type': 'application/pdf'},
                                                    {'description': 'Portable '
                                                                    'Document '
                                                                    'Format',
                                                     'enabledPlugin': 'WebKit '
                                                                      'built-in '
                                                                      'PDF',
                                                     'suffixes': 'pdf',
                                                     'type': 'text/pdf'}],
                                      'name': 'WebKit built-in PDF'}]},
            battery={'charging': False,
                     'chargingTime': None,
                     'dischargingTime': 29940,
                     'level': 0.98},
            videoCard=VideoCard(renderer='ANGLE (Apple, ANGLE Metal Renderer: '
                                         'Apple M2 Pro, Unspecified Version)',
                                vendor='Google Inc. (Apple)'),
            multimediaDevices={'micros': [{'deviceId': '',
                                           'groupId': '',
                                           'kind': 'audioinput',
                                           'label': ''}],
                               'speakers': [{'deviceId': '',
                                             'groupId': '',
                                             'kind': 'audiooutput',
                                             'label': ''}],
                               'webcams': [{'deviceId': '',
                                            'groupId': '',
                                            'kind': 'videoinput',
                                            'label': ''}]},
            fonts=['Arial Unicode MS', 'Gill Sans', 'Helvetica Neue', 'Menlo']
            mockWebRTC: False,
            slim: False)
```

</details>

### Constraining fingerprints

#### Screen width/height

Constrain the minimum/maximum screen width and height:

```py
from browserforge.fingerprints import Screen

screen = Screen(
    min_width=100
    max_width=1280
    min_height=400
    max_height=720
)

fingerprints = FingerprintGenerator(screen=screen)
```

Note: Not all bounds need to be defined.

#### Browser specifications

`FingerprintGenerator` and `FingerprintGenerator.generate` inherit the same parameters from `HeaderGenerator`.

Because of this, user agents, browser specifications, device types, and operating system constrains can also be passed into `FingerprintGenerator.generate`.

Here is a usage example:

```py
fingerprint.generate(browser='chrome', os='windows')
```

<hr width=50>

## Injecting Fingerprints

> [!WARNING]
> Fingerprint injection in BrowserForge is deprecated. Please check out [Camoufox] instead.

BrowserForge is fully compatible with your existing Playwright and Pyppeteer code. You only have to change your context/page initialization.

### Playwright

#### Async API:

```py
# Import the AsyncNewContext injector
from browserforge.injectors.playwright import AsyncNewContext

async def main():
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch()
        # Create a new async context with the injected fingerprint
        context = await AsyncNewContext(browser, fingerprint=fingerprint)
        page = await context.new_page()
        ...
```

Replace `await browser.new_context` with `await AsyncNewContext` in your existing Playwright code.

<details>
<summary>Parameters for AsyncNewContext</summary>

```
Injects an async_api Playwright context with a Fingerprint.

Parameters:
    browser (Browser): The browser to create the context in
    fingerprint (Optional[Fingerprint]): The fingerprint to inject. If None, one will be generated
    fingerprint_options (Optional[Dict]): Options for the Fingerprint generator if `fingerprint` is not passed
    **new_context_options: Other options for the new context
```

</details>

#### Sync API:

```py
# Import the NewContext injector
from browserforge.injectors.playwright import NewContext

def main():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        # Create a new context with the injected fingerprint
        context = NewContext(browser, fingerprint=fingerprint)
        page = context.new_page()
        ...
```

Replace `browser.new_context` with `NewContext` in your existing Playwright code.

<details>
<summary>Parameters for NewContext</summary>

```
Injects a sync_api Playwright context with a Fingerprint.

Parameters:
    browser (Browser): The browser to create the context in
    fingerprint (Optional[Fingerprint]): The fingerprint to inject. If None, one will be generated
    fingerprint_options (Optional[Dict]): Options for the Fingerprint generator if `fingerprint` is not passed
    **new_context_options: Other options for the new context
```

</details>

#### Undetected-Playwright

[Undetected-Playwright](https://github.com/kaliiiiiiiiii/undetected-playwright-python) is also supported in the `browserforge.injectors.undetected_playwright` package. The usage is the same as the Playwright injector.

### Pyppeteer

```py
# Import the NewPage injector
from browserforge.injectors.pyppeteer import NewPage
from pyppeteer import launch

async def test():
    browser = await launch()
    # Create a new page with the injected fingerprint
    page = await NewPage(browser, fingerprint=fingerprint)
    ...
```

Replace `browser.newPage` with `NewPage` in your existing Pyppeteer code.

<details>
<summary>Parameters for NewPage</summary>

```
Injects a Pyppeteer browser object with a Fingerprint.

Parameters:
    browser (Browser): The browser to create the context in
    fingerprint (Optional[Fingerprint]): The fingerprint to inject. If None, one will be generated
    fingerprint_options (Optional[Dict]): Options for the Fingerprint generator if `fingerprint` is not passed
```

</details>

<hr width=50>

## Uninstall

To fully remove all files, run the following commands:

```
python -m browserforge remove
pip uninstall browserforge
```

---

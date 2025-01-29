from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Literal, Optional, Tuple, Union

from browserforge.bayesian_network import BayesianNetwork, get_possible_values

from .utils import get_browser, get_user_agent, pascalize_headers, tuplify

try:
    import orjson as json
except ImportError:
    import json

try:
    from typing import TypeAlias  # novm
except ImportError:
    from typing_extensions import TypeAlias  # <3.10


"""Constants"""
SUPPORTED_BROWSERS = ('chrome', 'firefox', 'safari', 'edge')
SUPPORTED_OPERATING_SYSTEMS = ('windows', 'macos', 'linux', 'android', 'ios')
SUPPORTED_DEVICES = ('desktop', 'mobile')
SUPPORTED_HTTP_VERSIONS = ('1', '2')
MISSING_VALUE_DATASET_TOKEN = '*MISSING_VALUE*'
HTTP1_SEC_FETCH_ATTRIBUTES = {
    'Sec-Fetch-Mode': 'same-site',
    'Sec-Fetch-Dest': 'navigate',
    'Sec-Fetch-Site': '?1',
    'Sec-Fetch-User': 'document',
}
HTTP2_SEC_FETCH_ATTRIBUTES = {
    'sec-fetch-mode': 'same-site',
    'sec-fetch-dest': 'navigate',
    'sec-fetch-site': '?1',
    'sec-fetch-user': 'document',
}
DATA_DIR: Path = Path(__file__).parent / 'data'
ListOrString: TypeAlias = Union[Tuple[str, ...], List[str], str]


@dataclass
class Browser:
    """Represents a browser specification with name, min/max version, and HTTP version"""

    name: str
    min_version: Optional[int] = None
    max_version: Optional[int] = None
    http_version: Union[str, int] = '2'

    def __post_init__(self):
        # Convert http_version to
        if isinstance(self.http_version, int):
            self.http_version = str(self.http_version)
        # Confirm min_version < max_version
        if (
            isinstance(self.min_version, int)
            and isinstance(self.max_version, int)
            and self.min_version > self.max_version
        ):
            raise ValueError(
                f'Browser min version constraint ({self.min_version}) cannot exceed max version ({self.max_version})'
            )


@dataclass
class HttpBrowserObject:
    """Represents an HTTP browser object with name, version, complete string, and HTTP version"""

    name: Optional[str]
    version: Tuple[int, ...]
    complete_string: str
    http_version: str

    @property
    def is_http2(self):
        return self.http_version == '2'


class HeaderGenerator:
    """Generates HTTP headers based on a set of constraints"""

    relaxation_order: Tuple[str, ...] = ('locales', 'devices', 'operatingSystems', 'browsers')

    # Initialize networks
    input_generator_network = BayesianNetwork(DATA_DIR / "input-network.zip")
    header_generator_network = BayesianNetwork(DATA_DIR / "header-network.zip")

    def __init__(
        self,
        browser: Union[ListOrString, Iterable[Browser]] = SUPPORTED_BROWSERS,
        os: ListOrString = SUPPORTED_OPERATING_SYSTEMS,
        device: ListOrString = SUPPORTED_DEVICES,
        locale: ListOrString = 'en-US',
        http_version: Literal[1, 2] = 2,
        strict: bool = False,
    ):
        """
        Initializes the HeaderGenerator with the given options.

        Parameters:
            browser (Union[ListOrString, Iterable[Browser]], optional): Browser(s) or Browser object(s).
            os (ListOrString, optional): Operating system(s) to generate headers for.
            device (ListOrString, optional): Device(s) to generate the headers for.
            locale (ListOrString, optional): List of at most 10 languages for the Accept-Language header. Default is 'en-US'.
            http_version (Literal[1, 2], optional): Http version to be used to generate headers. Defaults to 2.
            strict (bool, optional): Throws an error if it cannot generate headers based on the input. Defaults to False.
        """
        http_ver: str = str(http_version)

        self.options = {
            'browsers': self._prepare_browsers_config(tuplify(browser), http_ver),
            'os': tuplify(os),
            'devices': tuplify(device),
            'locales': tuplify(locale),
            'http_version': http_ver,
            'strict': strict,
        }
        # Loader orders
        self.unique_browsers = self._load_unique_browsers()
        self.headers_order = self._load_headers_order()

    def generate(
        self,
        *,
        browser: Optional[Iterable[Union[str, Browser]]] = None,
        os: Optional[ListOrString] = None,
        device: Optional[ListOrString] = None,
        locale: Optional[ListOrString] = None,
        http_version: Optional[Literal[1, 2]] = None,
        user_agent: Optional[ListOrString] = None,
        strict: Optional[bool] = None,
        request_dependent_headers: Optional[Dict[str, str]] = None,
    ):
        """
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
        """

        options = {
            'browsers': tuplify(browser),
            'os': tuplify(os),
            'devices': tuplify(device),
            'locales': tuplify(locale),
            'http_version': str(http_version) if http_version else None,
            'strict': strict,
            'user_agent': tuplify(user_agent),
            'request_dependent_headers': request_dependent_headers,
        }
        generated: Dict[str, str] = self._get_headers(
            **{k: v for k, v in options.items() if v is not None}
        )
        if (options['http_version'] or self.options['http_version']) == '2':
            return pascalize_headers(generated)
        return generated

    def _get_headers(
        self,
        request_dependent_headers: Optional[Dict[str, str]] = None,
        user_agent: Optional[Iterable[str]] = None,
        **options: Any,
    ) -> Dict[str, str]:
        """
        Generates HTTP headers based on the given constraints.

        Parameters:
            request_dependent_headers (Dict[str, str], optional): Dictionary of request-dependent headers.
            user_agent (Iterable[str], optional): User-Agent value(s).
            **options (Any): Additional options for header generation.

        Returns:
            Dict[str, str]: Dictionary of generated HTTP headers.
        """
        if request_dependent_headers is None:
            request_dependent_headers = {}

        # Process new options
        if 'browsers' in options or (
            # if a unique http_version was passed
            'http_version' in options
            and options['http_version'] != self.options['http_version']
        ):
            self._update_http_version(options)

        header_options = {**self.options, **options}
        possible_attribute_values = self._get_possible_attribute_values(header_options)

        if user_agent:
            # evaluate iterable
            if not isinstance(user_agent, (tuple, list)):
                user_agent = tuple(user_agent)
            http1_values, http2_values = (
                get_possible_values(self.header_generator_network, {'User-Agent': user_agent}),
                get_possible_values(self.header_generator_network, {'user-agent': user_agent}),
            )
        else:
            http1_values, http2_values = {}, {}

        constraints = self._prepare_constraints(
            possible_attribute_values, http1_values, http2_values
        )

        input_sample = self.input_generator_network.generate_consistent_sample_when_possible(
            constraints
        )
        if not input_sample:
            if header_options['http_version'] == '1':
                headers2 = self._get_headers(
                    request_dependent_headers, user_agent, **options, http_version='2'
                )
                return self.order_headers(pascalize_headers(headers2))

            relaxation_index = next(
                (i for i, key in enumerate(self.relaxation_order) if key in options), -1
            )
            if header_options['strict'] or relaxation_index == -1:
                raise ValueError(
                    'No headers based on this input can be generated. Please relax or change some of the requirements you specified.'
                )

            relaxed_options = {**options}
            del relaxed_options[self.relaxation_order[relaxation_index]]
            return self._get_headers(request_dependent_headers, user_agent, **relaxed_options)

        generated_sample = self.header_generator_network.generate_sample(input_sample)
        generated_http_and_browser = self._prepare_http_browser_object(
            generated_sample['*BROWSER_HTTP']
        )

        # Add Accept-Language header
        accept_language_field_name = (
            'accept-language' if generated_http_and_browser.is_http2 else 'Accept-Language'
        )
        generated_sample[accept_language_field_name] = self._get_accept_language_header(
            header_options['locales']
        )

        # Add Sec headers
        if self._should_add_sec_fetch(generated_http_and_browser):
            if generated_http_and_browser.is_http2:
                generated_sample.update(HTTP2_SEC_FETCH_ATTRIBUTES)
            else:
                generated_sample.update(HTTP1_SEC_FETCH_ATTRIBUTES)

        # Ommit connection, close, and missing value headers
        generated_sample = {
            k: v
            for k, v in generated_sample.items()
            if not (
                k.lower() == 'connection'
                and v == 'close'
                or k.startswith('*')
                or v == MISSING_VALUE_DATASET_TOKEN
            )
        }

        # Reorder headers
        return self.order_headers({**generated_sample, **request_dependent_headers})

    def _update_http_version(
        self,
        options: Dict[str, Any],
    ):
        """
        Prepares options when a `browsers` or `http_version` kwarg is passed to .generate.

        Parameters:
            options (Dict[str, Any]): Other arguments.
        """
        if 'http_version' in options:
            http_version = options['http_version']
        else:
            http_version = self.options['http_version']

        if 'browsers' in options:
            options['browsers'] = self._prepare_browsers_config(options['browsers'], http_version)
        else:
            # Create a copy of the class browsers with an updated http_version
            options['browsers'] = [
                (
                    Browser(
                        name=brwsr.name,
                        min_version=brwsr.min_version,
                        max_version=brwsr.max_version,
                        http_version=http_version,
                    )
                    if isinstance(brwsr, Browser)
                    else Browser(name=brwsr, http_version=http_version)
                )
                for brwsr in self.options['browsers']
            ]

    def _prepare_browsers_config(
        self, browsers: Iterable[Union[str, Browser]], http_version: str
    ) -> List[Browser]:
        """
        Prepares the browser configuration based on the given browsers and HTTP version.

        Parameters:
            browsers (Iterable[Union[str, Browser]]): Supported browsers or Browser objects.
            http_version (str): HTTP version ('1' or '2').

        Returns:
            List[Browser]: List of Browser objects.
        """
        return [
            (
                Browser(name=browser, http_version=http_version)
                if isinstance(browser, str)
                else browser
            )
            for browser in browsers
        ]

    def _get_browser_http_options(self, browsers: Iterable[Browser]) -> List[str]:
        """
        Retrieves the browser HTTP options based on the given browser specifications.

        Parameters:
            browsers (Iterable[Browser]): Iterable of Browser objects.

        Returns:
            List[str]: List of browser HTTP options.
        """
        return [
            browser_option.complete_string
            for browser in browsers
            for browser_option in self.unique_browsers
            if browser.name == browser_option.name
            and (not browser.min_version or browser.min_version <= browser_option.version[0])
            and (not browser.max_version or browser.max_version >= browser_option.version[0])
            and (not browser.http_version or browser.http_version == browser_option.http_version)
        ]

    def order_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        """
        Orders the headers based on the browser-specific header order.

        Parameters:
            headers (Dict[str, str]): Dictionary of headers.

        Returns:
            Dict[str, str]: Ordered dictionary of headers.
        """
        # get the browser name
        user_agent = get_user_agent(headers)
        if user_agent is None:
            raise ValueError("Failed to find User-Agent in generated response")
        browser_name = get_browser(user_agent)
        if browser_name is None:
            raise ValueError("Failed to find browser in User-Agent")

        header_order = self.headers_order.get(browser_name)
        # Order headers according to the specific browser's header order
        return (
            {key: headers[key] for key in header_order if key in headers}
            if header_order
            else headers
        )

    def _get_possible_attribute_values(
        self, header_options: Dict[str, Any]
    ) -> Dict[str, List[str]]:
        """
        Retrieves the possible attribute values based on the given header options.

        Parameters:
            header_options (Dict[str, Any]): Dictionary of header options.

        Returns:
            Dict[str, List[str]]: Dictionary of possible attribute values.
        """
        browsers = self._prepare_browsers_config(
            header_options.get('browsers', ()),
            header_options.get('http_version', '2'),
        )
        browser_http_options = self._get_browser_http_options(browsers)

        possible_attribute_values = {
            '*BROWSER_HTTP': browser_http_options,
            '*OPERATING_SYSTEM': header_options.get('os', SUPPORTED_OPERATING_SYSTEMS),
        }
        if 'devices' in header_options:
            possible_attribute_values['*DEVICE'] = header_options['devices']

        return possible_attribute_values

    def _should_add_sec_fetch(self, browser: HttpBrowserObject) -> bool:
        """
        Determines whether Sec-Fetch headers should be added based on the user agent.

        Parameters:
            browser (HttpBrowserObject): Browser object.

        Returns:
            bool: True if Sec-Fetch headers should be added, False otherwise.
        """
        if browser.name == 'chrome' and browser.version[0] >= 76:
            return True
        if browser.name == 'firefox' and browser.version[0] >= 90:
            return True
        if browser.name == 'edge' and browser.version[0] >= 79:
            return True
        return False

    def _get_accept_language_header(self, locales: ListOrString) -> str:
        """
        Generates the Accept-Language header based on the given locales.

        Parameters:
            locales (ListOrString): Locale(s).

        Returns:
            str: Accept-Language header string.
        """
        return ', '.join(
            f"{locale};q={1.0 - index * 0.1:.1f}" for index, locale in enumerate(locales)
        )

    def _load_headers_order(self) -> Dict[str, List[str]]:
        """
        Loads the headers order from the headers-order.json file.

        Returns:
            Dict[str, List[str]]: Dictionary of headers order for each browser.
        """
        headers_order_path = DATA_DIR / "headers-order.json"
        return json.loads(headers_order_path.read_bytes())

    def _load_unique_browsers(self) -> List[HttpBrowserObject]:
        """
        Loads the unique browsers from the browser-helper-file.json file.

        Returns:
            List[HttpBrowserObject]: List of HttpBrowserObject instances.
        """
        browser_helper_path = DATA_DIR / 'browser-helper-file.json'
        unique_browser_strings = json.loads(browser_helper_path.read_bytes())
        return [
            self._prepare_http_browser_object(browser_str)
            for browser_str in unique_browser_strings
            if browser_str != MISSING_VALUE_DATASET_TOKEN
        ]

    def _prepare_constraints(
        self,
        possible_attribute_values: Dict[str, List[str]],
        http1_values: Dict[str, Any],
        http2_values: Dict[str, Any],
    ) -> Dict[str, Iterable[str]]:
        """
        Prepares the constraints for generating consistent samples.

        Parameters:
            possible_attribute_values (Dict[str, List[str]]): Dictionary of possible attribute values.
            http1_values (Dict[str, Any]): Dictionary of HTTP/1 values.
            http2_values (Dict[str, Any]): Dictionary of HTTP/2 values.

        Returns:
            Dict[str, Iterable[str]]: Dictionary of constraints for each attribute.
        """
        return {
            key: tuple(
                filter(
                    lambda x: (
                        self.filter_browser_http(x, http1_values, http2_values)
                        if key == '*BROWSER_HTTP'
                        else self.filter_other_values(x, http1_values, http2_values, key)
                    ),
                    values,
                )
            )
            for key, values in possible_attribute_values.items()
        }

    @staticmethod
    def filter_browser_http(
        value: str, http1_values: Dict[str, Any], http2_values: Dict[str, Any]
    ) -> bool:
        """
        Filters the browser HTTP value based on the HTTP/1 and HTTP/2 values.

        Parameters:
            value (str): Browser HTTP value.
            http1_values (Dict[str, Any]): Dictionary of HTTP/1 values.
            http2_values (Dict[str, Any]): Dictionary of HTTP/2 values.

        Returns:
            bool: True if the value should be included, False otherwise.
        """
        browser_name, http_version = value.split('|')
        return (
            (not http1_values or browser_name in http1_values.get('*BROWSER', ()))
            if http_version == '1'
            else (not http2_values or browser_name in http2_values.get('*BROWSER', ()))
        )

    @staticmethod
    def filter_other_values(
        value: str, http1_values: Dict[str, Any], http2_values: Dict[str, Any], key: str
    ) -> bool:
        """
        Filters the other attribute values based on the HTTP/1 and HTTP/2 values.

        Parameters:
            value (str): Attribute value.
            http1_values (Dict[str, Any]): Dictionary of HTTP/1 values.
            http2_values (Dict[str, Any]): Dictionary of HTTP/2 values.
            key (str): Attribute key.

        Returns:
            bool: True if the value should be included, False otherwise.
        """
        if http1_values or http2_values:
            return value in http1_values.get(key, ()) or value in http2_values.get(key, ())
        return True

    def _prepare_http_browser_object(self, http_browser_string: str) -> HttpBrowserObject:
        """
        Extracts structured information about a browser and HTTP version from a string.

        Parameters:
            http_browser_string (str): HTTP browser string.

        Returns:
            HttpBrowserObject: HttpBrowserObject instance.
        """
        browser_string, http_version = http_browser_string.split('|')
        if browser_string == MISSING_VALUE_DATASET_TOKEN:
            return HttpBrowserObject(
                name=None, version=(), complete_string=MISSING_VALUE_DATASET_TOKEN, http_version=''
            )

        browser_name, version_string = browser_string.split('/')
        version_parts = version_string.split('.')
        version = tuple(int(part) for part in version_parts)
        return HttpBrowserObject(
            name=browser_name,
            version=version,
            complete_string=http_browser_string,
            http_version=http_version,
        )

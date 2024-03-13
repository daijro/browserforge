from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import orjson

from browserforge.bayesian_network import BayesianNetwork, get_possible_values
from browserforge.headers import HeaderGenerator
from browserforge.headers.utils import get_user_agent

DATA_DIR: Path = Path(__file__).parent / 'data'


@dataclass(frozen=True)
class ScreenFingerprint:
    availHeight: int
    availWidth: int
    availTop: int
    availLeft: int
    colorDepth: int
    height: int
    pixelDepth: int
    width: int
    devicePixelRatio: float
    pageXOffset: int
    pageYOffset: int
    innerHeight: int
    outerHeight: int
    outerWidth: int
    innerWidth: int
    screenX: int
    clientWidth: int
    clientHeight: int
    hasHDR: bool


@dataclass(frozen=True)
class NavigatorFingerprint:
    userAgent: str
    userAgentData: Dict[str, str]
    doNotTrack: Optional[str]
    appCodeName: str
    appName: str
    appVersion: str
    oscpu: str
    webdriver: str
    language: str
    languages: List[str]
    platform: str
    deviceMemory: Optional[int]
    hardwareConcurrency: int
    product: str
    productSub: str
    vendor: str
    vendorSub: str
    maxTouchPoints: int
    extraProperties: Dict[str, str]


@dataclass(frozen=True)
class VideoCard:
    renderer: str
    vendor: str


@dataclass(frozen=True)
class Fingerprint:
    """Output data of the fingerprint generator"""

    screen: ScreenFingerprint
    navigator: NavigatorFingerprint
    headers: Dict[str, str]
    videoCodecs: Dict[str, str]
    audioCodecs: Dict[str, str]
    pluginsData: Dict[str, str]
    battery: Optional[Dict[str, str]]
    videoCard: Optional[VideoCard]
    multimediaDevices: List[str]
    fonts: List[str]


@dataclass
class Screen:
    """Constrains the screen dimensions of the generated fingerprint"""

    min_width: Optional[int] = None
    max_width: Optional[int] = None
    min_height: Optional[int] = None
    max_height: Optional[int] = None

    def __post_init__(self):
        if (
            None not in (self.min_width, self.max_width)
            and self.min_width > self.max_width
            or None not in (self.min_height, self.max_height)
            and self.min_height > self.max_height
        ):
            raise ValueError(
                "Invalid screen constraints: min values cannot be greater than max values"
            )

    def is_set(self) -> bool:
        """
        Returns true if any constraints were set
        """
        return any(value is not None for value in self.__dict__.values())


class FingerprintGenerator:
    """Generates realistic browser fingerprints"""

    fingerprint_generator_network = BayesianNetwork(DATA_DIR / "fingerprint-network.json")

    def __init__(
        self,
        screen: Optional[Screen] = None,
        strict: bool = False,
        **header_kwargs,
    ):
        """
        Initializes the FingerprintGenerator with the given options.

        Parameters:
            screen (Screen, optional): Screen constraints for the generated fingerprint.
            strict (bool): Whether to raise an exception if the constraints are too strict. Default is False.
            **header_kwargs: Header generation options for HeaderGenerator
        """
        self.header_generator: HeaderGenerator = HeaderGenerator(**header_kwargs)

        self.screen: Optional[Screen] = screen
        self.strict: bool = strict

    def generate(
        self,
        *,
        screen: Optional[Screen] = None,
        strict: Optional[bool] = None,
        **header_kwargs,
    ) -> Fingerprint:
        """
        Generates a fingerprint and a matching set of ordered headers using a combination of the default options
        specified in the constructor and their possible overrides provided here.

        Parameters:
            screen (Screen, optional): Screen constraints for the generated fingerprint.
            strict (bool, optional): Whether to raise an exception if the constraints are too strict.
            **header_kwargs: Additional header generation options for HeaderGenerator.generate
        """
        filtered_values: Dict[str, str] = {}
        if header_kwargs is None:
            header_kwargs = {}

        # merge new options with old
        if screen is None:
            screen = self.screen
        if strict is None:
            strict = self.strict

        partial_csp = self.partial_csp(
            strict=strict, screen=screen, filtered_values=filtered_values
        )

        # Generate headers consistent with the inputs to get input-compatible user-agent
        # and accept-language headers needed later
        if partial_csp:
            header_kwargs['user_agent'] = partial_csp['userAgent']
        headers = self.header_generator.generate(**header_kwargs)
        # Extract generated User-Agent
        user_agent = get_user_agent(headers)
        if user_agent is None:
            raise ValueError("Failed to find User-Agent in generated response")

        # Generate fingerprint consistent with the generated user agent
        while True:
            fingerprint: Optional[Dict] = (
                self.fingerprint_generator_network.generate_consistent_sample_when_possible(
                    {**filtered_values, 'userAgent': (user_agent,)}
                )
            )
            if fingerprint is not None:
                break
            # Raise
            if strict:
                raise ValueError(
                    'Cannot generate headers. User-Agent may be invalid, or screen constraints are too restrictive.'
                )
            # If no fingerprint was generated, relax the filtered values.
            # This seems to be an issue with some Mac and Linux systems
            filtered_values = {}

        # Delete any missing attributes and unpack any object/array-like attributes
        # that have been packed together to make the underlying network simpler
        for attribute in list(fingerprint.keys()):
            if fingerprint[attribute] == '*MISSING_VALUE*':
                fingerprint[attribute] = None
            if isinstance(fingerprint[attribute], str) and fingerprint[attribute].startswith(
                '*STRINGIFIED*'
            ):
                fingerprint[attribute] = orjson.loads(
                    fingerprint[attribute][len('*STRINGIFIED*') :]
                )

        # Manually add the set of accepted languages required by the input
        accept_language_header_value = headers.get(
            'Accept-Language', headers.get('accept-language', '')
        )
        accepted_languages = [
            locale.split(';', 1)[0] for locale in accept_language_header_value.split(',')
        ]
        fingerprint['languages'] = accepted_languages

        return self._transform_fingerprint(fingerprint, headers)

    def partial_csp(
        self, strict: bool, screen: Optional[Screen], filtered_values: Dict
    ) -> Optional[Dict]:
        """
        Generates partial content security policy (CSP) based on the provided options and filtered values.

        Parameters:
            strict (bool, optional): Whether to raise an exception if the constraints are too strict.
            screen (Screen, optional): Screen for generating the partial CSP.
            filtered_values (Dict): Filtered values used for generating the partial CSP.

        Returns:
            Dict: Partial CSP values.
        """
        # if extensive constraints need to be used
        if not (screen and screen.is_set()):
            return None

        filtered_values['screen'] = [
            screen_string
            for screen_string in self.fingerprint_generator_network.nodes_by_name[
                'screen'
            ].possible_values
            if self._is_screen_within_constraints(screen_string, screen)
        ]

        try:
            return get_possible_values(self.fingerprint_generator_network, filtered_values)
        except Exception as e:
            if strict:
                raise e
            del filtered_values['screen']
        return None

    @staticmethod
    def _is_screen_within_constraints(screen_string: str, screen_options: Screen) -> bool:
        """
        Checks if the given screen dimensions are within the specified constraints.

        Parameters:
            screen_string (str): Stringified screen dimensions.
            screen_options (Screen): Screen constraint options.

        Returns:
            bool: True if the screen dimensions are within the constraints, False otherwise.
        """
        screen = orjson.loads(screen_string[len('*STRINGIFIED*') :])
        return (
            screen['width'] >= (screen_options.min_width or 0)
            and screen['width'] <= (screen_options.max_width or 1e5)
            and screen['height'] >= (screen_options.min_height or 0)
            and screen['height'] <= (screen_options.max_height or 1e5)
        )

    @staticmethod
    def _transform_fingerprint(fingerprint: Dict, headers: Dict) -> Fingerprint:
        """
        Transforms fingerprint into a final dataclass instance.

        Parameters:
            fingerprint (Dict): Fingerprint to be transformed.
            headers (Dict): Generated headers.

        Returns:
            Fingerprint: Transformed fingerprint as a Fingerprint dataclass instance.
        """

        navigator_kwargs = {
            k: fingerprint[k]
            for k in (
                'userAgent',
                'userAgentData',
                'doNotTrack',
                'appCodeName',
                'appName',
                'appVersion',
                'oscpu',
                'webdriver',
                'platform',
                'deviceMemory',
                'product',
                'productSub',
                'vendor',
                'vendorSub',
                'extraProperties',
                'hardwareConcurrency',
                'languages',
            )
        }

        # Assuming 'languages' is a list and you always take the first element for 'language'.
        navigator_kwargs['language'] = navigator_kwargs['languages'][0]
        navigator_kwargs['maxTouchPoints'] = fingerprint.get('maxTouchPoints', 0)

        return Fingerprint(
            screen=ScreenFingerprint(**fingerprint['screen']),
            navigator=NavigatorFingerprint(**navigator_kwargs),
            headers=headers,
            videoCodecs=fingerprint['videoCodecs'],
            audioCodecs=fingerprint['audioCodecs'],
            pluginsData=fingerprint['pluginsData'],
            battery=fingerprint['battery'],
            videoCard=(
                VideoCard(**fingerprint['videoCard']) if fingerprint.get('videoCard') else None
            ),
            multimediaDevices=fingerprint['multimediaDevices'],
            fonts=fingerprint['fonts'],
        )

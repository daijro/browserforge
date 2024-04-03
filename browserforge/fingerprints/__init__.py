from browserforge.download import download_if_not_exists

download_if_not_exists(fingerprints=True)

from browserforge.headers import Browser

from .generator import (
    Fingerprint,
    FingerprintGenerator,
    NavigatorFingerprint,
    Screen,
    ScreenFingerprint,
    VideoCard,
)

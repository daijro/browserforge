from typing import Dict

from browserforge.fingerprints import Fingerprint


def _context_options(
    fingerprint: Fingerprint,
    options: Dict,
):
    """Builds options for new context"""
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
        'device_scale_factor': fingerprint.screen.devicePixelRatio,
        **options,
    }

from typing import Any, Dict, Iterable, Optional


def get_user_agent(headers: Dict[str, str]) -> Optional[str]:
    """
    Retrieves the User-Agent from the headers dictionary.
    """
    return headers.get('User-Agent') or headers.get('user-agent')


def get_browser(user_agent: str) -> Optional[str]:
    """
    Determines the browser name from the User-Agent string.
    """
    if any(alias in user_agent for alias in ('Firefox', 'FxiOS')):
        return 'firefox'
    elif any(alias in user_agent for alias in ('Chrome', 'CriOS')):
        return 'chrome'
    elif 'Safari' in user_agent:
        return 'safari'
    elif any(alias in user_agent for alias in ('Edge', 'EdgA', 'Edg', 'EdgiOS')):
        return 'edge'
    return None


PASCALIZE_UPPER = {'dnt', 'rtt', 'ect'}


def pascalize(name: str) -> str:
    # ignore
    if name.startswith(':') or name.startswith('sec-ch-ua'):
        return name
    # uppercase
    if name in PASCALIZE_UPPER:
        return name.upper()
    return name.title()


def pascalize_headers(headers: Dict[str, str]) -> Dict[str, str]:
    return {pascalize(key): value for key, value in headers.items()}


def tuplify(obj: Any):
    if (isinstance(obj, Iterable) and not isinstance(obj, str)) or obj is None:
        return obj
    return (obj,)

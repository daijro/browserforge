"""
The undetected_playwright injector is a 1:1 copy of the playwright injector,
using the "undetected_playwright" import name for typing purposes.
"""

from browserforge.injectors.utils import CheckIfInstalled

CheckIfInstalled('undetected_playwright')

from .injector import AsyncNewContext, NewContext

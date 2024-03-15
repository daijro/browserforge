from browserforge.injectors.utils import CheckIfInstalled

CheckIfInstalled('playwright')

from .injector import AsyncNewContext, NewContext

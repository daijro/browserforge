from click import secho

"""
Public download functions (deprecated)
"""


def Download(headers=False, fingerprints=False) -> None:
    """
    **DEPRECATED**
    As of v1.2.4, model files are included in their own Python package dependency.
    """
    secho(
        'BrowserForge model files are now bundled in their own Python package dependency. This command is deprecated.',
        fg='bright_black',
    )


def DownloadIfNotExists(**flags: bool) -> None:
    """
    **DEPRECATED**
    As of v1.2.4, model files are included in their own Python package dependency.
    Mark as downloaded by default.
    """
    pass


def IsDownloaded(**flags: bool) -> bool:
    """
    **DEPRECATED**
    As of v1.2.4, model files are included in their own Python package dependency.
    Mark as downloaded by default.
    """
    return True


def Remove() -> None:
    """
    **DEPRECATED**
    As of v1.2.4, model files are included in their own Python package dependency.
    """
    pass

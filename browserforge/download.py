
import click

"""
Downloads the required model definitions - deprecated
"""


"""
Public download functions
"""


def Download(headers=False, fingerprints=False) -> None:
    """
    Deprecated. Downloading model definition files is no longer needed.

    Files are included as explicit python package dependency.
    """
    click.secho('Deprecated. Downloading model definition files is no longer needed.', fg='bright_yellow')


def DownloadIfNotExists(**flags: bool) -> None:
    """
    Deprecated. Downloading model definition files is no longer needed.

    Files are included as explicit python package dependency.
    """
    pass


def IsDownloaded(**flags: bool) -> bool:
    """
    Deprecated. Downloading model definition files is no longer needed.

    Files are included as explicit python package dependency.
    """
    return True


def Remove() -> None:
    """
    Deprecated. Downloading model definition files is no longer needed.

    Files are included as explicit python package dependency.
    """
    pass

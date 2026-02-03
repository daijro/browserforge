import click
from click import secho

"""
Stub cli for backwards compatibility to not break existing projects on <1.2.4
"""


class DownloadException(Exception):
    """Raises when the download fails."""


@click.group()
def cli() -> None:
    """
    NOTE: BrowserForge CLI is DEPRECATED!

    As of 1.2.4, model files are included as its own Python package dependency.
    Manual downloads are no longer required.
    """
    pass


@cli.command(name='update')
@click.option('--headers', is_flag=True)
@click.option('--fingerprints', is_flag=True)
def update(headers=False, fingerprints=False):
    """
    **DEPRECATED**
    """
    secho(
        'BrowserForge: As of v1.2.4, model files are included in their own Python package dependency.',
        fg='bright_yellow',
    )
    pass


@cli.command(name='remove')
def remove():
    """
    **DEPRECATED**
    """
    secho(
        'BrowserForge: As of v1.2.4, model files are included in their own Python package dependency.',
        fg='bright_yellow',
    )
    pass


if __name__ == '__main__':
    cli()

import click

"""
Stub cli for backwards compatibility to not break existing projects on <1.2.4
"""


class DownloadException(Exception):
    """**DEPRECATED**"""


def _deprecated() -> None:
    click.secho(
        'DEPRECATED: As of v1.2.4, BrowserForge model files are now bundled in their own Python package dependency.',
        fg='red',
    )


@click.group()
def cli() -> None:
    """
    NOTE: BrowserForge CLI is DEPRECATED!

    BrowserForge: As of v1.2.4, model files are already bundled in their own package dependency.
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
    _deprecated()


@cli.command(name='remove')
def remove():
    """
    **DEPRECATED**
    """
    _deprecated()


if __name__ == '__main__':
    cli()

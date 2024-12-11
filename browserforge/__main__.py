import click

from browserforge.download import Download, Remove


class DownloadException(Exception):
    """Raises when the download fails."""


@click.group()
def cli() -> None:
    pass


@cli.command(name='update')
@click.option('--headers', is_flag=True, help='Only update header definitions')
@click.option('--fingerprints', is_flag=True, help='Only update fingerprint definitions')
def update(headers=False, fingerprints=False):
    """
    Fetches header and fingerprint definitions
    """
    # if no options passed, mark both as True
    if not headers ^ fingerprints:
        headers = fingerprints = True

    Download(headers=headers, fingerprints=fingerprints)


@cli.command(name='remove')
def remove():
    """
    Remove all downloaded files
    """
    Remove()
    click.secho('Removed all files!', fg='bright_yellow')


if __name__ == '__main__':
    cli()

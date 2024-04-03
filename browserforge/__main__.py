import click

from browserforge.download import download, remove


class DownloadException(Exception):
    """Raises when the download fails."""


@click.group()
def cli() -> None:
    pass


@cli.command(name="update")
@click.option("--headers", is_flag=True, help="Only update header definitions")
@click.option(
    "--fingerprints", is_flag=True, help="Only update fingerprint definitions"
)
def update(headers=False, fingerprints=False):
    """
    Fetches header and fingerprint definitions
    """
    # if no options passed, mark both as True
    if not headers ^ fingerprints:
        headers = fingerprints = True

    click.secho("Downloading model definition files...", fg="green")

    download(headers=headers, fingerprints=fingerprints)
    click.secho("Complete!", fg="green")


@cli.command(name="remove")
def remove():
    """
    Remove all downloaded files
    """
    remove()
    click.secho("Removed all files!", fg="green")


if __name__ == "__main__":
    cli()

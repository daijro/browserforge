import shutil
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Iterator

import click

"""
Downloads the required model definitions
"""


ROOT_DIR: Path = Path(__file__).parent

"""Constants for headers and fingerprints data"""
DATA_DIRS: Dict[str, Path] = {
    "headers": ROOT_DIR / "headers/data",
    "fingerprints": ROOT_DIR / "fingerprints/data",
}
DATA_FILES: Dict[str, Dict[str, str]] = {
    "headers": {
        "browser-helper-file.json": "browser-helper-file.json",
        "header-network.zip": "header-network-definition.zip",
        "headers-order.json": "headers-order.json",
        "input-network.zip": "input-network-definition.zip",
    },
    "fingerprints": {
        "fingerprint-network.zip": "fingerprint-network-definition.zip",
    },
}
REMOTE_PATHS: Dict[str, str] = {
    "headers": "https://github.com/apify/fingerprint-suite/raw/master/packages/header-generator/src/data_files",
    "fingerprints": "https://github.com/apify/fingerprint-suite/raw/master/packages/fingerprint-generator/src/data_files",
}


class DownloadException(Exception):
    """Raises when the download fails."""


class DataDownloader:
    """
    Download and extract data files for both headers and fingerprints.
    """

    def __init__(self, **kwargs: bool) -> None:
        self.options = _enabled_flags(kwargs)

    def download_file(self, url: str, path: str) -> None:
        """
        Download a file from the specified URL and save it to the given path.
        """
        with urllib.request.urlopen(url) as resp:  # nosec
            if resp.status != 200:
                raise DownloadException(f"Download failed with status code: {resp.status}")
            with open(path, "wb") as f:
                shutil.copyfileobj(resp, f)

    def download(self) -> None:
        """
        Download and extract data files for both headers and fingerprints.
        """
        futures = {}
        with ThreadPoolExecutor(10) as executor:
            for data_type in self.options:
                for local_name, remote_name in DATA_FILES[data_type].items():
                    url = f"{REMOTE_PATHS[data_type]}/{remote_name}"
                    path = str(DATA_DIRS[data_type] / local_name)
                    future = executor.submit(self.download_file, url, path)
                    futures[future] = local_name
            for f in as_completed(futures):
                try:
                    future.result()
                    click.secho(f"{futures[f]:<30}OK!", fg="green")
                except Exception as e:
                    click.secho(f"Error downloading {local_name}: {e}", fg="red")


def _enabled_flags(flags: Dict[str, bool]) -> Iterator[str]:
    """
    Returns a list of enabled flags based on a given dictionary
    """
    for flag, enabled in flags.items():
        if enabled:
            yield flag


def _get_all_paths(**flags: bool) -> Iterator[Path]:
    """
    Yields all the paths to the downloaded data files
    """
    for data_type in _enabled_flags(flags):
        data_path = DATA_DIRS[data_type]
        for local_name, _ in DATA_FILES[data_type].items():
            yield data_path / local_name


"""
Public download functions
"""


def Download(headers=False, fingerprints=False) -> None:
    """
    Download the required data files
    """
    # Announce that files are being downloaded
    click.secho('Downloading model definition files...', fg='bright_yellow')
    try:
        DataDownloader(headers=headers, fingerprints=fingerprints).download()
    except KeyboardInterrupt:
        print("Download interrupted.")
        Remove()
        exit()


def DownloadIfNotExists(**flags: bool) -> None:
    """
    Download the required data files if they don't exist
    """
    if not IsDownloaded(**flags):
        Download(**flags)


def IsDownloaded(**flags: bool) -> bool:
    """
    Check if the required data files are already downloaded and not older than a month.
    Returns True if all the requested data files are present and not older than a month, False otherwise.
    """
    for path in _get_all_paths(**flags):
        if not path.exists():
            return False

    # Check if the file is older than a month
    file_creation_time = datetime.fromtimestamp(path.stat().st_ctime)
    one_month_ago = datetime.now() - timedelta(weeks=5)
    return file_creation_time >= one_month_ago


def Remove() -> None:
    """
    Deletes all downloaded data files
    """
    for path in _get_all_paths(headers=True, fingerprints=True):
        path.unlink(missing_ok=True)

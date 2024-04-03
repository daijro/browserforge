from io import BytesIO
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Iterator
from zipfile import ZipFile

import click
import httpx


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
        "header-network.json": "header-network-definition.zip",
        "headers-order.json": "headers-order.json",
        "input-network.json": "input-network-definition.zip",
    },
    "fingerprints": {
        "fingerprint-network.json": "fingerprint-network-definition.zip",
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

    def download_and_extract(self, url: str, path: str) -> None:
        """
        Download a file from the specified URL and save it to the given path.
        If the URL points to a ZIP file, extract the first JSON file found inside it and save the extracted JSON file.
        """
        with httpx.Client(follow_redirects=True) as client:
            resp = client.get(url)
            if resp.status_code == 200:
                # Ensure the directory exists
                Path(path).parent.mkdir(parents=True, exist_ok=True)
                if url.endswith(".zip"):
                    # Extract JSON from ZIP
                    with BytesIO(resp.content) as iostream:
                        with ZipFile(iostream, "r") as zip_ref:
                            file = next(
                                (
                                    file
                                    for file in zip_ref.namelist()
                                    if file.endswith(".json")
                                ),
                                None,
                            )
                            if not file:
                                raise Exception("Cannot find json file in zip")
                            with open(path, "wb") as dest_file:
                                dest_file.write(zip_ref.read(file))
                else:
                    # Write the content to the file
                    with open(path, "wb") as f:
                        f.write(resp.content)
            else:
                raise Exception(
                    "Download failed with status code: " + str(resp.status_code)
                )

    def download(self, **kwargs) -> None:
        """
        Download and extract data files for both headers and fingerprints.
        """
        futures = {}
        with ThreadPoolExecutor(10) as executor:
            for data_type, enabled in kwargs.items():
                if not enabled:
                    # if the option is marked as False, ignore
                    continue
                for local_name, remote_name in DATA_FILES[data_type].items():
                    url = f"{REMOTE_PATHS[data_type]}/{remote_name}"
                    path = str(DATA_DIRS[data_type] / local_name)
                    future = executor.submit(self.download_and_extract, url, path)
                    futures[future] = local_name
                for f in as_completed(futures):
                    try:
                        future.result()
                        click.secho(f"{futures[f]:<30}OK!", fg="green")
                    except Exception as e:
                        click.secho(f"Error downloading {local_name}: {e}", fg="red")


def download(headers=True, fingerprints=True) -> None:
    try:
        DataDownloader().download(headers=headers, fingerprints=fingerprints)
    except KeyboardInterrupt:
        print("Download interrupted.")
        remove()
        exit()


def download_if_not_exists(headers: bool = False, fingerprints: bool = False) -> None:
    if not is_downloaded(headers=headers, fingerprints=fingerprints):
        download(headers=headers, fingerprints=fingerprints)


def get_all_paths(headers=False, fingerprints=False) -> Iterator[Path]:
    """
    Yields all the paths to the downloaded data files
    """
    for data_type, data_path in DATA_DIRS.items():
        if (headers and data_type == "headers") or (
            fingerprints and data_type == "fingerprints"
        ):
            for local_name, remote_name in DATA_FILES[data_type].items():
                yield data_path / local_name


def is_downloaded(headers=False, fingerprints=False) -> bool:
    """
    Check if the required data files are already downloaded and not older than a week.
    Returns True if all the requested data files are present and not older than a week, False otherwise.
    """
    for path in get_all_paths(headers=headers, fingerprints=fingerprints):
        if not path.exists():
            return False
    # Check if the file is older than a week
    file_creation_time = datetime.fromtimestamp(path.stat().st_ctime)
    one_week_ago = datetime.now() - timedelta(weeks=1)
    if file_creation_time < one_week_ago:
        return False
    return True


def remove() -> None:
    """
    Deletes all downloaded data files
    """
    for path in get_all_paths(headers=True, fingerprints=True):
        path.unlink(missing_ok=True)

import asyncio
import contextvars
import functools
import io
from pathlib import Path
from shutil import copyfileobj
from typing import AsyncIterable, Dict, Iterator
from zipfile import ZipFile

import aiofiles
import httpx
from rich.progress import BarColumn, DownloadColumn, Progress, TaskID, TransferSpeedColumn

"""
Downloads the required model definitions
"""


ROOT_DIR: Path = Path(__file__).parent

"""Constants for headers and fingerprints data"""
DATA_DIRS: Dict[str, Path] = {
    'headers': ROOT_DIR / 'headers/data',
    'fingerprints': ROOT_DIR / 'fingerprints/data',
}
DATA_FILES: Dict[str, Dict[str, str]] = {
    'headers': {
        'browser-helper-file.json': 'browser-helper-file.json',
        'header-network.json': 'header-network-definition.zip',
        'headers-order.json': 'headers-order.json',
        'input-network.json': 'input-network-definition.zip',
    },
    'fingerprints': {
        'fingerprint-network.json': 'fingerprint-network-definition.zip',
    },
}
REMOTE_PATHS: Dict[str, str] = {
    'headers': 'https://github.com/apify/fingerprint-suite/raw/master/packages/header-generator/src/data_files',
    'fingerprints': 'https://github.com/apify/fingerprint-suite/raw/master/packages/fingerprint-generator/src/data_files',
}


class DownloadException(Exception):
    """Raises when the download fails."""


class DataDownloader:
    """
    Download and extract data files for both headers and fingerprints.
    """

    async def web_fileobj(
        self, url: str, progress: Progress, task_id: TaskID, session: httpx.AsyncClient
    ) -> AsyncIterable[bytes]:
        """
        Download the file from the specified URL and yield it as an async iterable of bytes.
        Update the progress bar during the download.
        """
        try:
            async with session.stream('GET', url, follow_redirects=True, timeout=120) as resp:
                total = int(resp.headers['Content-Length'])
                progress.update(task_id, total=total)
                async for chunk in resp.aiter_bytes():
                    progress.update(task_id, advance=len(chunk))
                    yield chunk
        except httpx.ConnectError as e:
            raise DownloadException('Cannot connect to the server.') from e

    async def _download_file(
        self, url: str, path: str, progress: Progress, task_id: TaskID, session: httpx.AsyncClient
    ) -> None:
        """
        Download a file from the specified URL and save it to the given path.
        """
        async with aiofiles.open(path, 'wb') as fstream:
            async for chunk in self.web_fileobj(url, progress, task_id, session):
                await fstream.write(chunk)

    async def _extract_json_from_zip(
        self, url: str, path: str, progress: Progress, task_id: TaskID, session: httpx.AsyncClient
    ) -> None:
        """
        Download a ZIP file from the specified URL, extract the first JSON file found inside it,
        and save the extracted JSON file to the given path.
        """

        def extract_json(iostream: io.BytesIO, path: str) -> None:
            with ZipFile(iostream, 'r') as zip_ref:
                file = next((file for file in zip_ref.namelist() if file.endswith('.json')), None)
                if not file:
                    raise DownloadException('Cannot find json file in zip')
                with open(path, 'wb') as dest_file:
                    copyfileobj(zip_ref.open(file), dest_file)

        iostream = io.BytesIO()
        async for chunk in self.web_fileobj(url, progress, task_id, session):
            iostream.write(chunk)

        await to_thread(extract_json, iostream, path)

    async def _download_and_extract(
        self, url: str, path: str, progress: Progress, task_id: TaskID, session: httpx.AsyncClient
    ) -> None:
        """
        Download a file from the specified URL and save it to the given path.
        If the URL points to a ZIP file, extract the first JSON file found inside it and save the extracted JSON file.
        """
        if url.endswith('.zip'):
            await self._extract_json_from_zip(url, path, progress, task_id, session)
        else:
            await self._download_file(url, path, progress, task_id, session)

    async def download(self, **kwargs) -> None:
        """
        Download and extract data files for both headers and fingerprints.
        """
        with Progress(
            "[progress.description]{task.description}",
            BarColumn(bar_width=40),
            '[progress.percentage]{task.percentage:>3.0f}%',
            DownloadColumn(),
            TransferSpeedColumn(),
        ) as progress:
            async with httpx.AsyncClient() as session:
                tasks = []
                for data_type, enabled in kwargs.items():
                    if not enabled:
                        # if the option is marked as False, ignore
                        continue
                    for local_name, remote_name in DATA_FILES[data_type].items():
                        url = f'{REMOTE_PATHS[data_type]}/{remote_name}'
                        path = str(DATA_DIRS[data_type] / local_name)
                        task_id = progress.add_task(local_name, total=None)
                        tasks.append(
                            self._download_and_extract(url, path, progress, task_id, session)
                        )
                await asyncio.gather(*tasks)


async def AsyncDownload(headers=True, fingerprints=True) -> None:
    """
    Download and extract data files for both headers and fingerprints.
    """
    downloader = DataDownloader()
    await downloader.download(headers=headers, fingerprints=fingerprints)


def Download(headers=True, fingerprints=True) -> None:
    try:
        asyncio.run(AsyncDownload(headers=headers, fingerprints=fingerprints))
    except KeyboardInterrupt:
        print('Download interrupted.')
        Remove()
        exit()


def DownloadIfNotExists() -> None:
    if not IsDownloaded():
        Download()


def get_all_paths() -> Iterator[Path]:
    """
    Yields all the paths to the downloaded data files
    """
    for data_type, data_path in DATA_DIRS.items():
        for local_name in DATA_FILES[data_type].keys():
            yield data_path / local_name


def IsDownloaded() -> bool:
    """
    Check if the required data files are already downloaded.
    Returns True if all the requested data files are present, False otherwise.
    """
    for path in get_all_paths():
        if not path.exists():
            return False
    return True


def Remove() -> None:
    """
    Deletes all downloaded data files
    """
    for path in get_all_paths():
        path.unlink(missing_ok=True)


async def to_thread(func, /, *args, **kwargs):
    """
    asyncio.to_thread backported for Python 3.8
    """
    loop = asyncio.get_running_loop()
    ctx = contextvars.copy_context()
    func_call = functools.partial(ctx.run, func, *args, **kwargs)
    return await loop.run_in_executor(None, func_call)

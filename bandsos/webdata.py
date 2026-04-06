# -*- coding: utf-8 -*-

import logging
import shutil
import time
import warnings
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr
from herbie import HerbieLatest, Herbie

from .utils import timeout

CYCLE_FORMAT = "%Y%m%d%H"
PRIORITY_SOURCE = ["aws", "google", "nomads"]
SEARCH_STRINGS = {
    "full": "(:UGRD:10 m above ground|:VGRD:10 m above ground|:PRMSL:mean sea level|:TMP:surface|:SPFH:2 m above ground)",
    "minimal": "(:UGRD:10 m above ground|:VGRD:10 m above ground|:PRMSL:mean sea level)"
}
SEARCH = SEARCH_STRINGS["minimal"]
TIMELIMIT = 30 * 60  # 30 minutes


class GFS_0p25_1hr:
    def __init__(self, data_dir="./gfs", data_prefix='gfs_', search_length="3d"):
        """GFS Data Class for 0p25 degree hourly outputs

        Args:
            data_dir (pathlike, optional): Data saving directory. Defaults to "./gfs".
            data_prefix (str, optional): Prefix of the output file. Defaults to 'gfs_'.
        """
        self.logger = logging.getLogger("GFS_0p25_1hr")

        self.data_dir = Path(data_dir)
        if not self.data_dir.exists():
            self.data_dir.mkdir()

        self.data_prefix = data_prefix
        self.search_length = pd.to_timedelta(search_length)

        self.available = self._list_available_cycles()
        self.downloaded = self._list_downloaded_cycles()
        self.remaining = self._list_remaining_cycles()

    @property
    def last(self) -> str:
        """Gives the last cycle name

        Returns:
            str: cycle name %Y%m%d%H
        """
        H = HerbieLatest(
            model="gfs",
            product="pgrb2.0p25",
            verbose=False,
            priority=PRIORITY_SOURCE,
            save_dir=Path("./.herbie_data")
        )

        tick_now = pd.to_datetime("now", utc=True).tz_localize(None)
        last_cycle = H.date
        self.logger.info(f"Found last cycle {last_cycle}, checking age.")

        cycle_age = tick_now - last_cycle
        if cycle_age <= pd.to_timedelta("5h"):
            last_cycle = last_cycle - pd.to_timedelta("6h")
            self.logger.info(f"Last cycle is less than 5 hours old, going back to one-cycle back")

        last_cycle = datetime2cycle(last_cycle)
        return last_cycle

    def check(self) -> bool:
        """Check if new download is available

        Returns:
            bool: availability of forecast to download
        """
        self.available = self._list_available_cycles()
        self.downloaded = self._list_downloaded_cycles()
        self.remaining = self._list_remaining_cycles()

        return len(self.remaining) > 0

    def _list_available_cycles(self) -> list:
        """List available cycles

        To be consistent with the previous interface, it gives the cycles for the last 10 days

        Returns:
            list: List of available cycles
        """
        cycle_time_now = cycle2datetime(self.last)
        cycle_time_10d = cycle_time_now - self.search_length

        cycle_timestamps = pd.date_range(cycle_time_10d, cycle_time_now, freq="6h")
        cycles = cycle_timestamps.strftime(CYCLE_FORMAT).to_list()

        return cycles

    def _list_downloaded_cycles(self) -> list:
        """List already downloaded cycles

        Returns:
            list: list of downloaded cycles
        """
        fpaths = list(self.data_dir.glob(f'{self.data_prefix}*.nc'))
        cycles = [fpath.name.split(self.data_prefix)[1].split('.nc')[0] for fpath in fpaths]

        return cycles

    def _list_remaining_cycles(self) -> list:
        """List remaining cycles to download

        Returns:
            list: list of cycles to download
        """
        remaining = list(set(self.available).difference(set(self.downloaded)))
        remaining.sort()
        return remaining

    def download(self, extent=None):
        """Download remaining cycles using multiple threads."""

        if extent is None:
            extent = [0, 360, -90, 90]

        for cycle in self.remaining:
            fname = self.data_dir / f"{self.data_prefix}{cycle}.nc"
            if fname.exists():
                self.logger.info(f"Already downloaded cycle {cycle}")
                continue

            self.logger.info(f"Downloading cycle {cycle}")
            download_cycle(cycle, fname, extent=extent, fxx_list=None)
            self.logger.info(f"Downloaded cycle {cycle} to {fname}")


def cycle2datetime(cycle, fmt=CYCLE_FORMAT):
    """Convert cycle to datetime

    Args:
        cycle (str): A cycle in %Y%m%d%H format
        fmt (str, optional): Datetime format. Defaults to CYCLE_FORMAT.

    Returns:
        datetime: Datetime
    """
    timestamp = pd.to_datetime(cycle, format=fmt)
    return timestamp


def datetime2cycle(timestamp, fmt=CYCLE_FORMAT):
    """Convert datetime to cycle

    Args:
        timestamp (datetime): datetime to convert
        fmt (str, optional): Output string format. Defaults to CYCLE_FORMAT.

    Returns:
        str: cycle corresponding to the datetime
    """
    timestamp = pd.to_datetime(timestamp)
    cycle = timestamp.strftime(fmt)
    return cycle


def download_step(timestamp, fxx, temp_dir):
    """Download the cycle using Herbie

    Args:
        timestamp: datetime to download
        fxx: step to download
        temp_dir: directory for temporary files
    """
    timestamp = pd.to_datetime(timestamp)
    temp_dir = Path(temp_dir)

    cycle = timestamp.strftime("%Y%m%d%H")

    fname = temp_dir / f"{cycle}_f{fxx:03d}.nc"
    if fname.exists():
        return fname

    H = Herbie(timestamp, model="gfs", product="pgrb2.0p25", verbose=False, fxx=fxx, save_dir=temp_dir)
    ds_list = H.xarray(search=SEARCH)

    try:
        ds_list = [ds.expand_dims("valid_time") for ds in ds_list]
    except:
        logging.fatal(f"Herbie did not return valid dataset for {fxx}, exiting.")
        import sys
        sys.exit()

    ds = xr.merge(ds_list, combine_attrs="drop_conflicts", compat="override")
    ds = ds.assign_coords(time=ds.valid_time)
    ds = ds.swap_dims({"valid_time": "time"})
    ds = ds.drop_vars([
        "valid_time",
        "step",
        "meanSea",
        "heightAboveGround",
        "gribfile_projection"
    ])
    ds = ds.rename({"longitude": "lon", "latitude": "lat"})
    ds.to_netcdf(fname)

    return fname


@timeout(TIMELIMIT)
def download_cycle(cycle, fname, extent=None, fxx_list=None):
    """Download the cycle using Herbie

    Args:
        cycle (str): cycle name in %Y%m%d%H format
        fname (PathLike): Path to save the file in NetCDF format
        extent (list, optional): Geographical extent of the data. Defaults to None.

    Raises:
        Exception: Available data list is empty for a cycle
    """

    if fxx_list is None:
        fxx_list = np.append(np.arange(0, 120, 1), np.arange(120, 384 + 1, 3)).flatten().tolist()

    temp_dir = Path(f"./.tmp_{cycle}")
    if temp_dir.exists():
        gfs_dir = temp_dir / "gfs"
        if gfs_dir.exists():
            shutil.rmtree(gfs_dir)

    def _download_task(fxx):
        # The specific function to execute
        func_download = lambda: download_step(timestamp=cycle2datetime(cycle, fmt=CYCLE_FORMAT), fxx=fxx,
                                              temp_dir=temp_dir)

        # Apply your existing silent/retry logic inside the thread
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=UserWarning)
            return retry(func=func_download)

    with ThreadPoolExecutor(max_workers=10) as executor:
        fns = list(executor.map(_download_task, fxx_list))

    ds = xr.open_mfdataset(fns)

    if extent is not None:
        w, e, s, n = extent
        ds = ds.sel(
            lon=ds.lon.where(
                (ds.lon >= w) & (ds.lon <= e),
                drop=True
            ),
            lat=ds.lat.where(
                (ds.lat >= s) & (ds.lat <= n),
                drop=True
            )
        )

    ds.to_netcdf(fname)
    shutil.rmtree(temp_dir)


def retry(func: callable, retries: int = 5, delay: int = 1, exceptions: Exception = (Exception,),
          logger: logging.Logger = None):
    """Helper function to retry a function

    Args:
        func (callable): A callable function
        retries (int, optional): Number of retries. Defaults to 3.
        delay (int, optional): Delay before next try. Defaults to 1.
        exceptions (Exception, optional): Which exceptions to consider. Defaults to (Exception,).
        logger (logging.Logger, optional): Data logger. Defaults to None.
    """
    if logger is None:
        logger = logging.getLogger("retry")
    else:
        logger = logger

    for attempt in range(1, retries + 1):
        try:
            return func()
        except exceptions as e:
            logger.info(f"Attempt {attempt}/{retries} failed with {e}")
            if attempt == retries:
                raise Exception("All retries failed")
            time.sleep(delay)
            continue


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', stream=sys.stdout)

    gfs = GFS_0p25_1hr()
    if gfs.check():
        gfs.download(extent=[75, 102, 5, 30])

import os
import shutil
from pathlib import Path

import earthaccess
import fsspec
import rasterio
import requests
from pystac_client import Client
from rasterio.io import MemoryFile
from rasterio.merge import merge

# Mapping of product short names for Earthdata access
EARTHDATA_SHORT_NAME = {
    "swot": "SWOT_L2_HR_Raster_2.0",
    "dswx_s1": "OPERA_L3_DSWX-S1_V1",
}

# STAC API endpoints for HAND and ESA WorldCover collections
STAC_CATALOG = {
    "hand": "https://stac.asf.alaska.edu",
    "esa_worldcover": "https://services.terrascope.be/stac/",
}

# STAC collection identifiers
STAC_COLLECTIONS = {
    "hand": "glo-30-hand",
    "esa_worldcover": "urn:eop:VITO:ESA_WorldCover_10m_2021_AWS_V2",
}

# Asset keys for each STAC layer
STAC_ASSEST = {"hand": "data", "esa_worldcover": "ESA_WORLDCOVER_10M_MAP"}

# ESA WorldCover class definitions, labels, and colors
ESA_WORLDCOVER_CLASSES = {
    "classes": [10, 20, 30, 40, 50, 60, 70, 80, 90, 95, 100],
    "labels": [
        "Tree",
        "Shrubland",
        "Grassland",
        "Cropland",
        "Built-up",
        "Bare/sparse",
        "Snow",
        "Permanent",
        "Herbaceous",
        "Mangroves",
        "Moss",
    ],
    "hex_color": [
        "#33a02c",
        "#b15928",
        "#ffff33",
        "#ff7f00",
        "#e31a1c",
        "#d9d9d9",
        "#f7f7f7",
        "#1f78b4",
        "#66c2a5",
        "#00896b",
        "#ffffb2",
    ],
}


def _earthacess_authenticate():
    """Authenticate with NASA Earthdata.

    Returns:
        auth (earthaccess.Auth): Authenticated EarthAccess session object.

    """
    env_list = ["EARTHDATA_USERNAME", "EARTHDATA_PASSWORD"]
    netrc_path = Path.home() / ".netrc"
    persist = False

    # Check if envs are set
    if all(var in os.environ for var in env_list):
        strategy = "environment"
    # Check if .netcdf exist in home dir
    elif netrc_path.exists():
        strategy = "netcdf"
    # Enter in interactive mode
    else:
        strategy = "interactive"
        persist = True

    # Login to earthdata access
    print(f"Login in to earthdata with: {strategy}")
    auth = earthaccess.login(strategy=strategy, persist=persist)
    if auth.authenticated:
        print("Authentication success!")
    else:
        print("Authentication failed!")
    return auth


def download_swot(
    output_dir: str | Path, start_date: str, end_date: str, granule_id: str
) -> list[str] | str:
    """Download SWOT Level-2 high-resolution raster data from NASA Earthdata.

    Args:
        output_dir (str or Path): Directory to save downloaded files.
        start_date (str): Start date in 'YYYY-MM-DD' format.
        end_date (str): End date in 'YYYY-MM-DD' format.
        granule_id (str): Identifier for the specific granule (wildcards supported).

    Returns:
        List[str] or str: Paths to downloaded files or a single file path if only one
        is downloaded.

    """
    _ = _earthacess_authenticate()

    # Output directory
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)

    kwargs = {
        "short_name": EARTHDATA_SHORT_NAME["swot"],
        "temporal": (start_date, end_date),
        "granule_name": f"*100m*{granule_id}*",
    }

    search_results = earthaccess.search_data(**kwargs)
    out = earthaccess.download(search_results, local_path=output_dir)
    return out


def download_dswx_s1(
    output_dir: str | Path, start_date: str, end_date: str, granule_id: str
) -> list[str] | str:
    """Download OPERA Level-3 DSWX-S1 flood mapping products from NASA Earthdata.

    Args:
        output_dir (str or Path): Directory to save downloaded files.
        start_date (str): Start date in 'YYYY-MM-DD' format.
        end_date (str): End date in 'YYYY-MM-DD' format.
        granule_id (str): Identifier for the specific granule (wildcards supported).

    Returns:
        List[str] or str: Paths to downloaded files or a single file path if only one
        is downloaded.

    """
    _ = _earthacess_authenticate()

    # Output directory
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)

    kwargs = {
        "short_name": EARTHDATA_SHORT_NAME["dswx_s1"],
        "temporal": (start_date, end_date),
        "granule_name": f"*{granule_id}*",
    }

    search_results = earthaccess.search_data(**kwargs)
    out = earthaccess.download(search_results, local_path=output_dir)
    return out


def download_stac(
    output_dir: str | Path, aoi_bbox: list | tuple, stac_lyr: str = "hand"
) -> Path:
    """Download and merge geospatial data from a STAC API for a given area of interest.

    Args:
        output_dir (str or Path): Directory to save the merged output.
        aoi_bbox (list or tuple): Bounding box [minX, minY, maxX, maxY] of the area
            of interest.
        stac_lyr (str): Layer key ('hand' or 'esa_worldcover'). Defaults to 'hand'.

    Returns:
        Path: File path to the merged GeoTIFF.

    """
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)

    temp_dir = output_dir / "temp"
    temp_dir.mkdir(exist_ok=True)

    # Connect to the STAC API
    catalog = Client.open(STAC_CATALOG[stac_lyr])

    # Search
    search = catalog.search(
        collections=[STAC_COLLECTIONS[stac_lyr]], bbox=aoi_bbox, limit=10
    )

    # Get items
    items = list(search.items())

    hand_list = []
    for item in items:
        # Download each item
        url = item.assets[STAC_ASSEST[stac_lyr]].href
        print(f"Download URL: {url}")

        if url.startswith("https://") or url.startswith("http://"):
            response = requests.get(url)
            response.raise_for_status()
            with MemoryFile(response.content) as memfile:
                with memfile.open() as src:
                    profile = src.profile
                    temp_output = temp_dir / f"{item.id}.tif"
                    print(f"Saving to: {temp_output}")

                    with rasterio.open(temp_output, "w", **profile) as dst:
                        dst.write(src.read())  # write all bands

        elif url.startswith("s3://"):
            fs = fsspec.filesystem("s3", anon=True)
            with fs.open(url, "rb") as fobj:
                with rasterio.open(fobj) as src:
                    profile = src.profile
                    temp_output = temp_dir / f"{item.id}.tif"
                    print(f"Saving to: {temp_output}")

                    with rasterio.open(temp_output, "w", **profile) as dst:
                        dst.write(src.read())  # write all bands

        else:
            raise ValueError(f"Unknown URL scheme: {url}")

        hand_list.append(temp_output)

    # Merge all HAND tiles over AOI
    src_files_to_mosaic = [rasterio.open(fp) for fp in hand_list]
    mosaic, transform = merge(src_files_to_mosaic)

    # Define the output metadata
    out_meta = src_files_to_mosaic[0].meta.copy()
    out_meta.update(
        {"height": mosaic.shape[1], "width": mosaic.shape[2], "transform": transform}
    )

    # Save the merged file
    merged_output = output_dir / f"{stac_lyr}_merged.tif"
    with rasterio.open(merged_output, "w", **out_meta) as dest:
        dest.write(mosaic)

    # After you are done with temp files:
    shutil.rmtree(temp_dir)

    return merged_output

from pathlib import Path
from typing import NamedTuple, Tuple

import fiona
import geopandas as gpd
import numpy as np


class GRID(NamedTuple):
    """NamedTuple to store grid coordinates and metadata for MGRS tiles.

    Parameters
    ----------
    x : np.ndarray
        Array of x coordinates.
    y : np.ndarray
        Array of y coordinates.
    bounds : tuple of float
        The bounds of the MGRS tile (minx, miny, maxx, maxy).
    epsg : int
        EPSG code for the tile's coordinate reference system.

    """

    x: np.array
    y: np.array
    bounds: Tuple[float, float, float, float]
    epsg: int


def read_database(input_file: str | Path) -> gpd.GeoDataFrame:
    """Read the first layer of a SQLite database file into a GeoDataFrame.

    Parameters
    ----------
    input_file : str or Path
        Path to the SQLite database file.

    Returns
    -------
    gpd.GeoDataFrame
        GeoDataFrame of the first layer in the database.

    Raises
    ------
    ValueError
        If the database file cannot be opened or read, or if there are no layers in the
        file.

    """
    input_file = Path(input_file)

    # Get sqlite layers
    layers = fiona.listlayers(input_file)

    # Read database
    try:
        gdf = gpd.read_file(input_file, layer=layers[0])
    except Exception as e:
        raise ValueError(f"Cannot open input file {input_file}: {e}")

    return gdf


def get_mgrs_tile_coords(tile_df: gpd.GeoDataFrame, resolution: int = 90) -> GRID:
    """Generate grid based on the bounds of an MGRS tile and resolution.

    Parameters
    ----------
    tile_df : gpd.GeoDataFrame
        GeoDataFrame containing MGRS tile geometries and the 'epsg' column.
    resolution : int
        Grid resolution in the units of the tile's CRS. The default is 90 meters.

    Returns
    -------
    GRID
        NamedTuple containing x and y coordinate arrays, bounds, and the EPSG code.

    Raises
    ------
    ValueError
        If the GeoDataFrame does not contain an 'epsg' column or if the CRS does
        not match the EPSG code.

    """
    if "epsg" in tile_df.columns:
        tile_epsg = tile_df.epsg.values[0]
        crs_epsg = tile_df.crs.to_epsg()

        if crs_epsg != tile_epsg:
            tile_df = tile_df.to_crs(epsg=tile_epsg)
    else:
        raise ValueError("MGRS tile is expected to have a  EPSG code column.")

    # Get bounds
    bounds = np.rint(tile_df.geometry.bounds)

    minx = bounds.minx.iloc[0]
    miny = bounds.miny.iloc[0]
    maxx = bounds.maxx.iloc[0]
    maxy = bounds.maxy.iloc[0]

    # Get grid size
    size_y = int((maxy - miny) / resolution)
    size_x = int((maxx - minx) / resolution)

    # Create linspace coordinates
    x_coords = np.linspace(minx, maxx, size_x)
    y_coords = np.linspace(miny, maxy, size_y)

    # Create and return namedtuple
    return GRID(x=x_coords, y=y_coords, bounds=bounds.values, epsg=tile_epsg)

from typing import Tuple, Literal, Dict, Hashable, Any, List
from datetime import datetime
import os
from os import DirEntry
from dataclasses import dataclass, asdict
import csv

from osgeo import gdal
import fiona
from fiona.crs import to_string

@dataclass
class Metadata:
    name: str
    data_type: Literal["vector", "raster"]
    format: str
    volume_in_MB: float
    spatial_reference: str
    extent: Tuple[float]
    creation_date: str
    update_date: str

def vector_data_reader(sourcefile: DirEntry) -> Dict[Hashable, Any]:
    with fiona.open(sourcefile.name, "r") as file:
        data_type: str = "vector"
        extent: Tuple[float] = file.bounds
        format: str = file.driver
        spatial_reference: str = to_string(file.crs)
        return {"extent": extent,
                "format": format, 
                "spatial_reference": spatial_reference,
                "data_type": data_type}
    
def raster_data_reader(sourcefile: DirEntry) -> Dict[Hashable, Any]:
    file = gdal.Open(sourcefile.name)
    data_type: str = "raster"
    spatial_reference: str = file.GetProjection()
    format: str = file.GetDriver().LongName

    xmin, xres, _, ymax, yres, _ = file.GetGeoTransform()
    xmax = xmin + file.RasterXSize * xres
    ymin = ymax + file.RasterYSize * yres
    extent: Tuple[float] = (xmin, ymin, xmax, ymax)
    return {"extent": extent,
            "format": format, 
            "spatial_reference": spatial_reference,
            "data_type": data_type}

def metadata_creator(
        name: str,
        non_spatial_information: os.stat_result,
        spatial_information: Dict[Hashable, Any]
    ) -> Metadata:
    return Metadata(
        name = name,
        data_type = spatial_information["data_type"],
        format = spatial_information["format"],
        volume_in_MB = round((non_spatial_information.st_size / 1024) / 1024, 2),
        spatial_reference = spatial_information["spatial_reference"],
        extent = spatial_information["extent"],
        creation_date = datetime.fromtimestamp(non_spatial_information.st_ctime).ctime(),
        update_date = datetime.fromtimestamp(non_spatial_information.st_atime).ctime()
    )

def parse_metadata(sourcefile: DirEntry) -> Metadata:
    non_spatial_information = sourcefile.stat()
    name = sourcefile.name
    if sourcefile.name.endswith(".gpkg") or\
        sourcefile.name.endswith(".shp") or\
        sourcefile.name.endswith(".geojson"):
        spatial_information = vector_data_reader(sourcefile)
        return metadata_creator(name, non_spatial_information, spatial_information)
    elif sourcefile.name.endswith(".tif") or\
        sourcefile.name.endswith(".img"):
        spatial_information = raster_data_reader(sourcefile)  
        return metadata_creator(name, non_spatial_information, spatial_information)
    else:
        return

def scan_directory(path: str = None) -> None:
    if path is None:
        path = os.path.dirname(os.path.abspath(__file__))
    
    metadata_store: List[Dict[Hashable, Any]] = list()
    with os.scandir(path=path) as scanner:
        for sourcefile in scanner:
            metadata = parse_metadata(sourcefile)
            if metadata is not None:
                metadata_dict = asdict(metadata)
                metadata_store.append(metadata_dict)

    with open("metadata.csv", "w", newline="") as csv_file:
        fields_names = ["name", "data_type", "format", "volume_in_MB",
                        "spatial_reference", "extent", "creation_date", "update_date"]
        writer = csv.DictWriter(f = csv_file, fieldnames=fields_names)
        writer.writeheader()
        writer.writerows(metadata_store)


if __name__ == "__main__":
    scan_directory()
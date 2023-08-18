import pathlib
import urllib.request

from marda_extractors_api import extract

# Download an example MPR file from the registry
download_path = pathlib.Path(__file__).parent / "data" / "example.mpr"
url = "https://github.com/the-grey-group/datalab/raw/main/pydatalab/example_data/echem/jdb11-1_c3_gcpl_5cycles_2V-3p8V_C-24_data_C09.mpr"
if not download_path.exists():
    download_path.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(url, download_path)


# Extract it in Python mode (default)
# data = extract(download_path, "biologic-mpr")
# print(data)

# Extract it in CLI mode
extract(download_path, "biologic-mpr", preferred_mode="cli", output_path="data/test.nc")

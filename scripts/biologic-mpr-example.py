import pathlib
import urllib.request

from marda_extractors_api import extract

download_path = pathlib.Path(__file__).parent / "data" / "example.mpr"
url = "https://github.com/marda-alliance/metadata_extractors_registry/blob/main/marda_registry/data/lfs/biologic-mpr/ca.mpr"
if not download_path.exists():
    download_path.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(url, download_path)

data = extract(download_path, "biologic-mpr")

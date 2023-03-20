import urllib.request
from pathlib import Path

import pytest

from marda_extractors_api import extract


@pytest.fixture
def test_mpr() -> Path:
    download_path = Path(__file__).parent / "data" / "example.mpr"
    url = "https://github.com/the-grey-group/datalab/blob/main/pydatalab/example_data/echem/jdb11-1_c3_gcpl_5cycles_2V-3p8V_C-24_data_C09.mpr?raw=true"
    if not download_path.exists():
        download_path.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(url, download_path)

    return download_path


@pytest.mark.parametrize("preferred_mode", ["python", "cli"])
def test_extract(tmp_path, preferred_mode, test_mpr):
    data = extract(
        test_mpr,
        "biologic-mpr",
        output_file=tmp_path,
        preferred_mode=preferred_mode,
    )
    if preferred_mode == "python":
        assert data
    else:
        assert tmp_path.exists()

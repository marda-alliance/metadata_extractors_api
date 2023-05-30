import urllib.request
from pathlib import Path

import pytest

from marda_extractors_api import MardaExtractor, SupportedExecutionMethod, extract


@pytest.fixture
def test_mpr() -> Path:
    download_path = Path(__file__).parent / "data" / "example.mpr"
    url = "https://github.com/the-grey-group/datalab/blob/main/pydatalab/example_data/echem/jdb11-1_c3_gcpl_5cycles_2V-3p8V_C-24_data_C09.mpr?raw=true"
    if not download_path.exists():
        download_path.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(url, download_path)

    return download_path


@pytest.mark.parametrize(
    "preferred_mode", [SupportedExecutionMethod.PYTHON, SupportedExecutionMethod.CLI]
)
def test_extract(tmp_path, preferred_mode, test_mpr):
    output_file = tmp_path / "example.hdf5"
    data = extract(
        test_mpr,
        "biologic-mpr",
        output_file=output_file,
        preferred_mode=preferred_mode,
    )
    if preferred_mode == SupportedExecutionMethod.PYTHON:
        assert data
    else:
        assert output_file.exists()


def test_marda_extractor_template_method():
    command = MardaExtractor.apply_template_args(
        "parse --type=example {{ input_path }}",
        method=SupportedExecutionMethod.CLI,
        file_type="example",
        file_path=Path("example.txt"),
        output_file=Path("example.json"),
    )

    assert command == "parse --type=example example.txt"


def test_marda_extractor_python_method():
    function, args, kwargs = MardaExtractor._prepare_python(
        'extract("biologic-mpr", "/path/to/file")'
    )

    assert function == ["extract"]
    assert args == ["biologic-mpr", "/path/to/file"]
    assert kwargs == {}

    function, args, kwargs = MardaExtractor._prepare_python(
        "extract('biologic-mpr', '/path/to/file')"
    )

    assert function == ["extract"]
    assert args == ["biologic-mpr", "/path/to/file"]
    assert kwargs == {}

    function, args, kwargs = MardaExtractor._prepare_python(
        'example.extractors.extract("example.txt", type="example")'
    )

    assert function == ["example", "extractors", "extract"]
    assert args == ["example.txt"]
    assert kwargs == {"type": "example"}

    function, args, kwargs = MardaExtractor._prepare_python(
        'extract(filename="example.txt", type="example")'
    )

    assert function == ["extract"]
    assert args == []
    assert kwargs == {"filename": "example.txt", "type": "example"}

    with pytest.raises(RuntimeError):
        function, args, kwargs = MardaExtractor._prepare_python(
            'extract(filename="example.txt", type={"test": "example", "dictionary": "example"})'
        )

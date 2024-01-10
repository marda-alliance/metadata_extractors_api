import urllib.request
from pathlib import Path

import pytest

from marda_extractors_api import MardaExtractor, SupportedExecutionMethod, extract


@pytest.fixture
def test_mpr_urls():
    return [
        "https://github.com/the-grey-group/datalab/raw/main/pydatalab/example_data/echem/jdb11-1_c3_gcpl_5cycles_2V-3p8V_C-24_data_C09.mpr",
        "https://github.com/marda-alliance/metadata_extractors_registry/raw/main/marda_registry/data/lfs/biologic-mpr/peis.mpr",
        "https://github.com/marda-alliance/metadata_extractors_registry/raw/main/marda_registry/data/lfs/biologic-mpr/ca.mpr",
        "https://github.com/marda-alliance/metadata_extractors_registry/raw/main/marda_registry/data/lfs/biologic-mpr/gcpl.mpr",
    ]


@pytest.fixture
def get_test_mprs(test_mpr_urls) -> Path:
    download_dir = Path(__file__).parent / "data"

    if not download_dir.exists():
        download_dir.mkdir(parents=True, exist_ok=True)

    for url in test_mpr_urls:
        if not (download_dir / url.split("/")[-1]).exists():
            urllib.request.urlretrieve(url, download_dir / url.split("/")[-1])

    return download_dir


@pytest.fixture
def test_mprs(get_test_mprs):
    return get_test_mprs.glob("*.mpr")


@pytest.mark.parametrize("preferred_mode", ["python", "cli"])
def test_biologic_extract(tmp_path, preferred_mode, test_mprs):
    for ind, test_mpr in enumerate(test_mprs):
        output_path = tmp_path / test_mpr.name.replace(".mpr", ".nc")
        data = extract(
            test_mpr,
            "biologic-mpr",
            output_path=output_path,
            preferred_mode=preferred_mode,
            install=(ind == 0),
        )
        if preferred_mode == "python":
            assert data
        else:
            assert output_path.exists()


def test_biologic_extract_from_url(tmp_path, test_mpr_urls):
    for ind, test_mpr in enumerate(test_mpr_urls):
        output_path = f"mpr-{ind}.nc"
        data = extract(
            test_mpr,
            "biologic-mpr",
            output_path=output_path,
            preferred_mode="python",
            install=(ind == 0),
        )
        assert data


def test_biologic_extract_no_registry(test_mprs):
    for ind, test_mpr in enumerate(test_mprs):
        output_path = f"mpr-{ind}.nc"
        data = extract(
            test_mpr,
            "biologic-mpr",
            output_path=output_path,
            preferred_mode="python",
            install=(ind == 0),
            extractor_definition={
                "id": "yadg",
                "supported_filetypes": [{"id": "biologic-mpr"}],
                "usage": [
                    {
                        "method": "python",
                        "setup": "yadg",
                        "command": "yadg.extractors.extract({{ input_type }}, {{ input_path }})",
                    }
                ],
                "installation": [
                    {
                        "method": "pip",
                        "requires_python": ">=3.9",
                        "requirements": None,
                        "packages": ["yadg~=5.0"],
                    }
                ],
            },
        )
        assert data


def test_marda_extractor_template_method():
    command = MardaExtractor.apply_template_args(
        "parse --type=example {{ input_path }}",
        method=SupportedExecutionMethod.CLI,
        input_type="example",
        input_path=Path("example.txt"),
        output_path=Path("example.json"),
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

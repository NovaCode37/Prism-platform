import pytest
from PIL import Image, TiffImagePlugin

from modules import metadata_extractor
from modules.metadata_extractor import (
    _dms_to_decimal,
    _parse_exif_gps,
    _parse_xmp_coord,
    _to_float,
    _xmp_frac,
    extract_docx_metadata,
    extract_image_metadata,
    extract_metadata,
    extract_pdf_metadata,
)
from modules.module_status import ERROR, OK, SKIPPED


def test_dms_to_decimal_handles_south_and_west_ref():
    assert _dms_to_decimal((12, 30, 0), "S") == -12.5
    assert _dms_to_decimal((45, 30, 0), "W") == -45.5
    assert _dms_to_decimal((51, 28, 12.34), "N") == pytest.approx(51.470094)


def test_xmp_fraction_and_coord_parsing():
    assert _xmp_frac("3/2") == 1.5
    assert _xmp_frac("12.5") == 12.5
    assert _to_float((3, 2)) == 1.5

    assert _parse_xmp_coord("51, 28, 12.34 N") == pytest.approx(51.470094)
    assert _parse_xmp_coord("12, 30, 0 S") == -12.5
    assert _parse_xmp_coord("44, 51, 15.5 W") == pytest.approx(-44.854306)


def test_parse_exif_gps_assembles_coordinate_pair():
    gps_ifd = {
        1: "S",
        2: ((12, 1), (30, 1), (0, 1)),
        3: "W",
        4: ((45, 1), (30, 1), (0, 1)),
        6: (123, 1),
    }

    assert _parse_exif_gps(gps_ifd) == {"lat": -12.5, "lng": -45.5, "altitude": 123.0}


def test_extract_image_metadata_reads_known_exif_and_gps(tmp_path):
    img_path = tmp_path / "gps.jpg"
    exif = Image.Exif()
    exif[34853] = {
        1: "S",
        2: (
            TiffImagePlugin.IFDRational(12, 1),
            TiffImagePlugin.IFDRational(30, 1),
            TiffImagePlugin.IFDRational(0, 1),
        ),
        3: "W",
        4: (
            TiffImagePlugin.IFDRational(45, 1),
            TiffImagePlugin.IFDRational(30, 1),
            TiffImagePlugin.IFDRational(0, 1),
        ),
        6: TiffImagePlugin.IFDRational(123, 1),
    }
    exif[0x010F] = "Example Camera"
    exif[0x0131] = "Example Software"
    exif[0x013B] = "Example Artist"

    Image.new("RGB", (20, 20), color="white").save(img_path, exif=exif)

    result = extract_metadata(str(img_path))

    assert result["format"] == "JPEG"
    assert result["gps"] == {"lat": -12.5, "lng": -45.5, "altitude": 123.0}
    assert result["raw_exif"]
    assert result["software"] == "Example Software"
    assert result["author"] == "Example Artist"
    assert result["error"] is None
    assert result["status"] == OK


def test_extract_image_metadata_without_metadata_returns_clean_result(tmp_path):
    img_path = tmp_path / "empty.jpg"
    Image.new("RGB", (20, 20), color="white").save(img_path)

    result = extract_image_metadata(str(img_path))

    assert result["format"] == "JPEG"
    assert result["gps"] is None
    assert result["raw_exif"] == {}
    assert result["error"] is None
    assert result["status"] == OK


def test_extract_image_metadata_handles_malformed_exif_block(tmp_path, monkeypatch):
    img_path = tmp_path / "bad_exif.jpg"
    Image.new("RGB", (20, 20), color="white").save(img_path)

    class BrokenExif:
        def items(self):
            raise ValueError("bad exif block")

        def get_ifd(self, *args, **kwargs):
            raise ValueError("bad exif block")

    monkeypatch.setattr("PIL.Image.Image.getexif", lambda self: BrokenExif())

    result = extract_image_metadata(str(img_path))

    assert isinstance(result, dict)
    assert result["error"] is not None
    assert result["status"] == ERROR


def test_extract_metadata_rejects_corrupt_file_without_raising(tmp_path):
    bad_path = tmp_path / "broken.jpg"
    bad_path.write_bytes(b"not a real jpeg")

    result = extract_image_metadata(str(bad_path))

    assert isinstance(result, dict)
    assert result["error"] is not None
    assert result["status"] == ERROR


def test_extract_metadata_handles_unknown_file_type():
    result = extract_metadata("notes.txt")

    assert result["file"] == "notes.txt"
    assert result["error"].startswith("Unsupported file type:")
    assert result["status"] == ERROR


@pytest.mark.parametrize(
    "flag, func, filename, hint",
    [
        ("PILLOW_AVAILABLE", extract_image_metadata, "photo.jpg", "pip install Pillow"),
        ("PYPDF_AVAILABLE", extract_pdf_metadata, "doc.pdf", "pip install pypdf"),
        ("DOCX_AVAILABLE", extract_docx_metadata, "doc.docx", "pip install python-docx"),
    ],
)
def test_missing_library_is_skipped_not_error(tmp_path, monkeypatch, flag, func, filename, hint):
    path = tmp_path / filename
    path.write_bytes(b"placeholder")
    monkeypatch.setattr(metadata_extractor, flag, False)

    result = func(str(path))

    assert result["status"] == SKIPPED
    assert hint in result["status_reason"]
    assert result["error"] is None


def test_corrupt_pdf_is_error(tmp_path):
    path = tmp_path / "broken.pdf"
    path.write_bytes(b"not a real pdf")

    result = extract_pdf_metadata(str(path))

    assert result["status"] == ERROR
    assert result["error"]


def test_corrupt_docx_is_error(tmp_path):
    path = tmp_path / "broken.docx"
    path.write_bytes(b"not a real docx")

    result = extract_docx_metadata(str(path))

    assert result["status"] == ERROR
    assert result["error"]


def _blank_pdf(path, metadata=None):
    import pypdf

    writer = pypdf.PdfWriter()
    writer.add_blank_page(width=72, height=72)
    if metadata:
        writer.add_metadata(metadata)
    with open(path, "wb") as f:
        writer.write(f)


def test_pdf_with_metadata_is_ok(tmp_path):
    path = tmp_path / "tagged.pdf"
    _blank_pdf(path, {"/Title": "Report", "/Author": "Jane Doe"})

    result = extract_pdf_metadata(str(path))

    assert result["status"] == OK
    assert result["error"] is None
    assert result["pages"] == 1
    assert result["title"] == "Report"
    assert result["author"] == "Jane Doe"


def test_pdf_without_metadata_is_ok(tmp_path):
    path = tmp_path / "plain.pdf"
    _blank_pdf(path)

    result = extract_pdf_metadata(str(path))

    assert result["status"] == OK
    assert result["error"] is None
    assert result["title"] is None
    assert result["author"] is None


def test_docx_with_metadata_is_ok(tmp_path):
    import docx

    path = tmp_path / "tagged.docx"
    document = docx.Document()
    document.core_properties.author = "Jane Doe"
    document.save(path)

    result = extract_docx_metadata(str(path))

    assert result["status"] == OK
    assert result["error"] is None
    assert result["author"] == "Jane Doe"

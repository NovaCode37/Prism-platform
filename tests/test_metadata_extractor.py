import pytest
from PIL import Image, TiffImagePlugin

from modules.metadata_extractor import (
    _dms_to_decimal,
    _parse_exif_gps,
    _parse_xmp_coord,
    _to_float,
    _xmp_frac,
    extract_image_metadata,
    extract_metadata,
)



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
    assert result["status"] == "ok"
    assert result["error"] is None


def test_extract_image_metadata_without_metadata_returns_clean_result(tmp_path):
    img_path = tmp_path / "empty.jpg"
    Image.new("RGB", (20, 20), color="white").save(img_path)

    result = extract_image_metadata(str(img_path))

    assert result["format"] == "JPEG"
    assert result["gps"] is None
    assert result["raw_exif"] == {}
    assert result["status"] == "ok"
    assert result["error"] is None


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
    assert result["status"] == "error"
    assert result["error"] is not None


def test_extract_metadata_rejects_corrupt_file_without_raising(tmp_path):
    bad_path = tmp_path / "broken.jpg"
    bad_path.write_bytes(b"not a real jpeg")

    result = extract_image_metadata(str(bad_path))

    assert isinstance(result, dict)
    assert result["status"] == "error"
    assert result["error"] is not None


def test_extract_metadata_handles_unknown_file_type():
    result = extract_metadata("notes.txt")

    assert result["file"] == "notes.txt"
    assert result["status"] == "error"
    assert result["error"].startswith("Unsupported file type:")


def test_extract_image_metadata_missing_pillow_is_skipped(monkeypatch, tmp_path):
    import modules.metadata_extractor as mod

    monkeypatch.setattr(mod, "PILLOW_AVAILABLE", False)
    test_path = tmp_path / "dummy.jpg"
    test_path.write_bytes(b"dummy")

    result = mod.extract_image_metadata(str(test_path))

    assert result["status"] == "skipped"
    assert result["status_reason"] == "Pillow not installed: pip install Pillow"
    assert result["error"] is None


def test_extract_pdf_metadata_missing_pypdf_is_skipped(monkeypatch, tmp_path):
    import modules.metadata_extractor as mod

    monkeypatch.setattr(mod, "PYPDF_AVAILABLE", False)
    test_path = tmp_path / "dummy.pdf"
    test_path.write_bytes(b"dummy")

    result = mod.extract_pdf_metadata(str(test_path))

    assert result["status"] == "skipped"
    assert result["status_reason"] == "pypdf not installed: pip install pypdf"
    assert result["error"] is None


def test_extract_docx_metadata_missing_docx_is_skipped(monkeypatch, tmp_path):
    import modules.metadata_extractor as mod

    monkeypatch.setattr(mod, "DOCX_AVAILABLE", False)
    test_path = tmp_path / "dummy.docx"
    test_path.write_bytes(b"dummy")

    result = mod.extract_docx_metadata(str(test_path))

    assert result["status"] == "skipped"
    assert result["status_reason"] == "python-docx not installed: pip install python-docx"
    assert result["error"] is None


def test_extract_pdf_metadata_corrupt_file_is_error(tmp_path):
    pytest.importorskip("pypdf")
    bad_path = tmp_path / "broken.pdf"
    bad_path.write_bytes(b"not a valid pdf content")

    result = extract_metadata(str(bad_path))

    assert result["status"] == "error"
    assert result["error"] is not None


def test_extract_docx_metadata_corrupt_file_is_error(tmp_path):
    pytest.importorskip("docx")
    bad_path = tmp_path / "broken.docx"
    bad_path.write_bytes(b"not a valid zip or docx content")

    result = extract_metadata(str(bad_path))

    assert result["status"] == "error"
    assert result["error"] is not None


def test_extract_pdf_metadata_valid_with_and_without_metadata(tmp_path):
    pypdf = pytest.importorskip("pypdf")

    # 1. Valid PDF with metadata
    writer = pypdf.PdfWriter()
    writer.add_blank_page(width=100, height=100)
    writer.add_metadata({"/Title": "Test Title", "/Author": "Test Author"})
    with_meta_path = tmp_path / "with_meta.pdf"
    with open(with_meta_path, "wb") as f:
        writer.write(f)

    res_meta = extract_metadata(str(with_meta_path))
    assert res_meta["status"] == "ok"
    assert res_meta["error"] is None
    assert res_meta["title"] == "Test Title"
    assert res_meta["author"] == "Test Author"
    assert res_meta["pages"] == 1

    # 2. Valid PDF without metadata
    writer_blank = pypdf.PdfWriter()
    writer_blank.add_blank_page(width=100, height=100)
    no_meta_path = tmp_path / "no_meta.pdf"
    with open(no_meta_path, "wb") as f:
        writer_blank.write(f)

    res_no_meta = extract_metadata(str(no_meta_path))
    assert res_no_meta["status"] == "ok"
    assert res_no_meta["error"] is None
    assert res_no_meta["pages"] == 1
    assert res_no_meta["title"] is None


def test_extract_docx_metadata_valid_with_and_without_metadata(tmp_path):
    docx = pytest.importorskip("docx")

    # 1. Valid DOCX with metadata
    doc = docx.Document()
    doc.core_properties.title = "DOCX Sample"
    doc.core_properties.author = "Docx Author"
    with_meta_path = tmp_path / "with_meta.docx"
    doc.save(str(with_meta_path))

    res_meta = extract_metadata(str(with_meta_path))
    assert res_meta["status"] == "ok"
    assert res_meta["error"] is None
    assert res_meta["title"] == "DOCX Sample"
    assert res_meta["author"] == "Docx Author"

    # 2. Valid DOCX without metadata
    doc_blank = docx.Document()
    no_meta_path = tmp_path / "no_meta.docx"
    doc_blank.save(str(no_meta_path))

    res_no_meta = extract_metadata(str(no_meta_path))
    assert res_no_meta["status"] == "ok"
    assert res_no_meta["error"] is None



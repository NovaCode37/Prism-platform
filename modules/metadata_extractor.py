import os
import re
import struct
import xml.etree.ElementTree as ET
from typing import Dict, Any, Optional
from datetime import datetime


def _extract_xmp(file_path: str) -> Optional[str]:
    try:
        with open(file_path, "rb") as f:
            data = f.read()
        marker = b"http://ns.adobe.com/xap/1.0/"
        idx = data.find(marker)
        if idx == -1:
            return None
        start = data.find(b"<", idx)
        if start == -1:
            return None
        end = data.find(b"</x:xmpmeta>", start)
        if end != -1:
            end += len(b"</x:xmpmeta>")
        else:
            end = data.find(b"<?xpacket end", start)
            if end != -1:
                end = data.find(b">", end) + 1
        return data[start:end].decode("utf-8", errors="ignore") if end > start else None
    except Exception:
        return None


def _xmp_frac(s: str) -> Optional[float]:
    s = s.strip()
    try:
        if "/" in s:
            n, d = s.split("/", 1)
            return float(n) / float(d) if float(d) else None
        return float(s)
    except Exception:
        return None


def _parse_xmp_coord(raw: str) -> Optional[float]:
    raw = raw.strip()
    ref = None
    if raw and raw[-1] in "NSEWnsew":
        ref = raw[-1].upper()
        raw = raw[:-1].strip()
    parts = re.split(r"[,\s]+", raw)
    try:
        vals = [_xmp_frac(p) for p in parts if p]
        vals = [v for v in vals if v is not None]
        d = vals[0] if len(vals) > 0 else 0.0
        m = vals[1] if len(vals) > 1 else 0.0
        s = vals[2] if len(vals) > 2 else 0.0
        dec = d + m / 60 + s / 3600
        if ref in ("S", "W"):
            dec = -dec
        return round(dec, 6)
    except Exception:
        return None


def _parse_xmp_metadata(xmp_str: str) -> Dict[str, Any]:
    result: Dict[str, Any] = {"raw_exif": {}, "gps": None, "author": None, "software": None, "timestamps": {}}
    try:
        root = ET.fromstring(xmp_str)

        NS = {
            "rdf":       "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
            "exif":      "http://ns.adobe.com/exif/1.0/",
            "tiff":      "http://ns.adobe.com/tiff/1.0/",
            "xmp":       "http://ns.adobe.com/xap/1.0/",
            "dc":        "http://purl.org/dc/elements/1.1/",
            "photoshop": "http://ns.adobe.com/photoshop/1.0/",
            "Iptc4xmpCore": "http://iptc.org/std/Iptc4xmpCore/1.0/xmlns/",
        }
        BRACE = {f"{{{v}}}": k for k, v in NS.items()}
        RDF_NS = NS["rdf"]

        def resolve(tag: str) -> Optional[str]:
            for brace, prefix in BRACE.items():
                if tag.startswith(brace):
                    return f"{prefix}:{tag[len(brace):]}"
            return None

        clean: Dict[str, str] = {}

        for desc in root.iter(f"{{{RDF_NS}}}Description"):
            for attr, val in desc.attrib.items():
                if attr == f"{{{RDF_NS}}}about" or not val:
                    continue
                r = resolve(attr)
                if r and not r.startswith("rdf:"):
                    clean[r] = val

            for child in desc:
                r = resolve(child.tag)
                if not r or r.startswith("rdf:"):
                    continue
                if child.text and child.text.strip():
                    clean[r] = child.text.strip()
                else:
                    for li in child.iter(f"{{{RDF_NS}}}li"):
                        if li.text and li.text.strip():
                            clean[r] = li.text.strip()
                            break

        result["raw_exif"] = clean

        lat_raw = clean.get("exif:GPSLatitude")
        lon_raw = clean.get("exif:GPSLongitude")
        if lat_raw and lon_raw:
            lat = _parse_xmp_coord(lat_raw)
            lng = _parse_xmp_coord(lon_raw)
            if lat is not None and lng is not None:
                result["gps"] = {"lat": lat, "lng": lng}

        result["author"] = (
            clean.get("dc:rights")
            or clean.get("exif:Copyright")
            or clean.get("dc:creator")
            or clean.get("photoshop:Credit")
        )
        result["software"] = clean.get("xmp:CreatorTool") or clean.get("tiff:Software")

        for field in ("exif:DateTimeOriginal", "xmp:CreateDate", "xmp:ModifyDate"):
            if clean.get(field):
                result["timestamps"][field.split(":")[-1]] = clean[field]

    except Exception:
        pass
    return result


def _to_float(val) -> Optional[float]:
    try:
        if hasattr(val, 'numerator'):
            return val.numerator / val.denominator if val.denominator else None
        return float(val)
    except Exception:
        return None


def _dms_to_decimal(dms_tuple, ref: str) -> Optional[float]:
    try:
        d = _to_float(dms_tuple[0])
        m = _to_float(dms_tuple[1])
        s = _to_float(dms_tuple[2])
        if None in (d, m, s):
            return None
        decimal = d + m / 60 + s / 3600
        if ref in ("S", "W"):
            decimal = -decimal
        return round(decimal, 6)
    except Exception:
        return None


def _parse_exif_gps(gps_ifd: Dict) -> Optional[Dict]:
    try:
        from PIL.ExifTags import GPSTAGS
        named = {GPSTAGS.get(k, k): v for k, v in gps_ifd.items()}

        lat_ref = named.get("GPSLatitudeRef") or gps_ifd.get(1)
        lat_dms = named.get("GPSLatitude") or gps_ifd.get(2)
        lon_ref = named.get("GPSLongitudeRef") or gps_ifd.get(3)
        lon_dms = named.get("GPSLongitude") or gps_ifd.get(4)

        if not (lat_dms and lon_dms and lat_ref and lon_ref):
            return None

        lat = _dms_to_decimal(lat_dms, str(lat_ref))
        lng = _dms_to_decimal(lon_dms, str(lon_ref))
        if lat is None or lng is None:
            return None

        result: Dict = {"lat": lat, "lng": lng}

        alt_val = named.get("GPSAltitude") or gps_ifd.get(6)
        if alt_val is not None:
            alt = _to_float(alt_val)
            if alt is not None:
                result["altitude"] = round(alt, 1)

        return result
    except Exception:
        return None


def extract_image_metadata(file_path: str) -> Dict[str, Any]:
    result = {
        "file": os.path.basename(file_path),
        "format": None,
        "size_bytes": None,
        "dimensions": None,
        "camera": {},
        "gps": None,
        "timestamps": {},
        "software": None,
        "author": None,
        "raw_exif": {},
        "error": None,
    }

    try:
        from PIL import Image
        from PIL.ExifTags import TAGS, GPSTAGS

        result["size_bytes"] = os.path.getsize(file_path)

        with Image.open(file_path) as img:
            result["format"] = img.format
            result["dimensions"] = {"width": img.width, "height": img.height}

            exif = img.getexif()

            if exif:
                decoded = {}
                for tag_id, value in exif.items():
                    tag = TAGS.get(tag_id, str(tag_id))
                    try:
                        decoded[tag] = str(value) if not isinstance(value, (int, float, str)) else value
                    except Exception:
                        pass

                gps_ifd = exif.get_ifd(0x8825)
                if gps_ifd:
                    result["gps"] = _parse_exif_gps(gps_ifd)

                result["raw_exif"] = decoded

                cam = {}
                if decoded.get("Make"):
                    cam["make"] = str(decoded["Make"]).strip()
                if decoded.get("Model"):
                    cam["model"] = str(decoded["Model"]).strip()
                if decoded.get("LensModel"):
                    cam["lens"] = str(decoded["LensModel"]).strip()
                if decoded.get("FocalLength"):
                    cam["focal_length"] = str(decoded["FocalLength"])
                if decoded.get("ExposureTime"):
                    cam["exposure"] = str(decoded["ExposureTime"])
                if decoded.get("FNumber"):
                    cam["aperture"] = f"f/{decoded['FNumber']}"
                if decoded.get("ISOSpeedRatings"):
                    cam["iso"] = str(decoded["ISOSpeedRatings"])
                result["camera"] = cam

                ts = {}
                for field in ("DateTimeOriginal", "DateTimeDigitized", "DateTime"):
                    if decoded.get(field):
                        ts[field] = str(decoded[field])
                result["timestamps"] = ts

                result["software"] = decoded.get("Software")
                result["author"] = decoded.get("Artist") or decoded.get("Copyright")

            if not result["gps"] or not result["raw_exif"]:
                xmp_str = _extract_xmp(file_path)
                if xmp_str:
                    xmp = _parse_xmp_metadata(xmp_str)
                    if not result["gps"]:
                        result["gps"] = xmp.get("gps")
                    if not result["raw_exif"]:
                        result["raw_exif"] = xmp.get("raw_exif", {})
                    if not result["author"]:
                        result["author"] = xmp.get("author")
                    if not result["software"]:
                        result["software"] = xmp.get("software")
                    if not result["timestamps"]:
                        result["timestamps"] = xmp.get("timestamps", {})

    except ImportError:
        result["error"] = "Pillow not installed: pip install Pillow"
    except Exception as e:
        result["error"] = str(e)

    return result


def extract_pdf_metadata(file_path: str) -> Dict[str, Any]:
    result = {
        "file": os.path.basename(file_path),
        "format": "PDF",
        "size_bytes": os.path.getsize(file_path),
        "pages": None,
        "author": None,
        "creator": None,
        "producer": None,
        "subject": None,
        "title": None,
        "keywords": None,
        "created": None,
        "modified": None,
        "gps": None,
        "error": None,
    }

    try:
        import pypdf
        with open(file_path, "rb") as f:
            reader = pypdf.PdfReader(f)
            result["pages"] = len(reader.pages)
            meta = reader.metadata
            if meta:
                result["author"]   = meta.get("/Author")
                result["creator"]  = meta.get("/Creator")
                result["producer"] = meta.get("/Producer")
                result["subject"]  = meta.get("/Subject")
                result["title"]    = meta.get("/Title")
                result["keywords"] = meta.get("/Keywords")
                result["created"]  = str(meta.get("/CreationDate", "")).strip("D:").split("+")[0]
                result["modified"] = str(meta.get("/ModDate", "")).strip("D:").split("+")[0]
    except ImportError:
        try:
            import PyPDF2
            with open(file_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                result["pages"] = len(reader.pages)
                meta = reader.metadata
                if meta:
                    result["author"]   = meta.get("/Author")
                    result["creator"]  = meta.get("/Creator")
                    result["producer"] = meta.get("/Producer")
                    result["title"]    = meta.get("/Title")
        except ImportError:
            result["error"] = "pypdf not installed: pip install pypdf"
        except Exception as e:
            result["error"] = str(e)
    except Exception as e:
        result["error"] = str(e)

    return result


def extract_docx_metadata(file_path: str) -> Dict[str, Any]:
    result = {
        "file": os.path.basename(file_path),
        "format": "DOCX",
        "size_bytes": os.path.getsize(file_path),
        "author": None,
        "last_modified_by": None,
        "created": None,
        "modified": None,
        "revision": None,
        "title": None,
        "subject": None,
        "keywords": None,
        "gps": None,
        "error": None,
    }

    try:
        import docx
        doc = docx.Document(file_path)
        cp = doc.core_properties
        result["author"]           = cp.author
        result["last_modified_by"] = cp.last_modified_by
        result["created"]          = cp.created.isoformat() if cp.created else None
        result["modified"]         = cp.modified.isoformat() if cp.modified else None
        result["revision"]         = cp.revision
        result["title"]            = cp.title
        result["subject"]          = cp.subject
        result["keywords"]         = cp.keywords
    except ImportError:
        result["error"] = "python-docx not installed: pip install python-docx"
    except Exception as e:
        result["error"] = str(e)

    return result


def extract_metadata(file_path: str) -> Dict[str, Any]:
    ext = os.path.splitext(file_path)[1].lower()
    if ext in (".jpg", ".jpeg", ".png", ".tiff", ".tif", ".heic", ".heif", ".webp"):
        return extract_image_metadata(file_path)
    elif ext == ".pdf":
        return extract_pdf_metadata(file_path)
    elif ext in (".docx", ".docm"):
        return extract_docx_metadata(file_path)
    else:
        return {"error": f"Unsupported file type: {ext}", "file": os.path.basename(file_path)}

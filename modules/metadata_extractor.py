import os
import re
import struct
from typing import Dict, Any, Optional
from datetime import datetime


def _dms_to_decimal(dms_tuple, ref: str) -> Optional[float]:
    try:
        d, m, s = float(dms_tuple[0]), float(dms_tuple[1]), float(dms_tuple[2])
        decimal = d + m / 60 + s / 3600
        if ref in ("S", "W"):
            decimal = -decimal
        return round(decimal, 6)
    except Exception:
        return None


def _parse_exif_gps(gps_info: Dict) -> Optional[Dict]:
    try:
        lat = _dms_to_decimal(gps_info[2], gps_info[1])
        lng = _dms_to_decimal(gps_info[4], gps_info[3])
        if lat is not None and lng is not None:
            result = {"lat": lat, "lng": lng}
            if 6 in gps_info:
                result["altitude"] = float(gps_info[6])
            if 7 in gps_info:
                h, m, s = gps_info[7]
                result["gps_time"] = f"{int(h):02d}:{int(m):02d}:{int(s):02d} UTC"
            return result
    except Exception:
        pass
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

            exif_data = img._getexif() if hasattr(img, "_getexif") else None
            if not exif_data:
                return result

            decoded = {}
            gps_raw = {}
            for tag_id, value in exif_data.items():
                tag = TAGS.get(tag_id, str(tag_id))
                if tag == "GPSInfo":
                    for gps_tag_id, gps_val in value.items():
                        gps_tag = GPSTAGS.get(gps_tag_id, str(gps_tag_id))
                        gps_raw[gps_tag] = gps_val
                    result["gps"] = _parse_exif_gps(value)
                else:
                    try:
                        decoded[tag] = str(value) if not isinstance(value, (int, float, str)) else value
                    except Exception:
                        pass

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

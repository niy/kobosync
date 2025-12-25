import os
import re
import shutil
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

import pymupdf

from ..logging_config import get_logger

if TYPE_CHECKING:
    from .types import BookMetadata

logger = get_logger(__name__)


class PdfMetadataExtractor:
    def extract(self, filepath: str) -> BookMetadata:
        metadata: BookMetadata = {}

        path = Path(filepath)
        if not path.exists():
            logger.debug("PDF file not found", path=filepath)
            return metadata

        try:
            doc = pymupdf.open(filepath)
            try:
                pdf_meta = doc.metadata
                if pdf_meta:
                    if pdf_meta.get("title"):
                        metadata["title"] = pdf_meta["title"]
                    if pdf_meta.get("author"):
                        metadata["author"] = pdf_meta["author"]
                    if pdf_meta.get("subject"):
                        metadata["description"] = pdf_meta["subject"]

                xmp_data = doc.xref_get_key(-1, "Metadata")
                if xmp_data and xmp_data[0] == "stream":
                    try:
                        xmp_stream = doc.xref_stream(-1)
                        if xmp_stream:
                            self._parse_xmp(
                                xmp_stream.decode("utf-8", errors="ignore"), metadata
                            )
                    except Exception as e:
                        logger.debug("Failed to parse XMP stream", error=str(e))

                if metadata.get("isbn"):
                    metadata["isbn"] = re.sub(
                        r"[^0-9X]",
                        "",
                        metadata["isbn"].upper(),
                    )

            finally:
                doc.close()

        except Exception as e:
            logger.warning(
                "Error extracting PDF metadata",
                path=filepath,
                error=str(e),
            )

        return metadata

    def _parse_xmp(self, xmp_str: str, metadata: BookMetadata) -> None:
        """Parse XMP metadata from XML string."""
        import xml.etree.ElementTree as ET

        try:
            ns_dc = "http://purl.org/dc/elements/1.1/"

            root = ET.fromstring(xmp_str)

            for elem in root.iter(f"{{{ns_dc}}}title"):
                for li in elem.iter():
                    if li.text and li.text.strip():
                        metadata["title"] = li.text.strip()
                        break

            for elem in root.iter(f"{{{ns_dc}}}creator"):
                creators = []
                for li in elem.iter():
                    if li.text and li.text.strip():
                        creators.append(li.text.strip())
                if creators:
                    metadata["author"] = ", ".join(creators)

            for elem in root.iter(f"{{{ns_dc}}}description"):
                for li in elem.iter():
                    if li.text and li.text.strip():
                        metadata["description"] = li.text.strip()
                        break

            for elem in root.iter(f"{{{ns_dc}}}language"):
                for li in elem.iter():
                    if li.text and li.text.strip():
                        metadata["language"] = li.text.strip()
                        break

            for elem in root.iter(f"{{{ns_dc}}}identifier"):
                for li in elem.iter():
                    if li.text:
                        isbn = self._parse_isbn(li.text)
                        if isbn:
                            metadata["isbn"] = isbn
                            break

        except ET.ParseError as e:
            logger.debug("XMP parse error", error=str(e))

    def write_metadata(self, filepath: str, metadata: BookMetadata) -> None:
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"PDF file not found: {filepath}")

        pdf_metadata: dict[str, str] = {}
        if metadata.get("title"):
            pdf_metadata["title"] = metadata["title"]
        if metadata.get("author"):
            pdf_metadata["author"] = metadata["author"]
        if metadata.get("description"):
            pdf_metadata["subject"] = metadata["description"]

        keywords = []
        if metadata.get("isbn"):
            keywords.append(f"ISBN:{metadata['isbn']}")
        if metadata.get("language"):
            keywords.append(f"Lang:{metadata['language']}")
        if keywords:
            pdf_metadata["keywords"] = ", ".join(keywords)

        pdf_metadata["producer"] = "KoboSync"
        pdf_metadata["creator"] = "KoboSync"

        if not pdf_metadata:
            return

        fd, temp_path_str = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
        os.close(fd)
        temp_path = Path(temp_path_str)

        try:
            doc = pymupdf.open(filepath)
            try:
                doc.set_metadata(pdf_metadata)

                xmp_bytes = self._generate_xmp(metadata)
                if xmp_bytes:
                    doc.set_xml_metadata(xmp_bytes.decode("utf-8"))

                doc.save(str(temp_path), garbage=4, deflate=True)
            finally:
                doc.close()

            shutil.move(str(temp_path), str(path))
            logger.info("Updated PDF metadata", path=filepath)

        except Exception:
            if temp_path.exists():
                temp_path.unlink()
            raise

    def _generate_xmp(self, metadata: BookMetadata) -> bytes:
        import xml.etree.ElementTree as ET

        NS_RDF = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
        NS_XMP = "http://ns.adobe.com/xap/1.0/"
        NS_DC = "http://purl.org/dc/elements/1.1/"
        NS_XMPIDQ = "http://ns.adobe.com/xmp/Identifier/qual/1.0/"
        NS_CALIBRE = "http://calibre-ebook.com/xmp-namespace"
        NS_CALIBRE_SI = "http://calibre-ebook.com/xmp-namespace-series-index"
        NS_XML = "http://www.w3.org/XML/1998/namespace"

        ET.register_namespace("rdf", NS_RDF)
        ET.register_namespace("xmp", NS_XMP)
        ET.register_namespace("dc", NS_DC)
        ET.register_namespace("xmpidq", NS_XMPIDQ)
        ET.register_namespace("calibre", NS_CALIBRE)
        ET.register_namespace("calibreSI", NS_CALIBRE_SI)
        ET.register_namespace("xml", NS_XML)

        xmpmeta = ET.Element("{adobe:ns:meta/}xmpmeta")
        xmpmeta.set("{adobe:ns:meta/}xmptk", "KoboSync via PyMuPDF")

        rdf = ET.SubElement(xmpmeta, f"{{{NS_RDF}}}RDF")

        desc_main = ET.SubElement(rdf, f"{{{NS_RDF}}}Description")
        desc_main.set(f"{{{NS_RDF}}}about", "")
        desc_main.set(f"{{{NS_XMP}}}CreateDate", datetime.now(UTC).isoformat())
        desc_main.set(f"{{{NS_XMP}}}CreatorTool", "KoboSync")

        if metadata.get("title"):
            title_elem = ET.SubElement(desc_main, f"{{{NS_DC}}}title")
            alt_bag = ET.SubElement(title_elem, f"{{{NS_RDF}}}Alt")
            li = ET.SubElement(alt_bag, f"{{{NS_RDF}}}li")
            li.set(f"{{{NS_XML}}}lang", "x-default")
            li.text = metadata["title"]

        if metadata.get("author"):
            creator_elem = ET.SubElement(desc_main, f"{{{NS_DC}}}creator")
            seq = ET.SubElement(creator_elem, f"{{{NS_RDF}}}Seq")
            li = ET.SubElement(seq, f"{{{NS_RDF}}}li")
            li.text = metadata["author"]

        if metadata.get("description"):
            desc_elem = ET.SubElement(desc_main, f"{{{NS_DC}}}description")
            alt_bag = ET.SubElement(desc_elem, f"{{{NS_RDF}}}Alt")
            li = ET.SubElement(alt_bag, f"{{{NS_RDF}}}li")
            li.set(f"{{{NS_XML}}}lang", "x-default")
            li.text = metadata["description"]

        if metadata.get("language"):
            lang_elem = ET.SubElement(desc_main, f"{{{NS_DC}}}language")
            bag = ET.SubElement(lang_elem, f"{{{NS_RDF}}}Bag")
            li = ET.SubElement(bag, f"{{{NS_RDF}}}li")
            li.text = metadata["language"]

        identifiers = []
        if metadata.get("isbn"):
            identifiers.append(("isbn", metadata["isbn"]))
        if metadata.get("amazon_id"):
            identifiers.append(("amazon", metadata["amazon_id"]))
        if metadata.get("goodreads_id"):
            identifiers.append(("goodreads", metadata["goodreads_id"]))

        xmp_id_elem = ET.SubElement(desc_main, f"{{{NS_XMP}}}Identifier")
        bag_id = ET.SubElement(xmp_id_elem, f"{{{NS_RDF}}}Bag")

        for scheme, value in identifiers:
            li = ET.SubElement(bag_id, f"{{{NS_RDF}}}li")
            li.set(f"{{{NS_RDF}}}parseType", "Resource")

            sch = ET.SubElement(li, f"{{{NS_XMPIDQ}}}Scheme")
            sch.text = scheme

            val = ET.SubElement(li, f"{{{NS_RDF}}}value")
            val.text = value

        if metadata.get("series"):
            desc_cal = ET.SubElement(rdf, f"{{{NS_RDF}}}Description")
            desc_cal.set(f"{{{NS_RDF}}}about", "")

            series_elem = ET.SubElement(desc_cal, f"{{{NS_CALIBRE}}}series")
            series_elem.set(f"{{{NS_RDF}}}parseType", "Resource")

            val_elem = ET.SubElement(series_elem, f"{{{NS_RDF}}}value")
            val_elem.text = metadata["series"]

            if metadata.get("series_index"):
                idx_elem = ET.SubElement(
                    series_elem, f"{{{NS_CALIBRE_SI}}}series_index"
                )
                idx_elem.text = f"{metadata['series_index']:.2f}"

        xml_str = ET.tostring(xmpmeta, encoding="utf-8")

        start = b'<?xpacket begin="\xef\xbb\xbf" id="W5M0MpCehiHzreSzNTczkc9d"?>'
        end = b'<?xpacket end="w"?>'

        return start + xml_str + end  # type: ignore[no-any-return]

    def _parse_isbn(self, text: str) -> str | None:
        if not text:
            return None

        if "urn:isbn:" in text.lower():
            cleaned = re.sub(r"[^0-9X]", "", text.upper())
            if len(cleaned) in (10, 13):
                return cleaned

        cleaned = re.sub(r"[^0-9X]", "", text.upper())
        if len(cleaned) in (10, 13):
            if len(cleaned) == 13 and cleaned.startswith(("978", "979")):
                return cleaned
            if len(cleaned) == 10:
                return cleaned

        return None

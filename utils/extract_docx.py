import zipfile, os, uuid
from lxml import etree
from django.conf import settings
from .xml_runs import extract_paragraph_text, is_heading
from .xml_table import extract_table_text
from .xml_images import extract_images_for_drawing

NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
    "rels": "http://schemas.openxmlformats.org/package/2006/relationships",
}

def _save_image(tmpdir, name, data):
    os.makedirs(tmpdir, exist_ok=True)
    path = os.path.join(tmpdir, name)
    with open(path, "wb") as f:
        f.write(data)
    # Return relative media path for Django FileField
    rel = os.path.relpath(path, settings.MEDIA_ROOT)
    return rel.replace("\\", "/")

def extract_blocks_from_docx(docx_path, paper=None):
    """
    Returns a list of blocks: {type, xml, text, images:[media_relpath,...]}
    """
    blocks = []
    with zipfile.ZipFile(docx_path) as z:
        document_xml = z.read("word/document.xml")
        root = etree.fromstring(document_xml)

        # Read rels to resolve images
        rels = {}
        try:
            rels_xml = z.read("word/_rels/document.xml.rels")
            rels_root = etree.fromstring(rels_xml)
            for rel in rels_root.findall("rels:Relationship", namespaces=NS):
                r_id = rel.get("Id")
                target = rel.get("Target")
                rels[r_id] = target  # e.g., media/image1.png
        except KeyError:
            pass

        # tmp image dir for this paper
        media_subdir = f"paper_images/{paper.id if paper else 'tmp'}"
        abs_media_dir = os.path.join(settings.MEDIA_ROOT, media_subdir)

        # Walk top-level children in document order
        body = root.find("w:body", NS)
        for child in body:
            tag = etree.QName(child).localname  # p | tbl | sectPr
            if tag == "p":
                xml = etree.tostring(child, encoding="unicode")
                text = extract_paragraph_text(child)
                btype = "heading" if is_heading(child) else "paragraph"

                # any drawings (images) inside p?
                imgs = extract_images_for_drawing(child, rels, z, abs_media_dir, media_subdir, save_cb=_save_image)

                # If it’s only image(s), call it image; else keep paragraph & attach images
                if text.strip() == "" and imgs:
                    blocks.append({"type": "image", "xml": xml, "text": "", "images": imgs})
                else:
                    blocks.append({"type": btype, "xml": xml, "text": text, "images": imgs})

            elif tag == "tbl":
                xml = etree.tostring(child, encoding="unicode")
                text = extract_table_text(child)  # human-friendly table text
                # Also capture drawings/images embedded inside table cells
                imgs = extract_images_for_drawing(
                    child, rels, z, abs_media_dir, media_subdir, save_cb=_save_image
                )
                blocks.append({"type": "table", "xml": xml, "text": text, "images": imgs})

            else:
                # ignore section properties
                pass
    return blocks

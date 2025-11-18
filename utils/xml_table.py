from lxml import etree
from html import escape

NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}

def extract_cell_text(tc):
    return "".join(t.text or "" for t in tc.findall(".//w:t", NS))

def extract_table_text(tbl):
    """
    Return a simple HTML table built from the WordprocessingML table.
    This preserves structure so the UI can style it.
    """
    parts = ["<table class=\"docx-table\">"]
    for tr in tbl.findall("w:tr", NS):
        parts.append("<tr>")
        for tc in tr.findall("w:tc", NS):
            txt = escape(extract_cell_text(tc))
            # Use <td>; could detect header rows if needed
            parts.append(f"<td>{txt}</td>")
        parts.append("</tr>")
    parts.append("</table>")
    return "".join(parts)

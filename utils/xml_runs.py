from lxml import etree
NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}

def extract_paragraph_text(p):
    runs = p.findall(".//w:t", NS)
    return "".join([t.text or "" for t in runs])

def is_heading(p):
    # detect heading style by pStyle val (e.g., Heading1)
    ppr = p.find("w:pPr", NS)
    if ppr is not None:
        pstyle = ppr.find("w:pStyle", NS)
        if pstyle is not None:
            val = pstyle.get("{%s}val" % NS["w"]) or ""
            return val.lower().startswith("heading")
    # heuristics: bold + larger? (skip for now)
    return False

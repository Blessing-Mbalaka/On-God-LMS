from lxml import etree
NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
}

def extract_images_for_drawing(p_node, rels_map, zipfile_obj, abs_media_dir, media_subdir, save_cb):
    imgs = []
    for blip in p_node.findall(".//a:blip", NS):
        rId = blip.get("{%s}embed" % NS["r"])
        if not rId: 
            continue
        target = rels_map.get(rId)
        if target and target.startswith("media/"):
            # Read the bytes from the docx
            data = zipfile_obj.read(f"word/{target}")
            name = target.split("/")[-1]
            relpath = save_cb(abs_media_dir, name, data)
            # store as MEDIA relative path for Django ImageField later
            imgs.append(relpath)
    return imgs

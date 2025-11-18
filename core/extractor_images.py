# extractor_images.py
import os, shutil, subprocess
from pathlib import Path
import docx
from django.conf import settings

def _media_outdir() -> Path:
    out = Path(settings.MEDIA_ROOT) / "question_images"
    out.mkdir(parents=True, exist_ok=True)
    return out

def convert_emf_to_png(emf_path, output_path):
    try:
        import win32com.client as win32
        word = win32.gencache.EnsureDispatch("Word.Application")
        word.Visible = False
        doc = word.Documents.Add()
        shp = doc.Shapes.AddPicture(FileName=str(emf_path), LinkToFile=False, SaveWithDocument=True)
        shp.SaveAsPicture(str(output_path))
        doc.Close(False); word.Quit()
        return True
    except Exception as e:
        print(f"[Word] {e}")
    try:
        subprocess.run(["magick", emf_path, output_path], check=True)
        return True
    except Exception as e:
        print(f"[magick] {e}")
    return False

def extract_images_with_emf_fallback(docx_path: str) -> list[str]:
    outdir = _media_outdir()
    doc = docx.Document(docx_path)
    rels = doc.part._rels
    saved: set[str] = set()
    urls: list[str] = []

    for rel_id, rel_obj in rels.items():
        if "image" not in rel_obj.target_ref:
            continue
        name = os.path.basename(rel_obj.target_ref)
        stem, ext = os.path.splitext(name)
        raw = rel_obj.target_part.blob

        # write the original
        target = outdir / name
        target.write_bytes(raw)
        saved.add(name.lower())

        # if EMF/WMF try to create a PNG sibling and use that
        if ext.lower() in (".emf", ".wmf"):
            png_path = outdir / f"{stem}.png"
            if convert_emf_to_png(str(target), str(png_path)) and png_path.exists():
                rel = f"question_images/{png_path.name}"
                urls.append(rel)   # prefer png
            else:
                rel = f"question_images/{target.name}"
                urls.append(rel)   # fallback emf (won’t render, but link exists)
        else:
            # non-emf: just use what we saved
            rel = f"question_images/{target.name}"
            urls.append(rel)

    # return RELATIVE media paths, e.g. "question_images/file.png"
    return urls

# extractor_images.py
import os, shutil, subprocess

from pathlib import Path
import docx
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

def _media_outdir() -> Path:
    # Deprecated: local storage. Now using S3 via Django storage backend.
    return "question_images"

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

        # Save the original image to S3
        s3_path = f"{outdir}/{name}"
        if not default_storage.exists(s3_path):
            default_storage.save(s3_path, ContentFile(raw))
        saved.add(name.lower())

        # if EMF/WMF try to create a PNG sibling and use that
        if ext.lower() in (".emf", ".wmf"):
            # Download the file locally for conversion
            local_emf = f"/tmp/{name}"
            with open(local_emf, "wb") as f:
                f.write(raw)
            png_name = f"{stem}.png"
            local_png = f"/tmp/{png_name}"
            if convert_emf_to_png(local_emf, local_png) and os.path.exists(local_png):
                # Upload PNG to S3
                s3_png_path = f"{outdir}/{png_name}"
                with open(local_png, "rb") as f:
                    default_storage.save(s3_png_path, ContentFile(f.read()))
                rel = f"question_images/{png_name}"
                urls.append(rel)
                os.remove(local_png)
            else:
                rel = f"question_images/{name}"
                urls.append(rel)
            os.remove(local_emf)
        else:
            # non-emf: just use what we saved
            rel = f"question_images/{name}"
            urls.append(rel)

    # return RELATIVE media paths, e.g. "question_images/file.png"
    return urls

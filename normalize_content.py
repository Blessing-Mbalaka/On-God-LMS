import os
from django.conf import settings
def normalize_content_and_copy_media(node_content, src_media_dir, paper_id):
    """Normalize tables/paragraphs; copy figures to MEDIA and emit {type:'image', src:...}"""
    normalized = []
    dest_media_dir = os.path.join(settings.MEDIA_ROOT, 'media', str(paper_id))
    os.makedirs(dest_media_dir, exist_ok=True)

    for item in (node_content or []):
        if not isinstance(item, dict):
            continue
        t = item.get('type')

        if t == 'table' and 'rows' in item:
            normalized.append({'type': 'table', 'rows': item['rows']})
            continue

        if t in ('figure', 'image'):
            # data URI case
            if item.get('data_uri'):
                normalized.append({
                    'type': 'image',
                    'src': item['data_uri'],
                    'caption': item.get('caption', '')
                })
                continue

            # filenames case
            for fn in (item.get('images') or []):
                try:
                    src = os.path.join(src_media_dir, fn)
                    if os.path.isfile(src):
                        dst = os.path.join(dest_media_dir, fn)
                        if not os.path.exists(dst):
                            shutil.copyfile(src, dst)
                        web_src = f"{settings.MEDIA_URL.rstrip('/')}/media/{paper_id}/{fn}"
                    else:
                        # fallback if file missing (older manifests)
                        web_src = f"media/{fn}"
                except Exception as e:
                    print(f"⚠️ image copy failed for {fn}: {e}")
                    web_src = f"media/{fn}"

                normalized.append({
                    'type': 'image',
                    'src': web_src,
                    'filename': fn,
                    'caption': item.get('caption', '')
                })
            continue

        if t in ('question_text', 'paragraph'):
            txt = (item.get('text') or '').strip()
            if txt:
                normalized.append({'type': t, 'text': txt})
            continue

        if t == 'pagebreak':
            normalized.append({'type': 'pagebreak'})
            continue

        # keep anything else just in case
        normalized.append(item)

    return normalized

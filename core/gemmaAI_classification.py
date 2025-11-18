import re
import requests
import json

# Noise and trivial-content detection patterns
noise_patterns = [
    r'^page\s+\d+',
    r'^answer all questions',
    r'^external integrated summative assessment',
    r'^students are only allowed',
    r'^\s*[-–—]{3,}\s*$',  # long dash separators
]

# Helper filters

def is_structural_noise(text):
    txt = text.strip().lower()
    return any(re.match(pat, txt) for pat in noise_patterns)

def is_trivial(text):
    t = text.strip()
    if not t or re.fullmatch(r'[\W_]+', t):
        return True
    if len(t.split()) < 2 and not re.match(r'^\d+(?:\.\d+)+', t):
        return True
    return False

def is_non_english(text):
    return not bool(re.search(r'[A-Za-z]', text))

def is_formula(text):
    return bool(re.fullmatch(r'[\d+\-*/=^()\s]+', text.strip()))

def classify_with_local_gemma(blocks, pre_types):
    """
    Uses local Ollama Gemma to classify each block, with additional noise filtering.
    Returns a list of types same length as blocks.
    """
    print("🔁 [FALLBACK] Trying classification with local Gemma...")

    merged = list(pre_types)
    to_index = []
    for i, b in enumerate(blocks):
        if merged[i] is not None:
            continue
        text = (b.get('text') or '').strip()
        if is_structural_noise(text) or is_trivial(text) or is_non_english(text):
            merged[i] = 'noise'
        elif is_formula(text):
            merged[i] = 'other'
        else:
            to_index.append(i)

    if not to_index:
        print("✅ [LOG] No additional blocks needed Gemma classification.")
        return merged

    snippet = [
        blocks[i].get('text') 
        or ('[FIGURE]' if blocks[i].get('data_uri') else '')
        or ('[TABLE]' if blocks[i].get('rows') else '')
        for i in to_index
    ]

    prompt = f"""
You are classifying extracted document blocks from a .docx exam paper.

Use only one of these labels:
['question','rubric','case_study','instruction','heading','paragraph','table','figure','noise','other']

Return a JSON list of types in the same order as these blocks:
{json.dumps(snippet, indent=2)}
""".strip()

    try:
        res = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "gemma3:latest",
                "prompt": prompt,
                "stream": False
            },
            timeout=120
        )

        api_json = res.json()
        raw_response = api_json.get("response", "").strip()
        print("🌀 [Gemma Raw API JSON]:", api_json)

        if not raw_response:
            raise ValueError("Gemma API returned an empty response.")

        print("📤 [Gemma Response Text]:", raw_response)

        match = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", raw_response, re.DOTALL)
        if match:
            cleaned_json = match.group(1)
            gtypes = json.loads(cleaned_json)
        else:
            gtypes = json.loads(raw_response)

    except Exception as e:
        print("❌ [Gemma Fallback Error]:", e)
        for i in to_index:
            merged[i] = 'paragraph'
        return merged

    for idx, typ in zip(to_index, gtypes):
        merged[idx] = typ

    print("✅ [LOG] Gemma fallback injected types:", merged)
    return merged

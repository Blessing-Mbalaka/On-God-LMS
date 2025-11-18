import json
import os

json_path = r"C:\Users\bjmba\CHIETA_LMS_fresh\upload_7bc5c5537edb472183cab51cd8a9669c_extract\structure_json.json"

# Load your JSON file
with open(json_path, 'r') as f:
    data = json.load(f)

# List of actual images in media folder
media_folder = r"C:\Users\bjmba\CHIETA_LMS_fresh\media"
actual_images = set(os.listdir(media_folder))

# Update image references in nodes
for node in data['nodes']:
    for block in node.get('content', []):
        if block.get('type') == 'figure':
            block['images'] = [img for img in block['images'] if img in actual_images]

# Save the updated JSON
with open(json_path, 'w') as f:
    json.dump(data, f, indent=2)

print("🎉 All done! Your image references are now fresh and happy. Go check your page! 🚀")
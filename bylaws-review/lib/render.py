import json
import os

TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), "..", "site", "template.html")
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "output", "index.html")


def render(entries, output_path=OUTPUT_PATH, template_path=TEMPLATE_PATH):
    with open(template_path, "r", encoding="utf-8") as f:
        template = f.read()

    data_json = json.dumps(entries, ensure_ascii=False).replace("</", "<\\/")
    html = template.replace("__DATA_JSON__", data_json)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    return output_path

import json
import sys
from pathlib import Path

from apiinference import generate_ui_code
from inference import run_detection
from tesseract_infer import run_ocr


def attach_text_to_elements(det_data, ocr_data):
    """Attach OCR text to the detected element whose box contains the text center."""
    elements = [dict(el, texts=[]) for el in det_data.get("elements", [])]
    unassigned = []

    for entry in ocr_data.get("entries", []):
        xs = [p[0] for p in entry["bbox"]]
        ys = [p[1] for p in entry["bbox"]]
        cx = sum(xs) / len(xs) if xs else 0.0
        cy = sum(ys) / len(ys) if ys else 0.0

        placed = False
        for element in elements:
            x1, y1, x2, y2 = element["bbox"]
            if x1 <= cx <= x2 and y1 <= cy <= y2:
                element["texts"].append(entry)
                placed = True
                break

        if not placed:
            unassigned.append(entry)

    layout = {
        "image_path": det_data.get("image_path"),
        "image_size": det_data.get("image_size"),
        "bbox_format": det_data.get("bbox_format", "normalized_xyxy"),
        "elements": elements,
        "unassigned_text": unassigned,
    }
    return layout


def add_section_ordering(elements, gap: float = 0.08):
    """Group elements into rows/sections by y-position and assign order for the LLM."""
    if not elements:
        return elements

    # Sort by center y, then center x
    sorted_elements = sorted(
        elements,
        key=lambda e: ((e["bbox"][1] + e["bbox"][3]) / 2.0, (e["bbox"][0] + e["bbox"][2]) / 2.0),
    )

    sections = []
    for el in sorted_elements:
        cy = (el["bbox"][1] + el["bbox"][3]) / 2.0
        placed = False
        for section in sections:
            if abs(section["cy"] - cy) <= gap:
                section["items"].append(el)
                section["cys"].append(cy)
                section["cy"] = sum(section["cys"]) / len(section["cys"])
                placed = True
                break
        if not placed:
            sections.append({"cy": cy, "cys": [cy], "items": [el]})

    for section_idx, section in enumerate(sections):
        # sort within section by center x
        section["items"].sort(key=lambda e: (e["bbox"][0] + e["bbox"][2]) / 2.0)
        for order_idx, el in enumerate(section["items"]):
            el["section_index"] = section_idx
            el["order_in_section"] = order_idx
    return sorted_elements


def build_layout(image_path: str, annotated_path: str = "frontend_detected.png"):
    det_data = run_detection(image_path=image_path, save_annotated_path=annotated_path)
    ocr_data = run_ocr(image_path=image_path)
    layout = attach_text_to_elements(det_data, ocr_data)
    layout["elements"] = add_section_ordering(layout.get("elements", []))
    return layout


def main():

    
    image_path = sys.argv[1] if len(sys.argv) > 1 else "frontend.png"
    layout = build_layout(image_path)

    layout_path = Path("layout_output.json")
    layout_path.write_text(json.dumps(layout, indent=2))
    print(f"Layout JSON written to {layout_path}")

    try:
        code = generate_ui_code(layout_path.read_text())
        Path("/mnt/windows/Users/Admin/Desktop/All/Not_College/Codes/NextJs/linkedin-ai-agent/app/page.tsx").write_text(code[6:-3])
        print("Generated UI written to generated_ui.jsx")
    except Exception as exc:
        print(f"Model invocation failed: {exc}")


if __name__ == "__main__":
    main()

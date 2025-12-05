from pathlib import Path
from typing import Dict

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()



llm = ChatOpenAI(
    model="kwaipilot/kat-coder-pro:free",
    temperature=0,
    base_url = "https://openrouter.ai/api/v1",
    verbose = True
)

layout_json = """
{
  "image_path": "./images/landing.png",
  "image_size": {"width": 1920, "height": 1080},
  "bbox_format": "normalized_xyxy",
  "elements": [
    {"label": "Navbar", "bbox": [0.0, 0.0, 1.0, 0.08], "texts": []},
    {"label": "Hero", "bbox": [0.05, 0.12, 0.95, 0.45], "texts": []}
  ],
  "unassigned_text": [
    {"text": "Welcome to Protein Co.", "bbox": [[0.1,0.1],[0.2,0.1],[0.2,0.12],[0.1,0.12]]}
  ]
}
""".strip()

filename = "landing.png"
expected_filename = f"{Path(filename).stem}.tsx"

components = {
    "landing.png": """import Link from "next/link";
import { Button } from "@/components/ui/button";
const App = () => (<div>Old landing placeholder</div>);
export default App;"""
}

palette = ["#0f172a", "#3b82f6", "#22c55e"]

prior_code = ""
if isinstance(components, dict) and filename in components:
    prior_code = (
        "\n\nExisting code for this page (for reference; reuse/augment, do not replace):\n"
        f"{components[filename]}"
    )
palette_hint = f"\n\nPreferred color palette: {palette}"


class ModelOutput(BaseModel):
    code: Dict[str, str]
    context: str

# ... setup layout_json, filename, components ...

system_prompt = f"""
You are an expert Frontend Engineer specialized in building pixel-perfect Next.js App Router applications from design data.

GOAL:
Generate a production-ready Next.js component (React + TypeScript) based on a structured layout JSON. Your output MUST be JSON containing a `code` object where keys are filenames and values are full file contents.

INPUT TYPES:
1. Layout JSON: contains normalized bounding boxes (0–1 xyxy), element labels, and OCR texts.
2. Unassigned Text: OCR text found outside detected regions; intelligently assign it to the nearest logical section.
3. Prior Code: If meaningful, merge into the new layout. If placeholder or one-liner, overwrite entirely.

TECH STACK RULES:
- Framework: Next.js 14+ App Router
- Styling: TailwindCSS utility classes only
- Icons: lucide-react
- Components: Use semantic HTML + Tailwind; do NOT import non-standard components
- Colors: Use only the provided palette for emphasis, backgrounds, or accents
- If you need client-side hooks or event handlers, add the directive exactly `"use client";` as the first line of that file.

OUTPUT CONTRACT (NON-NEGOTIABLE):
1. Output MUST be valid JSON.
2. The `code` object MUST contain a key named "{expected_filename}" with the full Next.js page component.
3. The `code` object MUST contain one additional file for EVERY unique `href="/xxx"` route found in any `<Link>` or `<a>` element in the generated code.
   • Example: if your page contains `<Link href="/about">` and `<Link href="/contact">`, then `code` MUST contain keys `"about.tsx"` and `"contact.tsx"`.
   • This rule is NOT optional.
4. Internal anchors (`href="#something"`) do NOT require additional files.
5. Missing required files is INVALID output.
6. Returning a single file when external routes exist is INVALID output.

ROUTE FILE RULES:
- Each generated route file MUST be a minimal, valid Next.js App Router page component:
  • Always export a default React function component
  • Use Tailwind utility classes
  • Include placeholder content consistent with page name
- You MAY generate simple stubs, but they MUST exist as separate keys inside the `code` object.

NO HALLUCINATIONS:
- DO NOT import from "@/components/*" unless you define that component in a returned file.
- DO NOT generate network requests, random APIs, or external images.
- If an image is needed, use a placeholder like a `div` with Tailwind background utilities.

RESPONSIVENESS REQUIREMENTS:
- Always include mobile responsiveness via Tailwind breakpoints (e.g., `md:flex`, `hidden md:block`).
- Navigation MUST collapse visually on mobile (hamburger or minimal nav).
- Large hero / sidebar regions MUST stack vertically on screens <768px.

INTERACTIVITY REQUIREMENTS:
- All buttons require hover styles AND meaningful href or onClick handlers.
- Use plausible routes ("/about", "/pricing", "/contact", "/products") when missing labels.
- No `href="#"` unless it is a scroll anchor (`#something`).

STRUCTURAL RULES:
- Sort layout elements vertically using bbox.y position.
- Group visually related sections into <section> or <div> containers.
- Insert unassigned text into the nearest semantic region (e.g., hero heading, nav brand, primary CTA).

ABSOLUTE PROHIBITIONS:
- DO NOT mention layout JSON, bounding boxes, OCR, "design", or "AI".
- DO NOT explain decisions.
- DO NOT summarize.
- DO NOT return Markdown or code fences.
- DO NOT collapse multiple files into a single file string.

VALIDATION RULE:
- Before returning, count all unique `href="/xxx"` patterns in your main file.
- The number of additional files in `code` MUST equal that count.
- If no external routes exist, only return one file.
- Returning additional files is **required** when routes exist.

YOUR OUTPUT SHOULD:
- Represent a realistic landing page using the provided palette
- Include a fixed navbar, hero, CTA, and semantic structure
- Be ready to paste directly into a Next.js `/app` directory
"""

user_prompt = f"""
Generate the UI code for the file: "{filename}"

---
LAYOUT JSON:
{layout_json}

---
COLOR PALETTE:
{palette}

---
EXISTING CODE (Reference only - Overwrite if generic):
{prior_code}

---
INSTRUCTION:
Generate the full TypeScript code for "{filename}". 
Ensure the `code` object in your response contains at least the key "{expected_filename}" mapped to its full file content. If you detect linked routes in the layout/navigation (e.g., /about, /login, /contact), also generate minimal but coherent page components for those routes and include them in `code`.
"""

messages = [
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": user_prompt},
]



model = llm.with_structured_output(ModelOutput)
print("Here")
result = model.invoke(messages)
print("Here")
if not result.code or expected_filename not in result.code:
    raise RuntimeError("Model returned empty code")
print(result)

path = "/mnt/windows/Users/Admin/Desktop/All/Not_College/Codes/MachineLearning/Sketch-To-Website/websiteTemp/app"
import os
for fname, code in result.code.items():
    page_dir = os.path.join(path, fname[:-4])
    os.makedirs(page_dir, exist_ok=True)
    with open(os.path.join(page_dir, "page.tsx"), "w") as f:
        f.write(code)

from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

model_dir = "./qwen2.5-3b"   # local folder

tokenizer = AutoTokenizer.from_pretrained(model_dir)
model = AutoModelForCausalLM.from_pretrained(
    model_dir,
    torch_dtype=torch.float16,
    device_map="auto"
)

messages = [
    {
        "role": "system",
        "content": (
			"You are an automated UI-code generator.\n"
            "The code MUST be syntactically complete and all JSX tags must be properly closed. Never stop in the middle of a tag."
			"- You MUST output valid React (react-web, NOT React Native) code.\n"
			"- NEVER use <template>, NEVER use Vue, NEVER use SFC syntax.\n"
			"- NEVER use 'class='; ALWAYS use 'className='.\n"
			"- You must ALWAYS return a single React functional component with a default export.\n"
			"- The component should look like: `const App = () => { return (<div>...</div>); }; export default App;`\n"
			"- Do NOT explain anything. Do NOT use markdown. Do NOT include ``` fences.\n"
			"- Output ONLY raw code that can be pasted into a .jsx or .tsx file."
            "- The code should look like a professional landing page created with professional tools ."
            "- Make use of ShadCn or lucide-react components if necessary."
        ),
    }
]
bbox_info = """'[     1042.7      513.85      1504.7      647.46]\nTextButton[     864.47      237.86      1242.8       337.9]\nTextButton[     191.02      238.99      491.92      335.61]\nTextButton[     811.84      701.05      1744.8      804.89]\nCheckedTextView[     200.65      553.84      755.11      649.16]\nTextButton[     204.81      699.07      1804.2      806.07]\nCheckedTextView[     204.47      1023.1      882.87      1143.1]\nTextButton[     533.34      238.08      826.78      338.61]\nTextButton[     224.83      864.33      602.98      969.22]\nTextButton[     872.64      237.01      1479.7      338.74]\nTextButton[     201.07      700.98      921.16      804.97]\nCheckedTextView[     184.38      237.22      866.04      341.11]\nCheckedTextView[     227.77      866.34      1721.5      972.41]\nCheckedTextView[     253.92      62.405      1464.3      180.38]\nTextButton[     802.54      535.38      1211.4      649.98]\nCheckedTextView[     1602.2      418.02      1743.4      655.73]\nImage[      529.9      234.52      1257.1      340.76]\nTextButton[     199.45      549.04       993.9      650.89]\nCheckedTextView[     514.65      62.184        1628      180.79]\nTextButton[     803.33      519.58      1526.2      650.06]\nCheckedTextView[     655.73      399.66      1345.2      451.24]\nText[     183.38      392.23      1339.5      476.84]\nCheckedTextView[     755.83      235.33      1725.4      339.12]\nTextButton[     725.15      890.46      1750.6      947.02]\nCheckedTextView[     906.17      1020.4      1808.5      1164.1]\nCheckedTextView[     803.35      548.71      995.62       650.1]\nCheckedTextView[     304.77      400.89      1330.8      449.35]\nText[     642.88      399.21        1162      453.04]\nText[     233.14           0      1298.8           0]\nUpperTaskBar[     1264.9      235.34      1719.2      336.15]\nTextButton[     808.89      554.16      995.68      649.84]\nImage[     970.74      62.709      1463.5      177.36]\nTextButton[     184.29      394.77      1588.2      496.94]\nCheckedTextView[     1028.7      407.54      1335.3      447.06]\nText[     200.89      704.82      609.76      803.13]\nCheckedTextView[      198.2      703.33       600.6      802.47]\nTextButton'
"""

user_prompt = f"""
You are an automated UI generator. The user has provided a drawing on paper
of how they want their landing page to look.

Since you cannot see the image, I am giving you the extracted bounding box
information and labels for all UI elements:

{bbox_info}

Each entry contains:
[x_min, y_min, x_max, y_max]  Label

Your task:
- Generate a React WEB landing page component (NO React Native).
- Use TailwindCSS classes for styling.
- Assume a white background overall.
- Group elements with similar vertical positions into horizontal sections/rows.
- Use semantic HTML where possible (header, main, section, footer).
- You MAY rename labels like TextButton/CheckedTextView into nicer UI copy.

STRICT RULES:
- Do NOT explain anything.
- Do NOT use markdown or ``` fences.
- Return ONLY a single default-exported React component (e.g. App or LandingPage).
- The code must be valid JSX and ready to paste into App.jsx.
"""

messages.append({"role": "user", "content": user_prompt})

# text = ''
# while(text!='exit'):
# 	text = input("You : ")
# 	if(text == "exit"):
# 		break
# 	messages.append({"role":"user","content":text})
# 	inputs = tokenizer.apply_chat_template(
# 		messages,
# 		add_generation_prompt=True,
# 		tokenize=True,
# 		return_dict=True,
# 		return_tensors="pt",
# 	).to(model.device)

# 	outputs = model.generate(
# 		**inputs,
# 		max_new_tokens=1024,
# 		do_sample=True,
# 		temperature=0.7,
# 		top_p=0.9
# 	)
# 	print("AI : ",end = "")
# 	print(tokenizer.decode(outputs[0][inputs["input_ids"].shape[-1]:]))
# 	messages.append({"role":"assistant","content":tokenizer.decode(outputs[0][inputs["input_ids"].shape[-1]:])})

inputs = tokenizer.apply_chat_template(
	messages,
	add_generation_prompt=True,
	tokenize=True,
	return_dict=True,
	return_tensors="pt",
).to(model.device)

outputs = model.generate(
	**inputs,
	max_new_tokens=1024,
	do_sample=True,
	temperature=0.4,
	top_p=0.9
)

gen_ids = outputs[0][inputs["input_ids"].shape[-1]:]
print("Generated tokens:", len(gen_ids))
response = tokenizer.decode(gen_ids, skip_special_tokens=True).strip()

print("AI: ", end="")
print(response)

messages.append({"role": "assistant", "content": response})

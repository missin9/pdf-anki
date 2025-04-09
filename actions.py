# actions.py
# -*- coding: utf-8 -*-
import base64
import json
import os
import fitz  # PyMuPDF
from PIL import Image
from io import BytesIO
import re
import uuid
import hashlib
import streamlit as st
import streamlit.components.v1 as components
import markdown
from mistral_config import create_mistral_client, create_chat_message, make_api_request

# Custom component to call AnkiConnect on client side
parent_dir = os.path.dirname(os.path.abspath(__file__))
build_dir = os.path.join(parent_dir, "API/frontend/build")
_API = components.declare_component("API", path=build_dir)

def API(action, key=None, deck=None, image=None, front=None, back=None, tags=None, flashcards=None,
        filename=None):
    component_value = _API(action=action, key=key, deck=deck, image=image, front=front, back=back, tags=tags,
                           flashcards=flashcards, filename=filename)
    return component_value

class Actions:
    def __init__(self, root):
        self.root = root

    def check_API(self, key=None):
        response = API(action="reqPerm", key=key)
        if response is not False and response is not None:
            st.session_state['api_perms'] = response

    def get_decks(self, key=None):
        decks = API(action="getDecks", key=key)
        if decks is not False and decks is not None:
            st.session_state['decks'] = decks

    @make_api_request
    def get_lang(self, text):
        if st.session_state['API_KEY'] == "":
            client = create_mistral_client(st.secrets['MISTRAL_API_KEY'])
        else:
            client = create_mistral_client(st.session_state['API_KEY'])

        try:
            messages = [
                create_chat_message("system", "You are a helpful assistant."),
                create_chat_message("user", f"Return in one word the language of this text: {text}")
            ]
            
            completion = client.chat(
                model="mistral-large-latest",
                messages=messages
            )
            
            return completion.choices[0].message.content
            
        except Exception as e:
            st.warning(f"Mistral API returned an error:\n\n{str(e)}\n\n**Refresh the page and try again**")
            st.session_state["mistral_error"] = e
            st.stop()

    @make_api_request
    def send_to_gpt(self, page):
        st.session_state["prompt"] = """
You are receiving the text from one slide of a lecture. Use the following principles when making the flashcards:

Material: "Source material"

Task: Your task is to analyze the Source Material and condense the information into concise and direct statements. Ensure that each statement is clearly written at a level appropriate for medical students while being easily understandable, and adheres to the specified formatting and reference criteria. 

Formatting Criteria: 
- Construct a table with two columns: "Statements" and "explanations".
- Each row of the "Statements" column should contain a single statement written in Anki cloze deletion mark-up.
- Each row of the "explanation" column should provide additional details for the corresponding "Statement". There should be no cloze deletions in this column.
- If no text is present, leave everything bland.

Reference Criteria for each "Statement":
- Restrict each statement to 1 or 2 cloze deletions. If needed, you may add 1-2 more cloze deletions but restrict them to either cloze1 or cloze2.
- Limit the word count of each statement to less than 40 words.
- Keep the text within the cloze deletions limited to one or two Source key words.
- Each statement must be able to stand alone.
- Keep ONLY simple, direct, statements in the "Statements" column. Keep any additional information in the "Explanation" column. Search and research USMLE textbook for detailed explanations supporting the statement.
- Use the following examples below as a guideline on how to construct a "Statement" and "Explanation" based on provided source material. Be mindful of the cloze positions, and how statements adhere to the source material with minimal deviation.

Example: 
    Source Material: 
        Hyperaldosteronism: Increased secretion of aldosterone from adrenal gland. Clinical features include hypertension, ↓ K⁺ (from increased renal Na+-K+ ATPase activity, resulting increased K⁺ secretion and causing hypokalemia) or normal K⁺, metabolic alkalosis. 1° hyperaldosteronism does not directly cause edema due to aldosterone escape mechanism. However, certain 2° causes of hyperaldosteronism (eg, heart failure) impair the aldosterone escape mechanism, leading to worsening of edema.
        Primary hyperaldosteronism: Seen with adrenal adenoma (Conn syndrome), ectopic aldosterone-secreting tumors (kidney, ovaries), or bilateral adrenal hyperplasia. ↑ aldosterone, ↓ renin. Presents with increased renal blood flow and increased glomerular filtration rate, resulting in sodium and water retention (severe volume overload). Causes resistant hypertension.
        Secondary hyperaldosteronism: Seen in patients with renovascular hypertension, juxtaglomerular cell tumors (independent activation of RAAS, from excess renin-producing "reninoma"), and edema (eg, cirrhosis, heart failure, nephrotic syndrome). ↑ aldosterone, ↑ renin. Characterized by increased aldosterone production due to an external stimulus, primarily as a response to activation of the renin-angiotensin-aldosterone system (RAAS).

    Table:
| Statements | Explanation 
| {{c1::word}} Give an example of what you want here | - Explanation here |
| This is a {{c1::second}} example to reinforce the formatting. | - Explanation here |
| {{c1::Primary}} hyperaldosteronism is characterized by high aldosterone and {{c2::low}} renin | - This results in resistant hypertension; renin is downregulated via high blood pressure |
| Hyperaldosteronism {{c2::increases}} K⁺ secretion and causes {{c2::hypo}}kalemia | - Increased Na+ reabsorption → increased Na+-K+ ATPase activity → increased driving force across luminal membrane from increased intracellular K+ |
| Primary hyperaldosteronism may present with {{c1::increased}} renal blood flow and {{c1::increased}} glomerular filtration rate | - Due to arterial hypertension and hypersecretion of aldosterone |
| Primary hyperaldosteronism initially causes severe volume {{c1::overload}} and {{c1::hyper}}tension | - Due to sodium and water retention |
| Adrenal adenoma and ectopic aldosterone-secreting tumors (kidney, ovaries) may cause {{c1::primary}} hyperaldosteronism | - Can lead to resistant hypertension |
| {{c1::Secondary}} hyperaldosteronism is seen in patients with juxtaglomerular cell tumor due to independent activation of the RAAS | - Results in severe hypertension that is difficult to control - These secrete renin (hence AKA reninoma), thus you also have Angiotensin II upregulation as well as aldosterone (failure of aldosterone escape) |
| Secondary hyperaldosteronism is due to activation of {{c1::renin-angiotensin}} system | - Seen in patients with renovascular hypertension (renal artery stenosis), juxtaglomerular cell tumors, and edema (cirrhosis, heart failure, nephrotic syndrome) |
| Congestive heart failure, cirrhosis, nephrotic syndrome, and excessive peripheral edema may cause {{c1::secondary}} hyperaldosteronism | - 2° hyperaldosteronism is driven by an increase in renin production (i.e. stimulation from edema) |
| {{c1::Secondary}} hyperaldosteronism is characterized by high aldosterone and {{c2::high}} renin | - Seen in patients with renovascular hypertension and juxtaglomerular cell tumor (due to independent activation of renin-angiotensin-aldosterone system), as well as causes of edema (cirrhosis, heart failure, nephrotic syndrome) |
End of Example

- Only add each piece of information once.
- Questions and answers must be in """ + st.session_state["lang"] + """.
- Ignore information about the school or professor.
- If whole slide fits on one flashcard, do that.
- Use 'null_function' if page is just a title slide.
- Return json.
"""

        new_chunk = st.session_state['text_' + str(page)]
        new_chunk = st.session_state["prompt"] + 'Text:\n' + new_chunk

        behaviour = "You are a flashcard making assistant. Follow the user's requirements carefully and to the letter. Always call one of the provided functions."

        if st.session_state['API_KEY'] == "":
            client = create_mistral_client(st.secrets['MISTRAL_API_KEY'])
        else:
            client = create_mistral_client(st.session_state['API_KEY'])

        max_retries = 3
        retries = 0
        while retries < max_retries:
            try:
                messages = [
                    create_chat_message("system", behaviour),
                    create_chat_message("user", new_chunk)
                ]
                
                completion = client.chat(
                    model="mistral-large-latest",
                    messages=messages,
                    temperature=0.8
                )
                
                response = completion.choices[0].message.content
                
                if "null_function" in response:
                    st.session_state[f"{str(page)}_is_title"] = True
                    return None
                    
                return response
                
            except Exception as e:
                print(f"Error: {str(e)}")
                retries += 1
                if retries == max_retries:
                    st.warning(f"Mistral API error:\n\n{str(e)}\n\n**Fix the problem, refresh the page and try again**")
                    st.session_state["mistral_error"] = e
                    st.stop()

    def add_image_to_anki(self, image_path, pdf_name, page):
        try:
            with open(image_path, "rb") as img_file:
                image_data = base64.b64encode(img_file.read()).decode('utf-8')

            base_name = os.path.basename(pdf_name)
            base_name_without_ext = os.path.splitext(base_name)[0]
            filename = f"{base_name_without_ext}_page_{page + 1}.jpg"

            image_stored = API("storeImage", image=image_data, filename=filename)
            return image_stored

        except Exception as e:
            st.error(f"add_image_to_anki error: {str(e)}")
            return None

    def cleanup_response(self, text):
        try:
            prefix = 'flashcard_function('
            if text.startswith(prefix):
                text = text[len(prefix):-1]

                json_strs = text.strip().split('\n})\n')
                json_strs = [text + '}' if not text.endswith('}') else text for text in json_strs]
                json_strs = ['{' + text if not text.startswith('{') else text for text in json_strs]

                text = json_strs[0]

            response_text_escaped = re.sub(r'(?<=\[)[^\[\]]*(?=\])', self.escape_inner_brackets, text)
            response_text_standard_quotes = self.replace_curly_quotes(response_text_escaped)
            response_text_single_quotes = re.sub(r'("(?:[^"\\]|\\.)*")', self.replace_inner_double_quotes,
                                                 response_text_standard_quotes)

            response_cards = json.loads(response_text_single_quotes, strict=False)
            response_data = response_cards["flashcards"]

            return response_data

        except Exception as e:
            print(f"Error with Mistral API: {str(e)}\nReturned:\n{text}")

    def escape_inner_brackets(self, match_obj):
        inner_text = match_obj.group(0)
        escaped_text = inner_text.replace('[', '\\[').replace(']', '\\]')
        return escaped_text

    def replace_curly_quotes(self, text):
        return text.replace('"', "'").replace('"', "'").replace('„', "'")

    def replace_inner_double_quotes(self, match_obj):
        inner_text = match_obj.group(0)
        pattern = r'(:\s*)("[^"]*")'
        matches = re.findall(pattern, inner_text)

        for match in matches:
            inner_quotes_replaced = match[1].replace('"', "'")
            inner_text = inner_text.replace(match[1], inner_quotes_replaced)

        return inner_text

# AppView.py
# -*- coding: utf-8 -*-
import io
import os
import json
import base64
import streamlit as st
from streamlit_extras.badges import badge
import fitz
import uuid
import time
import hashlib
import tempfile
from streamlit_cropper import st_cropper
from PIL import Image
from mistral_config import create_mistral_client
import markdown

class AppView:
    def __init__(self, actions):
        self.actions = actions

    @st.cache_data
    def extract_pdf_data(_self, file_path):
        doc = fitz.open(file_path)
        page_count = len(doc)

        extracted_data = {}
        for i in range(page_count):
            page = doc.load_page(i)
            text = page.get_text()
            pixmap = page.get_pixmap(dpi=150)
            image_bytes = pixmap.tobytes(output='jpg', jpg_quality=100)
            extracted_data[i] = {
                "text": text,
                "image": image_bytes
            }

        return extracted_data, page_count

    def reset_cache_on_new_file(self, file):
        if "last_uploaded_file" not in st.session_state:
            st.session_state["last_uploaded_file"] = None

        if file is not None:
            if file.name != st.session_state["last_uploaded_file"]:
                st.cache_data.clear()
                self.clear_flashcards()
                st.session_state["last_uploaded_file"] = file.name
                with open(os.path.join("/tmp", file.name), "wb") as f:
                    f.write(file.getbuffer())
                st.session_state["temp_file_path"] = os.path.join("/tmp", file.name)

    def display(self):
        st.session_state['dev'] = False
        col1, col2 = st.columns([0.7, 0.3])

        with col1:
            st.title('📄PDFtoAnki')

        with col2:
            st.markdown("""
            <style>
            div.stButton > button {
                font-size: 18px;
                font-weight: bold;
                padding: 15px;
                background-color: #1f77b4;
                color: white;
                border: 2px solid transparent;
                border-radius: 12px;
                width: 100%;
                transition: background-color 0.3s ease, transform 0.2s ease;
            }

            div.stButton > button:hover {
                background-color: #1a5f8e;
                transform: scale(1.02);
            }

            div.stButton > button:active {
                background-color: #174a6b;
                transform: scale(0.98);
            }
            </style>
            """, unsafe_allow_html=True)

            if self.has_active_flashcards():
                if st.button("Add All Active Cards to Anki"):
                    self.add_all_flashcards_to_anki()

        st.header('Powered by Mistral Large')

        if "no_ankiconnect" in st.session_state and st.session_state.no_ankiconnect == False:
            if "api_perms" not in st.session_state:
                self.actions.check_API()

        col1, col2 = st.columns([0.78, 0.22], gap="large")
        with col1:
            st.markdown(
                "[Buy Them Coffee](https://www.buymeacoffee.com/benno094) to support benno094, the original creator of PDFtoAnki")
        with col2:
            st.markdown("**Disclaimer:** Use at your own risk.")

        with st.sidebar:
            st.markdown(
                "## How to use\n"
                "1. Enter your [Mistral API key](https://console.mistral.ai/) below🔑\n"
                "2. Upload a pdf📄\n"
                "3. Choose pages and Anki Deck🃏\n"
                "4. Make your Anki Cards📚\n"
                "4. Have fun studying🫡\n"
            )
            badge(type="twitter", name="PDFToAnki")
            badge(type="github", name="Zediious95/pdf-anki")

            api_key = st.empty()
            api_key_text = st.empty()
            if "mistral_error" in st.session_state:
                st.warning(
                    f"**Refresh the page and reenter API key, the following error still persists:**\n\n {st.session_state['mistral_error']}")
                st.stop()

            if st.session_state['dev'] == True:
                st.session_state['API_KEY'] = st.secrets.MISTRAL_API_KEY
            elif "email" in st.experimental_user and "EMAIL" in st.secrets and st.experimental_user.email == st.secrets.EMAIL:
                st.session_state['API_KEY'] = st.secrets.MISTRAL_API_KEY
            else:
                st.session_state['API_KEY'] = api_key.text_input(
                    "Enter Mistral API key (Get one [here](https://console.mistral.ai/))",
                    type="password")
                api_key_text.info(
                    "Make sure you have sufficient credits in your Mistral account.")
            if st.session_state["API_KEY"] != "":
                st.session_state["model"] = "mistral-large-latest"

                api_key.empty()
                api_key_text.empty()

            if "deck_key" not in st.session_state:
                st.session_state["deck_key"] = "deck_0"
            deck = st.session_state["deck_key"]
            if "decks" in st.session_state:
                st.selectbox(
                    'Choose a deck',
                    st.session_state['decks'],
                    key=deck,
                    index=None,
                    placeholder='Anki deck'
                )

                if st.button("Refresh decks", key="deck_refresh_btn"):
                    if "decks" in st.session_state:
                        del st.session_state["decks"]
                        if "deck_count" not in st.session_state:
                            st.session_state["deck_count"] = 1
                        st.session_state["deck_count"] += 1
                        st.session_state["deck_key"] = f"deck_{st.session_state['deck_count']}"
                    self.actions.get_decks()

            if "languages" not in st.session_state:
                st.session_state["languages"] = ['English', 'Bengali', 'French', 'German', 'Hindi', 'Urdu',
                                                 'Mandarin Chinese', 'Polish', 'Portuguese', 'Spanish', 'Arabic', 'Russian', 'Romanian']
            if "gpt_lang" in st.session_state:
                if st.session_state["gpt_lang"] in st.session_state["languages"]:
                    st.session_state["languages"].remove(st.session_state["gpt_lang"])
                st.session_state["languages"].insert(0, st.session_state["gpt_lang"])
                del st.session_state["gpt_lang"]
            st.selectbox("Returned language", st.session_state["languages"], on_change=self.clear_flashcards,
                         key="lang")

            page_info = st.empty()
            col1, col2 = st.columns(2)
            with col1:
                if st.session_state['API_KEY'] == "":
                    num = st.number_input('Number of pages', value=1, format='%d', disabled=True)
                else:
                    if "deck_key" in st.session_state:
                        num = st.number_input('Number of pages', value=10, min_value=1,
                                              max_value=st.session_state['page_count'], format='%d', key="num_pages")
                    else:
                        num = st.number_input('Number of pages',
                                              value=st.session_state['page_count'] if st.session_state[
                                                                                          'page_count'] < 10 else 10,
                                              min_value=1, max_value=st.session_state['page_count'], format='%d',
                                              key="num_pages")
            with col2:
                if "deck_key" in st.session_state:
                    if "start_page" not in st.session_state:
                        st.session_state['start_page'] = 1
                    start = st.number_input('Starting page', value=st.session_state.start_page, min_value=1,
                                            max_value=st.session_state['page_count'], format='%i', key="start_page")
                else:
                    start = st.number_input('Starting page', value=None, min_value=1,
                                            max_value=st.session_state['page_count'], format='%i', key="start_page")
            if st.session_state['API_KEY'] == "":
                st.warning("Enter API key to remove limitations")

            deck_info = st.empty()
        if "start_page" in st.session_state and st.session_state.start_page == None:
            page_info.info("Choose a starting page")
            if "temp_file_path" in st.session_state:
                extracted_data, page_count = self.extract_pdf_data(st.session_state["temp_file_path"])

                st.markdown("**Preview:**")

                for i in range(0, st.session_state['page_count']):
                    if i == st.session_state['page_count']:
                        break
                    st.image(extracted_data[i]["image"], caption=f"Page {str(i + 1)}")
        else:
            with st.sidebar:
                if "deck_key" not in st.session_state:
                    st.session_state["deck_key"] = "deck_0"
                deck = st.session_state["deck_key"]
                if "decks" in st.session_state:
                    st.selectbox(
                        'Choose a deck',
                        st.session_state['decks'],
                        key=deck,
                        index=None,
                        placeholder='Anki deck'
                    )

                    if st.button("Refresh decks", key="deck_refresh_btn"):
                        if "decks" in st.session_state:
                            del st.session_state["decks"]
                            if "deck_count" not in st.session_state:
                                st.session_state["deck_count"] = 1
                            st.session_state["deck_count"] += 1
                            st.session_state["deck_key"] = f"deck_{st.session_state['deck_count']}"
                        self.actions.get_decks()
            if st.session_state['API_KEY'] == "":
                st.warning("Please enter your Mistral API key to use the flashcard generation feature.")
                st.stop()

            if "temp_file_path" in st.session_state:
                extracted_data, page_count = self.extract_pdf_data(st.session_state["temp_file_path"])

                st.markdown("**Preview:**")

                for i in range(st.session_state['start_page'] - 1,
                               min(st.session_state['start_page'] + st.session_state['num_pages'] - 1,
                                   st.session_state['page_count'])):
                    if i == st.session_state['page_count']:
                        break
                    st.image(extracted_data[i]["image"], caption=f"Page {str(i + 1)}")

            if "temp_file_path" in st.session_state:
                extracted_data, page_count = self.extract_pdf_data(st.session_state["temp_file_path"])

                st.markdown("**Flashcards:**")

                for i in range(st.session_state['start_page'] - 1,
                               min(st.session_state['start_page'] + st.session_state['num_pages'] - 1,
                                   st.session_state['page_count'])):
                    if i == st.session_state['page_count']:
                        break

                    col1, col2 = st.columns([0.7, 0.3])

                    with col1:
                        st.image(extracted_data[i]["image"], caption=f"Page {str(i + 1)}")

                    with col2:
                        if 'flashcards_' + str(i) in st.session_state:
                            p = i
                            flashcards = json.loads(json.dumps(st.session_state['flashcards_' + str(i)]))

                            if f"{i}_is_title" in st.session_state:
                                flashcards = None
                                st.info(
                                    "No flashcards generated for this slide as it doesn't contain relevant information.")

                            if flashcards:
                                if st.session_state['API_KEY'] == "":
                                    if len(flashcards) > 2:
                                        flashcards = flashcards[:2]
                                length = len(flashcards)
                                st.session_state["flashcards_" + str(i) + "_count"] = length

                                for j in range(length):
                                    if f"fc_active_{i, j}" not in st.session_state:
                                        st.session_state[f"fc_active_{i, j}"] = True

                                    if f"flashcards_{i}_tags" not in st.session_state:
                                        st.session_state[f"flashcards_{i}_tags"] = ""

                                    st.markdown(f"**Flashcard {j + 1}:**")
                                    st.checkbox("Active", key=f"fc_active_{i, j}", value=True)
                                    st.text_area("Front", key=f"fc_front_{i, j}", value=flashcards[j]['front'],
                                                 height=100)
                                    st.text_area("Back", key=f"fc_back_{i, j}", value=flashcards[j]['back'],
                                                  height=100)
                                    st.text_input("Tags", key=f"fc_tags_{i, j}",
                                                  value=st.session_state[f"flashcards_{i}_tags"])

                                    if st.button("Add to Anki", key=f"add_{i, j}"):
                                        if st.session_state[f"fc_active_{i, j}"]:
                                            self.add_flashcard_to_anki(i, j)

                                    st.markdown("---")

                                if st.button("Regenerate Flashcards", key=f"regen_{i}"):
                                    self.generate_flashcards(i, regen=True)

                                if st.button("Add All to Anki", key=f"add_all_{i}"):
                                    self.add_all_flashcards_to_anki(i)

                        else:
                            if st.button("Generate Flashcards", key=f"gen_{i}"):
                                self.generate_flashcards(i)

                    st.markdown("---")

    def generate_flashcards(self, page, regen=None):
        if regen:
            if f"{page}_is_title" in st.session_state:
                del st.session_state[f"{page}_is_title"]
            if f"flashcards_generated_{page}" in st.session_state:
                del st.session_state[f"flashcards_generated_{page}"]
        if f"flashcards_generated_{page}" not in st.session_state:
            flashcards = self.actions.send_to_gpt(page)

            if flashcards:
                flashcards_clean = self.actions.cleanup_response(flashcards)

                st.session_state['flashcards_' + str(page)] = flashcards_clean

            if regen:
                st.rerun()

    def add_flashcard_to_anki(self, page, index):
        deck = st.session_state[f"{st.session_state['deck_key']}"]
        front = st.session_state[f"fc_front_{page, index}"]
        back = st.session_state[f"fc_back_{page, index}"]
        tags = st.session_state[f"fc_tags_{page, index}"]

        front = markdown.markdown(front, extensions=['nl2br'])
        back = markdown.markdown(back, extensions=['nl2br'])

        note = {
            "deckName": deck,
            "modelName": "AnkingOverhaul",
            "front": front,
            "back": back,
            "tags": [tags]
        }

        API("addNotes", deck=deck, flashcards=[note])

    def add_all_flashcards_to_anki(self, page=None):
        if page is not None:
            self.add_all_flashcards_to_anki_page(page)
        else:
            for i in range(st.session_state['start_page'] - 1,
                           min(st.session_state['start_page'] + st.session_state['num_pages'] - 1,
                               st.session_state['page_count'])):
                if i == st.session_state['page_count']:
                    break
                self.add_all_flashcards_to_anki_page(i)

    def add_all_flashcards_to_anki_page(self, page):
        if 'flashcards_' + str(page) in st.session_state:
            flashcards = json.loads(json.dumps(st.session_state['flashcards_' + str(page)]))

            if f"{page}_is_title" in st.session_state:
                return

            if flashcards:
                if st.session_state['API_KEY'] == "":
                    if len(flashcards) > 2:
                        flashcards = flashcards[:2]
                length = len(flashcards)
                st.session_state["flashcards_" + str(page) + "_count"] = length

                notes = []
                for j in range(length):
                    if f"fc_active_{page, j}" in st.session_state and st.session_state[f"fc_active_{page, j}"]:
                        front = st.session_state[f"fc_front_{page, j}"]
                        back = st.session_state[f"fc_back_{page, j}"]
                        tags = st.session_state[f"fc_tags_{page, j}"]

                        front = markdown.markdown(front, extensions=['nl2br'])
                        back = markdown.markdown(back, extensions=['nl2br'])

                        note = {
                            "deckName": st.session_state[f"{st.session_state['deck_key']}"],
                            "modelName": "AnkingOverhaul",
                            "front": front,
                            "back": back,
                            "tags": [tags]
                        }

                        notes.append(note)

                if notes:
                    API("addNotes", deck=st.session_state[f"{st.session_state['deck_key']}"], flashcards=notes)

    def clear_flashcards(self):
        for key in list(st.session_state.keys()):
            if key.startswith('flashcards_'):
                del st.session_state[key]
            if key.startswith('fc_'):
                del st.session_state[key]

    def clear_data(self):
        for key in list(st.session_state.keys()):
            if key.startswith('text_'):
                del st.session_state[key]
            if key.startswith('image_'):
                del st.session_state[key]
            if key.startswith('flashcards_'):
                del st.session_state[key]
            if key.startswith('fc_'):
                del st.session_state[key]

    def has_active_flashcards(self):
        for key in list(st.session_state.keys()):
            if key.startswith('fc_active_'):
                if st.session_state[key]:
                    return True
        return False

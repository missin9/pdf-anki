# PDF to Anki

## Introduction

PDF to Anki program using GPT3.5-turbo from OpenAI. Streamlit is the web-GUI

Version 0.2 alpha (It is very buggy; lots of room for user error)

## Requirements:

- An OpenAI key (with credits, obviously)
- Anki with AnkiConnect installed (Addon #: 2055492159)

## Usage:

1. Select a PDF.
2. Click pages in pdf to be turned into flash cards; they will turn grey. The text from page will be automatically sent to GPT.
3. Flash cards created by GPT will be displayed and can then be modified before being added to Anki.

~~Note: It is possible to select other pages while one page is loading.~~

### To do:

- Allow user to select regions of slides
- Make layout prettier!
- Add option to choose title of deck and possibly call up available decks in Anki to choose location
- Better error management
- Option to select returned language
- Change prompt options ()

### Changelog:

0.2 alpha
- Changed to Streamlit Web-GUI (This greatly simplified the frontend)
- Removed image detection
- Added multi-threading to load flashcards without locking up preview 
- Shifted flashcards view to show alongside page preview
- Added status bar to keep user in the loop
- Using pymupdf instead of pdf2image to reduce reliance on external libraries

0.1 alpha
- First release
# Automated WhatsApp Assistant

Ever missed out on grabbing a shift because someone canceled in the group chat and you saw it too late?  
Or spent way too long watching WhatsApp like it’s the stock market?  
**Not anymore.**

**AutoWA (Automated WhatsApp Assistant)** is your automated sidekick that:
- 👀 Monitors WhatsApp Desktop for messages about canceled shifts  
- 🧠 Understands casual time ranges like "2 to 4" or "9-11"  
- 📆 Checks your Google Calendar to see if you’re free  
- 🤖 Sends a reply in WhatsApp *for you*  
- 📌 Adds the shift directly to your calendar

All hands-free. All in real time.

[Screen Recording 2025-05-09 at 3.24.53 PM.zip](https://github.com/user-attachments/files/20127953/Screen.Recording.2025-05-09.at.3.24.53.PM.zip)

# Setup 

To get started with AutoWA, first clone the repository to your local machine and install the required Python libraries listed at the top of the script. This will set up key dependencies like pytesseract for OCR, spaCy for natural language processing, dateparser for interpreting fuzzy time phrases, and google-api-python-client to access your Google Calendar. You’ll also need to install the English NLP model with python -m spacy download en_core_web_sm. After installing dependencies, set up your Google Calendar API by creating a project in the Google Cloud Console, enabling the Calendar API, and downloading your credentials.json file into the project directory. When you first run the script, you’ll be prompted to authorize access via your browser. Since AutoWA automates WhatsApp via AppleScript and pyautogui, it only works on macOS. Make sure WhatsApp Desktop is installed and that your terminal has accessibility permissions enabled. Once everything is configured, simply run python AutomatedWhatsApp.py. The script will bring WhatsApp to the front, read incoming messages via OCR, detect any cancellations, parse the mentioned time, check your calendar for availability, and—if you’re free—automatically send a message in WhatsApp and add the event to your calendar. If no action is needed, it checks again every 10 seconds. Once a shift is claimed, the script exits.

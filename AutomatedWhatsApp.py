
"""
----------------------------------------------------------
Automated WhatsApp Calendar Tool
----------------------------------------------------------
Description:
This script monitors messages in the WhatsApp desktop window using OCR (Optical Character Recognition) 
to detect if a TA has cancelled their office hours. When a cancellation is identified, it extracts the 
mentioned time range from the message, infers AM/PM if not specified, and checks the user's availability 
on Google Calendar for that period.

If the user is free during the cancelled slot, the script automatically:
  - Responds in WhatsApp offering to take over the shift
  - Adds the shift to the user's Google Calendar
  - Stops running after a successful handoff

Features:
- Uses AppleScript on macOS to bring WhatsApp to the front
- Captures and reads message text using OCR via pytesseract
- Applies natural language processing with spaCy to identify cancellation context
- Parses flexible time ranges (e.g., "2 to 4", "9:30-11") and intelligently infers AM/PM
- Validates schedule conflicts using the Google Calendar API
- Sends an automated WhatsApp reply if the shift can be covered
- Automatically logs the shift in the user's calendar

Platform: macOS (WhatsApp Desktop)
Dependencies: pytesseract, pyautogui, dateparser, spaCy, Google API client, AppleScript


Author: Quinn Carolan
Created: April 14th, 2025
Latest version: May 8th, 2025
----------------------------------------------------------
"""

from Google import Create_Service                                               # Returns a service object that lets you call Google Calendar API 
import datetime                                                                 # Used to check real/current time
import time                                                                     # Pausing execution (e.g., time.sleep(10))
import pyautogui                                                                # Automates mouse, keyboard, and screenshots                                                     # Lets you interact with open application windows on screen
import spacy                                                                    # NLP to interpret WhatsApp lingo
import re                                                                       # interprets patterns in WhatsApp conversation
import dateparser                                                               # Extract time ranges from WhatsApp
import pytesseract                                                              # Reads and analyzes text from WhatsApp screenshots
import subprocess                                                               # Controls apps on MacOS
from pytz import timezone                                                       # Handles time zone location

CLIENT_SECRET_FILE = 'credentials.json'                                         # Path to Google API credentials
API_NAME = 'calendar'                                                           # Specifies the Google service you're using (Google Calendar)
API_VERSION = 'v3'
SCOPES = ['https://www.googleapis.com/auth/calendar']                           # Define access permissions (read/write)

service = Create_Service(CLIENT_SECRET_FILE, API_NAME, API_VERSION, SCOPES)     # Initialize Google Calendar API service with your credentials

nlp = spacy.load("en_core_web_sm")                                              # Load language model for natural language processing

def bring_whatsapp_to_front():
    subprocess.run([                                                            # Uses subprocess to run an AppleScript command on macOS
        "osascript", "-e",                                                      # Brings WhatsApp to foreground
        'tell application "WhatsApp" to activate'
    ])

def read_whatsapp():
    try:
        bring_whatsapp_to_front() 
        time.sleep(1)
        region = (100, 100, 800, 600)
        screenshot = pyautogui.screenshot(region=region)
        text = pytesseract.image_to_string(screenshot)                          # Use OCR to convert screenshot into readable text 
        return text
    except Exception as e:                                                      # If window not found or OCR fails, show error 
        print("Error reading WhatsApp:", e)
        return ""

def message_indicates_cancellation(text):
    doc = nlp(text.lower())                                                     # Convert message to lowercase and proces using spacy

    cancel_keywords = {"cancel", "skip", "drop", "remove", "postpone"}          # Common verbs indicating cancellation 
    oh_keywords = {"office hours", "oh", "ta hours", "hours"}                   # Key worlds suggesting what the message is about 

    cancel_found = False
    oh_found = False

    for token in doc:                                                           # Loop through all words in the message
        if token.lemma_ in cancel_keywords:                                     # Check if any word matches cancellation 
            cancel_found = True

    for chunk in doc.noun_chunks:                                               # Check phases like "ta hours"
        if any(keyword in chunk.text for keyword in oh_keywords):
            oh_found = True

    return cancel_found and oh_found                                            # Only return true if BOTH conditions are met 

def extract_time_range_from_text(text):
    now = datetime.datetime.now()                                               # Get current datetime
    today = now.date()                                                          # Get today's date

    pattern = r'(\d{1,2}(?::\d{2})?)\s*(?:to|-)\s*(\d{1,2}(?::\d{2})?)'
    matches = re.findall(pattern, text, re.IGNORECASE)                          # Find all matching time pairs

    for start_raw, end_raw in matches:                                          # Loop through each matched time range
        def infer_am_pm(raw, is_start=True):                                    # Helper function to guess am/pm if not given
            # Extract just the hour
            hour_part = raw.split(":")[0] if ":" in raw else raw                # Extract the hour part
            try:
                hour = int(hour_part)                                           # Convert to integer
            except:
                return raw                                                      # If conversion fails, return unchanged
            
            if 'am' in raw.lower() or 'pm' in raw.lower():
                return raw                                                      # If already contains am/pm, leave it alone

            
            if is_start and 1 <= hour <= 11:                                    # Assume am if before 12 and it's the start time
                return raw + 'am'
            
            elif not is_start and 1 <= hour <= 7:                               # Assume pm if it's the end time and if it's in the 1-7 range
                return raw + 'pm'
            
            return raw + 'pm'                                                   # Default to pm otherwise

        start_str = infer_am_pm(start_raw, is_start=True)                       # Apply am/pm start and end times
        end_str = infer_am_pm(end_raw, is_start=False)

        settings = {                                                            # Interpret time in context of today
            'RELATIVE_BASE': datetime.datetime.combine(today, datetime.time(0, 0)),
            'PREFER_DATES_FROM': 'future'                                       # Helps prevent past-time parsing mistakes
        }

        start_dt = dateparser.parse(start_str, settings=settings)               # Parse strings into datetime objects
        end_dt = dateparser.parse(end_str, settings=settings)

        if start_dt and end_dt:                                                 # Force both datetimes to use today's date
           
            start_dt = start_dt.replace(year=now.year, month=now.month, day=now.day)
            end_dt = end_dt.replace(year=now.year, month=now.month, day=now.day)

            
            if start_dt > end_dt:                                               # Reject invalid time ranges (e.g.m 5pm to 2 pm)
                print(f"❌ Ignoring reversed time range: {start_dt} to {end_dt}")
                return None, None

            eastern = timezone('America/New_York')                              # Convert times to Eastern
            start_dt = eastern.localize(start_dt)
            end_dt = eastern.localize(end_dt)
            return start_dt.isoformat(), end_dt.isoformat()                     # Return ISO-formatted strings suitable for google Calender API

    return None, None


def check_availability(time_start,time_end):                                    # Checks if your free between two ISO-formatted times 
    events_result = service.events().list(
        calendarId='primary',
        timeMin=time_start,
        timeMax=time_end,
        maxResults=10,                                                          # Limit results for performance
        singleEvents=True
    ).execute()

    events = events_result.get('items', [])                                     # Extracts list of events 

    for event in events:                                                        # Loop through events to check for time conflicts
        event_start = event['start'].get('dateTime', event['start'].get('date'))# Get event start time
        event_end = event['end'].get('dateTime', event['end'].get('date'))      # Get event end time

        if event_start and event_end:                                           # Only proceed if both times are present 
                                                                                
            event_start = datetime.datetime.fromisoformat(event_start)          # Convert event time strings to datetime objects
            event_end = datetime.datetime.fromisoformat(event_end)
            
                                                                                
            new_start = datetime.datetime.fromisoformat(time_start)             # Convert input time range to datetime objects
            new_end = datetime.datetime.fromisoformat(time_end)

                                                                                # Check if the event overlaps the proposed time
            if (new_start < event_end and new_end > event_start):               # Overlap condition
                print(f"Conflict with event: {event.get('summary', 'No Title')}")
                return False                                                    # If there's an overlap, you're not free

    return True                                                                 # Free if loop completes with no overlap

def send_whatsapp_reply(message):
    time.sleep(0.5)
    pyautogui.write(message, interval=0.1)                                      # Type intended message at a slower speed to make sure its correct
    pyautogui.press('enter')                                                    # Press enter to send 

def create_calendar_event(start_time, end_time):                                # Function creates calendar event
    event = {                                                                   
        'summary': 'TA Office Hours (Covered)',                                 # Event title
        'start': {'dateTime': start_time, 'timeZone': 'America/New_York'},      # Define start time
        'end': {'dateTime': end_time, 'timeZone': 'America/New_York'},          # Define end time
    }
    service.events().insert(calendarId='primary', body=event).execute()         # Use Google Calendar API to add the event to the primary calendar

def main_loop():
    print("🕵️‍♂️ Listening in on WhatsApp chatter... waiting for a TA to flake.")
    while True:                                                                 # Continuous loop to monitor for messages
        text = read_whatsapp()                                                  # Get text via OCR
        if message_indicates_cancellation(text):                                # Check if message suggests cancellation
            time_start, time_end = extract_time_range_from_text(text)           # Extract start and end time from text

            if time_start and time_end:                                         # Proceed only if a valid time range is extracted
                print(f"Time range extracted: {time_start} to {time_end}")
                                                                                                          
                if check_availability(time_start, time_end):                    # Check availability during that time 
                    send_whatsapp_reply("I'm free, I can take over!")           # If free, offer to take the shift
                    create_calendar_event(time_start, time_end)                 # Create an event in your primary google calendar
                    print("✅ Shift secured. Exiting.")                         # If shift was secured, exit code
                    break
                else:
                    print("❌ Not free during that time.")                      
            else:
                print("🕑 Could not understand the time range.")                # Couldn't parse the time from message
        time.sleep(10)                                                          # Wait for a while before checking again    

main_loop()
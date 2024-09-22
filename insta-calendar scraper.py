#web scraping
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait

import os
import wget
import time
import getpass

#ocr
import requests
from io import BytesIO
import tempfile
from bs4 import BeautifulSoup
import lxml
import pytesseract
import PIL.Image
import cv2

import spacy
import re

#calendar automation
import datetime as dt
from datetime import datetime, timedelta

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES= ["https://www.googleapis.com/auth/calendar"]


my_user= getpass.getpass('Enter username: ')
my_pw= getpass.getpass('Enter password: ')
driver= webdriver.Chrome()
driver.get("https://www.instagram.com/")
user_field= WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input[name='username']")))
pass_field= WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input[name='password']")))

user_field.clear()
pass_field.clear()
user_field.send_keys(my_user)
pass_field.send_keys(my_pw)

log_in= WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']"))).click()
try:
    not_now = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, "//div[contains(text(), 'Not now') and @role='button']")))
    not_now.click()
except Exception as e:
    print(f"Exception: {e}")
try:
    not_now_notif = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Not Now')]")))
    not_now_notif.click()
except Exception as e:
    print(f"Exception: {e}")


def download_image(url):
    response= requests.get(url)
    image= PIL.Image.open(BytesIO(response.content))
    temp_dir= tempfile.mkdtemp()

    temp_image_path= os.path.join(temp_dir, 'temp_image.jpg')
    image.save(temp_image_path)
    return temp_image_path

def ocr_function(image_path):
    myconfig= r"--psm 3 --oem 3"
    image_text= pytesseract.image_to_string(PIL.Image.open(image_path), config=myconfig)
    return image_text

#add the instagram pages you want to look through here
instagram_pages= []
post_data= []
for page in instagram_pages:
    try:
        driver.get(page)
    except Exception as e:
        print(f"couldn't get to website. error: {e}")   
    post_elements= WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div._aagu")))
    post_elements[0].click()

    for index, post_element in enumerate(post_elements[:4]):
        try:
            caption_element= post_element.find_element(By.XPATH, "//h1[@class='_ap3a _aaco _aacu _aacx _aad7 _aade']")
            caption= caption_element.text
        except Exception as e:
            print(f"caption not found. error {e}")
        try:
            image_elements= post_element.find_elements(By.XPATH, ".//div[@class='_aagv']/img")
            for image_element in image_elements:
                image_src= image_element.get_attribute('src')

                image_path= download_image(image_src)
                if image_path: #debugging
                    image_text= ocr_function(image_path)
                else:
                    print("Image couldn't be downloaded")
        except Exception as e:
            print(f"image not found. error {e}")
        post_data.append({'caption': caption, 'image': image_text, 'account': page})       
        try:
            next_post= WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button._abl-[type='button'] svg[aria-label='Next']"))).click()
        except Exception as e:
            print(f"Error going to next post: {e}")
print(post_data)
    
def parse_datetime(date, time):
    current_date= dt.datetime.now()
    if date.lower()== "today":
        event_date= current_date
    elif date.lower() == "tomorrow":
        event_date = current_date + timedelta(days=1)
    else:
        event_date = None
    time_formats= [
        "%I:%M %p", 
        "%I %p",
        "%I%p",
    ]
    if event_date:
        for f in time_formats:
            try:
                event_time= dt.datetime.strptime(time, f).time()
                event_datetime = datetime.combine(event_date.date(), event_time)
                return event_datetime.isoformat()
            except ValueError:
                continue   
    datetime_str = f"{date} {time}"
    possible_datetime_formats = [
        "%B %d %I:%M %p",
        "%B %d %I %p",
        "%A, %B %d %I:%M %p",
        "%A, %B %d %I %p",
        ]
    for f in possible_datetime_formats:
        try:
            event_datetime = dt.datetime.strptime(datetime_str, f)
            return event_datetime.isoformat()
        except ValueError:
                continue     
    return None  

nlp= spacy.load("en_core_web_trf")

def extract_event_details(text):
    doc= nlp(text)
    date= ""
    time= ""
    location= ""
    title= ""

    for ent in doc.ents:
        if ent.label_ == "DATE":
            date = ent.text
        elif ent.label_ == "TIME":
            time = ent.text
        elif ent.label_== "GPE":
            location= ent.text
        elif not location:
            location_patterns = re.compile(r'@\w+|at \w+|in \w+|on \w+')
            matches= location_patterns.findall(text)
            if matches:
                location= matches[0]
    if not location:
        location_patterns= re.compile(r'(@\w+|at \w+|in \w+|on \w+)')
        matches = location_patterns.findall(text)
        if matches:
            location = matches[0]
    excluded_words = set(["the", "a", "an", "and", "at", "in", "on", "with", "for", "of", "to", "by", "from", "is", "as"])
    title_chunks = [chunk.text for chunk in doc.noun_chunks if chunk.text.lower() not in excluded_words]
    if title_chunks:
        title = max(title_chunks, key=len)
    title = title.strip().replace('\n', ' ').replace('\r', '')
    title = re.sub(' +', ' ', title)
    event_datetime= ""
    if date and time:
        try:
            event_datetime= parse_datetime(date, time)
        except ValueError as e:
            print(f"Error parsing date and time: {e}")
    return {"date": event_datetime, "location": location, "title": title, "page": ""}

extracted_events= []
for event in post_data:
    caption= event['caption']
    image= event['image']
    page= event['account']
    details= extract_event_details(caption+ " " + image+ " " + page)
    details['page']= page

    if details["date"]:
        try: 
            event_datetime = dt.datetime.fromisoformat(details['date'])
            details['start_datetime'] = event_datetime.isoformat()
            details['end_datetime'] = (event_datetime + timedelta(hours=1)).isoformat()
            
            extracted_events.append(details)
        except ValueError as e:
            print(f"Error parsing date and time: {e}")


def main():
    creds= None
    creds_path= os.path.join(os.path.expanduser("~"), "Desktop", "scraper", "credentials.json") 
    if os.path.exists("token.json"):
        creds= Credentials.from_authorized_user_file("token.json")
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow= InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
            creds= flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    try:
        service= build("calendar", "v3", credentials= creds)
        for event in extracted_events:
            event_datetime= event["date"]
            if event_datetime:
                calendar_event= {
                    "summary": event["title"],
                    "location": event["location"],
                    "description": event["page"],
                    "colorId": 9,
                    "start":{
                        "dateTime": event_datetime,
                        "timeZone": "America/New_York"
                    },  
                    "end":{
                        "dateTime": (datetime.fromisoformat(event_datetime) + timedelta(hours=1)).isoformat(),
                        "timeZone": "America/New_York"
                    },
                }
                calendar_event= service.events().insert(calendarId="primary", body=calendar_event).execute()
                print(f"Event created {event.get('htmlLink')}")

    except HttpError as error:
        print("An error has occured:", error)

if __name__== "__main__":
    main()
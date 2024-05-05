from selenium import webdriver
from selenium.webdriver import ActionChains, Keys
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from dotenv import load_dotenv
import logging
import requests
from datetime import datetime
import base64
import json
import time
import pytz
import re
import os

## write to log
logging.basicConfig(level=logging.INFO,filename='log_correction.txt',filemode='a',
    format='%(asctime)s %(filename)s %(levelname)s:%(message)s')


def wait_for_element_location_to_be_stable(element):
    initial_location = element.location
    previous_location = initial_location
    start_time = time.time()
    while time.time() - start_time < 1:
        current_location = element.location
        if current_location != previous_location:
            previous_location = current_location
            start_time = time.time()
        time.sleep(0.4)

def click_more_buttons():
    more_buttons = 0
    body_elements = driver.find_elements(By.CLASS_NAME, 'jftiEf')# Find buttons within the current 'jftiEf' element
    for body in body_elements: 
        buttons = body.find_elements(By.CLASS_NAME, "w8nwRe")# Iterate over each button within the current 'jftiEf' element
        for button in buttons:
            if button.text == "全文":# Check if the button text is "More"
                more_buttons += 1
                button.click()
            print(more_buttons)#this will tell us how many more buttons are currently loaded
            print(body.text)

def find_attribute_or_text(driver, by_method, selector, attribute=None):
    try:
        element = driver.find_element(by_method, selector)
        if attribute:
            return element.get_attribute(attribute)
        else:
            return element.text
    except NoSuchElementException:
        return None

# read the ramen list
restaurant_name = []
with open("ramen_list.txt",'r') as input:
    for line in input:
        restaurant_name.append(re.sub(r'\((\d+|\w)*(開幕|預定|試賣|未定|試營運|預計)*\)|\((\w|\d+)*停\w*業*\)',
                                '', line.strip()))

## browser setting
google_maps = 'https://www.google.com.tw/maps'
options = Options()
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')  
driver = webdriver.Edge(options=options)


# timezone = pytz.timezone('Asia/Taipei')
datetime.now(pytz.utc)
## loop throught list
last_successful_index = 303
last_title = 'a'
title = 'a'

# open the browser and handle the status
driver.get(google_maps)
origin_window = driver.current_window_handle

# for i in range(last_successful_index, len(restaurant_name)):
for i in range(last_successful_index, 423):
    ramen = restaurant_name[i]

    if origin_window not in driver.window_handles:
        driver.quit()
        driver = webdriver.Edge(options=options) # resatrt
        driver.get(google_maps)
        origin_window = driver.current_window_handle
        time.sleep(1)

    actionChains = ActionChains(driver)
    wait = WebDriverWait(driver, timeout=5)
    time.sleep(1)
    try:
        search_box = wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'searchboxinput')))
        search_box.clear()
        ## go to the ramen restaurant
        actionChains.send_keys_to_element(search_box, ramen)  # Send keys to the element
        actionChains.send_keys(Keys.ENTER)  # Press Enter key
        actionChains.perform()  # Perform the actions
        time.sleep(1)
        
        ## get the name
        try:
            counter = 0
            while title == last_title:
                time.sleep(1)
                counter += 1
                heading_element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'h1.DUwDvf')))
                title = heading_element.text
                if counter == 5:
                    break

        except Exception as e:
            logging.error(f"cannot get name: {ramen}!{e}")

        ## get coordination
        try:
            get_url = driver.current_url
            url = re.sub(r'@([-\d.]+),([-\d.]+),(\d+).*(\d+)\w/','',get_url)
            # print(url)
            coord = re.search(r'([-\d.]+)(!4d)([-\d.]+)',get_url)
            latitude = coord.group(1)
            longitude = coord.group(3)

            crawling_result = {
                "alias":ramen,
                "name":title,
                "maps_url":url,
                "latitude":latitude,
                "longitude":longitude,
                "update_time":datetime.now(pytz.utc)
            }
            # print(crawling_result)
            print(f"Success:\t{ramen}\t{title}")
            # print(f"{crawling_result}\n\n")
            with open('./correction_list.json','a',encoding='utf-8') as file:
                json.dump(crawling_result,file,ensure_ascii=False,indent=4)
                file.write(",\n")
            
            # for next round check
            last_title = title
        except:
            print(f"Error:\t{ramen}")
            with open("redo_please.txt","a") as redo:
                redo.write(f"{ramen}\t{get_url}\n")

    # hadling session error like page crash
    except Exception as e:
        logging.exception(f"Exception for {ramen}: {e}")
        time.sleep(2)

        try:
            driver.quit()
        except:
            logging.info("Browser had been closed!")

        driver = webdriver.Edge(options=options) # resatrt
        driver.get(google_maps)
        continue


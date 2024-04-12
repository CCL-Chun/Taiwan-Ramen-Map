from selenium import webdriver
from selenium.webdriver import ActionChains, Keys
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException
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
import re
import os

logging.basicConfig(level=logging.INFO,filename='log.txt',filemode='a',
    format='%(asctime)s %(filename)s %(levelname)s:%(message)s')

## connect to cloud MongoDB
try:
    load_dotenv()
    username = os.getenv("MongoDB_user")
    password = os.getenv("MongoDB_password")
    cluster_url = os.getenv("MongoDB_cluster_url")
    uri = f"mongodb+srv://{username}:{password}@{cluster_url}?retryWrites=true&w=majority&appName=ramen-taiwan"
    client = MongoClient(uri, server_api=ServerApi('1')) # Create a new client and connect to the server
    db = client['ramen-taiwan']
    collection = db['ramen_info']
except Exception as e:
    logging.error(f"Cannot connect to MongoDB!{e}")

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


# read the ramen list
restaurant_name = []
with open("ramen_list.txt",'r') as input:
    for line in input:
        restaurant_name.append(re.sub(r'\((\d+|\w)*(開幕|預定|試賣|未定|試營運|預計)*\)|\((\w|\d+)*停\w*業*\)',
                                '', line.strip()))

## start browser
google_maps = 'https://www.google.com.tw/maps'
options = Options()
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')  
driver = webdriver.Edge(options=options)

for ramen in restaurant_name:
    ## start browser
    driver.get(google_maps)
    actionChains = ActionChains(driver)
    ## go to the ramen restaurant
    actionChains.send_keys(ramen)  # Send keys to the element
    actionChains.send_keys(Keys.ENTER)  # Press Enter key
    actionChains.perform()  # Perform the actions
    wait = WebDriverWait(driver, 5)

    ## get the name
    try:
        heading_element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'h1.DUwDvf')))
        title = heading_element.text
        print(title)
    except Exception as e:
        logging.error(f"cannot get name: {ramen}!{e}")
        title = ramen

    ## go to opening time
    try:
        opening_buttons = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR,'button[data-item-id="oh"]')))
        actionChains.scroll_to_element(opening_buttons[0]).perform()
        opening_buttons[0].click()
    except TimeoutException:
        try:
            opening_buttons = wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME,'o0Svhf')))
            actionChains.scroll_to_element(opening_buttons[0]).perform()
            opening_buttons[0].click()
        except Exception as e:
            logging.error(f"Find no element of opening time: {ramen}!{e}")
    except Exception as e:
        logging.exception(f"cannot get opening time of {ramen}!")

    try:
        time_all = wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "y0skZc")))
        open_time = {}

        for time_detail in time_all:
            day = time_detail.find_element(By.CLASS_NAME,'ylH6lf').text
            duration = [item.text for item in time_detail.find_elements(By.CLASS_NAME,'G8aQO')]
            if day:
                open_time[day] = duration
    except Exception as e:
        logging.error(f"Error while crawling opening time: {ramen}!{e}")
    
    ## get back page if need
    try:
        back_button = driver.find_element(By.CSS_SELECTOR,'button[aria-label="返回"]')
        back_button.click()
    except Exception:
        logging.info(f"no need to get back from opening time page: {ramen}!")

    ## get img url
    img_button = wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "ZKCDEc")))
    time.sleep(1)
    image_element = img_button[0].find_element(By.TAG_NAME, 'img')
    img_url = image_element.get_attribute('src')

    ## img to base64
    try:
        response = requests.get(img_url,timeout=10)
        image_content = response.content
        base64_string = base64.b64encode(image_content)
        base64_string = base64_string.decode('utf-8')
        base64_image_url = f'data:image/png;base64,{base64_string}'
    except Exception as e:
        logging.exception(f"cannot convert url to base64 for {ramen}!Exception: {e}")

    ## get official website
    try:
        website = driver.find_element(By.CSS_SELECTOR,'a[data-item-id="authority"]').get_attribute('href')
    except Exception as e:
        logging.exception(f"cannot find website of {ramen} !Exception: {e}")

    ## get address
    try:
        address = driver.find_element(By.CSS_SELECTOR,'button[data-item-id="address"]').get_attribute('aria-label')
        address = re.sub(r'(地址: \d+)','',address)
    except Exception as e:
        logging.exception(f"cannot find address of {ramen} !Exception: {e}")

    ## go to reviews
    try:
        main_buttons = wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "Gpq6kf")))
    except Exception as e:
        logging.error(f"{ramen} reviews not done yet!Error: {e}")
        continue

    actionChains.move_to_element(main_buttons[1]).perform()
    main_buttons[1].click()

    ## get stats rating
    ## mean rating
    mean_rating_element = wait.until(EC.presence_of_all_elements_located((By.XPATH, '//*[@id="QA0Szd"]/div/div/div[1]/div[2]/div/div[1]/div/div/div[2]/div[2]/div/div[2]/div[1]')))
    mean_rating = mean_rating_element[0].text
    overall_rating = {"mean":mean_rating}
    ## rating distribution
    rating_elements = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'tr.BHOKXe')))
    for element in rating_elements:
        aria_label = element.get_attribute('aria-label')
        parts = aria_label.split()
        star_rating = int(parts[0]) 
        review_count = ''.join(filter(str.isdigit, parts[1])) # remove commas and other words
        review_count = int(review_count)  
        overall_rating[f'amount_{star_rating}'] = review_count
    
    break_condition = False
    while not break_condition:
        try:
            end_of_reviews = driver.find_elements(By.CLASS_NAME, 'qjESne')
        except Exception:
            end_of_reviews = driver.find_elements(By.CLASS_NAME, 'qCHGyb')
            break_condition = True
        
        click_more_buttons()
        actionChains.scroll_to_element(end_of_reviews[-1]).perform()

        try:
            results = wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "jftiEf")))
        except Exception as e:
            logging.info(f"{ramen} has no more reviews!")
            break_condition = True

        temp = results[-1]
        wait_for_element_location_to_be_stable(temp)

        if len(results) > 100:
            break_condition = True

    ## get coordination
    get_url = driver.current_url
    coord = re.search(r'@([-\d.]+),([-\d.]+)',get_url)
    latitude = coord.group(1)
    longitude = coord.group(2)

    reviews = []
    for i, result in enumerate(results, start=0):
        comment_span = result.find_element(By.CLASS_NAME, 'wiI7pd')
        user_url = result.find_element(By.CLASS_NAME, "al6Kxe").get_attribute("data-href")
        user_rating = result.find_element(By.CLASS_NAME, "kvMYJc").get_attribute("aria-label").split()[0]
        user_name = result.find_element(By.CLASS_NAME, "d4r55").text
        user_id = re.search(r'(?<=contrib/)\d+', user_url).group(0)
        reviews.append({"user_id":user_id,"user_url":user_url,"user_name":user_name,
                        "rating":user_rating,"comment":comment_span.text})

    crawling_result = {
        "name":title,
        "maps_url":get_url,
        "img_url":img_url,
        "img_base64":base64_image_url,
        "open_time":open_time,
        "website":website,
        "overall_rating":overall_rating,
        "address":address,
        "latitude":latitude,
        "longitude":longitude,
        # "PlaceID":place_id,
        "reviews":reviews,
        "create_time":datetime.utcnow(),
        "update_time":datetime.utcnow()
    }

    insertion = collection.insert_one(crawling_result)
    logging.info(f"Data inserted with _id: {insertion.inserted_id}")
    time.sleep(1)

driver.quit()

from selenium import webdriver
from tempfile import mkdtemp
from selenium.webdriver.common.by import By
from selenium.webdriver import ActionChains, Keys
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from datetime import datetime
import base64
import logging
import requests
import pytz
import boto3
import json
import time
import sys
import re

# system related log
logger = logging.getLogger()
logger.setLevel(logging.INFO)
# selenium log
selenium_logger = logging.getLogger('selenium')
selenium_logger.setLevel(logging.WARNING)
selenium_logger.addHandler(logging.StreamHandler(sys.stderr))

timezone = pytz.timezone('Asia/Taipei')

def lambda_handler(event, context):

    result = []
    errors = []
    # Loop through each message received from SQS
    for record in event['Records']:
        # Parse the message body
        message_body = json.loads(record['body'])
        name = message_body['name']
        maps_url = message_body['maps_url']
        alias = message_body['alias']

        # Process the URL with Selenium
        try:
            processed = scrape_with_selenium(name,maps_url,alias)
            result.append(processed)
        except Exception as e:
            error_message = f"Failed to process {name}: {str(e)}"
            logger.error(error_message)
            errors.append(error_message)
        time.sleep(1)

    try:
        local_time = datetime.now(timezone).strftime("%Y_%m_%d_%H_%M_%S")
        upload_to_s3(result, "ramen-selenium-results", f"test_{local_time}.json")
        logger.info("Successfully uploaded results to S3.")
    except Exception as e:
        logger.error(f"Failed to upload results to S3: {str(e)}")

    if errors:
        upload_to_s3(errors, "ramen-selenium-results", f"errors_{local_time}.json")

    return {
        "statusCode": 200,
        "body": json.dumps({
            "result": "Processing completed",
            "errors": len(errors)
        })
    }


def scrape_with_selenium(name,maps_url,alias):
    # Set the options in the browser
    options = webdriver.ChromeOptions()
    service = webdriver.ChromeService("/opt/chromedriver")

    options.binary_location = '/opt/chrome/chrome'
    options.add_argument("--headless=new")
    options.add_argument('--no-sandbox')
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1280x1696")
    options.add_argument("--single-process")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-dev-tools")
    options.add_argument("--no-zygote")
    options.add_argument(f"--user-data-dir={mkdtemp()}")
    options.add_argument(f"--data-path={mkdtemp()}")
    options.add_argument(f"--disk-cache-dir={mkdtemp()}")
    options.add_experimental_option("prefs", {"intl.accept_languages": "zh-TW"}) ## need to force it

    driver = webdriver.Chrome(options=options, service=service)

    try:
        driver.get(maps_url)
        actionChains = ActionChains(driver)
        wait = WebDriverWait(driver, timeout=5)
        time.sleep(1)

        heading_element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'h1.DUwDvf')))
        title = heading_element.text

        ## get coordination
        try:
            get_url = driver.current_url
            url = re.sub(r'@([-\d.]+),([-\d.]+),(\d+).*(\d+)\w/','',get_url)
            new_url = re.sub(r'place/.*/data','place/data',url)
            coord = re.search(r'([-\d.]+)(!4d)([-\d.]+)',get_url)
            latitude = coord.group(1)
            longitude = coord.group(3)
        except Exception as e:
            logger.exception(f"{title} wrong with url")

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
                logger.error(f"Find no element of opening time: {title}!{e}")
        except Exception as e:
            logger.exception(f"cannot get opening time of {title}!")

        try:
            time_all = wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "y0skZc")))
            open_time = {}

            for time_detail in time_all:
                day = time_detail.find_element(By.CLASS_NAME,'ylH6lf').text
                duration = [item.text for item in time_detail.find_elements(By.CLASS_NAME,'G8aQO')]
                if day:
                    open_time[day] = duration
        except Exception as e:
            logger.error(f"Error while crawling opening time: {title}!{e}")
            open_time = None
        
        ## get back page if need
        try:
            back_button = driver.find_element(By.CSS_SELECTOR,'button[aria-label="返回"]')
            back_button.click()
        except Exception:
            logger.info(f"no need to get back from opening time page: {title}!")

        ## get img url
        try:
            img_button = wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "ZKCDEc")))
            time.sleep(1)
            image_element = img_button[0].find_element(By.TAG_NAME, 'img')
            img_url = image_element.get_attribute('src')
        except Exception as e:
            logger.error(f"Error while getting image url {title}!{e}")

        ## img to base64
        try:
            response = requests.get(img_url,timeout=10)
            image_content = response.content
            base64_string = base64.b64encode(image_content)
            base64_string = base64_string.decode('utf-8')
            base64_image_url = f'data:image/png;base64,{base64_string}'
        except Exception as e:
            logger.exception(f"cannot convert url to base64 for {title}!Exception: {e}")
            img_url = None
            base64_image_url = None

        ## get official website
        try:
            website = driver.find_element(By.CSS_SELECTOR,'a[data-item-id="authority"]').get_attribute('href')
        except Exception as e:
            logger.exception(f"cannot find website of {title} !Exception: {e}")
            website = None

        ## get address
        try:
            address = driver.find_element(By.CSS_SELECTOR,'button[data-item-id="address"]').get_attribute('aria-label')
            address = re.sub(r'(地址: \d+)','',address)
        except Exception as e:
            logger.exception(f"cannot find address of {title} !Exception: {e}")
            address = None

        ## go to reviews
        try:
            main_buttons = wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "Gpq6kf")))
        except Exception as e:
            logger.error(f"{title} reviews not done yet!Error: {e}")

        actionChains.move_to_element(main_buttons[1]).perform()
        main_buttons[1].click()

        ## get stats rating
        try:
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
        except Exception:
            logger.error(f"Error {title}: no rating info for {title}")
            overall_rating = None
        
        start_time = time.time()
        while True:
            break_condition = False
            while not break_condition:
                try:
                    end_of_reviews = driver.find_elements(By.CLASS_NAME, 'qjESne')
                except Exception:
                    end_of_reviews = driver.find_elements(By.CLASS_NAME, 'qCHGyb')
                    break_condition = True
                
                click_more_buttons(driver)
                try:
                    actionChains.scroll_to_element(end_of_reviews[-1]).perform()
                except (IndexError, TimeoutException):
                    logger.info(f"{title} has no more reviews1!")
                    break_condition = True
                    continue
                except Exception as e:
                    logger.exception(f"Something wired scrolling reviews: {title} {e}")
                    break_condition = True
                    continue

                try:
                    results = wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "jftiEf")))
                except Exception as e:
                    logger.info(f"{title} has no more reviews2!")
                    break_condition = True

                temp = results[-1]
                wait_for_element_location_to_be_stable(temp)

                if len(results) > 100:
                    break_condition = True

                if time.time() - start_time > 35:
                    break_condition = True
                    logger.info(f"collecting {title} reviews timeout!")
            break

        reviews = []
        for i, result in enumerate(results, start=0):
            comment_span = find_attribute_or_text(result, By.CLASS_NAME, 'wiI7pd')
            user_url = find_attribute_or_text(result, By.CLASS_NAME, "al6Kxe", "data-href")
            user_rating = find_attribute_or_text(result, By.CLASS_NAME, "kvMYJc", "aria-label")
            if user_rating:
                user_rating = user_rating.split()[0]
                user_name = find_attribute_or_text(result, By.CLASS_NAME, "d4r55")
            user_id = re.search(r'(?<=contrib/)\d+', user_url).group(0)
            reviews.append({"user_id":user_id,"user_url":user_url,"user_name":user_name,
                            "rating":user_rating,"comment":comment_span})

    except Exception as e:
        raise Exception(f"Cannot action on: {title}!{e}")
    finally:
        driver.quit()

    crawling_result = {
        "name":title,
        "maps_url":new_url,
        "img_url":img_url,
        "img_base64":base64_image_url,
        "open_time":open_time,
        "website":website,
        "overall_rating":overall_rating,
        "address":address,
        "latitude":latitude,
        "longitude":longitude,
        "reviews":reviews
    }

    return crawling_result

def upload_to_s3(data, bucket_name, s3_path):
    s3 = boto3.client('s3')
    try:
        json_data = json.dumps(data, ensure_ascii=False)
        s3.put_object(Body=json_data,
                      Bucket=bucket_name, Key=s3_path)
    except Exception as e:
        raise Exception(f"Error uploading file to S3: {e}")

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

def click_more_buttons(driver):
    more_buttons = 0
    body_elements = driver.find_elements(By.CLASS_NAME, 'jftiEf')# Find buttons within the current 'jftiEf' element
    for body in body_elements: 
        buttons = body.find_elements(By.CLASS_NAME, "w8nwRe")# Iterate over each button within the current 'jftiEf' element
        for button in buttons:
            if button.text == "全文":# Check if the button text is "More"
                more_buttons += 1
                button.click()
            # print(more_buttons)#this will tell us how many more buttons are currently loaded

def find_attribute_or_text(driver, by_method, selector, attribute=None):
    try:
        element = driver.find_element(by_method, selector)
        if attribute:
            return element.get_attribute(attribute)
        else:
            return element.text
    except NoSuchElementException:
        return None

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
from operator import itemgetter
import logging
import boto3
import time
import re

logging.basicConfig(level=logging.INFO,filename='log.txt',filemode='a',
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

## check S3 connection
# s3_client = boto3.client('s3')

## read the ramen list
# restaurant_name = []
# with open("test_ramen_list.txt",'r') as input:
#     for line in input:
#         restaurant_name.append(re.sub(r'\((\d+|\w)*(開幕|預定|試賣|未定|試營運|預計)*\)|\((\w|\d+)*停\w*業*\)',
#                                 '', line.strip()))

## start browser
website = 'https://www.google.com.tw/maps'
options = Options()
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')  
driver = webdriver.Edge(options=options)
# driver.get(website)
# actionChains = ActionChains(driver)

# for ramen in restaurant_name:
for ramen in ['拉麵公子']:
    ## start browser
    driver.get(website)
    actionChains = ActionChains(driver)
    ###### go to the ramen restaurant
    actionChains.send_keys(ramen)  # Send keys to the element
    actionChains.send_keys(Keys.ENTER)  # Press Enter key
    actionChains.perform()  # Perform the actions
    wait = WebDriverWait(driver, 5)
    ## go to opening time
    try:
        opening_buttons = wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "RcCsl")))
        opening_buttons[1].click()
        time_all = wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "y0skZc")))

        open_time = {}
        for time_detail in time_all:
            day = time_detail.find_element(By.CLASS_NAME,'ylH6lf').text
            duration = [item.text for item in time_detail.find_elements(By.CLASS_NAME,'G8aQO')]
            open_time[day] = duration
    except Exception as e:
        logging.exception(f"cannot get opening time of {ramen}!Exception: {e}")
    ## get back
    back_button = driver.find_element(By.CSS_SELECTOR,'button[aria-label="返回"]')
    back_button.click()
    time.sleep(3)

    ## go to reviews
    try:
        main_buttons = wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "Gpq6kf")))
    except Exception as e:
        logging.error(f"{ramen} not done yet!Error: {e}")
        continue

    actionChains.move_to_element(main_buttons[1]).perform()
    # print(main_buttons[1].text)
    main_buttons[1].click()

    break_condition = True

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

        if len(results) > 10:
            break_condition = True

    get_url = driver.current_url
    print("The current url is:"+str(get_url))
    print(open_time)
    # for i, result in enumerate(results, start=0):
    #     comment_span = result.find_element(By.CLASS_NAME, 'wiI7pd')
    #     user_url = result.find_element(By.CLASS_NAME, "al6Kxe").get_attribute("data-href")
    #     user_rating = result.find_element(By.CLASS_NAME, "kvMYJc").get_attribute("aria-label")
    #     print(f"Result {i}: ['{user_url}','{user_rating}','{comment_span.text}']") # user name & rating not yet


driver.quit()


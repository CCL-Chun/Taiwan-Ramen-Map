from dotenv import load_dotenv
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver import ActionChains, Keys
from selenium.webdriver.common.by import By
import requests
import json
import time
import os

# load ramen maps
load_dotenv()
url = os.getenv('ramen_map_list_url')

# open browser
options = Options()
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')  
driver = webdriver.Edge(options=options)
driver.get(url)

actionChains = ActionChains(driver)
wait = WebDriverWait(driver, timeout=5)

# open list
show_more_list = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'span[class="HzV7m-pbTTYe-bN97Pc-ti6hGc-z5C9Gb"]')))
for show_more in show_more_list:
    show_more.click()
# get all ramen elements
ramen_all = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'div[class="pbTTYe-ibnC6b-Bz112c"]')))
wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'div[class="pbTTYe-ibnC6b-Bz112c"]')))
# ramen_all[3].click() 

# loop through all ramen
tags = []

for ramen_icon in ramen_all:
    data = {}
    ramen_icon.click()# go into details page

    # get detailed info
    featurecard_panel = wait.until(EC.presence_of_element_located((By.ID, 'featurecardPanel')))
    time.sleep(0.5)
    details = featurecard_panel.find_elements(By.CLASS_NAME, 'qqvbed-p83tee')
    for detail in details:
        # The first child div contains the header/title
        header = detail.find_element(By.CLASS_NAME, 'qqvbed-p83tee-V1ur5d').text
        # The second child div contains the description
        description = detail.find_element(By.CLASS_NAME, 'qqvbed-p83tee-lTBxed').text
        # Add to dictionary
        data[header] = description
    # save to list
    tags.append(data)
    # go back
    return_button = featurecard_panel.find_element(By.CLASS_NAME, 'Ce1Y1c')
    return_button.click()

print(tags)

with open('./ramen_tags.json','w',encoding='utf-8') as file:
    json.dump(tags,file,ensure_ascii=False,indent=4)

time.sleep(1)
driver.quit()

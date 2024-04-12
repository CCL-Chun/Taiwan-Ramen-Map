import os
import time
import requests
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


# load ramen maps
load_dotenv()
url = os.getenv('ramen_map_list_url')

# open browser
options = Options()
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')  
driver = webdriver.Edge(options=options)
driver.get(url)
# wait = WebDriverWait(driver, 20)
# wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "suEOdc")))
time.sleep(5)

# Parse the HTML content using BeautifulSoup
soup = BeautifulSoup(driver.page_source, 'lxml')

# Find the div with class 'suEOdc' and extract text
div_content = soup.find_all('div', class_='suEOdc')
if div_content:
    for div in div_content:
        print(div.text)  # This prints the text of each div on a new line
else:
    print("The specified div was not found.")

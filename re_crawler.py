from selenium import webdriver
from selenium.webdriver import ActionChains, Keys
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from datetime import datetime
import logging
import requests
import base64
import json
import pytz
import time
import re
import os

## write to log
logging.basicConfig(level=logging.INFO,filename='log_redo.txt',filemode='a',
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
restaurant_name = ['道樂製麵所-豚骨專賣店', '森一男豚骨拉麵', '小野家', '橫山家拉麵 - 七賢店', '賀也拉麵', '拉麵彼得', '姥夥房-新竹水田店', '隣tonari', '塩琉-3號店', '鬍子大叔の蝦湯拉麵 ', 'RAMEN天神 - ', '豚人拉麵 - 真龍店', '四娘拉麵', '熊麵製造所', '究Sho石燒拉麵-育德店', '麵屋好', '千代姬拉麵', '海拉麵', '橫濱家系大和家 - 忠孝SOGO店', '一階堂拉麵 - 中壢新光店', '樂蝦拉麵家 - 宏匯廣場店', '北海道えびそば一幻-高雄店', '拉麵家-長安店', '鷹流台灣總本店', '麵屋萬居', '麵屋心 拉麵沾麵專賣店', '天雞', '松田麵屋 沾麵專門店', '洛屋 - 牛骨拉麵、鴨清湯拉麵', '雞白郎. 拉麵', '森麵堂 - 中山店', '☆辣麻味噌沾麵 鬼金棒', '☆辣麻味噌拉麵 鬼金棒', '塩琉', '柑橘Shinn', '麵屋壹の穴 ICHI', '一番星拉麵', '麵屋壹の穴ichi-沾麵專門店', '博多幸龍総本店', '吉鴙ラーメン（吉鴙拉麵）', '麵屋雞金', '橫濱家系ラーメン大和家-復興店', '橫濱家系ラーメン大和家-中山店', '麵屋一虎 ICHI TORA', '金澤冠軍拉麵咖喱', '11番町豚骨拉麵-桃園銘傳店', '麵家三士-桃園華泰店(桃園／中壢)', '東京板前豚骨拉麵-板橋店', '日本富士八峰拉麵-淡水北新店', '月見拉麵', '熱烈一番亭', 'RAMEN IROHA 富山黑拉麵', '綜也蔬食 Vegan Ramen Shop', '博多担々麺梟 台灣總本店', 'KIYO拉麵 博多ラーメン', '麵屋川去 MENYA Kawasari', '麵試十一次', '餃 麵', '裸湯拉麵', '力量拉麵-台北安和店', '毘沙門天らーめん工房| 北海道拉麵', '浪漫軒擔擔麵-本店', '豚總長 二郎風乾拌拉麵', '橫濱家系ラーメン大和家-南港店', '鳳華雞豚濃湯拉麵專門店-二號店', '裸湯拉麵 · 雞白湯-永春店', 'KASUI禾穗麵屋', '裸湯拉麵 · 雞白湯-和平店', '虎記餃子(北市／中正)', '麵屋牛心', '札幌炎神拉麵-永春店', '麵屋鳥美庵 (9/26開幕)', '森麵堂', "Hiro's らぁ麵 Kitchen-竹北店", "Hiro's らぁ麵 Kitchen-新北新店店", '豚戈屋台 拉麵&拌麵專門店', '我孫子Abiko', '勝山家拉麵', '谷太 · Goodtime', '匠月雞白湯拉麵', 'ラーメン 鷄白湯', '玩味・雞湯事務所', '麵屋おく村', '千嵐拉麵-貳號殿', '森拉麵', '七匹の子ぶた', 'Mr. 和 創作日本拉麺', '豚嶼拉麵', 'らぁ麺魚堺', '豚骨一笑', '麵吉祥', '横浜家系ラーメン拉麵家-台中店', '升龍拉麵', '札幌炎神拉麵 台中麗寶店', '強棒亭', '千璽公子 鶏パイタン專門', 'Hiro’s らぁ麵Kitchen-台中三井店', '', '靑拉麵', '麵屋青鳥', '麵屋木心 ラーメン専門店', '一拉面', '誠拉麵まこと', '双赫日式拉麵-善化店', '麵屋高', '麵屋柴 雞白湯拉麵專賣店', '有麥點手作料理-裕農店', '東京板前豚骨拉麵-台南店', '臥龍拉麵-林森店', '双赫日式拉麵-台南店', '京都柚子豚骨拉麵研究中心-台南高鐵店', '將屋拉麵', '大宮町ラーメン拉麵', '究-Sho石燒拉麵《文化参店》(台南／東區)', '橫濱九田家系拉麵專賣店', '極道製麵所', '俺貳豚骨醬油', '倉麵屋ラーメン', '水行者海洋運動中心附設拉麵部', '隱家拉麵-公館店(北市／中正)', '道樂ラーメン專門店(北市／士林)', '山嵐拉麵-台灣總店(北市／大安)', '山嵐拉麵-安通溫泉店(花蓮／富里)', 'ラーメン凪 Ramen Nagi-天母店(北市／士林)', 'ラーメン凪 Ramen Nagi-台中店(台中／西屯)', '鷹流東京醤油拉麺【蘭丸ranmaru】台北中山店', '鷹流東京醤油拉麺【蘭丸ranmaru】新竹勝利店', '鷹流東京醤油拉麺【蘭丸ranmaru】新竹竹北店', '長生塩人-北投店(北市／北投)', '長生塩人-淡水店(新北／淡水)', '長生塩人-台中店(台中／西屯)', '長生塩人-台東店(台東／台東)', '屯京拉麵-信義A8店(北市／信義)', '屯京拉麵-三井lalapoart店(台中／東區)', '屯京拉麵-台南南紡店(台南／東區)', '屯京拉麵-高雄夢時代店(高雄／前鎮)', '太陽蕃茄拉麵-站前本店(北市／中正)', '太陽蕃茄拉麵-美麗華百樂園店(北市／中山)', '太陽蕃茄拉麺-林口三井店(新北／林口)', '太陽蕃茄拉麵-三井lalapoart店(台中／東區)', '太陽蕃茄拉麵-漢神本館店(高雄／前金)', '花月嵐-信義威秀店(北市／信義)', '花月嵐-松山車站店(北市／松山)', '花月嵐-台北凱撒店(北市／中正)', '花月嵐-統一時代店(北市／信義)', '花月嵐-北投石牌店(北市／北投)', '花月嵐-桂林家樂福店(北市／萬華)', '花月嵐-重新家樂福店(新北／三重)', '花月嵐-新店家樂福店(新北／新店)', '花月嵐-樹林秀泰店(新北／樹林)', '花月嵐-中壢SOGO店(桃園／中壢)', '花月嵐-桃園台茂店(桃園／蘆竹)', '花月嵐-台中中友店(台中／北區)', '花月嵐-台中清水店(台中／清水)', '花月嵐-文心家樂福店(台中／南屯)', '花月嵐-新光中山店(台南／中西)', '花月嵐-新光左營店(高雄／左營)', '一風堂-中山本店(北市／中山)', '一風堂-新莊宏匯店(新北／新莊)', '一風堂-桃園高鐵店(桃園／中壢)', '一風堂EXPRESS-新竹巨城店(新竹／東區)', '一風堂-遠百竹北店(新竹／竹北)', '一風堂-台中三越中港店(台中／西屯)', '一風堂-台中秀泰文心店(台中／西屯)', '一風堂-台南西門店(台南／中西)', '一風堂-台南南紡店(台南／東區)', '一風堂-漢神巨蛋店(高雄／左營)', '樂麵屋-永康店(北市／大安)', '樂麵屋-永康公園店(北市／大安)', '樂麵屋-西門店(北市／萬華)', '樂麵屋-南港店(北市／南港)', '樂麵屋-板橋店(新北／板橋)', '小高拉麵-板橋民權店(新北／板橋)', '小高拉麵-中和南勢角(新北／中和)', '滝禾製麵所-苗栗大埔店(苗栗／苗栗)', '滝禾製麵所-太平創始店(台中／太平)', '滝禾製麵所-金門金城店(金門／金城)', '九湯屋-創始店(新竹／北區)', '奧特拉麵 Ramen Ultra-南港車站店(新北／板橋)', '奧特拉麵 Ramen Ultra-桃園華泰店(桃園／中壢)', '奧特拉麵 Ramen Ultra-大葉高島屋(北市／士林)', 'Mr.拉麺-台北店(北市／中正)', 'Mr.拉麵-台南文成店(台南／北區)', 'Mr.拉麵-楠梓家樂福店(高雄／楠梓)', '雲拉麵(雲林／斗六)', '九州豚將日本拉麵-總公司(高雄／鳳山)', '幸花拉麵雞白湯專門店-全國總本店(台中／北屯)', '月見町拉麵 - 大葉店(彰化／大樹)', '虎記餃子-敦北店(北市／松山)', '淺草咖哩蛋包(苗栗／苗栗)', '信洲食之屋(南投／草屯)', '榆。拉麵ラーメン(北市／中山)', '玄拉麵北大店(新北／三峽)', '苹果拉麵、丼飯(新北／永和)', '衛門府-蘆洲店(新北／蘆洲)', '温泉拉麵.瀑布美食(新北／烏來)', '富士達人日本拉麵-東安店(台南／東區)', '樂山娘-中山店(北市／中山)', '樂山娘-林森店(北市／中山)', '樂山娘-台中店(台中／西區)', '樂山娘-前金店(高雄／前金)', '屋台拉麵-高雄燕巢店(高雄／燕巢)', '樂山溫泉拉麵(宜蘭／礁溪)', '樂山拉麵-宜蘭店(宜蘭／宜蘭)']

## browser setting
google_maps = 'https://www.google.com.tw/maps'
options = Options()
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')  
driver = webdriver.Edge(options=options)

## loop throught list
last_successful_index = 0
last_title = 'a'
title = 'a'

# open the browser and handle the status
driver.get(google_maps)
origin_window = driver.current_window_handle

for i in range(last_successful_index, len(restaurant_name)):
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

        ## multiple searching results
        multiple = driver.find_elements(By.CLASS_NAME, 'Nv2PK')
        if multiple:
            print(f"Error:\t{ramen}")
            with open("redo_please2.txt","a") as redo:
                redo.write(f"{ramen}\n")

            continue # end this time

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
            open_time = None
        
        ## get back page if need
        try:
            back_button = driver.find_element(By.CSS_SELECTOR,'button[aria-label="返回"]')
            back_button.click()
        except Exception:
            logging.info(f"no need to get back from opening time page: {ramen}!")

        ## get img url
        try:
            img_button = wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "ZKCDEc")))
            time.sleep(1)
            image_element = img_button[0].find_element(By.TAG_NAME, 'img')
            img_url = image_element.get_attribute('src')
        except Exception as e:
            logging.error(f"Error while getting image url {ramen}!{e}")

        ## img to base64
        try:
            response = requests.get(img_url,timeout=10)
            image_content = response.content
            base64_string = base64.b64encode(image_content)
            base64_string = base64_string.decode('utf-8')
            base64_image_url = f'data:image/png;base64,{base64_string}'
        except Exception as e:
            logging.exception(f"cannot convert url to base64 for {ramen}!Exception: {e}")
            img_url = None
            base64_image_url = None

        ## get official website
        try:
            website = driver.find_element(By.CSS_SELECTOR,'a[data-item-id="authority"]').get_attribute('href')
        except Exception as e:
            logging.exception(f"cannot find website of {ramen} !Exception: {e}")
            website = None

        ## get address
        try:
            address = driver.find_element(By.CSS_SELECTOR,'button[data-item-id="address"]').get_attribute('aria-label')
            address = re.sub(r'(地址: \d+)','',address)
        except Exception as e:
            logging.exception(f"cannot find address of {ramen} !Exception: {e}")
            address = None

        ## go to reviews
        try:
            main_buttons = wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "Gpq6kf")))
        except Exception as e:
            logging.error(f"{ramen} reviews not done yet!Error: {e}")
            last_title = title

            print(f"Error:\t{ramen}")
            with open("redo_please2.txt","a") as redo:
                redo.write(f"{ramen}\n")

            continue

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
            logging.error(f"Error {ramen}: no rating info for {title}")
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
                
                click_more_buttons()
                try:
                    actionChains.scroll_to_element(end_of_reviews[-1]).perform()
                except (IndexError, TimeoutException):
                    logging.info(f"{ramen} has no more reviews1!")
                    break_condition = True
                    continue
                except Exception as e:
                    logging.exception(f"Something wired scrolling reviews: {ramen} {e}")
                    break_condition = True
                    continue

                try:
                    results = wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "jftiEf")))
                except Exception as e:
                    logging.info(f"{ramen} has no more reviews2!")
                    break_condition = True

                temp = results[-1]
                wait_for_element_location_to_be_stable(temp)

                if len(results) > 100:
                    break_condition = True

                if time.time() - start_time > 30:
                    break_condition = True
                    logging.info(f"collecting {ramen} reviews timeout!")
            break


        ## get coordination
        try:
            get_url = driver.current_url
            url = re.sub(r'@([-\d.]+),([-\d.]+),(\d+).*(\d+)\w/','',get_url)
            new_url = re.sub(r'place/.*/data','place/data',url)
            # print(url)
            coord = re.search(r'([-\d.]+)(!4d)([-\d.]+)',get_url)
            latitude = coord.group(1)
            longitude = coord.group(3)
        except Exception as e:
            logging.info(f"{ramen} wrong with url")


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

        print(f"Success:\t{ramen}\t{title}")
        with open('./redo_list.json','a',encoding='utf-8') as file:
                json.dump(crawling_result,file,ensure_ascii=False,indent=4)
                file.write(",\n")
        # for next round check
        last_title = title
    # hadling session error like page crash
    except Exception as e:
        logging.exception(f"Exception for {ramen}: {e}")
        time.sleep(2)
        print(f"Error:\t{ramen}")
        with open("redo_please2.txt","a") as redo:
            redo.write(f"{ramen}\n")

        # try:
        #     driver.quit()
        # except:
        #     logging.info("Browser had been closed!")
        driver.quit()
        driver = webdriver.Edge(options=options) # resatrt
        driver.get(google_maps)
        continue

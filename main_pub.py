import logging
import re
import time
import cv2
import numpy as np
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
import threading
from flask import Flask, request, jsonify

# region INIT

driver = None
false = False
true = True
URL = "http://127.0.0.1:1345/v0.1/"

cookies = []

for cookie in cookies:
    cookie["sameSite"] = "None"
pattern_pos = re.compile(r"\d+,\d+")
app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)
app_init = 0
ELEMENT = None
ACTIONS = None

# endregion

# region MAIN

def flask_app():
    app.run(debug=True, port=1347, threaded=True, use_reloader=False)



def init():
    global driver
    print("INITIALIZING")
    # 设置浏览器驱动和选项
    options = Options()
    options.headless = True  # 无界面模式
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36")
    options.add_argument(
        "Accept=text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7")
    options.add_argument("Accept-Encoding=gzip, deflate, br, zstd")
    options.add_argument("Accept-Language=zh-CN,zh;q=0.9,en;q=0.8")
    options.add_argument("Sec-Fetch-Dest=document")
    options.add_argument("Sec-Fetch-User=?1")
    options.add_argument("Sec-Fetch-Mode=navigate")
    options.add_argument("Sec-Fetch-Site=none")
    options.add_argument("Upgrade-Insecure-Requests=1")
    options.add_argument('sec-ch-ua-platform="Windows"')
    options.add_argument("sec-ch-ua-mobile=?0")
    options.add_argument('sec-ch-ua="Not A(Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"')
    driver = webdriver.Chrome(options=options)
    driver.get('https://pc-play.games.dmm.co.jp/')

    for cookie in cookies:
        print(cookie)
        driver.add_cookie(cookie)

    driver.get('https://pc-play.games.dmm.co.jp/play/imys_r/')
    return driver


def main():
    global driver
    print("MAIN")
    driver = init()
    print("Cookies are set and page is refreshed.")

    print("Action made")
    while True:
        time.sleep(10)
        # Making a GET request to the Burp Suite API
        response = requests.get(URL)

        # Print the status code and response data
        print("Status Code:", response.status_code)
        pass


@app.before_request
def before_request():
    pass

# endregion

# region TASK

def find_image_in_screenshot(web, locale):
    print(f"Find {locale} in {web}")
    local_image = cv2.imread(locale)

    screenshot_gray = cv2.cvtColor(web, cv2.COLOR_BGR2GRAY)
    local_image_gray = cv2.cvtColor(local_image, cv2.COLOR_BGR2GRAY)

    result = cv2.matchTemplate(screenshot_gray, local_image_gray, cv2.TM_CCOEFF_NORMED)

    threshold = 0.8
    locations = np.where(result >= threshold)

    matches = []
    for pt in zip(*locations[::-1]):
        matches.append((pt[0], pt[1], pt[0] + local_image.shape[1], pt[1] + local_image.shape[0]))
    print(f"get matches {matches}")
    return matches

@app.route('/click', methods=['POST'])
def click_place():
    global app_init
    global ELEMENT
    global ACTIONS
    if app_init == 0:
        print(f"initing{app_init}")
        app_init = 1
        # 假设这里是获取 ELEMENT 的逻辑
        driver.switch_to.frame("game_frame")
        driver.switch_to.frame("iframe")
        element_group = driver.find_elements(By.XPATH, "/html/body/div/div[1]")
        ELEMENT = element_group[0]
        ACTIONS = ActionChains(driver)
        print(f"ELEMENT {ELEMENT}")
    try:
        # g.ACTIONS.move_to_element(g.ELEMENT).click().perform()
        data = request.get_json()
        print(f"Received data: {data}")
        x, y = data['x'], data['y']
        ACTIONS.move_to_element_with_offset(ELEMENT, x - 640, y - 360).click().perform()
        print(f"Clicked:{x},{y}")
        print()
        return jsonify({"status": "Click processed"}), 200
    except Exception as e:
        print(f"ERROR :{e}")
        app_init = 0
        click_place()


@app.route('/screenshot', methods=['POST'])
def get_screenshot():
    is_match = ""
    # element = driver.find_element(by="xpath", value='//*[@id="unity-canvas"]')
    # start_x = element.location['x']
    # start_y = element.location['y']
    data = request.get_json()
    for path in data:
        screenshot = driver.get_screenshot_as_png()
        with open(f"./1.png", "wb") as f:
            f.write(screenshot)
            print("SAVED")
        nparr = np.frombuffer(screenshot, np.uint8)
        screenshot = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        matches = find_image_in_screenshot(screenshot, path)
        url = "http://127.0.0.1:1346/screenshot"
        headers = {'Content-Type': 'application/json'}
        if matches:
            response = requests.post(url, json=path, headers=headers)
            print(f"respond {path}")
            return jsonify({"status": "Match"}), 200
        else:
            response = requests.post(url, json="None", headers=headers)
            print(f"respond None")
            return jsonify({"status": "Not match"}), 200
    return jsonify({"status": "Not match"}), 200

# endregion

if __name__ == '__main__':
    server_thread = threading.Thread(target=flask_app)
    main_thread = threading.Thread(target=main)

    server_thread.start()
    main_thread.start()


    server_thread.join()
    main_thread.join()

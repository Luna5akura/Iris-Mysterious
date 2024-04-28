import datetime
import re
import sys
import time

import logging
from logging.handlers import RotatingFileHandler
import atexit

from threading import Thread
from threading import Timer
from threading import Lock

import requests
from flask import Flask, request, jsonify

# region INIT
app = Flask(__name__)

inactivity_timer = None
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
atexit.register(logging.shutdown)
logger = logging.getLogger("MyLogger")
logger.setLevel(logging.DEBUG)
handler = RotatingFileHandler(
    'my_app.log', maxBytes=1024 * 1024 * 5, backupCount=5)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

pattern_request = re.compile(r'^(GET|POST)\s*\S*\s*HTTP/\d')
pattern_response = re.compile(r"HTTP/(2|\d.\d) 200")
lock = Lock()
current_status = None
running = False
changed = False
responses = []
un_responded = {}
# endregion

# region MAP
STATUS = {
    "ini": re.compile(r"/v1/events"),
    "init": re.compile(r"/game_type"),
    "home": re.compile(r"/mypage"),
    "quest": re.compile(r"/quest"),
    "battle_start": re.compile(r"/battle/start"),
    "battle_finish": re.compile(r"/battle/finish"),
    "dialog": re.compile(r"/scenarios"),
}
click_map = {
    "ini": (650, 575),
    "enter": (690, 640),
    "back": (66, 44),
    "next": (1145, 680),
    "close": (680, 635),
    "home": (66, 666),
    "home_to_quest": (1070, 390),
    "quest_to_ingredients": (890, 345),
    "quest_to_sidestory": (450, 340),
    "quest_start": (985, 660),
    "ingredients_gem": (244, 122),
    "ingredients_gem_upgrade_easy": (85, 240),
    "battle_skip": (1090, 660),
    "ingredients_gem_upgrade_skip": (160, 210),
    "battle_skip_go": (770, 660),
    "battle_skip_down": (635, 400),
    "sidestory_flarelight": (845, 90),
    "sidestory_first": (180, 235),
    "level_dialog_skip": (865, 585),

}
screenshot_map = {
    "quest_collect": "./lib/quest_collect.png",
    "quest_main": "./lib/quest_main.png",
    "quest_sidestory": "./lib/quest_sidestory.png",
    "quest_sidestory_flarelight_able": "./lib/flarelight_able.png",
    "quest_sidestory_flarelight_disable": "./lib/flarelight_disable.png",
    "quest_new_level": "./lib/quest_new_level.png",
    "quest_unvisit_level": "./lib/quest_unvisit_level.png",
    "level_dialog_unskip": "./lib/level_dialog_unskip.png",
    "close": "./lib/close.png",
    "next": "./lib/next.png",
}


# endregion

# region MAIN

@app.route('/')
def home():
    return "Welcome to the Flask app!"


@app.route('/receive', methods=['POST'])
def receive_data():
    reset_inactivity_timer()
    global changed
    global un_responded
    if request.method == 'POST':
        payload = request.get_json()
        data = payload['data']
        messageID = payload['messageID']
        match = pattern_response.search(data[:200])
        if match:
            with lock:
                print("CHANGED TO TRUE")
                changed = True
                success = un_responded.pop(messageID)
                thread = Thread(target=analysis_response, args=(success['request'],))
                thread.start()
                # print(f"\n{messageID} Response:", match.group(0)[:50])
                return jsonify({"status": "Data received successfully"}), 200
        match = pattern_request.search(data[:200])
        if match:
            with lock:
                print("CHANGED TO TRUE")
                changed = True
                un_responded[messageID] = {'request': match.group(0), 'timestamp': datetime.datetime.now()}
                # print(f"\n{messageID} Request:", match.group(0)[:50])
                to_delete = []
                for key, value in un_responded.items():
                    current_time = datetime.datetime.now()
                    if (current_time - value['timestamp']).total_seconds() > 5:
                        to_delete.append(key)
                for key in to_delete:
                    del un_responded[key]
                # print("NOW DICT:", un_responded.keys())
            return jsonify({"status": "Data received successfully"}), 200

        # print(data[:50])
        return jsonify({"status": "Data received successfully"}), 200


@app.route('/send_data', methods=['POST'])
def send_data():
    data = request.json
    print("Received：", data)
    response = {"message": "Received"}
    return jsonify(response)


def analysis_response(success):
    print(f"Analysing response {success}")
    global current_status
    global running
    if success:
        for name, pattern in STATUS.items():
            # print(f"Matching {pattern} with {success}")
            if pattern.search(success):
                if not running:
                    print("SCRIPT BEGINS RUNNING!!!!!")
                    running = True
                else:
                    print("ALREADY IN RUNNING!!!!")
                print(f"{success} __matches__ {pattern},Set current state {name},Begin {current_script}")
                current_status = name
                loaded(current_script)
                return current_status
    pass


def handle_exception(exc_type, exc_value, exc_traceback):
    logging.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))


sys.excepthook = handle_exception



def reset_inactivity_timer():
    global inactivity_timer
    if inactivity_timer:
        inactivity_timer.cancel()
    inactivity_timer = Timer(5.0, timeout_function)
    inactivity_timer.start()

def timeout_function():
    print("No activity for 5 seconds, executing get_screenshot_match.")
    pathlist = screenshot_map.values()
    get_screenshot_match(pathlist, called="timeout_check")

# endregion

# region BASE


def log_function_call(func):
    def wrapper(*args, **kwargs):
        args_repr = [repr(a) for a in args]
        kwargs_repr = [f"{k}={v!r}" for k, v in kwargs.items()]
        signature = ", ".join(args_repr + kwargs_repr)
        logging.debug(f"Calling {func.__name__}({signature})")
        result = func(*args, **kwargs)
        logging.debug(f"{func.__name__} returned {result!r}")
        return result

    return wrapper


@log_function_call
def wait():
    pass


@log_function_call
def loaded(func, *args, **kwargs):
    # print("Waiting for loaded")
    global changed
    current_time = datetime.datetime.now()
    keys_to_delete = []
    for key, value in un_responded.items():
        if (current_time - value['timestamp']).total_seconds() > 5:
            keys_to_delete.append(key)

    for key in keys_to_delete:
        del un_responded[key]

    # print(f"CHANGED SITUATION:{changed}")
    if not un_responded and changed == False:
        try:
            if args:
                # print(f"executing:({func}(*{args})")
                func(*args)
            else:
                # print(f"executing:({func}()")
                func()
        except Exception as e:
            print(f"ERROR {e}")
            exit(10)
    else:
        changed = False
        print(f"Trying to execute {func},Still loading:{un_responded}")
        time.sleep(1)
        loaded(func, *args, **kwargs)


@log_function_call
def sended(func, *args, max_retries=5, bad=None, bad_args=None, bad_kwargs=None, **kwargs):
    global changed
    initial_responses = responses.copy()
    retry_count = 0

    while retry_count < max_retries:
        print(f"Current script {current_script}")
        func(*args, **kwargs)
        # print(f"CHANGED SITUATION:{changed}")
        if initial_responses == responses and changed == False:
            time.sleep(1)
            retry_count += 1
            print(f"Attempt {retry_count}: No change in un_responded, retrying...")
        else:
            changed = False
            # print("Successfully executed")
            return

    print("Max retries reached without changes in un_responded.")
    if bad:
        print(f"Calling {bad}")
        if bad_args:
            bad(bad_args)
    return "No changes in un_responded after 5 attempts."


# endregion

# region CONNECTION

@log_function_call
def send_click(x, y, called=None):
    # print(f"Sending click: {x}, {y} for function {called}")
    url = "http://127.0.0.1:1347/click"
    pos = {"x": x, "y": y}
    headers = {'Content-Type': 'application/json'}
    try:
        response = requests.post(url, json=pos, headers=headers, timeout=5)
        print(f"Sended click: {x}, {y} for function {called}, {response}")
    except requests.Timeout:
        print(f"Timeout occurred when sending click: {x}, {y} for function {called}")


@log_function_call
def get_screenshot_match(pathlist, called=None):
    url = "http://127.0.0.1:1347/screenshot"
    headers = {'Content-Type': 'application/json'}
    try:
        response = requests.post(url, json=pathlist, headers=headers, timeout=5)
        print(f"Sended get screenshot match:{response},{pathlist},CALLED = {called}")
    except requests.Timeout:
        print(f"Timeout occurred when getting screenshot match: {pathlist},CALLED = {called}")


@app.route('/screenshot', methods=['POST'])
def receive_screenshot_path():
    data = request.json
    print(f"Receive screenshot path {data}")
    loaded(current_script, data)
    return jsonify({"status": "Receive screenshot"}), 200


# endregion

# region SCRIPTS

def initialize(script=None, path=None):
    print("INITIALIZING")
    global current_script
    if current_status == "ini":
        time.sleep(1)
        loaded(wait)
        sended(send_click, *click_map["ini"], called="ini", bad=initialize)
    if current_status == "init":
        is_initialized = True
        loaded(wait)
        sended(send_click, *click_map["enter"], called="enter", bad=initialize)


@log_function_call
def auto_sidestory(path=None):
    global running
    print("AUTO_SIDESTORY")
    global current_script
    global current_status
    if not path:
        if current_status == "ini" or current_status == "init":
            initialize()
            running = False
            return
        elif current_status == "home":
            loaded(wait)
            pathlist = [screenshot_map["close"]]
            sended(send_click, *click_map["home_to_quest"], called="home_to_quest", bad=get_screenshot_match,
                   bad_args=pathlist, bad_kwargs={"called": auto_sidestory})
            running = False
            return
        elif current_status == "quest":
            loaded(wait)
            loaded(send_click, *click_map["quest_to_sidestory"], called="quest_to_sidestory")
            loaded(wait)
            time.sleep(2)
            pathlist = [screenshot_map["quest_sidestory"]]
            loaded(get_screenshot_match, pathlist, called=auto_sidestory)
            return
        else:
            loaded(wait)
            sended(send_click, *click_map["home"], called="home")
            return
    else:
        # print("Received path")
        # print(f"Path is {path}")
        if path == r"./lib/quest_sidestory.png":
            pathlist = [screenshot_map["quest_sidestory_flarelight_able"],
                        screenshot_map["quest_sidestory_flarelight_disable"]]
            loaded(get_screenshot_match, pathlist, called=auto_sidestory)
            return
        elif path == r"./lib/flarelight_disable.png":
            # print("flarelight_disable")
            time.sleep(0.2)
            send_click(*click_map["sidestory_flarelight"], called="sidestory_flarelight")
            send_click(*click_map["sidestory_first"], called="sidestory_first")
            auto_event(called=auto_sidestory)
            return
        elif path == r"./lib/flarelight_able.png":
            # print("flarelight_able")
            send_click(*click_map["sidestory_first"], called="sidestory_first")
            auto_event(called=auto_sidestory)
            return
        elif path == r"./lib/close.png":
            # print("close")
            send_click(*click_map["close"], called="close")
            auto_sidestory()
            return
        else:
            if current_script == auto_sidestory:
                sended(send_click, *click_map["home"], called="home")
                return


@log_function_call
def auto_event(path=None, called=None):
    # print(f"Auto event,called = {called}, path = {path}")
    global current_script
    global current_status
    current_script = auto_event
    if not path:
        pathlist = [screenshot_map["close"], screenshot_map["next"], screenshot_map["level_dialog_unskip"],
                    screenshot_map["quest_new_level"], screenshot_map["quest_unvisit_level"]]
        loaded(wait)
        time.sleep(0.5)
        loaded(get_screenshot_match, pathlist, called=auto_event)
        return
    else:
        if path == r"./lib/quest_new_level.png" or r"./lib/quest_unvisit_level.png":
            sended(send_click, *click_map["quest_start"], called=auto_event)
            current_script = auto_level
            auto_level(called=auto_event)
            return
        elif path in [screenshot_map["close"], screenshot_map["next"], screenshot_map["level_dialog_unskip"]]:
            auto_level(path=path, called=auto_event)
            return


auto_event_called = ""


@log_function_call
def auto_level(path=None, called=None):
    global auto_event_called
    global running
    if called:
        auto_level_called = called
    # print("Begin auto level")
    global current_script
    global current_status
    current_script = auto_level
    if not path:
        print(f"Current status : {current_status}")
        if current_status == "quest" or current_status == "dialog":
            pathlist = [screenshot_map["level_dialog_unskip"], screenshot_map["quest_new_level"],
                        screenshot_map["quest_unvisit_level"]]
            loaded(wait)
            loaded(get_screenshot_match, pathlist, called=auto_level)
            # auto_level()
            return
        elif current_status == "battle_finish":
            pathlist = [screenshot_map["close"], screenshot_map["next"], screenshot_map["level_dialog_unskip"],
                        screenshot_map["quest_new_level"], screenshot_map["quest_unvisit_level"]]
            loaded(get_screenshot_match, pathlist, called=auto_level)
            return
        elif current_status == "battle_start":
            time.sleep(1)
            auto_level(called=auto_event_called)
            return
        else:
            auto_level(called=auto_event_called)
            return
    else:
        # print(f"Path is {path}")
        if path == r"./lib/level_dialog_unskip.png":
            send_click(*click_map["level_dialog_skip"], called=auto_level)
            running = False
            return
        elif path == r"./lib/close.png":
            send_click(*click_map["close"], called=auto_level)
            path = r"./lib/next.png"
            current_status = "quest"
            if auto_event_called:
                current_script = auto_event_called
            sended(send_click, *click_map["next"], called=auto_level)
            pathlist = [screenshot_map["close"], screenshot_map["next"], screenshot_map["level_dialog_unskip"],
                        screenshot_map["quest_new_level"], screenshot_map["quest_unvisit_level"]]
            loaded(get_screenshot_match, pathlist, called=auto_level)
            return
        elif path == r"./lib/next.png":
            current_status = "quest"
            if auto_event_called:
                current_script = auto_event_called
            sended(send_click, *click_map["next"], called=auto_level)
            pathlist = [screenshot_map["close"], screenshot_map["next"], screenshot_map["level_dialog_unskip"],
                        screenshot_map["quest_new_level"], screenshot_map["quest_unvisit_level"]]
            loaded(get_screenshot_match, pathlist, called=auto_level)
            return
        else:
            loaded(current_script)
            return


# endregion

if __name__ == '__main__':
    current_script = auto_sidestory
    app.run(debug=False, port=1346)

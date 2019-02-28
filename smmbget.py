from bs4 import BeautifulSoup
import urllib.request as urllib2
import re
import requests
import json

def ConvertSVG(svg2text):
	if svg2text == "percent":
		return("%")
	elif svg2text == "minute":
		return(":")
	elif svg2text == "second":
		return(".")
	elif svg2text == "slash":
		return("/")
	elif svg2text == "hyphen":
		return("-")
	else:
		return(svg2text)

def check_level_duplicate(level):
    levels = json.load(open('levels.json', 'r'))
    for x in levels['records']:
        if level == x['level_id']:
            return True
        
def get_level_info (levelid):
    #Beautiful Soup Setup. This gets the classes needed to strip for the information we need.
    url = f'https://supermariomakerbookmark.nintendo.net/courses/{levelid}'
    page = urllib2.urlopen(url)
    soup = BeautifulSoup(page, 'html.parser')
    name_box = soup.find('div', attrs={'class': 'course-title'})
    clearrate_box = soup.find("div", {"class" : "clear-rate"})
    difficulty_box = soup.find('div', class_='course-header')
    img_box = soup.find('div', attrs={'class': 'course-image'})
    img_long_box = soup.find('div', attrs={'class': 'course-image-full-wrapper'})
    name = name_box.text.strip()
    difficulty = difficulty_box.text.strip()
    img = img_box.find("img")['src']
    img_long = img_long_box.find("img")['src']

    #this will call the ConvertSVG to format the typograohy classes to numbers and store it in a string called ClearRate     
    
    ClearRate = ""
    for i in clearrate_box.findAll("div",{"class" : re.compile("typography.*")}):
        #print(i) #this is for testing and debugging to see how if it is regurning the correct classes
        ClearRate += ConvertSVG(re.match(".*typography.*typography-(\w+).*",str(i.attrs)).group(1))

    level_queue = {
        "level_id": levelid,
        "coursename": name,
        "img_url": img,
        "level_img_long": img_long,
        "clear_rate": ClearRate,
        "difficulty": difficulty
        }
    return level_queue

def check_valid_level(level_id):
    url = f'https://supermariomakerbookmark.nintendo.net/courses/{level_id}'
    check = requests.get(f'{url}')
    if int(check.status_code) == 200:
        return True
    else:
        return False

def write_level_info(level_info,user,platform):
    levels = json.load(open('levels.json', 'r'))
    level_info['name'] = user
    level_info["platform"] = platform
    levels["queue"].append(level_info)
    levels["records"].append(level_info)
    with open('levels.json', 'w') as f:
        json.dump(levels, f, indent=2)




'''level = "978A-0000-03A7-A65A" 
#Testing and Debugging
check = check_valid_level(level)
if check == True:
    print("Yes Its good")
    test = get_level_info(level)
    print(test)
    write_level_info(test, "Randall", "Twitch")

else:
    print("No it wasn't good")'''
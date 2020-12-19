import shutil
import os
import re
from pprint import pprint
import datetime
import requests, requests_cache  # https://requests-cache.readthedocs.io/en/latest/
from bs4 import BeautifulSoup
import cv2
import concurrent.futures
import operator

# https://github.com/ryanseddon/earthin24/blob/master/create_video.sh
# https://downlinkapp.com/sources.json
# https://eumetview.eumetsat.int/static-images/latestImages/
satinfo = {'goes-16': {'url': 'https://cdn.star.nesdis.noaa.gov/GOES16/ABI/FD/GEOCOLOR/5424x5424.jpg',
                       'longitude': '75.2 W',
                       'order': 3,
                       'name': 'GOES-16'},
           'goes-17': {'url': 'https://cdn.star.nesdis.noaa.gov/GOES17/ABI/FD/GEOCOLOR/5424x5424.jpg',
                       'longitude': '137.2 W',
                       'order': 2,
                       'name': 'GOES-17'},
           'himawari': {'url': 'http://rammb.cira.colostate.edu/ramsdis/online/images/latest_hi_res/himawari-8/full_disk_ahi_true_color.jpg',
                        'longitude': '140.7 E',
                        'order': 1,
                        'name': 'Himawari-8'},
           'meteosat-11': {'longitude': '0',
                           'order': 4,
                           'name': 'METEOSAT-11'},
           'meteosat-8': {'longitude': '41.5 E',
                          'order': 5,
                          'name': 'METEOSAT-8'},
           }

maxprocesses=6
# image_width=5424
# image_height=5424
image_width=2000
image_height=2000

def x(sat):
    targetdir=f"{sat}/tiles"
    for dir in [sat, targetdir]:
        if not os.path.exists(dir):
            os.makedirs(dir)

def rambinfo(sat='goes-16'):
    url = f'https://rammb-slider.cira.colostate.edu/data/json/{sat}/full_disk/geocolor/latest_times.json'
    r = requests.get(url)
    try:
        result = sorted(r.json()['timestamps_int'])
    except:
        result = None
    return result

def eumetsat(sat):
    urls = {'meteosat-8': 'https://eumetview.eumetsat.int/static-images/MSG/RGB/NATURALCOLORENHNCD/FULLRESOLUTION',
            'meteosat-11': 'https://eumetview.eumetsat.int/static-images/MSGIODC/RGB/NATURALCOLORENHNCD/FULLRESOLUTION',
        }
    #    https://eumetview.eumetsat.int/static-images/MSG/RGB/NATURALCOLORENHNCD/FULLRESOLUTION/index.htm   meteosat-11 0 deg
    #    https://eumetview.eumetsat.int/static-images/MSGIODC/RGB/NATURALCOLORENHNCD/FULLDISC/index.htm  MeteoSat-8 41.5 deg
    page = requests.get(urls[sat])
    soup = BeautifulSoup(page.content, 'html.parser')
    options = [x.text for x in soup.find('select', {'name': 'selectImage'}).find_all('option')]
    imagenames = []
    for line in page.text.splitlines():
        m = re.search('\s*array_nom_imagen\[\d+\]="(\w+)"', line)
        if (m):
            imagenames.append(m.group(1))
    files = {options[i]: imagenames[i] for i in range(len(imagenames))}
    lastdatestr = sorted(list(files.keys()))[-1]
    latestdatetime = datetime.datetime.strptime(lastdatestr, '%y/%m/%d   %H:%M UTC')
    return  f"{urls[sat]}/IMAGESDisplay/{files[lastdatestr]}", latestdatetime, files

def concat_tile(im_list_2d):
    return cv2.vconcat([cv2.hconcat(im_list_h) for im_list_h in im_list_2d])

def get_latest_full_disk_image(sat, mask=True, label=True):
    targetdir=f"{sat}/tiles"
    for dir in [sat, targetdir]:
        if not os.path.exists(dir):
            os.makedirs(dir)
    dates = rambinfo(sat=sat)
    datestr = dates[-1]
    filename=f'{sat}/{datestr}.png'
    processes=[]
    with concurrent.futures.ProcessPoolExecutor(max_workers=maxprocesses) as executor:
        if not os.path.exists(filename):
            if 'meteosat' in sat:
                get_cira_tiles(datestr, filename, sat, targetdir)
            elif sat in satinfo.keys():
                processes.append(executor.submit(getimage, filename, satinfo[sat]['url']))
            else:
                raise ValueError(f"{sat} not implemented")
    for future in concurrent.futures.as_completed(processes):
        _ = future.result()
    img = cv2.imread(filename, cv2.IMREAD_UNCHANGED)
    resized = cv2.resize(img, (image_width,image_height), interpolation=cv2.INTER_AREA)
    cv2.imwrite(filename, resized)
    if mask:
        maskup(filename)
    if label:
        label_lower_left(filename, sat)
    shutil.rmtree(targetdir)
    return filename, datestr

def get_cira_tiles(datestr, resultfile, sat, targetdir):
    rows = []
    for x in range(8):
        images = []
        for y in range(8):
            url = f"https://rammb-slider.cira.colostate.edu/data/imagery/{str(datestr)[:8]}/{sat}---full_disk/natural_color/{datestr}/03/{x:03}_{y:03}.png"
            filename = f"{targetdir}/{datestr}_{x:03}_{y:03}.png"
            getimage(filename, url)
            images.append(cv2.imread(filename))
        rows.append(images)
    im_tile = concat_tile(rows)
    cv2.imwrite(resultfile, im_tile)

def getimage(filename, url):
    returncode = None
    if not os.path.exists(filename):
        r = requests.get(url, stream=True)
        returncode = r.status_code
        if returncode == 200:
            with open(filename, 'wb') as f:
                r.raw.decode_content = True
                shutil.copyfileobj(r.raw, f)
    return returncode

def label_lower_left(filename, sat):
    image = cv2.imread(filename)
    font = cv2.FONT_HERSHEY_SIMPLEX
    line1 = (round(image.shape[0]*.03), round(image.shape[1]*.93))
    line2 = (round(image.shape[0]*.03), round(image.shape[1]*.96))
    fontScale = round(image.shape[0]/1000)
    color = (255, 255, 255)
    thickness = round(image.shape[0]/2000)
    image = cv2.putText(image, satinfo[sat.lower()]['name'], line1, font, fontScale, color, thickness, cv2.LINE_AA)
    image = cv2.putText(image, satinfo[sat.lower()]['longitude'].replace('º', '\u00B0'), line2, font, fontScale, color, thickness, cv2.LINE_AA)
    cv2.imwrite(filename, image)
    return filename

def label_upper_right(filename, timestamp):
    image = cv2.imread(filename)
    font = cv2.FONT_HERSHEY_SIMPLEX
    line = (round(image.shape[1]*.90), round(image.shape[0]*.08))
    fontScale = round(image.shape[1]/3000)
    color = (255, 255, 255)
    thickness = round(image.shape[0]/1000)
    image = cv2.putText(image, timestamp, line, font, fontScale, color, thickness, cv2.LINE_AA)
    cv2.imwrite(filename, image)
    return filename

def maskup(filename):
    im = cv2.imread(filename)
    im_mask = cv2.imread('mask.png')
    # resized = cv2.resize(im_mask, (image_width,image_height), interpolation=cv2.INTER_AREA)
    if im.shape != im_mask.shape:
        resized = cv2.resize(im_mask, (image_width, image_height), interpolation=cv2.INTER_AREA)
        cv2.imwrite('/tmp/mask.png', resized)
        im_mask = cv2.imread('/tmp/mask.png')

    added_image = cv2.bitwise_and(im, im_mask)
    cv2.imwrite(filename, added_image)
    return filename

def by_order_value(item):
    return item[1]['order']

def buildcollage():
    images=[]
    jdish=set()
    for sat, info in sorted(satinfo.items(), key=by_order_value):
        print(sat)
        filename, dateint = get_latest_full_disk_image(sat)
        jdish.add(dateint)
        image = cv2.imread(filename)
        # resized = cv2.resize(image, (480, 480), interpolation=cv2.INTER_AREA)
        # filename=(f'{sat}/test.png')
        # cv2.imwrite(filename, resized)
        # im = cv2.imread(filename)
        images.append(image)
    im_colage = cv2.hconcat(images)
    date, time = divmod(max(jdish), 1000000)
    hour, minute = divmod(time, 10000)
    minute, sec = divmod(minute, 100)
    newfilename=f"{date}{hour:02}{minute:02}.png"
    cv2.imwrite(newfilename, im_colage)
    newfile = label_upper_right(newfilename, f"{date} {hour:02}{minute:02}Z")
    print(newfile)


if __name__ == '__main__':
    buildcollage()
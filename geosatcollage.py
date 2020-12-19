import shutil
import os
import re
from pprint import pprint
import datetime
import requests, requests_cache  # https://requests-cache.readthedocs.io/en/latest/
from bs4 import BeautifulSoup
import cv2
import concurrent.futures

# https://github.com/ryanseddon/earthin24/blob/master/create_video.sh
# https://downlinkapp.com/sources.json
# https://eumetview.eumetsat.int/static-images/latestImages/
fulldiskurls = {'goes-16': 'https://cdn.star.nesdis.noaa.gov/GOES16/ABI/FD/GEOCOLOR/5424x5424.jpg',
                'goes-17': 'https://cdn.star.nesdis.noaa.gov/GOES17/ABI/FD/GEOCOLOR/5424x5424.jpg',
                'himawari': 'http://rammb.cira.colostate.edu/ramsdis/online/images/latest_hi_res/himawari-8/full_disk_ahi_true_color.jpg',
                }
maxprocesses=5
# image_width=5424
# image_height=5424
image_width=640
image_height=640

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
    urls = {'meteosat-11': 'https://eumetview.eumetsat.int/static-images/MSG/RGB/NATURALCOLORENHNCD/FULLRESOLUTION',
            'meteosat-8': 'https://eumetview.eumetsat.int/static-images/MSGIODC/RGB/NATURALCOLORENHNCD/FULLRESOLUTION',
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

def get_latest_full_disk_image(sat='meteosat-8'):
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
            elif sat in fulldiskurls.keys():
                processes.append(executor.submit(getimage, filename, fulldiskurls[sat]))
            else:
                raise ValueError(f"{sat} not implemented")
    for future in concurrent.futures.as_completed(processes):
        print(future.result())
    img = cv2.imread(filename, cv2.IMREAD_UNCHANGED)
    resized = cv2.resize(img, (image_width,image_height), interpolation=cv2.INTER_AREA)
    cv2.imwrite(filename, resized)
    shutil.rmtree(targetdir)
    return filename

def get_cira_tiles(datestr, resultfile, sat, targetdir):
    rows = []
    for x in range(8):
        images = []
        for y in range(8):
            url = f"https://rammb-slider.cira.colostate.edu/data/imagery/{str(datestr)[:8]}/{sat}---full_disk/natural_color/{datestr}/03/{x:03}_{y:03}.png"
            filename = f"{targetdir}/{datestr}_{x:03}_{y:03}.png"
            print(filename)
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

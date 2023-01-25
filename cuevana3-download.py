#!/usr/bin/python3.8
# -*- coding: utf-8 -*-

import httpx
import json
import requests
from datetime import datetime
from lxml import html
from os.path import exists
from os import remove
from sys import argv
from tqdm import tqdm

class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def error(msg: str, quit: bool=True, quiet: bool=False) -> None:
    '''Print error message and exit (code 1)'''
    if not quiet:
        print(f"{Colors.FAIL}[ERROR]{Colors.ENDC} {msg}")
    if quit:
        exit(1)

def info(msg: str, quiet: bool=False) -> None:
    '''Print info message'''
    if not quiet:
        print(f"{Colors.OKCYAN}[INFO]{Colors.ENDC} {msg}")


class CLIParameter:
    '''Handle CLI parameter and it's optional value'''
    def __init__(self, name: str, isBoolean :bool=False):
        self.__name = name
        self.__isBoolean = isBoolean

    def test(self) -> bool:
        '''Test if parameter is present at CLI parameters'''
        return self.__name in argv

    def getValue(self) -> str:
        '''Get value from not boolean CLI parameter'''
        if self.__isBoolean:
            return None
        else:
            try:
                i = argv.index(self.__name)
                value =  argv[i + 1]
                if value[0] == '-':
                    error(f"{self.__name} value not given!")
                return value
            except IndexError:
                error(f"{self.__name} value not given!")
            except ValueError:
                return None


try:
    if len(argv) == 1:
        error("Movie URL not given!")
    else:
        session = requests.Session()
        url = argv[1]
        h = {
            'User-Agen': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36'
        }
        info("Requesting URL...")
        res = session.get(url, headers=h)
        if res.status_code == 200:
            htmlDom = html.fromstring(res.text)
            iframesLinks = [e.get('data-src').replace('//', 'https://') for e in htmlDom.cssselect('iframe.no-you')]
            movieTitle = htmlDom.cssselect('h1.Title')[0].text_content()
            movieTitle = movieTitle.replace(' ', '-').replace(':', '').lower() + '.mp4'

            # LET USER CHOSE DOWNLOAD OPTIONS

            # LOAD IFRAME
            info("Requesting movie iframe...")
            res = session.get(iframesLinks[0], headers=h)
            if res.status_code == 200:
                # GET TOKEN
                token = res.text.split('<input type="hidden" id="url" name="url" value="')[1].split('" />')[0]

                # GET PLAYER REDIRECTION
                url = 'https://apialfa.tomatomatela.club/ir/redirect_ddh.php'
                h = httpx.Headers({
                    'authority':                 'apialfa.tomatomatela.club',
                    'method':                    'POST',
                    'path':                      '/ir/redirect_ddh.php',
                    'scheme':                    'https',
                    'accept':                    'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
                    'accept-encoding':           'gzip, deflate, br',
                    'accept-language':           'es-CL,es;q=0.9,en-US;q=0.8,en;q=0.7',
                    'cache-control':             'max-age=0',
                    'content-type':              'application/x-www-form-urlencoded',
                    'origin':                    'null',
                    'sec-ch-ua':                 '"Not?A_Brand";v="8", "Chromium";v="108"',
                    'sec-ch-ua-mobile':          '?0',
                    'sec-ch-ua-platform':        '"Linux"',
                    'sec-fetch-dest':            'iframe',
                    'sec-fetch-mode':            'navigate',
                    'sec-fetch-site':            'same-origin',
                    'upgrade-insecure-requests': '1',
                    'user-agent':                'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36'
                })

                fileURLRequestURL = None
                info("Requesting access to file URL")
                while True:
                    res = httpx.post(url, data={'url': token}, headers=h)
                    if res.status_code == 302:
                        if not 'location' in res.headers.keys():
                            continue
                        else:
                            fileURLRequestURL = "https://tomatomatela.club/details.php?v=" + res.headers['location'].split('#')[1]
                            break
                    else:
                        error(f"Player redirection code: {res.status_code}")

                # GET FILE URL
                if fileURLRequestURL != None:
                    h = httpx.Headers({
                        'authority':                 'tomatomatela.club',
                        'method':                    'GET',
                        'path':                      fileURLRequestURL,
                        'scheme':                    'https',
                        'accept':                    'application/json, text/javascript, */*; q=0.01',
                        'accept-encoding':           'gzip, deflate, br',
                        'accept-language':           'es-CL,es;q=0.9,en-US;q=0.8,en;q=0.7',
                        'cache-control':             'max-age=0',
                        'content-type':              'application/x-www-form-urlencoded',
                        'origin':                    'null',
                        'sec-ch-ua':                 '"Not?A_Brand";v="8", "Chromium";v="108"',
                        'sec-ch-ua-mobile':          '?0',
                        'sec-ch-ua-platform':        '"Linux"',
                        'sec-fetch-dest':            'empty',
                        'sec-fetch-mode':            'cors',
                        'sec-fetch-site':            'same-origin',
                        'user-agent':                'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36'
                    })
                    res = httpx.get(fileURLRequestURL, headers=h)
                    info("Requesting download...")
                    if res.status_code == 200:
                        res = json.loads(res.text)
                        fileURL = res['file']

                        try:
                            # DOWNLOAD FILE
                            chunk = 1024
                            res = requests.get(fileURL, stream=True)
                            if res.status_code == 200:
                                
                                # CHECK IF FILE ALREADY EXISTS
                                if exists(movieTitle):
                                    while True:
                                        info(f"File '{movieTitle}' already exists, override?[y/n]")
                                        answer = input('')

                                        if not answer in ['n', 'y']:
                                            continue
                                        elif answer == 'y':
                                            remove(movieTitle)
                                            info(f"File: '{movieTitle}' deleted!")
                                            break
                                        elif answer == 'n':
                                            movieTitle_old = movieTitle
                                            movieTitle = movieTitle.replace('.mp4', '') + '_' + datetime.now().strftime("%d-%m-%Y-%H-%M-%S") + '.mp4'
                                            info(f"File: '{movieTitle_old}' renamed to '{movieTitle}'!")

                                info("Downloading...")

                                with open( movieTitle, 'wb' ) as f, tqdm(
                                    desc=movieTitle,
                                    total=int(res.headers.get('content-length', 0)),
                                    unit='iB',
                                    unit_scale=True,
                                    unit_divisor=chunk
                                ) as bar:
                                    for data in res.iter_content(chunk_size=chunk):
                                        size = f.write(data)
                                        bar.update(size)
                                info(f"File saved as '{movieTitle}'!")
                        except KeyboardInterrupt:
                            while True:
                                info(f"Do you want to delete the file {movieTitle}?[y/n]")
                                answer = input()
                                if not answer in ['n', 'y']:
                                    continue
                                elif answer == 'y':
                                    remove(movieTitle)
                                    info(f"File '{movieTitle}' deleted!")
                                    break
                            info('Abborted!')

                    else:
                        error("Could not request movie file!")
                else:
                    error("Could not request movie file!")
            else:
                error(f"Could not load iframe: {iframesLinks[0]}")
        else:
            error(f"Could not load: {url}")
except KeyboardInterrupt:
    info("Abborted!")
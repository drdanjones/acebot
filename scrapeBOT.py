from bs4 import BeautifulSoup
import re
import os
import requests
from dateutil import parser
from datetime import datetime
import moment
import calendar
import csv
from slackclient import SlackClient
from pocket import Pocket, PocketException


def smmry(link, smm):
    apilink = "http://api.smmry.com/&SM_API_KEY=" + smm + "&SM_LENGTH=5&SM_URL=" + link
    tesSUM = requests.get(apilink)
    return tesSUM.json()


def is_valid_date(string):
    today = datetime.today()
    try:
        x = parser.parse(string).replace(tzinfo=None)
        if 1000 > (today - x).days > 0:
            return x.date()
    except ValueError:
        return False
    return False


def is_date(string):
    try:
        parser.parse(string)
        return True
    except ValueError:
        return False


def find_date(string):
    string = string.split(' ')
    lgth = len(string)
    for k in range(lgth):
        if is_date(string[k]):
            i = k
            j = k + 1
            while is_date(' '.join(string[i:j])) and j < lgth + 1:
                j += 1
            return is_valid_date(' '.join(string[i:j - 1]))
    return False


def galink(link):
    if re.search('&ct=', link):
        return re.findall(r'&url=(.*?)&ct=', link)[0]
    else:
        return link


def scrape_pocket(command):
    print(command)
    filestring, chan = command.split("chan=")
    chan, user = chan.split('user=')
    d = find_date(filestring)
    since = None
    if d:
        since = calendar.timegm(d.timetuple())
    print(since)
    # command, filestring, chan, user = command.split(" ")
    # print(command, filestring, chan, user)
    if user == 'U2Y66L4A3':
        slack_client = SlackClient(os.environ.get('WILL_TOKEN'))
        # pock_toke = os.environ.get("BOWDITCH_POCKET")
    elif user == "U1Z8B013R":
        slack_client = SlackClient(os.environ.get('FARAI_TOKEN'))
        # pock_toke = os.environ.get("FARAI_POCKET")
    elif user == 'U2KJK9TU6':
        slack_client = SlackClient(os.environ.get('ANDY_TOKEN'))
        # pock_toke = os.environ.get("ANDY_POCKET")
    elif user == 'U2Z3K0GMP':
        slack_client = SlackClient(os.environ.get('ANDY_TOKEN'))
        # pock_toke = os.environ.get("COXON_POCKET")
    elif user == 'U23H209TQ':
        slack_client = SlackClient(os.environ.get('DAN_TOKEN'))
    else:
        return "I'm sorry, you are not authorised to do that. Your laptop is set to self-destruct in 10 seconds. Please step away from the laptop"

    pocket_tokens = [os.environ.get(person + "_POCKET") for person in ["BOWDITCH", "FARAI", "COXON"]]
    c_key = os.environ.get("POCKET_TOKEN")
    # pock_toke = os.environ.get("DAN_POCKET")
    # cc_toke = os.environ.get("COXON_POCKET")
    # wb_toke = os.environ.get("BOWDITCH_POCKET")
    # #print(c_key, cc_toke)
    # if is_date(since):
    #   since = parser.parse(since).timestamp()
    ad = []
    for pock_toke in pocket_tokens:
        p = Pocket(consumer_key=c_key, access_token=pock_toke)
        try:
            poks = p.get(sort='newest', detailType='complete', since=since)[0]  # tag, since parameters too
        except PocketException as e:
            print(e.message)
            return "Uh-oh.  I've had a problem trying to look in your Pocket."
        print(poks)
        for key in poks['list']:
            ad.append(key)

    links = [poks['list'][a]['resolved_url'] for a in ad if 'resolved_url' in poks['list'][a]]
    tt = [poks['list'][a]['resolved_title'] for a in ad if 'given_title' in poks['list'][a]]

    SMMRY_API = os.environ.get('SMMRY_API')

    lRow = []
    e = requests.Session()
    e.headers.update({'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.68 Safari/537.36'})

    for link in range(len(ad)):
        lDict = {
            'Topic': "",
            'Date Added': datetime.today().date(),
            'Date of Material': "",
            'Contributor': "SlackBot",
            'Type': "Google Alert News",
            'Link(s)': "",
            'Title or Brief Description': "",
            'Summary': ""
        }
        lDict['Link(s)'] = links[link]
        if 'tags' in poks['list'][ad[link]]:
            tags = [k for k in poks['list'][ad[link]]['tags']]
            lDict['Topic'] = ", ".join(tags)
        # if filestring == 'pocket':
        lDict['Title or Brief Description'] = tt[link]
        f = e.get(links[link])  # error handle here, pdf check?
        f = BeautifulSoup(f.text, 'html.parser')
        for thing in f(["script", "style", "head", "a"]):
            thing.extract()
        text = f.get_text()
        lines = (line.strip().replace('.', ':') for line in text.splitlines())
        # chunks = (phrase.strip() for line in lines for phrase in line.split(" "))
        textOut = '\n'.join(line for line in lines if line)

        dates = [is_date(line) for line in lines]
        if len(dates) > 0:
            # print(dates[0])
            lDict['Date of Material'] = dates[0]
        else:
            for line in textOut.split('\n'):
                # print(line)
                if find_date(line):
                    # print(find_date(line))
                    lDict['Date of Material'] = find_date(line)
                    break
        summary = smmry(links[link], SMMRY_API)
        if 'sm_api_title' in summary:
            lDict['Title or Brief Description'] = summary['sm_api_title']
            lDict['Summary'] = summary['sm_api_content'].replace(".", ".\n\n")
        else:
            titles = [cand.get_text().strip() for cand in f("h1")][::-1]
        # print(titles)
            while len(titles) > 0:
                if len(titles[-1]) > 0 and len(lDict['Title or Brief Description']) < 3:
                    # print(titles[-1])
                    lDict['Title or Brief Description'] = titles[-1]
                    break
                titles.pop()

        lRow.append(lDict)
        # print(lDict)
        # print(lRow)
    # print(lRow)
    tstamp = moment.now().format('MMM_DD_YYYY')
    with open(tstamp + '_bot_summary.csv', 'w') as csvfile:
        fieldnames = ['Topic', 'Date Added', 'Date of Material', 'Contributor', 'Type', 'Link(s)', 'Title or Brief Description', 'Summary']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in lRow:
            writer.writerow(row)
    with open(tstamp + '_bot_summary.csv', 'r') as csvfile:
        slack_client.api_call("files.upload", file=csvfile, filename=tstamp + '_bot_summary.csv', channels=chan)
        # testf = slack_client.api_call("files.upload", file=csvfile, filename=tstamp + '_bot_summary.csv', channels=chan)
        # print(testf)
    return "There you go!"

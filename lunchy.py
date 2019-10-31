import requests
from bs4 import BeautifulSoup, NavigableString
import datetime
import re
import os
import time
from schedule import Scheduler
import pickle
import threading

from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.pdfpage import PDFPage
from pdfminer.converter import TextConverter, HTMLConverter
from pdfminer.layout import LAParams
import io

def pdfparser(data):

    # fp = open(data, 'rb')
    fp = io.BytesIO(data)
    rsrcmgr = PDFResourceManager()
    retstr = io.BytesIO()

    device = HTMLConverter(rsrcmgr, retstr, codec='utf-8')
    # Create a PDF interpreter object.
    interpreter = PDFPageInterpreter(rsrcmgr, device)
    # Process each page contained in the document.

    for page in PDFPage.get_pages(fp):
        interpreter.process_page(page)
        data =  retstr.getvalue().decode('UTF-8')

    return data

class Lunchy(object):
    '''
    A docstring documenting this bot.
    '''
    def __init__(self):
        self.schedule = Scheduler()
        self.cease_continuous_run = self.run_continously()
        self.stored_menu = {}
        
        self.updateMenu()

        self.schedule.every().day.at('11:00').do(
            lambda: self.updateMenu if datetime.datetime.today().weekday() < 5 else False)

    def run_continously(self, interval=1):
        cease_continuous_run = threading.Event()

        class ScheduleThread(threading.Thread):
            @classmethod
            def run(cls):
                while not cease_continuous_run.is_set():
                    self.schedule.run_pending()
                    time.sleep(interval)

        continuous_thread = ScheduleThread()
        continuous_thread.start()
        return cease_continuous_run

    def tag(self):
        lst = ['Montag', 'Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag', 'Samstag', 'Sonntag']
        return lst[datetime.datetime.today().weekday()]

    def wiatshaus(self):
        print('Parsing wiener-wiazhaus.at')

        page = requests.get('https://www.wiener-wiazhaus.com/mittag')

        soup = BeautifulSoup(page.text, 'html.parser')
        elem = soup.find("a", string="MITTAGSMENÜS.PDF")

        pdf = requests.get(elem.attrs['href'])
        txt = pdfparser(pdf.content)

        soup = BeautifulSoup(txt, 'html.parser')
        elem = soup.find("span",string=self.tag())

        if not elem: 
            return []

        start = elem.find_next("span",style=re.compile('.*position:absolute.*'))
        body = start.next

        items = [
            re.findall('I\. (.+?)II\. ', body),
            re.findall('II\. (.+?)III\. ', body),
            re.findall('III\.(.+)', body)
        ]
        
        def clean(i):
            if len(i) > 0:
                return i[0].strip()
            return None
            
        price = clean(re.findall('([0-9,]+)\s*€',txt)) or '..€'
        return ['{} - *€{}*'.format(t, price) for t in [clean(i) for i in items] if t is not None]

    def salonwichtig(self):
        print('Parsing facebook.com/salonwichtig')
        page = requests.get('https://www.facebook.com/salonwichtig')

        soup = BeautifulSoup(page.text, 'html.parser')
        timestamp = soup.find_all("span", attrs={"class": "timestampContent"})

        last = [t for t in timestamp if re.match('\d+ Std', t.text)]

        if last:
            p = last[0].find_parent("div", attrs={"class": None}).find_parent("div", attrs={"class": None})
            pars = p.find_all('p')

            all = ''
            for p in pars:
                all += p.text

            lines = all.split('#')

            if len(lines) >= 2:
                return lines[2:-1]
            else:
                return lines

        else:
            return []

    def teigware(self):
        print('Parsing teigware.at')

        page = requests.get('http://www.teigware.at/')

        soup = BeautifulSoup(page.text, 'html.parser')
        elem = soup.find("table", attrs={"cellpadding": "8"})
        text = []

        def clean(s):
            return ' '.join(s.split())

        for r in elem.find_all('tr'):
            row = [c.text.strip() for c in r.find_all('td') if c.text.strip()]

            if re.search(self.tag(), row[0], flags=re.IGNORECASE):

                if row[1].isupper():
                    text = ['Geschlossen']
                    break

                text.append('{} - *{}*'.format(clean(row[1]), '€5,80'))
                text.append('{} - *{}*'.format(clean(row[2]), '€6,80'))

        return text

    def feinessen(self):
        print('Parsing feinessen.at')

        page = requests.get('http://www.feinessen.at/')

        soup = BeautifulSoup(page.text, 'html.parser')
        elem = soup.find("div", attrs={"id": "vbid-424badbc-rraljy31"})

        text = []

        # create separated list of items on page
        def br_list(node):
            list = []
            current = ''

            for c in node.find_all():

                if c.name == 'p':
                    list.append(current)
                    current = ''

                elif type(c.next) == NavigableString:
                    
                    if c.string and c.string.startswith('__'):
                        list.append(current)
                        list.append('__')
                        current = ''
                    else:
                        current += str(c.string)

                        if c.find_parent(name='h3'):
                            list.append(current)
                            current = ''

            list.append(current)
            return list

        list = [l for l in br_list(elem) if l is not '']

        for i, e in enumerate(list):
            if re.search(self.tag(), e, flags=re.IGNORECASE) or re.search('WOCHENGERICHTE', e):
                if list[i+2] is not '__':
                    text.append('{} - *{}*'.format(list[i + 1], list[i + 2].replace(' ', '')))
                else:
                    text.append(list[i+1])
        return text

    def updateMenu(self):
        # msg = "**{}'s lunch menu**\n\n".format(self.tag())
        # msg += "**Teigware:**\n" + "\n".join(self.teigware()) + '\n\n'
        # msg += "**Feinessen:**\n" + "\n".join(self.feinessen()) + '\n\n'
        # msg += "**Salon Wichtig:**\n" + "\n".join(self.salonwichtig()) + '\n\n'
        # msg += "**Wiener Wiazhaus:**\n" + "\n".join(self.wiatshaus()) + '\n'

        self.stored_menu  = {'day':  self.tag(),
                'teigware': ','.join(self.teigware()),
                'feinessen': ','.join(self.feinessen()),
                'salonwichtig': ','.join(self.salonwichtig()), 
                'wiatshaus': ','.join(self.wiatshaus())}

        print(self.stored_menu)
        return self.stored_menu

    def menu(self):
        if not self.stored_menu:
            self.updateMenu()

        return self.stored_menu
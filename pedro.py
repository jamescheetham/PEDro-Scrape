from bs4 import BeautifulSoup
from soupsieve import select
from urllib.request import Request
import urllib.request
import urllib.parse
import re
import sys
import requests
from datetime import datetime

# Need to get the Cookie on each request and set it each time from the previous value. Also need to send the cookie on the Ajax request. Need to make sure that the headers are getting sent.

class Select:
    def __init__(self, title, html_id, field_name=None):
        self.title = title
        self.html_id = html_id
        if field_name == None:
            self.field_name = self.html_id
        else:
            self.field_name = field_name
        self.options = []
        self.selected = None
        
    def get_options(self, html):
        for o in html.find_all("option"):
            value = o['value']
            if value != "0":
                text = o.text
                self.options.append(SelectOptions(text, value))
                
    def select(self):
        print(self.title)
        for i in range(len(self.options)):
            print('%3d) %s' % (i+1, self.options[i].name))
        while True:
            tmp = input('Please select (leave blank for none): ').strip()
            if tmp == '':
                return
            try:
                selected_option = int(tmp)
            except ValueError:
                print('Invalid Option')
                continue
            if selected_option < 1 or selected_option > len(self.options):
                print('Invalid Option')
            else:
                self.selected = selected_option - 1
                return
            
    def get_selected(self):
        return ("0" if self.selected == None else self.options[self.selected].value)
                                    
    def __str__(self):
        output = '--%s--\n' % self.html_id
        for o in self.options:
            output += '%s\n' % o
        return output[:-1]

        
class SelectOptions:
    def __init__(self, name, value):
        self.name = name
        self.value = value
        
    def __str__(self):
        return '%s - %s' % (self.value, self.name)
        

SEARCH_URL = 'https://search.pedro.org.au/advanced-search'
RESULTS_URL = 'https://search.pedro.org.au/advanced-search/results'
AJAX_URL = 'https://search.pedro.org.au/ajax/add-record'
SAVE_RESULTS_URL = 'https://search.pedro.org.au/save-results/results'
SUMMARY_RESULTS_URL = 'https://search.pedro.org.au/search-results/selected-records'
PER_PAGE = 50
SAVE_FILE = 'results_%s.ris' % (datetime.now().strftime("%Y%m%d_%H%M%S"))


urllib_request = urllib.request.urlopen(SEARCH_URL)
cookie_data = urllib_request.getheader('Set-Cookie').split(';')[0]
#print(cookie_data)
search_page = BeautifulSoup(urllib_request, "lxml")
therapy_select = search_page.find("select", { "id" : "therapy" })
select_fields = [Select('Therapy', 'therapy'), Select('Problem', 'problem'), Select('Body Part', "body-part", "body_part"), Select('Subdiscipline', "subdiscipline"), Select('Topic', "topic"), Select('Method', 'method')]

for s in select_fields:
    s.get_options(search_page.find('select', { 'id' : s.html_id }))

while True:
    abstract = input('Abstract & Title: ').strip()
    if abstract != "":
        break

for s in select_fields:
    s.select()
    
author = input('Author/Association: ').strip()
title_only = input('Title Only: ').strip()
source = input('Source: ').strip()
published_since = input('Published Since: ').strip()
records_added_since = input('New Records Added Since: ').strip()
minimum_score = input('Score of at least: ').strip()
while True:
    search_join = input('When Searching [AND]/OR: ').strip().lower()
    if search_join == "":
        search_join = 'and'
    if search_join == 'and' or search_join == 'or':
        break

#https://search.pedro.org.au/advanced-search/results?abstract_with_title=&therapy=VL01376&problem=0&body_part=0&subdiscipline=0&topic=0&method=0&authors_association=&title=&source=&year_of_publication=&date_record_was_created=&nscore=&perpage=20&lop=and&find=&find=Start+Search

params = [abstract.replace(' ', '+')] + [x.get_selected() for x in select_fields] + [author, title_only, source, published_since, records_added_since, minimum_score, PER_PAGE, search_join]

get_request = 'abstract_with_title=%s&therapy=%s&problem=%s&body_part=%s&subdiscipline=%s&topic=%s&method=%s&authors_association=%s&title=%s&source=%s&year_of_publication=%s&date_record_was_created=%s&nscore=%s&perpage=%s&lop=%s&find=Start+Search' % tuple(params)

url_request = Request('%s?%s' % (RESULTS_URL, get_request))
url_request.add_header('Cookie', cookie_data)
#print(url_request.header_items())
urllib_request = urllib.request.urlopen(url_request)
cookie_data = urllib_request.getheader('Set-Cookie').split(';')[0]
results_page = BeautifulSoup(urllib_request, 'lxml')

with open("output1.html", "w") as f:
    f.write(str(results_page))

re_prog = re.compile('Found ([0-9]+) records?')
re_result = re_prog.search(results_page.find("div", {'id' : 'search-content'}).text)
if re_result is None:
    print('The Search returned 0 results')
    sys.exit(0)
try:
    search_count = int(re_result.group(1))
except ValueError:
    sys.exit('Unable to parse the Result Count into an Integer')
print('Found %d Results' % search_count)
while True:
    answer = input('Do you wish to Continue [Y/n]? ').strip()
    if answer == '' or answer.lower() == 'y':
        break
    if answer.lower() == 'n':
        sys.exit(0)
    print('Invalid Response')
page_count = 0
try:
  pagination = results_page.find("ul", {'class' : 'pagination'}).findChildren('li', recursive=False)
  for p in pagination:
      if p.text == '«' or p.text == '»' or p.text == '...':
          continue
      try:
          page_num = int(p.text)
      except ValueError:
          sys.exit("Unable to parse page number (%s) into integer" % p.text)
      if page_num > page_count:
          page_count = page_num
except AttributeError:
  page_count = 1
print('There are %d pages with %d results per page' % (page_count, PER_PAGE))

id_list = []

id_search = results_page.find_all('td', {'id' : re.compile("art-[0-9]+")}, recusive=False)
for i in id_search:
    id_list.append(i['id'][4:])

for page in range(2, page_count+1):
    url_request = Request('%s?%s&page=%d' % (RESULTS_URL, get_request, page))
    url_request.add_header('Cookie', cookie_data)
    urllib_request = urllib.request.urlopen(url_request)
    cookie_data = urllib_request.getheader('Set-Cookie').split(';')[0]
    results_page = BeautifulSoup(urllib_request, 'lxml')
    id_search = results_page.find_all('td', {'id' : re.compile("art-[0-9]+")})
    for i in id_search:
        id_list.append(i['id'][4:])

start_time = datetime.now()
print('Making AJAX Calls')
count = 0
for i in id_list:
    payload={'article_id': i, 'type': 'list'}
    headers = {'Cookie': cookie_data}
    ajax_response = requests.post(AJAX_URL, data=payload, headers=headers)
    cookie_data = ajax_response.headers['Set-Cookie'].split(';')[0]
    count += 1
    if count % 10 == 0:
        print('Completed %d' % count)
if count % 10 != 0:
    print('Completed %d' % count)
print('AJAX Complete in %d seconds' % (datetime.now() - start_time).seconds)
print('Saving output to %s' % SAVE_FILE)
url_request = Request(SUMMARY_RESULTS_URL)
url_request.add_header('Cookie', cookie_data)
urllib_request = urllib.request.urlopen(url_request)
cookie_data = urllib_request.getheader('Set-Cookie').split(';')[0]
#temp = BeautifulSoup(urllib_request, 'lxml')
#with open("output2.html", "w") as f:
    #f.write(str(temp))
results_file = urllib.request.URLopener()
results_file.addheader('Cookie', cookie_data)
results_file.retrieve(SAVE_RESULTS_URL, SAVE_FILE)

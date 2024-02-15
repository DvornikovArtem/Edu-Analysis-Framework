import json
from random import random

import requests
from time import sleep
from bs4 import BeautifulSoup as BSoup


class ParserISU:
    def __init__(self, cookie: str, remember_sso):
        self.cookies = {'ISU_AP_COOKIE': cookie,
                        'REMEMBER_SSO': remember_sso}

    def parse_users_data(self):
        base_isu_person_link = 'https://isu.itmo.ru/person/'

        for isu_person_id in range(103466, int(1e6)):
            sleep(0.2 + random())
            person_link = base_isu_person_link + str(isu_person_id)
            try:
                response = requests.get(person_link, cookies=self.cookies)
                print(isu_person_id, response.status_code)
                person_data = self.parse_data_from_html(response.text)
            except (requests.exceptions.ConnectTimeout, requests.exceptions.ReadTimeout):
                print(f'User with ISU id {isu_person_id} does not exist')

            open('page.html', 'w', encoding='utf-8').write(response.text)
            break

    def parse_data_from_html(self, html_text):
        soup = BSoup(html_text, 'html.parser')

        data = {'publications': self.parse_publications(soup), 'rid': self.parse_rid(soup)}
        # data = {'rid': self.parse_rid(soup)}

        return data

    def parse_publications(self, soup: BSoup):
        data: str = str(soup.find('span', id='R1724073431179133097').find('script'))

        publications = []
        data = (data[data.find('.jsonData={') + 10:data.find('};') + 1])
        data: dict = json.loads(data)
        data.pop('recordsFiltered')

        for row in data['data']:
            year_index = row[3].find('>') + 1
            publications.append({'type': row[1],
                                 'year': int(row[3][year_index:year_index + 4]),
                                 'authors': self.parse_authors(row[2]),
                                 'title': row[2][row[2].rfind('</a>') + 5:]
                                 })
        return publications

    def parse_rid(self, soup: BSoup):
        data: str = str(soup.find('span', id='R1724086259370226350').find('script'))
        data: dict = json.loads(data[data.find('jsonData={') + 9:data.find('};') + 1])
        data.pop('recordsFiltered')

        rids = []
        for row in data['data']:
            year_index = row[1].find('>') + 1
            rids.append({
                'year': int(row[1][year_index:year_index + 4]),
                'type': row[2].strip(),
                'title': row[3].strip(),
                'authors': self.parse_authors(row[5])
            })
        return rids

    @staticmethod
    def parse_authors(authors_string: str) -> list:
        authors = []
        for author in authors_string.split(','):
            first_quote = author.find('"')
            second_quote = first_quote + author[first_quote + 1:].find('"') + 1
            third_quote = second_quote + author[second_quote + 1:].find('"') + 1
            fourth_quote = third_quote + author[third_quote + 1:].find('"') + 1
            author = {'isu_profile': author[first_quote + 1:second_quote],
                      'name': author[third_quote + 1: fourth_quote]}
            authors.append(author)
        return authors


if __name__ == '__main__':
    parser = ParserISU('your_cookie',
                       'your_sso_token')

    # parser.parse_users_data()
    print(parser.parse_data_from_html(open('page.html', 'r', encoding='utf-8').read()))

# ["<center><span class=\"npr text-primary-click \"
#

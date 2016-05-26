#!/usr/bin/env python
# -*- coding: utf-8 -*-

import urllib2
from BeautifulSoup import BeautifulSoup
from HTMLParser import HTMLParser
import csv
import codecs
import json
from click import click

('\n'
 'Variable declaration\n'
 '@DEFAULT_URL\n'
 '@URL_FIELDS\n'
 '@dicionario\n'
 '@letter_href_dict\n'
 '@fieldnames\n'
 '@count\n')

DEFAULT_URL = "http://www.portaldalinguaportuguesa.org"
URL_fields = "/index.php?action=syllables&act=list"
fieldnames = ["word", "division", "syllables", "morphology"]
parser = HTMLParser()
dicionario = {}
letter_href_dict = {}


'''
Function declaration
'''


def get_count():
    global count
    return count

count = 0


def inc_counter(val):
    global count
    count += val


def build_url(fields):
    return DEFAULT_URL+fields


def get_page(url):
    return urllib2.urlopen(url).read()


def get_main_table(soup_object):
    return soup_object.find('table', {'name': 'rollovertable'})


def get_letters_table(soup_object):
    return soup_object.find('table', {'name': 'maintable'})


def get_table_lines(table_object):
    return table_object('td', {'title': 'Palavra'})


def get_table_rows(table_object):
    return table_object.findAll('tr')


def file_put_contents(format, outfile, contents, utf8=True):
    if format == 'csv':
        fp = open(outfile, 'w+')
        writer = csv.DictWriter(fp, delimiter=",", quoting=csv.QUOTE_NONNUMERIC, quotechar='"', fieldnames=fieldnames)
        writer.writeheader()
        for row in contents:
            row = {k: v.strip().encode('utf-8') if type(v) in (str, unicode) else v for k, v in row.items()}
            writer.writerow(row)

    elif format == 'json':
        fp = codecs.open(outfile, 'w+', 'utf-8')
        fp.write(json.dumps(contents, encoding='utf-8', ensure_ascii=False, indent=2, sort_keys=True))
        fp.close()


def parse_href(element):
    return element['href']


def next_page(element):
    if check_for_next(element):
        href = map(parse_href, element.findAll('a', href=True))
        # Debug:
        # print href
        return href[len(href) - 1]  # always return last element
    return False


def check_for_next(element):
    text = ''.join(element.findAll(text=True))
    # print text.replace(";", " ").replace(",", " ").split()
    if "seguintes" in text.lower():
        return True
    #elif "anteriores" in text.lower():
    else:
        return False
    return False


def count_syllable(div_word):
    s = div_word.split("-")
    return len(s)


def parse_string(s):
    # add only text
    text = ''.join(s.findAll(text=True))
    # Replace the html chars &middot; (present in the html code) with '-'
    string = text.replace("&middot;", "-")
    # head = word
    # word's morphology in between '()'
    # head will always contain the word or the syllabic division
    head, sep, tail = string.partition(" (")
    # store text in between ()
    h, s, t = tail.partition(")")
    return head.strip("\n")
    # return text.strip()


def add_to_letter_dict(keys, vals):
    for enum in range(0, len(keys)):
        letter_href_dict[keys[enum]] = vals[enum]


def add_to_dict(index, key, val, syl_count):
    dicionario[index] = (key, val, syl_count)


def find_letters_url(row_object):
    for row in row_object:
        # find all available letters
        data = map(parse_string, row.findAll('td'))
        # print data
        # find all hrefs to all letters
        href = map(parse_href, row.findAll('a', href=True))
        # print str(data) + '@' + str(href)
        add_to_letter_dict(data, href)


def find_words(rows):
    # fieldnames : morphology string not implemented yet
    tmp = []
    for row in rows:
        data = map(parse_string, row.findAll('td'))
        # DEBUG:
        # print str(i) + ' ' + data[0] + ' @ ' + data[1]
        counter = count_syllable(data[1])
        # add_to_dict(i, data[0], data[1], count)
        tmp.append({"word": data[0],
                    "division": data[1],
                    "syllables": counter,
                    "morphology": ""})
    return tmp


def char_range(c1, c2):
    """Generates the characters from `c1` to `c2`, inclusive."""
    for c in xrange(ord(c1), ord(c2)+1):
        yield chr(c)


def parse(url_fields, current_letter, end_letter, outfile, format, verbose):
    next_ = False
    soup = BeautifulSoup(get_page(DEFAULT_URL + url_fields))
    next_link = soup.find('p', {'style': "color: #666666;"})
    if next_link:
        next_ = next_page(next_link)
    main_table = get_main_table(soup)
    # line = get_table_lines(main_table)
    rows = get_table_rows(main_table)[1:]  # [1:] to ignore table headers
    content = find_words(rows)  # content of all rows inside "rollover table"
    if verbose:
        print "writing to file: "+outfile
    file_put_contents(format, outfile, content)
    if next_:
        if verbose:
            print "current URL: "+next_
        # stat char <- next_
        # parse all instances of words for a given letter
        parse(next_, current_letter, end_letter, outfile, format, verbose)
    else:  # in case there are no more 'seguinte'/'next' links to follow
        if verbose:
            print "current URL: "+url_fields
        inc_counter(1)
        print "end of scraping letter: " + current_letter
        # move on to different letter/char
        next_char = chr(ord(current_letter) + 1)
        return next_char


def scrape_page(url_fields, start_letter, end_letter, outfile, frmt="csv", verbose=False):

    # only useful on 1st iteration
    # init BeautifulSoup object
    soup = BeautifulSoup(get_page(DEFAULT_URL + url_fields))

    # static table for available chars
    letter_table = get_letters_table(soup)

    # static table row with available chars
    letter_row = get_table_rows(letter_table)
    find_letters_url(letter_row)

    # for every letter that user wants
    # debug:
    # range_ = ''.join(char_range(start_letter, end_letter))
    # print range

    for letter in char_range(start_letter, end_letter):
        if letter_href_dict.has_key(letter.lower()):  # if available in website

            if verbose:
                print ("Starting letter: " + start_letter + ", on my way to: " + end_letter)

            url_fields = letter_href_dict.get(letter.lower())
            parse(url_fields, letter, end_letter, outfile, frmt, verbose)  # parse all words for a given letter
        else:
            continue_letter = chr(ord(letter) + 1)  # try to use next word in alphabet
            print "URL not found for letter: " + letter
            print "Continuing my job @ letter: " + continue_letter + "^.^"
            # restart with different start letter
            scrape_page(URL_fields, continue_letter, end_letter, outfile, format, verbose)
        print "Scraped " + str(get_count()) + " letters"

    print "\n" \
          "****************************\n" \
          "* Scrapples job is done :) *\n" \
          "****************************\n"


@click.command()
@click.option("--start", default="a", help="Start letter, default A")
@click.option("--end", default="z", help="End letter, default Z")
@click.option("--format", default="csv", help="Define output format -> csv(default) or JSON")
@click.option("--outfile", type=click.Path(), help="Path to specific file")
@click.option("--verbose", is_flag=True, help="Print useful? information while executing")
def main(start, end, format, verbose, outfile):

    if not outfile and format == "json":
        outfile = "dict-silabas-scraper.json"
    elif not outfile and format == "csv":
        outfile = "dict-silabas-scraper.json"
    if not start and not end:
        start = 'a'
        end = 'z'
    elif not end:
        end = 'z'
    elif not start:
        start = 'a'

    if verbose:
        print "\n" \
              "I will be expressive"
        print "Destination file: "+outfile
        print "Format: "+format
        print "Range of scrape, from "+ start + " to " + end
        print "\n"
    scrape_page(URL_fields, start, end, outfile, format, verbose)


if __name__ == "__main__":
    main()

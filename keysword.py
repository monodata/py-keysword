# -*- coding: utf-8 -*-

"""
Keysword is a utility for extracting Filevault2 keys from JAMF JSS
~~~~~~~~~~~~
This module implements the Requests API.
:copyright: (c) 2019 by Mike Mackintosh.
:license: Apache2, see LICENSE for more details.
"""

import requests
import cookielib
import argparse
from os import getenv
from xml.dom.minidom import parseString

__VERSION__ = "1.0"

JAMF_HOST = "JSS_HOST"
JAMF_USERNAME = "JSS_USER"
JAMF_PASSWORD = "JSS_PASSWORD"


"""
getComputerID
-------------
Converts a computer name to a computer ID using the JAMF API
  :param name string
  :return id string
"""


def getComputerID(name):
    auth = requests.auth.HTTPBasicAuth(JAMF_USERNAME, JAMF_PASSWORD)
    headers = {"Accept": "application/json"}
    resp = requests.get("{}/JSSResource/computers/name/{}".format(JAMF_HOST, name), auth=auth, headers=headers)

    # TODO: add error checking here
    return resp.json()["computer"]["general"]["id"]


"""
getSessionToken
-------------
Gets a session token from the legacy pages to get access to the ajax API
  :param s requests.Session
  :param jar cookie jar
  :return token string
"""


def getSessionToken(s, jar, id):
    resp = s.post('{}/?failover'.format(JAMF_HOST), cookies=jar, data={'username':JAMF_USERNAME, 'password':JAMF_PASSWORD, 'resetUsername':''})
    if resp.status_code != 200:
        print "Looks like you failed to authenticate"
        exit(1)

    params = {"id": id, "o": "r", "v": "management"}
    resp = s.get('{}/legacy/computers.html'.format(JAMF_HOST), params=params, cookies=jar)
    session_token = ""

    # TODO: add error checking here
    for line in resp.content.splitlines():
        if "session-token" in line:
            return line.encode('utf-8').translate(None, '<>"').split('=')[-1]
    print "Unable to find session token"


"""
main
-------------
Connects to the JAMF JSS API and extracts a filevault key for the provided device ID
  :param id string
  :param name string
"""


def main(id, name):
    """ Create the cookie jar and session for requests """
    jar = cookielib.CookieJar()
    s = requests.Session()
    s.cookies = jar

    """ Get the computer id if a hostname was provided """
    if len(name) > 0:
        id = getComputerID(name)

    """ Get the session token """
    session_token = getSessionToken(s, jar, id)
    if len(session_token) == 0:
        print "Unable to find session token"
        exit()

    """ Make the request against the computers.ajax endpoint """
    data = "&ajaxAction=AJAX_ACTION_READ_FILE_VAULT_2_KEY&session-token={}".format(session_token)
    resp = s.post('{}/computers.ajax?id={}&o=r&v=management'.format(JAMF_HOST, id), data="{}".format(data), cookies=jar, headers={
        "X-Requested-With": "XMLHttpRequest",
        "Origin": JAMF_HOST,
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Accept": "*/*",
        "Content-Length": "{}".format(len(data)),
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "keep-alive",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/72.0.3626.81 Safari/537.36",
        "Referer": "{}/legacy/computers.html?id={}&o=r&v=management".format(JAMF_HOST, id)
    })

    # TODO: add error checking here
    e = parseString(resp.content)
    if len(e.getElementsByTagName("individualKey")) > 0:
        for n in e.getElementsByTagName("individualKey")[0].childNodes:
            if n.nodeType == n.TEXT_NODE:
                print n.data
                return

    """ If we couldn't find the key, print """
    print "Unable to find filevault key"


""" main """
if __name__ == "__main__":

    """ Create Argparser """
    parser = argparse.ArgumentParser(prog='keysword')
    parser.add_argument('-id', action="store", default="", dest="id")
    parser.add_argument('-name', action="store", default="", dest="name")
    parser.add_argument('--version', action='version', version='%(prog)s {}'.format(__VERSION__))
    results = parser.parse_args()

    """ Quick validation of arguments """
    if len(results.id) == 0 and len(results.name) == 0:
        print "Please provide a computer id with -id or computer name with -name"
        exit()

    elif len(results.id) != 0 and len(results.name) != 0:
        print "Please provide only one computer id with -id or with -name, but not both"
        exit()

    if len("JAMF_USERNAME") == 0 \
            or len("JAMF_USERNAME") == 0 \
            or len("JAMF_HOST") == 0:
        print "Please set your environment variables appropriately"
        exit()

    """ run main """
    main(results.id, results.name)

# -*- coding: utf-8 -*-
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#
#  Author: Mauro Soria

import random
import urllib.parse
import socket
import http.client
import urllib.request
import urllib.parse
import urllib.error
from urllib.parse import urlparse

import thirdparty.requests as requests
from .Response import *
from .RequestException import *


class Requester(object):

    headers = {
        'User-agent': 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/28.0.1468.0 Safari/537.36',
        'Accept-Language': 'en-us',
        'Accept-Encoding': 'identity',
        'Keep-Alive': '300',
        'Connection': 'keep-alive',
        'Cache-Control': 'max-age=0',
        }

    def __init__(self, url, cookie=None, useragent=None, maxPool=1, maxRetries=5, timeout=30, ip=None, proxy=None,
                 redirect=False, sameDomain=True):
        # if no backslash, append one
        if not url.endswith('/'):
            url = url + '/'
        parsed = urllib.parse.urlparse(url)
        self.basePath = parsed.path

        # if not protocol specified, set http by default
        if parsed.scheme != 'http' and parsed.scheme != 'https':
            parsed = urllib.parse.urlparse('http://' + url)
            self.basePath = parsed.path
        self.protocol = parsed.scheme
        if self.protocol != 'http' and self.protocol != 'https':
            self.protocol = 'http'
        self.host = parsed.netloc.split(':')[0]

        # resolve DNS to decrease overhead
        if ip is not None:
            self.ip = ip
        else:
            try:
                self.ip = socket.gethostbyname(self.host)
            except socket.gaierror:
                raise RequestException({'message': "Couldn't resolve DNS"})
        self.headers['Host'] = self.host

        # If no port specified, set default (80, 443)
        try:
            self.port = parsed.netloc.split(':')[1]
        except IndexError:
            self.port = (443 if self.protocol == 'https' else 80)

        # Set cookie and user-agent headers
        if cookie is not None:
            self.setHeader('Cookie', cookie)
        if useragent is not None:
            self.setHeader('User-agent', useragent)
        self.maxRetries = maxRetries
        self.maxPool = maxPool
        self.timeout = timeout
        self.pool = None
        self.proxy = proxy
        self.redirect = redirect
        self.randomAgents = None
        self.sameDomain = sameDomain

    def setHeader(self, header, content):
        self.headers[header] = content

    def getDomain(self,url):
        urlp = urlparse(url)
        domain = urlp.netloc.split('@')[-1]
        if domain.rfind(':') == -1:
            if urlp.scheme=='http':
                domain+=':80'
            elif urlp.scheme=='https':
                domain+=':443'
        return "%s://%s"%(urlp.scheme,domain)

    def setRandomAgents(self, agents):
        self.randomAgents = list(agents)

    def unsetRandomAgents(self):
        self.randomAgents = None

    def getDirPath(self, path):
        if path.find(self.basePath)==0:
            return path[len(self.basePath):]
        else:
            return path
    def request(self, path):
        i = 0
        proxy = None
        result = []
        while i <= self.maxRetries:
            try:
                if self.proxy is not None:
                    proxy = {"https" : self.proxy, "http" : self.proxy}
                url = "{0}://{1}:{2}".format(self.protocol, self.ip, self.port)
                url = urllib.parse.urljoin(url, self.basePath)

                # Joining with concatenation because a urljoin bug with "::"
                if not url.endswith('/'):
                    url += "/"
                if path.startswith('/'):
                    path = path[1:]
                url += path

                headers = dict(self.headers)
                if self.randomAgents is not None:
                    headers["User-agent"] = random.choice(self.randomAgents)
                headers["Host"] = self.host
                # include port in Host header if it's non-standard
                if (self.protocol == "https" and self.port != 443) or (self.protocol == "http" and self.port != 80):
                    headers["Host"]+=":{0}".format(self.port)
                # if '/Joomla/' in url:
                #     print(url,proxy,headers,self.timeout)
                response = requests.get(url, proxies=proxy, verify=False, allow_redirects=False, \
                                        headers=headers, timeout=self.timeout)
                if self.redirect and response.status_code in [301, 302, 307]:
                    domain = self.getDomain(url)
                    current_domain = self.getDomain(response.headers['Location'])
                    #print(domain,current_domain)
                    if self.sameDomain and (current_domain=='' or domain==current_domain):
                        response = requests.get(url, proxies=proxy, verify=False, allow_redirects=True, \
                                            headers=headers, timeout=self.timeout)
                response_list = response.history+[response]
                for response_one in response_list:
                    response_path = urlparse(response_one.url).path
                    if response_path.replace('/','') !='':
                        result.append(Response(response_path, self.getDirPath(response_path), response_one.status_code, response_one.reason, response_one.headers, response_one.content))
                del headers
                break
            except requests.exceptions.TooManyRedirects as e:
                raise RequestException({'message': 'Too many redirects: {0}'.format(e)})
            except requests.exceptions.ConnectionError as e:
                if self.proxy is not None:
                    raise RequestException({'message': 'Error with the proxy: {0}'.format(e)})
                continue
            except (requests.exceptions.ReadTimeout, requests.exceptions.Timeout, http.client.IncompleteRead, \
                    socket.timeout,requests.exceptions.InvalidSchema):
                continue
            finally:
                i = i + 1
        if i > self.maxRetries:
            raise RequestException(\
                {'message': 'CONNECTION TIMEOUT: There was a problem in the request to: {0}'.format(path)}
                )
        return result

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

import threading
from lib.reports import *

class ReportManager(object):

    def __init__(self):
        self.outputs = []
        self.lock = threading.Lock()

    def addOutput(self, output):
        self.outputs.append(output)

    def addPath(self, path, status, response):
        with self.lock:
            for output in self.outputs:
                output.addPath(path, status, response)

    def save(self):
        with self.lock:
            for output in self.outputs:
                output.save()

    def smartSave(self,showMax):
        with self.lock:
            for output in self.outputs:
                if output.__class__ is not JSONReport:
                    output.save()
                    continue
                tmpPathList = []
                checkList = []
                for plo in output.pathList:
                    path = plo[0]
                    status = plo[1]
                    contentLength = plo[2]
                    redirect = plo[3]
                    finded = False
                    for check in checkList:
                        if check[0][1]==status and check[0][2]==contentLength and check[0][3]==redirect:
                            check[1]+=1
                            finded = True
                    if not finded:
                        checkList.append([(path, status, contentLength, redirect),1])
                for check in checkList:
                    if check[1]<showMax:
                        tmpPathList.append(check[0])
                output.pathList = tmpPathList
                output.save()
    def close(self):
        for output in self.outputs:
            output.close()



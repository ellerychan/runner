#!/usr/bin/python
#
#   File: runner.py
# Author: Ellery Chan
#  Email: ellery@precisionlightworks.com
#   Date: Sep 20, 2015
# Copyright (c) 2015 Ellery Chan
#----------------------------------------------------------------------------
"""
Usage: runner.py [-h] [-w CMDWIDTH] commandFile

A simple GUI for running a canned set of commands on demand. The commands are
loaded from a file in JSON format. The file contains an array of objects
containing a "button" field, a "cmd" field, and an optional "tooltip" field,
as in the following example:

[
   {
      "button" : "Backup Database",
      "cmd"    : "pgdump > db_backup.sql",
      "tooltip": "Dump the database contents to a SQL file"
   },
   {
      "button" : "Restore Database",
      "cmd" : "psql -U admin < db_backup.sql",
      "tooltip": "Restore the database contents from an SQL file"
   }
]

positional arguments:
  commandFile           A file containing button labels and commands, in JSON
                        format

optional arguments:
  -h, --help            show this help message and exit
  -w CMDWIDTH, --cmdWidth CMDWIDTH
                        The displayed width of the command field (default 80)
"""

from __future__ import print_function, division

import sys
import subprocess
import os.path
import json
from argparse import ArgumentParser
from Tkinter import Tk, Button, Entry, END
from idlelib.ToolTip import ToolTip

#----------------------------------------------------------------------------
class RunnerApp(object):
    """ A simple GUI for running a canned set of commands on demand.
    
        The commands are loaded from a file in JSON format.  The file
        contains an array of objects containing a "button" field, a "cmd"
        field, and an optional "tooltip" field, as in the following example:
        
        [
           {
              "button" : "Backup Database",
              "cmd"    : "pgdump > db_backup.sql",
              "tooltip": "Dump the database contents to a SQL file"
           },
           {
              "button" : "Restore Database",
              "cmd"    : "psql -U admin < db_backup.sql",
              "tooltip": "Restore the database contents from an SQL file"
           }
        ]
    """
    DEFAULT_CMD_WIDTH = 80
    
    def __init__(self):
        self.args     = None
        self.cmds     = None
        self.title    = None
        self.cmdWidth = 0
        self.root     = None
    
    def parseCmdLine(self):
        parser = ArgumentParser(description=self.__doc__)
        parser.add_argument("-w", "--cmdWidth", type=int, default=0,
                            help="The displayed width of the command field (default {})".format(self.DEFAULT_CMD_WIDTH))
        parser.add_argument(dest="commandFile",
                            help="A file containing button labels and commands, in JSON format")
        self.args = parser.parse_args()
        
        if self.args.cmdWidth >= 0:
            self.cmdWidth = self.args.cmdWidth

    def readCmds(self):
        self.title = os.path.splitext(os.path.basename(self.args.commandFile))[0]
        with open(self.args.commandFile, "r") as f:
            data = json.load(f)
            if isinstance(data, (list, tuple)):
                self.cmds = data
            else:
                if "title" in data:
                    self.title = data["title"]
                if "cmds" in data:
                    self.cmds = data["cmds"]
                if "width" in data and self.cmdWidth <= 0:
                    self.cmdWidth = data["width"]

    
    def makeCmdButton(self, parent, cmd, row):
        cmdText = Entry(parent, width=self.cmdWidth)
        cmdText.grid(row=row, column=1, sticky="ew", ipady=2)
        cmdText.delete(0, END)
        cmdText.insert(0, cmd["cmd"])

        button = Button(parent, text=cmd["button"], command=lambda: self.execute(cmd["button"], cmdText))
        button.grid(row=row, column=0, sticky="ew", padx=2, pady=2)
        
        if "tooltip" in cmd:
            ToolTip(button, cmd["tooltip"])
            ToolTip(cmdText, cmd["tooltip"])
        
    def buildGUI(self):
        self.root = Tk()
        self.root.title(self.title)
        self.root.grid_columnconfigure(1, weight=1)
        row = 0
        for cmd in self.cmds:
            self.root.grid_rowconfigure(row, pad=2)
            self.makeCmdButton(self.root, cmd, row)
            row += 1
        
    def execute(self, label, cmdWidget):
        print("\nRunning {}:".format(label))
        subprocess.call(cmdWidget.get(), shell=True)
        print("=" * 80)
        
    def run(self, args=None):
        self.parseCmdLine()
        self.readCmds()
        self.buildGUI()
        
        self.root.mainloop()
        

#----------------------------------------------------------------------------
if __name__ == '__main__':
    app = RunnerApp()
    app.run()
    sys.exit(0)

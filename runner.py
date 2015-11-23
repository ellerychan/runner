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
#----------------------------------------------------------------------------
from __future__ import print_function, division

import sys
import subprocess
import os.path
import json
from argparse import ArgumentParser
from Tkinter import Tk, Button, Entry, Label, Menu, Toplevel, END, BOTH
from idlelib.ToolTip import ToolTip

from FileMenu import FileMenu


#----------------------------------------------------------------------------
class RunnerNamePopup(Toplevel):
    def __init__(self, parent):
        """ Create and display the popup """
        Toplevel.__init__(self, parent)
        self.transient(parent)
        
        self.parent = parent
        self.name = None
        
        self.title("Button Name")
        Label(self, text="Name:").grid(row=0, column=0, sticky="e")

        self.entry = Entry(self)
        self.entry.grid(row=0, column=1, sticky="we", padx=5)

        button = Button(self, text="OK", command=self.ok)
        button.grid(row=1, column=0, columnspan=2, pady=5)

    def ok(self):
        """ Retrieve the text input and destroy the window """
        self.name = self.entry.get()
        self.destroy()
        
    def show(self):
        """ Display the window and get user input.
            Return the input value, or None if the window is cancelled.
        """
        self.entry.focus_set()  # set focus to text area so user can type immediately
        self.parent.wait_window(self)
        return self.name

#----------------------------------------------------------------------------
class RunnerFileMenu(FileMenu):
    def __init__(self, menubar, **kwargs):
        FileMenu.__init__(self, menubar, **kwargs)
        self.onModifiedCB = None
        self.saveToFileCB = None
        self.onExitCB     = None
    
    def saveToFile(self, path):
        if self.saveToFileCB:
            return self.saveToFileCB(path)
    
    def onModifiedChange(self):
        if self.onModifiedCB:
            self.onModifiedCB(self.isModified)
    
    def onExit(self):
        if FileMenu.onExit(self):
            if self.onExitCB:
                self.onExitCB()
        

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
        self.fileMenu = None
        
    @property
    def isModified(self):
        return self.fileMenu.isModified
    
    @isModified.setter
    def isModified(self, value):
        self.fileMenu.setModified(value)
    
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
        
    def setTitle(self):
        self.root.title("{}: {}{}".format(self.title, os.path.basename(self.args.commandFile), " *" if self.isModified else ""))
    
    def onModified(self, isModified):
        self.setTitle()
        
    def addMenuBar(self):
        """ Attaches a Menu to the root window """
        menubar = Menu(self.root)
        self.root.config(menu=menubar)
        
        self.fileMenu = RunnerFileMenu(menubar, tearoff=False)
        menubar.add_cascade(label="File", menu=self.fileMenu)
        self.fileMenu.onModifiedCB = self.onModified
        self.fileMenu.saveToFileCB = self.saveToFile
        self.fileMenu.onExitCB     = self.onExit
        self.fileMenu.currFile = self.args.commandFile
        
        editMenu = Menu(menubar, tearoff=False)
#         editMenu.add_command(label="Preferences...", command=self.onEditPreferences)
        menubar.add_cascade(label="Edit", menu=editMenu)
        
        actionMenu = Menu(menubar, tearoff=False)
        actionMenu.add_command(label="Add Button", command=self.onAddButton)
        menubar.add_cascade(label="Actions", menu=actionMenu)
        
        menubar.add_command(label=" + ", command=self.onAddButton, foreground="red")
    
    def onAddButton(self):
        name = RunnerNamePopup(self.root).show()
        if name is None:
            return
        
        cmd = {
            "button":  name,
            "cmd":     "new stuff",
            "tooltip": "just added"
        }
        self.cmds.append(cmd)

        self.makeCmdButton(self.root, cmd, self.row)
        self.row += 1
        self.isModified = True
    
    def saveToFile(self, path):
        data = {
                "title": self.title,
                "width": self.cmdWidth,
                "cmds" : self.cmds,
               }
        with open(path, "w") as f:
            json.dump(data, f, indent=True)
        return True
        
    def buildGUI(self):
        self.root = Tk()
        self.addMenuBar()
        self.setTitle()

        self.root.grid_columnconfigure(1, weight=1)
        self.row = 0
        for cmd in self.cmds:
            self.root.grid_rowconfigure(self.row, pad=2)
            self.makeCmdButton(self.root, cmd, self.row)
            self.row += 1
            
        self.root.bind("<Control-s>", lambda e: self.fileMenu.onFileSave())
        self.root.protocol("WM_DELETE_WINDOW", self.fileMenu.onExit)

    def onExit(self):
        self.root.destroy()

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

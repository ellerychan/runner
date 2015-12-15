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
from Tkinter import Tk, Frame, Button, Entry, Label, Menu, Toplevel, END, DISABLED, NORMAL
from idlelib.ToolTip import ToolTip

from FileMenu import FileMenu


#----------------------------------------------------------------------------
class RunnerPopup(Toplevel):
    def __init__(self, parent, label="Text:", title="Enter Text", initialText=None, width=20, allowCancel=False):
        """ Create and display the popup """
        Toplevel.__init__(self, parent)
        self.transient(parent)

        
        self.parent = parent
        self.name = None
        self.columnconfigure(1, weight=1)
        
        self.title(title)
        Label(self, text=label).grid(row=0, column=0, sticky="e")

        self.entry = Entry(self, width=width)
        self.entry.grid(row=0, column=1, sticky="we", padx=5)
        
        if initialText:
            self.entry.delete(0, END)
            self.entry.insert(0, initialText)

        if allowCancel:
            frame = Frame(self)
            frame.grid(row=1, column=0, columnspan=2, sticky="we")
            frame.columnconfigure(0, weight=1)
            frame.columnconfigure(1, weight=1)
            button = Button(frame, text=" OK ", command=self.ok)
            button.grid(row=0, column=0, pady=5, sticky="ew")
            button = Button(frame, text="Cancel", command=self.cancel)
            button.grid(row=0, column=1, pady=5, sticky="we")
        else:
            button = Button(self, text="OK", command=self.ok)
            button.grid(row=1, column=0, columnspan=2, pady=5)

        self.entry.bind("<Return>", func=self.ok)
        self.entry.bind("<Escape>", func=self.cancel)

        px = parent.winfo_rootx()
        py = parent.winfo_rooty()
        pw = parent.winfo_width()
        ph = parent.winfo_height()
        self.update()
        ww = self.winfo_width()
        wh = self.winfo_height()
        geom = "+%d+%d" % (px+pw//2-ww//2,py+ph//2-wh//2)
        self.geometry(geom)
        
    def ok(self, event=None):
        """ Retrieve the text input and destroy the window """
        self.name = self.entry.get()
        self.destroy()
    
    def cancel(self, event=None):
        """ Destroy the window and set self.name to None """
        self.name = None
        self.destroy()
        
    def show(self):
        """ Display the window and get user input.
            Return the input value, or None if the window is cancelled.
        """
        self.entry.focus_set()  # set focus to text area so user can type immediately
        self.parent.wait_window(self)
        return self.name

#----------------------------------------------------------------------------
class RunnerNamePopup(RunnerPopup):
    def __init__(self, parent, allowCancel=False):
        RunnerPopup.__init__(self, parent, label="Name:", title="Button Name", allowCancel=allowCancel)
        
#----------------------------------------------------------------------------
class RunnerToolTipPopup(RunnerPopup):
    def __init__(self, parent, initialText=None):
        RunnerPopup.__init__(self, parent, label="ToolTip Text:", title="Enter ToolTip", initialText=initialText, width=len(initialText))
        
#----------------------------------------------------------------------------
class RunnerFileMenu(FileMenu):
    def __init__(self, menubar, **kwargs):
        FileMenu.__init__(self, menubar, **kwargs)
        self.onModifiedCB = None
        self.onFileOpenCB = None
        self.onRevertCB   = None
        self.saveToFileCB = None
        self.onExitCB     = None
        
    def onFileOpen(self, path=None):
        """ Calls FileMenu.onFileOpen() to:
                Save a modified file if needed.
                Get a pathname if None was specified.
                Return True if successful or False if the operation was cancelled.
            Then, if FileMenu.onFileOpen() was not cancelled, self.onFileOpenCB()
            is called with the new path and the return value of self.onFileOpenCB()
            is returned.  Otherwise, True is returned.
            If FileMenu.onFileOpen() was cancelled, False is returned.
        """
        if FileMenu.onFileOpen(self, path):
            if self.onFileOpenCB:
                return self.onFileOpenCB(path)
            else:
                return True
        return False
    
    def onRevert(self):
        if self.onRevertCB:
            return self.onRevertCB()
        else:
            return False
    
    def saveToFile(self, path):
        if self.saveToFileCB:
            return self.saveToFileCB(path)
        else:
            return False
    
    def onModifiedChange(self):
        if self.onModifiedCB:
            self.onModifiedCB(self.isModified)
    
    def onExit(self):
        if FileMenu.onExit(self):
            if self.onExitCB:
                self.onExitCB()

#----------------------------------------------------------------------------
class CmdWidget(object):
    updateCB = None
    
    def __init__(self, parent, cmd, row, cmdWidth=80, added=False):
        #Frame.__init__(self, parent)
        self.parent = parent
        self.cmd = cmd
        self.row = row
        self.disabled = False
        self.added = added  # new widget, not from a file
        
        self.cmdText = Entry(parent, width=cmdWidth)
        self.cmdText.grid(row=self.row, column=1, sticky="ew", ipady=2)
        self.cmdText.delete(0, END)
        self.cmdText.insert(0, self.cmd["cmd"])
        self.cmdText.parent = self
        self.cmdText.bind("<Button-3>", func=self.popup)  # attach popup to canvas

        self.button = Button(parent, text=self.cmd["button"], command=self.execute)
        self.button.grid(row=self.row, column=0, sticky="ew", padx=2, pady=2)
        self.button.bind("<Button-3>", func=self.popup)  # attach popup to canvas

        self.menu = Menu(self.button, tearoff=False, postcommand=self.onPopup)
        self.menu.add_command(label="Delete", command=self.delete)
        self.menu.add_command(label="Revert", command=self.revert)
        self.menu.add_command(label="Rename", command=self.rename)
        self.menu.add_command(label="Edit ToolTip", command=self.editToolTip)
        
        self.buttonTT = None
        self.cmdTextTT = None
        if "tooltip" in self.cmd:
            self.setToolTip(self.cmd["tooltip"])
            
        # Attach an event callback that gets called after the Entry field is updated
        bindtags = list(self.cmdText.bindtags())
        bindtags.insert(2, "PostInsert") # index 1 is where most default bindings live
        self.cmdText.bindtags(tuple(bindtags))
        self.cmdText.bind_class("PostInsert", "<Key>", self.updateButton)
    
    def setToolTip(self, tooltipText):
        self.buttonTT = ToolTip(self.button, tooltipText)
        self.cmdTextTT = ToolTip(self.cmdText, tooltipText)
        
    def onPopup(self):
        self.menu.entryconfig(0, label="Undelete" if self.disabled else "Delete")
            
    def popup(self, event):
        """ Display the popup menu (right-mouse menu) """
        self.menu.post(event.x_root, event.y_root)
            
    def isModified(self):
#         if self.cmd["cmd"] != self.cmdText.get():
#         print(self.cmd["cmd"] + " != " + self.cmdText.get())
        return self.cmd["cmd"] != self.cmdText.get().strip() or \
               self.cmd["button"] != self.button["text"].rstrip("*").strip() or \
               self.cmd["tooltip"] != self.buttonTT.text.strip() or \
               self.cmd["tooltip"] != self.cmdTextTT.text.strip() or \
               self.disabled or \
               self.added
    
    def commit(self):
        """ Copy widget fields to self.cmd fields.
            This is done right before saving the cmds to a file.
        """
        self.cmd["button"] = self.button["text"].rstrip("*").strip()
        self.cmd["cmd"] = self.cmdText.get().strip()
        self.cmd["tooltip"] = self.buttonTT.text.strip()
        self.cmdText.delete(0, END)
        self.cmdText.insert(0, self.cmd["cmd"])
        self.setToolTip(self.cmd["tooltip"])
        self.added = False
        self.updateButton()
        
    def revert(self):
        self.disabled = False
        self.cmdText.config(state=NORMAL)
        self.button.config(state=NORMAL)
        self.button.config(text=self.cmd["button"])
        self.cmdText.delete(0, END)
        self.cmdText.insert(0, self.cmd["cmd"])
        self.setToolTip(self.cmd["tooltip"])
        self.updateButton()

    def delete(self):
        if self.disabled:
            self.disabled = False
            self.cmdText.config(state=NORMAL)
            self.button.config(state=NORMAL)
        else:
            self.disabled = True
            self.cmdText.config(state=DISABLED)
            self.button.config(state=DISABLED)
#         self.optionsButton.config(hide=True)
        self.updateButton()

    def rename(self):
        """ Change the button text """
        name = RunnerNamePopup(self.parent.winfo_toplevel(), allowCancel=True).show()
        if name:
            self.button["text"] = name
        self.updateButton()
        
    def editToolTip(self):
        tooltip = RunnerToolTipPopup(self.parent.winfo_toplevel(), initialText=self.buttonTT.text).show()
        if tooltip is None:
            return
        self.setToolTip(tooltip)
        self.updateButton()
        
    def updateButton(self, event=None):
        """ Call this to update the modified state of the button and the app """
        if event:
            widget = event.widget.parent
        else:
            widget = self
        widget.button.config(text=(widget.button["text"].rstrip("*")+("*" if widget.isModified() else "")))
        if self.updateCB:
            self.updateCB()
        
    def execute(self):
        print("\nRunning {}:".format(self.cmd["button"]))
        subprocess.call(self.cmdText.get(), shell=True)
        print("=" * 80)
        
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
        self.widgets  = []
        self.quit     = False
        self.cmdFile = None
        
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
        
        self.title = os.path.splitext(os.path.basename(sys.argv[0]))[0].capitalize()

    def onFileOpen(self, path=None):
        """ Called by the fileMenu.onFileOpen method """
        if path:
            self.fileMenu.currFile = path
        if self.fileMenu.currFile and os.path.exists(self.fileMenu.currFile):
            self.cmdFile = self.fileMenu.currFile
            self.onExit(quit=False)
    
    def loadCmds(self):
        self.cmds = []
        if self.cmdFile and os.path.exists(self.cmdFile):
            self.readCmds()
            for cmd in self.cmds:
                self.addWidget(cmd)
        
    def readCmds(self):
        self.title = os.path.splitext(os.path.basename(self.cmdFile))[0]
        with open(self.cmdFile, "r") as f:
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

    
#     def makeCmdButton(self, parent, cmd, row):
#         cmdText = Entry(parent, width=self.cmdWidth)
#         cmdText.grid(row=row, column=1, sticky="ew", ipady=2)
#         cmdText.delete(0, END)
#         cmdText.insert(0, cmd["cmd"])
# 
#         button = Button(parent, text=cmd["button"], command=lambda: self.execute(cmd["button"], cmdText))
#         button.grid(row=row, column=0, sticky="ew", padx=2, pady=2)
#         
#         if "tooltip" in cmd:
#             ToolTip(button, cmd["tooltip"])
#             ToolTip(cmdText, cmd["tooltip"])
        
    def setTitle(self):
        self.root.title("{}: {}{}".format(self.title, os.path.basename(self.cmdFile), " *" if self.isModified else ""))
    
    def onModified(self, isModified):
        self.setTitle()
    
    def onRevert(self):
        for w in self.widgets:
            if w.added:
                w.delete()
            else:
                w.revert()
        self.isModified = False
        return True
    
    def onUpdate(self):
        """ Check whether any widget is modified, and set the isModified flag accordingly """
        for w in self.widgets:
            if w.isModified():
                self.isModified = True
                return
        self.isModified = False
        
    def addMenuBar(self):
        """ Attaches a Menu to the root window """
        menubar = Menu(self.root)
        self.root.config(menu=menubar)
        
        self.fileMenu = RunnerFileMenu(menubar, tearoff=False)
        menubar.add_cascade(label="File", menu=self.fileMenu)
        self.fileMenu.onModifiedCB = self.onModified
        self.fileMenu.onRevertCB   = self.onRevert
        self.fileMenu.onFileOpenCB = lambda f: self.onFileOpen(f)
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
            "cmd":     "",
            "tooltip": name
        }
        self.cmds.append(cmd)

#         self.makeCmdButton(self.root, cmd, self.row)
#         self.row += 1
        w = self.addWidget(cmd)
        w.updateButton()
        self.isModified = True
    
    def widgetCmds(self):
        widgetData = []
        for w in self.widgets:
            widgetData.append(w.cmd)
        return widgetData
    
    def saveToFile(self, path):
        for w in self.widgets:
            w.commit()
            
        data = {
                "title": self.title,
                "width": self.cmdWidth,
                "cmds" : self.widgetCmds(),
               }
        with open(path, "w") as f:
            json.dump(data, f, indent=True)
        return True
    
    def addWidget(self, cmd):
        """ Add a widget to the root frame at the specified row.
            The CmdWidget occupies one row and two columns of the grid.
        """
        w = CmdWidget(self.root, cmd, self.row, added=True)
        self.row += 1
        self.widgets.append(w)
        return w
        
    def buildGUI(self):
        self.root = Tk()
        self.addMenuBar()
        self.setTitle()

        self.root.grid_columnconfigure(1, weight=1)
        self.row = 0
            
        CmdWidget.updateCB = self.onUpdate
        self.root.bind("<Control-s>", lambda e: self.fileMenu.onFileSave())
        self.root.protocol("WM_DELETE_WINDOW", self.fileMenu.onExit)

    def onExit(self, quit=True):
        self.quit = quit
        self.root.destroy()

    def run(self, args=None):
        self.parseCmdLine()
        self.cmdFile = self.args.commandFile
        firstTime = True
        
        while not self.quit:
#         self.readCmds()
            if firstTime or (self.cmdFile and os.path.exists(self.cmdFile)):
                self.buildGUI()
                #self.onFileOpen(self.args.commandFile)
                self.loadCmds()
                #self.cmdFile = None
                
                self.root.mainloop()
                firstTime = False
        

#----------------------------------------------------------------------------
if __name__ == '__main__':
    app = RunnerApp()
    app.run()
    sys.exit(0)

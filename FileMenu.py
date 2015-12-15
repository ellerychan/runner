#!/usr/bin/python
#
#   File: FileMenu.py
# Author: Ellery Chan
#  Email: ellery@precisionlightworks.com
#   Date: Nov 19, 2015
#
# Copyright (c) 2015 Precision Lightworks, LLC.  All rights reserved.
#----------------------------------------------------------------------------
from __future__ import print_function, division

from Tkinter import Menu
import tkMessageBox
import tkFileDialog
import os.path

#----------------------------------------------------------------------------
class FileMenu(Menu):
    """ Base class for a file menu that has the common entries New, Open, Save, Save As, Export, and Exit """
    def __init__(self, menubar, **kwargs):
        """ Constructor """
        Menu.__init__(self, menubar, **kwargs)
        
        self.add_command(label="New", command=self.onFileNew)
        self.add_command(label="Open...", command=self.onFileOpen)
        self.add_command(label="Revert", command=self.onRevert)
        self.add_command(label="Save", command=self.onFileSave)
        self.add_command(label="Save As...", command=self.onFileSaveAs)
        self.add_command(label="Export...", command=self.onFileExport)
        self.add_separator()
        self.add_command(label="Exit", command=self.onExit)
        
        self._isModified = False
        self.currFile = None
        self.fileTypes = [('JSON files', '*.json'), ('All files', '*')]
        self.defaultExt = "json"
        self.exportFileTypes = [('PDF files', '*.pdf'), ("Markdown files", "*.md"), ('All files', '*')]
    
    @property
    def isModified(self):
        return self._isModified
    
    @isModified.setter
    def isModified(self, value):
        self.setModified(value)
        
    def setModified(self, value):
        """ Set the _isModified flag to value, and call self.onModifiedChange() """
        if self._isModified != value:
            self._isModified = value
            self.onModifiedChange()
    
    def onModifiedChange(self):
        """ Called when self._isModified is changed.
            Subclass should override this.
        """
        pass
    
    def askSave(self):
        """ Ask if the current file should be saved, then do as requested.
            Returns True to proceed, and False if the user wants to cancel.
        """
        resp = tkMessageBox.askyesnocancel(title="Save Modified File?", message="The current file is modified.\n\nClick Yes    to Save it.\nClick No    to discard changes.\nClick Cancel to resume editing the current file.")
        # Returns True, False, or None
        if resp is None:
            return False
        if resp:
            self.onFileSave()
        return True
        
    def onFileNew(self):
        """ Return False if the operation was cancelled. """
        if self.isModified:
            if not self.askSave():
                return False
        
        self.setModified(False)
        self.currFile = None
        return True

    def onFileOpen(self, path=None):
        """ Save a modified file if needed.
            Get a pathname if None was specified.
            Return True if successful or False if the operation was cancelled.
        """
        if self.isModified:
            if not self.askSave():
                return False
        
        # self.isModified is False at this point
        
        if path is None:  # Interactive file open
#             ftypes = [('JSON files', '*.json'), ('All files', '*')]
            path = tkFileDialog.askopenfilename(filetypes=self.fileTypes, defaultextension=self.defaultExt)
            
        if path:
            self.currFile = path
        return path and len(path)

    def onRevert(self):
        """ Reset to the initial state of the opened file """
        return True
    
    def onFileSave(self):
        """ Return False if the operation was cancelled. """
        if self.isModified:
            if not self.currFile:# or not os.path.exists(self.qaFile):
                if not self.onFileSaveAs():
                    return False
            else:
                if not self.saveToFile(self.currFile):
                    return False
            self.setModified(False)
        return True
    
    def onFileSaveAs(self):
        """ Request a filename from the user and save the file to that name.
            Note:  does not force an extension like the standard Windows save dialog
            Return False if the operation was cancelled.
        """
        saveDir = os.path.dirname(self.currFile) if self.currFile else None
        path = tkFileDialog.asksaveasfilename(filetypes=self.fileTypes, initialdir=saveDir)
        if path:
            if self.saveToFile(path):
                self.currFile = path
                self.setModified(False)
                return True
        return False
    
    def saveToFile(self, path):
        """ Save <something> to the specified file path.
            Subclass should override the default behavior.
            Return True on success.
        """
        return False
    
    def onFileExport(self):
        """ Request a filename from the user and export data to that name.
            Note:  does not force an extension like the standard Windows save dialog
            Return False if the operation  was cancelled.
        """
        path = tkFileDialog.asksaveasfilename(filetypes=self.exportFileTypes)
        if path:
            return self.exportToFile(path)
        return False
    
    def exportToFile(self, path):
        """ Export <something> to the specified file path.
            Subclass should override the default behavior.
            Return True on success.
        """
        return False
    
    def onExit(self):
        """ Subclass should override this method """
        if self.isModified:
            return self.askSave()
        else:
            return True
        
#----------------------------------------------------------------------------
if __name__ == "__main__":
    import sys
    import unittest
    
    class FileMenuTestCase(unittest.TestCase):
        def testInit(self):
            pass
        
#         def testEq(self):
#             obj = FileMenu()
#             self.assertEqual(obj, 42)
    
    unittest.main()  # run the unit tests
    sys.exit(0)

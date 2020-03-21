
# -*- mode: python ; coding: utf-8 -*-
#
# License: GNU AGPL, version 3 or later;
# http://www.gnu.org/copyleft/agpl.html
"""
Anki2 add-on to download card's fields with audio from Cambridge Dictionary

"""

import os
from PyQt5.QtGui import QIcon, QFont
from PyQt5.QtWidgets import * 
from PyQt5 import QtCore
#QAction, QMenu, QDialog, QVBoxLayout, QLabel, QLineEdit, QGridLayout,
#QDialogButtonBox, QCheckBox, QMessageBox

from aqt import mw
from aqt.utils import tooltip
from anki.hooks import addHook

#from .processors import processor
from .Cambridge import CDDownloader

from ._names import *
from .utils import *


icons_dir = os.path.join(mw.pm.addonFolder(), 'downloadaudio', 'icons')


#from .download_entry import DownloadEntry, Action
#from .get_fields import get_note_fields, get_side_fields
#from .language import language_code_from_card, language_code_from_editor
#from .review_gui import review_entries
#from .update_gui import update_data
# DOWNLOAD_SIDE_SHORTCUT = "t"
# DOWNLOAD_MANUAL_SHORTCUT = "Ctrl+t"
# Place were we keep our megaphone icon.
class LinkDialogue(QDialog):
    """
    A Dialog to let the user edit the texts or change the language.
    """
    def __init__(self, parent=None):
        self.user_url = ''
        self.word = ''
        QDialog.__init__(self)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
        self.initUI()

    def initUI(self):
        u"""Build the dialog box."""

        self.setWindowTitle(_(u'Anki – Download definitions'))
        self.setWindowIcon(QIcon(":/icons/anki.png"))
        layout = QVBoxLayout()
        self.setLayout(layout)
        self.edit_word_head = QLabel()

        self.edit_word_head.setText(_('''<h4>Enter link for parsing</h4>'''))
        bold_font = QFont()
        bold_font.setBold(True)
        self.edit_word_head.setFont(bold_font)
        layout.addWidget(self.edit_word_head)
        
        self.link_editor = QLineEdit()
        self.link_editor.placeholderText = 'Enter your link here'
        layout.addWidget(self.link_editor)

        dialog_buttons = QDialogButtonBox(self)
        dialog_buttons.addButton(QDialogButtonBox.Cancel)
        dialog_buttons.addButton(QDialogButtonBox.Ok)
        dialog_buttons.accepted.connect(self.get_word_definitions_from_link)
        dialog_buttons.rejected.connect(self.reject)
        layout.addWidget(dialog_buttons)
        self.link_editor.setFocus()

    def get_word_definitions_from_link(self):

        self.user_url = self.link_editor.text()
        if not self.user_url:
            QMessageBox.warning(mw,'Link is not provided','Please, provide a link for you word or phrase.')
            return

        downloader = mw.cddownloader
        downloader.clean_up()
        downloader.user_url = self.user_url
        downloader.get_word_defs()        
        self.setResult(QDialog.Accepted)
        self.done(QDialog.Accepted)


class WordDefDialogue(QDialog):
    """
    A Dialog to let the user to choose defs to be added.
    """
    def __init__(self,word_data,word):
        self.word_data = word_data
        self.word = word
        self.selected_defs = [] # list of selected defs (l1_word)
        self.deletion_mark = False
        self.l2_def = None
        self.single_word = False
        self.set_model()
        QDialog.__init__(self)
        self.initUI()


    def initUI(self):
        u"""Build the dialog box."""

        self.setWindowTitle(self.word)
        self.setWindowIcon(QIcon(":/icons/anki.png"))
        layout = QVBoxLayout()
        self.setLayout(layout)   
        # Looping through data structure
        for l1_word in self.word_data:
            row = 0
            gl = QGridLayout()
            gr = QGroupBox()
            gr.setLayout(gl)
            word_title = QLabel('<h3>' + l1_word['word_title'] + '</h3>')
            gl.addWidget(word_title,row,0)
            word_gram = QLabel('<h4>' + l1_word['word_gram'] + '</h4>')
            gl.addWidget(word_gram,row,1)
            #Looping through top-level meaning
            ck_it = 0
            self.ck_dict = {}
            for l2_meaning, l2_def_and_example in l1_word['meanings'].items():
                row += 1
                #mean_checkbox = QCheckBox(l2_meaning.upper())
                #mean_checkbox.l2_meaning = l2_meaning
                #mean_checkbox.stateChanged.connect(self.toggle_def)
                #ck_it += 1
                #gl.addWidget(mean_checkbox, row, 0,1,-1)
                for l2_def in l2_def_and_example:

                #for l2_def in l2_def_and_example:
                    row += 1
                    l2_def_check = QCheckBox(l2_def)
                    l2_def_check.l2_def = l2_def
                    l2_def_check.stateChanged.connect(self.toggle_def)
                    gl.addWidget(l2_def_check, row, 0,1,-1)
                    #for l2_examp in l2_def_and_example[l2_def]:
                    #    row += 1
                    #    l2_def_label = QLabel('<i>'+l2_examp+'</i>')
                    #    l2_def_label.setIndent(10)
                    #    gl.addWidget(l2_def_label, row, 0,1,-1)
                    self.l2_def = l2_def
            layout.addWidget(gr)

        dialog_buttons = QDialogButtonBox(self)
        dialog_buttons.addButton(QDialogButtonBox.Cancel)
        dialog_buttons.addButton(QDialogButtonBox.Ok)
        dialog_buttons.accepted.connect(self.create_selected_notes)
        dialog_buttons.rejected.connect(self.reject)
        layout.addWidget(dialog_buttons)

        # Automatic add single word with single def if in add_single mode
        if len(self.word_data) == 1:
            self.selected_defs.append(self.l2_def)
            self.create_selected_notes()
            self.single_word = True

    def toggle_def(self,state):
        sender = self.sender()
        l2_def = sender.l2_def
        if self.sender():
            if l2_def in self.selected_defs:
                self.selected_defs.remove(l2_def)
            else:
                self.selected_defs.append(l2_def)


    def create_selected_notes(self):

        if not self.selected_defs:
            mw.cddownloader.clean_up()
            self.word_data = None
            self.word = None
            self.selected_defs = [] # list of selected defs (l1_word)
            return

        word_to_add = self.word_data
        for next_def in self.selected_defs:
            for l1_word in self.word_data:
                for l2_key, l2_value in l1_word['meanings'].items():
                    for l3_specific_def, l3_examples in l2_value.items():
                        if l3_specific_def == next_def:
                            word_to_save = {}
                            word_to_save['word_title'] = l1_word['word_title']
                            word_to_save['word_gram'] = l1_word['word_gram']
                            word_to_save['word_pro_uk'] = l1_word['word_pro_uk']
                            word_to_save['word_uk_media'] = l1_word['word_uk_media']
                            word_to_save['word_pro_us'] = l1_word['word_pro_us']
                            word_to_save['word_us_media'] = l1_word['word_us_media']
                            word_to_save['word_general'] = l2_key
                            word_to_save['word_specific'] = l3_specific_def
                            word_to_save['word_examples'] = "<br> ".join(l3_examples)
                            word_to_save['word_image'] = l1_word['word_image']
                            self.add_note(word_to_save)
                            
        #for sel_def in self.selected_defs:
        #    if self.word_data[sel_def]:
        #mw.cddownloader.clean_up()
        #self.close(QDialog.Accepted)
        self.deletion_mark = True
        self.done(0)
        
       
    def set_model(self):
        self.model = prepare_model(mw.col, fields, styles.model_css)


    def add_note(self, word_to_add):
        """
        Note is an SQLite object in Anki so you need
        to fill it out inside the main thread

        """
        word = {}
        word['Word'] = word_to_add['word_title'] 
        word['Grammar'] = word_to_add['word_gram']
        word['Pronunciation'] = word_to_add['word_pro_uk'] + ' ' + word_to_add['word_pro_us']
        word['Meaning'] = word_to_add['word_general'] if not 'UNDEFINED' in word_to_add['word_general'] else ''
        word['Definition'] = word_to_add['word_specific']
        word['Examples'] = word_to_add['word_examples']
        word['Sounds'] = [word_to_add['word_uk_media'],word_to_add['word_us_media']]
        word['Picture'] = word_to_add['word_image']

        add_word(word, self.model)


class AddonConfigWindow(QDialog):
    """
    A Dialog to let the user to choose defs to be added.
    """
    def __init__(self):
        self.config = get_config()
        QDialog.__init__(self)
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Cambridge Addon Settings')
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Authorize and save cookies - Google OAuth2
        # Some useful varibale go here
        auth_layout = QHBoxLayout()
        auth_label = QLabel()
        auth_label.setText('Auorization status:')
        auth_layout.addWidget(auth_label)
        auth_label_status = QLabel()
        auth_label_status.setText('Unknown')
        auth_layout.addWidget(auth_label_status)
        auth_btn = QPushButton()
        auth_btn.setText('Authorize via Google')
        auth_btn.clicked.connect(self.btn_auth_clicked)
        auth_layout.addWidget(auth_btn)
        layout.addLayout(auth_layout)        

        # Cookie - for semi authorization
        h_layout = QHBoxLayout()
        h_label = QLabel()
        h_label.setText('Cookie:')
        h_layout.addWidget(h_label)
        h_layout.addStretch()        
        self.ledit_cookie = QLineEdit()
        self.ledit_cookie.setText(self.config['cookie'] if self.config['cookie'] else '')
        h_layout.addWidget(self.ledit_cookie,QtCore.Qt.AlignRight)
        layout.addLayout(h_layout,QtCore.Qt.AlignTop)

        # Stretcher
        layout.addStretch()

        # Bottom buttons - Ok, Cancel
        btn_bottom_layout = QHBoxLayout()
        btn_bottom_layout.addStretch()        
        btn_Ok = QPushButton()
        btn_Ok.setText('Ok')
        btn_bottom_layout.addWidget(btn_Ok,QtCore.Qt.AlignRight)
        btn_Cancel = QPushButton()
        btn_Cancel.setText('Cancel')
        btn_bottom_layout.addWidget(btn_Cancel,QtCore.Qt.AlignRight)
        layout.addLayout(btn_bottom_layout)
        btn_Ok.clicked.connect(self.btn_Ok)
        btn_Cancel.clicked.connect(self.close)
        

    def btn_auth_clicked(self):
        QMessageBox.information(self,'Auth','Auth')

    def btn_Ok(self):
        # Fill config dict with current settings and write them to file
        self.config['cookie'] = self.ledit_cookie.text()
        update_config(self.config)
        self.close()

    def btn_Cancel(self):
        self.close()


class WordListLinkDialogue(QDialog):
    """
    A Dialog to let the user enter link for word list.
    """
    def __init__(self, parent=None):
        self.user_url = ''
        QDialog.__init__(self)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
        self.initUI()

    def initUI(self):
        u"""Build the dialog box."""

        self.setWindowTitle(_(u'Anki – Word list link'))
        self.setWindowIcon(QIcon(":/icons/anki.png"))
        layout = QVBoxLayout()
        self.setLayout(layout)
        self.edit_word_head = QLabel()

        self.edit_word_head.setText(_('''<h4>Enter link for parsing</h4>'''))
        bold_font = QFont()
        bold_font.setBold(True)
        self.edit_word_head.setFont(bold_font)
        layout.addWidget(self.edit_word_head)
        
        self.link_editor = QLineEdit()
        self.link_editor.placeholderText = 'Enter your link here'
        layout.addWidget(self.link_editor)
        # Options
        self.ck_skip_multidef_words = QCheckBox('Skip milti-def words')
        layout.addWidget(self.ck_skip_multidef_words)

        dialog_buttons = QDialogButtonBox(self)
        dialog_buttons.addButton(QDialogButtonBox.Cancel)
        dialog_buttons.addButton(QDialogButtonBox.Ok)
        dialog_buttons.accepted.connect(self.parse_word_list_from_link)
        dialog_buttons.rejected.connect(self.reject)
        layout.addWidget(dialog_buttons)
        self.link_editor.setFocus()

    def parse_word_list_from_link(self):

        self.user_url = self.link_editor.text()
        if not self.user_url:
            QMessageBox.warning(mw,'Link is not provided','Please, provide a link for you word list')
            return

        downloader = mw.cddownloader
        all_words_in_list = downloader.get_all_words_in_list(self.user_url)
        if all_words_in_list:
            for cur_word in all_words_in_list:
                downloader.clean_up()
                downloader.user_url = cur_word['ref']
                downloader.word_id = cur_word['word_id']
                downloader.get_word_defs()
                if downloader.word_data:
                    sd = WordDefDialogue(downloader.word_data,downloader.word)
                    if sd.single_word:
                        downloader.delete_word_from_wordlist()
                        continue
                    if self.ck_skip_multidef_words.checkState() == QtCore.Qt.Checked:
                        continue
                    sd.exec_()
                    if sd.deletion_mark:
                        downloader.delete_word_from_wordlist()
            self.close()
                        

        self.setResult(QDialog.Accepted)
        self.done(QDialog.Accepted)

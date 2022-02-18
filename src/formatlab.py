import json
import os
import pathlib
import shutil
import sys
import time
import webbrowser
from copy import deepcopy
from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5.QtCore import QUrl, QSettings, QProcess
from PyQt5.QtGui import QDesktopServices, QIcon, QPixmap, QFont
from PyQt5.QtWidgets import QMainWindow, QApplication, QMessageBox, QFileDialog, QStyle, QCheckBox, \
    QGraphicsScene, QGraphicsPixmapItem, QGraphicsView
from account_threads import SaveLocalInToken, RefreshButtonThread, SyncAccountIdWithDb
from accounts import get_user_data_from_local, days_left, ApplicationStartupTask, check_for_local_token
from helper import check_internet_connection, check_default_location, \
    get_local_download_data, save_after_delete, \
    get_downloaded_data_filter, get_initial_download_dir, get_valid_video_file, \
    get_valid_audio_file, set_style_for_pause_play_button
from constant import AFTER_PLAYBACK, FREQUENCY_MAPPER, AFTER_PLAYBACK_REVERSE, QUALITY_MAP, AUDIO_CHANNELS_MAPPING
from system_monitor import RamThread, NetSpeedThread, CpuThread, DummyDataThread
from formatlab_threads import ProcessVideo, \
    ConvertVideo, ProcessAudio, ConvertAudio
from app_settings import AppSettings
from gui.main_functions import MainFunctions
from gui.ui_main import Ui_main_window

os.environ["QT_FONT_DPI"] = "100"

PRODUCT_NAME = "FORMAT_LAB"
THEME_PATH = '/snap/formatlab/current/'


class MainWindow(QMainWindow):
    def __init__(self):
        QMainWindow.__init__(self)
        self.ui = Ui_main_window()
        self.ui.setupUi(self)
        MainFunctions.setup_widgets(self)
        self.app_setting_ui = AppSettings()
        self.theme = open(THEME_PATH + 'dark.qss', 'r').read()
        self.setStyleSheet(self.theme)
        self.app_setting_ui.setStyleSheet(self.theme)
        self.setWindowTitle("Format Lab Pro")
        self.settings = QSettings("warlordsoft", "formatlab")
        self.tip_count = -1
        self.pytube_status = True
        self.ui.purchase_details.setEnabled(False)
        self.is_plan_active = True
        self.delete_source_file = True
        self.one_time_congratulate = True
        self.same_as_source = ["Same As Source"]

        #  App settings init ==========================================================================================
        self.Default_loc_import = get_initial_download_dir()
        self.system_frequency = 1
        self.speed_unit = "MB/s | KB/s | B/s"
        self.temp_unit = "°C  (Celsius)"
        self.default_frequency()
        self.after_playback_action = "loop_play"
        self.speed = "0.0"
        self.unit = "B/s"
        self.file_dialog = 'native'
        self.mpv_arguments = []
        self.Default_loc_video = get_initial_download_dir()
        self.Default_loc_audio = get_initial_download_dir()
        self.app_setting_ui.ui.download_path_edit_2.setText(self.Default_loc_video + "/FORMAT_LAB")
        self.app_setting_ui.ui.download_path_edit_playlist.setText(self.Default_loc_audio + "/FORMAT_LAB")
        self.ui.video_progressBar.setFixedHeight(2)
        self.ui.playlist_progressBar.setFixedHeight(2)
        self.hide_show_video_initial_banner(show=False)
        self.hide_show_playlist_initial_banner(show=False)
        self.ui.progress_bar.setFixedHeight(17)
        self.ui.account_progress_bar.setFixedHeight(2)
        self.ui.progress_bar.setFont(QFont('Ubuntu', 11))
        self.ui.stackedWidget.setCurrentIndex(0)
        self.hide_show_play_pause_button(hide=True)
        self.pause = False
        self.load_settings()
        self.show()

        # Home page ================================================================
        self.ui.copy_id.clicked.connect(
            lambda x: QApplication.clipboard().setText(self.ui.lineEdit_account_id_2.text()))
        self.ui.info_suggestion.clicked.connect(self.suggestion_info_popup)
        self.info_suggestion_count = 0
        self.ui.stack_downloads.clicked.connect(self.show_downloads_page)
        self.ui.stack_net_speed.clicked.connect(self.show_net_speed)
        self.ui.stack_accounts.clicked.connect(self.account_page)
        self.ui.stack_about.clicked.connect(self.about_page)
        self.ui.pause_button.clicked.connect(self.pause_button_pressed)
        self.ui.delete_button.clicked.connect(self.trigger_delete_action)
        self.ui.select_format_obj_2.currentTextChanged.connect(self.check_for_audio_only)

        # Video functionality ======================================================
        self.ui.stack_add_video.clicked.connect(self.add_video_method)
        self.ui.download_button_2.clicked.connect(self.download_action_video)
        self.ui.play_from_videos.clicked.connect(self.play_video_from_videos_tab)
        self.ui.horizontalSlider_video_quality.valueChanged.connect(self.change_label_video_quality)

        # Audio functionality ======================================================
        self.ui.stack_add_audio.clicked.connect(self.add_audio_method)
        self.ui.play_from_playlist.clicked.connect(self.play_audio)
        self.ui.download_button_playlist_2.clicked.connect(self.download_action_audio)

        # App settings =================================================================
        self.app_setting_ui.ui.close.clicked.connect(self.click_ok_button)
        self.app_setting_ui.ui.reset_default.clicked.connect(self.app_settings_defaults)
        self.app_setting_ui.ui.after_playback.currentIndexChanged.connect(self.select_after_playback_action)
        self.app_setting_ui.ui.download_path_button_2.clicked.connect(self.open_download_path)
        self.app_setting_ui.ui.download_path_button_playlist.clicked.connect(self.open_download_path_playlist)
        self.app_setting_ui.ui.native_dialog.clicked.connect(self.set_file_dialog)
        self.app_setting_ui.ui.qt_dialog.clicked.connect(self.set_file_dialog)
        self.app_setting_ui.ui.change_import.clicked.connect(self.change_import_path)

        # Downloads functionality ======================================================
        self.downloaded_file_filter = "all_files"
        self.ui.filter_by.currentIndexChanged.connect(self.set_file_downloaded_filter)
        self.download_search_map_list = []
        self.ui.open_videos.clicked.connect(self.show_downloads_folder)
        self.ui.play_video.clicked.connect(self.play_videos_from_downloads)
        self.ui.play_video_mpv.clicked.connect(self.play_videos_mpv_from_downloads)
        self.ui.details_video.clicked.connect(self.details_video_from_downloads)
        self.ui.delete_videos.clicked.connect(self.delete_video_from_downloads)
        self.ui.listWidget.itemDoubleClicked.connect(self.play_videos_mpv_from_downloads)
        self.ui.search_videos.textChanged.connect(self.search_videos)
        self.ui.search_videos.cursorPositionChanged.connect(self.clear_search_bar_on_edit)
        self.ui.clear_history.clicked.connect(self.clear_all_history)

        # net speed settings
        self.ui.horizontalSlider_freq.valueChanged.connect(self.change_frequency_net)
        self.ui.comboBox_speed_unit.currentIndexChanged.connect(self.change_net_speed_unit)
        self.ui.comboBox_cpu_temp.currentIndexChanged.connect(self.change_temp_unit)

        # Accounts/About functionality ======================================================
        # ApplicationStartupTask(PRODUCT_NAME).create_free_trial_offline()
        # self.ui.error_message.clear()
        # self.ui.error_message.setStyleSheet("color:red;")
        # self.my_plan()
        # self.sync_account_id_with_warlord_soft()
        self.ui.warlordsoft_button.clicked.connect(self.redirect_to_warlordsoft)
        self.ui.donate_button.clicked.connect(self.redirect_to_paypal_donation)
        self.ui.rate_button.clicked.connect(self.redirect_to_rate_snapstore)
        self.ui.feedback_button.clicked.connect(self.redirect_to_feedback_button)
        # self.ui.purchase_licence_2.clicked.connect(self.purchase_licence_2)
        # self.ui.refresh_account_2.clicked.connect(self.refresh_account_2)
        self.ui.ge_more_apps.clicked.connect(self.ge_more_apps)
        # self.ui.purchase_details.clicked.connect(self.purchase_details_after_payment)

        # thing temperory remoed after premium ========================== to remove later!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        self.ui.stack_accounts.setVisible(False) # remove later
        self.account.setVisible(False) # remove later

        # scroll zoom functionality: =======================================================
        self.factor = 1
        self.setAcceptDrops(True)
        self._zoom = 0
        self._empty = False
        self._scene = QGraphicsScene(self)
        self._photo = QGraphicsPixmapItem()
        self._scene.addItem(self._photo)
        self.ui.graphicsView_video.setScene(self._scene)
        self.ui.graphicsView_video.scale(2, 2)
        self.ui.graphicsView_video.setVisible(False)
        self._zoom_playlist = 0
        self._empty_playlist = False
        self._scene_playlist = QGraphicsScene(self)
        self._photo_playlist = QGraphicsPixmapItem()
        self._scene_playlist.addItem(self._photo_playlist)
        self.ui.graphicsView_playlist.setScene(self._scene_playlist)
        self.ui.graphicsView_playlist.scale(2, 2)
        self.ui.graphicsView_playlist.setVisible(False)

    def change_import_path(self):
        folder_loc = QFileDialog.getExistingDirectory(self, "Select Import Directory",
                                                      self.Default_loc_import,
                                                      QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks)
        if folder_loc:
            if check_default_location(folder_loc):
                self.app_setting_ui.ui.import_path.setText(folder_loc)
                self.Default_loc_import = folder_loc
            else:
                self.popup_message(title="Import Path Invalid",
                                   message="Import Path Must Inside Home Directory or Home")
                return False

        self.app_setting_ui.setWindowState(
            self.app_setting_ui.windowState() & ~QtCore.Qt.WindowMinimized | QtCore.Qt.WindowActive)

    def set_file_dialog(self):
        if self.app_setting_ui.ui.native_dialog.isChecked():
            self.file_dialog = 'native'
            self.app_setting_ui.ui.native_dialog.setChecked(True)
        elif self.app_setting_ui.ui.qt_dialog.isChecked():
            self.file_dialog = 'qt'
            self.app_setting_ui.ui.qt_dialog.setChecked(True)
        else:
            self.file_dialog = 'native'

    def check_for_audio_only(self):
        display_text = str(self.ui.select_format_obj_2.currentText())
        if display_text != "":
            if display_text.split("-")[-1].strip() == "AUDIO":
                self.ui.select_fps_obj_2.setEnabled(False)
                self.ui.select_quality_obj_2.setEnabled(False)
                self.ui.select_audio_birtare_in_video.setEnabled(True)
                self.ui.horizontalSlider_video_quality.setEnabled(False)
            else:
                self.ui.select_fps_obj_2.setEnabled(True)
                self.ui.select_quality_obj_2.setEnabled(True)
                self.ui.select_audio_birtare_in_video.setEnabled(False)
                self.ui.horizontalSlider_video_quality.setEnabled(True)

    def change_label_video_quality(self):
        self.ui.video_quality_label.setText(
            f"Video Quality ("f"{QUALITY_MAP.get(10 - self.ui.horizontalSlider_video_quality.value() + 1)})")

    def play_video_from_videos_tab(self):
        try:
            if self.ui.select_format_obj_2.currentText() != "Select Format":
                self.ui.video_progressBar.setRange(0, 0)
                self.process = QProcess()
                self.process.readyReadStandardOutput.connect(self.handle_stdout_from_videos)
                self.mpv_arguments = []
                if self.after_playback_action == "loop_play":
                    self.mpv_arguments.append("--loop")
                self.mpv_arguments.append("--force-window")
                self.mpv_arguments.append(self.video_path)
                self.mpv_arguments.append("--title={0}".format(self.video_show_title))
                self.mpv_arguments.append("--gpu-context=x11")
                self.process.start("mpv", self.mpv_arguments)
            else:
                self.popup_message(title="No Video File To Watch!",
                                   message="Please Add Files From Your PC")
        except Exception as e:
            self.ui.video_progressBar.setRange(0, 1)
            print(e)

    def handle_stdout_from_videos(self):
        try:
            self.ui.video_progressBar.setRange(0, 1)
        except Exception as e:
            print(e)

    def add_video_method(self):
        try:
            is_running = self.convert_pdf_thread.isRunning()
        except Exception as e:
            is_running = False

        try:
            is_running_pixmap = self.pixmap_load_thread.isRunning()
        except Exception as e:
            is_running_pixmap = False

        if is_running or is_running_pixmap:
            self.popup_message(title="Task Already In Queue", message="Please wait for the Running task to finish!")
        else:
            if self.file_dialog == "native":
                self.load_video, _ = QFileDialog.getOpenFileName(self, 'Select Video', self.Default_loc_import,
                                                                 "All files (*.*)")
            else:
                options = QFileDialog.Options()
                options |= QFileDialog.DontUseNativeDialog
                self.load_video, _ = QFileDialog.getOpenFileName(self, 'Select Video', self.Default_loc_import,
                                                                 "All files (*.*)",
                                                                 options=options)
            if len(self.load_video) == 0:
                return False

            self.load_video, invalid_file = get_valid_video_file(self.load_video)

            if invalid_file:
                self.popup_message(title="Invalid Video File Format!\n\nPlease Select Valid Video File Format!",
                                   message=f"File: {self.load_video}  is Invalid Video File Format.")
            else:
                self.convert_video()

    def play_audio(self):
        try:
            if self.ui.select_quality_audio.currentText() != "Select Format":
                self.ui.playlist_progressBar.setRange(0, 0)
                self.process = QProcess()
                self.process.readyReadStandardOutput.connect(self.handle_stdout_from_audio)
                self.mpv_arguments = []
                if self.after_playback_action == "loop_play":
                    self.mpv_arguments.append("--loop")
                self.mpv_arguments.append("--force-window")
                self.mpv_arguments.append(self.audio_path)
                self.mpv_arguments.append("--title={0}".format(self.audio_show_title))
                self.mpv_arguments.append("--gpu-context=x11")
                self.process.start("mpv", self.mpv_arguments)
            else:
                self.popup_message(title="No Audio File To Play!",
                                   message="Please Add Files From Your PC")
        except Exception as e:
            self.ui.playlist_progressBar.setRange(0, 1)
            print(e)

    def handle_stdout_from_audio(self):
        try:
            self.ui.playlist_progressBar.setRange(0, 1)
        except Exception as e:
            print(e)

    def add_audio_method(self):
        try:
            is_running = self.convert_pdf_thread.isRunning()
        except Exception as e:
            is_running = False

        try:
            is_running_pixmap = self.pixmap_load_thread.isRunning()
        except Exception as e:
            is_running_pixmap = False

        if is_running or is_running_pixmap:
            self.popup_message(title="Task Already In Queue", message="Please wait for the Running task to finish!")
        else:
            if self.file_dialog == "native":
                self.load_audio, _ = QFileDialog.getOpenFileName(self, 'Select Audio', self.Default_loc_import,
                                                                 "All files (*.*)")
            else:
                options = QFileDialog.Options()
                options |= QFileDialog.DontUseNativeDialog
                self.load_audio, _ = QFileDialog.getOpenFileName(self, 'Select Audio', self.Default_loc_import,
                                                                 "All files (*.*)",
                                                                 options=options)
            if len(self.load_audio) == 0:
                return False

            self.load_audio, invalid_file = get_valid_audio_file(self.load_audio)

            print(self.load_audio)

            if invalid_file:
                self.popup_message(title="Invalid Audio File Format!\n\nPlease Select Valid Audio File Format!",
                                   message=f"File: {self.load_audio}  is Invalid Audio File Format.")
            else:
                self.convert_audio()

    def show_downloads_page(self):
        MainFunctions.reset_selection(self)
        self.ui.stackedWidget.setCurrentIndex(3)
        self.get_user_download_data()
        self.downloads.set_active(True)

    def home_page(self):
        self.ui.stackedWidget.setCurrentIndex(0)
        MainFunctions.reset_selection(self)
        self.home_btn.set_active(True)

    # graphic view

    def setPhoto(self, pixmap=None):
        self._zoom = 0
        if pixmap and not pixmap.isNull():
            self._empty = False
            self.ui.graphicsView_video.setDragMode(QGraphicsView.ScrollHandDrag)
            self._photo.setPixmap(pixmap)
        else:
            self._empty = True
            self.ui.graphicsView_video.setDragMode(QGraphicsView.NoDrag)
            self._photo.setPixmap(QPixmap())
        self.fitInView()

    def setPhoto_playlist(self, pixmap=None):
        self._zoom_playlist = 0
        if pixmap and not pixmap.isNull():
            self._empty_playlist = False
            self.ui.graphicsView_playlist.setDragMode(QGraphicsView.ScrollHandDrag)
            self._photo_playlist.setPixmap(pixmap)
        else:
            self._empty_playlist = True
            self.ui.graphicsView_playlist.setDragMode(QGraphicsView.NoDrag)
            self._photo_playlist.setPixmap(QPixmap())
        self.fitInView_playlist()

    def fitInView(self, scale=True):
        try:
            rect = QtCore.QRectF(self._photo.pixmap().rect())
            if not rect.isNull():
                self.ui.graphicsView_video.setSceneRect(rect)
                if self.hasPhoto():
                    unity = self.ui.graphicsView_video.transform().mapRect(QtCore.QRectF(0, 0, 1, 1))
                    self.ui.graphicsView_video.scale(1 / unity.width(), 1 / unity.height())
                    viewrect = self.ui.graphicsView_video.viewport().rect()
                    scenerect = self.ui.graphicsView_video.transform().mapRect(rect)
                    factor = min(viewrect.width() / scenerect.width(),
                                 viewrect.height() / scenerect.height())
                    self.ui.graphicsView_video.scale(factor, factor)
                self._zoom = 0
        except Exception as e:
            pass

    def fitInView_playlist(self, scale=True):
        try:
            rect = QtCore.QRectF(self._photo_playlist.pixmap().rect())
            if not rect.isNull():
                self.ui.graphicsView_playlist.setSceneRect(rect)
                if self.hasPhoto_playlist():
                    unity = self.ui.graphicsView_playlist.transform().mapRect(QtCore.QRectF(0, 0, 1, 1))
                    self.ui.graphicsView_playlist.scale(1 / unity.width(), 1 / unity.height())
                    viewrect = self.ui.graphicsView_playlist.viewport().rect()
                    scenerect = self.ui.graphicsView_playlist.transform().mapRect(rect)
                    factor = min(viewrect.width() / scenerect.width(),
                                 viewrect.height() / scenerect.height())
                    self.ui.graphicsView_playlist.scale(factor, factor)
                self._zoom_playlist = 0
        except Exception as e:
            pass

    def hasPhoto(self):
        return not self._empty

    def hasPhoto_playlist(self):
        return not self._empty_playlist

    def hide_show_video_initial_banner(self, show=True):
        if show:
            for i in range(self.ui.gridLayout_5.count() - 1, -1, -1):
                items = self.ui.gridLayout_5.itemAt(i).widget()
                if items:
                    items.setVisible(True)
        else:
            for i in range(self.ui.gridLayout_5.count() - 1, -1, -1):
                items = self.ui.gridLayout_5.itemAt(i).widget()
                if items:
                    items.setVisible(False)

    def hide_show_playlist_initial_banner(self, show=True):
        if show:
            for i in range(self.ui.gridLayout_8.count() - 1, -1, -1):
                items = self.ui.gridLayout_8.itemAt(i).widget()
                if items:
                    items.setVisible(True)
        else:
            for i in range(self.ui.gridLayout_8.count() - 1, -1, -1):
                items = self.ui.gridLayout_8.itemAt(i).widget()
                if items:
                    items.setVisible(False)

    def hide_show_download_initial_banner(self, show=True):
        if show:
            self.ui.listWidget.setVisible(True)
            self.ui.label_26.setVisible(False)
        else:
            self.ui.listWidget.setVisible(False)
            self.ui.label_26.setVisible(True)

    def suggestion_info_popup(self, message=None):
        self.msg = QMessageBox()
        self.msg.setWindowFlag(QtCore.Qt.FramelessWindowHint)
        self.msg.setStyleSheet("background-color:#263a4e;color:#eaeaea;")
        self.msg.setIcon(QMessageBox.Information)
        self.msg.setText("FORMAT_LAB Tips and Tricks!")
        if message:
            self.msg.setInformativeText(message)
        else:
            self.msg.setInformativeText(
                "Please rate the app in AppStore and send us your feedback about the app or request any new feature. "
                "mail us: contact@warlordsoftwares.in")
        close = self.msg.addButton(QMessageBox.Yes)
        next_tip = self.msg.addButton(QMessageBox.Yes)
        prev_tip = self.msg.addButton(QMessageBox.Yes)
        next_tip.setText('Next Tip')
        prev_tip.setText('Previous Tip')
        close.setText('Close')
        next_tip.setIcon(QIcon(QApplication.style().standardIcon(QStyle.SP_ArrowRight)))
        prev_tip.setIcon(QIcon(QApplication.style().standardIcon(QStyle.SP_ArrowLeft)))
        close.setIcon(QIcon(QApplication.style().standardIcon(QStyle.SP_BrowserStop)))
        self.msg.exec_()
        message_list = [
            "Higher the video/audio quality and FPS, More will be the output size of the file.",
            "Webm video format does not support video quality option.",
            "Same as source option is best suitable when you are not sure about the input operations",
            "Mpv stream player Keyboard shortcuts:\n\nQ :   Stop and Quit Player\nF :   "
            "Toggle Fullscreen\nP :  Pause / Playback\n9 and 0 :    Volume Control\nW and E :"
            "   ZoomIn/ZoomOut\nShift+A :    Screen Aspect Ratio\nArrow Keys :   Seek 5 seconds.",
            "If you like this app, support the developer by donating, Thanks.",
        ]
        try:
            if self.msg.clickedButton() == next_tip:
                if self.tip_count <= 3:
                    self.tip_count += 1
                    self.suggestion_info_popup(message_list[self.tip_count])
                else:
                    self.tip_count = 0
                    self.suggestion_info_popup(message_list[self.tip_count])
            elif self.msg.clickedButton() == prev_tip:
                if self.tip_count >= 1:
                    self.tip_count -= 1
                    self.suggestion_info_popup(message_list[self.tip_count])
                else:
                    self.tip_count = 4
                    self.suggestion_info_popup(message_list[self.tip_count])
            elif self.msg.clickedButton() == close:
                pass
        except Exception as e:
            pass

    def click_ok_button(self):
        self.app_setting_ui.hide()
        self.home_page()

    def select_after_playback_action(self):
        self.after_playback_action = AFTER_PLAYBACK.get(self.app_setting_ui.ui.after_playback.currentText(),
                                                        "loop_play")

    def app_settings_defaults(self):
        self.msg = QMessageBox()
        self.msg.setWindowFlag(QtCore.Qt.FramelessWindowHint)
        self.msg.setStyleSheet("background-color:#263a4e;color:#eaeaea;")
        self.msg.setIcon(QMessageBox.Information)
        self.msg.setText("Are you sure want to reset to default settings?")
        yes_button = self.msg.addButton(QMessageBox.Yes)
        no_button = self.msg.addButton(QMessageBox.No)
        self.msg.exec_()
        if self.msg.clickedButton() == yes_button:
            #  yt setting defaults
            self.app_setting_ui.ui.after_playback.setCurrentIndex(0)
            self.after_playback_action = "loop_play"
            self.Default_loc_video = get_initial_download_dir()
            self.Default_loc_audio = get_initial_download_dir()
            self.app_setting_ui.ui.download_path_edit_2.setText(self.Default_loc_video + "/FORMAT_LAB")
            self.app_setting_ui.ui.download_path_edit_playlist.setText(self.Default_loc_audio + "/FORMAT_LAB")
            self.Default_loc_import = get_initial_download_dir()
            self.file_dialog = 'native'
            #  file dialog defaults
            if self.file_dialog == "native":
                self.app_setting_ui.ui.native_dialog.setChecked(True)
                self.app_setting_ui.ui.qt_dialog.setChecked(False)
            elif self.file_dialog == "qt":
                self.app_setting_ui.ui.native_dialog.setChecked(False)
                self.app_setting_ui.ui.qt_dialog.setChecked(True)
            else:
                self.app_setting_ui.ui.native_dialog.setChecked(True)
                self.app_setting_ui.ui.qt_dialog.setChecked(False)

            #  Import defaults
            self.app_setting_ui.ui.import_path.setText(self.Default_loc_import)

        if self.msg.clickedButton() == no_button:
            pass

    def open_yt_setting_page(self):
        self.app_setting_ui.show()
        self.app_setting_ui.raise_()
        self.app_setting_ui.activateWindow()

    def show_net_speed(self):
        MainFunctions.reset_selection(self)
        self.ui.stackedWidget.setCurrentIndex(4)
        self.system_monitor.set_active(True)
        try:
            dummy_data_thread = self.dummy_data_thread.isRunning()
        except Exception:
            dummy_data_thread = False
        try:
            cpu_thread = self.cpu_thread.isRunning()
        except Exception:
            cpu_thread = False
        try:
            ram_thread = self.ram_thread.isRunning()
        except Exception:
            ram_thread = False
        try:
            net_speed_thread = self.net_speed_thread.isRunning()
        except Exception:
            net_speed_thread = False
        if not dummy_data_thread:
            self.load_annimation_data()
        if not cpu_thread:
            self.start_cpu_thread()
        if not ram_thread:
            self.start_ram_thread()
        if not net_speed_thread:
            self.start_net_speed_thread()

    def default_frequency(self):
        self.ui.horizontalSlider_freq.setValue(4)
        self.ui.frequency_label.setText("1.0 Sec")

    def change_net_speed_unit(self):
        self.speed_unit = self.ui.comboBox_speed_unit.currentText()
        try:
            dummy_data_thread = self.dummy_data_thread.isRunning()
        except Exception:
            dummy_data_thread = False
        if not dummy_data_thread:
            self.load_annimation_data()
        try:
            self.net_speed_thread.terminate()
            self.start_net_speed_thread()
        except Exception as e:
            pass

    def change_temp_unit(self):
        self.temp_unit = self.ui.comboBox_cpu_temp.currentText()
        try:
            dummy_data_thread = self.dummy_data_thread.isRunning()
        except Exception:
            dummy_data_thread = False
        if not dummy_data_thread:
            self.load_annimation_data()
        try:
            self.cpu_thread.terminate()
            self.start_cpu_thread()
        except Exception as e:
            pass

    def change_frequency_net(self):
        self.system_frequency = FREQUENCY_MAPPER.get(self.ui.horizontalSlider_freq.value(), 4)
        self.ui.frequency_label.setText(str(self.system_frequency) + " Sec")
        try:
            dummy_data_thread = self.dummy_data_thread.isRunning()
        except Exception:
            dummy_data_thread = False
        if not dummy_data_thread:
            self.load_annimation_data()
        try:
            self.net_speed_thread.terminate()
            self.start_net_speed_thread()
        except Exception as e:
            pass
        try:
            self.cpu_thread.terminate()
            self.start_cpu_thread()
        except Exception as e:
            pass
        try:
            self.ram_thread.terminate()
            self.start_ram_thread()
        except Exception as e:
            pass

    def start_cpu_thread(self):
        self.cpu_thread = CpuThread(self.system_frequency, self.temp_unit, self)
        self.cpu_thread.change_value.connect(self.setProgress_cpu)
        self.cpu_thread.start()

    def start_ram_thread(self):
        self.ram_thread = RamThread(self.system_frequency, self)
        self.ram_thread.change_value.connect(self.setProgress_ram)
        self.ram_thread.start()

    def start_net_speed_thread(self):
        self.net_speed_thread = NetSpeedThread(self.system_frequency, self.speed_unit, self)
        self.net_speed_thread.change_value.connect(self.setProgress_net_speed)
        self.net_speed_thread.start()

    def load_annimation_data(self):
        self.dummy_data_thread = DummyDataThread(self)
        self.dummy_data_thread.change_value.connect(self.setProgress_dummy_data)
        self.dummy_data_thread.start()

    def setProgress_cpu(self, value):
        self.ui.cpu_usage_3.setText(value[0])
        self.ui.cpu_temp_3.setText(value[1])

    def setProgress_ram(self, value):
        self.ui.ram_usage_3.setText(value[0])
        self.ui.ram_total_3.setText(value[1])
        self.ui.ram_free_3.setText(value[2])

    def setProgress_net_speed(self, value):
        self.ui.internet_speed_3.setText(value[0][0])
        self.ui.internet_unit_3.setText(value[0][1])
        self.ui.internet_connection_3.setText(value[1])
        self.speed = value[0][0]
        self.unit = value[0][1]

    def setProgress_dummy_data(self, value):
        self.ui.cpu_usage_3.setText(value[0])
        self.ui.ram_usage_3.setText(value[0])
        self.ui.internet_speed_3.setText(value[1])

    def closeEvent(self, event):
        self.save_settings()
        self.app_setting_ui.hide()
        super().closeEvent(event)

    def save_settings(self):
        self.settings.setValue("delete_source_file_check", self.delete_source_file)
        self.settings.setValue("net_speed_unit", self.ui.comboBox_speed_unit.currentText())
        self.settings.setValue("system_frequency", self.ui.horizontalSlider_freq.value())
        self.settings.setValue("cpu_temp_unit", self.ui.comboBox_cpu_temp.currentText())
        #  one time congratulate
        self.settings.setValue("one_time_congratulate", self.one_time_congratulate)
        # save window state
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("windowState", self.saveState())
        # save formatlab settings
        self.settings.setValue("after_playback_action",
                               AFTER_PLAYBACK.get(self.app_setting_ui.ui.after_playback.currentText(), "loop_play"))
        self.settings.setValue("file_dialog", self.file_dialog)
        self.settings.setValue("Default_loc_import", self.Default_loc_import)
        self.settings.setValue("default_loc_video", self.Default_loc_video)
        self.settings.setValue("default_loc_audio", self.Default_loc_audio)

    def load_settings(self):
        if self.settings.contains("delete_source_file_check"):
            self.delete_source_file = json.loads(self.settings.value("delete_source_file_check").lower())
        if self.settings.contains("net_speed_unit"):
            self.speed_unit = self.settings.value("net_speed_unit")
            self.ui.comboBox_speed_unit.setCurrentText(self.speed_unit)
        if self.settings.contains("system_frequency"):
            self.system_frequency = FREQUENCY_MAPPER.get(int(self.settings.value("system_frequency")), 4)
            self.ui.horizontalSlider_freq.setValue(int(self.settings.value("system_frequency")))
            self.ui.frequency_label.setText(
                str(FREQUENCY_MAPPER.get(int(self.settings.value("system_frequency")), "1.0")) + " Sec")
        if self.settings.contains("cpu_temp_unit"):
            self.temp_unit = self.settings.value("cpu_temp_unit")
            self.ui.comboBox_cpu_temp.setCurrentText(self.temp_unit)

        #  one time congratulate
        if self.settings.contains("one_time_congratulate"):
            self.one_time_congratulate = json.loads(self.settings.value("one_time_congratulate"))

        # load window state
        if self.settings.contains("geometry"):
            self.restoreGeometry(self.settings.value("geometry"))
        if self.settings.contains("windowState"):
            self.restoreState(self.settings.value("windowState", ""))

        #  formatlab settings load
        if self.settings.contains("default_loc_video"):
            self.Default_loc_video = self.settings.value("default_loc_video")
            self.app_setting_ui.ui.download_path_edit_2.setText(self.Default_loc_video + "/FORMAT_LAB")
        if self.settings.contains("default_loc_audio"):
            self.Default_loc_audio = self.settings.value("default_loc_audio")
            self.app_setting_ui.ui.download_path_edit_playlist.setText(self.Default_loc_audio + "/FORMAT_LAB")
        if self.settings.contains("after_playback_action"):
            self.after_playback_action = self.settings.value("after_playback_action")
            self.app_setting_ui.ui.after_playback.setCurrentText(
                AFTER_PLAYBACK_REVERSE.get(self.after_playback_action, "Loop Play"))
        if self.settings.contains("file_dialog"):
            self.file_dialog = self.settings.value("file_dialog")
        if self.settings.contains("Default_loc_import"):
            self.Default_loc_import = self.settings.value("Default_loc_import")

        # loads defaults===================================================:
        if self.file_dialog == "native":
            self.app_setting_ui.ui.native_dialog.setChecked(True)
            self.app_setting_ui.ui.qt_dialog.setChecked(False)
        elif self.file_dialog == "qt":
            self.app_setting_ui.ui.native_dialog.setChecked(False)
            self.app_setting_ui.ui.qt_dialog.setChecked(True)
        else:
            self.app_setting_ui.ui.native_dialog.setChecked(True)
            self.app_setting_ui.ui.qt_dialog.setChecked(False)

        self.app_setting_ui.ui.import_path.setText(self.Default_loc_import)

    def file_download_success_dialog(self, title, folder_path, play_path):
        self.msg = QMessageBox()
        self.msg.setWindowFlag(QtCore.Qt.FramelessWindowHint)
        self.msg.setStyleSheet("background-color:#263a4e;color:#eaeaea;")
        self.msg.setIcon(QMessageBox.Information)
        self.msg.setText(title)
        self.msg.setInformativeText("")
        close = self.msg.addButton(QMessageBox.Yes)
        show_in_downloads = self.msg.addButton(QMessageBox.Yes)
        play = self.msg.addButton(QMessageBox.Yes)
        mpv_play = self.msg.addButton(QMessageBox.Yes)
        open_folder = self.msg.addButton(QMessageBox.Yes)
        open_folder.setText('Open Folder')
        show_in_downloads.setText('Show Downloads')
        play.setText('Play')
        mpv_play.setText('MPV Play')
        close.setText('Close')
        play.setIcon(QIcon(QApplication.style().standardIcon(QStyle.SP_MediaPlay)))
        mpv_play.setIcon(QIcon(QApplication.style().standardIcon(QStyle.SP_MediaPlay)))
        close.setIcon(QIcon(QApplication.style().standardIcon(QStyle.SP_BrowserStop)))
        open_folder.setIcon(QIcon(QApplication.style().standardIcon(QStyle.SP_DirIcon)))
        show_in_downloads.setIcon(QIcon(QApplication.style().standardIcon(QStyle.SP_DirOpenIcon)))
        self.msg.exec_()
        try:
            if self.msg.clickedButton() == open_folder:
                print(folder_path)
                QDesktopServices.openUrl(QUrl.fromLocalFile(folder_path))
            elif self.msg.clickedButton() == play:
                print(play_path)
                QDesktopServices.openUrl(QUrl.fromLocalFile(play_path))
            elif self.msg.clickedButton() == mpv_play:
                self.process = QProcess()
                self.mpv_arguments = []
                if self.after_playback_action == "loop_play":
                    self.mpv_arguments.append("--loop")
                self.mpv_arguments.append("--force-window")
                self.mpv_arguments.append(play_path)
                self.mpv_arguments.append("--title={0}".format(str(title).replace("Convert Success\n\n", "")
                                                               .replace("File Already Exists!\n\n", "")))
                self.mpv_arguments.append("--gpu-context=x11")
                self.process.start("mpv", self.mpv_arguments)
            elif self.msg.clickedButton() == show_in_downloads:
                self.show_downloads_page()
            elif self.msg.clickedButton() == close:
                pass
        except Exception as e:
            pass

    def pause_button_pressed(self):
        try:
            convert_video_thread = self.convert_video_thread.isRunning()
        except Exception as e:
            convert_video_thread = False
        try:
            convert_audio_thread = self.convert_audio_thread.isRunning()
        except Exception as e:
            convert_audio_thread = False

        if convert_video_thread:
            if self.pause:
                self.convert_video_thread.resume()
                set_style_for_pause_play_button(self, pause=True)
                self.pause = False
            else:
                self.convert_video_thread.pause()
                set_style_for_pause_play_button(self, pause=False)
                self.pause = True
        elif convert_audio_thread:
            if self.pause:
                self.convert_audio_thread.resume()
                set_style_for_pause_play_button(self, pause=True)
                self.pause = False
            else:
                self.convert_audio_thread.pause()
                set_style_for_pause_play_button(self, pause=False)
                self.pause = True

    def trigger_delete_action(self):
        try:
            self.msg = QMessageBox()
            self.msg.setWindowFlag(QtCore.Qt.FramelessWindowHint)
            self.msg.setStyleSheet("background-color:#263a4e;color:#eaeaea;")
            self.msg.setIcon(QMessageBox.Information)
            self.msg.setText("Are you sure want to stop on-going task?")
            yes_button = self.msg.addButton(QMessageBox.Yes)
            no_button = self.msg.addButton(QMessageBox.No)
            self.msg.exec_()
            if self.msg.clickedButton() == yes_button:
                self.delete_button_pressed()
            if self.msg.clickedButton() == no_button:
                pass
        except Exception as e:
            self.popup_message(title="Error while deleting the task!", message="", error=True)
            pass

    def delete_button_pressed(self):
        try:
            convert_video_thread = self.convert_video_thread.isRunning()
        except Exception as e:
            convert_video_thread = False
        try:
            convert_audio_thread = self.convert_audio_thread.isRunning()
        except Exception as e:
            convert_audio_thread = False

        try:
            if convert_video_thread:
                self.progress_bar_disable()
                self.pause = False
                set_style_for_pause_play_button(self, pause=True)
                self.hide_show_play_pause_button(hide=True)
                self.convert_video_thread.kill()
            elif convert_audio_thread:
                self.progress_bar_disable()
                self.pause = False
                set_style_for_pause_play_button(self, pause=True)
                self.hide_show_play_pause_button(hide=True)
                self.convert_audio_thread.kill()
        except Exception as e:
            pass

    def popup_message(self, title, message, error=False):
        self.msg = QMessageBox()
        self.msg.setWindowFlag(QtCore.Qt.FramelessWindowHint)
        self.msg.setStyleSheet("background-color:#263a4e;color:#eaeaea;")
        if error:
            self.msg.setIcon(QMessageBox.Warning)
        else:
            self.msg.setIcon(QMessageBox.Information)
        self.msg.setText(title)
        self.msg.setInformativeText(message)
        self.msg.setStandardButtons(QMessageBox.Ok)
        self.msg.exec_()

    def progress_bar_enable(self):
        self.ui.progress_bar.setRange(0, 0)

    def progress_bar_disable(self):
        self.ui.progress_bar.setRange(0, 1)

    def open_download_path(self):
        folder_loc = QFileDialog.getExistingDirectory(self, "Select Output Directory",
                                                      self.Default_loc_video,
                                                      QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks)
        if folder_loc:
            if check_default_location(folder_loc):
                self.app_setting_ui.ui.download_path_edit_2.setText(folder_loc + "/FORMAT_LAB")
                self.Default_loc_video = folder_loc
            else:
                self.popup_message(title="Download Path Invalid", message="Download Path Must Inside Home Directory")
                return False

    def open_download_path_playlist(self):
        folder_loc = QFileDialog.getExistingDirectory(self, "Select Output Directory",
                                                      self.Default_loc_audio,
                                                      QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks)
        if folder_loc:
            if check_default_location(folder_loc):
                self.app_setting_ui.ui.download_path_edit_playlist.setText(folder_loc + "/FORMAT_LAB")
                self.Default_loc_audio = folder_loc
            else:
                self.popup_message(title="Download Path Invalid", message="Download Path Must Inside Home Directory")
                return False

    def hide_show_play_pause_button(self, hide=True):
        self.ui.pause_button.setVisible(not hide)
        self.ui.delete_button.setVisible(not hide)

    def convert_video(self):
        self.ui.progress_bar.setRange(0, 0)
        self.ui.select_format_obj_2.clear()
        self.ui.select_quality_obj_2.clear()
        self.ui.select_fps_obj_2.clear()
        self.ui.select_audio_birtare_in_video.clear()
        self.process_video_thread = ProcessVideo(self.load_video, self.Default_loc_video, self)
        self.process_video_thread.meta_data_signal.connect(self.set_video_info)
        self.process_video_thread.start()

    def convert_audio(self):
        try:
            is_running = self.process_ytv_thread.isRunning()
        except Exception as e:
            is_running = False
        try:
            is_playlist_fetch_running = self.get_videos_list.isRunning()
        except Exception as e:
            is_playlist_fetch_running = False
        try:
            is_playlist_download_running = self.process_ytv_play_list_thread.isRunning()
        except Exception as e:
            is_playlist_download_running = False
        try:
            is_playlist_process = self.process_ytv_playlist_thread.isRunning()
        except Exception as e:
            is_playlist_process = False
        if not is_running and not is_playlist_fetch_running and not is_playlist_download_running and not is_playlist_process:
            self.ui.progress_bar.setRange(0, 0)

            self.ui.select_audio_birtare.clear()
            self.ui.select_quality_audio.clear()
            self.ui.select_audio_channels.clear()

            self.process_audio_thread = ProcessAudio(self.load_audio, self.Default_loc_audio, self)
            self.process_audio_thread.meta_data_signal.connect(self.set_audio_info)
            self.process_audio_thread.start()

        else:
            self.popup_message(title="Task Already In Queue",
                               message="Please wait for the Running task to finish!")

    def set_video_info(self, video_data):
        if video_data.get("status"):
            self.video_path = video_data.get("file_name")
            self.video_title = video_data.get("title")
            self.video_show_title = video_data.get("title_show")
            self.video_duration = video_data.get("duration")
            self.video_size = video_data.get("size")
            self.input_audio_bitrate = video_data.get("input_audio_bitrate")
            self.input_quality = video_data.get("quality")
            self.input_fps = video_data.get("frame")
            self.ui.video_title_5.setText(video_data.get("title_show_full"))
            self.ui.video_size.setText(self.video_size)
            self.ui.video_duration.setText(self.video_duration)
            self.hide_show_video_initial_banner(show=True)
            self.ui.video_format.setText(video_data.get("format"))
            self.ui.video_quality.setText(video_data.get("quality"))
            self.ui.video_frame.setText(f'{video_data.get("frame")} FPS')
            self.ui.descriptions.setText(video_data.get("more_info_str"))

            self.ui.textBrowser_thumbnail_9.setVisible(False)
            self.ui.graphicsView_video.setVisible(True)
            all_quality, all_format, all_fps, all_audio_bitrate = video_data.get("format_data")

            for index, item in enumerate(self.same_as_source + all_quality):
                self.ui.select_quality_obj_2.addItem(item)
                icon = QtGui.QIcon()
                icon.addPixmap(QtGui.QPixmap(":/myresource/resource/icons8-ok-144.png"), QtGui.QIcon.Normal,
                               QtGui.QIcon.Off)
                self.ui.select_quality_obj_2.setItemIcon(index, icon)

            for index, item in enumerate(self.same_as_source + all_format):
                self.ui.select_format_obj_2.addItem(item)
                icon = QtGui.QIcon()
                if index > 13:
                    icon.addPixmap(QtGui.QPixmap(":/myresource/resource/music.png"), QtGui.QIcon.Normal,
                                   QtGui.QIcon.Off)
                else:
                    icon.addPixmap(QtGui.QPixmap(":/myresource/resource/video_7.png"), QtGui.QIcon.Normal,
                                   QtGui.QIcon.Off)
                self.ui.select_format_obj_2.setItemIcon(index, icon)

            for index, item in enumerate(self.same_as_source + all_fps):
                self.ui.select_fps_obj_2.addItem(item)
                icon = QtGui.QIcon()
                icon.addPixmap(QtGui.QPixmap(":/myresource/resource/icons8-tick-box-120.png"), QtGui.QIcon.Normal,
                               QtGui.QIcon.Off)
                self.ui.select_fps_obj_2.setItemIcon(index, icon)

            for index, item in enumerate(self.same_as_source + all_audio_bitrate):
                self.ui.select_audio_birtare_in_video.addItem(item)
                icon = QtGui.QIcon()
                icon.addPixmap(QtGui.QPixmap(":/myresource/resource/icons8-music-120.png"), QtGui.QIcon.Normal,
                               QtGui.QIcon.Off)
                self.ui.select_audio_birtare_in_video.setItemIcon(index, icon)

            self.ui.select_quality_obj_2.setCurrentIndex(1)
            self.ui.select_format_obj_2.setCurrentIndex(1)
            self.ui.select_fps_obj_2.setCurrentIndex(1)
            self.ui.select_audio_birtare_in_video.setCurrentIndex(1)
            self.ui.stackedWidget.setCurrentIndex(1)
            self.setPhoto(QPixmap(video_data.get("thumbnail_path")))
            MainFunctions.reset_selection(self)
            self.video.set_active(True)
            self.ui.progress_bar.setRange(0, 1)
        else:
            self.ui.progress_bar.setRange(0, 1)
            self.popup_message(title="Invalid input file",
                               message="Please check your video format !")

    def set_audio_info(self, audio_data):
        if audio_data.get("status"):
            self.audio_path = audio_data.get("file_name")
            self.audio_title = audio_data.get("title")
            self.audio_show_title = audio_data.get("title_show")
            self.audio_duration = audio_data.get("duration")
            self.audio_size = audio_data.get("size")
            self.input_bitrate = audio_data.get("bitrate")
            self.input_channel = audio_data.get("input_channel")

            self.ui.audio_title.setText(audio_data.get("title_show_full"))
            self.ui.audio_size.setText(self.audio_size)
            self.ui.audio_duration.setText(self.audio_duration)
            self.ui.audio_bitrate.setText(f"{audio_data.get('bitrate')} Kbps")
            self.hide_show_playlist_initial_banner(show=True)
            self.ui.audio_format.setText(str(audio_data.get("format")).upper())
            self.ui.descriptions_audio.setText(audio_data.get("more_info_str"))
            self.ui.textBrowser_playlist_thumbnail.setVisible(False)
            self.ui.graphicsView_playlist.setVisible(True)
            all_format, all_bitrate, all_channels = audio_data.get("format_data")

            for index, item in enumerate(self.same_as_source + all_format):
                self.ui.select_quality_audio.addItem(item)
                icon = QtGui.QIcon()
                icon.addPixmap(QtGui.QPixmap(":/myresource/resource/icons8-ok-144.png"), QtGui.QIcon.Normal,
                               QtGui.QIcon.Off)
                self.ui.select_quality_audio.setItemIcon(index, icon)

            for index, item in enumerate(self.same_as_source + all_bitrate):
                self.ui.select_audio_birtare.addItem(item)
                icon = QtGui.QIcon()
                icon.addPixmap(QtGui.QPixmap(":/myresource/resource/music.png"), QtGui.QIcon.Normal,
                               QtGui.QIcon.Off)
                self.ui.select_audio_birtare.setItemIcon(index, icon)

            for index, item in enumerate(self.same_as_source + all_channels):
                self.ui.select_audio_channels.addItem(item)
                icon = QtGui.QIcon()
                icon.addPixmap(QtGui.QPixmap(":/myresource/resource/icons8-music-120.png"), QtGui.QIcon.Normal,
                               QtGui.QIcon.Off)
                self.ui.select_audio_channels.setItemIcon(index, icon)

            # for item in self.same_as_source + all_format:
            #     self.ui.select_quality_audio.addItem(item)
            # for item in self.same_as_source + all_bitrate:
            #     self.ui.select_audio_birtare.addItem(item)
            # for item in self.same_as_source + all_channels:
            #     self.ui.select_audio_channels.addItem(item)

            self.ui.select_audio_birtare.setCurrentIndex(1)
            self.ui.select_quality_audio.setCurrentIndex(1)
            self.ui.select_audio_channels.setCurrentIndex(2)

            self.ui.stackedWidget.setCurrentIndex(2)
            self.setPhoto_playlist(QPixmap(audio_data.get("thumbnail_path")))
            MainFunctions.reset_selection(self)
            self.playlist.set_active(True)
            self.ui.progress_bar.setRange(0, 1)
        else:
            self.ui.progress_bar.setRange(0, 1)
            self.popup_message(title="Invalid input file",
                               message="Please check your audio format !")

    def download_action_video(self):
        context = dict()
        if str(self.ui.select_quality_obj_2.currentText().lower()) != "same as source":
            context["quality"] = (str(self.ui.select_quality_obj_2.currentText()).split(" ")[0]).lower()
        else:
            context["quality"] = str(self.ui.select_quality_obj_2.currentText()).lower()

        try:
            convert_video_thread = self.convert_video_thread.isRunning()
        except Exception as e:
            convert_video_thread = False
        try:
            convert_audio_thread = self.convert_audio_thread.isRunning()
        except Exception as e:
            convert_audio_thread = False

        if convert_video_thread or convert_audio_thread:
            self.popup_message(title="Task Already In Queue", message="Please wait for the Running task to finish!")

        else:
            if context["quality"] not in ['select', '', None]:

                context["formats"] = str(self.ui.select_format_obj_2.currentText()).lower().split(" - ")[0]
                context["format_type"] = "video"

                if str(self.ui.select_format_obj_2.currentText().lower()) != "same as source":
                    if str(self.ui.select_format_obj_2.currentText()).split(" - ")[1] == "AUDIO":
                        context["format_type"] = "audio"

                print(context["format_type"])
                if str(self.ui.select_audio_birtare_in_video.currentText().lower()) != "same as source":
                    context["audio_bitrate"] = (
                        str(self.ui.select_audio_birtare_in_video.currentText()).split(" ")[0]).lower()
                else:
                    context["audio_bitrate"] = str(self.ui.select_audio_birtare_in_video.currentText()).lower()

                if context["formats"] == "webm":
                    self.popup_message("Info! WEBM Video Format Selected!", "Video quality option is not "
                                                                            "available for WEBM video format "
                                                                            "and will not be affected on "
                                                                            "the output video")
                if str(self.ui.select_fps_obj_2.currentText().lower()) != "same as source":
                    context["fps"] = str(self.ui.select_fps_obj_2.currentText()).split(" ")[0]
                else:
                    context["fps"] = str(self.ui.select_fps_obj_2.currentText()).lower()
                context["audio_video_quality"] = self.ui.horizontalSlider_video_quality.value()
                context["video_path"] = self.video_path
                context["input_format"] = str(pathlib.Path(self.video_path).suffix).replace(".", "")
                context["input_quality"] = str(self.input_quality).split(" ")[0]
                context["input_fps"] = str(self.input_fps).split(" ")[0]
                self.progress_bar_enable()
                self.ui.progress_bar.setRange(0, 100)
                context["location"] = self.Default_loc_video
                context["title"] = self.video_title
                context["show_title"] = self.video_show_title
                context["duration"] = self.video_duration
                context["size"] = self.video_size
                context["input_audio_bitrate"] = self.input_audio_bitrate
                context["main"] = self
                response = True
                if response:
                    self.convert_video_thread = ConvertVideo(context, self)
                    self.convert_video_thread.change_value.connect(self.tc_process_download_video)
                    self.convert_video_thread.finished.connect(self.tc_finished_downloading_thread_video)
                    self.convert_video_thread.error.connect(self.tc_error_on_downloading_video)
                    self.convert_video_thread.no_error.connect(self.tc_no_error_video)
                    self.convert_video_thread.after_kill.connect(self.tc_after_kill_video)
                    self.convert_video_thread.start()
            else:
                self.popup_message(title="No Audio/Video File To Convert!",
                                   message="Please Add Files From Your PC")

    def download_action_audio(self):
        context = dict()
        if str(self.ui.select_audio_birtare.currentText().lower()) != "same as source":
            context["bitrate"] = (str(self.ui.select_audio_birtare.currentText()).split(" ")[0]).lower()
        else:
            context["bitrate"] = str(self.ui.select_audio_birtare.currentText()).lower()
        try:
            convert_video_thread = self.convert_video_thread.isRunning()
        except Exception as e:
            convert_video_thread = False
        try:
            convert_audio_thread = self.convert_audio_thread.isRunning()
        except Exception as e:
            convert_audio_thread = False

        if convert_video_thread or convert_audio_thread:
            self.popup_message(title="Task Already In Queue", message="Please wait for the Running task to finish!")
        else:
            if context["bitrate"] not in ['select', '', None]:

                context["formats"] = str(self.ui.select_quality_audio.currentText()).lower()

                if str(self.ui.select_audio_channels.currentText().lower()) == "same as source":
                    context["output_channel"] = str(self.ui.select_audio_channels.currentText()).lower()
                else:
                    context["output_channel"] = AUDIO_CHANNELS_MAPPING.get(
                        str(self.ui.select_audio_channels.currentText()), "2")

                context["input_channel"] = self.input_channel

                context["input_format"] = str(pathlib.Path(self.audio_path).suffix).replace(".", "")
                context["input_bitrate"] = self.input_bitrate
                context["audio_path"] = self.audio_path
                self.progress_bar_enable()
                self.ui.progress_bar.setRange(0, 100)
                context["location"] = self.Default_loc_audio
                context["title"] = self.audio_title
                context["show_title"] = self.audio_show_title
                context["duration"] = self.audio_duration
                context["size"] = self.audio_size
                context["main"] = self
                response = True
                if response:
                    self.convert_audio_thread = ConvertAudio(context, self)
                    self.convert_audio_thread.change_value.connect(self.tc_process_download_audio)
                    self.convert_audio_thread.finished.connect(self.tc_finished_downloading_thread_audio)
                    self.convert_audio_thread.error.connect(self.tc_error_on_downloading_audio)
                    self.convert_audio_thread.no_error.connect(self.tc_no_error_audio)
                    self.convert_audio_thread.after_kill.connect(self.tc_after_kill_audio)
                    self.convert_audio_thread.start()
            else:
                self.popup_message(title="No Audio/Video File To Convert!",
                                   message="Please Add Files From Your PC")

    def tc_process_download_video(self, value_dict):
        if not value_dict.get("is_killed"):
            f_type = str(value_dict.get("type")).capitalize()
            output_format = str(value_dict.get("output_format")).capitalize()
            display_status = f'Converting {f_type} to {output_format}.. {value_dict.get("progress")}% Completed'
            self.ui.progress_bar.setRange(0, 100)
            self.ui.progress_bar.setFormat(display_status)
            self.ui.progress_bar.setValue(value_dict.get("progress"))
        else:
            self.ui.progress_bar.reset()
            self.progress_bar_disable()

    def tc_finished_downloading_thread_video(self, json_data):
        if not json_data.get("is_killed"):
            self.hide_show_play_pause_button(hide=True)
            self.progress_bar_disable()
            message = f"Convert Success\n\n{json_data.get('title')}"
            self.file_download_success_dialog(message, json_data.get("output_folder"),
                                              json_data.get("output_video_path"))

    def tc_error_on_downloading_video(self, error_dict):
        if error_dict.get("error") == "File Already Exists":
            file_path = error_dict.get("output_folder")
            play_path = error_dict.get("output_video_path")
            title = error_dict.get("title")
            message = f"File Already Exists!\n\n{title}"
            if file_path and play_path:
                self.file_download_success_dialog(message, file_path, play_path)
            else:
                self.popup_message(title="File Already Exists", message=error_dict.get("error"))
        else:
            message = "Unable to convert this input file!\n\nPlease change to another file format or report to the " \
                      "developer about it!"
            print(error_dict.get("error"))
            self.popup_message(title="Error Has Occurred!", message=message)
            self.hide_show_play_pause_button(hide=True)
            self.tc_after_kill_video(error_dict.get("output_video_path"))

    def tc_no_error_video(self, message):
        if message == "no_error":
            self.hide_show_play_pause_button(hide=False)

    def tc_after_kill_video(self, unfinished_file_path):
        try:
            self.progress_bar_disable()
            os.remove(unfinished_file_path)
        except Exception as e:
            pass

    def tc_process_download_audio(self, value_dict):
        if not value_dict.get("is_killed"):
            output_format = str(value_dict.get("output_format")).capitalize()
            display_status = f'Converting Audio to {output_format}.. {value_dict.get("progress")}% Completed'
            self.ui.progress_bar.setRange(0, 100)
            self.ui.progress_bar.setFormat(display_status)
            self.ui.progress_bar.setValue(value_dict.get("progress"))
        else:
            self.ui.progress_bar.reset()
            self.progress_bar_disable()

    def tc_finished_downloading_thread_audio(self, json_data):
        if not json_data.get("is_killed"):
            self.hide_show_play_pause_button(hide=True)
            self.progress_bar_disable()
            message = f"Convert Success\n\n{json_data.get('title')}"
            self.file_download_success_dialog(message, json_data.get("output_folder"),
                                              json_data.get("output_audio_path"))

    def tc_error_on_downloading_audio(self, error_dict):
        if error_dict.get("error") == "File Already Exists":
            file_path = error_dict.get("output_folder")
            play_path = error_dict.get("output_audio_path")
            title = error_dict.get("title")
            message = f"File Already Exists!\n\n{title}"
            if file_path and play_path:
                self.file_download_success_dialog(message, file_path, play_path)
            else:
                self.popup_message(title="File Already Exists", message=error_dict.get("error"))
        else:
            message = "Unable to convert this input file!\n\nPlease change to another file format or report to the " \
                      "developer about it!"
            print(error_dict.get("error"))
            self.popup_message(title="Error Has Occurred!", message=message)
            self.hide_show_play_pause_button(hide=True)
            self.tc_after_kill_audio(error_dict.get("output_audio_path"))

    def tc_no_error_audio(self, message):
        if message == "no_error":
            self.hide_show_play_pause_button(hide=False)

    def tc_after_kill_audio(self, unfinished_file_path):
        try:
            self.progress_bar_disable()
            os.remove(unfinished_file_path)
        except Exception as e:
            pass

    def clear_all_history(self):
        try:
            self.msg = QMessageBox()
            self.msg.setWindowFlag(QtCore.Qt.FramelessWindowHint)
            self.msg.setStyleSheet("background-color:#263a4e;color:#eaeaea;")
            self.msg.setIcon(QMessageBox.Information)
            self.msg.setText("Are you sure want to clear all videos and Audios history?")
            cb = QCheckBox("Delete all Source file too")
            cb.setChecked(self.delete_source_file)
            self.msg.setCheckBox(cb)
            yes_button = self.msg.addButton(QMessageBox.Yes)
            no_button = self.msg.addButton(QMessageBox.No)
            self.msg.exec_()
            if self.msg.clickedButton() == yes_button:
                if cb.isChecked():
                    self.delete_source_file = True
                    self.clear_download_history_all()
                else:
                    self.delete_source_file = False
                    self.clear_download_history_all()
                self.get_user_download_data()
            if self.msg.clickedButton() == no_button:
                if cb.isChecked():
                    self.delete_source_file = True
                else:
                    self.delete_source_file = False

        except Exception as e:
            self.popup_message(title="Error while deleting the file!", message="", error=True)
            pass

    def clear_download_history_all(self):
        try:
            video_history_path = self.Default_loc_video + "/FORMAT_LAB/.downloads/download_data.json"
            os.remove(video_history_path)
        except Exception as e:
            pass
        try:
            playlist_history_path = self.Default_loc_audio + "/FORMAT_LAB/.downloads/download_data.json"
            os.remove(playlist_history_path)
        except Exception as e:
            pass
        if self.delete_source_file:
            try:
                video_file_path = self.Default_loc_video + "/FORMAT_LAB"
                shutil.rmtree(video_file_path)
            except Exception as e:
                pass
            try:
                playlist_video_path = self.Default_loc_audio + "/FORMAT_LAB"
                shutil.rmtree(playlist_video_path)
            except Exception as e:
                pass

    def set_file_downloaded_filter(self):
        self.downloaded_file_filter = "_".join(str(self.ui.filter_by.currentText()).lower().split(" "))
        self.ui.search_videos.clear()
        self.download_search_map_list = []
        self.get_user_download_data()

    def get_user_download_data(self):
        try:
            self.ui.listWidget.clear()
            size = QtCore.QSize()
            size.setHeight(100)
            size.setWidth(100)
            if self.downloaded_file_filter == "all_files":
                if self.Default_loc_video == self.Default_loc_audio:
                    user_json_data = get_local_download_data(self.Default_loc_video)
                else:
                    user_json_data = get_local_download_data(self.Default_loc_video) + get_local_download_data(
                        self.Default_loc_audio)
            elif self.downloaded_file_filter in ["playlist_video", "playlist_audio"]:
                user_json_data = get_local_download_data(self.Default_loc_audio)
            else:
                user_json_data = get_local_download_data(self.Default_loc_video)
            if user_json_data:
                self.hide_show_download_initial_banner(show=True)
            else:
                self.hide_show_download_initial_banner(show=False)
            user_json_data = sorted(user_json_data, key=lambda k: k['sort_param'], reverse=True)
            exist_entry = [self.ui.listWidget.item(x).text() for x in range(self.ui.listWidget.count())]
            filter_user_json_data = get_downloaded_data_filter(user_json_data, self.downloaded_file_filter)
            for row in filter_user_json_data:
                file_type = str(row.get("type")).upper()
                thumbnail_path = row.get("thumbnail_path")
                audio_channel = row.get("audio_channel", "")
                if file_type == "AUDIO":
                    if not os.path.isfile(thumbnail_path):
                        thumbnail_path = ":/myresource/resource/audio_thumbnail.png"
                else:
                    if not os.path.isfile(thumbnail_path):
                        thumbnail_path = ":/myresource/resource/video_thumbnail.png"

                title = row.get("title_show")
                resolution = str(row.get("resolution")).upper()
                subtype = str(row.get("subtype")).upper()
                length = row.get("length")
                file_size = row.get("size")
                bitrate = row.get("bitrate", "")
                if file_type == "AUDIO":
                    details = f"{title}\n🇦​​​​​🇺​​​​​🇩​​​​​🇮​​​​​🇴​​​​​-{bitrate}Kbps-{audio_channel}-{subtype}\nSize: {file_size}\nLength: {length}"
                else:
                    details = f"{title}\n🇻​​​​​🇮​​​​​🇩​​​​​🇪​​​​​🇴​​​​​-{resolution}-{subtype}\nSize: {file_size}\nLength: {length}"

                if details not in exist_entry:
                    icon = QtGui.QIcon()
                    icon.addPixmap(QtGui.QPixmap(thumbnail_path), QtGui.QIcon.Normal, QtGui.QIcon.Off)
                    item = QtWidgets.QListWidgetItem(icon, details)
                    item.setSizeHint(size)
                    self.ui.listWidget.addItem(item)
            self.ui.listWidget.setIconSize(QtCore.QSize(150, 150))
        except Exception as e:
            self.popup_message(title="Error while getting download history!", message="", error=True)
            pass

    def show_downloads_folder(self):
        try:
            if self.downloaded_file_filter == "all_files":
                if self.Default_loc_video == self.Default_loc_audio:
                    user_json_data = get_local_download_data(self.Default_loc_video)
                else:
                    user_json_data = get_local_download_data(self.Default_loc_video) + get_local_download_data(
                        self.Default_loc_audio)
            elif self.downloaded_file_filter in ["playlist_video", "playlist_audio"]:
                user_json_data = get_local_download_data(self.Default_loc_audio)
            else:
                user_json_data = get_local_download_data(self.Default_loc_video)
            user_json_data = get_downloaded_data_filter(user_json_data, self.downloaded_file_filter)
            user_json_data = sorted(user_json_data, key=lambda k: k['sort_param'], reverse=True)
            c_index = self.ui.listWidget.currentIndex().row()
            if c_index != -1:
                selected_video = user_json_data[c_index]
                download_path = selected_video.get("download_path")
                if not os.path.isdir(download_path):
                    self.popup_message(title="Directory not found!", message="", error=True)
                else:
                    print(download_path)
                    QDesktopServices.openUrl(QUrl.fromLocalFile(download_path))
            else:
                self.popup_message(title="Please select file first!", message="", error=True)
        except Exception as e:
            self.popup_message(title="Error while opening the directory!", message="", error=True)
            pass

    def play_videos_from_downloads(self):
        try:
            if self.downloaded_file_filter == "all_files":
                if self.Default_loc_video == self.Default_loc_audio:
                    user_json_data = get_local_download_data(self.Default_loc_video)
                else:
                    user_json_data = get_local_download_data(self.Default_loc_video) + get_local_download_data(
                        self.Default_loc_audio)
            elif self.downloaded_file_filter in ["playlist_video", "playlist_audio"]:
                user_json_data = get_local_download_data(self.Default_loc_audio)
            else:
                user_json_data = get_local_download_data(self.Default_loc_video)
            user_json_data = get_downloaded_data_filter(user_json_data, self.downloaded_file_filter)
            user_json_data = sorted(user_json_data, key=lambda k: k['sort_param'], reverse=True)
            c_index = self.ui.listWidget.currentIndex().row()
            if c_index != -1:
                if len(self.download_search_map_list) > 0:
                    selected_video = self.download_search_map_list[c_index]
                else:
                    selected_video = user_json_data[c_index]
                file_path = selected_video.get("file_path")
                if not os.path.isfile(file_path):
                    self.popup_message(title="File not found or deleted!", message="", error=True)
                else:
                    print(file_path)
                    QDesktopServices.openUrl(QUrl.fromLocalFile(file_path))
            else:
                self.popup_message(title="Please select file first!!", message="", error=True)
        except Exception as e:
            self.popup_message(title="Error while playing the media!", message="", error=True)
            pass

    def play_videos_mpv_from_downloads(self):
        try:
            if self.downloaded_file_filter == "all_files":
                if self.Default_loc_video == self.Default_loc_audio:
                    user_json_data = get_local_download_data(self.Default_loc_video)
                else:
                    user_json_data = get_local_download_data(self.Default_loc_video) + get_local_download_data(
                        self.Default_loc_audio)
            elif self.downloaded_file_filter in ["playlist_video", "playlist_audio"]:
                user_json_data = get_local_download_data(self.Default_loc_audio)
            else:
                user_json_data = get_local_download_data(self.Default_loc_video)
            user_json_data = get_downloaded_data_filter(user_json_data, self.downloaded_file_filter)
            user_json_data = sorted(user_json_data, key=lambda k: k['sort_param'], reverse=True)
            c_index = self.ui.listWidget.currentIndex().row()
            if c_index != -1:
                if len(self.download_search_map_list) > 0:
                    selected_video = self.download_search_map_list[c_index]
                else:
                    selected_video = user_json_data[c_index]
                file_path = selected_video.get("file_path")
                if not os.path.isfile(file_path):
                    self.popup_message(title="File not found or deleted!", message="", error=True)
                else:
                    self.process = QProcess()
                    self.mpv_arguments = []
                    if self.after_playback_action == "loop_play":
                        self.mpv_arguments.append("--loop")
                    self.mpv_arguments.append("--force-window")
                    self.mpv_arguments.append(file_path)
                    self.mpv_arguments.append("--title={0}".format(selected_video.get("title_show", PRODUCT_NAME)))
                    self.mpv_arguments.append("--gpu-context=x11")
                    self.process.start("mpv", self.mpv_arguments)
            else:
                self.popup_message(title="Please select file first!!", message="", error=True)
        except Exception as e:
            self.popup_message(title="Error while playing the media!", message="", error=True)
            pass

    def details_video_from_downloads(self):
        try:
            c_index = self.ui.listWidget.currentIndex().row()
            if c_index != -1:
                if self.downloaded_file_filter == "all_files":
                    if self.Default_loc_video == self.Default_loc_audio:
                        video_info = get_local_download_data(self.Default_loc_video)
                    else:
                        video_info = get_local_download_data(self.Default_loc_video) + get_local_download_data(
                            self.Default_loc_audio)
                elif self.downloaded_file_filter in ["playlist_video", "playlist_audio"]:
                    video_info = get_local_download_data(self.Default_loc_audio)
                else:
                    video_info = get_local_download_data(self.Default_loc_video)
                video_info = get_downloaded_data_filter(video_info, self.downloaded_file_filter)
                video_info = sorted(video_info, key=lambda k: k['sort_param'], reverse=True)
                if len(self.download_search_map_list) > 0:
                    video_info = self.download_search_map_list[c_index]
                else:
                    video_info = video_info[c_index]
                title = video_info.get("title_show", "-")
                length = video_info.get("length", "-")
                v_type = video_info.get("type", "-")
                subtype = video_info.get("subtype", "-")
                bitrate = video_info.get("bitrate", "-")

                if v_type == "video":
                    fps = video_info.get("fps", "-")
                    resolution = video_info.get("resolution", "-")
                else:
                    fps = "N/A"
                    resolution = "N/A"
                size = video_info.get("size", "-")
                download_date = video_info.get("download_date", "-")
                download_time = video_info.get("download_time", "-")
                audio_channel = video_info.get("audio_channel", "")

                all_videos_list = [
                    f"File Type -     {str(v_type).upper()}\n"
                    f"Length -        {length}\n"
                    f"Resolution -        {str(resolution).upper()}\n"
                    f"Bitrate -        {bitrate}Kbps\n"
                    f"Channels -        {audio_channel}\n"
                    f"Format -        {str(subtype).upper()}\n"
                    f"FPS -       {fps}\n"
                    f"Size -      {size}\n"
                    f"Downloaded On -     {download_date} {download_time}"]
                res = "".join(all_videos_list)
                self.popup_message(f"Title | {title}", res)
            else:
                self.popup_message(title="Please select file first!", message="", error=True)
        except Exception as e:
            self.popup_message(title="Error while getting details!", message="", error=True)
            pass

    def delete_video_from_downloads(self):
        try:
            self.msg = QMessageBox()
            self.msg.setWindowFlag(QtCore.Qt.FramelessWindowHint)
            self.msg.setStyleSheet("background-color:#263a4e;color:#eaeaea;")
            self.msg.setIcon(QMessageBox.Information)
            c_index = self.ui.listWidget.currentIndex().row()
            if c_index != -1:
                current_file_to_delete = self.ui.listWidget.currentItem().text()
                self.msg.setText(f"Are you sure want to delete ?\n\n{current_file_to_delete}")
                cb = QCheckBox("Delete Source file too")
                cb.setChecked(self.delete_source_file)
                self.msg.setCheckBox(cb)
                yes_button = self.msg.addButton(QMessageBox.Yes)
                no_button = self.msg.addButton(QMessageBox.No)
                self.msg.exec_()
                if self.msg.clickedButton() == yes_button:
                    if cb.isChecked():
                        self.delete_source_file = True
                        self.delete_entry_from_list(delete_source_file=True)
                    else:
                        self.delete_source_file = False
                        self.delete_entry_from_list()
                if self.msg.clickedButton() == no_button:
                    if cb.isChecked():
                        self.delete_source_file = True
                    else:
                        self.delete_source_file = False
            else:
                self.popup_message(title="Please select file first!", message="", error=True)
        except Exception as e:
            self.popup_message(title="Error while deleting the file!", message="", error=True)
            pass

    def delete_entry_from_list(self, delete_source_file=False):
        if self.downloaded_file_filter == "all_files":
            if self.Default_loc_video == self.Default_loc_audio:
                video_info = get_local_download_data(self.Default_loc_video)
            else:
                video_info = get_local_download_data(self.Default_loc_video) + get_local_download_data(
                    self.Default_loc_audio)
        elif self.downloaded_file_filter in ["playlist_video", "playlist_audio"]:
            video_info = get_local_download_data(self.Default_loc_audio)
        else:
            video_info = get_local_download_data(self.Default_loc_video)
        video_info_without_filter = deepcopy(video_info)
        c_index = self.ui.listWidget.currentIndex().row()
        if c_index != -1:
            video_info = get_downloaded_data_filter(video_info, self.downloaded_file_filter)
            video_info = sorted(video_info, key=lambda k: k['sort_param'], reverse=True)
            if self.downloaded_file_filter != "all_files":
                video_info_copy = video_info_without_filter
            else:
                video_info_copy = deepcopy(video_info)
            if len(self.download_search_map_list) > 0:
                poped_item = self.download_search_map_list.pop(c_index)
            else:
                poped_item = video_info.pop(c_index)
            poped_item_copy_index = video_info_copy.index(poped_item)
            video_info_copy.pop(poped_item_copy_index)
            delete_location = str(poped_item.get("download_path")).split("FORMAT_LAB")[0]
            video_info_copy_1 = []
            for item_dict in video_info_copy:
                if delete_location in item_dict.get("download_path"):
                    video_info_copy_1.append(item_dict)
            save_after_delete(video_info_copy_1, delete_location)
            self.ui.listWidget.clear()
            self.ui.search_videos.clear()
            self.get_user_download_data()
            if delete_source_file:
                try:
                    file_path = poped_item.get("file_path")
                    os.remove(file_path)
                except Exception as e:
                    pass
        else:
            self.popup_message(title="Please select file first!", message="", error=True)

    def search_videos(self):
        try:
            search_string = self.ui.search_videos.text()
            if search_string in ["", None]:
                self.ui.filter_by.setCurrentIndex(0)
                self.downloaded_file_filter = "all_files"

            if self.Default_loc_video == self.Default_loc_audio:
                video_info = get_local_download_data(self.Default_loc_video)
            else:
                video_info = get_local_download_data(self.Default_loc_video) + get_local_download_data(
                    self.Default_loc_audio)
            video_info = sorted(video_info, key=lambda k: k['sort_param'], reverse=True)
            exist_entry = [x.get("title_show") for x in video_info]
            index = -1
            flag = 0
            index_list = set()
            for entry in exist_entry:
                index += 1
                if search_string.lower() in entry.lower():
                    index_list.add(index)
                    flag = 1
            if flag == 0:
                pass
            else:
                self.ui.listWidget.clear()
                size = QtCore.QSize()
                size.setHeight(100)
                size.setWidth(100)
                self.download_search_map_list = []
                for number in range(0, len(video_info)):
                    if number in index_list:
                        row = video_info[number]
                        self.download_search_map_list.append(row)
                        thumbnail_path = row.get("thumbnail_path")
                        if not os.path.isfile(thumbnail_path):
                            thumbnail_path = ":/myresource/resource/download_preview.png"
                        title = row.get("title_show")
                        file_type = str(row.get("type")).upper()
                        resolution = str(row.get("resolution")).upper()
                        subtype = str(row.get("subtype")).upper()
                        length = row.get("length")
                        file_size = row.get("size")
                        if file_type == "AUDIO":
                            details = f"{title}\n🇦​​​​​🇺​​​​​🇩​​​​​🇮​​​​​🇴​​​​​\nSize: {file_size}\nLength: {length}"
                        else:
                            details = f"{title}\n🇻​​​​​🇮​​​​​🇩​​​​​🇪​​​​​🇴​​​​​-{resolution}-{subtype}\nSize: {file_size}\nLength: {length}"

                        if details not in exist_entry:
                            icon = QtGui.QIcon()
                            icon.addPixmap(QtGui.QPixmap(thumbnail_path), QtGui.QIcon.Normal, QtGui.QIcon.Off)
                            item = QtWidgets.QListWidgetItem(icon, details)
                            item.setSizeHint(size)
                            self.ui.listWidget.addItem(item)
                self.ui.listWidget.setIconSize(QtCore.QSize(150, 150))
        except Exception as e:
            self.popup_message(title="Error while searching the files!", message="", error=True)
            pass

    def clear_search_bar_on_edit(self):
        if self.ui.search_videos.text() == "Search Download History":
            self.ui.search_videos.clear()

    def about_page(self):
        MainFunctions.reset_selection(self)
        self.ui.stackedWidget.setCurrentIndex(6)
        self.about.set_active(True)

    def account_page(self):
        MainFunctions.reset_selection(self)
        self.ui.stackedWidget.setCurrentIndex(5)
        self.account.set_active(True)
        try:
            account_id = str(self.ui.lineEdit_account_id_2.text())
            if account_id not in ["", None]:
                self.ui.error_message_2.setText(
                    f'<html><head/><body><p align="center"><span style=" color:#4e9a06;">If you have changed your PC or lost your account, </span><a href="https://warlordsoftwares.in/contact_us/?account_id={account_id}&application={PRODUCT_NAME}"><span style=" text-decoration: underline; color:#ef2929;">@Contact us</span></a><span style=" color:#4e9a06;"> to restore.</span></p></body></html>')
        except Exception as e:
            print(e)
            self.ui.error_message_2.setText(
                '<html><head/><body><p align="center"><span style=" color:#4e9a06;">If you have changed your PC or lost your account, </span><a href="https://warlordsoftwares.in/contact_us/"><span style=" text-decoration: underline; color:#ef2929;">@Contact us</span></a><span style=" color:#4e9a06;"> to restore.</span></p></body></html>')

    def pro_plan_hide_plan_compare_chart(self):
        self.ui.groupBox.setVisible(False)
        self.ui.groupBox_2.setVisible(True)
        self.ui.purchase_licence_2.setVisible(False)
        self.ui.refresh_account_2.setVisible(False)

    def redirect_to_warlordsoft(self):
        warlord_soft_link = "https://warlordsoftwares.in/warlord_soft/dashboard/"
        webbrowser.open(warlord_soft_link)

    def redirect_to_paypal_donation(self):
        paypal_donation_link = "https://www.paypal.com/paypalme/rishabh3354/10"
        webbrowser.open(paypal_donation_link)

    def ge_more_apps(self):
        paypal_donation_link = "https://snapcraft.io/search?q=rishabh"
        webbrowser.open(paypal_donation_link)

    def redirect_to_rate_snapstore(self):
        QDesktopServices.openUrl(QUrl("snap://formatlab"))

    def redirect_to_feedback_button(self):
        feedback_link = "https://warlordsoftwares.in/contact_us/"
        webbrowser.open(feedback_link)

    def purchase_details_after_payment(self):
        if check_internet_connection():
            account_dict = get_user_data_from_local()
            if account_dict:
                account_id = str(account_dict.get("email")).split("@")[0]
                if account_id:
                    warlord_soft_link = f"https://warlordsoftwares.in/warlord_soft/subscription/?product={PRODUCT_NAME}&account_id={account_id} "
                else:
                    warlord_soft_link = f"https://warlordsoftwares.in/warlord_soft/dashboard/"
                webbrowser.open(warlord_soft_link)
                time.sleep(5)
                webbrowser.open("https://warlordsoftwares.in/warlord_soft/your_plan/")
        else:
            self.popup_message(title="No internet connection", message="Please check your internet connection!")

    def purchase_licence_2(self):
        if check_internet_connection():
            account_dict = get_user_data_from_local()
            if account_dict:
                account_id = str(account_dict.get("email")).split("@")[0]
                if account_id:
                    warlord_soft_link = f"https://warlordsoftwares.in/warlord_soft/subscription/?product={PRODUCT_NAME}&account_id={account_id} "
                else:
                    warlord_soft_link = f"https://warlordsoftwares.in/signup/"
                webbrowser.open(warlord_soft_link)
                data = dict()
                data["email"] = f"{account_id}@warlordsoft.in"
                data["password"] = f"{account_id}@warlordsoft.in"
                data["re_password"] = f"{account_id}@warlordsoft.in"
                self.save_token = SaveLocalInToken(data)
                self.save_token.start()
        else:
            self.popup_message(title="No internet connection", message="Please check your internet connection!")

    def sync_account_id_with_warlord_soft(self):
        try:
            if check_internet_connection():
                account_dict = get_user_data_from_local()
                if account_dict:
                    account_id = str(account_dict.get("email")).split("@")[0]
                    data = dict()
                    data["sync_url"] = f"warlord_soft/subscription/?product={PRODUCT_NAME}&account_id={account_id}"
                    data["email"] = f"{account_id}@warlordsoft.in"
                    data["password"] = f"{account_id}@warlordsoft.in"
                    data["re_password"] = f"{account_id}@warlordsoft.in"
                    self.sync_account = SyncAccountIdWithDb(data)
                    self.sync_account.start()
        except Exception as e:
            print(e)
            pass

    def refresh_account_2(self):
        self.ui.error_message.clear()
        self.ui.account_progress_bar.setRange(0, 0)
        self.refresh_thread = RefreshButtonThread(PRODUCT_NAME, self)
        self.refresh_thread.change_value_refresh.connect(self.after_refresh)
        self.refresh_thread.start()

    def after_refresh(self, response_dict):
        if response_dict.get("status"):
            user_plan_data = get_user_data_from_local()
            if user_plan_data:
                self.logged_in_user_plan_page(user_plan_data)
        else:
            self.ui.error_message.setText(response_dict.get("message"))
        self.ui.account_progress_bar.setRange(0, 1)

    def my_plan(self):
        token = check_for_local_token()
        if token not in [None, ""]:
            user_plan_data = get_user_data_from_local()
            if user_plan_data:
                self.logged_in_user_plan_page(user_plan_data)
            else:
                user_plan_data = dict()
                user_plan_data['plan'] = "N/A"
                user_plan_data['expiry_date'] = "N/A"
                user_plan_data['email'] = "N/A"
                self.logged_in_user_plan_page(user_plan_data)
        else:
            user_plan_data = get_user_data_from_local()
            if user_plan_data:
                self.logged_in_user_plan_page(user_plan_data)

    def logged_in_user_plan_page(self, user_plan_data):
        self.ui.groupBox_2.setVisible(False)
        account_email = user_plan_data.get('email')
        plan = user_plan_data.get("plan", "N/A")
        expiry_date = user_plan_data.get("expiry_date")
        if account_email:
            account_id = str(account_email).split("@")[0]
            self.ui.lineEdit_account_id_2.setText(account_id)
        else:
            self.ui.lineEdit_account_id_2.setText("N/A")
        if plan == "Free Trial":
            self.ui.lineEdit_plan_2.setText("Evaluation")
        elif plan == "Life Time Free Plan":
            self.ui.purchase_details.setEnabled(True)
            self.ui.purchase_licence_2.setEnabled(False)
            self.ui.refresh_account_2.setEnabled(False)
            self.ui.lineEdit_plan_2.setText(plan)
            self.pro_plan_hide_plan_compare_chart()
            if self.one_time_congratulate:
                self.ui.account_progress_bar.setRange(0, 1)
                self.popup_message(title="Congratulations! Plan Upgraded to PRO",
                                   message="Your plan has been upgraded to PRO. Enjoy lifetime licence. "
                                           "Thankyou for your purchase.\n\nPLEASE RESTART YOUR APP TO SEE CHANGES.")
                self.one_time_congratulate = False
        else:
            self.ui.purchase_licence_2.setText("UPGRADE PLAN")
            self.ui.lineEdit_plan_2.setText(plan)
            self.ui.purchase_details.setEnabled(True)

        if expiry_date:
            if plan == "Life Time Free Plan":
                self.ui.lineEdit_expires_on_2.setText(f"{PRODUCT_NAME} PRO VERSION")
                self.is_plan_active = True
            else:
                plan_days_left = days_left(expiry_date)
                if plan_days_left == "0 Day(s) Left":
                    self.ui.error_message.setText("Evaluation period ended, Upgrade to Pro")
                    self.ui.lineEdit_expires_on_2.setText(plan_days_left)
                    self.is_plan_active = False
                else:
                    self.is_plan_active = True
                    self.ui.lineEdit_expires_on_2.setText(plan_days_left)
        else:
            self.ui.lineEdit_expires_on_2.setText("N/A")

    def check_your_plan(self):
        if not self.is_plan_active:
            self.msg = QMessageBox()
            self.msg.setWindowFlag(QtCore.Qt.FramelessWindowHint)
            self.msg.setStyleSheet("background-color:#263a4e;color:#eaeaea;")
            self.msg.setIcon(QMessageBox.Information)
            self.msg.setText("Evaluation period ended, Upgrade to Pro")
            self.msg.setInformativeText(
                "In FORMAT LAB free version, HD+ video quality option is not available. But you can still download SD "
                "quality videos.\n "
                "Please support the developer and purchase a license to UNLOCK this feature.")
            purchase = self.msg.addButton(QMessageBox.Yes)
            close = self.msg.addButton(QMessageBox.Yes)
            purchase.setText('Purchase Licence')
            close.setText('Close')
            purchase.setIcon(QIcon(QApplication.style().standardIcon(QStyle.SP_DialogOkButton)))
            close.setIcon(QIcon(QApplication.style().standardIcon(QStyle.SP_BrowserStop)))
            self.msg.exec_()
            try:
                if self.msg.clickedButton() == purchase:
                    self.account_page()
                elif self.msg.clickedButton() == close:
                    pass
            except Exception as e:
                pass
            return False
        return True


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    sys.exit(app.exec_())

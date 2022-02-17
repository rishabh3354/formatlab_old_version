from PyQt5 import QtCore
from PyQt5.QtWidgets import QWidget, QDesktopWidget
from ui_settings import Ui_AppSettings


class AppSettings(QWidget):

    def __init__(self):
        QWidget.__init__(self)
        self.ui = Ui_AppSettings()
        self.ui.setupUi(self)
        self.setWindowTitle("Settings")
        self.setWindowFlags(QtCore.Qt.WindowCloseButtonHint)
        qtRectangle = self.frameGeometry()
        centerPoint = QDesktopWidget().availableGeometry().center()
        qtRectangle.moveCenter(centerPoint)
        self.move(qtRectangle.topLeft())


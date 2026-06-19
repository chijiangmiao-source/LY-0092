from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont
from PySide6.QtWidgets import QApplication
from qfluentwidgets import (
    NavigationItemPosition, FluentWindow,
    SplashScreen, FluentIcon as FIF
)

from app.ui.pages.review_list_page import ReviewListPage
from app.ui.pages.rectification_page import RectificationPage
from app.ui.pages.topic_page import TopicPage
from app.ui.pages.statistics_page import StatisticsPage


def create_app_icon():
    pixmap = QPixmap(128, 128)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)

    painter.setBrush(QColor("#0078d4"))
    painter.setPen(Qt.NoPen)
    painter.drawRoundedRect(10, 10, 108, 108, 20, 20)

    painter.setPen(QColor("white"))
    font = QFont("Microsoft YaHei", 40, QFont.Bold)
    painter.setFont(font)
    painter.drawText(pixmap.rect(), Qt.AlignCenter, "宿")

    painter.end()
    return QIcon(pixmap)


class MainWindow(FluentWindow):
    def __init__(self):
        super().__init__()
        self.initWindow()

        icon = create_app_icon()
        self.setWindowIcon(icon)

        self.splashScreen = SplashScreen(icon, self)
        self.splashScreen.setIconSize(QSize(100, 100))
        self.splashScreen.raise_()

        self.initPages()

        QApplication.processEvents()
        self.splashScreen.finish()

    def initWindow(self):
        self.resize(1280, 800)
        self.setMinimumSize(1024, 680)
        self.setWindowTitle("民宿差评整改跟踪板")

    def initPages(self):
        self.reviewListPage = ReviewListPage(self)
        self.rectificationPage = RectificationPage(self)
        self.topicPage = TopicPage(self)
        self.statisticsPage = StatisticsPage(self)

        self.addSubInterface(self.reviewListPage, FIF.DOCUMENT, '差评记录')
        self.addSubInterface(self.rectificationPage, FIF.BOOK_SHELF, '整改任务')
        self.addSubInterface(self.topicPage, FIF.HISTORY, '重点整改专题')
        self.addSubInterface(self.statisticsPage, FIF.VIEW, '统计分析')

        self.navigationInterface.setCurrentItem(self.reviewListPage.objectName())

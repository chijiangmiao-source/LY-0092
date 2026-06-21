from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QLabel, QAbstractItemView, QFrame,
    QGraphicsDropShadowEffect, QSplitter, QTextEdit, QScrollArea
)
from qfluentwidgets import (
    PushButton, ComboBox, PrimaryPushButton,
    InfoBar, InfoBarPosition, FluentIcon as FIF, CardWidget,
    TabWidget, SubtitleLabel, StrongBodyLabel, BodyLabel,
    DateEdit
)

from app.dao.review_analysis_dao import ReviewAnalysisDAO
from app.dao.review_dao import ReviewDAO
from app.models.models import BadReview, RectificationReview
from app.ui.dialogs.review_analysis_dialog import ReviewAnalysisDialog
from app.utils.constants import (
    PROBLEM_TYPES, ROOM_TYPES, REVIEW_SOURCES,
    RESPONSIBILITY_TYPES, RECURRENCE_LEVELS
)
from app.utils.query_builder import ReviewFilterParams


class ReviewAnalysisPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("reviewAnalysisPage")
        self.dao = ReviewAnalysisDAO()
        self.review_dao = ReviewDAO()
        self.initUI()
        self.refresh()

    def initUI(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        headerLayout = QHBoxLayout()
        headerLayout.setSpacing(10)

        title = QLabel("整改效果复盘中心")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #1a1a1a;")
        headerLayout.addWidget(title)
        headerLayout.addStretch()

        self.refreshBtn = PushButton("刷新")
        self.refreshBtn.setIcon(FIF.SYNC)
        self.refreshBtn.clicked.connect(self.refresh)
        headerLayout.addWidget(self.refreshBtn)

        layout.addLayout(headerLayout)

        filterCard = CardWidget()
        filterLayout = QHBoxLayout(filterCard)
        filterLayout.setContentsMargins(16, 12, 16, 12)
        filterLayout.setSpacing(12)

        filterLayout.addWidget(BodyLabel("开始日期："))
        self.startDateEdit = DateEdit()
        self.startDateEdit.setDisplayFormat("yyyy-MM-dd")
        self.startDateEdit.setCalendarPopup(True)
        self.startDateEdit.setFixedHeight(32)
        self.startDateEdit.setFixedWidth(130)
        filterLayout.addWidget(self.startDateEdit)

        filterLayout.addWidget(BodyLabel("结束日期："))
        self.endDateEdit = DateEdit()
        self.endDateEdit.setDisplayFormat("yyyy-MM-dd")
        self.endDateEdit.setCalendarPopup(True)
        self.endDateEdit.setFixedHeight(32)
        self.endDateEdit.setFixedWidth(130)
        filterLayout.addWidget(self.endDateEdit)

        filterLayout.addWidget(BodyLabel("问题类型："))
        self.problemTypeFilter = ComboBox()
        self.problemTypeFilter.addItem("全部", "")
        for t in PROBLEM_TYPES:
            self.problemTypeFilter.addItem(t, t)
        self.problemTypeFilter.setFixedWidth(120)
        self.problemTypeFilter.setFixedHeight(32)
        filterLayout.addWidget(self.problemTypeFilter)

        filterLayout.addWidget(BodyLabel("房型："))
        self.roomTypeFilter = ComboBox()
        self.roomTypeFilter.addItem("全部", "")
        for t in ROOM_TYPES:
            self.roomTypeFilter.addItem(t, t)
        self.roomTypeFilter.setFixedWidth(120)
        self.roomTypeFilter.setFixedHeight(32)
        filterLayout.addWidget(self.roomTypeFilter)

        filterLayout.addWidget(BodyLabel("来源："))
        self.sourceFilter = ComboBox()
        self.sourceFilter.addItem("全部", "")
        for s in REVIEW_SOURCES:
            self.sourceFilter.addItem(s, s)
        self.sourceFilter.setFixedWidth(100)
        self.sourceFilter.setFixedHeight(32)
        filterLayout.addWidget(self.sourceFilter)

        filterLayout.addWidget(BodyLabel("责任："))
        self.responsibilityFilter = ComboBox()
        self.responsibilityFilter.addItem("全部", "")
        for r in RESPONSIBILITY_TYPES:
            self.responsibilityFilter.addItem(r, r)
        self.responsibilityFilter.setFixedWidth(100)
        self.responsibilityFilter.setFixedHeight(32)
        filterLayout.addWidget(self.responsibilityFilter)

        filterLayout.addStretch()

        self.applyFilterBtn = PrimaryPushButton("应用筛选")
        self.applyFilterBtn.setFixedHeight(32)
        self.applyFilterBtn.clicked.connect(self.onFilter)
        filterLayout.addWidget(self.applyFilterBtn)

        self.resetFilterBtn = PushButton("重置")
        self.resetFilterBtn.setFixedHeight(32)
        self.resetFilterBtn.clicked.connect(self.resetFilters)
        filterLayout.addWidget(self.resetFilterBtn)

        layout.addWidget(filterCard)

        self.summaryWidget = self.createSummaryWidget()
        layout.addWidget(self.summaryWidget)

        self.detailStatsWidget = self.createDetailStatsWidget()
        layout.addWidget(self.detailStatsWidget, 1)

        self.problemTypeFilter.currentIndexChanged.connect(self.onFilter)
        self.roomTypeFilter.currentIndexChanged.connect(self.onFilter)
        self.sourceFilter.currentIndexChanged.connect(self.onFilter)
        self.responsibilityFilter.currentIndexChanged.connect(self.onFilter)
        self.startDateEdit.dateChanged.connect(self.onFilter)
        self.endDateEdit.dateChanged.connect(self.onFilter)

    def createSummaryWidget(self):
        widget = QWidget()
        widgetLayout = QVBoxLayout(widget)
        widgetLayout.setContentsMargins(0, 0, 0, 0)
        widgetLayout.setSpacing(10)

        mainStats = QWidget()
        mainStatsLayout = QHBoxLayout(mainStats)
        mainStatsLayout.setContentsMargins(0, 0, 0, 0)
        mainStatsLayout.setSpacing(12)

        self.totalCard = self.createStatCard("整改完成数", "0", "📋", "#0078d4")
        mainStatsLayout.addWidget(self.totalCard, 1)

        self.passRateCard = self.createStatCard("复查通过率", "0%", "✅", "#107c10")
        mainStatsLayout.addWidget(self.passRateCard, 1)

        self.avgDurationCard = self.createStatCard("平均整改时长", "0天", "⏱", "#d83b01")
        mainStatsLayout.addWidget(self.avgDurationCard, 1)

        self.recurrenceRateCard = self.createStatCard("重复发生率", "0%", "🔄", "#e81123")
        mainStatsLayout.addWidget(self.recurrenceRateCard, 1)

        widgetLayout.addWidget(mainStats)

        detailRow = QWidget()
        detailRowLayout = QHBoxLayout(detailRow)
        detailRowLayout.setContentsMargins(0, 0, 0, 0)
        detailRowLayout.setSpacing(12)

        self.passedCard = self.createStatCard("整改有效", "0", "👍", "#107c10")
        detailRowLayout.addWidget(self.passedCard, 1)

        self.partialCard = self.createStatCard("部分有效", "0", "🤔", "#ffb900")
        detailRowLayout.addWidget(self.partialCard, 1)

        self.failedCard = self.createStatCard("整改无效", "0", "👎", "#e81123")
        detailRowLayout.addWidget(self.failedCard, 1)

        self.followCard = self.createStatCard("需持续跟踪", "0", "👀", "#5c2d91")
        detailRowLayout.addWidget(self.followCard, 1)

        self.notReviewedCard = self.createStatCard("待复盘", "0", "📝", "#8764b8")
        detailRowLayout.addWidget(self.notReviewedCard, 1)

        widgetLayout.addWidget(detailRow)

        return widget

    def createStatCard(self, title, value, icon, color):
        card = CardWidget()
        card.setFixedHeight(90)
        layout = QHBoxLayout(card)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)

        iconLabel = QLabel(icon)
        iconLabel.setStyleSheet(f"font-size: 28px;")
        iconLabel.setAlignment(Qt.AlignCenter)
        iconLabel.setFixedWidth(48)
        layout.addWidget(iconLabel)

        textLayout = QVBoxLayout()
        textLayout.setSpacing(2)
        textLayout.setContentsMargins(0, 0, 0, 0)

        titleLabel = QLabel(title)
        titleLabel.setStyleSheet("color: #666; font-size: 12px;")
        textLayout.addWidget(titleLabel)

        valueLabel = QLabel(value)
        valueLabel.setStyleSheet(f"color: {color}; font-size: 24px; font-weight: bold;")
        textLayout.addWidget(valueLabel)

        layout.addLayout(textLayout, 1)

        card.valueLabel = valueLabel
        return card

    def createDetailStatsWidget(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self.tabWidget = TabWidget(self)

        self.overviewPage = self.createOverviewPage()
        self.recurrencePage = self.createRecurrencePage()
        self.durationPage = self.createDurationPage()
        self.passRatePage = self.createPassRatePage()
        self.reviewListPage = self.createReviewListPage()

        self.tabWidget.addTab(self.overviewPage, "整改前后对比")
        self.tabWidget.addTab(self.recurrencePage, "重复发生率")
        self.tabWidget.addTab(self.durationPage, "整改时长分析")
        self.tabWidget.addTab(self.passRatePage, "复查通过率")
        self.tabWidget.addTab(self.reviewListPage, "复盘记录管理")

        layout.addWidget(self.tabWidget, 1)

        return widget

    def createOverviewPage(self):
        page = QWidget()
        pageLayout = QVBoxLayout(page)
        pageLayout.setContentsMargins(0, 10, 0, 0)
        pageLayout.setSpacing(10)

        hint = StrongBodyLabel("整改前后效果对比分析 - 按问题类型、房间、来源、责任多维度统计")
        hint.setStyleSheet("color: #666;")
        pageLayout.addWidget(hint)

        contentWidget = QWidget()
        contentLayout = QHBoxLayout(contentWidget)
        contentLayout.setContentsMargins(0, 0, 0, 0)
        contentLayout.setSpacing(15)

        leftPanel = self.createComparisonPanel("按问题类型", "by_problem_type")
        contentLayout.addWidget(leftPanel, 1)

        rightPanel = QWidget()
        rightLayout = QVBoxLayout(rightPanel)
        rightLayout.setContentsMargins(0, 0, 0, 0)
        rightLayout.setSpacing(15)

        topRight = self.createComparisonPanel("按差评来源", "by_source")
        rightLayout.addWidget(topRight, 1)

        bottomRight = self.createComparisonPanel("按责任归因", "by_responsibility")
        rightLayout.addWidget(bottomRight, 1)

        contentLayout.addWidget(rightPanel, 1)

        pageLayout.addWidget(contentWidget, 1)

        bottomPanel = self.createComparisonPanel("按房型", "by_room_type")
        pageLayout.addWidget(bottomPanel, 1)

        return page

    def createComparisonPanel(self, title, data_key):
        card = CardWidget()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)

        titleLabel = StrongBodyLabel(f"📊 {title}")
        titleLabel.setStyleSheet("font-size: 14px; font-weight: bold; color: #1a1a1a;")
        layout.addWidget(titleLabel)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        self.comparisonContent = QWidget()
        self.comparisonLayout = QVBoxLayout(self.comparisonContent)
        self.comparisonLayout.setContentsMargins(0, 4, 0, 0)
        self.comparisonLayout.setSpacing(8)

        scroll.setWidget(self.comparisonContent)
        layout.addWidget(scroll, 1)

        setattr(self, f"{data_key}_content", self.comparisonContent)
        setattr(self, f"{data_key}_layout", self.comparisonLayout)

        return card

    def createRecurrencePage(self):
        page = QWidget()
        pageLayout = QVBoxLayout(page)
        pageLayout.setContentsMargins(0, 10, 0, 0)
        pageLayout.setSpacing(10)

        hint = StrongBodyLabel("各类问题重复发生率统计 - 识别高回潮风险问题")
        hint.setStyleSheet("color: #666;")
        pageLayout.addWidget(hint)

        splitter = QSplitter(Qt.Horizontal)

        leftCard = CardWidget()
        leftLayout = QVBoxLayout(leftCard)
        leftLayout.setContentsMargins(16, 14, 16, 14)
        leftLayout.setSpacing(8)

        leftTitle = StrongBodyLabel("🔄 按问题类型重复发生率")
        leftTitle.setStyleSheet("font-size: 14px; font-weight: bold; color: #1a1a1a;")
        leftLayout.addWidget(leftTitle)

        self.recurrenceTable = QTableWidget()
        self.recurrenceTable.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.recurrenceTable.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.recurrenceTable.setSelectionMode(QAbstractItemView.SingleSelection)
        self.recurrenceTable.setAlternatingRowColors(True)
        self.recurrenceTable.verticalHeader().setVisible(False)

        headers = ["问题类型", "总数", "高风险", "中风险", "低风险", "无风险", "重复发生率"]
        self.recurrenceTable.setColumnCount(len(headers))
        self.recurrenceTable.setHorizontalHeaderLabels(headers)

        h = self.recurrenceTable.horizontalHeader()
        for i in range(len(headers)):
            h.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(0, QHeaderView.Stretch)

        leftLayout.addWidget(self.recurrenceTable, 1)

        splitter.addWidget(leftCard)

        rightCard = CardWidget()
        rightLayout = QVBoxLayout(rightCard)
        rightLayout.setContentsMargins(16, 14, 16, 14)
        rightLayout.setSpacing(8)

        rightTitle = StrongBodyLabel("⚠️ 重点问题回潮情况")
        rightTitle.setStyleSheet("font-size: 14px; font-weight: bold; color: #1a1a1a;")
        rightLayout.addWidget(rightTitle)

        self.recurrenceListWidget = QWidget()
        self.recurrenceListLayout = QVBoxLayout(self.recurrenceListWidget)
        self.recurrenceListLayout.setContentsMargins(0, 4, 0, 0)
        self.recurrenceListLayout.setSpacing(6)
        rightLayout.addWidget(self.recurrenceListWidget, 1)

        splitter.addWidget(rightCard)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)

        pageLayout.addWidget(splitter, 1)

        return page

    def createDurationPage(self):
        page = QWidget()
        pageLayout = QVBoxLayout(page)
        pageLayout.setContentsMargins(0, 10, 0, 0)
        pageLayout.setSpacing(10)

        hint = StrongBodyLabel("整改时长分析 - 平均整改时长、最长/最短整改时间")
        hint.setStyleSheet("color: #666;")
        pageLayout.addWidget(hint)

        overviewCard = CardWidget()
        overviewLayout = QHBoxLayout(overviewCard)
        overviewLayout.setContentsMargins(16, 14, 16, 14)
        overviewLayout.setSpacing(20)

        self.avgDurationDetail = self.createDetailStat("平均时长", "0天", "#0078d4")
        overviewLayout.addWidget(self.avgDurationDetail, 1)

        self.maxDurationDetail = self.createDetailStat("最长时长", "0天", "#e81123")
        overviewLayout.addWidget(self.maxDurationDetail, 1)

        self.minDurationDetail = self.createDetailStat("最短时长", "0天", "#107c10")
        overviewLayout.addWidget(self.minDurationDetail, 1)

        self.totalCountDetail = self.createDetailStat("统计样本", "0个", "#5c2d91")
        overviewLayout.addWidget(self.totalCountDetail, 1)

        pageLayout.addWidget(overviewCard)

        detailCard = CardWidget()
        detailLayout = QVBoxLayout(detailCard)
        detailLayout.setContentsMargins(16, 14, 16, 14)
        detailLayout.setSpacing(8)

        detailTitle = StrongBodyLabel("⏱ 按问题类型整改时长统计")
        detailTitle.setStyleSheet("font-size: 14px; font-weight: bold; color: #1a1a1a;")
        detailLayout.addWidget(detailTitle)

        self.durationTable = QTableWidget()
        self.durationTable.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.durationTable.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.durationTable.setSelectionMode(QAbstractItemView.SingleSelection)
        self.durationTable.setAlternatingRowColors(True)
        self.durationTable.verticalHeader().setVisible(False)

        headers = ["问题类型", "整改数", "平均时长(天)", "最长时长(天)", "最短时长(天)"]
        self.durationTable.setColumnCount(len(headers))
        self.durationTable.setHorizontalHeaderLabels(headers)

        h = self.durationTable.horizontalHeader()
        for i in range(len(headers)):
            h.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(0, QHeaderView.Stretch)

        detailLayout.addWidget(self.durationTable, 1)

        pageLayout.addWidget(detailCard, 1)

        return page

    def createDetailStat(self, title, value, color):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignCenter)

        titleLabel = BodyLabel(title)
        titleLabel.setStyleSheet(f"color: {color}; font-size: 13px;")
        titleLabel.setAlignment(Qt.AlignCenter)
        layout.addWidget(titleLabel)

        valueLabel = SubtitleLabel(value)
        valueLabel.setStyleSheet(f"color: {color}; font-size: 22px; font-weight: bold;")
        valueLabel.setAlignment(Qt.AlignCenter)
        layout.addWidget(valueLabel)

        widget.valueLabel = valueLabel
        return widget

    def createPassRatePage(self):
        page = QWidget()
        pageLayout = QVBoxLayout(page)
        pageLayout.setContentsMargins(0, 10, 0, 0)
        pageLayout.setSpacing(10)

        hint = StrongBodyLabel("复查通过率分析 - 按多维度对比整改效果")
        hint.setStyleSheet("color: #666;")
        pageLayout.addWidget(hint)

        splitter = QSplitter(Qt.Vertical)

        topCard = CardWidget()
        topLayout = QVBoxLayout(topCard)
        topLayout.setContentsMargins(16, 14, 16, 14)
        topLayout.setSpacing(8)

        topTitle = StrongBodyLabel("✅ 按问题类型复查通过率")
        topTitle.setStyleSheet("font-size: 14px; font-weight: bold; color: #1a1a1a;")
        topLayout.addWidget(topTitle)

        self.passRateTable = QTableWidget()
        self.passRateTable.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.passRateTable.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.passRateTable.setSelectionMode(QAbstractItemView.SingleSelection)
        self.passRateTable.setAlternatingRowColors(True)
        self.passRateTable.verticalHeader().setVisible(False)

        headers = ["问题类型", "总数", "通过数", "失败数", "通过率", "失败率"]
        self.passRateTable.setColumnCount(len(headers))
        self.passRateTable.setHorizontalHeaderLabels(headers)

        h = self.passRateTable.horizontalHeader()
        for i in range(len(headers)):
            h.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(0, QHeaderView.Stretch)

        topLayout.addWidget(self.passRateTable, 1)

        splitter.addWidget(topCard)

        bottomCard = CardWidget()
        bottomLayout = QVBoxLayout(bottomCard)
        bottomLayout.setContentsMargins(16, 14, 16, 14)
        bottomLayout.setSpacing(8)

        bottomTitle = StrongBodyLabel("📊 多维度通过率对比")
        bottomTitle.setStyleSheet("font-size: 14px; font-weight: bold; color: #1a1a1a;")
        bottomLayout.addWidget(bottomTitle)

        self.passRateDetailWidget = QWidget()
        self.passRateDetailLayout = QVBoxLayout(self.passRateDetailWidget)
        self.passRateDetailLayout.setContentsMargins(0, 4, 0, 0)
        self.passRateDetailLayout.setSpacing(10)
        bottomLayout.addWidget(self.passRateDetailWidget, 1)

        splitter.addWidget(bottomCard)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)

        pageLayout.addWidget(splitter, 1)

        return page

    def createReviewListPage(self):
        page = QWidget()
        pageLayout = QVBoxLayout(page)
        pageLayout.setContentsMargins(0, 10, 0, 0)
        pageLayout.setSpacing(10)

        splitter = QSplitter(Qt.Horizontal)

        leftCard = CardWidget()
        leftLayout = QVBoxLayout(leftCard)
        leftLayout.setContentsMargins(16, 14, 16, 14)
        leftLayout.setSpacing(8)

        leftHeader = QHBoxLayout()
        leftTitle = StrongBodyLabel("📝 待复盘整改记录")
        leftTitle.setStyleSheet("font-size: 14px; font-weight: bold; color: #1a1a1a;")
        leftHeader.addWidget(leftTitle)
        leftHeader.addStretch()
        self.unreviewedCountLabel = BodyLabel("0条")
        self.unreviewedCountLabel.setStyleSheet("color: #8764b8; font-weight: bold;")
        leftHeader.addWidget(self.unreviewedCountLabel)
        leftLayout.addLayout(leftHeader)

        self.unreviewedTable = QTableWidget()
        self.unreviewedTable.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.unreviewedTable.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.unreviewedTable.setSelectionMode(QAbstractItemView.SingleSelection)
        self.unreviewedTable.setAlternatingRowColors(True)
        self.unreviewedTable.verticalHeader().setVisible(False)

        headers = ["记录编号", "入住日期", "房间号", "问题类型", "来源", "责任", "整改完成日"]
        self.unreviewedTable.setColumnCount(len(headers))
        self.unreviewedTable.setHorizontalHeaderLabels(headers)

        h = self.unreviewedTable.horizontalHeader()
        for i in range(len(headers)):
            h.setSectionResizeMode(i, QHeaderView.ResizeToContents)

        leftLayout.addWidget(self.unreviewedTable, 1)

        leftBtnLayout = QHBoxLayout()
        leftBtnLayout.addStretch()
        self.createReviewBtn = PrimaryPushButton("填写复盘")
        self.createReviewBtn.setIcon(FIF.EDIT)
        self.createReviewBtn.clicked.connect(self.createReview)
        leftBtnLayout.addWidget(self.createReviewBtn)
        leftLayout.addLayout(leftBtnLayout)

        splitter.addWidget(leftCard)

        rightCard = CardWidget()
        rightLayout = QVBoxLayout(rightCard)
        rightLayout.setContentsMargins(16, 14, 16, 14)
        rightLayout.setSpacing(8)

        rightHeader = QHBoxLayout()
        rightTitle = StrongBodyLabel("📋 已复盘记录")
        rightTitle.setStyleSheet("font-size: 14px; font-weight: bold; color: #1a1a1a;")
        rightHeader.addWidget(rightTitle)
        rightHeader.addStretch()
        self.reviewedCountLabel = BodyLabel("0条")
        self.reviewedCountLabel.setStyleSheet("color: #107c10; font-weight: bold;")
        rightHeader.addWidget(self.reviewedCountLabel)
        rightLayout.addLayout(rightHeader)

        self.reviewedTable = QTableWidget()
        self.reviewedTable.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.reviewedTable.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.reviewedTable.setSelectionMode(QAbstractItemView.SingleSelection)
        self.reviewedTable.setAlternatingRowColors(True)
        self.reviewedTable.verticalHeader().setVisible(False)

        headers = ["记录编号", "复盘结论", "回潮风险", "复盘人", "复盘时间", "操作"]
        self.reviewedTable.setColumnCount(len(headers))
        self.reviewedTable.setHorizontalHeaderLabels(headers)

        h = self.reviewedTable.horizontalHeader()
        for i in range(len(headers)):
            h.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(0, QHeaderView.Stretch)

        rightLayout.addWidget(self.reviewedTable, 1)

        detailPanel = QFrame()
        detailPanel.setFrameShape(QFrame.StyledPanel)
        detailPanel.setStyleSheet("background-color: #f8f9fa; border-radius: 6px;")
        detailLayout = QVBoxLayout(detailPanel)
        detailLayout.setContentsMargins(12, 10, 12, 10)
        detailLayout.setSpacing(6)

        detailTitle = StrongBodyLabel("复盘详情")
        detailTitle.setStyleSheet("color: #333;")
        detailLayout.addWidget(detailTitle)

        self.experienceDetail = BodyLabel("选择一条已复盘记录查看详情")
        self.experienceDetail.setWordWrap(True)
        self.experienceDetail.setStyleSheet("color: #666;")
        detailLayout.addWidget(self.experienceDetail)

        self.preventionDetail = BodyLabel("")
        self.preventionDetail.setWordWrap(True)
        self.preventionDetail.setStyleSheet("color: #666;")
        detailLayout.addWidget(self.preventionDetail)

        rightLayout.addWidget(detailPanel)

        splitter.addWidget(rightCard)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)

        pageLayout.addWidget(splitter, 1)

        self.unreviewedTable.itemSelectionChanged.connect(self.onUnreviewedSelectionChanged)
        self.reviewedTable.itemSelectionChanged.connect(self.onReviewedSelectionChanged)

        return page

    def getFilters(self):
        return ReviewFilterParams(
            start_date=self.startDateEdit.date().toString("yyyy-MM-dd"),
            end_date=self.endDateEdit.date().toString("yyyy-MM-dd"),
            problem_type=self.problemTypeFilter.currentData() or "",
            room_type=self.roomTypeFilter.currentData() or "",
            source=self.sourceFilter.currentData() or "",
            responsibility=self.responsibilityFilter.currentData() or "",
        )

    def onFilter(self):
        self.loadData()

    def resetFilters(self):
        self.startDateEdit.setDate(self.startDateEdit.minimumDate())
        self.endDateEdit.setDate(self.endDateEdit.maximumDate())
        self.problemTypeFilter.setCurrentIndex(0)
        self.roomTypeFilter.setCurrentIndex(0)
        self.sourceFilter.setCurrentIndex(0)
        self.responsibilityFilter.setCurrentIndex(0)
        self.refresh()

    def refresh(self):
        from datetime import datetime, timedelta
        three_months_ago = datetime.now() - timedelta(days=90)
        self.startDateEdit.setDate(three_months_ago)
        self.endDateEdit.setDate(datetime.now())
        self.loadData()

    def loadData(self):
        fp = self.getFilters()

        comparison = self.dao.get_comparison_analysis(
            fp.start_date, fp.end_date, fp.problem_type,
            fp.room_type, fp.source, fp.responsibility
        )
        recurrence_stats = self.dao.get_recurrence_stats(
            fp.start_date, fp.end_date, fp.problem_type,
            fp.room_type, fp.source, fp.responsibility
        )
        duration_stats = self.dao.get_duration_stats(
            fp.start_date, fp.end_date, fp.problem_type,
            fp.room_type, fp.source, fp.responsibility
        )
        pass_rate_stats = self.dao.get_pass_rate_stats(
            fp.start_date, fp.end_date, fp.problem_type,
            fp.room_type, fp.source, fp.responsibility
        )
        high_risk = self.dao.get_high_risk_problems(fp.start_date, fp.end_date)

        self.updateSummaryCards(comparison, recurrence_stats)
        self.updateComparisonPanels(pass_rate_stats)
        self.updateRecurrenceTable(recurrence_stats)
        self.updateRecurrenceList(high_risk)
        self.updateDurationStats(duration_stats)
        self.updatePassRateStats(pass_rate_stats)
        self.loadReviewLists()

    def updateSummaryCards(self, comparison, recurrence_stats):
        self.updateStatCardValue(self.totalCard, str(comparison["total_completed"]))
        self.updateStatCardValue(self.passRateCard, f"{comparison['pass_rate']}%")
        self.updateStatCardValue(self.avgDurationCard, f"{comparison['avg_rectification_duration']}天")

        total_high_risk = sum(item["high_risk"] + item["medium_risk"] for item in recurrence_stats)
        total = sum(item["total"] for item in recurrence_stats)
        recurrence_rate = round(total_high_risk / total * 100, 1) if total > 0 else 0
        self.updateStatCardValue(self.recurrenceRateCard, f"{recurrence_rate}%")

        passed = sum(1 for _ in range(comparison["passed"]))
        self.updateStatCardValue(self.passedCard, str(comparison["passed"]))
        self.updateStatCardValue(self.partialCard, "0")
        self.updateStatCardValue(self.failedCard, str(comparison["failed"]))
        self.updateStatCardValue(self.followCard, str(comparison["need_follow"]))
        self.updateStatCardValue(self.notReviewedCard, str(comparison["not_reviewed"]))

    def updateStatCardValue(self, card, value):
        if hasattr(card, 'valueLabel'):
            card.valueLabel.setText(str(value))

    def updateComparisonPanels(self, pass_rate_stats):
        self.updateComparisonPanel("by_problem_type", pass_rate_stats["by_problem_type"])
        self.updateComparisonPanel("by_source", pass_rate_stats["by_source"])
        self.updateComparisonPanel("by_responsibility", pass_rate_stats["by_responsibility"])
        self.updateComparisonPanel("by_room_type", pass_rate_stats["by_room_type"])

    def updateComparisonPanel(self, data_key, data):
        layout = getattr(self, f"{data_key}_layout", None)
        if not layout:
            return

        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not data:
            emptyLabel = QLabel("暂无数据")
            emptyLabel.setStyleSheet("color: #999; font-size: 12px; padding: 10px;")
            emptyLabel.setAlignment(Qt.AlignCenter)
            layout.addWidget(emptyLabel)
            return

        max_total = max(item["total"] for item in data) if data else 1
        colors = ["#0078d4", "#107c10", "#d83b01", "#5c2d91", "#e81123", "#00b294", "#ffb900", "#8764b8"]

        for i, item in enumerate(data):
            bar_item = self.createPassRateBar(item, max_total, colors[i % len(colors)])
            layout.addWidget(bar_item)

    def createPassRateBar(self, item, max_total, color):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)

        headerRow = QHBoxLayout()
        headerRow.setSpacing(8)

        nameLabel = QLabel(item["name"][:12] + "..." if len(item["name"]) > 12 else item["name"])
        nameLabel.setStyleSheet("color: #333; font-size: 11px;")
        nameLabel.setFixedWidth(100)
        nameLabel.setToolTip(item["name"])
        headerRow.addWidget(nameLabel)

        countLabel = QLabel(f"{item['total']}条")
        countLabel.setStyleSheet("color: #666; font-size: 10px;")
        headerRow.addWidget(countLabel)

        passLabel = QLabel(f"通过率 {item['pass_rate']}%")
        passLabel.setStyleSheet(f"color: {color}; font-size: 10px; font-weight: bold;")
        headerRow.addWidget(passLabel)

        headerRow.addStretch()
        layout.addLayout(headerRow)

        barBg = QFrame()
        barBg.setFixedHeight(14)
        barBg.setStyleSheet("background-color: #f0f0f0; border-radius: 4px;")

        barLayout = QHBoxLayout(barBg)
        barLayout.setContentsMargins(0, 0, 0, 0)

        width_percent = (item["total"] / max_total * 100) if max_total > 0 else 0
        pass_width = int(width_percent * item["pass_rate"] / 100)
        fail_width = int(width_percent * item["fail_rate"] / 100)

        passFill = QFrame()
        passFill.setStyleSheet(f"background-color: {color}; border-radius: 4px 0 0 4px;")
        passFill.setMinimumWidth(max(1, pass_width))
        barLayout.addWidget(passFill)

        if fail_width > 0:
            failFill = QFrame()
            failFill.setStyleSheet(f"background-color: #e81123; border-radius: 0 4px 4px 0;")
            failFill.setMinimumWidth(max(1, fail_width))
            barLayout.addWidget(failFill)

        barLayout.addStretch()

        layout.addWidget(barBg)

        return widget

    def updateRecurrenceTable(self, recurrence_stats):
        self.recurrenceTable.setRowCount(0)
        for item in recurrence_stats:
            row = self.recurrenceTable.rowCount()
            self.recurrenceTable.insertRow(row)

            self.recurrenceTable.setItem(row, 0, QTableWidgetItem(item["problem_type"]))
            self.recurrenceTable.setItem(row, 1, QTableWidgetItem(str(item["total"])))

            high_item = QTableWidgetItem(str(item["high_risk"]))
            high_item.setForeground(QColor(RECURRENCE_LEVELS["高"]))
            self.recurrenceTable.setItem(row, 2, high_item)

            medium_item = QTableWidgetItem(str(item["medium_risk"]))
            medium_item.setForeground(QColor(RECURRENCE_LEVELS["中"]))
            self.recurrenceTable.setItem(row, 3, medium_item)

            low_item = QTableWidgetItem(str(item["low_risk"]))
            low_item.setForeground(QColor(RECURRENCE_LEVELS["低"]))
            self.recurrenceTable.setItem(row, 4, low_item)

            none_item = QTableWidgetItem(str(item["no_risk"]))
            none_item.setForeground(QColor(RECURRENCE_LEVELS["无"]))
            self.recurrenceTable.setItem(row, 5, none_item)

            rate_item = QTableWidgetItem(f"{item['recurrence_rate']}%")
            rate_color = self._getRateColor(item["recurrence_rate"])
            rate_item.setForeground(QColor(rate_color))
            rate_item.setFont(rate_item.font())
            self.recurrenceTable.setItem(row, 6, rate_item)

    def _getRateColor(self, rate):
        if rate >= 50:
            return RECURRENCE_LEVELS["高"]
        elif rate >= 30:
            return RECURRENCE_LEVELS["中"]
        elif rate >= 10:
            return RECURRENCE_LEVELS["低"]
        else:
            return RECURRENCE_LEVELS["无"]

    def updateRecurrenceList(self, high_risk):
        while self.recurrenceListLayout.count():
            item = self.recurrenceListLayout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not high_risk:
            emptyLabel = QLabel("暂无高风险回潮问题")
            emptyLabel.setStyleSheet("color: #999; font-size: 12px; padding: 10px;")
            emptyLabel.setAlignment(Qt.AlignCenter)
            self.recurrenceListLayout.addWidget(emptyLabel)
            return

        for i, item in enumerate(high_risk[:10]):
            risk_card = self.createHighRiskCard(item, i)
            self.recurrenceListLayout.addWidget(risk_card)

    def createHighRiskCard(self, item, index):
        card = CardWidget()
        card.setStyleSheet("background-color: #fff5f5; border: 1px solid #fecaca;")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)

        headerRow = QHBoxLayout()
        headerRow.setSpacing(8)

        badgeLabel = QLabel(f"⚠️ #{index + 1}")
        badgeLabel.setStyleSheet("color: #dc2626; font-size: 12px; font-weight: bold;")
        headerRow.addWidget(badgeLabel)

        roomLabel = QLabel(f"房间 {item['room_no']}")
        roomLabel.setStyleSheet("color: #1a1a1a; font-size: 12px; font-weight: bold;")
        headerRow.addWidget(roomLabel)

        typeLabel = QLabel(item["problem_type"])
        typeLabel.setStyleSheet("color: #dc2626; font-size: 11px;")
        headerRow.addWidget(typeLabel)

        headerRow.addStretch()

        countLabel = QLabel(f"重复 {item['count']} 次")
        countLabel.setStyleSheet("color: #dc2626; font-size: 12px; font-weight: bold;")
        headerRow.addWidget(countLabel)

        layout.addLayout(headerRow)

        summary = item['summaries'][0][:30] + "..." if len(item['summaries'][0]) > 30 else item['summaries'][0]
        summaryLabel = QLabel(summary)
        summaryLabel.setStyleSheet("color: #666; font-size: 11px;")
        summaryLabel.setWordWrap(True)
        layout.addWidget(summaryLabel)

        dateLabel = QLabel(f"最近发生: {item['last_date']}")
        dateLabel.setStyleSheet("color: #999; font-size: 10px;")
        layout.addWidget(dateLabel)

        return card

    def updateDurationStats(self, duration_stats):
        overall = duration_stats["overall"]
        self.avgDurationDetail.valueLabel.setText(f"{overall['avg_duration']}天")
        self.maxDurationDetail.valueLabel.setText(f"{overall['max_duration']}天")
        self.minDurationDetail.valueLabel.setText(f"{overall['min_duration']}天")
        self.totalCountDetail.valueLabel.setText(f"{overall['total_count']}个")

        self.durationTable.setRowCount(0)
        for item in duration_stats["by_problem"]:
            row = self.durationTable.rowCount()
            self.durationTable.insertRow(row)

            self.durationTable.setItem(row, 0, QTableWidgetItem(item["problem_type"]))
            self.durationTable.setItem(row, 1, QTableWidgetItem(str(item["count"])))
            self.durationTable.setItem(row, 2, QTableWidgetItem(str(item["avg_duration"])))

            max_item = QTableWidgetItem(str(item["max_duration"]))
            max_item.setForeground(QColor("#e81123"))
            self.durationTable.setItem(row, 3, max_item)

            min_item = QTableWidgetItem(str(item["min_duration"]))
            min_item.setForeground(QColor("#107c10"))
            self.durationTable.setItem(row, 4, min_item)

    def updatePassRateStats(self, pass_rate_stats):
        self.passRateTable.setRowCount(0)
        for item in pass_rate_stats["by_problem_type"]:
            row = self.passRateTable.rowCount()
            self.passRateTable.insertRow(row)

            self.passRateTable.setItem(row, 0, QTableWidgetItem(item["name"]))
            self.passRateTable.setItem(row, 1, QTableWidgetItem(str(item["total"])))
            self.passRateTable.setItem(row, 2, QTableWidgetItem(str(item["passed"])))
            self.passRateTable.setItem(row, 3, QTableWidgetItem(str(item["failed"])))

            pass_item = QTableWidgetItem(f"{item['pass_rate']}%")
            pass_color = "#107c10" if item["pass_rate"] >= 80 else "#ffb900" if item["pass_rate"] >= 50 else "#e81123"
            pass_item.setForeground(QColor(pass_color))
            self.passRateTable.setItem(row, 4, pass_item)

            fail_item = QTableWidgetItem(f"{item['fail_rate']}%")
            fail_item.setForeground(QColor("#e81123"))
            self.passRateTable.setItem(row, 5, fail_item)

        while self.passRateDetailLayout.count():
            item = self.passRateDetailLayout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        detail_row = QWidget()
        detail_row_layout = QHBoxLayout(detail_row)
        detail_row_layout.setContentsMargins(0, 0, 0, 0)
        detail_row_layout.setSpacing(10)

        source_card = self.createPassRateSummaryCard("按来源", pass_rate_stats["by_source"][:3])
        detail_row_layout.addWidget(source_card, 1)

        resp_card = self.createPassRateSummaryCard("按责任", pass_rate_stats["by_responsibility"][:3])
        detail_row_layout.addWidget(resp_card, 1)

        room_card = self.createPassRateSummaryCard("按房型", pass_rate_stats["by_room_type"][:3])
        detail_row_layout.addWidget(room_card, 1)

        self.passRateDetailLayout.addWidget(detail_row)

    def createPassRateSummaryCard(self, title, items):
        card = CardWidget()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        titleLabel = StrongBodyLabel(f"📊 {title}")
        titleLabel.setStyleSheet("font-size: 13px; font-weight: bold; color: #1a1a1a;")
        layout.addWidget(titleLabel)

        if not items:
            emptyLabel = QLabel("暂无数据")
            emptyLabel.setStyleSheet("color: #999; font-size: 11px;")
            layout.addWidget(emptyLabel)
            return card

        for item in items:
            row = QHBoxLayout()
            row.setSpacing(6)

            name = item["name"][:8] + "..." if len(item["name"]) > 8 else item["name"]
            nameLabel = QLabel(name)
            nameLabel.setStyleSheet("color: #666; font-size: 11px;")
            nameLabel.setFixedWidth(70)
            nameLabel.setToolTip(item["name"])
            row.addWidget(nameLabel)

            rate_color = "#107c10" if item["pass_rate"] >= 80 else "#ffb900" if item["pass_rate"] >= 50 else "#e81123"
            rateLabel = QLabel(f"{item['pass_rate']}%")
            rateLabel.setStyleSheet(f"color: {rate_color}; font-size: 11px; font-weight: bold;")
            row.addWidget(rateLabel)

            row.addStretch()
            layout.addLayout(row)

        return card

    def loadReviewLists(self):
        unreviewed = self.dao.get_unreviewed_completed()
        reviewed = self.dao.get_reviewed_reviews()

        self.unreviewedCountLabel.setText(f"{len(unreviewed)}条")
        self.reviewedCountLabel.setText(f"{len(reviewed)}条")

        self.unreviewedTable.setRowCount(0)
        for review in unreviewed:
            row = self.unreviewedTable.rowCount()
            self.unreviewedTable.insertRow(row)

            item0 = QTableWidgetItem(review.record_no)
            item0.setData(Qt.UserRole, review)
            self.unreviewedTable.setItem(row, 0, item0)

            self.unreviewedTable.setItem(row, 1, QTableWidgetItem(review.stay_date))
            self.unreviewedTable.setItem(row, 2, QTableWidgetItem(review.room_no))
            self.unreviewedTable.setItem(row, 3, QTableWidgetItem(review.problem_type))
            self.unreviewedTable.setItem(row, 4, QTableWidgetItem(review.source))
            self.unreviewedTable.setItem(row, 5, QTableWidgetItem(review.responsibility))
            self.unreviewedTable.setItem(row, 6, QTableWidgetItem(review.updated_at[:10]))

        self.reviewedTable.setRowCount(0)
        for review, analysis in reviewed:
            row = self.reviewedTable.rowCount()
            self.reviewedTable.insertRow(row)

            item0 = QTableWidgetItem(review.record_no)
            item0.setData(Qt.UserRole, (review, analysis))
            self.reviewedTable.setItem(row, 0, item0)

            conclusion_item = QTableWidgetItem(analysis.review_conclusion)
            conclusion_color = self._getConclusionColor(analysis.review_conclusion)
            conclusion_item.setForeground(QColor(conclusion_color))
            self.reviewedTable.setItem(row, 1, conclusion_item)

            risk_item = QTableWidgetItem(analysis.recurrence_risk)
            risk_color = RECURRENCE_LEVELS.get(analysis.recurrence_risk, "#666")
            risk_item.setForeground(QColor(risk_color))
            self.reviewedTable.setItem(row, 2, risk_item)

            self.reviewedTable.setItem(row, 3, QTableWidgetItem(analysis.reviewer or "-"))
            self.reviewedTable.setItem(row, 4, QTableWidgetItem(analysis.reviewed_at[:16]))

            btnWidget = QWidget()
            btnLayout = QHBoxLayout(btnWidget)
            btnLayout.setContentsMargins(5, 2, 5, 2)
            btnLayout.setSpacing(5)

            editBtn = PushButton("编辑")
            editBtn.setFixedSize(50, 28)
            editBtn.clicked.connect(lambda _=False, r=review, a=analysis: self.editReview(r, a))
            btnLayout.addWidget(editBtn)

            deleteBtn = PushButton("删除")
            deleteBtn.setFixedSize(50, 28)
            deleteBtn.clicked.connect(lambda _=False, a=analysis: self.deleteReview(a))
            btnLayout.addWidget(deleteBtn)

            self.reviewedTable.setCellWidget(row, 5, btnWidget)

        self.current_unreviewed = unreviewed
        self.current_reviewed = reviewed

    def _getConclusionColor(self, conclusion):
        if conclusion == "整改有效":
            return "#107c10"
        elif conclusion == "整改部分有效":
            return "#ffb900"
        elif conclusion == "整改无效":
            return "#e81123"
        else:
            return "#5c2d91"

    def onUnreviewedSelectionChanged(self):
        pass

    def onReviewedSelectionChanged(self):
        current_row = self.reviewedTable.currentRow()
        if current_row < 0:
            self.experienceDetail.setText("选择一条已复盘记录查看详情")
            self.preventionDetail.setText("")
            return

        item = self.reviewedTable.item(current_row, 0)
        if not item:
            return

        data = item.data(Qt.UserRole)
        if not data:
            return

        review, analysis = data
        exp_text = f"<b>经验沉淀：</b><br>{analysis.experience_summary or '无'}" if analysis.experience_summary else "<b>经验沉淀：</b>无"
        prev_text = f"<b>预防建议：</b><br>{analysis.prevention_measures or '无'}" if analysis.prevention_measures else "<b>预防建议：</b>无"

        self.experienceDetail.setText(exp_text)
        self.experienceDetail.setTextFormat(Qt.RichText)
        self.preventionDetail.setText(prev_text)
        self.preventionDetail.setTextFormat(Qt.RichText)

    def createReview(self):
        current_row = self.unreviewedTable.currentRow()
        if current_row < 0:
            QMessageBox.information(self, "提示", "请先选择一条待复盘的记录")
            return

        item = self.unreviewedTable.item(current_row, 0)
        if not item:
            return

        review = item.data(Qt.UserRole)
        if not review:
            return

        dialog = ReviewAnalysisDialog(review=review, parent=self)
        if dialog.exec():
            created, validation = self.dao.create(dialog.analysis)
            if validation:
                InfoBar.success(
                    title="保存成功",
                    content="复盘记录已添加",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=3000,
                    parent=self
                )
                self.loadData()
            else:
                QMessageBox.warning(self, "保存失败", "\n".join(validation.errors))

    def editReview(self, review: BadReview, analysis: RectificationReview):
        dialog = ReviewAnalysisDialog(review=review, analysis=analysis, parent=self)
        if dialog.exec():
            updated, validation = self.dao.update(dialog.analysis)
            if validation:
                InfoBar.success(
                    title="更新成功",
                    content="复盘记录已更新",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=3000,
                    parent=self
                )
                self.loadData()
            else:
                QMessageBox.warning(self, "更新失败", "\n".join(validation.errors))

    def deleteReview(self, analysis: RectificationReview):
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除这条复盘记录吗？\n\n记录编号：{analysis.record_no}",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.dao.delete(analysis.id)
            InfoBar.success(
                title="删除成功",
                content="复盘记录已删除",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
            self.loadData()

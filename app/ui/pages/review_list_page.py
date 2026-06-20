from PySide6.QtCore import Qt, QSize, QRegularExpression
from PySide6.QtGui import QRegularExpressionValidator, QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QLabel, QAbstractItemView
)
from qfluentwidgets import (
    PushButton, LineEdit, ComboBox, PrimaryPushButton,
    InfoBar, InfoBarPosition, FluentIcon as FIF
)

from app.dao.review_dao import ReviewDAO
from app.dao.warning_dao import WarningDAO
from app.models.models import BadReview
from app.ui.dialogs.review_dialog import ReviewDialog
from app.utils.signal_bus import SignalBus
from app.utils.constants import PROBLEM_TYPES, REVIEW_SOURCES, RECTIFICATION_STATUSES, WARNING_TYPES, WARNING_TYPE_COLORS


class ReviewListPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("reviewListPage")
        self.dao = ReviewDAO()
        self.warning_dao = WarningDAO()
        self.signalBus = SignalBus()
        self.initUI()
        self.refresh()

    def initUI(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        headerLayout = QHBoxLayout()
        headerLayout.setSpacing(10)

        title = QLabel("差评记录管理")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #1a1a1a;")
        headerLayout.addWidget(title)
        headerLayout.addStretch()

        self.searchEdit = LineEdit()
        self.searchEdit.setPlaceholderText("搜索记录编号或摘要...")
        self.searchEdit.setFixedWidth(280)
        self.searchEdit.textChanged.connect(self.onSearch)
        headerLayout.addWidget(self.searchEdit)

        self.addBtn = PrimaryPushButton("新增记录", self)
        self.addBtn.setIcon(FIF.ADD)
        self.addBtn.clicked.connect(self.addReview)
        headerLayout.addWidget(self.addBtn)

        layout.addLayout(headerLayout)

        filterLayout = QHBoxLayout()
        filterLayout.setSpacing(10)

        filterLayout.addWidget(QLabel("问题类型："))
        self.problemTypeFilter = ComboBox()
        self.problemTypeFilter.addItem("全部", "")
        for t in PROBLEM_TYPES:
            self.problemTypeFilter.addItem(t, t)
        self.problemTypeFilter.currentIndexChanged.connect(self.onFilter)
        filterLayout.addWidget(self.problemTypeFilter)

        filterLayout.addWidget(QLabel("整改状态："))
        self.statusFilter = ComboBox()
        self.statusFilter.addItem("全部", "")
        for s in RECTIFICATION_STATUSES:
            self.statusFilter.addItem(s, s)
        self.statusFilter.currentIndexChanged.connect(self.onFilter)
        filterLayout.addWidget(self.statusFilter)

        filterLayout.addWidget(QLabel("差评来源："))
        self.sourceFilter = ComboBox()
        self.sourceFilter.addItem("全部", "")
        for s in REVIEW_SOURCES:
            self.sourceFilter.addItem(s, s)
        self.sourceFilter.currentIndexChanged.connect(self.onFilter)
        filterLayout.addWidget(self.sourceFilter)

        filterLayout.addWidget(QLabel("房间号："))
        self.roomFilter = LineEdit()
        self.roomFilter.setPlaceholderText("输入房间号")
        self.roomFilter.setFixedWidth(120)
        room_regex = QRegularExpression(r'^[A-Za-z0-9\-]{0,10}$')
        self.roomFilter.setValidator(QRegularExpressionValidator(room_regex, self))
        self.roomFilter.textChanged.connect(self.onFilter)
        filterLayout.addWidget(self.roomFilter)

        filterLayout.addWidget(QLabel("预警："))
        self.warningFilter = ComboBox()
        self.warningFilter.addItem("全部", "")
        self.warningFilter.addItem("有预警", "has_warning")
        for wt in WARNING_TYPES:
            self.warningFilter.addItem(wt, wt)
        self.warningFilter.currentIndexChanged.connect(self.onFilter)
        filterLayout.addWidget(self.warningFilter)

        self.refreshBtn = PushButton("刷新")
        self.refreshBtn.setIcon(FIF.SYNC)
        self.refreshBtn.clicked.connect(self.refresh)
        filterLayout.addWidget(self.refreshBtn)

        filterLayout.addStretch()
        layout.addLayout(filterLayout)

        self.table = QTableWidget()
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)

        headers = [
            "记录编号", "入住日期", "房间号", "差评来源",
            "问题类型", "差评摘要", "责任归因", "整改状态",
            "复查结果", "预警", "创建时间", "操作"
        ]
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.Stretch)
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(8, QHeaderView.Stretch)
        header.setSectionResizeMode(9, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(10, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(11, QHeaderView.ResizeToContents)

        layout.addWidget(self.table, 1)

    def getFilters(self):
        filters = {}
        pt = self.problemTypeFilter.currentData()
        if pt:
            filters["problem_type"] = pt
        st = self.statusFilter.currentData()
        if st:
            filters["rectification_status"] = st
        sc = self.sourceFilter.currentData()
        if sc:
            filters["source"] = sc
        rn = self.roomFilter.text().strip()
        if rn:
            filters["room_no"] = rn
        return filters

    def getWarningFilter(self):
        return self.warningFilter.currentData()

    def onSearch(self):
        self.loadData()

    def onFilter(self):
        self.loadData()

    def refresh(self):
        self.searchEdit.clear()
        self.problemTypeFilter.setCurrentIndex(0)
        self.statusFilter.setCurrentIndex(0)
        self.sourceFilter.setCurrentIndex(0)
        self.roomFilter.clear()
        self.warningFilter.setCurrentIndex(0)
        self.loadData()

    def loadData(self):
        keyword = self.searchEdit.text().strip()
        filters = self.getFilters()
        warning_filter = self.getWarningFilter()
        reviews = self.dao.get_all(filters=filters, keyword=keyword)

        if warning_filter:
            review_ids = [r.id for r in reviews]
            warnings_by_review = self.warning_dao.get_active_warnings_for_reviews(review_ids)

            if warning_filter == "has_warning":
                reviews = [r for r in reviews if r.id in warnings_by_review and warnings_by_review[r.id]]
            else:
                reviews = [r for r in reviews if r.id in warnings_by_review and
                           any(w.warning_type == warning_filter for w in warnings_by_review[r.id])]

        self.table.setRowCount(0)
        review_ids = [r.id for r in reviews]
        warnings_by_review = self.warning_dao.get_active_warnings_for_reviews(review_ids)

        for review in reviews:
            self.addTableRow(review, warnings_by_review.get(review.id, []))

        InfoBar.success(
            title="加载成功",
            content=f"共 {len(reviews)} 条记录",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self
        )

    def addTableRow(self, review: BadReview, warnings=None):
        row = self.table.rowCount()
        self.table.insertRow(row)

        self.table.setItem(row, 0, QTableWidgetItem(review.record_no))
        self.table.setItem(row, 1, QTableWidgetItem(review.stay_date))
        self.table.setItem(row, 2, QTableWidgetItem(review.room_no))
        self.table.setItem(row, 3, QTableWidgetItem(review.source))
        self.table.setItem(row, 4, QTableWidgetItem(review.problem_type))
        self.table.setItem(row, 5, QTableWidgetItem(review.summary))
        self.table.setItem(row, 6, QTableWidgetItem(review.responsibility))

        statusItem = QTableWidgetItem(review.rectification_status)
        if review.rectification_status == "已完成":
            statusItem.setForeground(Qt.darkGreen)
        elif review.rectification_status == "整改中":
            statusItem.setForeground(Qt.darkBlue)
        else:
            statusItem.setForeground(Qt.darkRed)
        self.table.setItem(row, 7, statusItem)

        self.table.setItem(row, 8, QTableWidgetItem(review.review_result))

        if warnings:
            warning_types = "、".join([w.warning_type for w in warnings])
            warning_item = QTableWidgetItem(f"⚠ {warning_types}")
            color = WARNING_TYPE_COLORS.get(warnings[0].warning_type, "#e74c3c")
            warning_item.setForeground(QColor(color))
            self.table.setItem(row, 9, warning_item)
        else:
            self.table.setItem(row, 9, QTableWidgetItem(""))

        self.table.setItem(row, 10, QTableWidgetItem(review.created_at[:16]))

        btnWidget = QWidget()
        btnLayout = QHBoxLayout(btnWidget)
        btnLayout.setContentsMargins(5, 2, 5, 2)
        btnLayout.setSpacing(5)

        editBtn = PushButton("编辑")
        editBtn.setFixedSize(50, 28)
        editBtn.clicked.connect(lambda _=False, r=review: self.editReview(r))
        btnLayout.addWidget(editBtn)

        deleteBtn = PushButton("删除")
        deleteBtn.setFixedSize(50, 28)
        deleteBtn.clicked.connect(lambda _=False, r=review: self.deleteReview(r))
        btnLayout.addWidget(deleteBtn)

        self.table.setCellWidget(row, 11, btnWidget)

    def addReview(self):
        dialog = ReviewDialog(parent=self)
        if dialog.exec():
            review, validation = self.dao.create(dialog.review)
            if validation:
                InfoBar.success(
                    title="保存成功",
                    content="差评记录已添加",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=3000,
                    parent=self
                )
                self.loadData()
                self.signalBus.notifyChanged()
            else:
                QMessageBox.warning(self, "保存失败", "\n".join(validation.errors))

    def editReview(self, review: BadReview):
        dialog = ReviewDialog(review=review, parent=self)
        if dialog.exec():
            updated, validation = self.dao.update(dialog.review)
            if validation:
                InfoBar.success(
                    title="更新成功",
                    content="差评记录已更新",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=3000,
                    parent=self
                )
                self.loadData()
                self.signalBus.notifyChanged()
            else:
                QMessageBox.warning(self, "更新失败", "\n".join(validation.errors))

    def deleteReview(self, review: BadReview):
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除记录 {review.record_no} 吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.dao.delete(review.id)
            InfoBar.success(
                title="删除成功",
                content="差评记录已删除",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
            self.loadData()
            self.signalBus.notifyChanged()

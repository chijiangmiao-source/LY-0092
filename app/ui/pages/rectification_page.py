from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QLabel, QAbstractItemView, QSplitter,
    QTextEdit
)
from qfluentwidgets import (
    PushButton, PrimaryPushButton,
    InfoBar, InfoBarPosition, FluentIcon as FIF,
    TabWidget, SubtitleLabel, StrongBodyLabel, BodyLabel
)

from app.dao.review_dao import ReviewDAO
from app.models.models import BadReview
from app.ui.dialogs.review_dialog import ReviewDialog
from app.utils.signal_bus import SignalBus


class RectificationPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("rectificationPage")
        self.dao = ReviewDAO()
        self.signalBus = SignalBus()
        self.signalBus.dataChanged.connect(self.refresh)
        self.initUI()
        self.refresh()

    def initUI(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        headerLayout = QHBoxLayout()
        title = QLabel("整改任务维护")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #1a1a1a;")
        headerLayout.addWidget(title)
        headerLayout.addStretch()

        self.refreshBtn = PushButton("刷新")
        self.refreshBtn.setIcon(FIF.SYNC)
        self.refreshBtn.clicked.connect(self.refresh)
        headerLayout.addWidget(self.refreshBtn)

        layout.addLayout(headerLayout)

        statsLayout = QHBoxLayout()
        statsLayout.setSpacing(15)

        self.pendingCard = self.createStatCard("待整改", "0", "#ff4757")
        self.inProgressCard = self.createStatCard("整改中", "0", "#ffa502")
        self.completedCard = self.createStatCard("已完成", "0", "#2ed573")

        statsLayout.addWidget(self.pendingCard)
        statsLayout.addWidget(self.inProgressCard)
        statsLayout.addWidget(self.completedCard)
        statsLayout.addStretch()

        layout.addLayout(statsLayout)

        self.tabWidget = TabWidget(self)

        self.pendingPage = self.createTaskPage("pending")
        self.inProgressPage = self.createTaskPage("in_progress")

        self.tabWidget.addTab(self.pendingPage, "待整改任务")
        self.tabWidget.addTab(self.inProgressPage, "整改中任务")

        self.tabWidget.currentChanged.connect(self.onTabChanged)

        layout.addWidget(self.tabWidget, 1)

    def createStatCard(self, title, value, color):
        card = QWidget()
        card.setStyleSheet(f"""
            QWidget {{
                background-color: {color}20;
                border-radius: 8px;
                padding: 15px;
            }}
        """)
        cardLayout = QVBoxLayout(card)
        cardLayout.setSpacing(5)

        titleLabel = BodyLabel(title)
        titleLabel.setStyleSheet(f"color: {color}; font-size: 14px;")

        valueLabel = SubtitleLabel(value)
        valueLabel.setStyleSheet(f"color: {color}; font-size: 28px; font-weight: bold;")

        cardLayout.addWidget(titleLabel)
        cardLayout.addWidget(valueLabel)

        return card

    def createTaskPage(self, task_type):
        page = QWidget()
        pageLayout = QVBoxLayout(page)
        pageLayout.setContentsMargins(0, 10, 0, 0)
        pageLayout.setSpacing(10)

        if task_type == "pending":
            label_text = "待整改任务 - 需要分配处理人员和制定整改方案"
        else:
            label_text = "整改中任务 - 正在执行整改措施，需跟踪进度"

        hintLabel = StrongBodyLabel(label_text)
        hintLabel.setStyleSheet("color: #666;")
        pageLayout.addWidget(hintLabel)

        splitter = QSplitter(Qt.Horizontal)

        table = QTableWidget()
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setSelectionMode(QAbstractItemView.SingleSelection)
        table.setAlternatingRowColors(True)
        table.verticalHeader().setVisible(False)

        headers = ["记录编号", "入住日期", "房间号", "问题类型", "差评摘要", "责任归因"]
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)

        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.Stretch)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)

        detailPanel = QWidget()
        detailLayout = QVBoxLayout(detailPanel)
        detailLayout.setContentsMargins(15, 10, 10, 10)
        detailLayout.setSpacing(10)

        detailTitle = StrongBodyLabel("任务详情")
        detailLayout.addWidget(detailTitle)

        self.detailLabels = {}
        for field in ["record_no", "stay_date", "room_no", "source", "problem_type"]:
            rowLayout = QHBoxLayout()
            label = BodyLabel(self.getFieldLabel(field))
            label.setFixedWidth(80)
            value = BodyLabel("-")
            value.setWordWrap(True)
            self.detailLabels[field] = value
            rowLayout.addWidget(label)
            rowLayout.addWidget(value, 1)
            detailLayout.addLayout(rowLayout)

        detailLayout.addWidget(StrongBodyLabel("差评摘要："))
        self.summaryDetail = QTextEdit()
        self.summaryDetail.setReadOnly(True)
        self.summaryDetail.setFixedHeight(80)
        detailLayout.addWidget(self.summaryDetail)

        detailLayout.addWidget(StrongBodyLabel("责任归因："))
        self.responsibilityDetail = BodyLabel("-")
        self.responsibilityDetail.setWordWrap(True)
        detailLayout.addWidget(self.responsibilityDetail)

        detailLayout.addWidget(StrongBodyLabel("整改措施："))
        self.measureDetail = QTextEdit()
        self.measureDetail.setPlaceholderText("请输入整改措施...")
        self.measureDetail.setFixedHeight(100)
        detailLayout.addWidget(self.measureDetail)

        btnLayout = QHBoxLayout()
        btnLayout.setSpacing(10)

        self.editBtn = PrimaryPushButton("编辑完整信息")
        self.editBtn.setIcon(FIF.EDIT)
        self.editBtn.clicked.connect(lambda: self.editCurrentReview(task_type))
        btnLayout.addWidget(self.editBtn)

        if task_type == "pending":
            self.startBtn = PrimaryPushButton("开始整改")
            self.startBtn.setIcon(FIF.PLAY)
            self.startBtn.clicked.connect(lambda: self.updateStatus(task_type, "整改中"))
            btnLayout.addWidget(self.startBtn)
        else:
            self.completeBtn = PrimaryPushButton("完成整改")
            self.completeBtn.setIcon(FIF.ACCEPT)
            self.completeBtn.clicked.connect(lambda: self.completeTask(task_type))
            btnLayout.addWidget(self.completeBtn)

        btnLayout.addStretch()
        detailLayout.addLayout(btnLayout)
        detailLayout.addStretch()

        splitter.addWidget(table)
        splitter.addWidget(detailPanel)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)

        pageLayout.addWidget(splitter, 1)

        if task_type == "pending":
            self.pendingTable = table
            self.pendingDetailPanel = detailPanel
        else:
            self.inProgressTable = table
            self.inProgressDetailPanel = detailPanel

        table.itemSelectionChanged.connect(lambda: self.onSelectionChanged(task_type))

        return page

    def getFieldLabel(self, field):
        labels = {
            "record_no": "记录编号：",
            "stay_date": "入住日期：",
            "room_no": "房间号：",
            "source": "差评来源：",
            "problem_type": "问题类型："
        }
        return labels.get(field, field)

    def onTabChanged(self, index):
        if index == 0:
            self.pendingTable.clearSelection()
        else:
            self.inProgressTable.clearSelection()
        self.clearDetail()

    def onSelectionChanged(self, task_type):
        table = self.pendingTable if task_type == "pending" else self.inProgressTable
        current_row = table.currentRow()

        if current_row < 0:
            self.clearDetail()
            return

        review = table.item(current_row, 0).data(Qt.UserRole)
        if not review:
            return

        self.detailLabels["record_no"].setText(review.record_no)
        self.detailLabels["stay_date"].setText(review.stay_date)
        self.detailLabels["room_no"].setText(review.room_no)
        self.detailLabels["source"].setText(review.source)
        self.detailLabels["problem_type"].setText(review.problem_type)
        self.summaryDetail.setPlainText(review.summary)
        self.responsibilityDetail.setText(review.responsibility)
        self.measureDetail.setPlainText(review.rectification_measure)

    def clearDetail(self):
        for label in self.detailLabels.values():
            label.setText("-")
        self.summaryDetail.clear()
        self.responsibilityDetail.setText("-")
        self.measureDetail.clear()

    def getCurrentReview(self, task_type):
        table = self.pendingTable if task_type == "pending" else self.inProgressTable
        current_row = table.currentRow()
        if current_row < 0:
            return None
        return table.item(current_row, 0).data(Qt.UserRole)

    def updateStatus(self, task_type, new_status):
        review = self.getCurrentReview(task_type)
        if not review:
            QMessageBox.information(self, "提示", "请先选择一条记录")
            return

        measure = self.measureDetail.toPlainText().strip()
        if not measure:
            QMessageBox.warning(self, "提示", "请先填写整改措施")
            return

        review.rectification_measure = measure
        review.rectification_status = new_status

        updated, validation = self.dao.update(review)
        if validation:
            InfoBar.success(
                title="操作成功",
                content=f"状态已更新为「{new_status}」",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
            self.refresh()
            self.signalBus.notifyChanged()
        else:
            QMessageBox.warning(self, "操作失败", "\n".join(validation.errors))

    def completeTask(self, task_type):
        review = self.getCurrentReview(task_type)
        if not review:
            QMessageBox.information(self, "提示", "请先选择一条记录")
            return

        dialog = ReviewDialog(review=review, parent=self)
        if dialog.exec():
            if dialog.review.rectification_status != "已完成":
                QMessageBox.information(self, "提示", "请将整改状态设置为「已完成」")
                return

            measure = self.measureDetail.toPlainText().strip()
            if measure:
                dialog.review.rectification_measure = measure

            updated, validation = self.dao.update(dialog.review)
            if validation:
                InfoBar.success(
                    title="操作成功",
                    content="整改已完成，复查结果已登记",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=3000,
                    parent=self
                )
                self.refresh()
                self.signalBus.notifyChanged()
            else:
                QMessageBox.warning(self, "操作失败", "\n".join(validation.errors))

    def editCurrentReview(self, task_type):
        review = self.getCurrentReview(task_type)
        if not review:
            QMessageBox.information(self, "提示", "请先选择一条记录")
            return

        dialog = ReviewDialog(review=review, parent=self)
        if dialog.exec():
            updated, validation = self.dao.update(dialog.review)
            if validation:
                InfoBar.success(
                    title="更新成功",
                    content="记录信息已更新",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=3000,
                    parent=self
                )
                self.refresh()
                self.signalBus.notifyChanged()
            else:
                QMessageBox.warning(self, "更新失败", "\n".join(validation.errors))

    def refresh(self):
        pending = self.dao.get_pending_tasks()
        in_progress = self.dao.get_in_progress_tasks()

        self.updateStatCards(len(pending), len(in_progress),
                             self.dao.get_statistics()["completed"])

        self.loadTableData(self.pendingTable, pending)
        self.loadTableData(self.inProgressTable, in_progress)

        self.clearDetail()

    def updateStatCards(self, pending, in_progress, completed):
        self.pendingCard.findChild(SubtitleLabel).setText(str(pending))
        self.inProgressCard.findChild(SubtitleLabel).setText(str(in_progress))
        self.completedCard.findChild(SubtitleLabel).setText(str(completed))

    def loadTableData(self, table, reviews):
        table.setRowCount(0)
        for review in reviews:
            row = table.rowCount()
            table.insertRow(row)

            item0 = QTableWidgetItem(review.record_no)
            item0.setData(Qt.UserRole, review)
            table.setItem(row, 0, item0)

            table.setItem(row, 1, QTableWidgetItem(review.stay_date))
            table.setItem(row, 2, QTableWidgetItem(review.room_no))
            table.setItem(row, 3, QTableWidgetItem(review.problem_type))
            table.setItem(row, 4, QTableWidgetItem(review.summary))
            table.setItem(row, 5, QTableWidgetItem(review.responsibility))

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QLabel,
    QAbstractItemView, QSplitter
)
from qfluentwidgets import (
    PushButton, PrimaryPushButton, ComboBox,
    InfoBar, InfoBarPosition, FluentIcon as FIF,
    StrongBodyLabel, BodyLabel, SubtitleLabel, CardWidget
)

from app.dao.topic_dao import TopicDAO
from app.models.models import SpecialTopic


class TopicPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("topicPage")
        self.dao = TopicDAO()
        self.initUI()
        self.refresh()

    def initUI(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        headerLayout = QHBoxLayout()
        title = QLabel("重点整改专题")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        headerLayout.addWidget(title)
        headerLayout.addStretch()

        self.statusFilter = ComboBox()
        self.statusFilter.addItem("全部专题", "")
        self.statusFilter.addItem("进行中", "进行中")
        self.statusFilter.addItem("已关闭", "已关闭")
        self.statusFilter.currentIndexChanged.connect(self.onFilter)
        headerLayout.addWidget(self.statusFilter)

        self.refreshBtn = PushButton("刷新")
        self.refreshBtn.setIcon(FIF.SYNC)
        self.refreshBtn.clicked.connect(self.refresh)
        headerLayout.addWidget(self.refreshBtn)

        layout.addLayout(headerLayout)

        hintLabel = BodyLabel("系统自动检测：当同一问题类型连续出现3条差评时，将自动创建重点整改专题")
        hintLabel.setStyleSheet("color: #e74c3c; padding: 10px; background-color: #fdecea; border-radius: 4px;")
        hintLabel.setWordWrap(True)
        layout.addWidget(hintLabel)

        splitter = QSplitter(Qt.Horizontal)

        leftPanel = QWidget()
        leftLayout = QVBoxLayout(leftPanel)
        leftLayout.setContentsMargins(0, 0, 0, 0)
        leftLayout.setSpacing(10)

        leftTitle = StrongBodyLabel("专题列表")
        leftLayout.addWidget(leftTitle)

        self.topicList = QListWidget()
        self.topicList.setSelectionMode(QAbstractItemView.SingleSelection)
        self.topicList.currentItemChanged.connect(self.onTopicSelected)
        leftLayout.addWidget(self.topicList, 1)

        splitter.addWidget(leftPanel)

        rightPanel = QWidget()
        rightLayout = QVBoxLayout(rightPanel)
        rightLayout.setContentsMargins(15, 0, 0, 0)
        rightLayout.setSpacing(15)

        self.detailCard = CardWidget()
        detailCardLayout = QVBoxLayout(self.detailCard)
        detailCardLayout.setContentsMargins(20, 20, 20, 20)
        detailCardLayout.setSpacing(10)

        self.topicNameLabel = SubtitleLabel("请选择一个专题查看详情")
        self.topicNameLabel.setStyleSheet("font-size: 18px; font-weight: bold;")
        detailCardLayout.addWidget(self.topicNameLabel)

        self.topicInfoLayout = QVBoxLayout()
        self.topicInfoLayout.setSpacing(8)

        self.triggerReasonLabel = BodyLabel("")
        self.triggerReasonLabel.setWordWrap(True)
        self.statusLabel = BodyLabel("")
        self.createdAtLabel = BodyLabel("")
        self.closedAtLabel = BodyLabel("")
        self.countLabel = BodyLabel("")

        self.topicInfoLayout.addWidget(self.triggerReasonLabel)
        self.topicInfoLayout.addWidget(self.statusLabel)
        self.topicInfoLayout.addWidget(self.createdAtLabel)
        self.topicInfoLayout.addWidget(self.closedAtLabel)
        self.topicInfoLayout.addWidget(self.countLabel)

        detailCardLayout.addLayout(self.topicInfoLayout)

        btnLayout = QHBoxLayout()
        btnLayout.setSpacing(10)

        self.toggleStatusBtn = PrimaryPushButton("")
        self.toggleStatusBtn.clicked.connect(self.toggleTopicStatus)
        self.toggleStatusBtn.setEnabled(False)
        btnLayout.addWidget(self.toggleStatusBtn)

        self.deleteBtn = PushButton("删除专题")
        self.deleteBtn.setIcon(FIF.DELETE)
        self.deleteBtn.clicked.connect(self.deleteTopic)
        self.deleteBtn.setEnabled(False)
        btnLayout.addWidget(self.deleteBtn)

        btnLayout.addStretch()
        detailCardLayout.addLayout(btnLayout)

        rightLayout.addWidget(self.detailCard)

        self.reviewTable = QTableWidget()
        self.reviewTable.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.reviewTable.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.reviewTable.setAlternatingRowColors(True)
        self.reviewTable.verticalHeader().setVisible(False)

        headers = ["记录编号", "入住日期", "房间号", "问题类型", "差评摘要", "整改状态"]
        self.reviewTable.setColumnCount(len(headers))
        self.reviewTable.setHorizontalHeaderLabels(headers)

        header = self.reviewTable.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.Stretch)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)

        rightLayout.addWidget(StrongBodyLabel("关联差评记录"), 0)
        rightLayout.addWidget(self.reviewTable, 1)

        splitter.addWidget(rightPanel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)

        layout.addWidget(splitter, 1)

    def onFilter(self):
        self.loadTopics()

    def refresh(self):
        self.statusFilter.setCurrentIndex(0)
        self.loadTopics()

    def loadTopics(self):
        status = self.statusFilter.currentData()
        if status:
            topics = self.dao.get_all(status=status)
        else:
            topics = self.dao.get_all()

        self.topicList.clear()
        for topic in topics:
            item = QListWidgetItem()
            item.setData(Qt.UserRole, topic)

            status_icon = "🔴" if topic.status == "进行中" else "🟢"
            item.setText(f"{status_icon} {topic.topic_name} ({len(topic.review_ids)}条)")

            self.topicList.addItem(item)

        self.clearDetail()

    def onTopicSelected(self, current, previous):
        if not current:
            self.clearDetail()
            return

        topic = current.data(Qt.UserRole)
        if not topic:
            return

        self.topicNameLabel.setText(topic.topic_name)
        self.triggerReasonLabel.setText(f"触发原因：{topic.trigger_reason}")
        self.statusLabel.setText(f"专题状态：{topic.status}")
        self.createdAtLabel.setText(f"创建时间：{topic.created_at[:16]}")

        if topic.closed_at:
            self.closedAtLabel.setText(f"关闭时间：{topic.closed_at[:16]}")
            self.closedAtLabel.setVisible(True)
        else:
            self.closedAtLabel.setVisible(False)

        self.countLabel.setText(f"关联记录数：{len(topic.review_ids)} 条")

        if topic.status == "进行中":
            self.toggleStatusBtn.setText("关闭专题")
            self.toggleStatusBtn.setIcon(FIF.ACCEPT)
        else:
            self.toggleStatusBtn.setText("重新开启")
            self.toggleStatusBtn.setIcon(FIF.PLAY)

        self.toggleStatusBtn.setEnabled(True)
        self.deleteBtn.setEnabled(True)

        self.loadTopicReviews(topic.id)

    def clearDetail(self):
        self.topicNameLabel.setText("请选择一个专题查看详情")
        self.triggerReasonLabel.setText("")
        self.statusLabel.setText("")
        self.createdAtLabel.setText("")
        self.closedAtLabel.setText("")
        self.countLabel.setText("")
        self.toggleStatusBtn.setEnabled(False)
        self.deleteBtn.setEnabled(False)
        self.reviewTable.setRowCount(0)

    def loadTopicReviews(self, topic_id):
        reviews = self.dao.get_topic_reviews(topic_id)
        self.reviewTable.setRowCount(0)

        for review in reviews:
            row = self.reviewTable.rowCount()
            self.reviewTable.insertRow(row)

            self.reviewTable.setItem(row, 0, QTableWidgetItem(review.record_no))
            self.reviewTable.setItem(row, 1, QTableWidgetItem(review.stay_date))
            self.reviewTable.setItem(row, 2, QTableWidgetItem(review.room_no))
            self.reviewTable.setItem(row, 3, QTableWidgetItem(review.problem_type))
            self.reviewTable.setItem(row, 4, QTableWidgetItem(review.summary))

            statusItem = QTableWidgetItem(review.rectification_status)
            if review.rectification_status == "已完成":
                statusItem.setForeground(Qt.darkGreen)
            elif review.rectification_status == "整改中":
                statusItem.setForeground(Qt.darkBlue)
            else:
                statusItem.setForeground(Qt.darkRed)
            self.reviewTable.setItem(row, 5, statusItem)

    def getCurrentTopic(self) -> SpecialTopic:
        item = self.topicList.currentItem()
        if not item:
            return None
        return item.data(Qt.UserRole)

    def toggleTopicStatus(self):
        topic = self.getCurrentTopic()
        if not topic:
            return

        if topic.status == "进行中":
            reply = QMessageBox.question(
                self, "确认关闭",
                f"确定要关闭专题「{topic.topic_name}」吗？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.dao.close_topic(topic.id)
                InfoBar.success(
                    title="操作成功",
                    content="专题已关闭",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=3000,
                    parent=self
                )
        else:
            self.dao.reopen_topic(topic.id)
            InfoBar.success(
                title="操作成功",
                content="专题已重新开启",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )

        self.loadTopics()

    def deleteTopic(self):
        topic = self.getCurrentTopic()
        if not topic:
            return

        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除专题「{topic.topic_name}」吗？\n注意：删除后关联的差评记录不会被删除。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.dao.delete(topic.id)
            InfoBar.success(
                title="删除成功",
                content="专题已删除",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
            self.loadTopics()

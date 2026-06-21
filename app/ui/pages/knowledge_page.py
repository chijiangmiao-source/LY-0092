from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QLabel, QAbstractItemView
)
from qfluentwidgets import (
    PushButton, LineEdit, ComboBox, PrimaryPushButton,
    InfoBar, InfoBarPosition, FluentIcon as FIF
)

from app.dao.knowledge_dao import KnowledgeDAO
from app.models.models import RectificationKnowledge
from app.ui.dialogs.knowledge_dialog import KnowledgeDialog
from app.utils.constants import PROBLEM_TYPES


class KnowledgePage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("knowledgePage")
        self.dao = KnowledgeDAO()
        self.initUI()
        self.refresh()

    def initUI(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        headerLayout = QHBoxLayout()
        headerLayout.setSpacing(10)

        title = QLabel("整改知识库")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #1a1a1a;")
        headerLayout.addWidget(title)
        headerLayout.addStretch()

        self.searchEdit = LineEdit()
        self.searchEdit.setPlaceholderText("搜索场景、原因、措施、要点...")
        self.searchEdit.setFixedWidth(280)
        self.searchEdit.textChanged.connect(self.onSearch)
        headerLayout.addWidget(self.searchEdit)

        self.addBtn = PrimaryPushButton("新增知识", self)
        self.addBtn.setIcon(FIF.ADD)
        self.addBtn.clicked.connect(self.addKnowledge)
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

        self.refreshBtn = PushButton("刷新")
        self.refreshBtn.setIcon(FIF.SYNC)
        self.refreshBtn.clicked.connect(self.refresh)
        filterLayout.addWidget(self.refreshBtn)

        filterLayout.addStretch()

        self.statsLabel = QLabel("")
        self.statsLabel.setStyleSheet("color: #666; font-size: 12px;")
        filterLayout.addWidget(self.statsLabel)

        layout.addLayout(filterLayout)

        self.table = QTableWidget()
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)

        headers = [
            "ID", "问题类型", "典型场景", "原因分析",
            "推荐整改措施", "复查要点", "适用房型",
            "使用次数", "创建时间", "操作"
        ]
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.Stretch)
        header.setSectionResizeMode(5, QHeaderView.Stretch)
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(8, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(9, QHeaderView.ResizeToContents)

        layout.addWidget(self.table, 1)

    def getFilters(self):
        pt = self.problemTypeFilter.currentData()
        return pt if pt else ""

    def onSearch(self):
        self.loadData()

    def onFilter(self):
        self.loadData()

    def refresh(self):
        self.searchEdit.clear()
        self.problemTypeFilter.setCurrentIndex(0)
        self.loadData()

    def loadData(self):
        keyword = self.searchEdit.text().strip()
        problem_type = self.getFilters()
        knowledge_list = self.dao.get_all(problem_type=problem_type, keyword=keyword)

        self.table.setRowCount(0)
        for knowledge in knowledge_list:
            self.addTableRow(knowledge)

        stats = self.dao.get_statistics()
        self.statsLabel.setText(f"共 {stats['total']} 条知识")

    def addTableRow(self, knowledge: RectificationKnowledge):
        row = self.table.rowCount()
        self.table.insertRow(row)

        self.table.setItem(row, 0, QTableWidgetItem(str(knowledge.id)))
        self.table.setItem(row, 1, QTableWidgetItem(knowledge.problem_type))
        self.table.setItem(row, 2, QTableWidgetItem(knowledge.typical_scenario))
        self.table.setItem(row, 3, QTableWidgetItem(knowledge.cause_analysis))
        self.table.setItem(row, 4, QTableWidgetItem(knowledge.recommended_measures))
        self.table.setItem(row, 5, QTableWidgetItem(knowledge.review_points))
        self.table.setItem(row, 6, QTableWidgetItem(knowledge.applicable_rooms))

        useCountItem = QTableWidgetItem(str(knowledge.use_count))
        useCountItem.setForeground(QColor("#0078d4"))
        self.table.setItem(row, 7, useCountItem)

        self.table.setItem(row, 8, QTableWidgetItem(knowledge.created_at[:16]))

        btnWidget = QWidget()
        btnLayout = QHBoxLayout(btnWidget)
        btnLayout.setContentsMargins(5, 2, 5, 2)
        btnLayout.setSpacing(5)

        editBtn = PushButton("编辑")
        editBtn.setFixedSize(50, 28)
        editBtn.clicked.connect(lambda _=False, k=knowledge: self.editKnowledge(k))
        btnLayout.addWidget(editBtn)

        deleteBtn = PushButton("删除")
        deleteBtn.setFixedSize(50, 28)
        deleteBtn.clicked.connect(lambda _=False, k=knowledge: self.deleteKnowledge(k))
        btnLayout.addWidget(deleteBtn)

        self.table.setCellWidget(row, 9, btnWidget)

    def addKnowledge(self):
        dialog = KnowledgeDialog(parent=self)
        if dialog.exec():
            knowledge, validation = self.dao.create(dialog.knowledge)
            if validation:
                InfoBar.success(
                    title="保存成功",
                    content="整改知识已添加",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=3000,
                    parent=self
                )
                self.loadData()
            else:
                QMessageBox.warning(self, "保存失败", "\n".join(validation.errors))

    def editKnowledge(self, knowledge: RectificationKnowledge):
        dialog = KnowledgeDialog(knowledge=knowledge, parent=self)
        if dialog.exec():
            updated, validation = self.dao.update(dialog.knowledge)
            if validation:
                InfoBar.success(
                    title="更新成功",
                    content="整改知识已更新",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=3000,
                    parent=self
                )
                self.loadData()
            else:
                QMessageBox.warning(self, "更新失败", "\n".join(validation.errors))

    def deleteKnowledge(self, knowledge: RectificationKnowledge):
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除这条整改知识吗？\n\n类型：{knowledge.problem_type}\n场景：{knowledge.typical_scenario}",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.dao.delete(knowledge.id)
            InfoBar.success(
                title="删除成功",
                content="整改知识已删除",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
            self.loadData()

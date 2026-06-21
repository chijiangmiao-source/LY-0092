from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QLabel, QAbstractItemView, QFrame,
    QGraphicsDropShadowEffect
)
from qfluentwidgets import (
    PushButton, LineEdit, ComboBox, PrimaryPushButton,
    InfoBar, InfoBarPosition, FluentIcon as FIF, CardWidget
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
        self.current_filtered_count = 0
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

        self.statsWidget = self.createStatsWidget()
        layout.addWidget(self.statsWidget)

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

    def createStatsWidget(self):
        widget = QWidget()
        widgetLayout = QHBoxLayout(widget)
        widgetLayout.setContentsMargins(0, 0, 0, 0)
        widgetLayout.setSpacing(12)

        self.totalCard = self.createStatCard("知识总数", "0", "📚", "#0078d4")
        widgetLayout.addWidget(self.totalCard, 1)

        self.typeCard = self.createStatCard("分类数", "0", "📊", "#107c10")
        widgetLayout.addWidget(self.typeCard, 1)

        self.useCard = self.createStatCard("累计使用", "0", "🔥", "#d83b01")
        widgetLayout.addWidget(self.useCard, 1)

        self.filteredCard = self.createStatCard("当前筛选", "0", "🔍", "#5c2d91")
        widgetLayout.addWidget(self.filteredCard, 1)

        detailWidget = QWidget()
        detailLayout = QHBoxLayout(detailWidget)
        detailLayout.setContentsMargins(0, 0, 0, 0)
        detailLayout.setSpacing(12)

        self.categoryStatsCard = self.createCategoryStatsCard()
        detailLayout.addWidget(self.categoryStatsCard, 3)

        self.topUsedCard = self.createTopUsedCard()
        detailLayout.addWidget(self.topUsedCard, 2)

        mainWidget = QWidget()
        mainLayout = QVBoxLayout(mainWidget)
        mainLayout.setContentsMargins(0, 0, 0, 0)
        mainLayout.setSpacing(10)
        mainLayout.addWidget(widget)
        mainLayout.addWidget(detailWidget)

        return mainWidget

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

    def createCategoryStatsCard(self):
        card = CardWidget()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)

        titleLabel = QLabel("📊 分类统计")
        titleLabel.setStyleSheet("font-size: 14px; font-weight: bold; color: #1a1a1a;")
        layout.addWidget(titleLabel)

        self.categoryListWidget = QWidget()
        self.categoryListLayout = QVBoxLayout(self.categoryListWidget)
        self.categoryListLayout.setContentsMargins(0, 4, 0, 0)
        self.categoryListLayout.setSpacing(6)
        layout.addWidget(self.categoryListWidget, 1)

        return card

    def createTopUsedCard(self):
        card = CardWidget()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)

        titleLabel = QLabel("🔥 最常用知识 TOP5")
        titleLabel.setStyleSheet("font-size: 14px; font-weight: bold; color: #1a1a1a;")
        layout.addWidget(titleLabel)

        self.topUsedListWidget = QWidget()
        self.topUsedListLayout = QVBoxLayout(self.topUsedListWidget)
        self.topUsedListLayout.setContentsMargins(0, 4, 0, 0)
        self.topUsedListLayout.setSpacing(6)
        layout.addWidget(self.topUsedListWidget, 1)

        return card

    def updateCategoryStats(self, stats):
        while self.categoryListLayout.count():
            item = self.categoryListLayout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not stats["by_problem_type"]:
            emptyLabel = QLabel("暂无数据")
            emptyLabel.setStyleSheet("color: #999; font-size: 12px; padding: 10px;")
            emptyLabel.setAlignment(Qt.AlignCenter)
            self.categoryListLayout.addWidget(emptyLabel)
            return

        max_count = max(item["count"] for item in stats["by_problem_type"]) if stats["by_problem_type"] else 1
        colors = ["#0078d4", "#107c10", "#d83b01", "#5c2d91", "#e81123", "#00b294", "#ffb900", "#8764b8"]

        for i, item in enumerate(stats["by_problem_type"]):
            self.categoryListLayout.addWidget(
                self.createCategoryBar(
                    item["problem_type"],
                    item["count"],
                    item["total_uses"] or 0,
                    max_count,
                    colors[i % len(colors)]
                )
            )

    def createCategoryBar(self, name, count, total_uses, max_count, color):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)

        headerRow = QHBoxLayout()
        headerRow.setSpacing(8)

        nameLabel = QLabel(name)
        nameLabel.setStyleSheet("color: #333; font-size: 12px;")
        nameLabel.setFixedWidth(80)
        headerRow.addWidget(nameLabel)

        countLabel = QLabel(f"{count} 条")
        countLabel.setStyleSheet("color: #666; font-size: 11px;")
        headerRow.addWidget(countLabel)

        useLabel = QLabel(f"使用 {total_uses} 次")
        useLabel.setStyleSheet(f"color: {color}; font-size: 11px;")
        headerRow.addWidget(useLabel)

        headerRow.addStretch()
        layout.addLayout(headerRow)

        barBg = QFrame()
        barBg.setFixedHeight(8)
        barBg.setStyleSheet("background-color: #f0f0f0; border-radius: 4px;")

        barLayout = QHBoxLayout(barBg)
        barLayout.setContentsMargins(0, 0, 0, 0)

        barFill = QFrame()
        barFill.setStyleSheet(f"background-color: {color}; border-radius: 4px;")
        width_percent = (count / max_count * 100) if max_count > 0 else 0
        barFill.setMinimumWidth(max(2, int(width_percent)))
        barLayout.addWidget(barFill)
        barLayout.addStretch()

        layout.addWidget(barBg)

        return widget

    def updateTopUsed(self, most_used):
        while self.topUsedListLayout.count():
            item = self.topUsedListLayout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not most_used:
            emptyLabel = QLabel("暂无数据")
            emptyLabel.setStyleSheet("color: #999; font-size: 12px; padding: 10px;")
            emptyLabel.setAlignment(Qt.AlignCenter)
            self.topUsedListLayout.addWidget(emptyLabel)
            return

        medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
        for i, knowledge in enumerate(most_used):
            self.topUsedListLayout.addWidget(
                self.createTopUsedItem(
                    medals[i] if i < len(medals) else f"{i+1}.",
                    knowledge
                )
            )

    def createTopUsedItem(self, medal, knowledge):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.setSpacing(8)

        medalLabel = QLabel(medal)
        medalLabel.setFixedWidth(28)
        medalLabel.setAlignment(Qt.AlignCenter)
        medalLabel.setStyleSheet("font-size: 14px;")
        layout.addWidget(medalLabel)

        textLayout = QVBoxLayout()
        textLayout.setSpacing(0)
        textLayout.setContentsMargins(0, 0, 0, 0)

        scenarioLabel = QLabel(knowledge.typical_scenario[:25] + "..." if len(knowledge.typical_scenario) > 25 else knowledge.typical_scenario)
        scenarioLabel.setStyleSheet("color: #333; font-size: 12px;")
        textLayout.addWidget(scenarioLabel)

        typeLabel = QLabel(f"{knowledge.problem_type}")
        typeLabel.setStyleSheet("color: #999; font-size: 10px;")
        textLayout.addWidget(typeLabel)

        layout.addLayout(textLayout, 1)

        useLabel = QLabel(f"{knowledge.use_count} 次")
        useLabel.setStyleSheet("color: #d83b01; font-size: 12px; font-weight: bold;")
        useLabel.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        layout.addWidget(useLabel)

        return widget

    def updateStatCardValue(self, card, value):
        if hasattr(card, 'valueLabel'):
            card.valueLabel.setText(str(value))

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

        self.current_filtered_count = len(knowledge_list)

        self.table.setRowCount(0)
        for knowledge in knowledge_list:
            self.addTableRow(knowledge)

        stats = self.dao.get_statistics()

        self.updateStatCardValue(self.totalCard, stats["total"])
        self.updateStatCardValue(self.typeCard, len(stats["by_problem_type"]))
        total_uses = sum(item["total_uses"] or 0 for item in stats["by_problem_type"])
        self.updateStatCardValue(self.useCard, total_uses)
        self.updateStatCardValue(self.filteredCard, self.current_filtered_count)

        if problem_type or keyword:
            filter_desc = []
            if problem_type:
                filter_desc.append(problem_type)
            if keyword:
                filter_desc.append(f'"{keyword}"')
            self.statsLabel.setText(f"筛选结果：{self.current_filtered_count} 条 / 共 {stats['total']} 条（{'、'.join(filter_desc)}）")
        else:
            self.statsLabel.setText(f"共 {stats['total']} 条知识")

        self.updateCategoryStats(stats)
        self.updateTopUsed(stats["most_used"])

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

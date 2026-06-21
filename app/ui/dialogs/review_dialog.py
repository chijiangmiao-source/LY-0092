from PySide6.QtCore import Qt, QDate, QRegularExpression
from PySide6.QtGui import QRegularExpressionValidator, QColor
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QDateEdit, QComboBox, QTextEdit, QCheckBox,
    QDialogButtonBox, QLabel, QScrollArea, QWidget, QMessageBox,
    QFrame, QSizePolicy
)
from qfluentwidgets import ComboBox, PushButton, LineEdit, TextEdit, CardWidget

from app.models.models import BadReview, RectificationKnowledge
from app.utils.constants import (
    PROBLEM_TYPES, RESPONSIBILITY_TYPES, REVIEW_SOURCES,
    RECTIFICATION_STATUSES, SUMMARY_MIN_LENGTH
)
from app.dao.knowledge_dao import KnowledgeDAO


class ReviewDialog(QDialog):
    def __init__(self, review: BadReview = None, parent=None):
        super().__init__(parent)
        self.review = review or BadReview()
        self.is_edit = review is not None
        self.knowledge_dao = KnowledgeDAO()
        self.used_knowledge_ids = []
        self.initUI()
        if self.is_edit:
            self.loadData()
        self.loadKnowledgeRecommendations()

    def initUI(self):
        self.setWindowTitle("编辑差评记录" if self.is_edit else "新增差评记录")
        self.resize(760, 820)
        self.setMinimumWidth(640)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)

        content = QWidget()
        contentLayout = QVBoxLayout(content)
        contentLayout.setContentsMargins(0, 0, 0, 0)
        contentLayout.setSpacing(15)

        formWidget = QWidget()
        formLayout = QFormLayout(formWidget)
        formLayout.setSpacing(15)
        formLayout.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self.recordNoEdit = LineEdit()
        self.recordNoEdit.setReadOnly(True)
        if not self.is_edit:
            from app.dao.review_dao import ReviewDAO
            dao = ReviewDAO()
            self.recordNoEdit.setText(dao.generate_record_no())
        formLayout.addRow("记录编号：", self.recordNoEdit)

        self.stayDateEdit = QDateEdit()
        self.stayDateEdit.setCalendarPopup(True)
        self.stayDateEdit.setDisplayFormat("yyyy-MM-dd")
        self.stayDateEdit.setDate(QDate.currentDate())
        formLayout.addRow("入住日期：", self.stayDateEdit)

        self.roomNoEdit = LineEdit()
        self.roomNoEdit.setPlaceholderText("请输入房间编号，如：101、203A、B102")
        room_regex = QRegularExpression(r'^[A-Za-z0-9\-]{1,10}$')
        self.roomNoEdit.setValidator(QRegularExpressionValidator(room_regex, self))
        formLayout.addRow("房间编号：", self.roomNoEdit)

        self.sourceCombo = ComboBox()
        self.sourceCombo.addItems(REVIEW_SOURCES)
        formLayout.addRow("差评来源：", self.sourceCombo)

        self.problemTypeCombo = ComboBox()
        self.problemTypeCombo.addItems(PROBLEM_TYPES)
        self.problemTypeCombo.currentTextChanged.connect(self.onProblemTypeChanged)
        formLayout.addRow("问题类型：", self.problemTypeCombo)

        self.summaryEdit = TextEdit()
        self.summaryEdit.setPlaceholderText(f"请输入差评摘要（不少于{SUMMARY_MIN_LENGTH}个字）")
        self.summaryEdit.setFixedHeight(100)
        formLayout.addRow("差评摘要：", self.summaryEdit)

        respLabel = QLabel("责任归因：")
        respWidget = QWidget()
        respLayout = QVBoxLayout(respWidget)
        respLayout.setContentsMargins(0, 0, 0, 0)
        respLayout.setSpacing(8)

        self.respCheckboxes = []
        for i in range(0, len(RESPONSIBILITY_TYPES), 3):
            rowLayout = QHBoxLayout()
            rowLayout.setSpacing(20)
            for j in range(3):
                if i + j < len(RESPONSIBILITY_TYPES):
                    cb = QCheckBox(RESPONSIBILITY_TYPES[i + j])
                    self.respCheckboxes.append(cb)
                    rowLayout.addWidget(cb)
            rowLayout.addStretch()
            respLayout.addLayout(rowLayout)

        formLayout.addRow(respLabel, respWidget)

        contentLayout.addWidget(formWidget)

        knowledgeSectionLabel = QLabel("📚 整改知识库推荐")
        knowledgeSectionLabel.setStyleSheet("font-size: 14px; font-weight: bold; color: #1a1a1a; margin-top: 5px;")
        contentLayout.addWidget(knowledgeSectionLabel)

        self.knowledgeTipLabel = QLabel("选择问题类型后，将自动推荐相关整改知识")
        self.knowledgeTipLabel.setStyleSheet("color: #999; font-size: 12px;")
        contentLayout.addWidget(self.knowledgeTipLabel)

        self.knowledgeContainer = QWidget()
        self.knowledgeLayout = QVBoxLayout(self.knowledgeContainer)
        self.knowledgeLayout.setContentsMargins(0, 0, 0, 0)
        self.knowledgeLayout.setSpacing(8)
        contentLayout.addWidget(self.knowledgeContainer)

        contentLayout.addSpacing(10)

        self.measureEdit = TextEdit()
        self.measureEdit.setPlaceholderText("请输入整改措施（可选），或点击上方知识库中的\"应用\"按钮自动填充")
        self.measureEdit.setFixedHeight(80)
        measureLabel = QLabel("整改措施：")
        formLayout2 = QFormLayout()
        formLayout2.setSpacing(15)
        formLayout2.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        formLayout2.addRow(measureLabel, self.measureEdit)
        contentLayout.addLayout(formLayout2)

        self.statusCombo = ComboBox()
        self.statusCombo.addItems(RECTIFICATION_STATUSES)
        self.statusCombo.currentTextChanged.connect(self.onStatusChanged)
        formLayout3 = QFormLayout()
        formLayout3.setSpacing(15)
        formLayout3.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        formLayout3.addRow("整改状态：", self.statusCombo)
        contentLayout.addLayout(formLayout3)

        self.reviewResultEdit = TextEdit()
        self.reviewResultEdit.setPlaceholderText("整改状态为已完成时必须填写")
        self.reviewResultEdit.setFixedHeight(80)
        self.reviewResultEdit.setEnabled(False)
        formLayout4 = QFormLayout()
        formLayout4.setSpacing(15)
        formLayout4.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        formLayout4.addRow("复查结果：", self.reviewResultEdit)
        contentLayout.addLayout(formLayout4)

        contentLayout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll, 1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            self
        )
        buttons.button(QDialogButtonBox.Ok).setText("保存")
        buttons.button(QDialogButtonBox.Cancel).setText("取消")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def onStatusChanged(self, status):
        self.reviewResultEdit.setEnabled(status == "已完成")
        if status != "已完成":
            self.reviewResultEdit.setPlainText("")

    def onProblemTypeChanged(self, _):
        self.loadKnowledgeRecommendations()

    def loadKnowledgeRecommendations(self):
        problem_type = self.problemTypeCombo.currentText()

        while self.knowledgeLayout.count():
            item = self.knowledgeLayout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not problem_type:
            self.knowledgeTipLabel.setText("选择问题类型后，将自动推荐相关整改知识")
            return

        knowledge_list = self.knowledge_dao.get_by_problem_type(problem_type)

        if not knowledge_list:
            self.knowledgeTipLabel.setText(f"暂无\"{problem_type}\"相关的整改知识，可在整改知识库中添加")
            return

        self.knowledgeTipLabel.setText(f"找到 {len(knowledge_list)} 条相关整改知识，点击\"应用\"可自动填充整改措施")

        for knowledge in knowledge_list:
            card = self.createKnowledgeCard(knowledge)
            self.knowledgeLayout.addWidget(card)

    def createKnowledgeCard(self, knowledge: RectificationKnowledge):
        card = CardWidget()
        cardLayout = QVBoxLayout(card)
        cardLayout.setContentsMargins(12, 10, 12, 10)
        cardLayout.setSpacing(6)

        headerLayout = QHBoxLayout()
        headerLayout.setSpacing(10)

        scenarioLabel = QLabel(knowledge.typical_scenario)
        scenarioLabel.setStyleSheet("font-weight: bold; color: #1a1a1a; font-size: 13px;")
        scenarioLabel.setWordWrap(True)
        headerLayout.addWidget(scenarioLabel, 1)

        useCountLabel = QLabel(f"使用 {knowledge.use_count} 次")
        useCountLabel.setStyleSheet("color: #0078d4; font-size: 11px; padding: 2px 8px; "
                                     "background: #e8f0fe; border-radius: 10px;")
        headerLayout.addWidget(useCountLabel)

        applyBtn = PushButton("应用")
        applyBtn.setFixedSize(60, 26)
        applyBtn.clicked.connect(lambda _=False, k=knowledge: self.applyKnowledge(k))
        headerLayout.addWidget(applyBtn)

        cardLayout.addLayout(headerLayout)

        detailsLayout = QVBoxLayout()
        detailsLayout.setSpacing(4)

        causeLabel = QLabel(f"<span style='color:#666;'>原因分析：</span>{knowledge.cause_analysis}")
        causeLabel.setTextFormat(Qt.RichText)
        causeLabel.setStyleSheet("color: #333; font-size: 12px;")
        causeLabel.setWordWrap(True)
        detailsLayout.addWidget(causeLabel)

        measuresLabel = QLabel(f"<span style='color:#666;'>整改措施：</span>{knowledge.recommended_measures}")
        measuresLabel.setTextFormat(Qt.RichText)
        measuresLabel.setStyleSheet("color: #333; font-size: 12px;")
        measuresLabel.setWordWrap(True)
        detailsLayout.addWidget(measuresLabel)

        if knowledge.review_points:
            reviewLabel = QLabel(f"<span style='color:#666;'>复查要点：</span>{knowledge.review_points}")
            reviewLabel.setTextFormat(Qt.RichText)
            reviewLabel.setStyleSheet("color: #333; font-size: 12px;")
            reviewLabel.setWordWrap(True)
            detailsLayout.addWidget(reviewLabel)

        if knowledge.applicable_rooms:
            roomsLabel = QLabel(f"<span style='color:#666;'>适用房型：</span>{knowledge.applicable_rooms}")
            roomsLabel.setTextFormat(Qt.RichText)
            roomsLabel.setStyleSheet("color: #333; font-size: 12px;")
            roomsLabel.setWordWrap(True)
            detailsLayout.addWidget(roomsLabel)

        cardLayout.addLayout(detailsLayout)

        return card

    def applyKnowledge(self, knowledge: RectificationKnowledge):
        current_text = self.measureEdit.toPlainText().strip()
        if current_text:
            new_text = current_text + "\n\n" + knowledge.recommended_measures
        else:
            new_text = knowledge.recommended_measures
        self.measureEdit.setPlainText(new_text)

        if knowledge.id not in self.used_knowledge_ids:
            self.knowledge_dao.increment_use_count(knowledge.id)
            self.used_knowledge_ids.append(knowledge.id)
            self.loadKnowledgeRecommendations()

        if knowledge.review_points and not self.reviewResultEdit.toPlainText().strip():
            self.reviewResultEdit.setPlaceholderText("参考知识库复查要点：" + knowledge.review_points[:50] + "...")

    def loadData(self):
        self.recordNoEdit.setText(self.review.record_no)
        self.stayDateEdit.setDate(QDate.fromString(self.review.stay_date, "yyyy-MM-dd"))
        self.roomNoEdit.setText(self.review.room_no)
        self.sourceCombo.setCurrentText(self.review.source)
        self.problemTypeCombo.setCurrentText(self.review.problem_type)
        self.summaryEdit.setPlainText(self.review.summary)
        self.measureEdit.setPlainText(self.review.rectification_measure)
        self.statusCombo.setCurrentText(self.review.rectification_status)
        self.reviewResultEdit.setPlainText(self.review.review_result)

        resp_list = [r.strip() for r in self.review.responsibility.split(",") if r.strip()]
        for cb in self.respCheckboxes:
            cb.setChecked(cb.text() in resp_list)

        self.reviewResultEdit.setEnabled(self.review.rectification_status == "已完成")

    def getSelectedResponsibilities(self):
        selected = [cb.text() for cb in self.respCheckboxes if cb.isChecked()]
        return ",".join(selected)

    def validate(self) -> bool:
        errors = []

        if not self.roomNoEdit.text().strip():
            errors.append("房间编号不能为空")

        summary = self.summaryEdit.toPlainText().strip()
        if not summary:
            errors.append("差评摘要不能为空")
        elif len(summary) < SUMMARY_MIN_LENGTH:
            errors.append(f"差评摘要不少于{SUMMARY_MIN_LENGTH}个字")

        if not self.getSelectedResponsibilities():
            errors.append("责任归因至少选择一项")
        else:
            resp_list = [r.strip() for r in self.getSelectedResponsibilities().split(",") if r.strip()]
            prob_type = self.problemTypeCombo.currentText()
            if len(resp_list) == 1 and resp_list[0] == prob_type:
                errors.append("责任归因不能与问题类型完全一致")

        if self.statusCombo.currentText() == "已完成" and not self.reviewResultEdit.toPlainText().strip():
            errors.append("整改状态为已完成时，复查结果必须填写")

        if errors:
            QMessageBox.warning(self, "数据校验失败", "\n".join(errors))
            return False

        return True

    def accept(self):
        if not self.validate():
            return

        self.review.record_no = self.recordNoEdit.text()
        self.review.stay_date = self.stayDateEdit.date().toString("yyyy-MM-dd")
        self.review.room_no = self.roomNoEdit.text().strip()
        self.review.source = self.sourceCombo.currentText()
        self.review.problem_type = self.problemTypeCombo.currentText()
        self.review.summary = self.summaryEdit.toPlainText().strip()
        self.review.responsibility = self.getSelectedResponsibilities()
        self.review.rectification_measure = self.measureEdit.toPlainText().strip()
        self.review.rectification_status = self.statusCombo.currentText()
        self.review.review_result = self.reviewResultEdit.toPlainText().strip()

        super().accept()

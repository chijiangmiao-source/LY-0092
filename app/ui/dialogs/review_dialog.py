from PySide6.QtCore import Qt, QDate, QRegularExpression
from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QDateEdit, QComboBox, QTextEdit, QCheckBox,
    QDialogButtonBox, QLabel, QScrollArea, QWidget, QMessageBox
)
from qfluentwidgets import ComboBox, PushButton, LineEdit, TextEdit

from app.models.models import BadReview
from app.utils.constants import (
    PROBLEM_TYPES, RESPONSIBILITY_TYPES, REVIEW_SOURCES,
    RECTIFICATION_STATUSES, SUMMARY_MIN_LENGTH
)


class ReviewDialog(QDialog):
    def __init__(self, review: BadReview = None, parent=None):
        super().__init__(parent)
        self.review = review or BadReview()
        self.is_edit = review is not None
        self.initUI()
        if self.is_edit:
            self.loadData()

    def initUI(self):
        self.setWindowTitle("编辑差评记录" if self.is_edit else "新增差评记录")
        self.resize(680, 720)
        self.setMinimumWidth(600)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)

        content = QWidget()
        formLayout = QFormLayout(content)
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

        self.measureEdit = TextEdit()
        self.measureEdit.setPlaceholderText("请输入整改措施（可选）")
        self.measureEdit.setFixedHeight(80)
        formLayout.addRow("整改措施：", self.measureEdit)

        self.statusCombo = ComboBox()
        self.statusCombo.addItems(RECTIFICATION_STATUSES)
        self.statusCombo.currentTextChanged.connect(self.onStatusChanged)
        formLayout.addRow("整改状态：", self.statusCombo)

        self.reviewResultEdit = TextEdit()
        self.reviewResultEdit.setPlaceholderText("整改状态为已完成时必须填写")
        self.reviewResultEdit.setFixedHeight(80)
        self.reviewResultEdit.setEnabled(False)
        formLayout.addRow("复查结果：", self.reviewResultEdit)

        scroll.setWidget(content)
        layout.addWidget(scroll)

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

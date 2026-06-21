from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel,
    QTextEdit, QMessageBox, QLineEdit
)
from qfluentwidgets import (
    ComboBox, PrimaryPushButton, PushButton,
    StrongBodyLabel, BodyLabel, CardWidget
)

from app.models.models import RectificationReview, BadReview
from app.utils.constants import REVIEW_CONCLUSIONS


class ReviewAnalysisDialog(QDialog):
    def __init__(self, review: BadReview, analysis: RectificationReview = None, parent=None):
        super().__init__(parent)
        self.review = review
        self.analysis = analysis
        self.setWindowTitle("整改复盘")
        self.resize(650, 600)
        self.initUI()
        self.loadData()

    def initUI(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        title = StrongBodyLabel("整改效果复盘")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)

        infoCard = CardWidget()
        infoLayout = QFormLayout(infoCard)
        infoLayout.setContentsMargins(16, 16, 16, 16)
        infoLayout.setSpacing(10)

        infoLayout.addRow(BodyLabel("记录编号："), BodyLabel(self.review.record_no))
        infoLayout.addRow(BodyLabel("入住日期："), BodyLabel(self.review.stay_date))
        infoLayout.addRow(BodyLabel("房间号："), BodyLabel(self.review.room_no))
        infoLayout.addRow(BodyLabel("问题类型："), BodyLabel(self.review.problem_type))
        infoLayout.addRow(BodyLabel("差评来源："), BodyLabel(self.review.source))
        infoLayout.addRow(BodyLabel("责任归因："), BodyLabel(self.review.responsibility))

        summaryLabel = BodyLabel("差评摘要：")
        summaryValue = BodyLabel(self.review.summary)
        summaryValue.setWordWrap(True)
        summaryValue.setStyleSheet("color: #333;")
        infoLayout.addRow(summaryLabel, summaryValue)

        measureLabel = BodyLabel("整改措施：")
        measureValue = BodyLabel(self.review.rectification_measure or "无")
        measureValue.setWordWrap(True)
        measureValue.setStyleSheet("color: #333;")
        infoLayout.addRow(measureLabel, measureValue)

        infoLayout.addRow(BodyLabel("复查结果："), BodyLabel(self.review.review_result or "无"))

        layout.addWidget(infoCard)

        formLayout = QFormLayout()
        formLayout.setSpacing(12)

        conclusionLabel = BodyLabel("复盘结论 <span style='color: #e74c3c;'>*</span>")
        conclusionLabel.setTextFormat(Qt.RichText)
        self.conclusionCombo = ComboBox()
        self.conclusionCombo.addItems(REVIEW_CONCLUSIONS)
        self.conclusionCombo.setFixedHeight(36)
        formLayout.addRow(conclusionLabel, self.conclusionCombo)

        riskLabel = BodyLabel("回潮风险 <span style='color: #e74c3c;'>*</span>")
        riskLabel.setTextFormat(Qt.RichText)
        self.riskCombo = ComboBox()
        self.riskCombo.addItems(["高", "中", "低", "无"])
        self.riskCombo.setCurrentText("低")
        self.riskCombo.setFixedHeight(36)
        formLayout.addRow(riskLabel, self.riskCombo)

        experienceLabel = BodyLabel("经验沉淀")
        self.experienceEdit = QTextEdit()
        self.experienceEdit.setPlaceholderText("请输入本次整改的经验总结，哪些做法值得推广...")
        self.experienceEdit.setFixedHeight(100)
        formLayout.addRow(experienceLabel, self.experienceEdit)

        preventionLabel = BodyLabel("预防建议")
        self.preventionEdit = QTextEdit()
        self.preventionEdit.setPlaceholderText("请输入后续预防措施，如何避免类似问题再次发生...")
        self.preventionEdit.setFixedHeight(100)
        formLayout.addRow(preventionLabel, self.preventionEdit)

        reviewerLabel = BodyLabel("复盘人")
        self.reviewerEdit = QLineEdit()
        self.reviewerEdit.setPlaceholderText("请输入复盘人姓名")
        self.reviewerEdit.setFixedHeight(36)
        formLayout.addRow(reviewerLabel, self.reviewerEdit)

        layout.addLayout(formLayout)

        btnLayout = QHBoxLayout()
        btnLayout.addStretch()

        cancelBtn = PushButton("取消")
        cancelBtn.clicked.connect(self.reject)
        btnLayout.addWidget(cancelBtn)

        saveBtn = PrimaryPushButton("保存复盘")
        saveBtn.clicked.connect(self.accept)
        btnLayout.addWidget(saveBtn)

        layout.addLayout(btnLayout)

    def loadData(self):
        if self.analysis:
            if self.analysis.review_conclusion:
                idx = self.conclusionCombo.findText(self.analysis.review_conclusion)
                if idx >= 0:
                    self.conclusionCombo.setCurrentIndex(idx)
            if self.analysis.recurrence_risk:
                idx = self.riskCombo.findText(self.analysis.recurrence_risk)
                if idx >= 0:
                    self.riskCombo.setCurrentIndex(idx)
            self.experienceEdit.setPlainText(self.analysis.experience_summary or "")
            self.preventionEdit.setPlainText(self.analysis.prevention_measures or "")
            self.reviewerEdit.setText(self.analysis.reviewer or "")

    def accept(self):
        conclusion = self.conclusionCombo.currentText()
        if not conclusion:
            QMessageBox.warning(self, "提示", "请选择复盘结论")
            return

        if self.analysis:
            self.analysis.review_conclusion = conclusion
            self.analysis.recurrence_risk = self.riskCombo.currentText()
            self.analysis.experience_summary = self.experienceEdit.toPlainText().strip()
            self.analysis.prevention_measures = self.preventionEdit.toPlainText().strip()
            self.analysis.reviewer = self.reviewerEdit.text().strip()
        else:
            self.analysis = RectificationReview(
                review_id=self.review.id,
                record_no=self.review.record_no,
                review_conclusion=conclusion,
                recurrence_risk=self.riskCombo.currentText(),
                experience_summary=self.experienceEdit.toPlainText().strip(),
                prevention_measures=self.preventionEdit.toPlainText().strip(),
                reviewer=self.reviewerEdit.text().strip()
            )

        super().accept()

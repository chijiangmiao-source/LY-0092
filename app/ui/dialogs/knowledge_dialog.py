from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QDialogButtonBox, QMessageBox,
    QScrollArea, QWidget, QLabel
)
from qfluentwidgets import ComboBox, TextEdit, LineEdit

from app.models.models import RectificationKnowledge
from app.utils.constants import PROBLEM_TYPES


class KnowledgeDialog(QDialog):
    def __init__(self, knowledge: RectificationKnowledge = None, parent=None):
        super().__init__(parent)
        self.knowledge = knowledge or RectificationKnowledge()
        self.is_edit = knowledge is not None
        self.initUI()
        if self.is_edit:
            self.loadData()

    def initUI(self):
        self.setWindowTitle("编辑整改知识" if self.is_edit else "新增整改知识")
        self.resize(720, 760)
        self.setMinimumWidth(640)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)

        content = QWidget()
        formLayout = QFormLayout(content)
        formLayout.setSpacing(15)
        formLayout.setLabelAlignment(Qt.AlignRight | Qt.AlignTop)

        self.problemTypeCombo = ComboBox()
        self.problemTypeCombo.addItems(PROBLEM_TYPES)
        formLayout.addRow("问题类型：", self.problemTypeCombo)

        self.scenarioEdit = TextEdit()
        self.scenarioEdit.setPlaceholderText("请输入典型场景描述")
        self.scenarioEdit.setFixedHeight(80)
        formLayout.addRow("典型场景：", self.scenarioEdit)

        self.causeEdit = TextEdit()
        self.causeEdit.setPlaceholderText("请输入原因分析")
        self.causeEdit.setFixedHeight(100)
        formLayout.addRow("原因分析：", self.causeEdit)

        self.measuresEdit = TextEdit()
        self.measuresEdit.setPlaceholderText("请输入推荐整改措施")
        self.measuresEdit.setFixedHeight(120)
        formLayout.addRow("推荐整改措施：", self.measuresEdit)

        self.reviewPointsEdit = TextEdit()
        self.reviewPointsEdit.setPlaceholderText("请输入复查要点")
        self.reviewPointsEdit.setFixedHeight(100)
        formLayout.addRow("复查要点：", self.reviewPointsEdit)

        self.applicableRoomsEdit = LineEdit()
        self.applicableRoomsEdit.setPlaceholderText("请输入适用房型，如：大床房、双床房、套房等")
        formLayout.addRow("适用房型：", self.applicableRoomsEdit)

        if self.is_edit:
            useCountLabel = QLabel(str(self.knowledge.use_count))
            useCountLabel.setStyleSheet("color: #0078d4; font-weight: bold; font-size: 14px;")
            formLayout.addRow("使用次数：", useCountLabel)

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

    def loadData(self):
        self.problemTypeCombo.setCurrentText(self.knowledge.problem_type)
        self.scenarioEdit.setPlainText(self.knowledge.typical_scenario)
        self.causeEdit.setPlainText(self.knowledge.cause_analysis)
        self.measuresEdit.setPlainText(self.knowledge.recommended_measures)
        self.reviewPointsEdit.setPlainText(self.knowledge.review_points)
        self.applicableRoomsEdit.setText(self.knowledge.applicable_rooms)

    def validate(self) -> bool:
        errors = []

        if not self.scenarioEdit.toPlainText().strip():
            errors.append("典型场景不能为空")

        if not self.causeEdit.toPlainText().strip():
            errors.append("原因分析不能为空")

        if not self.measuresEdit.toPlainText().strip():
            errors.append("推荐整改措施不能为空")

        if not self.reviewPointsEdit.toPlainText().strip():
            errors.append("复查要点不能为空")

        if errors:
            QMessageBox.warning(self, "数据校验失败", "\n".join(errors))
            return False

        return True

    def accept(self):
        if not self.validate():
            return

        self.knowledge.problem_type = self.problemTypeCombo.currentText()
        self.knowledge.typical_scenario = self.scenarioEdit.toPlainText().strip()
        self.knowledge.cause_analysis = self.causeEdit.toPlainText().strip()
        self.knowledge.recommended_measures = self.measuresEdit.toPlainText().strip()
        self.knowledge.review_points = self.reviewPointsEdit.toPlainText().strip()
        self.knowledge.applicable_rooms = self.applicableRoomsEdit.text().strip()

        super().accept()

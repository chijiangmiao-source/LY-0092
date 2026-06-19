from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGridLayout
)
from PySide6.QtGui import QFont
from qfluentwidgets import (
    PushButton, FluentIcon as FIF,
    CardWidget, SubtitleLabel, StrongBodyLabel, BodyLabel
)

import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from app.dao.review_dao import ReviewDAO
from app.utils.signal_bus import SignalBus

plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False


class StatisticsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("statisticsPage")
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
        title = QLabel("统计分析")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #1a1a1a;")
        headerLayout.addWidget(title)
        headerLayout.addStretch()

        self.refreshBtn = PushButton("刷新")
        self.refreshBtn.setIcon(FIF.SYNC)
        self.refreshBtn.clicked.connect(self.refresh)
        headerLayout.addWidget(self.refreshBtn)

        layout.addLayout(headerLayout)

        statsGrid = QGridLayout()
        statsGrid.setSpacing(15)

        self.totalCard = self.createStatCard("总差评数", "0", "#3498db", 0)
        self.pendingCard = self.createStatCard("待整改", "0", "#e74c3c", 1)
        self.inProgressCard = self.createStatCard("整改中", "0", "#f39c12", 2)
        self.completedCard = self.createStatCard("已完成", "0", "#27ae60", 3)
        self.rateCard = self.createStatCard("整改完成率", "0%", "#9b59b6", 4, span=2)

        statsGrid.addWidget(self.totalCard, 0, 0)
        statsGrid.addWidget(self.pendingCard, 0, 1)
        statsGrid.addWidget(self.inProgressCard, 0, 2)
        statsGrid.addWidget(self.completedCard, 0, 3)
        statsGrid.addWidget(self.rateCard, 0, 4, 1, 2)

        layout.addLayout(statsGrid)

        chartLayout = QGridLayout()
        chartLayout.setSpacing(15)

        self.problemTypeChart = self.createChartCard("问题类型分布")
        self.sourceChart = self.createChartCard("差评来源分布")
        self.statusChart = self.createChartCard("整改状态分布")
        self.trendChart = self.createChartCard("近12个月差评趋势")

        chartLayout.addWidget(self.problemTypeChart['card'], 0, 0)
        chartLayout.addWidget(self.sourceChart['card'], 0, 1)
        chartLayout.addWidget(self.statusChart['card'], 1, 0)
        chartLayout.addWidget(self.trendChart['card'], 1, 1)

        layout.addLayout(chartLayout, 1)

    def createStatCard(self, title, value, color, index=0, span=1):
        card = CardWidget()
        cardLayout = QVBoxLayout(card)
        cardLayout.setContentsMargins(20, 20, 20, 20)
        cardLayout.setSpacing(5)

        titleLabel = BodyLabel(title)
        titleLabel.setStyleSheet(f"color: {color}; font-size: 14px;")

        valueLabel = SubtitleLabel(value)
        valueLabel.setStyleSheet(f"color: {color}; font-size: 32px; font-weight: bold;")

        cardLayout.addWidget(titleLabel)
        cardLayout.addWidget(valueLabel)

        return card

    def createChartCard(self, title):
        card = CardWidget()
        cardLayout = QVBoxLayout(card)
        cardLayout.setContentsMargins(15, 15, 15, 15)
        cardLayout.setSpacing(10)

        titleLabel = StrongBodyLabel(title)
        titleLabel.setStyleSheet("font-size: 16px; font-weight: bold;")
        cardLayout.addWidget(titleLabel)

        figure = Figure(figsize=(5, 4), dpi=100)
        canvas = FigureCanvas(figure)
        cardLayout.addWidget(canvas, 1)

        return {
            'card': card,
            'figure': figure,
            'canvas': canvas,
            'title': title
        }

    def refresh(self):
        stats = self.dao.get_statistics()
        self.updateStatCards(stats)
        self.updateCharts(stats)

    def updateStatCards(self, stats):
        total = stats["total"]
        pending = stats["pending"]
        in_progress = stats["in_progress"]
        completed = stats["completed"]
        rate = (completed / total * 100) if total > 0 else 0

        self.totalCard.findChild(SubtitleLabel).setText(str(total))
        self.pendingCard.findChild(SubtitleLabel).setText(str(pending))
        self.inProgressCard.findChild(SubtitleLabel).setText(str(in_progress))
        self.completedCard.findChild(SubtitleLabel).setText(str(completed))
        self.rateCard.findChild(SubtitleLabel).setText(f"{rate:.1f}%")

    def updateCharts(self, stats):
        self.plotProblemTypeChart(stats["by_problem_type"])
        self.plotSourceChart(stats["by_source"])
        self.plotStatusChart(stats)
        self.plotTrendChart(stats["by_month"])

    def plotProblemTypeChart(self, data):
        figure = self.problemTypeChart['figure']
        canvas = self.problemTypeChart['canvas']
        figure.clear()

        if not data:
            ax = figure.add_subplot(111)
            ax.text(0.5, 0.5, "暂无数据", ha='center', va='center', fontsize=14, color='gray')
            ax.axis('off')
            canvas.draw()
            return

        df = pd.DataFrame(data, columns=['问题类型', '数量'])
        df = df.sort_values('数量', ascending=True)

        ax = figure.add_subplot(111)
        colors = plt.cm.Set3(range(len(df)))
        bars = ax.barh(df['问题类型'], df['数量'], color=colors)

        for i, bar in enumerate(bars):
            width = bar.get_width()
            ax.text(width + 0.1, bar.get_y() + bar.get_height()/2,
                    f"{int(width)}", va='center', fontsize=9)

        ax.set_xlabel('差评数量')
        ax.set_title('问题类型分布')
        figure.tight_layout()
        canvas.draw()

    def plotSourceChart(self, data):
        figure = self.sourceChart['figure']
        canvas = self.sourceChart['canvas']
        figure.clear()

        if not data:
            ax = figure.add_subplot(111)
            ax.text(0.5, 0.5, "暂无数据", ha='center', va='center', fontsize=14, color='gray')
            ax.axis('off')
            canvas.draw()
            return

        df = pd.DataFrame(data, columns=['来源', '数量'])

        ax = figure.add_subplot(111)
        colors = plt.cm.Paired(range(len(df)))

        def autopct(pct, allvals):
            absolute = int(pct/100.*sum(allvals))
            return f"{pct:.1f}%\n({absolute}条)"

        wedges, texts, autotexts = ax.pie(
            df['数量'],
            labels=df['来源'],
            autopct=lambda pct: autopct(pct, df['数量']),
            colors=colors,
            startangle=90
        )

        for text in texts:
            text.set_fontsize(9)
        for autotext in autotexts:
            autotext.set_fontsize(8)

        ax.set_title('差评来源分布')
        figure.tight_layout()
        canvas.draw()

    def plotStatusChart(self, stats):
        figure = self.statusChart['figure']
        canvas = self.statusChart['canvas']
        figure.clear()

        data = [
            ('待整改', stats["pending"], '#e74c3c'),
            ('整改中', stats["in_progress"], '#f39c12'),
            ('已完成', stats["completed"], '#27ae60')
        ]

        labels = [d[0] for d in data]
        values = [d[1] for d in data]
        colors = [d[2] for d in data]

        ax = figure.add_subplot(111)
        bars = ax.bar(labels, values, color=colors, width=0.6)

        for bar, value in zip(bars, values):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                    str(value), ha='center', va='bottom', fontsize=11, fontweight='bold')

        ax.set_ylabel('数量')
        ax.set_title('整改状态分布')
        max_val = max(values) if values and max(values) > 0 else 10
        ax.set_ylim(0, max_val * 1.2)

        total = sum(values) if values else 0
        for i, bar in enumerate(bars):
            height = bar.get_height()
            if values and values[i] > 0 and total > 0:
                pct = values[i] / total * 100
                ax.text(bar.get_x() + bar.get_width()/2., height/2,
                        f"{pct:.1f}%", ha='center', va='center',
                        fontsize=10, color='white', fontweight='bold')

        figure.tight_layout()
        canvas.draw()

    def plotTrendChart(self, data):
        figure = self.trendChart['figure']
        canvas = self.trendChart['canvas']
        figure.clear()

        if not data:
            ax = figure.add_subplot(111)
            ax.text(0.5, 0.5, "暂无数据", ha='center', va='center', fontsize=14, color='gray')
            ax.axis('off')
            canvas.draw()
            return

        df = pd.DataFrame(data, columns=['月份', '数量'])
        df = df.sort_values('月份')

        ax = figure.add_subplot(111)
        ax.plot(df['月份'], df['数量'], marker='o', linewidth=2,
                markersize=6, color='#3498db', markerfacecolor='white',
                markeredgewidth=2, markeredgecolor='#3498db')

        for i, (month, count) in enumerate(zip(df['月份'], df['数量'])):
            ax.text(i, count + 0.3, str(count), ha='center', va='bottom',
                    fontsize=9, fontweight='bold')

        ax.set_xlabel('月份')
        ax.set_ylabel('差评数量')
        ax.set_title('近12个月差评趋势')
        ax.grid(True, alpha=0.3, linestyle='--')
        max_val = max(df['数量']) if not df['数量'].empty and max(df['数量']) > 0 else 10
        ax.set_ylim(0, max_val * 1.3)

        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right', fontsize=8)

        figure.tight_layout()
        canvas.draw()

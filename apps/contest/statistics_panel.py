"""
apps/contest/statistics_panel.py
ON3RT Radio Suite - Contest Logbook
"""

from PyQt6.QtWidgets import QWidget, QGridLayout, QLabel


class StatisticsPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QGridLayout(self)

        self.lbl_qsos = QLabel("0")
        self.lbl_points = QLabel("0")
        self.lbl_mult = QLabel("0")
        self.lbl_score = QLabel("0")

        layout.addWidget(QLabel("QSOs"), 0, 0)
        layout.addWidget(self.lbl_qsos, 0, 1)

        layout.addWidget(QLabel("Points"), 0, 2)
        layout.addWidget(self.lbl_points, 0, 3)

        layout.addWidget(QLabel("Multiplicateurs"), 0, 4)
        layout.addWidget(self.lbl_mult, 0, 5)

        layout.addWidget(QLabel("Score"), 0, 6)
        layout.addWidget(self.lbl_score, 0, 7)

    def update_statistics(self, stats: dict):
        self.lbl_qsos.setText(str(stats.get("qsos", 0)))
        self.lbl_points.setText(str(stats.get("points", 0)))
        self.lbl_mult.setText(str(stats.get("multipliers", 0)))
        self.lbl_score.setText(str(stats.get("score", 0)))

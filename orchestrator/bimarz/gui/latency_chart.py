"""Simple latency history chart with PySide6 fallback.

Latency history chart widget with PySide6 fallback.
"""

from __future__ import annotations

import math

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

try:
    from PySide6.QtCharts import QChart, QChartView, QLineSeries, QValueAxis

    _HAS_CHARTS = True
except ImportError:
    _HAS_CHARTS = False


class LatencyChart(QWidget):
    """Widget that displays latency history for the active profile."""

    _MAX_POINTS = 20

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self._data_points: list[float] = []

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)

        if _HAS_CHARTS:
            self._series = QLineSeries()
            self._series.setName("Latency (ms)")

            self._chart = QChart()
            self._chart.addSeries(self._series)
            self._chart.setTitle("Latency History")
            self._chart.legend().setVisible(False)

            self._axis_x = QValueAxis()
            self._axis_x.setLabelFormat("%i")
            self._axis_x.setTitleText("Sample")

            self._axis_y = QValueAxis()
            self._axis_y.setTitleText("ms")

            self._chart.addAxis(
                self._axis_x,
                Qt.AlignBottom,
            )

            self._chart.addAxis(
                self._axis_y,
                Qt.AlignLeft,
            )

            self._series.attachAxis(self._axis_x)
            self._series.attachAxis(self._axis_y)

            self._chart_view = QChartView(self._chart)
            self._layout.addWidget(self._chart_view)

        else:
            self._fallback_label = QLabel(
                "Latency chart unavailable"
            )
            self._fallback_label.setAlignment(
                Qt.AlignCenter
            )
            self._layout.addWidget(
                self._fallback_label
            )

    @Slot(float)
    def add_point(self, latency_ms: float) -> None:
        """Append latency sample."""

        if (
            math.isnan(latency_ms)
            or latency_ms < 0
            or math.isinf(latency_ms)
        ):
            return

        self._data_points.append(
            float(latency_ms)
        )

        if len(self._data_points) > self._MAX_POINTS:
            self._data_points.pop(0)

        if _HAS_CHARTS:
            self._refresh_chart()

        else:
            self._fallback_label.setText(
                f"Latest latency: {latency_ms:.0f} ms"
            )

    def _refresh_chart(self) -> None:
        self._series.clear()

        for index, value in enumerate(self._data_points):
            self._series.append(
                index,
                value,
            )

        max_value = max(
            self._data_points,
            default=10,
        )

        self._axis_x.setRange(
            0,
            max(
                len(self._data_points) - 1,
                1,
            ),
        )

        self._axis_y.setRange(
            0,
            max(
                max_value * 1.2,
                10,
            ),
        )

    def clear(self) -> None:
        """Reset chart data."""

        self._data_points.clear()

        if _HAS_CHARTS:
            self._series.clear()
            self._axis_x.setRange(0, 1)
            self._axis_y.setRange(0, 10)

        else:
            self._fallback_label.setText(
                "Latency chart unavailable"
            )

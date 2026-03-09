from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import QWidget


class TimelineWidget(QWidget):
    """Timeline with named steps and status-based colors."""

    dot_selected = pyqtSignal(int)

    COLOR_PENDING = QColor(150, 150, 150)
    COLOR_DONE = QColor(46, 169, 79)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(220)
        self.dot_radius = 10
        self.selected_index = -1
        self.step_names = [
            "ctrl_settings",
            "ctrl.config",
            "xplt.interface",
            "xplt.peripheral.c",
            "xplt.peripheral.h",
            "ctrl.c",
            "ctrl.h",
            "user.c",
            "user.h",
            "simulink_buffer",
        ]
        self.step_status = ["pending" for _ in self.step_names]
        if self.step_status:
            # Initial state: no generated files yet.
            self.selected_index = 0
        self.set_theme("light")

    def set_theme(self, theme_name: str):
        if theme_name == "dark":
            self.line_color = QColor(120, 130, 145)
            self.label_color = QColor(215, 220, 226)
            self.selected_outer_color = QColor(255, 180, 90)
            self.node_border_color = QColor(140, 180, 240)
        else:
            self.line_color = QColor(90, 90, 90)
            self.label_color = QColor(31, 35, 40)
            self.selected_outer_color = QColor(255, 166, 0)
            self.node_border_color = QColor(20, 70, 130)
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        # 水平居中：将时间线放在窗口宽度的中心
        x = self.width() // 2
        
        # 保持原始的垂直设置
        top_margin = 40
        bottom_margin = 40
        dot_count = len(self.step_names)
        usable_height = max(0, self.height() - top_margin - bottom_margin)
        spacing = usable_height // (dot_count - 1) if dot_count > 1 else 0

        painter.setPen(QPen(self.line_color, 2))
        for i in range(dot_count - 1):
            y1 = top_margin + i * spacing
            y2 = top_margin + (i + 1) * spacing
            painter.drawLine(x, y1, x, y2)

        for i in range(dot_count):
            y = top_margin + i * spacing
            painter.setBrush(self._status_color(self.step_status[i]))

            if i == self.selected_index:
                # Draw a stronger ring on the selected dot for clear visual feedback.
                painter.setPen(QPen(self.selected_outer_color, 4))
                painter.drawEllipse(
                    x - self.dot_radius - 4,
                    y - self.dot_radius - 4,
                    (self.dot_radius + 4) * 2,
                    (self.dot_radius + 4) * 2,
                )
                painter.setPen(QPen(self.node_border_color, 3))
            else:
                painter.setPen(QPen(self.node_border_color, 2))

            painter.drawEllipse(
                x - self.dot_radius,
                y - self.dot_radius,
                self.dot_radius * 2,
                self.dot_radius * 2,
            )

            # Draw label below each node to keep step name bound to its dot.
            painter.setPen(QPen(self.label_color, 1))
            painter.drawText(
                x - 100,
                y + self.dot_radius + 16,
                200,
                20,
                Qt.AlignmentFlag.AlignHCenter,
                self.step_names[i],
            )

    def _dot_center(self, index):
        # 水平居中：将时间线放在窗口宽度的中心
        x = self.width() // 2
        
        # 保持原始的垂直设置
        top_margin = 40
        bottom_margin = 40
        dot_count = len(self.step_names)
        usable_height = max(0, self.height() - top_margin - bottom_margin)
        spacing = usable_height // (dot_count - 1) if dot_count > 1 else 0
        y = top_margin + index * spacing
        return x, y

    def _status_color(self, status):
        if status == "done":
            return self.COLOR_DONE
        return self.COLOR_PENDING

    def _is_clickable(self, index):
        return 0 <= index < len(self.step_names)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            clicked_index = -1
            for i in range(len(self.step_names)):
                cx, cy = self._dot_center(i)
                dx = event.position().x() - cx
                dy = event.position().y() - cy
                if dx * dx + dy * dy <= (self.dot_radius + 3) * (self.dot_radius + 3):
                    clicked_index = i
                    break

            if clicked_index != -1 and self._is_clickable(clicked_index):
                self.selected_index = clicked_index
                self.dot_selected.emit(clicked_index)
                self.update()

        super().mousePressEvent(event)

    def has_selected_dot(self):
        return 0 <= self.selected_index < len(self.step_names)

    def step_name(self, index):
        if 0 <= index < len(self.step_names):
            return self.step_names[index]
        return ""

    def reset_after_file_created(self):
        # New file created: all steps remain pending until output files exist.
        self.step_status = ["pending" for _ in self.step_names]
        if self.step_status:
            self.selected_index = 0
        else:
            self.selected_index = -1
        self.update()

    def mark_step_done(self, index):
        if not (0 <= index < len(self.step_names)):
            return

        self.step_status[index] = "done"

        self.selected_index = index
        self.update()

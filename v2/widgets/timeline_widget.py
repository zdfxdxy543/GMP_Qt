from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import QWidget


class TimelineWidget(QWidget):
    """Timeline with named steps and status-based colors."""

    dot_selected = pyqtSignal(int)

    COLOR_PENDING = QColor(150, 150, 150)
    COLOR_ACTIVE = QColor(46, 169, 79)
    COLOR_DONE = QColor(40, 120, 200)

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
            # Initial state: first step is currently in progress.
            self.step_status[0] = "active"
            self.selected_index = 0

    def paintEvent(self, event):
        super().paintEvent(event)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        x = 56
        top_margin = 40
        bottom_margin = 40
        dot_count = len(self.step_names)
        usable_height = max(0, self.height() - top_margin - bottom_margin)
        spacing = usable_height // (dot_count - 1) if dot_count > 1 else 0

        painter.setPen(QPen(QColor(90, 90, 90), 2))
        for i in range(dot_count - 1):
            y1 = top_margin + i * spacing
            y2 = top_margin + (i + 1) * spacing
            painter.drawLine(x, y1, x, y2)

        for i in range(dot_count):
            y = top_margin + i * spacing
            painter.setBrush(self._status_color(self.step_status[i]))

            if i == self.selected_index:
                # Draw a stronger ring on the selected dot for clear visual feedback.
                painter.setPen(QPen(QColor(255, 166, 0), 4))
                painter.drawEllipse(
                    x - self.dot_radius - 4,
                    y - self.dot_radius - 4,
                    (self.dot_radius + 4) * 2,
                    (self.dot_radius + 4) * 2,
                )
                painter.setPen(QPen(QColor(20, 70, 130), 3))
            else:
                painter.setPen(QPen(QColor(20, 70, 130), 2))

            painter.drawEllipse(
                x - self.dot_radius,
                y - self.dot_radius,
                self.dot_radius * 2,
                self.dot_radius * 2,
            )

            # Draw label below each node to keep step name bound to its dot.
            painter.setPen(QPen(QColor(35, 35, 35), 1))
            painter.drawText(
                x - 100,
                y + self.dot_radius + 16,
                200,
                20,
                Qt.AlignmentFlag.AlignHCenter,
                self.step_names[i],
            )

    def _dot_center(self, index):
        x = 56
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
        if status == "active":
            return self.COLOR_ACTIVE
        return self.COLOR_PENDING

    def _is_clickable(self, index):
        return self.step_status[index] in {"active", "done"}

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
        # New file created: first step starts as active, the rest are pending.
        self.step_status = ["pending" for _ in self.step_names]
        if self.step_status:
            self.step_status[0] = "active"
            self.selected_index = 0
        else:
            self.selected_index = -1
        self.update()

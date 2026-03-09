from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class NewFileDialog(QDialog):
    """Collects folder, controller type, and chip type for a new file flow."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("新建配置")
        self.resize(520, 220)

        root_layout = QVBoxLayout(self)
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        folder_row = QHBoxLayout()
        self.folder_edit = QLineEdit(self)
        self.folder_edit.setPlaceholderText("请选择新文件要保存的文件夹")
        browse_btn = QPushButton("浏览...", self)
        browse_btn.clicked.connect(self._choose_folder)
        folder_row.addWidget(self.folder_edit, 1)
        folder_row.addWidget(browse_btn)

        self.controller_combo = QComboBox(self)
        self.controller_combo.currentTextChanged.connect(self._reload_chip_types)

        self.chip_combo = QComboBox(self)

        self.file_name = QLineEdit(self)

        form.addRow("新文件名", self.file_name)
        form.addRow("目标文件夹", self._wrap_layout(folder_row))
        form.addRow("控制器类型", self.controller_combo)
        form.addRow("芯片类型", self.chip_combo)
        root_layout.addLayout(form)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            parent=self,
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        root_layout.addWidget(button_box)

        self._load_controller_types()

    def _wrap_layout(self, layout):
        wrapper = QWidget(self)
        wrapper.setLayout(layout)
        return wrapper

    def _src_dir(self):
        # The v2 folder sits beside project-level src directory.
        return Path(__file__).resolve().parents[2] / "src"

    def _load_controller_types(self):
        src_dir = self._src_dir()
        controller_types = []
        if src_dir.exists():
            controller_types = sorted([p.name for p in src_dir.iterdir() if p.is_dir()])

        if not controller_types:
            controller_types = ["pmsm"]

        self.controller_combo.clear()
        self.controller_combo.addItems(controller_types)
        self._reload_chip_types(self.controller_combo.currentText())

    def _reload_chip_types(self, controller_type):
        chip_types = []
        src_dir = self._src_dir()
        controller_dir = src_dir / controller_type
        if controller_dir.exists() and controller_dir.is_dir():
            chip_types = sorted([p.name for p in controller_dir.iterdir() if p.is_dir()])

        if not chip_types:
            chip_types = ["f280049c"]

        self.chip_combo.clear()
        self.chip_combo.addItems(chip_types)

    def _choose_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "选择新文件对应的文件夹", "")
        if folder:
            self.folder_edit.setText(folder)

    def selected_config(self):
        return {
            "file_name": self.file_name.text().strip(),
            "folder": self.folder_edit.text().strip(),
            "controller": self.controller_combo.currentText().strip(),
            "chip": self.chip_combo.currentText().strip(),
        }

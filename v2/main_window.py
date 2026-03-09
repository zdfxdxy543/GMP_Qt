import json
from pathlib import Path
from datetime import datetime

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QFileDialog,
    QGroupBox,
    QLabel,
    QMainWindow,
    QMenu,
    QPushButton,
    QSplitter,
    QTextEdit,
    QToolBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from dialogs.new_file_dialog import NewFileDialog
from widgets.timeline_widget import TimelineWidget


class MainWindow(QMainWindow):
    """Main page containing toolbar, timeline, and file preview areas."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("PyQt6 页面示例")
        self.resize(1200, 760)

        self.file_path_label = None
        self.file_content_edit = None
        self.selected_dot_label = None
        self.timeline_widget = None

        self._setup_toolbar()
        self._setup_central_ui()
        self.statusBar().showMessage("就绪")

    def _setup_toolbar(self):
        toolbar = QToolBar("顶部工具栏", self)
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        file_menu = QMenu("文件", self)

        new_action = QAction("新建...", self)
        read_action = QAction("读取...", self)
        file_menu.addAction(new_action)
        file_menu.addAction(read_action)

        new_action.triggered.connect(self.create_new_file)
        read_action.triggered.connect(self.read_file)

        file_button = QToolButton(self)
        file_button.setText("文件工具")
        file_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        file_button.setMenu(file_menu)
        toolbar.addWidget(file_button)

    def _setup_central_ui(self):
        central = QWidget(self)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(12, 12, 12, 12)
        root_layout.setSpacing(0)

        timeline = TimelineWidget(central)
        self.timeline_widget = timeline
        timeline.dot_selected.connect(self.on_dot_selected)

        top_panel = QGroupBox("上半区域", central)
        top_panel_layout = QVBoxLayout(top_panel)
        top_panel_layout.addWidget(QLabel("这里是次左侧 1/3 区域的上半部分", top_panel))
        self.selected_dot_label = QLabel("当前选中点: 无", top_panel)
        change_color_btn = QPushButton("流程步骤由系统状态控制", top_panel)
        change_color_btn.setEnabled(False)
        top_panel_layout.addWidget(self.selected_dot_label)
        top_panel_layout.addWidget(change_color_btn)

        bottom_panel = QGroupBox("下半区域", central)
        bottom_panel_layout = QVBoxLayout(bottom_panel)
        bottom_panel_layout.addWidget(QLabel("这里是次左侧 1/3 区域的下半部分", bottom_panel))

        # Middle column: vertical splitter for top/bottom areas.
        middle_splitter = QSplitter(Qt.Orientation.Vertical, central)
        middle_splitter.setChildrenCollapsible(False)
        middle_splitter.addWidget(top_panel)
        middle_splitter.addWidget(bottom_panel)
        middle_splitter.setSizes([1, 1])

        file_area = QWidget(central)
        file_layout = QVBoxLayout(file_area)
        file_layout.setContentsMargins(0, 0, 0, 0)
        file_layout.setSpacing(8)

        title = QLabel("文件内容读取 + 显示", file_area)
        title.setStyleSheet("font-weight: 600; font-size: 14px;")

        self.file_path_label = QLabel("路径: (未选择)", file_area)
        self.file_path_label.setWordWrap(True)

        self.file_content_edit = QTextEdit(file_area)
        self.file_content_edit.setPlaceholderText("点击 文件工具 -> 读取文件 来加载内容")

        file_layout.addWidget(title)
        file_layout.addWidget(self.file_path_label)
        file_layout.addWidget(self.file_content_edit, 1)

        # Outer splitter: horizontal, keeps default 1/6 : 1/3 : 1/2 and supports drag resize.
        horizontal_splitter = QSplitter(Qt.Orientation.Horizontal, central)
        horizontal_splitter.setChildrenCollapsible(False)
        horizontal_splitter.addWidget(timeline)
        horizontal_splitter.addWidget(middle_splitter)
        horizontal_splitter.addWidget(file_area)
        horizontal_splitter.setSizes([200, 400, 600])

        splitter_style = """
            QSplitter::handle {
                background-color: #d0d5db;
            }
            QSplitter::handle:hover {
                background-color: #7aa8ff;
            }
            QSplitter::handle:pressed {
                background-color: #4a7de0;
            }
            QSplitter::handle:horizontal {
                width: 10px;
                margin: 0 2px;
            }
            QSplitter::handle:vertical {
                height: 10px;
                margin: 2px 0;
            }
        """
        horizontal_splitter.setStyleSheet(splitter_style)
        middle_splitter.setStyleSheet(splitter_style)

        root_layout.addWidget(horizontal_splitter)
        self.setCentralWidget(central)

    def create_new_file(self):
        dialog = NewFileDialog(self)
        if dialog.exec() != NewFileDialog.DialogCode.Accepted:
            self.statusBar().showMessage("已取消新建", 2000)
            return

        selected = dialog.selected_config()
        folder = selected["folder"]
        controller = selected["controller"] or "(未选择控制器类型)"
        chip = selected["chip"] or "(未选择芯片类型)"
        file_name = selected.get("file_name", "").strip() or "new_file_config"

        if not folder:
            self.statusBar().showMessage("请选择目标文件夹后再确认", 3000)
            return

        folder_path = Path(folder)
        try:
            folder_path.mkdir(parents=True, exist_ok=True)
        except OSError:
            self.statusBar().showMessage("目标文件夹不可用，JSON 未生成", 3500)
            return

        if not file_name.lower().endswith(".json"):
            file_name = f"{file_name}.json"

        output_path = folder_path / file_name
        payload = {
            "file_name": file_name,
            "folder": str(folder_path),
            "controller": controller,
            "chip": chip,
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }

        try:
            # JSON file is created only after user confirms in the dialog.
            output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError:
            self.statusBar().showMessage("JSON 文件写入失败", 3500)
            return

        # Reset timeline state for a newly created file.
        self.timeline_widget.reset_after_file_created()

        self.file_path_label.setText(f"路径: {output_path}")
        self.file_content_edit.setPlainText(
            "\n".join(
                [
                    "# 已生成 JSON 配置",
                    f"json={output_path}",
                    f"file_name={file_name}",
                    f"controller={controller}",
                    f"chip={chip}",
                    f"folder={folder_path}",
                ]
            )
        )
        self.statusBar().showMessage("JSON 文件已生成", 2500)

    def read_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "选择要读取的文件", "", "所有文件 (*.*)")
        if not file_path:
            return

        try:
            content = Path(file_path).read_text(encoding="utf-8")
        except UnicodeDecodeError:
            content = Path(file_path).read_text(encoding="gbk", errors="replace")
        except OSError:
            self.statusBar().showMessage("文件打开失败", 3000)
            return

        self.file_path_label.setText(f"路径: {file_path}")
        self.file_content_edit.setPlainText(content)
        self.statusBar().showMessage("文件读取成功", 2000)

    def on_dot_selected(self, index):
        step_name = self.timeline_widget.step_name(index)
        self.selected_dot_label.setText(f"当前步骤: {step_name}")
        self.statusBar().showMessage(f"已选中步骤: {step_name}", 2000)

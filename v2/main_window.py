import json
from pathlib import Path
from datetime import datetime

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QDialog,
    QFileDialog,
    QGroupBox,
    QLabel,
    QMainWindow,
    QMenu,
    QWizard,
    QStackedWidget,
    QSplitter,
    QTextEdit,
    QToolBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from dialogs.new_file_dialog import NewFileDialog
from widgets.source_ui_loader import create_visual_widget_from_py
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
        self.top_stack = None
        self.bottom_stack = None
        self.top_page_meta = {}

        self.current_controller = ""
        self.current_chip = ""
        self.current_target_folder = ""

        self.step_py_map = {
            "ctrl_settings": "ctrl_settings_setup.py",
            "ctrl.config": "config_setup.py",
            "xplt.interface": "ctrl_interface.py",
            "xplt.peripheral.c": "peripheral_c.py",
            "xplt.peripheral.h": "peripheral_h.py",
            "simulink_buffer": "pc_simulate_buffer.py",
        }

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
        top_panel_layout.setContentsMargins(0, 0, 0, 0)
        top_panel_layout.setSpacing(0)
        self.top_stack = QStackedWidget(top_panel)
        self._init_middle_top_pages()
        top_panel_layout.addWidget(self.top_stack)

        bottom_panel = QGroupBox("下半区域", central)
        bottom_panel_layout = QVBoxLayout(bottom_panel)
        self.bottom_stack = QStackedWidget(bottom_panel)
        self._init_middle_bottom_pages()
        bottom_panel_layout.addWidget(self.bottom_stack)

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
        self._reload_top_visual_pages()
        self._switch_middle_pages(self.timeline_widget.selected_index)

    def _init_middle_top_pages(self):
        self.top_page_meta = {}
        for index, step_name in enumerate(self.timeline_widget.step_names):
            page = QWidget(self.top_stack)
            page_layout = QVBoxLayout(page)
            page_layout.setContentsMargins(0, 0, 0, 0)
            page_layout.setSpacing(0)

            content_host = QWidget(page)
            content_layout = QVBoxLayout(content_host)
            content_layout.setContentsMargins(0, 0, 0, 0)
            content_layout.setSpacing(0)

            page_layout.addWidget(content_host, 1)

            self.top_page_meta[step_name] = {
                "content_layout": content_layout,
                "content_widget": None,
            }

            self.top_stack.addWidget(page)

    def _project_root(self):
        return Path(__file__).resolve().parents[1]

    def _selected_chip_dir(self):
        if not self.current_controller or not self.current_chip:
            return None
        return self._project_root() / "src" / self.current_controller / self.current_chip

    def _build_placeholder_widget(self, text):
        panel = QWidget(self)
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(0, 0, 0, 0)
        tip = QLabel(text, panel)
        tip.setWordWrap(True)
        panel_layout.addWidget(tip)
        panel_layout.addStretch(1)
        return panel

    def _set_top_step_widget(self, step_name, widget):
        meta = self.top_page_meta.get(step_name)
        if not meta:
            return

        old_widget = meta.get("content_widget")
        if old_widget is not None:
            old_widget.setParent(None)
            old_widget.deleteLater()

        meta["content_layout"].addWidget(widget)
        meta["content_widget"] = widget

        if isinstance(widget, QWizard):
            widget.finished.connect(
                lambda result, step=step_name, wizard=widget: self._on_step_wizard_finished(step, wizard, result)
            )

    def _reload_top_visual_pages(self):
        chip_dir = self._selected_chip_dir()

        if chip_dir is None:
            for step_name in self.timeline_widget.step_names:
                placeholder = self._build_placeholder_widget("请先通过“新建”选择控制器类型和芯片类型。")
                self._set_top_step_widget(step_name, placeholder)
            return

        if not chip_dir.exists() or not chip_dir.is_dir():
            for step_name in self.timeline_widget.step_names:
                placeholder = self._build_placeholder_widget(f"未找到目录: {chip_dir}")
                self._set_top_step_widget(step_name, placeholder)
            return

        for step_name in self.timeline_widget.step_names:
            file_name = self.step_py_map.get(step_name)
            if not file_name:
                placeholder = self._build_placeholder_widget("该时间线节点暂无可视化映射。")
                self._set_top_step_widget(step_name, placeholder)
                continue

            module_path = chip_dir / file_name
            load_result = create_visual_widget_from_py(module_path, self.current_target_folder)
            self._set_top_step_widget(step_name, load_result.widget)

    def _output_file_name_by_step(self, step_name):
        output_map = {
            "ctrl_settings": "ctrl_settings.h",
            "ctrl.config": "xplt.config.h",
            "xplt.interface": "xplt.ctl_interface.h",
            "xplt.peripheral.c": "xplt.peripheral.c",
            "xplt.peripheral.h": "xplt.peripheral.h",
            "simulink_buffer": "pc_simulate_buffer.h",
        }
        return output_map.get(step_name)

    def _collect_existing_outputs(self, folder_path: Path):
        existing = {}
        for step_name in self.timeline_widget.step_names:
            file_name = self._output_file_name_by_step(step_name)
            if not file_name:
                continue
            candidate = folder_path / file_name
            if candidate.exists() and candidate.is_file():
                existing[step_name] = candidate
        return existing

    def _apply_timeline_status_from_outputs(self, existing):
        statuses = ["pending" for _ in self.timeline_widget.step_names]
        for index, step_name in enumerate(self.timeline_widget.step_names):
            if step_name in existing:
                statuses[index] = "done"

        if self.timeline_widget.step_names and self.timeline_widget.selected_index < 0:
            self.timeline_widget.selected_index = 0

        self.timeline_widget.step_status = statuses
        self.timeline_widget.update()

    def _show_step_output_in_right_panel(self, step_name, folder_path: Path):
        file_name = self._output_file_name_by_step(step_name)
        if not file_name:
            self.file_path_label.setText("路径: (当前步骤无对应输出文件)")
            self.file_content_edit.clear()
            return

        file_path = folder_path / file_name
        if not file_path.exists() or not file_path.is_file():
            self.file_path_label.setText(f"路径: {file_path} (未生成)")
            self.file_content_edit.clear()
            return

        try:
            content = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            content = file_path.read_text(encoding="gbk", errors="replace")

        self.file_path_label.setText(f"路径: {file_path}")
        self.file_content_edit.setPlainText(content)

    def _refresh_outputs_and_status(self, folder_path: Path):
        if not folder_path.exists() or not folder_path.is_dir():
            return

        existing = self._collect_existing_outputs(folder_path)
        self._apply_timeline_status_from_outputs(existing)
        selected_step = self.timeline_widget.step_name(self.timeline_widget.selected_index)
        self._show_step_output_in_right_panel(selected_step, folder_path)

    def _wizard_target_folder(self, wizard: QWizard):
        first_page = wizard.page(0)
        folder_input = getattr(first_page, "folder_input", None)
        if folder_input is None or not hasattr(folder_input, "text"):
            return ""
        return folder_input.text().strip()

    def _on_step_wizard_finished(self, step_name, wizard: QWizard, result):
        if result != int(QDialog.DialogCode.Accepted):
            return

        target_folder = self._wizard_target_folder(wizard)
        if not target_folder:
            target_folder = self.current_target_folder

        if not target_folder:
            return

        self.current_target_folder = target_folder
        self._refresh_outputs_and_status(Path(target_folder))
        self.statusBar().showMessage(f"步骤 {step_name} 已完成，已刷新输出", 2500)

    def _init_middle_bottom_pages(self):
        for index, step_name in enumerate(self.timeline_widget.step_names):
            page = QWidget(self.bottom_stack)
            page_layout = QVBoxLayout(page)

            title = QLabel(f"下半区域 - {step_name}", page)
            title.setStyleSheet("font-weight: 600; font-size: 14px;")
            detail = QLabel(
                f"当前步骤序号: {index + 1}\n当前步骤键名: {step_name}\n这里可放置该步骤专属的下半区控件。",
                page,
            )
            detail.setWordWrap(True)

            page_layout.addWidget(title)
            page_layout.addWidget(detail)
            page_layout.addStretch(1)

            self.bottom_stack.addWidget(page)

    def _switch_middle_pages(self, index):
        if not self.timeline_widget.step_names:
            return

        if index < 0 or index >= len(self.timeline_widget.step_names):
            index = 0

        self.top_stack.setCurrentIndex(index)
        self.bottom_stack.setCurrentIndex(index)

    def create_new_file(self):
        dialog = NewFileDialog(self)
        if dialog.exec() != NewFileDialog.DialogCode.Accepted:
            self.statusBar().showMessage("已取消新建", 2000)
            return

        selected = dialog.selected_config()
        folder = selected["folder"]
        self.current_controller = selected["controller"]
        self.current_chip = selected["chip"]
        self.current_target_folder = folder

        controller = self.current_controller or "(未选择控制器类型)"
        chip = self.current_chip or "(未选择芯片类型)"
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
        self._reload_top_visual_pages()
        self._switch_middle_pages(self.timeline_widget.selected_index)

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
        self._refresh_outputs_and_status(folder_path)
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

        selected_folder = Path(file_path).parent
        if Path(file_path).suffix.lower() == ".json":
            try:
                payload = json.loads(content)
                folder = payload.get("folder", "")
                controller = payload.get("controller", "")
                chip = payload.get("chip", "")

                if folder:
                    selected_folder = Path(folder)
                    self.current_target_folder = folder
                if controller:
                    self.current_controller = controller
                if chip:
                    self.current_chip = chip
                if controller or chip:
                    self._reload_top_visual_pages()
            except json.JSONDecodeError:
                pass

        self._refresh_outputs_and_status(selected_folder)
        self.statusBar().showMessage("文件读取成功", 2000)

    def on_dot_selected(self, index):
        step_name = self.timeline_widget.step_name(index)
        self._switch_middle_pages(index)
        if self.current_target_folder:
            self._show_step_output_in_right_panel(step_name, Path(self.current_target_folder))
        else:
            self.file_path_label.setText("路径: (未选择目标文件夹)")
            self.file_content_edit.clear()
        self.statusBar().showMessage(f"已选中步骤: {step_name}", 2000)

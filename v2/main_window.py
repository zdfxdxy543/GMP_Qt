import json
from pathlib import Path
from datetime import datetime

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QPushButton,
    QStyle,
    QWizard,
    QStackedWidget,
    QSplitter,
    QToolBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from dialogs.new_file_dialog import NewFileDialog
from widgets.code_editor import CodeEditor
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
        self.editor_language_combo = None

        self.current_controller = ""
        self.current_chip = ""
        self.current_target_folder = ""
        self.current_edit_file = None
        self.current_theme = "light"
        self.middle_splitter = None
        self.horizontal_splitter = None

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
        self._apply_window_theme(self.current_theme)
        self.statusBar().showMessage("就绪")

    def _light_theme_stylesheet(self):
        return """
            QMainWindow, QWidget {
                background-color: #f3f5f7;
                color: #1f2328;
            }
            QGroupBox {
                background-color: #ffffff;
                border: 1px solid #d0d7de;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 8px;
                font-weight: 600;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 8px;
                left: 8px;
                color: #1f2328;
            }
            QLabel {
                color: #1f2328;
            }
            QToolBar {
                background-color: #ffffff;
                border-bottom: 1px solid #d0d7de;
                spacing: 6px;
                padding: 4px 6px;
            }
            QToolButton {
                background-color: #ffffff;
                color: #1f2328;
                border: 1px solid #c9d1d9;
                border-radius: 6px;
                padding: 4px 10px;
            }
            QToolButton:hover {
                background-color: #e7f1ff;
                border-color: #8ab4f8;
            }
            QToolButton:pressed {
                background-color: #dbeafe;
            }
            QMenu {
                background-color: #ffffff;
                color: #1f2328;
                border: 1px solid #d0d7de;
            }
            QMenu::item {
                padding: 6px 18px;
            }
            QMenu::item:selected {
                background-color: #2f81f7;
                color: #ffffff;
            }
            QStatusBar {
                background-color: #ffffff;
                color: #1f2328;
                border-top: 1px solid #d0d7de;
            }
            QPushButton[editorToolButton="true"] {
                background-color: #ffffff;
                border: 1px solid #c9d1d9;
                border-radius: 6px;
                min-width: 30px;
                max-width: 30px;
                min-height: 30px;
                max-height: 30px;
                padding: 0px;
            }
            QPushButton[editorToolButton="true"]:hover {
                background-color: #e7f1ff;
                border-color: #8ab4f8;
            }
            QPushButton[editorToolButton="true"]:pressed {
                background-color: #dbeafe;
            }
            QPushButton[editorToolButton="true"]:disabled {
                background-color: #eef1f4;
                border-color: #d8dee4;
            }
            QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QListView, QTreeView {
                color: #1f2328;
            }
            """

    def _dark_theme_stylesheet(self):
        return """
            QMainWindow, QWidget {
                background-color: #1f2228;
                color: #d7dce2;
            }
            QGroupBox {
                background-color: #252a31;
                border: 1px solid #3a414c;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 8px;
                font-weight: 600;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 8px;
                left: 8px;
                color: #d7dce2;
            }
            QLabel {
                color: #d7dce2;
            }
            QToolBar {
                background-color: #252a31;
                border-bottom: 1px solid #3a414c;
                spacing: 6px;
                padding: 4px 6px;
            }
            QToolButton {
                background-color: #2f3540;
                color: #d7dce2;
                border: 1px solid #49515e;
                border-radius: 6px;
                padding: 4px 10px;
            }
            QToolButton:hover {
                background-color: #394252;
                border-color: #6b8fc9;
            }
            QToolButton:pressed {
                background-color: #314059;
            }
            QMenu {
                background-color: #252a31;
                color: #d7dce2;
                border: 1px solid #3a414c;
            }
            QMenu::item {
                padding: 6px 18px;
            }
            QMenu::item:selected {
                background-color: #2f81f7;
                color: #ffffff;
            }
            QStatusBar {
                background-color: #252a31;
                color: #d7dce2;
                border-top: 1px solid #3a414c;
            }
            QPushButton[editorToolButton="true"] {
                background-color: #2f3540;
                border: 1px solid #49515e;
                border-radius: 6px;
                min-width: 30px;
                max-width: 30px;
                min-height: 30px;
                max-height: 30px;
                padding: 0px;
            }
            QPushButton[editorToolButton="true"]:hover {
                background-color: #394252;
                border-color: #6b8fc9;
            }
            QPushButton[editorToolButton="true"]:pressed {
                background-color: #314059;
            }
            QPushButton[editorToolButton="true"]:disabled {
                background-color: #2a2f36;
                border-color: #3f4652;
            }
            QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QListView, QTreeView {
                color: #d7dce2;
            }
            """

    def _apply_splitter_style(self):
        if self.current_theme == "dark":
            splitter_style = """
                QSplitter::handle { background-color: #3f4652; }
                QSplitter::handle:hover { background-color: #6b8fc9; }
                QSplitter::handle:pressed { background-color: #4d74b8; }
                QSplitter::handle:horizontal { width: 10px; margin: 0 2px; }
                QSplitter::handle:vertical { height: 10px; margin: 2px 0; }
            """
        else:
            splitter_style = """
                QSplitter::handle { background-color: #d0d5db; }
                QSplitter::handle:hover { background-color: #7aa8ff; }
                QSplitter::handle:pressed { background-color: #4a7de0; }
                QSplitter::handle:horizontal { width: 10px; margin: 0 2px; }
                QSplitter::handle:vertical { height: 10px; margin: 2px 0; }
            """

        if self.horizontal_splitter is not None:
            self.horizontal_splitter.setStyleSheet(splitter_style)
        if self.middle_splitter is not None:
            self.middle_splitter.setStyleSheet(splitter_style)

    def _apply_window_theme(self, theme_name):
        self.current_theme = theme_name if theme_name in {"light", "dark"} else "light"
        stylesheet = self._dark_theme_stylesheet() if self.current_theme == "dark" else self._light_theme_stylesheet()
        self.setStyleSheet(stylesheet)
        self._apply_splitter_style()

        if self.file_content_edit is not None and hasattr(self.file_content_edit, "set_theme"):
            self.file_content_edit.set_theme(self.current_theme)
        if self.timeline_widget is not None and hasattr(self.timeline_widget, "set_theme"):
            self.timeline_widget.set_theme(self.current_theme)

    def _open_preferences_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("首选项")
        dialog.setModal(True)

        layout = QVBoxLayout(dialog)
        label = QLabel("主题", dialog)
        theme_combo = QComboBox(dialog)
        theme_combo.addItem("浅色", "light")
        theme_combo.addItem("深色", "dark")

        selected_index = theme_combo.findData(self.current_theme)
        if selected_index >= 0:
            theme_combo.setCurrentIndex(selected_index)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            Qt.Orientation.Horizontal,
            dialog,
        )
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)

        layout.addWidget(label)
        layout.addWidget(theme_combo)
        layout.addWidget(button_box)

        if dialog.exec() == int(QDialog.DialogCode.Accepted):
            self._apply_window_theme(theme_combo.currentData())

    def _setup_toolbar(self):
        toolbar = QToolBar("顶部工具栏", self)
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        file_menu = QMenu("文件", self)

        new_action = QAction("新建...", self)
        read_action = QAction("读取...", self)
        save_action = QAction("保存", self)
        save_as_action = QAction("另存为...", self)
        preferences_action = QAction("首选项...", self)

        new_action.setShortcut(QKeySequence.StandardKey.New)
        read_action.setShortcut(QKeySequence.StandardKey.Open)
        save_action.setShortcuts([QKeySequence.StandardKey.Save, QKeySequence("Ctrl+S")])
        save_as_action.setShortcut(QKeySequence.StandardKey.SaveAs)
        preferences_action.setShortcut(QKeySequence("Ctrl+,"))

        for action in (new_action, read_action, save_action, save_as_action, preferences_action):
            action.setShortcutContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)

        file_menu.addAction(new_action)
        file_menu.addAction(read_action)
        file_menu.addSeparator()
        file_menu.addAction(save_action)
        file_menu.addAction(save_as_action)
        file_menu.addSeparator()
        file_menu.addAction(preferences_action)

        new_action.triggered.connect(self.create_new_file)
        read_action.triggered.connect(self.read_file)
        save_action.triggered.connect(self.save_current_file)
        save_as_action.triggered.connect(self.save_file_as)
        preferences_action.triggered.connect(self._open_preferences_dialog)

        edit_menu = QMenu("编辑", self)

        undo_action = QAction("撤销", self)
        redo_action = QAction("恢复", self)
        copy_action = QAction("复制", self)
        cut_action = QAction("剪切", self)
        paste_action = QAction("粘贴", self)
        select_all_action = QAction("全选", self)

        undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        redo_action.setShortcuts([QKeySequence.StandardKey.Redo, QKeySequence("Ctrl+Y")])
        copy_action.setShortcut(QKeySequence.StandardKey.Copy)
        cut_action.setShortcut(QKeySequence.StandardKey.Cut)
        paste_action.setShortcut(QKeySequence.StandardKey.Paste)
        select_all_action.setShortcut(QKeySequence.StandardKey.SelectAll)

        for action in (undo_action, redo_action, copy_action, cut_action, paste_action, select_all_action):
            action.setShortcutContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)

        undo_action.triggered.connect(lambda: self._invoke_editor_method("undo"))
        redo_action.triggered.connect(lambda: self._invoke_editor_method("redo"))
        copy_action.triggered.connect(lambda: self._invoke_editor_method("copy"))
        cut_action.triggered.connect(lambda: self._invoke_editor_method("cut"))
        paste_action.triggered.connect(lambda: self._invoke_editor_method("paste"))
        select_all_action.triggered.connect(lambda: self._invoke_editor_method("selectAll"))

        edit_menu.addAction(undo_action)
        edit_menu.addAction(redo_action)
        edit_menu.addSeparator()
        edit_menu.addAction(copy_action)
        edit_menu.addAction(cut_action)
        edit_menu.addAction(paste_action)
        edit_menu.addSeparator()
        edit_menu.addAction(select_all_action)

        file_button = QToolButton(self)
        file_button.setText("文件工具")
        file_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        file_button.setMenu(file_menu)
        toolbar.addWidget(file_button)

        edit_button = QToolButton(self)
        edit_button.setText("编辑工具")
        edit_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        edit_button.setMenu(edit_menu)
        toolbar.addWidget(edit_button)

    def _invoke_editor_method(self, method_name):
        if self.file_content_edit is None:
            return
        method = getattr(self.file_content_edit, method_name, None)
        if callable(method):
            method()

    def _set_editor_language(self, language_name):
        if self.file_content_edit is not None and hasattr(self.file_content_edit, "set_language"):
            self.file_content_edit.set_language(language_name)

    def _sync_language_combo(self, language_name):
        if self.editor_language_combo is None:
            return
        index = self.editor_language_combo.findData(language_name)
        if index < 0:
            return
        was_blocked = self.editor_language_combo.blockSignals(True)
        self.editor_language_combo.setCurrentIndex(index)
        self.editor_language_combo.blockSignals(was_blocked)

    def _detect_language_from_file(self, file_path: Path):
        suffix = file_path.suffix.lower()
        if suffix == ".py":
            return "Python"
        if suffix in {".c", ".h"}:
            return "C"
        if suffix in {".cpp", ".cxx", ".cc", ".hpp", ".hh", ".hxx"}:
            return "C++"
        return self.editor_language_combo.currentData() if self.editor_language_combo is not None else "C++"

    def _apply_editor_language_by_path(self, file_path: Path):
        language_name = self._detect_language_from_file(file_path)
        self._sync_language_combo(language_name)
        self._set_editor_language(language_name)

    def _on_editor_language_changed(self):
        if self.editor_language_combo is None:
            return
        self._set_editor_language(self.editor_language_combo.currentData())

    def save_current_file(self):
        if self.file_content_edit is None:
            return

        if self.current_edit_file is None:
            self.save_file_as()
            return

        file_path = Path(self.current_edit_file)
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(self.file_content_edit.toPlainText(), encoding="utf-8")
        except OSError:
            self.statusBar().showMessage("保存失败", 3000)
            return

        self.file_path_label.setText(f"路径: {file_path}")
        self.statusBar().showMessage(f"已保存: {file_path.name}", 2000)

    def save_file_as(self):
        default_path = self.current_edit_file or (self._project_root() / "untitled.txt")
        file_path, _ = QFileDialog.getSaveFileName(self, "另存为", str(default_path), "所有文件 (*.*)")
        if not file_path:
            return

        self.current_edit_file = Path(file_path)
        self.save_current_file()

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
        self.middle_splitter = QSplitter(Qt.Orientation.Vertical, central)
        self.middle_splitter.setChildrenCollapsible(False)
        self.middle_splitter.addWidget(top_panel)
        self.middle_splitter.addWidget(bottom_panel)
        self.middle_splitter.setSizes([1, 1])

        file_area = QWidget(central)
        file_layout = QVBoxLayout(file_area)
        file_layout.setContentsMargins(0, 0, 0, 0)
        file_layout.setSpacing(8)

        file_header = QWidget(file_area)
        file_header_layout = QHBoxLayout(file_header)
        file_header_layout.setContentsMargins(0, 0, 0, 0)
        file_header_layout.setSpacing(8)

        title = QLabel("文件内容读取 + 显示", file_header)
        title.setStyleSheet("font-weight: 600; font-size: 14px;")

        self.editor_language_combo = QComboBox(file_header)
        self.editor_language_combo.addItem("C", "C")
        self.editor_language_combo.addItem("C++", "C++")
        self.editor_language_combo.addItem("Python", "Python")
        self.editor_language_combo.setCurrentIndex(self.editor_language_combo.findData("C++"))
        self.editor_language_combo.setToolTip("选择编辑器关键词与补全语言")
        self.editor_language_combo.currentIndexChanged.connect(self._on_editor_language_changed)

        file_header_layout.addWidget(title)
        file_header_layout.addStretch(1)
        file_header_layout.addWidget(self.editor_language_combo)

        self.file_path_label = QLabel("路径: (未选择)", file_area)
        self.file_path_label.setWordWrap(True)

        editor_tools = QWidget(file_area)
        editor_tools_layout = QHBoxLayout(editor_tools)
        editor_tools_layout.setContentsMargins(0, 0, 0, 0)
        editor_tools_layout.setSpacing(6)

        save_btn = QPushButton(editor_tools)
        undo_btn = QPushButton(editor_tools)
        redo_btn = QPushButton(editor_tools)

        save_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton))
        undo_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowBack))
        redo_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowForward))

        for button, tooltip in (
            (save_btn, "保存 (Ctrl+S)"),
            (undo_btn, "撤销 (Ctrl+Z)"),
            (redo_btn, "恢复 (Ctrl+Y / Ctrl+Shift+Z)"),
        ):
            button.setToolTip(tooltip)
            button.setProperty("editorToolButton", True)
            button.setFixedSize(30, 30)
            button.setIconSize(QSize(18, 18))

        save_btn.clicked.connect(self.save_current_file)
        undo_btn.clicked.connect(lambda: self._invoke_editor_method("undo"))
        redo_btn.clicked.connect(lambda: self._invoke_editor_method("redo"))

        editor_tools_layout.addWidget(save_btn)
        editor_tools_layout.addWidget(undo_btn)
        editor_tools_layout.addWidget(redo_btn)
        editor_tools_layout.addStretch(1)

        self.file_content_edit = CodeEditor(self._project_root(), file_area)
        self.file_content_edit.setPlaceholderText("点击 文件工具 -> 读取文件 来加载内容")
        self._set_editor_language(self.editor_language_combo.currentData())

        file_layout.addWidget(file_header)
        file_layout.addWidget(self.file_path_label)
        file_layout.addWidget(editor_tools)
        file_layout.addWidget(self.file_content_edit, 1)

        # Outer splitter: horizontal, keeps default 1/6 : 1/3 : 1/2 and supports drag resize.
        self.horizontal_splitter = QSplitter(Qt.Orientation.Horizontal, central)
        self.horizontal_splitter.setChildrenCollapsible(False)
        self.horizontal_splitter.addWidget(timeline)
        self.horizontal_splitter.addWidget(self.middle_splitter)
        self.horizontal_splitter.addWidget(file_area)
        self.horizontal_splitter.setSizes([200, 400, 600])

        root_layout.addWidget(self.horizontal_splitter)
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
            self.current_edit_file = None
            return

        file_path = folder_path / file_name
        if not file_path.exists() or not file_path.is_file():
            self.file_path_label.setText(f"路径: {file_path} (未生成)")
            self.file_content_edit.clear()
            self.current_edit_file = None
            return

        try:
            content = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            content = file_path.read_text(encoding="gbk", errors="replace")

        self.file_path_label.setText(f"路径: {file_path}")
        self.file_content_edit.setPlainText(content)
        self.file_content_edit.add_tokens_from_text(content)
        self.current_edit_file = file_path
        self._apply_editor_language_by_path(file_path)

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
        self.file_content_edit.add_tokens_from_text(self.file_content_edit.toPlainText())
        self.current_edit_file = output_path
        self._apply_editor_language_by_path(output_path)
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
        self.file_content_edit.add_tokens_from_text(content)
        self.current_edit_file = Path(file_path)
        self._apply_editor_language_by_path(Path(file_path))

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
            self.current_edit_file = None
        self.statusBar().showMessage(f"已选中步骤: {step_name}", 2000)

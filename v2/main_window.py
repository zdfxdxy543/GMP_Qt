import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path
from datetime import datetime

from PyQt6.QtCore import QEvent, QObject, QPoint, QThread, QTimer, Qt, QSize, pyqtSignal
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLineEdit,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QStyle,
    QWizard,
    QStackedWidget,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QToolBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from dialogs.new_file_dialog import NewFileDialog
from widgets.code_editor import CodeEditor
from widgets.block_library_manager import BlockLibraryManager
from widgets.source_ui_loader import create_visual_widget_from_py
from widgets.timeline_widget import TimelineWidget


class _BlockPreviewPopup(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.ToolTip)
        self.setObjectName("blockPreviewPopup")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setMinimumSize(420, 260)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        self.title_label = QLabel("程序块预览", self)
        self.title_label.setStyleSheet("font-weight: 600;")

        self.preview_edit = QPlainTextEdit(self)
        self.preview_edit.setReadOnly(True)

        layout.addWidget(self.title_label)
        layout.addWidget(self.preview_edit, 1)

    def set_preview(self, title: str, text: str):
        self.title_label.setText(title)
        self.preview_edit.setPlainText(text)


class _AssistantApiWorker(QObject):
    finished = pyqtSignal(dict)

    def __init__(
        self,
        api_key: str,
        model_name: str,
        api_url: str,
        question: str,
        context: dict,
        candidate_blocks: list[dict],
    ):
        super().__init__()
        self.api_key = api_key
        self.model_name = model_name
        self.api_url = api_url
        self.question = question
        self.context = context
        self.candidate_blocks = candidate_blocks

    def run(self):
        if not self.api_key.strip():
            self.finished.emit({"ok": False, "error": "未配置 SILICONFLOW_API_KEY"})
            return

        endpoint = self.api_url.strip() or "https://api.siliconflow.cn/v1/chat/completions"
        context_brief = {
            "controller": self.context.get("controller", ""),
            "chip": self.context.get("chip", ""),
            "step": self.context.get("step", ""),
        }
        prompt = {
            "role": "user",
            "content": (
                "用户问题: "
                + self.question
                + "\n\n"
                + "工程上下文: "
                + json.dumps(context_brief, ensure_ascii=False)
                + "\n\n"
                + "候选程序块: "
                + json.dumps(self.candidate_blocks, ensure_ascii=False)
                + "\n\n"
                + "请基于候选程序块回答，优先说明应该使用哪些程序块和大致步骤。"
                + "如果候选不足，也要明确指出缺少哪些信息。"
            ),
        }

        payload = {
            "model": self.model_name,
            "messages": [
                {
                    "role": "system",
                    "content": "你是电机控制代码助手。回答要简洁，尽量给出可执行建议。",
                },
                prompt,
            ],
            "temperature": 0.2,
            "max_tokens": 700,
        }

        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            endpoint,
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=35) as response:
                response_text = response.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace") if hasattr(exc, "read") else str(exc)
            self.finished.emit({"ok": False, "error": f"HTTP {exc.code}: {detail}"})
            return
        except Exception as exc:  # noqa: BLE001
            self.finished.emit({"ok": False, "error": str(exc)})
            return

        try:
            data = json.loads(response_text)
            content = str(data["choices"][0]["message"].get("content", "")).strip()
        except (ValueError, KeyError, IndexError, TypeError):
            self.finished.emit({"ok": False, "error": "模型返回格式无法解析"})
            return

        self.finished.emit({"ok": True, "answer": content})


class _AssistantChatDialog(QDialog):
    def __init__(self, context_provider, recommend_blocks, jump_to_block, api_config_provider, parent=None):
        super().__init__(parent)
        self.setWindowTitle("智能助手")
        self.resize(620, 640)
        self.context_provider = context_provider
        self.recommend_blocks = recommend_blocks
        self.jump_to_block = jump_to_block
        self.api_config_provider = api_config_provider
        self._active_thread = None
        self._active_worker = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        title_label = QLabel("硅基流动智能助手", self)
        title_label.setStyleSheet("font-size: 15px; font-weight: 600;")

        tip_label = QLabel("支持本地程序块检索。若设置 SILICONFLOW_API_KEY，将自动调用硅基流动补充回答。", self)
        tip_label.setWordWrap(True)

        self.context_label = QLabel("上下文: -", self)
        self.context_label.setWordWrap(True)

        self.history_edit = QPlainTextEdit(self)
        self.history_edit.setReadOnly(True)
        self.history_edit.setPlaceholderText("对话记录将显示在这里")

        rec_title = QLabel("推荐程序块", self)
        rec_title.setStyleSheet("font-weight: 600;")

        self.recommend_list = QListWidget(self)
        self.recommend_list.setMinimumHeight(140)

        rec_actions = QWidget(self)
        rec_actions_layout = QHBoxLayout(rec_actions)
        rec_actions_layout.setContentsMargins(0, 0, 0, 0)
        rec_actions_layout.setSpacing(8)
        self.jump_button = QPushButton("定位到推荐程序块", rec_actions)
        rec_actions_layout.addStretch(1)
        rec_actions_layout.addWidget(self.jump_button)

        self.input_edit = QPlainTextEdit(self)
        self.input_edit.setPlaceholderText("例如：我该如何实现 PID 控制？")
        self.input_edit.setFixedHeight(96)

        actions = QWidget(self)
        actions_layout = QHBoxLayout(actions)
        actions_layout.setContentsMargins(0, 0, 0, 0)
        actions_layout.setSpacing(8)

        self.send_button = QPushButton("发送", actions)
        self.close_button = QPushButton("关闭", actions)

        actions_layout.addStretch(1)
        actions_layout.addWidget(self.send_button)
        actions_layout.addWidget(self.close_button)

        layout.addWidget(title_label)
        layout.addWidget(tip_label)
        layout.addWidget(self.context_label)
        layout.addWidget(self.history_edit, 1)
        layout.addWidget(rec_title)
        layout.addWidget(self.recommend_list)
        layout.addWidget(rec_actions)
        layout.addWidget(self.input_edit)
        layout.addWidget(actions)

        self.send_button.clicked.connect(self._handle_send)
        self.close_button.clicked.connect(self.close)
        self.jump_button.clicked.connect(self._handle_jump)
        self.recommend_list.itemDoubleClicked.connect(lambda _item: self._handle_jump())

    def _append_message(self, role: str, text: str):
        if not text.strip():
            return
        current = self.history_edit.toPlainText().strip()
        prefix = "\n\n" if current else ""
        self.history_edit.setPlainText(f"{current}{prefix}{role}:\n{text.strip()}")
        cursor = self.history_edit.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.history_edit.setTextCursor(cursor)

    def _handle_send(self):
        user_text = self.input_edit.toPlainText().strip()
        if not user_text:
            return

        context = self.context_provider() if callable(self.context_provider) else {}
        self._update_context_label(context)

        self._append_message("你", user_text)
        self.input_edit.clear()

        candidates = self.recommend_blocks(user_text, context) if callable(self.recommend_blocks) else []
        self._render_recommendations(candidates)

        if candidates:
            top_names = "、".join(item.get("name", item.get("id", "")) for item in candidates[:3])
            local_answer = f"基于本地知识库，建议优先关注这些程序块: {top_names}。"
        else:
            local_answer = "本地知识库未检索到高相关程序块，请尝试补充关键词（如速度环、电流环、采样、PWM）。"
        self._append_message("助手", local_answer)

        api_config = self.api_config_provider() if callable(self.api_config_provider) else {}
        api_key = str(api_config.get("api_key", "")).strip()
        if not api_key:
            self._append_message("助手", "未配置 API Key（首选项 -> API 设置），当前只提供本地推荐结果。")
            return

        if self._active_thread is not None:
            self._append_message("助手", "上一条模型请求仍在处理中，请稍候。")
            return

        self.send_button.setEnabled(False)
        self._append_message("助手", "正在请求硅基流动模型，请稍候...")

        model_name = str(api_config.get("model", "")).strip() or "Qwen/Qwen2.5-7B-Instruct"
        api_url = str(api_config.get("api_url", "")).strip() or "https://api.siliconflow.cn/v1/chat/completions"
        self._active_worker = _AssistantApiWorker(api_key, model_name, api_url, user_text, context, candidates[:8])
        self._active_thread = QThread(self)
        self._active_worker.moveToThread(self._active_thread)
        self._active_thread.started.connect(self._active_worker.run)
        self._active_worker.finished.connect(self._on_model_reply)
        self._active_worker.finished.connect(self._active_thread.quit)
        self._active_worker.finished.connect(self._active_worker.deleteLater)
        self._active_thread.finished.connect(self._active_thread.deleteLater)
        self._active_thread.finished.connect(self._clear_active_request)
        self._active_thread.start()

    def _update_context_label(self, context: dict):
        controller = str(context.get("controller", "-") or "-")
        chip = str(context.get("chip", "-") or "-")
        step = str(context.get("step", "-") or "-")
        self.context_label.setText(f"上下文: controller={controller} | chip={chip} | step={step}")

    def _render_recommendations(self, candidates: list[dict]):
        self.recommend_list.clear()
        for item in candidates:
            block_id = str(item.get("id", "")).strip()
            if not block_id:
                continue
            text = f"{item.get('name', block_id)}  [{item.get('library', '未分类')}]"
            list_item = QListWidgetItem(text)
            list_item.setData(Qt.ItemDataRole.UserRole, block_id)
            reason = str(item.get("reason", "")).strip()
            if reason:
                list_item.setToolTip(reason)
            self.recommend_list.addItem(list_item)

        if self.recommend_list.count() > 0:
            self.recommend_list.setCurrentRow(0)

    def _handle_jump(self):
        item = self.recommend_list.currentItem()
        if item is None or not callable(self.jump_to_block):
            return
        block_id = str(item.data(Qt.ItemDataRole.UserRole) or "").strip()
        if not block_id:
            return
        self.jump_to_block(block_id)

    def _on_model_reply(self, result: dict):
        if result.get("ok"):
            answer = str(result.get("answer", "")).strip()
            self._append_message("助手(模型)", answer or "模型未返回内容")
        else:
            self._append_message("助手", f"模型请求失败: {result.get('error', '未知错误')}")

        self.send_button.setEnabled(True)

    def _clear_active_request(self):
        self._active_thread = None
        self._active_worker = None


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
        self.bottom_page_meta = {}
        self.editor_language_combo = None

        self.current_controller = ""
        self.current_chip = ""
        self.current_target_folder = ""
        self.step_target_folders = {}
        self.current_config_json_path = None
        self.current_edit_file = None
        self.current_theme = "light"
        self.middle_splitter = None
        self.horizontal_splitter = None
        self.block_library_manager = BlockLibraryManager(self._project_root() / "v2" / "block_library")
        self.editor_insert_position = 0
        self.editor_insert_line = 1
        self.editor_insert_column = 1
        self.global_position_label = None
        self.editor_dirty = False
        self._editor_baseline_text = ""
        self._suspend_dirty_tracking = False
        self._active_step_index = -1
        self.block_preview_popup = None
        self.block_hover_timer = None
        self.pending_hover_preview = None
        self.block_list_viewports = {}
        self.middle_bottom_panel = None
        self.assistant_fab = None
        self.assistant_dialog = None
        self.assistant_api_key = os.getenv("SILICONFLOW_API_KEY", "").strip()
        self.assistant_model = os.getenv("SILICONFLOW_MODEL", "Qwen/Qwen2.5-7B-Instruct").strip()
        self.assistant_api_url = os.getenv("SILICONFLOW_API_URL", "https://api.siliconflow.cn/v1/chat/completions").strip()

        self._load_assistant_settings()

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
        self._setup_global_status_widgets()
        self._setup_block_preview_support()
        self.statusBar().showMessage("就绪")

    def _setup_global_status_widgets(self):
        self.global_position_label = QLabel("插入位置: 第 1 行, 第 1 列", self)
        self.statusBar().addPermanentWidget(self.global_position_label)

    def _setup_block_preview_support(self):
        self.block_preview_popup = _BlockPreviewPopup(self)
        self.block_hover_timer = QTimer(self)
        self.block_hover_timer.setSingleShot(True)
        self.block_hover_timer.setInterval(450)
        self.block_hover_timer.timeout.connect(self._show_pending_block_preview)

    def _hide_block_preview(self):
        if self.block_hover_timer is not None:
            self.block_hover_timer.stop()
        self.pending_hover_preview = None
        if self.block_preview_popup is not None:
            self.block_preview_popup.hide()

    def _schedule_block_preview(self, step_name: str, list_widget: QListWidget, item: QListWidgetItem | None):
        self._hide_block_preview()
        if item is None:
            return

        block_id = str(item.data(Qt.ItemDataRole.UserRole) or "").strip()
        if not block_id:
            return

        item_rect = list_widget.visualItemRect(item)
        global_pos = list_widget.viewport().mapToGlobal(item_rect.bottomRight() + QPoint(12, 8))
        self.pending_hover_preview = {
            "step_name": step_name,
            "block_id": block_id,
            "global_pos": global_pos,
        }
        self.block_hover_timer.start()

    def _build_block_preview_text(self, step_name: str, block: dict):
        code_template = str(block.get("code_template", "")).rstrip()
        active_file = Path(self.current_edit_file) if self.current_edit_file else self._default_insert_target_file(step_name)
        if active_file is None:
            return code_template or "(无程序块代码)"

        target_folder = Path(self.current_target_folder) if self.current_target_folder else active_file.parent
        selected_language = self._detect_language_from_file(active_file)
        preview_result = self.block_library_manager.preview_missing_definitions_for_language(
            block,
            target_folder,
            active_file,
            selected_language,
        )

        sections = []
        if not preview_result.get("ok"):
            sections.append(str(preview_result.get("message", "预览检查失败")))
        else:
            missing_definitions = preview_result.get("missing_definitions", [])
            if missing_definitions:
                sections.append("[将补齐的变量声明]\n" + "\n".join(missing_definitions))
            else:
                sections.append("[变量声明]\n(无新增声明)")

        sections.append("[将插入的程序块]\n" + (code_template or "(无程序块代码)"))
        return "\n\n".join(sections)

    def _show_pending_block_preview(self):
        if not self.pending_hover_preview or self.block_preview_popup is None:
            return

        step_name = self.pending_hover_preview.get("step_name", "")
        block_id = self.pending_hover_preview.get("block_id", "")
        global_pos = self.pending_hover_preview.get("global_pos", QPoint(0, 0))
        block = self.block_library_manager.get_block(block_id)
        if not block:
            return

        block_name = str(block.get("name", block_id))
        preview_text = self._build_block_preview_text(step_name, block)
        self.block_preview_popup.set_preview(f"程序块预览 - {block_name}", preview_text)
        self.block_preview_popup.adjustSize()
        self.block_preview_popup.move(global_pos)
        self.block_preview_popup.show()

    def eventFilter(self, watched, event):
        step_name = self.block_list_viewports.get(watched)
        if step_name is not None:
            if event.type() == QEvent.Type.Leave:
                self._hide_block_preview()
            elif event.type() == QEvent.Type.MouseMove:
                list_widget = self.bottom_page_meta.get(step_name, {}).get("block_list")
                if list_widget is not None and list_widget.itemAt(event.position().toPoint()) is None:
                    self._hide_block_preview()
        return super().eventFilter(watched, event)

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
            QPushButton[assistantFab="true"] {
                background-color: #0f766e;
                color: #ffffff;
                border: 1px solid #0d5f58;
                border-radius: 26px;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton[assistantFab="true"]:hover {
                background-color: #0d9488;
                border-color: #0f766e;
            }
            QPushButton[assistantFab="true"]:pressed {
                background-color: #0b6a63;
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
            QPushButton[assistantFab="true"] {
                background-color: #15907f;
                color: #ffffff;
                border: 1px solid #1fb8a4;
                border-radius: 26px;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton[assistantFab="true"]:hover {
                background-color: #1aa895;
                border-color: #52ccb8;
            }
            QPushButton[assistantFab="true"]:pressed {
                background-color: #13796b;
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

    def _assistant_settings_path(self):
        return self._project_root() / "v2" / ".assistant_settings.json"

    def _load_assistant_settings(self):
        settings_path = self._assistant_settings_path()
        if not settings_path.exists() or not settings_path.is_file():
            return

        try:
            payload = json.loads(settings_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return

        if not isinstance(payload, dict):
            return

        self.assistant_api_key = str(payload.get("api_key", self.assistant_api_key) or "").strip()
        self.assistant_model = str(payload.get("model", self.assistant_model) or "").strip()
        self.assistant_api_url = str(payload.get("api_url", self.assistant_api_url) or "").strip()

    def _save_assistant_settings(self):
        settings_path = self._assistant_settings_path()
        payload = {
            "api_key": self.assistant_api_key,
            "model": self.assistant_model,
            "api_url": self.assistant_api_url,
            "updated_at": datetime.now().isoformat(timespec="seconds"),
        }
        try:
            settings_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            return True
        except OSError:
            return False

    def _assistant_api_config(self):
        return {
            "api_key": self.assistant_api_key,
            "model": self.assistant_model,
            "api_url": self.assistant_api_url,
        }

    def _open_preferences_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("首选项")
        dialog.setModal(True)
        dialog.resize(560, 360)

        layout = QVBoxLayout(dialog)
        label = QLabel("主题", dialog)
        theme_combo = QComboBox(dialog)
        theme_combo.addItem("浅色", "light")
        theme_combo.addItem("深色", "dark")

        selected_index = theme_combo.findData(self.current_theme)
        if selected_index >= 0:
            theme_combo.setCurrentIndex(selected_index)

        api_group = QGroupBox("硅基流动 API 设置", dialog)
        api_layout = QVBoxLayout(api_group)
        api_layout.setContentsMargins(10, 10, 10, 10)
        api_layout.setSpacing(8)

        api_key_label = QLabel("API Key", api_group)
        api_key_input = QLineEdit(api_group)
        api_key_input.setPlaceholderText("例如：sk-...")
        api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        api_key_input.setText(self.assistant_api_key)

        show_api_key_checkbox = QCheckBox("显示 API Key", api_group)

        model_label = QLabel("模型名", api_group)
        model_input = QLineEdit(api_group)
        model_input.setPlaceholderText("例如：Qwen/Qwen2.5-7B-Instruct")
        model_input.setText(self.assistant_model)

        api_url_label = QLabel("接口地址", api_group)
        api_url_input = QLineEdit(api_group)
        api_url_input.setPlaceholderText("例如：https://api.siliconflow.cn/v1/chat/completions")
        api_url_input.setText(self.assistant_api_url)

        def on_toggle_api_key(checked):
            mode = QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
            api_key_input.setEchoMode(mode)

        show_api_key_checkbox.toggled.connect(on_toggle_api_key)

        api_layout.addWidget(api_key_label)
        api_layout.addWidget(api_key_input)
        api_layout.addWidget(show_api_key_checkbox)
        api_layout.addWidget(model_label)
        api_layout.addWidget(model_input)
        api_layout.addWidget(api_url_label)
        api_layout.addWidget(api_url_input)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            Qt.Orientation.Horizontal,
            dialog,
        )
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)

        layout.addWidget(label)
        layout.addWidget(theme_combo)
        layout.addWidget(api_group)
        layout.addWidget(button_box)

        if dialog.exec() == int(QDialog.DialogCode.Accepted):
            self._apply_window_theme(theme_combo.currentData())
            self.assistant_api_key = api_key_input.text().strip()
            self.assistant_model = model_input.text().strip() or "Qwen/Qwen2.5-7B-Instruct"
            self.assistant_api_url = api_url_input.text().strip() or "https://api.siliconflow.cn/v1/chat/completions"
            if self._save_assistant_settings():
                self.statusBar().showMessage("首选项已保存", 2000)
            else:
                self.statusBar().showMessage("首选项保存失败（仅本次会话生效）", 3500)

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

    def _on_editor_cursor_position_changed(self):
        if self.file_content_edit is None:
            return

        cursor = self.file_content_edit.textCursor()
        self.editor_insert_position = cursor.position()
        self.editor_insert_line = cursor.blockNumber() + 1
        self.editor_insert_column = cursor.positionInBlock() + 1
        self._update_insert_position_labels()

    def _update_insert_position_labels(self):
        text = f"插入位置: 第 {self.editor_insert_line} 行, 第 {self.editor_insert_column} 列"
        if self.global_position_label is not None:
            self.global_position_label.setText(text)

    def _set_file_path_label(self, text: str):
        if self.file_path_label is None:
            return
        self.file_path_label.setText(text)
        if self.editor_dirty and not text.endswith(" *"):
            self.file_path_label.setText(f"{text} *")

    def _set_editor_dirty(self, dirty: bool):
        self.editor_dirty = bool(dirty)
        if self.file_path_label is None:
            return

        current = self.file_path_label.text()
        if self.editor_dirty:
            if not current.endswith(" *"):
                self.file_path_label.setText(f"{current} *")
        else:
            if current.endswith(" *"):
                self.file_path_label.setText(current[:-2])

    def _on_editor_text_changed(self):
        if self._suspend_dirty_tracking:
            return

        current_text = self.file_content_edit.toPlainText()
        if self.current_edit_file is None and not current_text.strip():
            self._editor_baseline_text = current_text
            self._set_editor_dirty(False)
            return
        self._set_editor_dirty(current_text != self._editor_baseline_text)

    def _set_editor_text(self, text: str, mark_dirty: bool = False):
        if self.file_content_edit is None:
            return
        self._suspend_dirty_tracking = True
        try:
            self.file_content_edit.setPlainText(text)
            self.file_content_edit.add_tokens_from_text(text)
        finally:
            self._suspend_dirty_tracking = False
        if not mark_dirty:
            self._editor_baseline_text = text
        self._set_editor_dirty(mark_dirty)

    def _clear_editor_text(self):
        if self.file_content_edit is None:
            return
        self._suspend_dirty_tracking = True
        try:
            self.file_content_edit.clear()
        finally:
            self._suspend_dirty_tracking = False
        self._editor_baseline_text = ""
        self._set_editor_dirty(False)

    def _prompt_save_if_dirty(self, action_text: str):
        if not self.editor_dirty:
            return True

        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Warning)
        box.setWindowTitle("未保存更改")
        box.setText(f"当前文件有未保存更改，是否先保存再{action_text}？")
        box.setInformativeText("选择“保存”将写入文件；选择“不保存”将放弃未保存改动。")
        box.setStandardButtons(
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel
        )
        box.setDefaultButton(QMessageBox.StandardButton.Save)
        choice = box.exec()

        if choice == QMessageBox.StandardButton.Cancel:
            return False
        if choice == QMessageBox.StandardButton.Discard:
            return True

        self.save_current_file()
        return not self.editor_dirty

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

        self._set_file_path_label(f"路径: {file_path}")
        self._apply_editor_language_by_path(file_path)
        self._editor_baseline_text = self.file_content_edit.toPlainText()
        self._set_editor_dirty(False)
        self.statusBar().showMessage(f"已保存: {file_path.name}", 2000)

    def save_file_as(self):
        default_path = self.current_edit_file or (self._project_root() / "untitled.txt")
        file_path, _ = QFileDialog.getSaveFileName(self, "另存为", str(default_path), "所有文件 (*.*)")
        if not file_path:
            return

        self.current_edit_file = Path(file_path)
        self._apply_editor_language_by_path(self.current_edit_file)
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
        self.middle_bottom_panel = bottom_panel
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
        self.file_content_edit.cursorPositionChanged.connect(self._on_editor_cursor_position_changed)
        self.file_content_edit.textChanged.connect(self._on_editor_text_changed)

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
        self._active_step_index = self.timeline_widget.selected_index
        self._on_editor_cursor_position_changed()
        self._set_editor_dirty(False)
        self._setup_assistant_ui()
        self.middle_splitter.splitterMoved.connect(self._on_middle_splitter_moved)
        QTimer.singleShot(0, self._update_assistant_fab_position)

    def _setup_assistant_ui(self):
        if self.middle_bottom_panel is None:
            return
        if self.assistant_fab is None:
            self.assistant_fab = QPushButton("AI", self.middle_bottom_panel)
            self.assistant_fab.setProperty("assistantFab", True)
            self.assistant_fab.setFixedSize(52, 52)
            self.assistant_fab.setToolTip("打开智能助手")
            self.assistant_fab.clicked.connect(self._open_assistant_dialog)
            self.assistant_fab.show()
        self.assistant_fab.raise_()
        self._update_assistant_fab_position()

    def _on_middle_splitter_moved(self, *_args):
        self._update_assistant_fab_position()

    def _update_assistant_fab_position(self):
        if self.middle_bottom_panel is None or self.assistant_fab is None:
            return

        margin = 14
        x = max(margin, self.middle_bottom_panel.width() - self.assistant_fab.width() - margin)
        y = max(margin, self.middle_bottom_panel.height() - self.assistant_fab.height() - margin)
        self.assistant_fab.move(x, y)
        self.assistant_fab.raise_()

    def _open_assistant_dialog(self):
        if self.assistant_dialog is None:
            self.assistant_dialog = _AssistantChatDialog(
                self._assistant_context,
                self._assistant_recommend_blocks,
                self._assistant_jump_to_block,
                self._assistant_api_config,
                self,
            )
        self.assistant_dialog.show()
        self.assistant_dialog.raise_()
        self.assistant_dialog.activateWindow()

    def _assistant_context(self):
        current_step = self.timeline_widget.step_name(self.timeline_widget.selected_index)
        return {
            "controller": self.current_controller,
            "chip": self.current_chip,
            "step": current_step,
            "target_folder": self.current_target_folder,
        }

    def _assistant_recommend_blocks(self, question: str, context: dict, limit: int = 6):
        query = str(question or "").strip().lower()
        if not query:
            return []

        tokens = [token for token in re.findall(r"[\w\u4e00-\u9fff]+", query) if token]
        step_name = str(context.get("step", "") or "")
        candidates = []

        for block in self.block_library_manager.blocks:
            block_id = str(block.get("id", "")).strip()
            if not block_id:
                continue

            steps = block.get("steps", [])
            if isinstance(steps, list) and steps and step_name and step_name not in steps:
                continue

            name = str(block.get("name", ""))
            library = str(block.get("library", ""))
            language = str(block.get("language", ""))
            code_template = str(block.get("code_template", ""))
            haystack = " ".join([block_id, name, library, language, code_template]).lower()

            score = 0
            reasons = []
            for token in tokens:
                if token in haystack:
                    score += 2
                    reasons.append(f"命中关键词: {token}")
                if token in block_id.lower() or token in name.lower():
                    score += 3

            if any(key in query for key in ["pid", "pi", "速度", "电流", "控制"]):
                control_text = f"{name} {library} {block_id}".lower()
                if any(key in control_text for key in ["pi", "pid", "控制", "speed", "current"]):
                    score += 3
                    reasons.append("控制算法语义相关")

            if score <= 0:
                continue

            candidates.append(
                {
                    "id": block_id,
                    "name": name or block_id,
                    "library": library or "未分类",
                    "language": language,
                    "score": score,
                    "reason": "；".join(dict.fromkeys(reasons)) if reasons else "语义相关",
                }
            )

        candidates.sort(key=lambda item: (item.get("score", 0), item.get("name", "")), reverse=True)
        return candidates[:limit]

    def _assistant_jump_to_block(self, block_id: str):
        block = self.block_library_manager.get_block(block_id)
        if not block:
            self.statusBar().showMessage(f"未找到程序块: {block_id}", 2500)
            return

        target_step = self.timeline_widget.step_name(self.timeline_widget.selected_index)
        steps = block.get("steps", []) if isinstance(block.get("steps", []), list) else []
        if steps:
            first_step = str(steps[0]).strip()
            if first_step in self.timeline_widget.step_names:
                target_step = first_step

        if target_step in self.timeline_widget.step_names:
            step_index = self.timeline_widget.step_names.index(target_step)
            self.timeline_widget.selected_index = step_index
            self.timeline_widget.update()
            self.on_dot_selected(step_index)

        meta = self.bottom_page_meta.get(target_step)
        if not meta:
            self.statusBar().showMessage(f"当前步骤未找到程序块列表: {target_step}", 2500)
            return

        self._refresh_block_list_for_step(target_step)
        block_list = meta.get("block_list")
        if block_list is None:
            return

        for row in range(block_list.count()):
            item = block_list.item(row)
            if item is None:
                continue
            if str(item.data(Qt.ItemDataRole.UserRole) or "").strip() == block_id:
                block_list.setCurrentItem(item)
                block_list.scrollToItem(item)
                self.statusBar().showMessage(f"已定位推荐程序块: {block_id}", 2500)
                return

        self.statusBar().showMessage(f"推荐程序块未出现在当前筛选中: {block_id}", 3000)

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

            output_file_name = self._output_file_name_by_step(step_name)
            step_folder = self._folder_for_step(step_name)
            if output_file_name and step_folder is not None:
                output_path = step_folder / output_file_name
                if output_path.exists() and output_path.is_file():
                    placeholder = self._build_placeholder_widget(
                        f"检测到程序文件已存在，已跳过向导:\n{output_path}"
                    )
                    self._set_top_step_widget(step_name, placeholder)
                    continue

            module_path = chip_dir / file_name
            target_folder = str(step_folder) if step_folder is not None else self.current_target_folder
            load_result = create_visual_widget_from_py(module_path, target_folder)
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
            self._set_file_path_label("路径: (当前步骤无对应输出文件)")
            self._clear_editor_text()
            self.current_edit_file = None
            return

        file_path = folder_path / file_name
        if not file_path.exists() or not file_path.is_file():
            self._set_file_path_label(f"路径: {file_path} (未生成)")
            self._clear_editor_text()
            self.current_edit_file = None
            return

        try:
            content = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            content = file_path.read_text(encoding="gbk", errors="replace")

        self._set_file_path_label(f"路径: {file_path}")
        self._set_editor_text(content, mark_dirty=False)
        self.current_edit_file = file_path
        self._apply_editor_language_by_path(file_path)

    def _refresh_outputs_and_status(self, folder_path: Path):
        step_file_map = {step_name: self._output_file_name_by_step(step_name) for step_name in self.timeline_widget.step_names}
        step_path_map = {}
        for step_name in self.timeline_widget.step_names:
            resolved_folder = self._folder_for_step(step_name, folder_path)
            if resolved_folder is not None:
                step_path_map[step_name] = resolved_folder

        self.timeline_widget.refresh_status_by_step_paths(step_path_map, step_file_map)

        selected_step = self.timeline_widget.step_name(self.timeline_widget.selected_index)
        selected_folder = self._folder_for_step(selected_step, folder_path)
        if selected_folder is None:
            self._set_file_path_label("路径: (未选择目标文件夹)")
            self._clear_editor_text()
            self.current_edit_file = None
            self._refresh_all_block_lists()
            return

        if not selected_folder.exists() or not selected_folder.is_dir():
            self._set_file_path_label(f"路径: {selected_folder} (目录不存在)")
            self._clear_editor_text()
            self.current_edit_file = None
            self._refresh_all_block_lists()
            return

        self._show_step_output_in_right_panel(selected_step, selected_folder)
        self._refresh_all_block_lists()

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
        self.step_target_folders[step_name] = target_folder
        self._save_project_json()
        self._refresh_outputs_and_status(Path(target_folder))
        self.statusBar().showMessage(f"步骤 {step_name} 已完成，已刷新输出", 2500)

    def _init_middle_bottom_pages(self):
        self.bottom_page_meta = {}
        libraries = self.block_library_manager.library_names()
        for index, step_name in enumerate(self.timeline_widget.step_names):
            page = QWidget(self.bottom_stack)
            page_layout = QVBoxLayout(page)
            page_layout.setContentsMargins(8, 8, 8, 8)
            page_layout.setSpacing(8)

            top_row = QWidget(page)
            top_row_layout = QHBoxLayout(top_row)
            top_row_layout.setContentsMargins(0, 0, 0, 0)
            top_row_layout.setSpacing(8)

            title = QLabel(f"预包装程序块 - {step_name}", top_row)
            title.setStyleSheet("font-weight: 600; font-size: 14px;")

            control_panel = QWidget(top_row)
            control_layout = QVBoxLayout(control_panel)
            control_layout.setContentsMargins(0, 0, 0, 0)
            control_layout.setSpacing(6)

            search_input = QLineEdit(control_panel)
            search_input.setPlaceholderText("搜索程序块...")
            search_input.setFixedWidth(260)

            library_combo = QComboBox(control_panel)
            library_combo.setFixedWidth(260)
            library_combo.addItems(libraries)

            control_layout.addWidget(search_input, 0, Qt.AlignmentFlag.AlignRight)
            control_layout.addWidget(library_combo, 0, Qt.AlignmentFlag.AlignRight)

            top_row_layout.addWidget(title)
            top_row_layout.addStretch(1)
            top_row_layout.addWidget(control_panel)

            block_list = QListWidget(page)
            block_list.setObjectName(f"blockList_{step_name}")
            block_list.setMouseTracking(True)
            block_list.viewport().setMouseTracking(True)
            block_list.setProperty("stepName", step_name)

            insert_button = QPushButton("插入所选程序块", page)
            insert_button.setEnabled(False)

            bottom_row = QWidget(page)
            bottom_row_layout = QHBoxLayout(bottom_row)
            bottom_row_layout.setContentsMargins(0, 0, 0, 0)
            bottom_row_layout.setSpacing(8)

            bottom_row_layout.addStretch(1)
            bottom_row_layout.addWidget(insert_button)

            page_layout.addWidget(top_row)
            page_layout.addWidget(block_list, 1)
            page_layout.addWidget(bottom_row)
            page_layout.addStretch(1)

            self.bottom_page_meta[step_name] = {
                "search_input": search_input,
                "library_combo": library_combo,
                "block_list": block_list,
                "insert_button": insert_button,
            }
            self.block_list_viewports[block_list.viewport()] = step_name
            block_list.viewport().installEventFilter(self)

            search_input.textChanged.connect(lambda _, step=step_name: self._refresh_block_list_for_step(step))
            library_combo.currentIndexChanged.connect(lambda _, step=step_name: self._refresh_block_list_for_step(step))
            block_list.itemSelectionChanged.connect(lambda step=step_name: self._on_block_selection_changed(step))
            block_list.itemEntered.connect(lambda item, step=step_name, lst=block_list: self._schedule_block_preview(step, lst, item))
            insert_button.clicked.connect(lambda _, step=step_name: self._insert_selected_block(step))

            self._refresh_block_list_for_step(step_name)

            self.bottom_stack.addWidget(page)

    def _default_insert_target_file(self, step_name: str):
        folder_path = self._folder_for_step(step_name)
        if folder_path is None:
            return None
        file_name = self._output_file_name_by_step(step_name)
        if not file_name:
            return None
        return folder_path / file_name

    def _folder_for_step(self, step_name: str, fallback_folder=None):
        step_folder = self.step_target_folders.get(step_name, "")
        if str(step_folder).strip():
            return Path(step_folder)
        if self.current_target_folder:
            return Path(self.current_target_folder)
        if fallback_folder:
            return Path(fallback_folder)
        return None

    def _step_folders_for_json(self):
        return {
            step_name: str(path)
            for step_name, path in self.step_target_folders.items()
            if step_name in self.timeline_widget.step_names and str(path).strip()
        }

    def _save_project_json(self):
        if self.current_config_json_path is None:
            return

        payload = {}
        if self.current_config_json_path.exists() and self.current_config_json_path.is_file():
            try:
                payload = json.loads(self.current_config_json_path.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                payload = {}

        payload["file_name"] = payload.get("file_name") or self.current_config_json_path.name
        payload["folder"] = self.current_target_folder or payload.get("folder", "")
        payload["controller"] = self.current_controller or payload.get("controller", "")
        payload["chip"] = self.current_chip or payload.get("chip", "")
        payload["step_folders"] = self._step_folders_for_json()
        payload["updated_at"] = datetime.now().isoformat(timespec="seconds")

        try:
            self.current_config_json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError:
            self.statusBar().showMessage("JSON 更新失败", 3000)

    def _refresh_all_block_lists(self):
        for step_name in self.bottom_page_meta.keys():
            self._refresh_block_list_for_step(step_name)

    def _refresh_block_list_for_step(self, step_name: str):
        meta = self.bottom_page_meta.get(step_name)
        if not meta:
            return

        self._hide_block_preview()

        search_input = meta["search_input"]
        library_combo = meta["library_combo"]
        block_list = meta["block_list"]

        query = search_input.text().strip()
        library_name = library_combo.currentText().strip()
        blocks = self.block_library_manager.filter_blocks(query, library_name, step_name)

        block_list.clear()
        for block in blocks:
            block_name = str(block.get("name", block.get("id", "未知程序块")))
            block_library = str(block.get("library", "未分类"))
            language = str(block.get("language", "")).upper()
            item_text = f"{block_name}  [{block_library}]"
            if language:
                item_text += f"  ({language})"
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, str(block.get("id", "")))
            block_list.addItem(item)

        if block_list.count() > 0:
            block_list.setCurrentRow(0)
        self._on_block_selection_changed(step_name)

    def _on_block_selection_changed(self, step_name: str):
        meta = self.bottom_page_meta.get(step_name)
        if not meta:
            return

        block_list = meta["block_list"]
        insert_button = meta["insert_button"]
        insert_button.setEnabled(block_list.currentItem() is not None)

    def _insert_selected_block(self, step_name: str):
        meta = self.bottom_page_meta.get(step_name)
        if not meta:
            return

        block_list = meta["block_list"]
        current_item = block_list.currentItem()
        if current_item is None:
            self.statusBar().showMessage("请先选择一个程序块", 2500)
            return

        block_id = str(current_item.data(Qt.ItemDataRole.UserRole) or "").strip()
        block = self.block_library_manager.get_block(block_id)
        if not block:
            self.statusBar().showMessage("程序块数据无效或不存在", 3000)
            return

        preferred_file = Path(self.current_edit_file) if self.current_edit_file else self._default_insert_target_file(step_name)
        code_template = str(block.get("code_template", ""))
        if not code_template.strip():
            self.statusBar().showMessage("程序块代码为空，未执行插入", 2500)
            return

        active_file = preferred_file
        if active_file is None:
            self.statusBar().showMessage("请先在右侧 IDE 打开目标文件并定位光标", 3000)
            return

        editor_has_active_file = self.current_edit_file is not None and Path(self.current_edit_file) == active_file
        working_text = self.file_content_edit.toPlainText() if editor_has_active_file else ""
        if not editor_has_active_file:
            try:
                if active_file.exists():
                    working_text = active_file.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                working_text = active_file.read_text(encoding="gbk", errors="replace")
            except OSError:
                self.statusBar().showMessage("读取目标文件失败，已停止插入", 3500)
                return

        self._apply_editor_language_by_path(active_file)
        selected_language = self._detect_language_from_file(active_file)

        preview_result = self.block_library_manager.preview_missing_definitions_in_text_for_language(
            block,
            working_text,
            selected_language,
            active_file,
        )
        if not preview_result.get("ok"):
            self.statusBar().showMessage(str(preview_result.get("message", "预览检查失败")), 3000)
            return

        confirm_result = self._confirm_block_insert(
            block,
            active_file,
            preview_result,
            code_template,
            working_text,
            selected_language,
        )
        if not confirm_result:
            self.statusBar().showMessage("已取消插入", 2000)
            return

        insert_draft = confirm_result.get("insert_draft", {}) if isinstance(confirm_result.get("insert_draft", {}), dict) else {}
        code_template = str(insert_draft.get("snippet", ""))
        if not code_template.strip():
            self.statusBar().showMessage("程序块代码为空，未执行插入", 2500)
            return

        requested_insert_pos = self.editor_insert_position

        missing_definitions = list(insert_draft.get("missing_definitions", []))
        region = preview_result.get("region")
        if missing_definitions and region is not None:
            original_text = working_text
            _, end_pos = region
            insertion_line_pos = original_text.rfind("\n", 0, end_pos) + 1
            working_text = self.block_library_manager._insert_declarations_into_region(original_text, region, missing_definitions)
            if insertion_line_pos <= requested_insert_pos:
                requested_insert_pos += len(working_text) - len(original_text)

        self._set_editor_text(working_text, mark_dirty=False)

        cursor = self.file_content_edit.textCursor()
        insert_pos = max(0, min(requested_insert_pos, len(self.file_content_edit.toPlainText())))
        cursor.setPosition(insert_pos)
        snippet = self._apply_cursor_indent_to_snippet(code_template, cursor)
        if snippet and not snippet.endswith("\n"):
            snippet += "\n"
        cursor.insertText(snippet)
        self.file_content_edit.setTextCursor(cursor)
        self.file_content_edit.add_tokens_from_text(snippet)

        self.current_edit_file = active_file

        self._set_file_path_label(f"路径: {active_file}")
        self._apply_editor_language_by_path(active_file)
        self._on_editor_cursor_position_changed()
        self.statusBar().showMessage("程序块已插入到 IDE 指定位置（未自动保存）", 3000)
        return

    def _confirm_block_insert(
        self,
        block,
        active_file: Path,
        preview_result,
        code_template: str,
        working_text: str,
        selected_language: str,
    ):
        dialog = QDialog(self)
        dialog.setWindowTitle("程序块插入预览")
        dialog.setModal(True)
        dialog.resize(860, 700)

        layout = QVBoxLayout(dialog)

        block_name = str(block.get("name", block.get("id", "未知程序块")))
        header = QLabel(f"程序块: {block_name}", dialog)
        target_label = QLabel(f"代码插入文件: {active_file}", dialog)
        cursor_label = QLabel(f"IDE 插入位置: 第 {self.editor_insert_line} 行, 第 {self.editor_insert_column} 列", dialog)

        def_file = preview_result.get("definition_file", "")
        defs_title = QLabel(f"变量定义检查文件: {def_file}", dialog)

        variable_items = block.get("variables", []) if isinstance(block.get("variables", []), list) else []
        variable_names = []
        for item in variable_items:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name", "")).strip()
            if name:
                variable_names.append(name)

        rename_tip = QLabel("变量改名: 直接在下表“新变量名”列中修改", dialog)

        rename_table = QTableWidget(dialog)
        rename_table.setColumnCount(2)
        rename_table.setHorizontalHeaderLabels(["原变量名", "新变量名"])
        rename_table.setRowCount(len(variable_names))
        rename_table.verticalHeader().setVisible(False)
        rename_table.setAlternatingRowColors(True)
        rename_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        rename_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        rename_table.horizontalHeader().setStretchLastSection(True)
        rename_table.setMaximumHeight(190)

        for row, name in enumerate(variable_names):
            old_item = QTableWidgetItem(name)
            old_item.setFlags(old_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            rename_table.setItem(row, 0, old_item)
            new_name_editor = QLineEdit(name, rename_table)
            new_name_editor.textChanged.connect(lambda _text, _row=row: refresh_preview_texts())
            rename_table.setCellWidget(row, 1, new_name_editor)

        defs_editor = QPlainTextEdit(dialog)
        defs_editor.setReadOnly(True)
        defs_editor.setMaximumHeight(140)

        code_title = QLabel("即将插入的程序块代码:", dialog)
        code_editor = QPlainTextEdit(dialog)
        code_editor.setReadOnly(True)
        state = {
            "insert_draft": {
                "snippet": code_template,
                "missing_definitions": list(preview_result.get("missing_definitions", [])),
            },
            "valid": True,
        }
        ok_button = None

        def build_rename_map():
            rename_map = {}
            for row, old_name in enumerate(variable_names):
                new_editor = rename_table.cellWidget(row, 1)
                new_name = ""
                if isinstance(new_editor, QLineEdit):
                    new_name = new_editor.text().strip()
                rename_map[old_name] = new_name or old_name
            return rename_map

        def refresh_preview_texts():
            rename_map = build_rename_map()

            remapped_variables = []
            for item in variable_items:
                if not isinstance(item, dict):
                    continue
                mapped_item = dict(item)
                old_name = str(item.get("name", "")).strip()
                if old_name:
                    mapped_item["name"] = rename_map.get(old_name, old_name)
                if str(mapped_item.get("definition", "")).strip():
                    mapped_item["definition"] = self._apply_variable_renames(str(mapped_item.get("definition", "")), rename_map)
                if str(mapped_item.get("declaration", "")).strip():
                    mapped_item["declaration"] = self._apply_variable_renames(str(mapped_item.get("declaration", "")), rename_map)
                remapped_variables.append(mapped_item)

            remapped_block = dict(block)
            remapped_block["variables"] = remapped_variables

            recheck = self.block_library_manager.preview_missing_definitions_in_text_for_language(
                remapped_block,
                working_text,
                selected_language,
                active_file,
            )

            draft = state["insert_draft"]
            draft["snippet"] = self._apply_variable_renames(code_template, rename_map)
            if recheck.get("ok"):
                draft["missing_definitions"] = list(recheck.get("missing_definitions", []))
                state["valid"] = True
            else:
                draft["missing_definitions"] = []
                state["valid"] = False

            code_editor.setPlainText(str(draft.get("snippet", "")))
            missing_defs = list(draft.get("missing_definitions", []))
            if missing_defs:
                defs_editor.setPlainText("\n".join(missing_defs))
            elif state.get("valid", True):
                defs_editor.setPlainText("(无缺失变量定义)")
            else:
                defs_editor.setPlainText(str(recheck.get("message", "声明区检查失败")))
            if ok_button is not None:
                ok_button.setEnabled(bool(state.get("valid", True)))

        refresh_preview_texts()

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            Qt.Orientation.Horizontal,
            dialog,
        )
        ok_button = button_box.button(QDialogButtonBox.StandardButton.Ok)
        if ok_button is not None:
            ok_button.setText("确认插入")
        cancel_button = button_box.button(QDialogButtonBox.StandardButton.Cancel)
        if cancel_button is not None:
            cancel_button.setText("取消")

        def on_accept_clicked():
            rename_table.clearFocus()
            dialog.setFocus()
            refresh_preview_texts()
            if not state.get("valid", True):
                return
            dialog.accept()

        button_box.accepted.connect(on_accept_clicked)
        button_box.rejected.connect(dialog.reject)

        layout.addWidget(header)
        layout.addWidget(target_label)
        layout.addWidget(cursor_label)
        layout.addSpacing(4)
        layout.addWidget(rename_tip)
        layout.addWidget(rename_table)
        layout.addWidget(defs_title)
        layout.addWidget(defs_editor)
        layout.addWidget(code_title)
        layout.addWidget(code_editor, 1)
        layout.addWidget(button_box)

        refresh_preview_texts()

        if dialog.exec() != int(QDialog.DialogCode.Accepted):
            return None
        return {
            "insert_draft": state.get("insert_draft", {"snippet": code_template, "missing_definitions": []}),
        }

    def _apply_variable_renames(self, text: str, rename_map: dict[str, str]):
        result = text or ""
        if not rename_map:
            return result

        # Replace longer names first to avoid partial overlaps when identifiers share prefixes.
        ordered_names = sorted(rename_map.keys(), key=len, reverse=True)
        for old_name in ordered_names:
            new_name = str(rename_map.get(old_name, old_name)).strip() or old_name
            if old_name == new_name:
                continue
            result = re.sub(rf"\b{re.escape(old_name)}\b", new_name, result)
        return result

    def _apply_cursor_indent_to_snippet(self, snippet: str, cursor):
        text = snippet or ""
        if not text:
            return text

        line_prefix = cursor.block().text()[: cursor.positionInBlock()]
        indent_match = re.match(r"[ \t]*", line_prefix)
        indent = indent_match.group(0) if indent_match is not None else ""
        if not indent:
            return text

        has_trailing_newline = text.endswith("\n")
        lines = text.splitlines()
        if not lines:
            return text

        indented_text = "\n".join(f"{indent}{line}" for line in lines)
        if has_trailing_newline:
            indented_text += "\n"
        return indented_text

    def _switch_middle_pages(self, index):
        if not self.timeline_widget.step_names:
            return

        if index < 0 or index >= len(self.timeline_widget.step_names):
            index = 0

        self._hide_block_preview()
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
        self.step_target_folders = {}

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
            "step_folders": self._step_folders_for_json(),
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }

        try:
            # JSON file is created only after user confirms in the dialog.
            output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError:
            self.statusBar().showMessage("JSON 文件写入失败", 3500)
            return

        self.current_config_json_path = output_path

        # Reset timeline state for a newly created file.
        self.timeline_widget.reset_after_file_created()
        self._reload_top_visual_pages()
        self._switch_middle_pages(self.timeline_widget.selected_index)

        self._set_file_path_label(f"路径: {output_path}")
        self._set_editor_text(
            "\n".join(
                [
                    "# 已生成 JSON 配置",
                    f"json={output_path}",
                    f"file_name={file_name}",
                    f"controller={controller}",
                    f"chip={chip}",
                    f"folder={folder_path}",
                ]
            ),
            mark_dirty=False,
        )
        self.current_edit_file = output_path
        self._apply_editor_language_by_path(output_path)
        self._refresh_outputs_and_status(folder_path)
        self._refresh_all_block_lists()
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

        self._set_file_path_label(f"路径: {file_path}")
        self._set_editor_text(content, mark_dirty=False)
        self.current_edit_file = Path(file_path)
        self._apply_editor_language_by_path(Path(file_path))
        self.current_config_json_path = None
        self.step_target_folders = {}

        selected_folder = Path(file_path).parent
        if Path(file_path).suffix.lower() == ".json":
            try:
                payload = json.loads(content)
                folder = payload.get("folder", "")
                controller = payload.get("controller", "")
                chip = payload.get("chip", "")
                step_folders = payload.get("step_folders", {})

                if folder:
                    selected_folder = Path(folder)
                    self.current_target_folder = folder
                if controller:
                    self.current_controller = controller
                if chip:
                    self.current_chip = chip
                if isinstance(step_folders, dict):
                    self.step_target_folders = {
                        step_name: str(path)
                        for step_name, path in step_folders.items()
                        if step_name in self.timeline_widget.step_names and str(path).strip()
                    }
                if controller or chip:
                    self._reload_top_visual_pages()
                self.current_config_json_path = Path(file_path)
            except json.JSONDecodeError:
                pass

        self._refresh_outputs_and_status(selected_folder)
        self._refresh_all_block_lists()
        self.statusBar().showMessage("文件读取成功", 2000)

    def on_dot_selected(self, index):
        if index != self._active_step_index:
            if not self._prompt_save_if_dirty("切换步骤"):
                if 0 <= self._active_step_index < len(self.timeline_widget.step_names):
                    self.timeline_widget.selected_index = self._active_step_index
                    self.timeline_widget.update()
                return

        step_name = self.timeline_widget.step_name(index)
        self._switch_middle_pages(index)
        selected_folder = self._folder_for_step(step_name)
        if selected_folder is not None:
            self._show_step_output_in_right_panel(step_name, selected_folder)
        else:
            self._set_file_path_label("路径: (未选择目标文件夹)")
            self._clear_editor_text()
            self.current_edit_file = None
        self._active_step_index = index
        self.statusBar().showMessage(f"已选中步骤: {step_name}", 2000)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_assistant_fab_position()

    def closeEvent(self, event):
        if not self._prompt_save_if_dirty("退出"):
            event.ignore()
            return
        event.accept()

from __future__ import annotations

import keyword
import re
from pathlib import Path

from PyQt6.QtCore import QRect, QRegularExpression, QSize, QStringListModel, Qt
from PyQt6.QtGui import (
    QColor,
    QFont,
    QKeyEvent,
    QPainter,
    QSyntaxHighlighter,
    QTextCharFormat,
    QTextCursor,
    QTextFormat,
)
from PyQt6.QtWidgets import QCompleter, QPlainTextEdit, QTextEdit, QWidget


class _LineNumberArea(QWidget):
    def __init__(self, editor: "CodeEditor"):
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self):
        return QSize(self.editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self.editor.paint_line_number_area(event)


class _KeywordHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)
        self._language_name = "C++"
        self._theme_name = "light"
        self._keyword_patterns = []

        self._keyword_format = QTextCharFormat()
        self._string_format = QTextCharFormat()
        self._comment_format = QTextCharFormat()
        self._number_format = QTextCharFormat()

        self._number_pattern = QRegularExpression(r"\b\d+(?:\.\d+)?\b")
        self._double_quote_string = QRegularExpression(r'"[^"\\]*(?:\\.[^"\\]*)*"')
        self._single_quote_string = QRegularExpression(r"'[^'\\]*(?:\\.[^'\\]*)*'")

        self._refresh_language_patterns()
        self.set_theme("light")

    def set_theme(self, theme_name: str):
        self._theme_name = "dark" if theme_name == "dark" else "light"
        if self._theme_name == "dark":
            keyword_color = QColor("#4fc1ff")
            string_color = QColor("#ce9178")
            comment_color = QColor("#6a9955")
            number_color = QColor("#b5cea8")
        else:
            keyword_color = QColor("#005cc5")
            string_color = QColor("#a31515")
            comment_color = QColor("#22863a")
            number_color = QColor("#116329")

        self._keyword_format.setForeground(keyword_color)
        self._keyword_format.setFontWeight(QFont.Weight.Bold)

        self._string_format.setForeground(string_color)
        self._comment_format.setForeground(comment_color)
        self._number_format.setForeground(number_color)

        self.rehighlight()

    def set_language(self, language_name: str):
        self._language_name = language_name if language_name in {"C", "C++", "Python"} else "C++"
        self._refresh_language_patterns()
        self.rehighlight()

    def _refresh_language_patterns(self):
        keyword_sets = {
            "C": CodeEditor.C_KEYWORDS,
            "C++": CodeEditor.C_KEYWORDS | CodeEditor.CPP_KEYWORDS,
            "Python": set(keyword.kwlist),
        }
        keywords = keyword_sets.get(self._language_name, CodeEditor.C_KEYWORDS | CodeEditor.CPP_KEYWORDS)
        self._keyword_patterns = [QRegularExpression(rf"\b{re.escape(item)}\b") for item in sorted(keywords)]

    def highlightBlock(self, text: str):
        for pattern in self._keyword_patterns:
            iterator = pattern.globalMatch(text)
            while iterator.hasNext():
                match = iterator.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), self._keyword_format)

        for pattern in (self._double_quote_string, self._single_quote_string):
            iterator = pattern.globalMatch(text)
            while iterator.hasNext():
                match = iterator.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), self._string_format)

        if self._language_name == "Python":
            comment_pattern = QRegularExpression(r"#.*$")
        else:
            comment_pattern = QRegularExpression(r"//.*$")

        comment_match = comment_pattern.match(text)
        if comment_match.hasMatch():
            self.setFormat(comment_match.capturedStart(), comment_match.capturedLength(), self._comment_format)

        number_iterator = self._number_pattern.globalMatch(text)
        while number_iterator.hasNext():
            number_match = number_iterator.next()
            self.setFormat(number_match.capturedStart(), number_match.capturedLength(), self._number_format)


class CodeEditor(QPlainTextEdit):
    C_KEYWORDS = {
        "auto", "break", "case", "char", "const", "continue", "default", "do", "double", "else", "enum",
        "extern", "float", "for", "goto", "if", "inline", "int", "long", "register", "restrict", "return",
        "short", "signed", "sizeof", "static", "struct", "switch", "typedef", "union", "unsigned", "void", "volatile", "while",
    }

    CPP_KEYWORDS = {
        "class", "namespace", "template", "typename", "public", "private", "protected", "virtual", "override", "final",
        "constexpr", "nullptr", "new", "delete", "try", "catch", "throw", "using", "std", "string", "vector", "map",
        "include", "define", "ifdef", "ifndef", "endif", "pragma",
    }

    IDENTIFIER_PATTERN = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]{2,}\b")

    def __init__(self, project_root: Path, parent=None):
        super().__init__(parent)
        self.project_root = project_root
        self._theme_name = "light"
        self._language_name = "C++"
        self._line_number_bg = QColor("#eef2f6")
        self._line_number_fg = QColor("#6b7280")
        self._current_line_bg = QColor("#e9f2ff")

        self._line_number_area = _LineNumberArea(self)
        self._highlighter = _KeywordHighlighter(self.document())
        self._completion_words = set()
        self._workspace_words = set()
        self._dynamic_words = set()
        self._completer = QCompleter(self)
        self._completer_model = QStringListModel(self)
        self._completer.setModel(self._completer_model)
        self._completer.setWidget(self)
        self._completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self._completer.activated.connect(self.insert_completion)

        self._setup_editor_style()
        self._setup_line_numbers()
        self._build_completion_dictionary()
        self.set_language("C++")

    def _setup_editor_style(self):
        font = QFont("Consolas", 10)
        if not font.exactMatch():
            font = QFont("Courier New", 10)
        self.setFont(font)

        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.setTabStopDistance(4 * self.fontMetrics().horizontalAdvance(" "))
        self.setPlaceholderText("在此编辑代码... 支持 C/C++/Python 自动补全（Ctrl+Space）")

        self.set_theme("light")

    def set_theme(self, theme_name: str):
        self._theme_name = "dark" if theme_name == "dark" else "light"

        if self._theme_name == "dark":
            editor_bg = "#1e1e1e"
            editor_fg = "#d4d4d4"
            border = "#2d2d30"
            selection_bg = "#264f78"
            selection_fg = "#ffffff"
            scrollbar_bg = "#252526"
            completer_bg = "#252526"
            completer_fg = "#d4d4d4"
            completer_sel_bg = "#2f81f7"
            completer_sel_fg = "#ffffff"
            self._line_number_bg = QColor("#252526")
            self._line_number_fg = QColor("#858585")
            self._current_line_bg = QColor("#2a2d2e")
        else:
            editor_bg = "#ffffff"
            editor_fg = "#1f2328"
            border = "#d0d7de"
            selection_bg = "#cce5ff"
            selection_fg = "#0f172a"
            scrollbar_bg = "#f3f5f7"
            completer_bg = "#ffffff"
            completer_fg = "#1f2328"
            completer_sel_bg = "#2f81f7"
            completer_sel_fg = "#ffffff"
            self._line_number_bg = QColor("#eef2f6")
            self._line_number_fg = QColor("#6b7280")
            self._current_line_bg = QColor("#e9f2ff")

        self.setStyleSheet(
            f"""
            QPlainTextEdit {{
                background-color: {editor_bg};
                color: {editor_fg};
                border: 1px solid {border};
                selection-background-color: {selection_bg};
                selection-color: {selection_fg};
            }}
            QScrollBar:vertical, QScrollBar:horizontal {{
                background: {scrollbar_bg};
            }}
            """
        )

        self._completer.popup().setStyleSheet(
            f"""
            QListView {{
                background-color: {completer_bg};
                color: {completer_fg};
                border: 1px solid {border};
            }}
            QListView::item:selected {{
                background-color: {completer_sel_bg};
                color: {completer_sel_fg};
            }}
            """
        )

        self._highlighter.set_theme(self._theme_name)
        self.highlight_current_line()
        self._line_number_area.update()

    def _setup_line_numbers(self):
        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.cursorPositionChanged.connect(self.highlight_current_line)
        self.update_line_number_area_width(0)
        self.highlight_current_line()

    def _build_completion_dictionary(self):
        self._workspace_words = self._scan_workspace_identifiers()
        self._refresh_completion_dictionary()

    def _language_keywords(self):
        if self._language_name == "Python":
            return set(keyword.kwlist)
        if self._language_name == "C":
            return set(self.C_KEYWORDS)
        return set(self.C_KEYWORDS | self.CPP_KEYWORDS)

    def _refresh_completion_dictionary(self):
        words = set(self._workspace_words)
        words.update(self._dynamic_words)
        words.update(self._language_keywords())
        self._completion_words = words
        self._completer_model.setStringList(sorted(self._completion_words))

    def set_language(self, language_name: str):
        self._language_name = language_name if language_name in {"C", "C++", "Python"} else "C++"
        self._highlighter.set_language(self._language_name)
        self._refresh_completion_dictionary()

    def current_language(self):
        return self._language_name

    def _scan_workspace_identifiers(self):
        words = set()
        scan_patterns = ["src/**/*.py", "src/**/*.[ch]", "src/**/*.[ch]pp", "v2/**/*.py"]
        max_files = 300
        scanned = 0

        for pattern in scan_patterns:
            for file_path in self.project_root.glob(pattern):
                if not file_path.is_file():
                    continue
                if scanned >= max_files:
                    return words
                scanned += 1
                try:
                    content = file_path.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    content = file_path.read_text(encoding="gbk", errors="ignore")
                except OSError:
                    continue

                words.update(self.IDENTIFIER_PATTERN.findall(content))

        return words

    def add_tokens_from_text(self, text: str):
        words = set(self.IDENTIFIER_PATTERN.findall(text or ""))
        if not words:
            return

        if words.issubset(self._dynamic_words):
            return

        self._dynamic_words.update(words)
        self._refresh_completion_dictionary()

    def line_number_area_width(self):
        digits = len(str(max(1, self.blockCount())))
        return 16 + self.fontMetrics().horizontalAdvance("9") * digits

    def update_line_number_area_width(self, _):
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def update_line_number_area(self, rect, dy):
        if dy:
            self._line_number_area.scroll(0, dy)
        else:
            self._line_number_area.update(0, rect.y(), self._line_number_area.width(), rect.height())

        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self._line_number_area.setGeometry(QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height()))

    def paint_line_number_area(self, event):
        painter = QPainter(self._line_number_area)
        painter.fillRect(event.rect(), self._line_number_bg)

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = round(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + round(self.blockBoundingRect(block).height())

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                painter.setPen(self._line_number_fg)
                painter.drawText(0, top, self._line_number_area.width() - 6, self.fontMetrics().height(), Qt.AlignmentFlag.AlignRight, number)

            block = block.next()
            top = bottom
            bottom = top + round(self.blockBoundingRect(block).height())
            block_number += 1

    def highlight_current_line(self):
        extra_selections = []
        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()
            selection.format.setBackground(self._current_line_bg)
            selection.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extra_selections.append(selection)
        self.setExtraSelections(extra_selections)

    def insert_completion(self, completion):
        text_cursor = self.textCursor()
        text_cursor.select(QTextCursor.SelectionType.WordUnderCursor)
        text_cursor.insertText(completion)
        self.setTextCursor(text_cursor)

    def _text_under_cursor(self):
        text_cursor = self.textCursor()
        text_cursor.select(QTextCursor.SelectionType.WordUnderCursor)
        return text_cursor.selectedText()

    def keyPressEvent(self, event: QKeyEvent):
        if self._completer.popup().isVisible():
            popup = self._completer.popup()
            model = popup.model()

            if event.key() in {
                Qt.Key.Key_Up,
                Qt.Key.Key_Down,
                Qt.Key.Key_PageUp,
                Qt.Key.Key_PageDown,
            }:
                current_row = popup.currentIndex().row()
                if current_row < 0:
                    current_row = 0

                step = 1
                if event.key() == Qt.Key.Key_Up:
                    target_row = max(0, current_row - step)
                elif event.key() == Qt.Key.Key_Down:
                    target_row = min(model.rowCount() - 1, current_row + step)
                elif event.key() == Qt.Key.Key_PageUp:
                    target_row = max(0, current_row - 8)
                else:
                    target_row = min(model.rowCount() - 1, current_row + 8)

                popup.setCurrentIndex(model.index(target_row, 0))
                event.accept()
                return

            if event.key() in {Qt.Key.Key_Tab, Qt.Key.Key_Backtab}:
                popup_index = popup.currentIndex()
                completion = popup_index.data() if popup_index.isValid() else self._completer.currentCompletion()
                if completion:
                    self.insert_completion(str(completion))
                popup.hide()
                event.accept()
                return

            if event.key() in {
                Qt.Key.Key_Enter,
                Qt.Key.Key_Return,
                Qt.Key.Key_Escape,
            }:
                event.ignore()
                return

        is_shortcut = event.modifiers() == Qt.KeyboardModifier.ControlModifier and event.key() == Qt.Key.Key_Space
        if not is_shortcut:
            super().keyPressEvent(event)

        ctrl_or_shift = event.modifiers() & (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier)
        if ctrl_or_shift and not is_shortcut:
            return

        prefix = self._text_under_cursor()
        if not is_shortcut:
            if len(prefix) < 2:
                self._completer.popup().hide()
                return
            if event.text() and not (event.text().isalnum() or event.text() == "_"):
                self._completer.popup().hide()
                return

        if prefix.casefold() != self._completer.completionPrefix().casefold():
            self._completer.setCompletionPrefix(prefix)
            self._completer.popup().setCurrentIndex(self._completer.completionModel().index(0, 0))

        cursor_rect = self.cursorRect()
        cursor_rect.setWidth(self._completer.popup().sizeHintForColumn(0) + self._completer.popup().verticalScrollBar().sizeHint().width())
        self._completion_prefix = prefix
        self._completer.complete(cursor_rect)

from __future__ import annotations

from pathlib import Path
import importlib.util

from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget, QWizard


class UiLoadResult:
    def __init__(self, widget: QWidget, message: str = ""):
        self.widget = widget
        self.message = message


def _error_widget(text: str) -> QWidget:
    panel = QWidget()
    layout = QVBoxLayout(panel)
    label = QLabel(text, panel)
    label.setWordWrap(True)
    layout.addWidget(label)
    layout.addStretch(1)
    return panel


def _load_module(module_path: Path):
    unique_name = f"v2_dynamic_{module_path.stem}_{abs(hash(str(module_path)))}"
    spec = importlib.util.spec_from_file_location(unique_name, str(module_path))
    if spec is None or spec.loader is None:
        raise ImportError(f"无法创建模块加载器: {module_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _try_set_target_folder(widget: QWidget, target_folder: str):
    if not target_folder:
        return

    folder_input = getattr(widget, "folder_input", None)
    if folder_input is not None and hasattr(folder_input, "setText"):
        folder_input.setText(target_folder)


def _configure_embedded_wizard(wizard: QWizard):
    wizard.setOption(QWizard.WizardOption.NoCancelButton, True)

    cancel_button = wizard.button(QWizard.WizardButton.CancelButton)
    if cancel_button is not None:
        cancel_button.setEnabled(False)
        cancel_button.hide()

    wizard.reject = lambda: None


def create_visual_widget_from_py(module_path: Path, target_folder: str = "") -> UiLoadResult:
    if not module_path.exists() or not module_path.is_file():
        return UiLoadResult(_error_widget(f"文件不存在: {module_path}"), "文件不存在")

    try:
        module = _load_module(module_path)
    except Exception as exc:
        return UiLoadResult(_error_widget(f"加载失败: {module_path}\n\n{exc}"), f"加载失败: {exc}")

    wizard_cls = getattr(module, "ConfigWizard", None)
    if wizard_cls is not None:
        try:
            wizard = wizard_cls()
            if isinstance(wizard, QWizard):
                _configure_embedded_wizard(wizard)
                first_page = wizard.page(0)
                _try_set_target_folder(first_page, target_folder)
                return UiLoadResult(wizard)
        except Exception as exc:
            return UiLoadResult(_error_widget(f"创建 ConfigWizard 失败: {module_path}\n\n{exc}"), f"ConfigWizard 创建失败: {exc}")

    for attr_name in dir(module):
        attr = getattr(module, attr_name)
        if not isinstance(attr, type):
            continue
        if not issubclass(attr, QWidget):
            continue
        if attr is QWidget:
            continue

        try:
            widget = attr()
            return UiLoadResult(widget)
        except Exception:
            continue

    return UiLoadResult(_error_widget(f"未找到可视化 QWidget/ConfigWizard: {module_path}"), "无可视化类")

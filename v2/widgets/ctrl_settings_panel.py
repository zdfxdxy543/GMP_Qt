from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QToolButton,
    QVBoxLayout,
    QWidget,
)


class CollapsibleBlock(QWidget):
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self._button = QToolButton(self)
        self._button.setText(title)
        self._button.setCheckable(True)
        self._button.setChecked(False)
        self._button.setArrowType(Qt.ArrowType.RightArrow)
        self._button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self._button.clicked.connect(self._on_toggle)

        self.body = QGroupBox(self)
        self.body.setVisible(False)
        self.body_layout = QVBoxLayout(self.body)
        self.body_layout.setContentsMargins(10, 8, 10, 8)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(6)
        root.addWidget(self._button)
        root.addWidget(self.body)

    def _on_toggle(self, checked: bool):
        self._button.setArrowType(Qt.ArrowType.DownArrow if checked else Qt.ArrowType.RightArrow)
        self.body.setVisible(checked)

    def set_expanded(self, expanded: bool):
        self._button.setChecked(expanded)
        self._on_toggle(expanded)


class CtrlSettingsPanel(QWidget):
    """Rewritten ctrl_settings visual panel with collapsible step groups."""

    def __init__(self, controller: str, chip: str, target_folder: str = "", parent=None):
        super().__init__(parent)
        self.controller = controller
        self.chip = chip

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        root.addWidget(scroll, 1)

        content = QWidget(scroll)
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(8)

        self.target_block = self._build_target_folder_block()
        self.debug_block = self._build_debug_block()
        self.basic_block = self._build_basic_block()
        self.hardware_block = self._build_hardware_block()
        self.encoder_block = self._build_encoder_block()
        self.base_block = self._build_ctrl_base_block()
        self.ctrl_type_block = self._build_ctrl_type_block()

        content_layout.addWidget(self.target_block)
        content_layout.addWidget(self.debug_block)

        if chip == "stm32g431":
            self.board_pin_block = self._build_board_pin_block()
            content_layout.addWidget(self.board_pin_block)
        else:
            self.board_pin_block = None

        content_layout.addWidget(self.basic_block)
        content_layout.addWidget(self.hardware_block)
        content_layout.addWidget(self.encoder_block)
        content_layout.addWidget(self.base_block)
        content_layout.addWidget(self.ctrl_type_block)
        content_layout.addStretch(1)

        scroll.setWidget(content)

        self.set_target_folder(target_folder)
        self.target_block.set_expanded(True)

    def set_target_folder(self, folder: str):
        self.target_folder_edit.setText(folder or "")

    def _create_path_row(self, line_edit: QLineEdit, browse_slot):
        row_widget = QWidget(self)
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(6)
        row_layout.addWidget(line_edit, 1)

        browse_btn = QPushButton("浏览", row_widget)
        browse_btn.clicked.connect(browse_slot)
        row_layout.addWidget(browse_btn)
        return row_widget

    def _browse_target_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "选择目标文件夹", self.target_folder_edit.text().strip())
        if folder:
            self.target_folder_edit.setText(folder)

    def _browse_motor_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择电机参数文件",
            self.motor_file_edit.text().strip(),
            "头文件 (*.h);;所有文件 (*.*)",
        )
        if file_path:
            self.motor_file_edit.setText(file_path)

    def _browse_ctrl_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择控制器参数文件",
            self.ctrl_file_edit.text().strip(),
            "头文件 (*.h);;所有文件 (*.*)",
        )
        if file_path:
            self.ctrl_file_edit.setText(file_path)

    def generate_output_file(self, target_folder: str):
        folder = Path(target_folder)
        folder.mkdir(parents=True, exist_ok=True)

        data = {
            "build_level": self.debug_level_edit.text().strip() or "1",
            "ctrl_start_delay": self.start_delay_edit.text().strip() or "1000",
            "ctrl_freq": self.ctrl_freq_edit.text().strip() or "20e3",
            "pwm_depth": self.pwm_depth_edit.text().strip() or "2499",
            "pwm_deadband": self.pwm_deadband_edit.text().strip() or "10",
            "system_tick": self.tick_edit.text().strip() or "1000000",
            "ctrl_adc_ref": self.adc_ref_edit.text().strip() or "3.3",
            "motor_file": self.motor_file_edit.text().strip(),
            "ctrl_file": self.ctrl_file_edit.text().strip(),
            "use_default": self.use_default_box.isChecked(),
            "encoder_full": self.encoder_full_edit.text().strip() or "4096",
            "encoder_bias": self.encoder_bias_edit.text().strip() or "2048",
            "speed_div": self.speed_div_edit.text().strip() or "1000",
            "position_div": self.position_div_edit.text().strip() or "1000",
            "dc_bus": self.dc_bus_edit.text().strip() or "12.0",
            "base_current": self.base_current_edit.text().strip() or "10.0",
            "base_speed": self.base_speed_edit.text().strip() or "3000",
            "ctrl_type": "FOC" if self.type_foc.isChecked() else ("V/F" if self.type_vf.isChecked() else "SPEED"),
        }

        lines = [
            "#ifndef CTRL_SETTINGS_H",
            "#define CTRL_SETTINGS_H",
            "",
            f"#define BUILD_LEVEL ({data['build_level']})",
            f"//========================================================================================\n// Controller basic parameters\n",
            f"// Startup Delay, ms\n#define CTRL_STARTUP_DELAY ({data['ctrl_start_delay']})\n",
            f"// Controller Frequency\n#define CONTROLLER_FREQUENCY ({data['ctrl_freq']})\n",
            f"// PWM Depth\n#define CTRL_PWM_CMP_MAX ({data['pwm_depth']})\n",
            f"// PWM Deadband\n#define CTRL_PWM_DEADBAND_CMP ({data['pwm_deadband']})\n",
            f"// System tick\n#define DSP_C2000_DSP_TIME_DIV ({data['system_tick']})\n",
            f"// ADC_Voltage Reference\n#define CTRL_ADC_VOLTAGE_REF ({data['ctrl_adc_ref']})\n",
            f"//========================================================================================\n// Encoder parameters\n",
            f"// Encoder Full Scale\n#define CTRL_POS_ENC_FS ({data['encoder_full']})\n",
            f"// Encoder Bias\n#define CTRL_POS_ENC_BIAS ({data['encoder_bias']})\n",
            f"// Speed Division\n#define CTRL_SPEED_DIV ({data['speed_div']})\n",
            f"// Position Division\n#define CTRL_POS_DIV ({data['position_div']})\n",
            f"//========================================================================================\n// Controller base parameters\n",
            f"// DC Bus Voltage\n#define CTRL_DCBUS_VOLTAGE ({data['dc_bus']})\n",
            f"// Phase Voltage\n#define CTRL_VOLTAGE_BASE ({data['']})\n",
            f"// Current Base\n#define CTRL_CURRENT_BASE ({float(data['dc_bus']) / 1.732 / float(data['base_current'])})\n",
            f"// Base Current\n#define CTRL_BASE_CURRENT ({data['base_current']})\n",
            f"// Base Speed\n#define CTRL_BASE_SPEED ({data['base_speed']})\n",
            f"#define CTRL_TYPE_{data['ctrl_type'].replace('/', '_')} 1",
            f"#define CTRL_USE_DEFAULT_HW ({1 if data['use_default'] else 0})",
        ]

        if data["motor_file"]:
            lines.append(f"#define MOTOR_PARAM_FILE \"{data['motor_file']}\"")
        if data["ctrl_file"]:
            lines.append(f"#define CTRL_PARAM_FILE \"{data['ctrl_file']}\"")

        lines.extend(["", "#endif // CTRL_SETTINGS_H", ""])

        output_path = folder / "ctrl_settings.h"
        output_path.write_text("\n".join(lines), encoding="utf-8")
        return str(output_path)

    def _build_target_folder_block(self):
        block = CollapsibleBlock("步骤 1：目标文件夹", self)
        form = QFormLayout()
        self.target_folder_edit = QLineEdit(block.body)
        self.target_folder_edit.setPlaceholderText("来自新建文件选择的目标路径")
        form.addRow("目标文件夹", self._create_path_row(self.target_folder_edit, self._browse_target_folder))
        block.body_layout.addLayout(form)
        return block

    def _build_debug_block(self):
        block = CollapsibleBlock("步骤 2：调试选项", self)
        form = QFormLayout()
        self.debug_level_edit = QLineEdit(block.body)
        self.debug_level_edit.setPlaceholderText("例如 1~6")
        form.addRow("BUILD_LEVEL", self.debug_level_edit)

        hint = QLabel(
            "1: hardware validate, 2: current loop, 3: actual angle, 4: speed, 5: position, 6: communication",
            block.body,
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #9aa4b2;")
        block.body_layout.addLayout(form)
        block.body_layout.addWidget(hint)
        return block

    def _build_board_pin_block(self):
        block = CollapsibleBlock("步骤 3：板级引脚（STM32）", self)
        form = QFormLayout()
        self.pwm_pin_edit = QLineEdit(block.body)
        self.adc_pin_edit = QLineEdit(block.body)
        self.encoder_pin_edit = QLineEdit(block.body)
        form.addRow("PWM 引脚组", self.pwm_pin_edit)
        form.addRow("ADC 引脚组", self.adc_pin_edit)
        form.addRow("编码器引脚组", self.encoder_pin_edit)
        block.body_layout.addLayout(form)
        return block

    def _build_basic_block(self):
        block = CollapsibleBlock("步骤 4：控制器基本参数", self)
        form = QFormLayout()
        self.start_delay_edit = QLineEdit(block.body)
        self.ctrl_freq_edit = QLineEdit(block.body)
        self.pwm_depth_edit = QLineEdit(block.body)
        self.pwm_deadband_edit = QLineEdit(block.body)
        self.tick_edit = QLineEdit(block.body)
        self.adc_ref_edit = QLineEdit(block.body)

        self.start_delay_edit.setPlaceholderText("1000")
        self.ctrl_freq_edit.setPlaceholderText("20e3")
        self.pwm_depth_edit.setPlaceholderText("2499")
        self.pwm_deadband_edit.setPlaceholderText("10")
        self.tick_edit.setPlaceholderText("1000000")
        self.adc_ref_edit.setPlaceholderText("3.3")

        form.addRow("启动延时(ms)", self.start_delay_edit)
        form.addRow("控制频率(Hz)", self.ctrl_freq_edit)
        form.addRow("PWM最大比较值", self.pwm_depth_edit)
        form.addRow("PWM死区", self.pwm_deadband_edit)
        form.addRow("系统时钟周期(ns)", self.tick_edit)
        form.addRow("ADC参考电压(V)", self.adc_ref_edit)
        block.body_layout.addLayout(form)
        return block

    def _build_hardware_block(self):
        block = CollapsibleBlock("步骤 5：硬件参数", self)
        form = QFormLayout()
        self.motor_file_edit = QLineEdit(block.body)
        self.ctrl_file_edit = QLineEdit(block.body)
        self.use_default_box = QCheckBox("使用默认参数", block.body)
        self.use_default_box.setChecked(True)

        self.motor_file_edit.setPlaceholderText("电机参数文件路径")
        self.ctrl_file_edit.setPlaceholderText("控制器参数文件路径")

        form.addRow("电机参数文件", self._create_path_row(self.motor_file_edit, self._browse_motor_file))
        form.addRow("控制器参数文件", self._create_path_row(self.ctrl_file_edit, self._browse_ctrl_file))
        block.body_layout.addLayout(form)
        block.body_layout.addWidget(self.use_default_box)
        return block

    def _build_encoder_block(self):
        block = CollapsibleBlock("步骤 6：编码器参数", self)
        form = QFormLayout()
        self.encoder_full_edit = QLineEdit(block.body)
        self.encoder_bias_edit = QLineEdit(block.body)
        self.speed_div_edit = QLineEdit(block.body)
        self.position_div_edit = QLineEdit(block.body)

        self.encoder_full_edit.setPlaceholderText("4096")
        self.encoder_bias_edit.setPlaceholderText("2048")
        self.speed_div_edit.setPlaceholderText("1000")
        self.position_div_edit.setPlaceholderText("1000")

        form.addRow("满量程", self.encoder_full_edit)
        form.addRow("偏置", self.encoder_bias_edit)
        form.addRow("速度划分", self.speed_div_edit)
        form.addRow("位置划分", self.position_div_edit)
        block.body_layout.addLayout(form)
        return block

    def _build_ctrl_base_block(self):
        block = CollapsibleBlock("步骤 7：控制器基值", self)
        form = QFormLayout()
        self.dc_bus_edit = QLineEdit(block.body)
        self.base_current_edit = QLineEdit(block.body)
        self.base_speed_edit = QLineEdit(block.body)

        self.dc_bus_edit.setPlaceholderText("12.0")
        self.base_current_edit.setPlaceholderText("10.0")
        self.base_speed_edit.setPlaceholderText("3000")

        form.addRow("母线电压", self.dc_bus_edit)
        form.addRow("基准电流", self.base_current_edit)
        form.addRow("基准转速", self.base_speed_edit)
        block.body_layout.addLayout(form)
        return block

    def _build_ctrl_type_block(self):
        block = CollapsibleBlock("步骤 8：控制器类型", self)
        row = QHBoxLayout()
        self.type_foc = QRadioButton("FOC", block.body)
        self.type_vf = QRadioButton("V/F", block.body)
        self.type_speed = QRadioButton("速度环", block.body)
        self.type_foc.setChecked(True)
        row.addWidget(self.type_foc)
        row.addWidget(self.type_vf)
        row.addWidget(self.type_speed)
        row.addStretch(1)
        block.body_layout.addLayout(row)
        return block

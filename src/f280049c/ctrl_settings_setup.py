import sys
from PyQt6.QtWidgets import QApplication, QWizard, QWizardPage, QVBoxLayout, QLabel, QLineEdit, QPushButton, QFileDialog, QCheckBox, QDialog
from PyQt6.QtGui import QFont

class TargetFolderPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("步骤0：设置目标文件夹")

        # 初始化页面布局
        layout = QVBoxLayout()

        # 目标文件夹标签
        folder_label = QLabel("目标文件夹:")
        layout.addWidget(folder_label)

        # 文件夹路径输入框和浏览按钮
        folder_layout = QVBoxLayout()
        self.folder_input = QLineEdit()
        self.folder_input.setPlaceholderText("请选择目标文件夹")
        browse_button = QPushButton("浏览...")
        browse_button.clicked.connect(self.browse_folder)
        
        folder_layout.addWidget(self.folder_input)
        folder_layout.addWidget(browse_button)
        layout.addLayout(folder_layout)

        self.setLayout(layout)

    def browse_folder(self):
        # 打开文件对话框选择目标文件夹
        folder = QFileDialog.getExistingDirectory(self, "选择目标文件夹")
        if folder:
            self.folder_input.setText(folder)

    def validatePage(self):
        return bool(self.folder_input.text())
    
    def get_data(self):
        # 返回选中的目标文件夹
        return self.folder_input.text()

class DebugOptionPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("步骤1：设置调试选项")

        # 初始化页面布局
        layout = QVBoxLayout()

        # 添加标签和输入框
        self.debug_type = QLabel("请选择调试类型：")
        self.debug_type_input = QLineEdit()
        self.debug_type_input.setPlaceholderText("例如：1")

        self.comment_label = QLabel("BUILD_LEVEL 1: hardware validate, VF, voltage open loop\n"
                                    "BUILD_LEVEL 2: IF, current close loop\n"
                                    "BUILD_LEVEL 3: current loop with actual angle\n"
                                    "BUILD_LEVEL 4: speed loop\n"
                                    "BUILD_LEVEL 5: position loop\n"
                                    "BUILD_LEVEL 6: communication mode")

        font = QFont()
        font.setPointSize(8)
        self.comment_label.setFont(font)
        self.comment_label.setWordWrap(True)

        layout.addWidget(self.debug_type)
        layout.addWidget(self.debug_type_input)
        layout.addWidget(self.comment_label)
        
        self.setLayout(layout)

    def validatePage(self):
        return bool(self.debug_type_input.text())
    
    def get_data(self):
        return self.debug_type_input.text()

class ControllerBasicPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("步骤2：设置控制器基本参数")

        # 初始化页面布局
        layout = QVBoxLayout()

        # 添加标签输入框
        self.ctrl_start_delay = QLabel("请输入控制器启动延时（ms）：")
        self.ctrl_start_delay_input = QLineEdit()
        self.ctrl_start_delay_input.setPlaceholderText("例如：1000")

        self.ctrl_freq = QLabel("请输入控制器工作频率（Hz）：")
        self.ctrl_freq_input = QLineEdit()
        self.ctrl_freq_input.setPlaceholderText("例如：1000，科学计数法采用e表示，如20e3")

        self.pwm_depth = QLabel("请输入PWM比较最大值（%）：")
        self.pwm_depth_input = QLineEdit()
        self.pwm_depth_input.setPlaceholderText("例如：2499")

        self.pwm_deadband = QLabel("请输入PWM死区（%）：")
        self.pwm_deadband_input = QLineEdit()
        self.pwm_deadband_input.setPlaceholderText("例如：10")

        self.system_tick = QLabel("请输入系统时钟周期（ns）：")
        self.system_tick_input = QLineEdit()
        self.system_tick_input.setPlaceholderText("例如：1000000")

        self.ctrl_adc_ref = QLabel("请输入控制器ADC参考电压（V）：")
        self.ctrl_adc_ref_input = QLineEdit()
        self.ctrl_adc_ref_input.setPlaceholderText("例如：3.3")

        layout.addWidget(self.ctrl_start_delay)
        layout.addWidget(self.ctrl_start_delay_input)
        layout.addWidget(self.ctrl_freq)
        layout.addWidget(self.ctrl_freq_input)
        layout.addWidget(self.pwm_depth)
        layout.addWidget(self.pwm_depth_input)
        layout.addWidget(self.pwm_deadband)
        layout.addWidget(self.pwm_deadband_input)
        layout.addWidget(self.system_tick)
        layout.addWidget(self.system_tick_input)
        layout.addWidget(self.ctrl_adc_ref)
        layout.addWidget(self.ctrl_adc_ref_input)

        self.setLayout(layout)

    def get_data(self):
        return {
            "ctrl_start_delay": self.ctrl_start_delay_input.text(),
            "ctrl_freq": self.ctrl_freq_input.text(),
            "pwm_depth": self.pwm_depth_input.text(),
            "pwm_deadband": self.pwm_deadband_input.text(),
            "system_tick": self.system_tick_input.text(),
            "ctrl_adc_ref": self.ctrl_adc_ref_input.text(),
        }
    
    def validatePage(self):
        return bool(self.ctrl_start_delay_input.text() and
                    self.ctrl_freq_input.text() and
                    self.pwm_depth_input.text() and
                    self.pwm_deadband_input.text() and
                    self.system_tick_input.text() and
                    self.ctrl_adc_ref_input.text())

class HardwareSettings(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("步骤3：设置硬件参数")

        # 初始化页面布局
        layout = QVBoxLayout()

        self.motor_file_label = QLabel("请选择电机参数文件路径：")
        self.motor_file_path_input = QLineEdit()
        self.motor_file_path_input.setPlaceholderText("请选择文件")
        self.motor_file_path_input.setReadOnly(True)
        self.motor_file_path_button = QPushButton("浏览")
        self.motor_file_path_button.clicked.connect(lambda: self.browse_file("motor"))

        self.ctrl_file_label = QLabel("请选择电机控制器参数文件路径：")
        self.ctrl_file_path_input = QLineEdit()
        self.ctrl_file_path_input.setPlaceholderText("请选择文件")
        self.ctrl_file_path_input.setReadOnly(True)
        self.ctrl_file_path_button = QPushButton("浏览")
        self.ctrl_file_path_button.clicked.connect(lambda: self.browse_file("ctrl"))

        self.checkbox1 = QCheckBox("是否使用默认设置")
        self.checkbox1.setChecked(True)

        layout.addWidget(self.motor_file_label)
        layout.addWidget(self.motor_file_path_input)
        layout.addWidget(self.motor_file_path_button)
        layout.addWidget(self.ctrl_file_label)
        layout.addWidget(self.ctrl_file_path_input)
        layout.addWidget(self.ctrl_file_path_button)
        layout.addWidget(self.checkbox1)

        self.setLayout(layout)

    def browse_file(self, target):
        file_path, _ = QFileDialog.getOpenFileName(self, "选择电机参数文件", "", "C头文件 (*.h)")
        if file_path:
            if target == "motor":
                self.motor_file_path_input.setText(file_path)
            elif target == "ctrl":
                self.ctrl_file_path_input.setText(file_path)
    
    def get_data(self):
        return {
            "motor_file_path": self.motor_file_path_input.text(),
            "ctrl_file_path": self.ctrl_file_path_input.text(),
            "use_default": self.checkbox1.isChecked(),
        }
    
    def validatePage(self):
        return bool(self.motor_file_path_input.text() and
                    self.ctrl_file_path_input.text())
        
class EncoderSettings(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("步骤4：设置编码器参数")

        # 初始化页面布局
        layout = QVBoxLayout()

        self.full_scale = QLabel("请输入编码器满量程值：")
        self.full_scale_input = QLineEdit()
        self.full_scale_input.setPlaceholderText("例如：4096")

        self.ctrl_bias = QLabel("请输入电机控制器偏置值：")
        self.ctrl_bias_input = QLineEdit()
        self.ctrl_bias_input.setPlaceholderText("例如：2048")

        self.speed_division = QLabel("请输入速度划分值：")
        self.speed_division_input = QLineEdit()
        self.speed_division_input.setPlaceholderText("例如：1000")

        self.position_division = QLabel("请输入位置划分值：")
        self.position_division_input = QLineEdit()
        self.position_division_input.setPlaceholderText("例如：1000")

        layout.addWidget(self.full_scale)
        layout.addWidget(self.full_scale_input)
        layout.addWidget(self.ctrl_bias)
        layout.addWidget(self.ctrl_bias_input)
        layout.addWidget(self.speed_division)
        layout.addWidget(self.speed_division_input)
        layout.addWidget(self.position_division)
        layout.addWidget(self.position_division_input)

        self.setLayout(layout)

    def get_data(self):
        return {
            "full_scale": self.full_scale_input.text(),
            "ctrl_bias": self.ctrl_bias_input.text(),
            "speed_division": self.speed_division_input.text(),
            "position_division": self.position_division_input.text(),
        }
    
    def validatePage(self):
        return bool(self.full_scale_input.text() and
                    self.ctrl_bias_input.text() and
                    self.speed_division_input.text() and
                    self.position_division_input.text())

class CtrlBaseSettings(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("步骤5：设置电机控制器基值")

        # 初始化页面布局
        layout = QVBoxLayout()

        self.dc_bus_voltage = QLabel("请输入直流母线电压值：")
        self.dc_bus_voltage_input = QLineEdit()
        self.dc_bus_voltage_input.setPlaceholderText("例如：12.0")

        self.phase_voltage = QLabel("请输入三相电压值：")
        self.phase_voltage_input = QLineEdit()
        self.phase_voltage_input.setPlaceholderText("例如：4.0")

        self.current_base = QLabel("请输入电流基准值：")
        self.current_base_input = QLineEdit()
        self.current_base_input.setPlaceholderText("例如：1.0")

        layout.addWidget(self.dc_bus_voltage)
        layout.addWidget(self.dc_bus_voltage_input)
        layout.addWidget(self.phase_voltage)
        layout.addWidget(self.phase_voltage_input)
        layout.addWidget(self.current_base)
        layout.addWidget(self.current_base_input)

        self.setLayout(layout)

    def get_data(self):
        return {
            "dc_bus_voltage": self.dc_bus_voltage_input.text(),
            "phase_voltage": self.phase_voltage_input.text(),
            "current_base": self.current_base_input.text(),
        }

    def validatePage(self):
        return bool(self.dc_bus_voltage_input.text() and
                    self.phase_voltage_input.text() and
                    self.current_base_input.text())

class CtrlSettingsPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("步骤6：设置电机控制器参数")

        # 初始化页面布局
        layout = QVBoxLayout()

        self.use_discrete_pid = QLabel("请输入是否使用离散PID控制器：")
        self.use_discrete_pid_input = QCheckBox()
        self.use_discrete_pid_input.setChecked(True)

        self.enable_adc_calibration = QLabel("请输入是否启用ADC校准：")
        self.enable_adc_calibration_input = QCheckBox()
        self.enable_adc_calibration_input.setChecked(True)

        self.use_negative_modulator = QLabel("请输入是否使用负电流调制：")
        self.use_negative_modulator_input = QCheckBox()
        self.use_negative_modulator_input.setChecked(True)

        self.adc_calibrate_time = QLabel("请输入ADC校准时间（ms）：")
        self.adc_calibrate_time_input = QLineEdit()
        self.adc_calibrate_time_input.setPlaceholderText("例如：1000")

        self.motor_current_sample_phases = QLabel("请输入电机电流采样相位：")
        self.motor_current_sample_phases_input = QLineEdit()
        self.motor_current_sample_phases_input.setPlaceholderText("例如：3")

        self.enable_motor_fault_protection = QLabel("请输入是否启用电机故障保护：")
        self.enable_motor_fault_protection_input = QCheckBox()
        self.enable_motor_fault_protection_input.setChecked(True)

        self.enable_smooth_current_control = QLabel("请输入是否启用平滑电流控制：")
        self.enable_smooth_current_control_input = QCheckBox()
        self.enable_smooth_current_control_input.setChecked(True)

        layout.addWidget(self.use_discrete_pid)
        layout.addWidget(self.use_discrete_pid_input)
        layout.addWidget(self.enable_adc_calibration)
        layout.addWidget(self.enable_adc_calibration_input)

        layout.addWidget(self.use_negative_modulator)
        layout.addWidget(self.use_negative_modulator_input)

        layout.addWidget(self.adc_calibrate_time)
        layout.addWidget(self.adc_calibrate_time_input)

        layout.addWidget(self.motor_current_sample_phases)
        layout.addWidget(self.motor_current_sample_phases_input)

        layout.addWidget(self.enable_motor_fault_protection)
        layout.addWidget(self.enable_motor_fault_protection_input)

        layout.addWidget(self.enable_smooth_current_control)
        layout.addWidget(self.enable_smooth_current_control_input)

        self.setLayout(layout)

    def get_data(self):
        return {
            "use_discrete_pid": self.use_discrete_pid_input.isChecked(),
            "enable_adc_calibration": self.enable_adc_calibration_input.isChecked(),
            "use_negative_modulator": self.use_negative_modulator_input.isChecked(),
            "adc_calibrate_time": self.adc_calibrate_time_input.text(),
            "motor_current_sample_phases": self.motor_current_sample_phases_input.text(),
            "enable_motor_fault_protection": self.enable_motor_fault_protection_input.isChecked(),
            "enable_smooth_current_control": self.enable_smooth_current_control_input.isChecked(),
        }

    def validatePage(self):
        return bool(self.use_discrete_pid_input.isChecked() and
                    self.enable_adc_calibration_input.isChecked() and
                    self.use_negative_modulator_input.isChecked() and
                    self.adc_calibrate_time_input.text() and
                    self.motor_current_sample_phases_input.text() and
                    self.enable_motor_fault_protection_input.isChecked() and
                    self.enable_smooth_current_control_input.isChecked())

class ConfigWizard(QWizard):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("配置向导")
        self.setWizardStyle(QWizard.WizardStyle.ClassicStyle)

        self.addPage(TargetFolderPage())
        self.addPage(DebugOptionPage())
        self.addPage(ControllerBasicPage())
        self.addPage(HardwareSettings())
        self.addPage(EncoderSettings())
        self.addPage(CtrlBaseSettings())
        self.addPage(CtrlSettingsPage())

        self.finished.connect(self.on_finished)

    def on_finished(self, result):
        # 只有当用户点击Finish按钮时才生成头文件
        if result == QDialog.DialogCode.Accepted:
            targetFolder = self.page(0).get_data()
            debugData = self.page(1).get_data()
            basicData = self.page(2).get_data()
            hardwareData = self.page(3).get_data()
            encoderData = self.page(4).get_data()
            ctrlBaseData = self.page(5).get_data()
            ctrlSettingsData = self.page(6).get_data()

            # 生成头文件内容
            self.generate_ctrl_settings_header(targetFolder, debugData, basicData, hardwareData, encoderData, ctrlBaseData, ctrlSettingsData)

    def _add_float_suffix(self, value):
        """为小数添加f后缀"""
        try:
            # 尝试转换为浮点数
            float_val = float(value)
            # 如果是小数，添加f后缀
            if '.' in str(value):
                return f"{value}f"
            return value
        except ValueError:
            return value

    def generate_ctrl_settings_header(self, targetFolder, debugData, basicData, hardwareData, encoderData, ctrlBaseData, ctrlSettingsData):
        """生成ctrl_settings.h头文件"""
        import os
        header_content = "/*\n"
        header_content += " * ctrl_settings.h\n"
        header_content += " * 电机控制器配置参数\n"
        header_content += " * 自动生成，请勿手动修改\n"
        header_content += " */\n\n"
        header_content += "#ifndef CTRL_SETTINGS_H\n"
        header_content += "#define CTRL_SETTINGS_H\n\n"
        header_content += "// 调试选项\n"
        header_content += "#define BUILD_LEVEL (%s)\n\n"
        header_content += "// 控制器基本参数\n"
        header_content += "#define CTRL_STARTUP_DELAY (%s)  // 控制器启动延时（ms）\n"
        header_content += "#define CONTROLLER_FREQUENCY (%s)        // 控制器工作频率（Hz）\n"
        header_content += "#define CTRL_PWM_CMP_MAX (%s)        // PWM比较最大值（%%）\n"
        header_content += "#define CTRL_PWM_DEADBAND_CMP (%s)     // PWM死区（%%）\n"
        header_content += "#define DSP_C2000_DSP_TIME_DIV (%s)      // 系统时钟周期（ns）\n"
        header_content += "#define CTRL_ADC_VOLTAGE_REF (%s)     // 控制器ADC参考电压（V）\n\n"
        header_content += "// 硬件参数\n"
        if hardwareData.get("use_default", False):
            header_content += "#define BOOSTXL_3PHGANINV_IS_DEFAULT_PARAM // 是否启用平滑电流控制\n"
        header_content += "#include <%s> // invoke motor parameters\n"
        header_content += "#include <%s> // invoke motor controller parameters\n\n"
        header_content += "// 编码器参数\n"
        header_content += "#define CTRL_POS_ENC_FS (%s)      // 编码器满量程值\n"
        header_content += "#define CTRL_POS_ENC_BIAS (%s)               // 电机控制器偏置值\n"
        header_content += "#define CTRL_SPD_DIV (%s)          // 速度划分值\n"
        header_content += "#define CTRL_POS_DIV (%s)       // 位置划分值\n\n"
        header_content += "// 电机控制器基值\n"
        header_content += "#define CTRL_DCBUS_VOLTAGE (%s)   // 直流母线电压值\n"
        header_content += "#define CTRL_VOLTAGE_BASE (%s)    // 三相电压值\n"
        header_content += "#define CTRL_CURRENT_BASE (%s)      // 电流基准值\n\n"
        header_content += "#define CTRL_INVERTER_CURRENT_SENSITIVITY (MY_BOARD_PH_SHUNT_RESISTANCE_OHM * MY_BOARD_PH_CSA_GAIN_V_V) // 逆变器电流灵敏度\n"
        header_content += "#define CTRL_INVERTER_CURRENT_BIAS (MY_BOARD_PH_CSA_BIAS_V) // 逆变器电流偏置值\n"
        header_content += "#define CTRL_INVERTER_VOLTAGE_SENSITIVITY (MY_BOARD_PH_VOLTAGE_SENSE_GAIN) // 逆变器电压灵敏度\n"
        header_content += "#define CTRL_INVERTER_VOLTAGE_BIAS (MY_BOARD_PH_VOLTAGE_SENSE_BIAS_V) // 逆变器电压偏置值\n\n"
        header_content += "#define CTRL_DC_CURRENT_SENSITIVITY (MY_BOARD_DCBUS_CURRENT_SENSE_GAIN) // 直流母线电流灵敏度\n"
        header_content += "#define CTRL_DC_CURRENT_BIAS (MY_BOARD_DCBUS_CURRENT_SENSE_BIAS_V) // 直流母线电流偏置值\n"
        header_content += "#define CTRL_DC_VOLTAGE_SENSITIVITY (MY_BOARD_DCBUS_VOLTAGE_SENSE_GAIN) // 直流母线电压灵敏度\n"
        header_content += "#define CTRL_DC_VOLTAGE_BIAS (MY_BOARD_DCBUS_VOLTAGE_SENSE_BIAS_V) // 直流母线电压偏置值\n\n"
        header_content += "// 电机控制器参数\n"
        if ctrlSettingsData.get("use_discrete_pid", False):
            header_content += "#define _USE_DEBUG_DISCRETE_PID      // 是否使用离散PID控制器\n"
        if ctrlSettingsData.get("enable_adc_calibrate", False):
            header_content += "#define SPECIFY_ENABLE_ADC_CALIBRATE // 是否指定启用ADC校准\n"
        header_content += "#define PWM_MODULATOR_USING_NEGATIVE_LOGIC (%d)         // 是否使用负电流调制\n"
        header_content += "#define TIMEOUT_ADC_CALIB_MS (%s)            // ADC校准超时时间（ms）\n"
        header_content += "#define MC_CURRENT_SAMPLE_PHASE_MODE (%s)    // 电流采样相位模式\n"
        if ctrlSettingsData.get('enable_motor_fault_protection', False):
            header_content += "#define ENABLE_MOTOR_FAULT_PROTECTION         // 是否启用电机故障保护\n"
        if ctrlSettingsData.get('enable_smooth_current_control', False):
            header_content += "#define ENABLE_SMO         // 是否启用平滑电流控制\n\n"
        
        header_content += """// QEP encoder channel\n#define EQEP_Encoder_BASE EQEP2_J13_BASE\n\n
// System LED\n#define SYSTEM_LED     LED_R\n#define CONTROLLER_LED LED_G\n\n
// PWM Channels\n#define PHASE_U_BASE EPWM_J4_PHASE_U_BASE\n#define PHASE_V_BASE EPWM_J4_PHASE_V_BASE\n#define PHASE_W_BASE EPWM_J4_PHASE_W_BASE\n\n
// PWM Enable\n#define PWM_ENABLE_PORT ENABLE_GATE\n#define PWM_RESET_PORT  RESET_GATE\n\n
// DC Bus Voltage & Current\n#define INV_VBUS J3_VDC\n#define INV_IBUS\n\n
#define INV_VBUS_RESULT_BASE J3_VDC_RESULT_BASE\n#define INV_IBUS_RESULT_BASE\n\n
// Inverter side Voltage & Current\n#define INV_IU J3_IU\n#define INV_IV J3_IV\n#define INV_IW J3_IW\n\n
#define INV_IU_RESULT_BASE J3_IU_RESULT_BASE\n#define INV_IV_RESULT_BASE J3_IV_RESULT_BASE\n#define INV_IW_RESULT_BASE J3_IW_RESULT_BASE\n\n
#define INV_UU J3_VU\n#define INV_UV J3_VV\n#define INV_UW J3_VW\n\n
#define INV_UU_RESULT_BASE J3_VU_RESULT_BASE\n#define INV_UV_RESULT_BASE J3_VV_RESULT_BASE\n#define INV_UW_RESULT_BASE J3_VW_RESULT_BASE\n\n"""
        header_content += "#endif /* CTRL_SETTINGS_H */\n"

        # 准备参数
        debug_type = debugData
        ctrl_start_delay = basicData.get("ctrl_start_delay", "1000")
        ctrl_freq = basicData.get("ctrl_freq", "1000")
        pwm_depth = basicData.get("pwm_depth", "2499")
        pwm_deadband = basicData.get("pwm_deadband", "10")
        system_tick = basicData.get("system_tick", "1000000")
        ctrl_adc_ref = self._add_float_suffix(basicData.get("ctrl_adc_ref", "3.3"))

        motor_path = hardwareData.get('motor_file_path', "")
        ctrl_path = hardwareData.get('ctrl_file_path', "")

        encoder_full_scale = encoderData.get("full_scale", "4096")
        ctrl_bias = encoderData.get("ctrl_bias", "2048")
        speed_division = encoderData.get("speed_division", "1000")
        position_division = encoderData.get("position_division", "1000")

        dc_bus_voltage = self._add_float_suffix(ctrlBaseData.get("dc_bus_voltage", "12.0"))
        phase_voltage = self._add_float_suffix(ctrlBaseData.get("phase_voltage", "4.0"))
        current_base = self._add_float_suffix(ctrlBaseData.get("current_base", "1.0"))

        use_negative_modulator = 1 if ctrlSettingsData.get("use_negative_modulator", False) else 0
        adc_calibrate_time = ctrlSettingsData.get("adc_calibrate_time", "1000")
        motor_current_sample_phases = ctrlSettingsData.get("motor_current_sample_phases", "3")

        # 填充内容
        filled_content = header_content % (
            debug_type,
            ctrl_start_delay, ctrl_freq, pwm_depth, pwm_deadband, system_tick, ctrl_adc_ref,
            motor_path, ctrl_path,
            encoder_full_scale, ctrl_bias, speed_division, position_division,
            dc_bus_voltage, phase_voltage, current_base,
            use_negative_modulator, adc_calibrate_time, motor_current_sample_phases
        )

        # 确保目标文件夹存在
        os.makedirs(targetFolder, exist_ok=True)
        
        # 写入文件到目标文件夹
        file_path = os.path.join(targetFolder, "ctrl_settings.h")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(filled_content)

        print(f"ctrl_settings.h头文件已生成到: {file_path}")

def main():
    app = QApplication(sys.argv)

    wizard = ConfigWizard()
    
    # 检查是否有命令行参数
    if len(sys.argv) > 1:
        # 如果有参数，将第一个参数作为目标文件夹
        target_folder = sys.argv[1]
        # 设置目标文件夹到第一个页面
        target_page = wizard.page(0)
        if hasattr(target_page, 'folder_input'):
            target_page.folder_input.setText(target_folder)
    
    wizard.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()

import sys
from PyQt6.QtWidgets import QApplication, QWizard, QWizardPage, QVBoxLayout, QLabel, QLineEdit, QPushButton, QFileDialog, QCheckBox, QDialog, QRadioButton, QButtonGroup
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

class GMPCoreConfig(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("步骤1：设置GMP核心配置")

        # 初始化页面布局
        layout = QVBoxLayout()

        # 添加标签和输入框
        self.enable_csp = QLabel("是否使能CSP")
        self.enable_csp_input = QCheckBox()
        self.enable_csp_input.setChecked(True)

        self.enable_base_print = QLabel("是否使能基础打印")
        self.enable_base_print_input = QCheckBox()
        self.enable_base_print_input.setChecked(True)

        self.user_specified_log_print = QLabel("是否使用用户指定的日志打印函数")
        self.user_specified_log_print_input = QCheckBox()
        self.user_specified_log_print_input.setChecked(False)

        self.gmp_start_screen = QLabel("是否显示GMP启动界面")
        self.gmp_start_screen_input = QCheckBox()
        self.gmp_start_screen_input.setChecked(True)

        layout.addWidget(self.enable_csp)
        layout.addWidget(self.enable_csp_input)
        layout.addWidget(self.enable_base_print)
        layout.addWidget(self.enable_base_print_input)
        layout.addWidget(self.user_specified_log_print)
        layout.addWidget(self.user_specified_log_print_input)
        layout.addWidget(self.gmp_start_screen)
        layout.addWidget(self.gmp_start_screen_input)

        self.setLayout(layout)

    def validatePage(self):
        return True  # All checkboxes are optional, so always return True
    
    def get_data(self):
        return {
            "enable_csp": self.enable_csp_input.isChecked(),
            "enable_base_print": self.enable_base_print_input.isChecked(),
            "user_specified_log_print": self.user_specified_log_print_input.isChecked(),
            "gmp_start_screen": self.gmp_start_screen_input.isChecked()
        }

class CTLConfigPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("步骤2：设置CTL基本配置")

        # 初始化页面布局
        layout = QVBoxLayout()

        # 添加标签输入框
        self.enable_gmp_ctl = QLabel("是否启用GMP CTL：")
        self.enable_gmp_ctl_input = QCheckBox()
        self.enable_gmp_ctl_input.setChecked(True)

        self.enable_ctl_library = QLabel("是否指定启用控制器库：")
        self.enable_ctl_library_input = QCheckBox()
        self.enable_ctl_library_input.setChecked(True)

        self.enable_ctl_framework_nano = QLabel("是否指定启用控制器框架nano：")
        self.enable_ctl_framework_nano_input = QCheckBox()
        self.enable_ctl_framework_nano_input.setChecked(False)

        self.gmp_ctl_default_type = QLabel("请输入GMP CTL默认类型：")
        self.double_fpu_input = QRadioButton("双精度浮点数")
        self.float_fpu_input = QRadioButton("单精度浮点数")
        self.fixed_ti_iq_input = QRadioButton("TI IQ定点数")

        self.group = QButtonGroup(self)
        self.group.addButton(self.double_fpu_input)
        self.group.addButton(self.float_fpu_input)
        self.group.addButton(self.fixed_ti_iq_input)
        self.float_fpu_input.setChecked(True)

        layout.addWidget(self.enable_gmp_ctl)
        layout.addWidget(self.enable_gmp_ctl_input)
        layout.addWidget(self.enable_ctl_library)
        layout.addWidget(self.enable_ctl_library_input)
        layout.addWidget(self.enable_ctl_framework_nano)
        layout.addWidget(self.enable_ctl_framework_nano_input)
        layout.addWidget(self.gmp_ctl_default_type)
        layout.addWidget(self.double_fpu_input)
        layout.addWidget(self.float_fpu_input)
        layout.addWidget(self.fixed_ti_iq_input)

        self.setLayout(layout)

    def get_data(self):
        return {
            "enable_gmp_ctl": self.enable_gmp_ctl_input.isChecked(),
            "enable_ctl_library": self.enable_ctl_library_input.isChecked(),
            "enable_ctl_framework_nano": self.enable_ctl_framework_nano_input.isChecked(),
            "gmp_ctl_default_type": self.group.checkedButton().text() if self.group.checkedButton() else None
        }
    
    def validatePage(self):
        return bool(self.group.checkedButton())  # 确保至少选择一个默认类型

class PCSimulateConfigPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("步骤3：设置PC的Simulink配置")

        # 初始化页面布局
        layout = QVBoxLayout()

        # 添加标签输入框
        self.maximum_loop_count = QLabel("请输入最大循环次数：")
        self.maximum_loop_count_input = QLineEdit()
        self.maximum_loop_count_input.setText("1000000")

        self.specify_ASIO_config_json_file = QLabel("请指定ASIO配置.json文件路径：")
        self.specify_ASIO_config_json_file_input = QLineEdit()
        self.specify_ASIO_config_json_file_input.setPlaceholderText("请选择文件")
        self.specify_ASIO_config_json_file_input.setReadOnly(False)
        self.specify_ASIO_config_json_file_button = QPushButton("浏览")
        self.specify_ASIO_config_json_file_button.clicked.connect(lambda: self.browse_file())

        layout.addWidget(self.maximum_loop_count)
        layout.addWidget(self.maximum_loop_count_input)
        layout.addWidget(self.specify_ASIO_config_json_file)
        layout.addWidget(self.specify_ASIO_config_json_file_input)
        layout.addWidget(self.specify_ASIO_config_json_file_button)

        self.setLayout(layout)

    def browse_file(self):
        """打开文件对话框选择ASIO配置.json文件"""
        file_path, _ = QFileDialog.getOpenFileName(self, "选择ASIO配置.json文件", "", "JSON Files (*.json)")
        if file_path:
            self.specify_ASIO_config_json_file_input.setText(file_path)

    def get_data(self):
        return {
            "maximum_loop_count": int(self.maximum_loop_count_input.text()),
            "specify_ASIO_config_json_file": self.specify_ASIO_config_json_file_input.text()
        }
    
    def validatePage(self):
        return bool(self.maximum_loop_count_input.text() and
                    self.specify_ASIO_config_json_file_input.text())  # 确保指定了ASIO配置文件路径

class ConfigWizard(QWizard):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("配置向导")
        self.setWizardStyle(QWizard.WizardStyle.ClassicStyle)

        self.addPage(TargetFolderPage())
        self.addPage(GMPCoreConfig())
        self.addPage(CTLConfigPage())
        self.addPage(PCSimulateConfigPage())

        self.finished.connect(self.on_finished)

    def on_finished(self, result):
        # 只有当用户点击Finish按钮时才生成头文件
        if result == QDialog.DialogCode.Accepted:
            targetFolder = self.page(0).get_data()
            gmpCoreConfig = self.page(1).get_data()
            ctlConfig = self.page(2).get_data()
            pcSimulateConfig = self.page(3).get_data()

            # 生成头文件内容
            self.generate_ctrl_settings_header(targetFolder, gmpCoreConfig, ctlConfig, pcSimulateConfig)

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

    def generate_ctrl_settings_header(self, targetFolder, gmpCoreConfig, ctlConfig, pcSimulateConfig):
        """生成ctrl_settings.h头文件"""
        import os
        header_content = "// GMP core config module\n"
        if not gmpCoreConfig.get("enable_csp", True):
            header_content += "#define SPECIFY_DISABLE_CSP\n"
        if not gmpCoreConfig.get("enable_base_print", True):
            header_content += "#define SPECIFY_BASE_PRINT_NOT_IMPL\n"
        if gmpCoreConfig.get("user_specified_log_print", False):
            header_content += "#define USER_SPECIFIED_PRINT_FUNCTION printf_s\n"
        if not gmpCoreConfig.get("gmp_start_screen", True):
            header_content += "#define SPECIFY_DISABLE_GMP_LOGO\n\n"
        header_content += "// CTL config module\n"
        if not ctlConfig.get("enable_gmp_ctl", True):
            header_content += "#define SPECIFY_DISABLE_GMP_CTL\n"
        if ctlConfig.get("enable_ctl_library", False):
            header_content += "#define SPECIFY_ENABLE_GMP_CTL\n"
        if ctlConfig.get("enable_ctl_framework_nano", False):
            header_content += "#define SPECIFY_ENABLE_CTL_FRAMEWORK_NANO\n"
        if ctlConfig.get("gmp_ctl_default_type", "单精度浮点数") == "双精度浮点数":
            header_content += "#define SPECIFY_CTRL_GT_TYPE USING_DOUBLE_FPU\n\n"
        elif ctlConfig.get("gmp_ctl_default_type", "单精度浮点数") == "单精度浮点数":
            header_content += "#define SPECIFY_CTRL_GT_TYPE USING_FLOAT_FPU\n\n"
        else:
            header_content += "#define SPECIFY_CTRL_GT_TYPE USING_FIXED_TI_IQ_LIBRARY\n\n"

        header_content += "// PC environment setup\n#define SPECIFY_PC_ENVIRONMENT\n\n"
        header_content += "// PC environment maximum loop counter\n#define PC_ENV_MAX_ITERATION ((%s))\n\n"
        header_content += "// specify ASIO config .json file\n#define GMP_ASIO_CONFIG_JSON \"%s\"\n\n"
        header_content += "// specify Simulink Communicate buffer\n#define gmp_pc_simulink_rx_buffer_t dp_sil_rx_buf_t\n#define gmp_pc_simulink_tx_buffer_t dp_sil_tx_buf_t\n\n"
        header_content += "// Invoke Controller Settings\n"
        header_content += "#include <ctrl_settings.h>\n"

        # 填充内容到模板（如果有的话），这里直接使用生成的内容
        filled_content = header_content % (
            pcSimulateConfig["maximum_loop_count"],
            pcSimulateConfig["specify_ASIO_config_json_file"]
        )

        # 确保目标文件夹存在
        os.makedirs(targetFolder, exist_ok=True)
        
        # 写入文件到目标文件夹
        file_path = os.path.join(targetFolder, "xplt.config.h")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(filled_content)

        print(f"xplt.config.h头文件已生成到: {file_path}")

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

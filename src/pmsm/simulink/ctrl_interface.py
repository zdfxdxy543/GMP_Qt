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

class ConfigWizard(QWizard):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("配置向导")
        self.setWizardStyle(QWizard.WizardStyle.ClassicStyle)

        self.addPage(TargetFolderPage())

        self.finished.connect(self.on_finished)

    def on_finished(self, result):
        # 只有当用户点击Finish按钮时才生成头文件
        if result == QDialog.DialogCode.Accepted:
            targetFolder = self.page(0).get_data()

            # 生成头文件内容
            self.generate_ctrl_settings_header(targetFolder)

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

    def generate_ctrl_settings_header(self, targetFolder):
        """生成ctrl_settings.h头文件"""
        import os
        header_content = "// GMP core config module\n"
        header_content += "#include <ctl/component/motor_control/basic/std_sil_motor_interface.h>\n\n"
        header_content += "#include <xplt.peripheral.h>\n\n"
        header_content += "#ifndef _FILE_CTL_INTERFACE_H_\n#define _FILE_CTL_INTERFACE_H_\n\n"
        header_content += '#ifdef __cplusplus\nextern "C"\n{\n#endif // __cplusplus\n\n'
        header_content += "//=================================================================================================\n// Board peripheral mapping\n\n"
        header_content += "// Controller interface\n"
        header_content += "// Input Callbacks\n"
        header_content += "GMP_STATIC_INLINE void ctl_input_callback(void)\n{\n\n}\n\n"
        header_content += "// Output Callbacks\n"
        header_content += "GMP_STATIC_INLINE void ctl_output_callback(void)\n{\n\n}\n\n"
        header_content += "// Function prototype\n"
        header_content += "void GPIO_WritePin(uint16_t gpioNumber, uint16_t outVal);\n\n"
        header_content += "// Enable Output\n"
        header_content += "GMP_STATIC_INLINE void ctl_fast_enable_output()\n{\n\n}\n\n"
        header_content += "// Disable Output\n"
        header_content += "GMP_STATIC_INLINE void ctl_fast_disable_output()\n{\n\n}\n\n"
        header_content += "#ifdef __cplusplus\n}\n#endif // __cplusplus\n\n"
        header_content += "#endif // _FILE_CTL_INTERFACE_H_"

        # 填充内容到模板（如果有的话），这里直接使用生成的内容
        filled_content = header_content

        # 确保目标文件夹存在
        os.makedirs(targetFolder, exist_ok=True)
        
        # 写入文件到目标文件夹
        file_path = os.path.join(targetFolder, "xplt.ctl_interface.h")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(filled_content)

        print(f"xplt.ctl_interface.h头文件已生成到: {file_path}")

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

import sys
from PyQt6.QtWidgets import QApplication, QWizard, QWizardPage, QVBoxLayout, QLabel, QLineEdit, QPushButton


class Step1Page(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("步骤 1: 配置 IP 地址")

        # 页面布局
        layout = QVBoxLayout()

        # 添加标签和输入框
        self.ip_label = QLabel("请输入 IP 地址：")
        self.ip_input = QLineEdit()
        self.ip_input.setPlaceholderText("例如：192.168.0.1")

        layout.addWidget(self.ip_label)
        layout.addWidget(self.ip_input)

        self.setLayout(layout)

    def validatePage(self):
        # 确保 IP 地址字段非空
        return bool(self.ip_input.text())

    def get_data(self):
        return self.ip_input.text()


class Step2Page(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("步骤 2: 配置 DNS 地址")

        # 页面布局
        layout = QVBoxLayout()

        # 添加标签和输入框
        self.dns_label = QLabel("请输入 DNS 地址：")
        self.dns_input = QLineEdit()
        self.dns_input.setPlaceholderText("例如：8.8.8.8")

        layout.addWidget(self.dns_label)
        layout.addWidget(self.dns_input)

        self.setLayout(layout)

    def validatePage(self):
        # 确保 DNS 地址字段非空
        return bool(self.dns_input.text())

    def get_data(self):
        return self.dns_input.text()


class ConfigWizard(QWizard):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("多步向导示例")
        self.setWizardStyle(QWizard.WizardStyle.ClassicStyle)

        # 添加页面
        self.addPage(Step1Page())
        self.addPage(Step2Page())

        # 完成时的处理
        self.finished.connect(self.on_finish)

    def on_finish(self):
        # 获取数据
        ip = self.page(0).get_data()
        dns = self.page(1).get_data()
        print(f"生成配置文件：IP 地址 = {ip}, DNS 地址 = {dns}")

        # 生成配置文件或进行其他操作
        self.generate_config_file(ip, dns)

    def generate_config_file(self, ip, dns):
        # 这里简单示例：生成一个文本文件
        with open("config.txt", "w") as file:
            file.write(f"IP 地址: {ip}\n")
            file.write(f"DNS 地址: {dns}\n")
        print("配置文件已生成：config.txt")


def main():
    app = QApplication(sys.argv)

    wizard = ConfigWizard()
    wizard.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()

import sys
import os
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem, QLabel, QPushButton, QLineEdit, QFileDialog
from PyQt6.QtCore import QProcess


class WizardManager(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Wizard管理工具")
        self.setGeometry(100, 100, 600, 400)

        # 主布局
        main_layout = QVBoxLayout()

        # 标题
        title_label = QLabel("Wizard管理工具")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        main_layout.addWidget(title_label)

        # 列表布局
        list_layout = QHBoxLayout()

        # 创建三个列表
        self.left_list = QListWidget()
        self.middle_list = QListWidget()
        self.right_list = QListWidget()

        # 设置列表宽度
        self.left_list.setFixedWidth(150)
        self.middle_list.setFixedWidth(150)
        self.right_list.setFixedWidth(150)

        # 添加标签
        left_label = QLabel("类别")
        middle_label = QLabel("子类别")
        right_label = QLabel("选项")

        # 左侧布局
        left_layout = QVBoxLayout()
        left_layout.addWidget(left_label)
        left_layout.addWidget(self.left_list)

        # 中间布局
        middle_layout = QVBoxLayout()
        middle_layout.addWidget(middle_label)
        middle_layout.addWidget(self.middle_list)

        # 右侧布局
        right_layout = QVBoxLayout()
        right_layout.addWidget(right_label)
        right_layout.addWidget(self.right_list)

        # 添加到水平布局
        list_layout.addLayout(left_layout)
        list_layout.addLayout(middle_layout)
        list_layout.addLayout(right_layout)

        # 添加到主布局
        main_layout.addLayout(list_layout)

        # 目标文件夹设置
        folder_layout = QHBoxLayout()
        folder_label = QLabel("目标文件夹:")
        self.folder_input = QLineEdit()
        self.folder_input.setPlaceholderText("请选择目标文件夹")
        browse_button = QPushButton("浏览...")
        browse_button.clicked.connect(self.browse_folder)
        
        folder_layout.addWidget(folder_label)
        folder_layout.addWidget(self.folder_input)
        folder_layout.addWidget(browse_button)
        main_layout.addLayout(folder_layout)

        # 运行按钮
        self.run_button = QPushButton("运行Wizard")
        self.run_button.setEnabled(False)  # 初始禁用
        self.run_button.clicked.connect(self.on_run_wizard)
        main_layout.addWidget(self.run_button)

        # 状态标签
        self.status_label = QLabel("请选择要运行的Wizard")
        main_layout.addWidget(self.status_label)

        self.setLayout(main_layout)

        # 数据 - 存储exe文件路径信息
        self.exe_data = {}

        # 自动扫描tools目录
        self.scan_tools_directory()

    def scan_tools_directory(self):
        # 获取exe文件所在目录
        if getattr(sys, 'frozen', False):
            # 如果是打包后的exe文件
            app_dir = os.path.dirname(sys.executable)
        else:
            # 如果是直接运行Python脚本
            app_dir = os.path.dirname(os.path.abspath(__file__))
        
        tools_dir = os.path.join(app_dir, 'tools')
        
        # 初始化数据
        self.data = {}
        
        # 检查tools目录是否存在
        if not os.path.exists(tools_dir):
            self.status_label.setText(f"tools目录不存在: {tools_dir}")
            return
        
        # 遍历tools目录下的所有.exe文件
        for root, dirs, files in os.walk(tools_dir):
            for file in files:
                if file.endswith('.exe'):
                    # 获取文件的完整路径
                    exe_path = os.path.join(root, file)
                    # 计算相对于tools目录的路径
                    rel_path = os.path.relpath(exe_path, tools_dir)
                    # 分割路径获取各级目录
                    parts = rel_path.split(os.sep)
                    
                    # 解析路径：第一级/第二级/第三级.exe
                    if len(parts) >= 3:
                        first_dir = parts[0]
                        second_dir = parts[1]
                        third_dir = parts[2]
                        
                        # 移除.exe后缀作为显示名称
                        option_name = os.path.splitext(third_dir)[0]
                        
                        # 构建数据结构
                        if first_dir not in self.data:
                            self.data[first_dir] = {}
                        if second_dir not in self.data[first_dir]:
                            self.data[first_dir][second_dir] = []
                        
                        # 存储exe路径信息
                        if option_name not in self.data[first_dir][second_dir]:
                            self.data[first_dir][second_dir].append(option_name)
                        
                        # 存储完整的exe路径
                        if first_dir not in self.exe_data:
                            self.exe_data[first_dir] = {}
                        if second_dir not in self.exe_data[first_dir]:
                            self.exe_data[first_dir][second_dir] = {}
                        self.exe_data[first_dir][second_dir][option_name] = exe_path
        
        if not self.data:
            self.status_label.setText("未找到任何Wizard程序")
        else:
            self.status_label.setText(f"已加载 {len(self.data)} 个Wizard类别")
            
            # 填充左侧列表
            for category in self.data.keys():
                item = QListWidgetItem(category)
                self.left_list.addItem(item)

        # 连接信号
        self.left_list.itemClicked.connect(self.on_left_item_clicked)
        self.middle_list.itemClicked.connect(self.on_middle_item_clicked)
        self.right_list.itemClicked.connect(self.on_right_item_clicked)

        # 初始化选中状态
        self.selected_category = None
        self.selected_subcategory = None
        self.selected_option = None

    def on_left_item_clicked(self, item):
        # 清空中间和右侧列表
        self.middle_list.clear()
        self.right_list.clear()

        # 获取选中的类别
        category = item.text()
        self.selected_category = category

        # 填充中间列表
        subcategories = self.data.get(category, {})
        for subcategory in subcategories:
            subitem = QListWidgetItem(subcategory)
            self.middle_list.addItem(subitem)

        # 重置选中状态
        self.selected_subcategory = None
        self.selected_option = None
        self.update_run_button()

    def on_middle_item_clicked(self, item):
        # 清空右侧列表
        self.right_list.clear()

        # 获取选中的子类别
        subcategory = item.text()
        self.selected_subcategory = subcategory

        # 填充右侧列表
        if self.selected_category:
            options = self.data[self.selected_category].get(subcategory, [])
            for option in options:
                option_item = QListWidgetItem(option)
                self.right_list.addItem(option_item)

        # 重置选中状态
        self.selected_option = None
        self.update_run_button()

    def on_right_item_clicked(self, item):
        # 获取选中的选项
        option = item.text()
        self.selected_option = option
        self.update_run_button()

    def update_run_button(self):
        # 只有当三个列表都有选中项时，运行按钮才可用
        is_complete = bool(self.selected_category and self.selected_subcategory and self.selected_option)
        self.run_button.setEnabled(is_complete)
        
        if is_complete:
            self.status_label.setText(f"已选择: {self.selected_category} > {self.selected_subcategory} > {self.selected_option}")
        else:
            self.status_label.setText("请选择要运行的Wizard")

    def browse_folder(self):
        # 打开文件对话框选择目标文件夹
        folder = QFileDialog.getExistingDirectory(self, "选择目标文件夹")
        if folder:
            self.folder_input.setText(folder)
            self.status_label.setText(f"已选择目标文件夹: {folder}")

    def on_run_wizard(self):
        # 运行选中的Wizard
        if self.selected_category and self.selected_subcategory and self.selected_option:
            # 获取exe文件路径
            exe_path = self.exe_data.get(self.selected_category, {}).get(self.selected_subcategory, {}).get(self.selected_option)
            
            if exe_path and os.path.exists(exe_path):
                # 获取目标文件夹
                target_folder = self.folder_input.text()
                
                print(f"运行Wizard: {self.selected_category} > {self.selected_subcategory} > {self.selected_option}")
                print(f"Exe路径: {exe_path}")
                print(f"目标文件夹: {target_folder}")
                
                # 启动exe程序
                if target_folder:
                    # 带参数运行
                    QProcess.startDetached(exe_path, [target_folder])
                else:
                    # 不带参数运行
                    QProcess.startDetached(exe_path)
                
                self.status_label.setText(f"已运行: {self.selected_option}")
            else:
                self.status_label.setText(f"exe文件不存在: {exe_path}")


def main():
    app = QApplication(sys.argv)
    
    manager = WizardManager()
    manager.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()


from fbs_runtime.application_context.PyQt5 import ApplicationContext
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QLabel, QPushButton, QVBoxLayout
from PyQt5.QtWidgets import QMainWindow

import sys

class AppContext(ApplicationContext):           # 1. Subclass ApplicationContext
    def run(self):                              # 2. Implement run()
        self.app.setStyle('Fusion')                            
        window = QMainWindow()
        version = self.build_settings['version']
        window.setWindowTitle("PCF-Reader v" + version)
        window.resize(250, 150)
       

        text = QLabel()
        text.setWordWrap(True)
        button = QPushButton('Next quote >')
        button.clicked.connect(lambda: text.setText("test text"))
        layout = QVBoxLayout()
        layout.addWidget(text)
        layout.addWidget(button)
        layout.setAlignment(button, Qt.AlignHCenter)
        
        centralWidget = QWidget()
        centralWidget.setLayout(layout)

        window.setCentralWidget(centralWidget)
        
        window.show()

        return self.app.exec_()                 # 3. End run() with this line

if __name__ == '__main__':
    appctxt = AppContext()                      # 4. Instantiate the subclass
    stylesheet = appctxt.get_resource('styles.qss')
    appctxt.app.setStyleSheet(open(stylesheet).read())
    exit_code = appctxt.run()                   # 5. Invoke run()
    sys.exit(exit_code)
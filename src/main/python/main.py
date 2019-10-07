from fbs_runtime.application_context.PyQt5 import ApplicationContext
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QLabel, QPushButton, QVBoxLayout, QFileDialog, QStatusBar
from PyQt5.QtWidgets import QMainWindow, QMessageBox, QTableView, QHBoxLayout
import os
import re
import pandas as pd
from pandasmodel import PandasModel
import sys
from contextlib import contextmanager
from PyQt5.QtGui import QGuiApplication, QCursor
from PyQt5 import QtCore

@contextmanager
def wait_cursor():
    try:
        QGuiApplication.setOverrideCursor(QCursor(QtCore.Qt.WaitCursor))
        yield
    finally:
        QGuiApplication.restoreOverrideCursor()


class AppContext(ApplicationContext):           # 1. Subclass ApplicationContext
    def run(self):                              # 2. Implement run()
        self.app.setStyle('Fusion')                            
        window = QMainWindow()
        version = self.build_settings['version']
        window.setWindowTitle("PCF-Reader v" + version)
        window.resize(800, 600)
        self.statusBar = QStatusBar()
        window.setStatusBar(self.statusBar)
        self.statusBar.setUpdatesEnabled(True)
       
        self.tableView = QTableView()

        text = QLabel()
        text.setWordWrap(True)
        button1 = QPushButton('Open folder with PCF files')
        button1.clicked.connect(self.get_folder_name_and_process)
        button2 = QPushButton('Export to Exel file')
        button2.clicked.connect(self.excel_export)
        layout = QVBoxLayout()
        layout.addWidget(self.tableView)
        layout.addWidget(text)
        b_lay = QHBoxLayout()
        b_lay.addWidget(button1)
        b_lay.addWidget(button2)
        layout.addLayout(b_lay)
        layout.setAlignment(b_lay, Qt.AlignHCenter)
        
        centralWidget = QWidget()
        centralWidget.setLayout(layout)

        window.setCentralWidget(centralWidget)
        
        window.show()

        return self.app.exec_()                 # 3. End run() with this line

    def get_folder_name_and_process(self):
        path = QFileDialog.getExistingDirectory(caption = "Select directory with *.pcf files")
        if not path:
            return
        
        filenames = self.get_file_names(path) 
        self.statusBar.showMessage('Found {} PCF files'.format(len(filenames)))

        with wait_cursor():
        
            df = pd.DataFrame()
            for no, f_name in enumerate(filenames):
                short_name = f_name.split('\\')[-1]
                self.statusBar.showMessage('Parsing {} of {}, filename:  {}'.format(str(no+1), 
                                        str(len(filenames)), short_name))
                QtCore.QCoreApplication.processEvents()
                nodes = self.parse_file(f_name)
                if nodes is not None:
                    if df is not None:
                        df = pd.concat([df, self.create_df(nodes)], sort=False, ignore_index = True)
                
            self.df = df[self.get_columns_to_show(df.columns)]
        
        model = PandasModel(self.df)
        self.tableView.setModel(model)
        self.statusBar.showMessage('Elements retrieved')



    def get_file_names(self, folder_name):
        
        files = os.listdir(folder_name)
        files = list(filter(lambda x: x.endswith('.PCF'), files))
        files = [os.path.join(folder_name, f) for f in files]
        return files

    def parse_file(self, file_name):
        try: 
            fp = open(file_name, 'rt') 
        except FileNotFoundError:
            QMessageBox.critical(None, 'Error', "FileNotFound: {}".format(file_name), QMessageBox.Ok)
            return None
       
        nodes = []
        for line in fp:
            if  line[-1] == '\n':
                line = line[:-1]
            
            if self.is_root_element(line):
                root = self.get_new_root(line)
                nodes.append(root)
                value_idx = 2
                continue
            
            # processing inner element
            k,v = self.get_key_value(line)
            
            if k in root["inner_values"].keys():
                k = k + '_' + str(value_idx)
                value_idx += 1
            root["inner_values"][k] = v

            #if root["name"] == ["WELD"] and len(root["inner_values"]) > 9:
            #    print(root)

        
        return nodes

    def create_df(self, nodes):
         
        header_values = {
            "UNITS-BORE": "",
            "UNITS-CO-ORDS": "",
            "UNITS-BOLT-LENGTH": "",
            "UNITS-BOLT-DIA": "",
            "UNITS-WEIGHT": "", 
            "UID": ""}
        
        header_values = self.get_header_values(nodes, header_values)
        
        pipeline_values = {
            "PIPELINE-REFERENCE": "",
            "PL_PIPING-SPEC": "",
            "PL_UID": "",
            "PL_MISC-SPEC1":"",
            "PL_MISC-SPEC2":"",
            "PL_MISC-SPEC3":"",
            "PL_MISC-SPEC4":"",
        }

        pipeline_values = self.get_pipeline_values(nodes, pipeline_values)

        elements = self.get_node_elements_by_name(nodes,"WELD")
        if len(elements) == 0:
            return None
        
        df = pd.DataFrame()
        for e in elements:
            row = self.get_empty_row()
            
            for k,v in pipeline_values.items():
                row[k] = v
            
            idx = 1            
            for k,v in e["inner_values"].items():
                if 'POINT' in k:
                    x,y,z,dn = self.get_coords_from_endpoint(v)
                    if idx == 1:
                        row['UNITS-CO-ORDS'] = header_values['UNITS-CO-ORDS']

                    row['X' + str(idx)] = x
                    row['Y' + str(idx)] = y
                    row['Z'+ str(idx)] = z
                    row['DN' + str(idx)] = dn
                    if idx == 1:
                        row['UNITS-BORE'] = header_values['UNITS-BORE']
                    
                    idx += 1
                    
                else:
                    row[k] = v
            df = df.append(row, ignore_index = True, sort=False)
        
        return df

    def get_coords_from_endpoint(self, end_point):
        '''
        Function return x, y, z, dn from endpoint
        '''
        l = end_point.split()
        x,y,z = l[:3]
        if len(l) == 4:
            dn = l[3]
        else:
            dn = ""
        
        return x, y, z, dn

    def get_new_root(self, line):
        root = {}
        kv = self.get_key_value(line)
        root["name"] = kv[0]
        root["value"] = kv[1]
        root["inner_values"] = {}
        return root
        
    
    def get_key_value(self, line):
        kv = line.split(maxsplit=1)
        k = kv[0]
        v = kv[1] if len(kv) > 1 else ""
        return k, v
    
    def is_root_element(self, line):
        return not line.startswith(" ")
    
    
    def get_empty_row(self):
        return pd.Series()
    
        
    def get_header_values(self, nodes, header_values):
        '''
        processing header info
        '''
        for h_name, _ in header_values.items():
            elements = self.get_node_elements_by_name(nodes, h_name)
            if len(elements) == 1:
                header_values[h_name] = elements[0]["value"]
        return header_values        

    def get_pipeline_values(self, nodes, pipeline_values):
        elements = self.get_node_elements_by_name(nodes, "PIPELINE-REFERENCE")
        if len(elements) == 0:
            QMessageBox.critical(None, 'Error', "Pipiline Reference info not found", QMessageBox.Ok)
            return
        pl = elements[0]
        for h_name, _ in pipeline_values.items():
            if h_name == "PIPELINE-REFERENCE":
                pipeline_values["PIPELINE-REFERENCE"] = pl["value"]
            else:
                if h_name[3:] in pl["inner_values"].keys():
                    pipeline_values[h_name] = pl["inner_values"][h_name[3:]]
        
        return pipeline_values



    def get_node_elements_by_name(self, nodes, name):
        elements = list(filter(lambda x: x["name"] == name, nodes))
        return elements


    def get_columns_to_show(self, columns):
        new_cols = ['PIPELINE-REFERENCE', 'PL_PIPING-SPEC', 'PL_MISC-SPEC2', 'X1','Y1','Z1',"UNITS-CO-ORDS",
        "DN1","UNITS-BORE", "WELD-TYPE","CATEGORY","COMPONENT-IDENTIFIER","UID"]
        
        for c in new_cols:
            if c not in columns:
                QMessageBox.critical(None, 'Error', "Column not found in data: {}".format(c), QMessageBox.Ok)
                return columns
        
        return new_cols

    def excel_export(self):
        if self.df is not None:
            fileName = QFileDialog.getSaveFileName(None,"Select file name to export","","xlsx files (*.xlsx)")
            if fileName[0]:
                self.df.to_excel(fileName[0], sheet_name = "welds", index = False)
                self.statusBar.showMessage("Data exported")


if __name__ == '__main__':
    appctxt = AppContext()                      # 4. Instantiate the subclass
    stylesheet = appctxt.get_resource('styles.qss')
    appctxt.app.setStyleSheet(open(stylesheet).read())
    exit_code = appctxt.run()                   # 5. Invoke run()
    sys.exit(exit_code)
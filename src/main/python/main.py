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
import math
from functools import lru_cache
from config import Configuration
import logging
import tempfile
import time
from excelwriter import ExcelWorkBookWriter


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
        window.resize(1024, 600)
        self.statusBar = QStatusBar()
        window.setStatusBar(self.statusBar)
        self.statusBar.setUpdatesEnabled(True)
       
        self.tableView = QTableView()

        text = QLabel()
        text.setWordWrap(True)
        button1 = QPushButton('Open folder with PCF files')
        button1.clicked.connect(self.get_folder_name_and_process)
        button2 = QPushButton('Export to Excel file')
        button2.clicked.connect(self.excel_export)
        button3 = QPushButton('Export to BOM format Excel file')
        button3.clicked.connect(self.excel_bom_format_export)
        layout = QVBoxLayout()
        layout.addWidget(self.tableView)
        layout.addWidget(text)
        b_lay = QHBoxLayout()
        b_lay.addWidget(button1)
        b_lay.addWidget(button2)
        b_lay.addWidget(button3)
        layout.addLayout(b_lay)
        layout.setAlignment(b_lay, Qt.AlignHCenter)
        
        centralWidget = QWidget()
        centralWidget.setLayout(layout)

        window.setCentralWidget(centralWidget)
        #just for not to show empty window
        self.df = pd.DataFrame(columns=[c.upper() for c in self.config.column_names])
        model = PandasModel(self.df)
        self.tableView.setModel(model)

        window.show()
        QGuiApplication.restoreOverrideCursor()    
        return self.app.exec_()                 # 3. End run() with this line

    def get_folder_name_and_process(self):
        
        path = QFileDialog.getExistingDirectory(caption = "Select directory with *.pcf files")
        if not path:
            return
        df = pd.DataFrame()
        filenames = self.get_file_names(path) 
        self.statusBar.showMessage('Found {} PCF files'.format(len(filenames)))

        if len(filenames) == 0:
            QMessageBox.critical(None, 'Error', "PCF files does not found in selected dir", QMessageBox.Ok)
            return
        

        with wait_cursor():
            for no, f_name in enumerate(filenames):
                short_name = f_name.split('\\')[-1]
                self.curren_processed_file = short_name
                self.statusBar.showMessage('Parsing {} of {}, filename:  {}'.format(str(no+1), 
                                        str(len(filenames)), short_name))
                QtCore.QCoreApplication.processEvents()
                try:
                    self.nodes = self.parse_file(f_name)
                except Exception as err:
                    QMessageBox.critical(None, 'Error', str(err) + ' in file {}'
                                            .format(self.curren_processed_file), QMessageBox.Ok)

                if self.nodes is not None:
                    try:
                        one_file_df = self.create_one_file_df()
                    except (AssertionError, IndexError) as err:
                        QMessageBox.critical(None, 'Error', str(err) + ' in file {}'.format(self.curren_processed_file), QMessageBox.Ok)
                    else:
                        df = df.append(one_file_df, ignore_index = True, sort = False)
            
            if self.config.use_aggregation:
                self.row_data_df = self.group_values(df)

            self.df = self.final_formatting(self.row_data_df)
           
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
            QMessQMessageBox.critical(None, 'Error', "FileNotFound: {}".format(file_name), QMessageBox.Ok)
            return None
       
        nodes = []
        for line in fp:
            line = line[:-1] if line[-1] == '\n' else line
                            
            if self.is_root_element(line):
                root = self.get_new_root(line)
                nodes.append(root)
                continue
            
            # processing inner element
            k,v = self.get_key_value(line)
            new_k = self.check_key_exist_in_values(k, root["inner_values"], new_index = 2)
            root["inner_values"][new_k] = v
                    
        return nodes

    def is_root_element(self, line):
        return not line.startswith(" ")

    def get_new_root(self, line):
        root = {}
        k, v = self.get_key_value(line)
        root["name"] = k
        root["section_name"]= self.get_section_name(k)
        root["value"] = v
        root["inner_values"] = {}
        return root

    def get_key_value(self, line):
        kv = line.split(maxsplit=1)
        k = kv[0]
        v = kv[1] if len(kv) > 1 else ""
        return k, v

    def get_section_name(self, name):
        if name in self.config.header_sections: return "HEADER"
        if name in self.config.pipeline_sections: return "PIPELINE"
        if name in self.config.material_sections: return "MATERIAL"
        if name in self.config.section_not_report: return "NOT REPORT"
        if name in self.config.section_types: return name
        return "PART"


    def check_key_exist_in_values(self, k, inner_values, new_index):
        if k in inner_values.keys():
            k = self.get_value_without_ending_index(k)
            k = k + '_' + str(new_index)
            k = self.check_key_exist_in_values(k, inner_values, new_index+1)
        return k            
    
    def get_value_without_ending_index(self, k):
        if k.endswith(('_2','_3','_4','_5','_6')):
            k = k[:-2]
        return k

    def create_one_file_df(self):
        header_values = self.get_header_values()
            
        if "UNITS-CO-ORDS" in header_values.keys():
            self.dim_units = header_values["UNITS-CO-ORDS"].upper()
        
        pipeline_values = self.get_pipeline_values()

        df = pd.DataFrame()
        for section_name in self.config.section_to_report:
            section_df = self.create_section_df(header_values, pipeline_values, section_name)
            df = df.append(section_df, ignore_index = True, sort=False)
        return df.fillna('')
        
    def get_header_values(self):
        elements = self.get_elements_by_section_name("HEADER")
        if len(elements) == 0:
            QMessageBox.critical(None, 'Error', "Header not found", QMessageBox.Ok)
        header_values = {}
        for e in elements:
            header_values[e['name']] = e["value"]
                
        return header_values        

    def get_pipeline_values(self):
        elements = self.get_elements_by_section_name("PIPELINE")
        assert len(elements) > 0, "Pipeline Reference not found"
                               
        pipeline_values = {}
        pipeline_values['PIPELINE-REFERENCE'] = elements[0]['value']
        
        pipeline_values["PIPING-SPEC"] = elements[0]["inner_values"]["PIPING-SPEC"]
        '''
        pipeline_attributes = set(elements[0]["inner_values"].keys()) & set(self.config.column_names.values()) 
        for name in pipeline_attributes:
            if name in elements[0]["inner_values"].keys():
                pipeline_values[name] = elements[0]["inner_values"][name]
        '''
        return pipeline_values

    def get_elements_by_section_name(self, section_name):
        elements = list(filter(lambda x: x["section_name"] == section_name, self.nodes))
        return elements

    def create_section_df(self, header_values, pipeline_values, section_name):
        elements = self.get_elements_by_section_name(section_name)
        if len(elements) == 0:
            return None
        
        df = pd.DataFrame()
        for element in elements:
            if element["inner_values"] == {}:
                continue
            row = self.create_one_row(element, header_values, pipeline_values)
            
            df = df.append(row, ignore_index = True, sort=False)
        
        return df.fillna('').sort_values(by = "PART_TYPE")    
    
    def create_one_row(self, element, header_values, pipeline_values):
        row = self.get_empty_row()
        part_type = element["name"]        
        row['PART_TYPE'] = part_type 
        
        for k,v in pipeline_values.items():
            row[k] = v
              
        attributes = set(self.config.column_names.values())
        for attribute_name in attributes:
            attr_value = self.get_attribute_value(element["inner_values"], attribute_name, part_type)    
            if attr_value!= None and attribute_name != 'PIPELINE-REFERENCE':
                row[attribute_name] = attr_value

        
        for k, v in self.get_material_data(element["inner_values"]).items():
            row[k] = v
            
        for k,v in header_values.items():
            row[k] = v
        
                
        if row["PART_TYPE"] == 'PIPE':
            row['QTY_UNITS'] = 'm'
        else:
            row['QTY_UNITS'] = 'STK'

        # removing insulation info for uninsulated components 
        if "INSULATION" in row.index:
            if row["INSULATION"] != "ON":
                row["MISC-SPEC4"] = ""
        else:
            row["MISC-SPEC4"] = ""

        return row
   

    def get_attribute_value(self, inner_values, attribute_name, part_type = ""):
            if attribute_name.upper() in ["X1", "X2", "X3", "Y1", "Y2", "Y3", "Z1", "Z2", "Z3", "DN1", "DN2"]: 
                return self.get_coord_diam(inner_values, attribute_name.upper())
            elif attribute_name.upper() == 'QTY':
                return self.get_qty(inner_values, part_type)
            elif attribute_name.upper() in inner_values.keys():
                return inner_values[attribute_name]
            return None
                
     
    def get_coord_diam(self, inner_values, coord_name):
        coord_index = coord_name[-1]
        coord_name = coord_name[:-1]
                            
        if coord_index == '1':
            if "END-POINT" in inner_values.keys():
                return self.get_coords_from_endpoint(inner_values["END-POINT"], coord_name)
            elif "CENTRE-POINT" in inner_values.keys():  
                return self.get_coords_from_endpoint(inner_values["CENTRE-POINT"], coord_name)
            elif "CO-ORDS" in inner_values.keys():
                return self.get_coords_from_endpoint(inner_values["CO-ORDS"], coord_name)    
            else:
                return ""
        
        if coord_index == '2':
            if "END-POINT_2" in inner_values.keys():
                return self.get_coords_from_endpoint(inner_values["END-POINT_2"], coord_name)
            elif "CO-ORDS_2" in inner_values.keys():
                return self.get_coords_from_endpoint(inner_values["CO-ORDS_2"], coord_name)    
            elif "BRANCH1-POINT" in inner_values.keys():  
                return self.get_coords_from_endpoint(inner_values["BRANCH1-POINT"], coord_name)
            else:
                return ""
        return ""
    
    @lru_cache(maxsize=24)
    def get_coords_from_endpoint(self, end_point, coord_name):
        l = end_point.split()
        if coord_name == "X": return l[0]
        if coord_name == "Y": return l[1]
        if coord_name == "Z": return l[2]
        if coord_name == "DN":
            if len(l) == 4:
                return l[3]
            
        return ""
    
    def get_qty(self, inner_values, part_type):
        if part_type == "PIPE":
            X1 = float(self.get_coord_diam(inner_values, "X1"))
            Y1 = float(self.get_coord_diam(inner_values, "Y1"))
            Z1 = float(self.get_coord_diam(inner_values, "Z1"))
            X2 = float(self.get_coord_diam(inner_values, "X2"))
            Y2 = float(self.get_coord_diam(inner_values, "Y2"))
            Z2 = float(self.get_coord_diam(inner_values, "Z2"))
            pipe_len = math.sqrt((X2-X1)**2 + (Y2-Y1)**2 + (Z2-Z1)**2)
            if self.dim_units == "MM":
                pipe_len = pipe_len/1000

            return pipe_len
        elif part_type == "BOLT":
            return int(inner_values["BOLT-QUANTITY"])       
        else:
            return 1    

    def get_empty_row(self):
        return pd.Series()
    
    def get_material_data(self, inner_values):
        material_data = {}
        
        if 'MATERIAL-IDENTIFIER' in inner_values.keys():
            material_id = inner_values["MATERIAL-IDENTIFIER"]
            materials = self.get_elements_by_section_name("MATERIAL")
            try:
                material_attributes = set(materials[1]["inner_values"].keys()) & set(self.config.column_names.values())
            except IndexError:
                raise IndexError("Error reading material data")         
            
            for material in materials:
                if material['value'] == material_id:
                    for material_attribute in material_attributes:
                        if material_attribute in material['inner_values'].keys():
                            material_data[material_attribute] = material['inner_values'][material_attribute]
        return material_data


    def group_values(self, df):
        group_by_columns = [c for c in self.config.group_by if c in df.columns]
        reduced_columns = group_by_columns + list(set(self.config.aggregate_by) & set(df.columns)) 
        groupped = df.loc[:,reduced_columns].groupby(by = group_by_columns, sort = False, as_index  = False).sum()
        return groupped


    def final_formatting(self, df):
        def sort_fun(part_type):
            if part_type == "PIPE": return 1
            if part_type == "INSTRUMENT": return 3
            if part_type == "BOLT": return 4
            if part_type == "GASKET": return 5
            if part_type == "SUPPORT": return 6
            if part_type == "WELD": return 7
            return 2
                      
        df["TK"] = df["PART_TYPE"].apply(sort_fun)
        df = df.sort_values(by = ['PIPELINE-REFERENCE', 'TK'])
        df = df.drop(['TK'], axis = 1)

        df.QTY = df.QTY.round(2)

        df_new = pd.DataFrame()
        new_columns = [c.upper() for c in self.config.column_names]
        nodes_columns = [self.config.column_names[c].upper() for c in new_columns] 
        for new_name, node_name in zip(new_columns, nodes_columns):
            if node_name in df.columns:
                df_new[new_name] = df[node_name]
           

        return df_new
            

    def excel_export(self):
        if self.df is not None:
            fileName = QFileDialog.getSaveFileName(None,"Select file name to export","","xlsx files (*.xlsx)")
            if fileName[0]:
                self.statusBar.showMessage("Exporting data...")
                self.df.to_excel(fileName[0], sheet_name = "welds", index = False)
                self.statusBar.showMessage("Data exported")

    def excel_bom_format_export(self):
        if self.row_data_df is not None:
            fileName = QFileDialog.getSaveFileName(None,"Select file name to export","","xlsx files (*.xlsx)")
            if fileName[0]:
                self.statusBar.showMessage("Exporting data...")
                with wait_cursor():
                    QtCore.QCoreApplication.processEvents()
                    sheet_name = self.config.bom_options["SHEET_NAME"]
                    file_name =  self.config.bom_file_template
                    start_row = int(self.config.bom_options["START_ROW"])
                    header_row = int(self.config.bom_options["HEADER_ROW"])
                    excel_writer = ExcelWorkBookWriter(file_name, read_only = False)
                    header = excel_writer.get_header(sheet_name, header_row)
                    column_mapping_dict = self.config.bom_column_names
                    excel_writer.update_workbook(sheet_name, self.row_data_df, header, start_row, column_mapping_dict)
                    excel_writer.book.save(fileName[0])  
                msg = 'Writed ' + str(self.row_data_df.shape[0]) + ' to the sheet: ' + sheet_name
                logging.info(msg)
                self.statusBar.showMessage("Data exported")


if __name__ == '__main__':
    log_filename = tempfile.gettempdir() + '/' + "PCF_reader_{}.log".format(time.strftime("%d_%m_%Y_%H_%M_%S"))
    logging.basicConfig(format="%(asctime)s %(name) - 12s %(levelname)-8s %(message)s", level = logging.INFO, filename=log_filename)
       
    appctxt = AppContext()                      # 4. Instantiate the subclass
    QGuiApplication.setOverrideCursor(QCursor(QtCore.Qt.WaitCursor))
    stylesheet = appctxt.get_resource('styles.qss')
    appctxt.app.setStyleSheet(open(stylesheet).read())
    config = Configuration(appctxt)
    appctxt.config = config

    if len(config.column_names) == 0:
        QMessageBox.critical(None, 'Error', "Error in ini file", QMessageBox.Ok)
        sys.exit(-1)   
    
    logging.info('PCF Reader Main Application Started')
    exit_code = appctxt.run()                   # 5. Invoke run()
    sys.exit(exit_code)
import unittest
from main import AppContext
import os
import pandas as pd
from config import Configuration

class MainTests(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(MainTests, self).__init__(*args, **kwargs)
        
        self.app = AppContext()
        config = Configuration(self.app)
        self.app.config = config
       
    
    def test_get_file_names(self):
        file_names = self.app.get_file_names("fixtures\\test_pcfs")
        self.assertCountEqual(file_names, ['fixtures\\test_pcfs\\P49072.PCF','fixtures\\test_pcfs\\LS49047.PCF', 
        'fixtures\\test_pcfs\\C49002.PCF','fixtures\\test_pcfs\\SW49192.PCF'])    
    
    def test_get_section_names(self):
        self.assertEquals("HEADER", self.app.get_section_name("UNITS-BORE"))
        self.assertEquals("PIPELINE", self.app.get_section_name("PIPELINE-REFERENCE"))
        self.assertEquals("WELD", self.app.get_section_name("WELD"))
        self.assertEquals("PART", self.app.get_section_name("ELBOW"))
        self.assertEquals("NOT REPORT", self.app.get_section_name("FLOW-ARROW"))

    def test_parse_file(self):
        nodes = self.app.parse_file('fixtures/test_pcfs/P49072.PCF')
        
        self.assertEqual(len(nodes), 106)

    def test_get_key_value(self):
        k,v = self.app.get_key_value("key    value1  value2")
        self.assertEqual(k, "key")
        self.assertEqual(v, "value1  value2")

    def test_get_header_values(self):
        self.app.nodes = self.app.parse_file('fixtures/test_pcfs/P49072.PCF')
        header_values = self.app.get_header_values()
        self.assertEqual("INCH", header_values["UNITS-BORE"])

    def test_get_pipeline_values(self):
        self.app.nodes = self.app.parse_file('fixtures/test_pcfs/P49072.PCF')
        pipeline_values = self.app.get_pipeline_values()
        self.assertEqual("P49072", pipeline_values["PIPELINE-REFERENCE"])
        self.assertEqual("PU14", pipeline_values["PIPING-SPEC"])

    def test_get_coord_diam(self):
        inner_values = {"CO-ORDS": "42341.0000    86940.9000    101954.8700"}
        self.assertEquals("42341.0000", self.app.get_coord_diam(inner_values, "X1"))
        self.assertEquals("86940.9000", self.app.get_coord_diam(inner_values, "Y1"))
        self.assertEquals("101954.8700", self.app.get_coord_diam(inner_values, "Z1")) 
        inner_values = {"END-POINT": "42341.0000    86940.9000    101954.8700  0.0",
                        "END-POINT_2": "42341.0000    86940.9000    101954.8700 0.0",
                        "END-POINT_3": "1.0000    2.0000    3.0000     1.1"}
        self.assertEquals("3.0000", self.app.get_coord_diam(inner_values, "Z3")) 
        self.assertEquals("1.1", self.app.get_coord_diam(inner_values, "DN3")) 

    def test_get_new_root(self):
        root = self.app.get_new_root("PIPELINE-REFERENCE      P49072")
        self.assertEqual({"name":"PIPELINE-REFERENCE", "section_name": "PIPELINE", "value": "P49072",'inner_values': {}}, root)


    def test_create_one_row(self):
        self.app.nodes = self.app.parse_file('fixtures/test_pcfs/P49072.PCF')
        elements = self.app.get_elements_by_section_name("PIPE")
        header_values = self.app.get_header_values()
        pipeline_values = self.app.get_pipeline_values()
        df = self.app.create_one_row(elements[0], header_values, pipeline_values)
        #print(df.shape)
        self.assertEquals(15, df.shape[0])
    
    def test_create_one_file_df(self):
        self.app.nodes = self.app.parse_file('fixtures/test_pcfs/P49072.PCF')
        self.app.config.section_to_report = ["WELD","PIPE"]
        df = self.app.create_one_file_df()
        self.assertEqual(26, df.shape[0])
        
    def test_get_weld_attributes_from_config(self):
        config = Configuration(self.app)
        self.assertIn("REPEAT-WELD-IDENTIFIER", config.weld_attributes)
    
    def test_check_key_exist_in_values(self):
        values = {"COMPONENT-IDENTIFIER": 44, 
                  "END-POINT": "42509.1500    87090.0000    104692.9800 0.7500",
                  "END-POINT_2": "42798.0300    87090.0000    104692.8300 0.7500"                 
                  }  
        new_k = self.app.check_key_exist_in_values("END-POINT", values, 2)
        self.assertEquals(new_k,'END-POINT_3')    

    def test_get_material_data(self):
        self.app.nodes = self.app.parse_file('fixtures/test_pcfs/P49072.PCF')
        inner_values = {"COMPONENT-IDENTIFIER": 44, 
                  "MATERIAL-IDENTIFIER": "2",
                 }  
        material_data = self.app.get_material_data(inner_values)
        self.assertEquals('DM-551-RF-150', material_data['ITEM-CODE'])

if __name__ == '__main__':
    unittest.main()
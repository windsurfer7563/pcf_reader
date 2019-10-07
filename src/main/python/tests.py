import unittest
from main import AppContext
import os
import pandas as pd
from config import Configuration

class MainTests(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(MainTests, self).__init__(*args, **kwargs)
        
        self.app = AppContext()
       


    #def test_get_folder_name(self):
    #    self.assertEqual(self.app.get_folder_name(), '')
    
    def test_get_file_names(self):
        file_names = self.app.get_file_names("fixtures\\test_pcfs")
        self.assertCountEqual(file_names, ['fixtures\\test_pcfs\\P49072.PCF','fixtures\\test_pcfs\\LS49047.PCF', 
        'fixtures\\test_pcfs\\C49002.PCF','fixtures\\test_pcfs\\SW49192.PCF'])    
       
    def test_parse_file(self):
        nodes = self.app.parse_file('fixtures/test_pcfs/P49072.PCF')
        
        self.assertEqual(len(nodes), 106)

    def test_get_key_value(self):
        k,v = self.app.get_key_value("key    value1  value2")
        self.assertEqual(k, "key")
        self.assertEqual(v, "value1  value2")

    def test_get_header_values(self):
        header_values = {
            "PIPELINE-REFERENCE" : "",
            "UNITS-BORE": "",
            "UNITS-CO-ORDS": "",
            "UNITS-BOLT-LENGTH": "",
            "UNITS-BOLT-DIA": "",
            "UNITS-WEIGHT": "", 
            "UID": ""}
        nodes = self.app.parse_file('fixtures/test_pcfs/P49072.PCF')
        header_values = self.app.get_header_values(nodes, header_values)
        self.assertEqual("P49072", header_values["PIPELINE-REFERENCE"])
               
        self.assertEqual("INCH", header_values["UNITS-BORE"])

    def test_get_pipeline_values(self):
        pipeline_values = {
            "PIPELINE-REFERENCE": "",
            "PL_PIPING_SPEC": "",
            "PL_UID": "",
            "PL_MISC-SPEC1":"",
            "PL_MISC-SPEC2":"",
            "PL_MISC-SPEC3":"",
            "PL_MISC-SPEC4":"",
        }
        nodes = self.app.parse_file('fixtures/test_pcfs/P49072.PCF')
        pipeline_values = self.app.get_pipeline_values(nodes, pipeline_values)
        self.assertEqual("P49072", pipeline_values["PIPELINE-REFERENCE"])
        self.assertEqual("BY PIPING", pipeline_values["PL_MISC-SPEC1"])


    def test_get_new_root(self):
        root = self.app.get_new_root("PIPELINE-REFERENCE      P49072")
        self.assertEqual({"name":"PIPELINE-REFERENCE", "value": "P49072",'inner_values': {}}, root)


    def test_get_node_elements_by_name(self):
        nodes = self.app.parse_file('fixtures/test_pcfs/P49072.PCF')

        elements = self.app.get_node_elements_by_name(nodes,"PIPELINE-REFERENCE")
        self.assertEqual(len(elements),1)

    def test_create_df(self):
        nodes = self.app.parse_file('fixtures/test_pcfs/P49072.PCF')
        df = self.app.create_df(nodes)
        self.assertIsInstance(df, pd.DataFrame)
        self.assertEqual(19, df.shape[0])
        
    def test_get_coords_from_endpoint(self):
        end_point = "42341.0000    86940.9000    101222.1800 0.7500"
        
        x,y,z,dn = self.app.get_coords_from_endpoint(end_point)
        self.assertListEqual(["42341.0000","86940.9000","101222.1800", "0.7500"], [x,y,z,dn])    


    def test_get_weld_attributes_from_config(self):
        config = Configuration(self.app)
        self.assertIn("PIPELINE-REFERENCE", config.weld_attributes)

if __name__ == '__main__':
    unittest.main()
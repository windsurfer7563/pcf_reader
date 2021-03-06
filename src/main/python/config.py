import configparser


class Configuration:

  def __init__(self, app_context):
    try:
      self.config_ini = configparser.ConfigParser()
      self.config_ini.read(app_context.get_resource('config.ini'))
      
      self.section_types = self.config_ini['SECTIONS']['REPORTED_SECTION_TYPES'].split('\n')
      self.section_to_report = self.config_ini['SECTIONS']['REPORT_SECTIONS'].split('\n')
      self.section_not_report = self.config_ini['SECTIONS']['NOT_REPORT_SECTIONS'].split('\n')
      self.header_sections = self.config_ini['SECTIONS']['HEADER_SECTIONS'].split('\n')
      self.pipeline_sections = self.config_ini['SECTIONS']['PIPELINE_SECTIONS'].split('\n')
      self.material_sections = self.config_ini['SECTIONS']['MATERIAL_SECTIONS'].split('\n')

      self.column_names = self.config_ini["COLUMN_NAMES"]
      self.group_by = self.config_ini['AGGREGATION']["GROUP_BY_COLUMNS"].split('\n')
      self.aggregate_by = self.config_ini['AGGREGATION']["AGGREGATE_BY_COLUMNS"].split('\n')
      self.use_aggregation = True if self.config_ini['AGGREGATION']['USE_AGGREGATION'] == 'TRUE' else False

      self.bom_options = self.config_ini["BOM_FILE_OPTIONS"]
      self.bom_column_names = self.config_ini["BOM_COLUMN_NAMES"]

      self.bom_file_template = app_context.get_resource(self.config_ini["BOM_FILE_OPTIONS"]["FILE_NAME"])

    except FileNotFoundError:
      self.error = "File not found"

    


import configparser


class Configuration:

  def __init__(self, app_context):
    try:
      self.config_ini = configparser.ConfigParser()
      self.config_ini.read(app_context.get_resource('config.ini'))
      
      self.pipeline_attributes = self.config_ini['ATTRIBUTES']['PIPELINE_ATTRIBUTES'].split('\n')
      self.weld_attributes = self.config_ini['ATTRIBUTES']['WELD_ATTRIBUTES'].split('\n')
      self.part_attributes = self.config_ini['ATTRIBUTES']['PART_ATTRIBUTES'].split('\n')
      self.pipe_attributes = self.config_ini['ATTRIBUTES']['PIPE_ATTRIBUTES'].split('\n')
      self.instrument_attributes = self.config_ini['ATTRIBUTES']['INSTRUMENT_ATTRIBUTES'].split('\n')
      self.bolt_attributes = self.config_ini['ATTRIBUTES']['BOLT_ATTRIBUTES'].split('\n')
      self.support_attributes = self.config_ini['ATTRIBUTES']['SUPPORT_ATTRIBUTES'].split('\n')
      self.gasket_attributes = self.config_ini['ATTRIBUTES']['GASKET_ATTRIBUTES'].split('\n')
      self.material_attributes = self.config_ini['ATTRIBUTES']['MATERIAL_ATTRIBUTES'].split('\n')

      self.section_types = self.config_ini['SECTIONS']['REPORTED_SECTION_TYPES'].split('\n')
      self.section_to_report = self.config_ini['SECTIONS']['REPORT_SECTIONS'].split('\n')
      self.section_not_report = self.config_ini['SECTIONS']['NOT_REPORT_SECTIONS'].split('\n')
      self.header_sections = self.config_ini['SECTIONS']['HEADER_SECTIONS'].split('\n')
      self.pipeline_sections = self.config_ini['SECTIONS']['PIPELINE_SECTIONS'].split('\n')
      self.material_sections = self.config_ini['SECTIONS']['MATERIAL_SECTIONS'].split('\n')

      self.column_names = self.config_ini["COLUMN_NAMES"]


    except FileNotFoundError:
      self.error = "File not found"

    


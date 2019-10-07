import configparser


class Configuration:

  def __init__(self, app_context):
    try:
      self.config_ini = configparser.ConfigParser()
      self.config_ini.read(app_context.get_resource('config.ini'))
      self.weld_attributes = self.config_ini['ATTRIBUTES']['WELD_ATTRIBUTES'].split('\n')

      
    except FileNotFoundError:
      self.error = "File not found"

    


"""
| __filename__ = "weather.py"
| __coursename__ = "CMSC 495 7381 - Current Trends in Computer Science (2222)"
| __author__ = ["Sheldon Hallal", "Michael Annino", "Chelsey Hillen"]
| __copyright__ = "no copyright"
| __credits__ = ["Sheldon Hallal", "Michael Annino", "Chelsey Hillen"]
| __license__ = "no license"
| __version__ = "1.0.0"
| __maintainer__ = ["Sheldon Hallal", "Michael Annino", "Chelsey Hillen"]]
| __email__ = ["smhallal@gmail.com", "mannino@student.umgc.edu" , "clhillen1@yahoo.com" ]
| __status__ = "Baseline"
| __docformat__ = 'reStructuredText'

:blackboldunderline:`REQUIREMENTS:`

    * Retrieve Weather Data from API

        * Retrieves Daily Forecast(3 days)

        * Retrieves Hourly Forecast(10 hours)

        * Store Weather Data in Weather Object

    * Check if host machine has an internet connection

    * Check if user location input is valid

"""

####################################################################
# Imports
####################################################################
import datetime
import json
import time
from configparser import ConfigParser, NoSectionError
from datetime import timedelta
import geocoder
import pytz
import requests
from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Config, Window
from kivy.properties import DictProperty, ListProperty, StringProperty

####################################################################
# API and URL Info
####################################################################
API = '6dbf96c62daf4869844214624221104'

####################################################################
# Widget Defaults
####################################################################
Window.size = (675, 400)
Window.minimum_width, Window.minimum_height = (400, 400)
Config.set('input', 'mouse', 'mouse,multitouch_on_demand')
Window.set_system_cursor('hand')
Window.set_icon('DATA/icon.png')


def read_config_parser(instance):
    """ Function read_config_parser - opens config.ini and reads value for the instance parameter
    and returns the attribute.

    :param instance: String - Attribute requested to be parsed from the config.ini
    :rtype: String
    :return: Value for requested variable
    """
    try:
        parser = ConfigParser()
        parser.read('config.ini')
        return parser.get('USER_INFO', instance)

    except NoSectionError:
        filename = 'DATA/config.ini'
        parser = ConfigParser()
        parser.read(filename)
        return parser.get('USER_INFO', instance)


def get_ip_data():
    """ Function get_ip_data - looks up user IP and determines location. Returns the city, state,
    and country as a string.

    :rtype: String
    :return: Location City, Region, Country based on IP location
    """
    ip_data = geocoder.ip('me')
    return ip_data.address


def save_config():
    """ Function save_config - Saves the currents values for WeatherApp.user_config in the
    config.ini file.
    :return: **NONE**
    """
    config = ConfigParser()
    config['USER_INFO'] = {
        'setup': WeatherApp.user_config.setup,
        'ip': WeatherApp.user_config.ip,
        'location': WeatherApp.user_config.location,
        'temp': WeatherApp.user_config.temp,
        'wind': WeatherApp.user_config.wind,
        'clock': WeatherApp.user_config.hour
    }
    with open('DATA/config.ini', 'w', encoding='utf-8') as conf:
        config.write(conf)


class UserSettings:
    """ Class UserSettings - creates a UserSettings object from the values saved in the config file.
    """
    location = read_config_parser('location')
    temp = read_config_parser('temp')
    wind = read_config_parser('wind')
    hour = read_config_parser('clock')
    ip = bool(read_config_parser('ip') == 'True')
    setup = read_config_parser('setup')


class WeatherApp(App):
    """ Class Weather: Builds and maintains the weather object. Declares property variables
    for the GUI Labels
    """
    clock = StringProperty()
    weather_data = DictProperty()
    weather_current = DictProperty()
    weather_forecast = ListProperty()
    weather_location = StringProperty()
    current_temp = StringProperty()
    current_wind = StringProperty()
    hour_image = ListProperty()
    hour_display = ListProperty()
    hour_condition = ListProperty()
    day_display = ListProperty()
    user_config = UserSettings()

    def __init__(self, **kwargs):
        """ __init__: Initial setup of the weather object.

        location attribute: City or Zipcode of the user's location. Defaulted to 'Washington, DC'.
        :param  **kwargs: Arbitrary keyword arguments.
        :return: **NONE**
        """
        super().__init__(**kwargs)
        self.hour_condition = ['', '', '', '', '', '', '', '', '', '']
        self.hour_image = ['', '', '', '', '', '', '', '', '', '']
        self.hour_display = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        self.day_display = ['', '', '']
        self.weather_data = {}
        self.fetch()

    def build(self):
        """ Function build: Builds widget. Schedule fetch() function to repeat every 10 seconds.

        :return: super().build()
        """
        self.update_hour()
        self.update_day()
        Clock.schedule_interval(lambda dt: self.update_clock(), 30)
        Clock.schedule_interval(lambda dt: self.fetch(), 60)
        return super().build()

    def checkbox_click(self, checkbox, option, value):
        """ Function checkbox_clock - Changes attributes of user_config based on parameters passed
        from the GUI options menu. Calls the function to update labels in GUI.

        :param checkbox: True/False - checkbox checked or unchecked
        :param option: (ip,temp,wind,hour) attribute to be modified
        :param value: the new value for the attribute
        :return: **NONE**
        """
        if checkbox:
            options = {
                'ip': 'ip',
                'temp': 'temp',
                'wind': 'wind',
                'hour': 'hour'
            }
            selection = options.get(option)
            setattr(self.user_config, selection, value)

        else:
            if option == 'ip':
                setattr(self.user_config, 'ip', value)

        if checkbox:
            options = {
                'ip': self.fetch,
                'temp': self.update_temp,
                'wind': self.update_wind,
                'hour': self.update_clock
            }
            selection = options.get(option, None)
            selection()

        if option == 'hour':
            self.update_hour_display()

        save_config()

    def get_time(self):
        """ Function get_time: Retrieves current epoch time and retrieves the API time zone.
            The function uses the epoch and time zone to create local datetime and returns it.

        :return date_time: Returns datetime timestamp with the appropriate time and timezone
        """
        if self.weather_data == '':
            time_zone = pytz.timezone('UTC')
        else:
            time_zone = pytz.timezone(self.weather_data['location']['tz_id'])

        current_time = int(time.time())

        date_time = datetime.datetime.fromtimestamp(current_time, time_zone)
        return date_time

    def get_hour(self):
        """ Function get_hour: Retrieves datetime from get_time(), extracts and converts the
        24-Hour attribute into an Integer and returns the value.

        :rtype: Integer
        :return: Returns current hour(0-23)
        """
        date_time = self.get_time()
        hour = int(date_time.strftime("%H"))

        return hour

    def update_all(self):
        """ Function update_all: Calls all functions to update weather app.
        :return: **NONE**
        """
        self.update_location()
        self.update_clock()
        self.update_day()
        self.update_temp()
        self.update_wind()
        self.update_hour()

    def update_temp(self):
        """ Function update_temp - updates the user_config.temp attribute with the fahrenheit or
        celsius values from weather_current dictionary.

        :return: **NONE**
        """
        if self.user_config.temp == 'feelslike_c':
            temp = str(self.weather_current[self.user_config.temp]) + '\u00B0C'
            setattr(self, 'current_temp', temp)

        else:
            temp = str(self.weather_current[self.user_config.temp]) + '\u00B0F'
            setattr(self, 'current_temp', temp)

    def update_wind(self):
        """ Function update_temp - updates the user_config.temp attribute with the fahrenheit or
        celsius values from weather_current dictionary.
        :return: **NONE**
        """
        if self.user_config.wind == 'wind_mph':
            wind = str(self.weather_current[self.user_config.wind]) + ' mph'
            setattr(self, 'current_wind', wind)

        else:
            wind = str(self.weather_current[self.user_config.wind]) + ' km/h'
            setattr(self, 'current_wind', wind)

    def update_clock(self):
        """ Function update_clock: Retrieves current local datetime from get_time(), formats the
        clock. Uses the clock_type variable to return the appropriate time format to the
        clock on the GUI.

        :return: **NONE**
        """
        date_time = self.get_time()

        day_date = date_time.strftime("%a, %b %d")
        time_12 = date_time.strftime("%#I:%M %p")
        time_24 = date_time.strftime("%H:%M")

        if self.user_config.hour == '12':
            self.clock = str(day_date + '\r' + time_12)

        else:
            self.clock = str(day_date + '\r' + time_24)

    def get_city(self):
        """ Function get_city: gets the name attribute from weather_data dictionary.

        :rtype: string
        :return: Returns the city
        """
        return self.weather_data['location']['name']

    def get_state(self):
        """ Function get_state: gets the region attribute from weather_data dictionary.

        :rtype: string
        :return: Returns the state
        """
        return self.weather_data['location']['region']

    def get_county(self):
        """ Function get_county: gets the country attribute from weather_data dictionary.

        :rtype: string
        :return: Returns the country
        """
        return self.weather_data['location']['country']

    def update_location(self):
        """ Function update_location: Checks if time_zone is America and sets the weather_location
        variable accordingly. If the location is in America, weather_location is set to city, state.
        Otherwise, weather_location = city, country.

        :return: **None**
        """
        if 'America' in self.weather_data['location']['tz_id']:
            self.weather_location = str(f'{self.get_city()}, {self.get_state()}')

        else:
            self.weather_location = str(f'{self.get_city()}, {self.get_county()}')

    def update_day(self):
        """ Function update_day: Retrieves datetime timestamp from get_time(), formats the
        datetime(Day, MMM DD), and assigns the three days to the list variable day_display.

        :return: **NONE**
        """
        for i in range(3):
            date_time = self.get_time() + timedelta(days=i)
            self.day_display[i] = date_time.strftime("%a, %b %d")

    def update_hour(self):
        """ Function update_hour: Calls the following functions to update the hourly weather
        variables.

        :return: **NONE**
        """
        self.update_hour_display()
        self.update_hour_forecast()
        self.update_hour_image()

    def update_hour_forecast(self):
        """ Function update_hour_forecast: Gets the current hour from get_hour(), iterates through
        the next 10-hours, and sets the current condition in the list variable hour_condition. If
        an IndexError occurs, function moves to the next day(00:00).

        :return: **NONE**
        """
        for i in range(10):
            hour = self.get_hour() + i
            try:
                data = self.weather_forecast[0]['hour'][hour]
                self.hour_condition[i] = str(data['condition']['text'])
            except IndexError:
                data = self.weather_forecast[1]['hour'][hour - 24]
                self.hour_condition[i] = str(data['condition']['text'])

    def update_hour_display(self):
        """ Function update_hour_display: Gets the current hour from get_hour(), iterates through
        the next 10-hours, and sets the current condition in the list variable hour_display. If
        an IndexError occurs, function moves to the next day(00:00). Function checks if clock_type
        is either 12-hour or 24-hour format.

        :return: **NONE**
        """
        if self.user_config.hour == '12':

            for i in range(10):
                hour = self.get_hour() + i

                if hour < 24:
                    if hour == 0:
                        self.hour_display[i] = str(hour + 12) + ' AM'
                    elif hour < 12:
                        self.hour_display[i] = str(hour) + ' AM'
                    elif hour == 12:
                        self.hour_display[i] = str(hour) + ' PM'
                    else:
                        self.hour_display[i] = str(hour - 12) + ' PM'

                else:
                    if hour == 24:
                        self.hour_display[i] = str(hour - 12) + ' AM'
                    else:
                        self.hour_display[i] = str(hour - 24) + ' AM'
        else:
            for i in range(10):
                hour = self.get_hour() + i
                if hour < 24:
                    if hour < 10:
                        self.hour_display[i] = '0' + str(hour) + ':00'
                    else:
                        self.hour_display[i] = str(hour) + ':00'
                else:
                    self.hour_display[i] = '0' + str(hour - 24) + ':00'

    def update_hour_image(self):
        """ Function update_hour_display: Gets the current hour from get_hour(), iterates through
        the next 10-hours, and sets the image url in the list variable hour_image. If
        an IndexError occurs, function moves to the next day(00:00).

        :return: **NONE**
        """
        for i in range(10):
            hour = self.get_hour() + i

            try:
                data = self.weather_forecast[0]['hour'][hour]
                self.hour_image[i] = str('https:' + data['condition']['icon'])

            except IndexError:
                data = self.weather_forecast[1]['hour'][hour - 24]
                self.hour_image[i] = str('https:' + data['condition']['icon'])

    def read_input(self, location_update):
        """ Function read_input: User inputs location data into text field. On enter, function is
        activated to update the location attribute, and calls fetch to update API and labels.

        :param location_update: passes user input for desired location

        :return: **NONE**
        """
        try:
            setattr(self.user_config, 'location', location_update.text)
            setattr(self.user_config, 'ip', False)
            self.fetch()

        except AttributeError:
            pass

    def fetch(self):
        """
        Function fetch: Takes location variable and retrieves information from the Open Weather
        API. Information is saved to the weather_data attribute.

        :return:  **NONE**
        """
        if self.user_config.ip:
            location = get_ip_data()
        else:
            location = self.user_config.location

        try:
            url = f'https://api.weatherapi.com/v1/forecast.json?key={API}&q=' + \
                  f'{location}&days=3&aqi=yes&alerts=yes'

            if 'error' in requests.get(url).json():
                setattr(self.user_config, 'location', self.weather_location)

            else:
                setattr(self, 'weather_data', requests.get(url).json())
                setattr(self, 'weather_current', self.weather_data['current'])
                setattr(self, 'weather_forecast', self.weather_data['forecast']['forecastday'])
                setattr(self.user_config, 'location', location)
                self.update_all()

                save_config()

        except requests.exceptions.ConnectionError:
            if not self.weather_data:
                filename = 'DATA/default.json'
                with open(filename, encoding="utf8") as json_file:
                    self.weather_data = json.load(json_file)

                setattr(self, 'weather_current', self.weather_data['current'])
                setattr(self, 'weather_forecast', self.weather_data['forecast']['forecastday'])
                setattr(self.user_config, 'location', location)
                self.update_all()

            else:
                pass


if __name__ == "__main__":
    WeatherApp().run()

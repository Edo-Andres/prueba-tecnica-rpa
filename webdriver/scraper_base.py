import os

from time import sleep
from typing import Union, List, Dict
from selenium import webdriver
from selenium.webdriver.common.alert import Alert
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
from pyvirtualdisplay import Display
from .driver_factory import DriverFactory



class ScraperBase():

    driver = None
   

    def get_driver(self,
                   browser: str ='chrome',
                   options: webdriver.ChromeOptions = None,
                   prefs: dict = None
                   ):
        # Comentar o eliminar la lógica que llama a _gui
        # if os.getenv('ENV') != 'development' and not bool(os.getenv('HEADLESS')):
        #     self._gui()
        self.driver = DriverFactory().get_driver(browser=browser,
                                                 options=options,
                                                 prefs=prefs)

    def _gui(self):
        os.environ["DISPLAY"] = f':{self.psql_id}'
        display = Display(visible=0, size=(1024, 768))
        display.start()
        sleep(10)

    def driver_wait_by_alert(self, time: int=10):
        return WebDriverWait(self.driver, time).until(ec.alert_is_present())

    def driver_wait_by_visibility(
        self,
        element: str,
        element_type: str,
        time: int = 10
    ) -> WebDriverWait:
        waiter = self._expected_conditions_getter(element_type, element, 'visibility')
        return self._waiter(waiter, time, True)

    def driver_wait_disappear_by_visibility(
        self,
        element: str,
        element_type: str,
        time: int = 10
    ) -> WebDriverWait:
        waiter = self._expected_conditions_getter(element_type, element, 'visibility')
        return self._waiter(waiter, time, False)

    def driver_wait_by_presence(
        self,
        element: str,
        element_type: str,
        time: int = 10
    ) -> WebDriverWait:
        waiter = self._expected_conditions_getter(element_type, element, 'presence')
        return self._waiter(waiter, time, True)

    def driver_wait_disappear_by_presence(
        self,
        element: str,
        element_type: str,
        time: int = 10
    ) -> WebDriverWait:
        waiter = self._expected_conditions_getter(element_type, element, 'presence')
        return self._waiter(waiter, time, False)

    def driver_wait_disappear_by_all_presences(
        self,
        element: str,
        element_type: str,
        time: int=10
    ) -> WebDriverWait:
        waiter = self._expected_conditions_getter(element_type, element, 'all_presence')
        return self._waiter(waiter, time, False)

    def driver_wait_by_clickable(
        self,
        element: str,
        element_type: str,
        time: int=10
    ) -> WebDriverWait:
        waiter = self._expected_conditions_getter(element_type, element, 'clickable')
        return self._waiter(waiter, time, True)

    @classmethod
    def _expected_conditions_getter(cls, element_type: str, element: str, located: str) -> ec:
        _condition = None
        _by = getattr(By, element_type)
        if located == 'visibility':
            _condition = ec.visibility_of_element_located
        if located == 'presence':
            _condition = ec.presence_of_element_located
        if located == 'all_presence':
            _condition = ec.presence_of_all_elements_located
        if located == 'clickable':
            _condition = ec.element_to_be_clickable
        return _condition((_by, element))

    def _waiter(self, waiter: ec, time: int, presence: bool) -> WebDriverWait:
        driver_waiter = WebDriverWait(self.driver, time)
        if presence:
            return driver_waiter.until(waiter)
        return driver_waiter.until_not(waiter)

    @classmethod
    def driver_select(cls, element):
        return Select(element)

    @classmethod
    def driver_alert(cls, element):
        return Alert(element)

    @classmethod
    def clean_and_fill_input(cls, element, data):
        element.clear()
        element.send_keys(data)

    def free_driver(self):
        if self.driver:
            self.driver.quit()

    def switch_to_frame(self, frame: str):
        self.driver.switch_to.default_content()
        self.driver.switch_to.frame(frame)

    def get_all_cookies(self) -> List[Dict]:
        # Get cookies using Chrome DevTools Protocol (CDP)
        # Get all cookies even the HttpOnly marked
        cookies = self.driver.execute_cdp_cmd('Network.getAllCookies', {})
        return cookies["cookies"]

    def get_local_storage_by_key(self, key: str) -> Union[dict, str]:
        return self.driver.execute_script(f"return window.localStorage.getItem('{key}');")

    def get_session_storage_by_key(self, key: str) -> Union[dict, str]:
        return self.driver.execute_script(f"return window.sessionStorage.getItem('{key}');")

    def get_all_local_storage_data(self) -> dict:
        script = "return Object.fromEntries(Object.entries(window.localStorage));"
        return self.driver.execute_script(script)

    def get_all_session_storage_data(self) -> dict:
        script = "return Object.fromEntries(Object.entries(window.sessionStorage));"
        return self.driver.execute_script(script)

    def set_session_storage_variable(self, key: str, value) -> None:
        # Execute JavaScript to set a variable in sessionStorage
        script = f"window.sessionStorage.setItem('{key}', '{value}');"
        self.driver.execute_script(script)
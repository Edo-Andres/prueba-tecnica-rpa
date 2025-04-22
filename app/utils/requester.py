import json

import requests
from selenium.webdriver.chrome.webdriver import WebDriver


class Requester:
    def __init__(self, driver: WebDriver):
        self.driver = driver
        self.session = requests.Session()

    
    def get_headers(self, flow: str) -> dict:
        headers = {}
        return headers

    def set_cookies(self) -> None:
        for cookie in self.driver.get_cookies():
            self.session.cookies.set(cookie["name"], cookie["value"])

    def request(
        self,
        request: str,
        flow: str,
        payload: dict = None,
    ) -> requests.Response:
        self.set_cookies()
        http_method = getattr(self.session, request)
        return http_method(
            url=self.get_url(flow),
            headers=self.get_headers(flow),
            data=json.dumps(payload) if payload else payload,
        )

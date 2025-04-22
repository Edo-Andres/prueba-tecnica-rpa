from webdriver.scraper_base import ScraperBase



class BancoScraper(ScraperBase):
    def __init__(
        self,
        date_range: dict,
        usuario: str,
        password: str,
        account:str
    ):
        self.since = date_range["since"] 
        self.until = date_range["until"]
        self.usuario = usuario
        self.password = password
        self.account = account
        self.result = {}

    def execute(self) -> dict:
        self.get_driver()
        if self.login() and self.exists_account():
            self.obtain_documents()
        return self.result

    def login(self) -> bool:
        is_valid = False
        #Codigo para hacer login
        return is_valid

    def exists_account(self) -> bool:
        #codigo para verificar que existe la cuenta
        pass

    def obtain_documents(self) -> None:
        #aqui tcodigo para obtener los movimientos
        pass

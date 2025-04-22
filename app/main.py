from .controller import BancoScraper

def handle(event) -> dict:
    scraper = BancoScraper(
        event["date_range"],
        event["usuario"],
        event["password"],
        event["account"]
    )
    scraper.execute()
    print("After execute")

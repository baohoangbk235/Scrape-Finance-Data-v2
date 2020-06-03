# Used for getting the list of all companies

# catID: san giao dich (HOSE: 1, HNX: 2, etc.)
# industryID: chon nganh (danh sach co the duoc lay tu request Industry List (category 1) tren Postman
# businessTypeID: loai hinh doanh nghiep (danh sach lay tu request Business Type for Corporate A-Z) tren Postman
# type: tabs (A-Z, Danh sach CK dang NY/GD, Niem yet moi/DKGD moi, etc.)

import fad_crawl.spiders.models.constants as constants
import fad_crawl.spiders.models.utilities as utilities
import redis


r = redis.Redis(decode_responses=True)


name = "corporateAZ"


tickers_redis_key = ["financeInfo:tickers"]


scraper_api_key = constants.SCRAPER_API_KEY


data = {"url": "https://finance.vietstock.vn/data/corporateaz",
        "formdata": {
            "catID": constants.CAT_ID,
            "industryID": constants.INDUSTRY_ID,
            "page": constants.START_PAGE,
            "pageSize": constants.PAGE_SIZE,
            "type": "0",
            "code": "",
            "businessTypeID": constants.BUSINESSTYPE_ID,
            "orderBy": "Code",
            "orderDir": "ASC"
        },
        "headers": {
            "User-Agent": constants.USER_AGENT,
            "Content-Type": constants.CONTENT_TYPE
        },
        "cookies":  {
            "language": constants.LANGUAGE,
            "vts_usr_lg": constants.USER_COOKIE
        },
        "meta": {
            'pageid': "",
            # "proxy": f'http://scraperapi:{scraper_api_key}@proxy-server.scraperapi.com:8001',
        },
        "proxies": {
            "http": "127.0.0.1:8118",
            "https": "127.0.0.1:8118", }
        }
        


log_settings = utilities.log_settings(spiderName=name,
                                      log_level = "INFO")

middlewares_settings={
    'DOWNLOADER_MIDDLEWARES': {
        'rotating_proxies.middlewares.RotatingProxyMiddleware': 610,
        'rotating_proxies.middlewares.BanDetectionMiddleware': 620,
    }
}

proxy_settings = {
    # 'ROTATING_PROXY_LIST': r.lrange(constants.PROXIES_REDIS_KEY, 0, -1)
    'ROTATING_PROXY_LIST': ["127.0.0.1:8118"],
}

settings = {**log_settings, **middlewares_settings, **proxy_settings}

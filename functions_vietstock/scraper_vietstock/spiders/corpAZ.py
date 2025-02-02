
# This spider crawls the list of company names (tickers) on Vietstock,
# feeds the list to the Redis server for other Spiders to crawl

import json
import logging
import os
import sys
import traceback

import redis
import scrapy
from scrapy import FormRequest, Request
from scrapy.crawler import CrawlerRunner
from scrapy.utils.log import configure_logging
from scrapy_redis.spiders import RedisSpider
from twisted.internet import reactor

import scraper_vietstock.spiders.models.constants as constants
import scraper_vietstock.spiders.models.utilities as utilities
from scraper_vietstock.spiders.models.constants import REDIS_HOST
from scraper_vietstock.spiders.models.corporateaz import (business_type,
                                                  closed_redis_key)
from scraper_vietstock.spiders.models.corporateaz import data as az
from scraper_vietstock.spiders.models.corporateaz import (industry_list, name_express,
                                                  name_regular,
                                                  settings_express,
                                                  settings_regular,
                                                  tickers_redis_keys)
from scraper_vietstock.spiders.pdfDocs import pdfDocsHandler


TEST_TICKERS_LIST = ["AAA", "A32", "VIC"]
TEST_NUM_PAGES = 2


class corporateazHandler(scrapy.Spider):
    name = name_regular
    custom_settings = settings_regular

    def __init__(self, tickers_list="", *args, **kwargs):
        super(corporateazHandler, self).__init__(*args, **kwargs)
        self.r = redis.Redis(host=REDIS_HOST, decode_responses=True)
        self.r.set(closed_redis_key, "0")
        self.statusfilepath = f'run/scrapy/{self.name}.scrapy'
        os.makedirs(os.path.dirname(self.statusfilepath), exist_ok=True)
        with open(self.statusfilepath, 'w') as statusfile:
            statusfile.write('running')
            statusfile.close()

    def start_requests(self):
        req = FormRequest(url=az["url"],
                          formdata=az["formdata"],
                          headers=az["headers"],
                          cookies=az["cookies"],
                          meta=az["meta"],
                          callback=self.parse,
                          errback=self.handle_error)
        yield req

    def parse(self, response):
        if response:
            page = int(response.meta['page'])
            total_pages = response.meta['TotalPages']
            try:
                res = json.loads(response.text)
                tickers_list = [d["Code"]
                                for d in res]
                self.logger.info(
                    f'Found these tickers on page {page}: {str(tickers_list)}')

                ### For financeInfo
                ### Push the value ticker;1 to financeInfo to initiate its requests
                financeInfo_tickers = [f'{t};1' for t in tickers_list]
                self.r.lpush(tickers_redis_keys[0], *financeInfo_tickers)

                ### For other FAD Spiders
                ### Push the tickers list to Redis key of other Spiders
                for k in tickers_redis_keys[1:]:
                    # FOR TESTING PURPOSE
                    # if self.r.llen(k) <= 3:
                    self.r.lpush(k, *tickers_list)

                # Total pages need to be calculated or delivered from previous request's meta
                # If current page < total pages, send next request
                total_pages = res[0]['TotalRecord'] // int(
                    constants.PAGE_SIZE) + 1 if total_pages == "" else int(total_pages)

                if page < total_pages:
                    next_page = str(page + 1)
                    az["formdata"]["page"] = next_page
                    az["meta"]["page"] = next_page
                    az["meta"]["TotalPages"] = str(total_pages)
                    req_next = FormRequest(url=az["url"],
                                           formdata=az["formdata"],
                                           headers=az["headers"],
                                           cookies=az["cookies"],
                                           meta=az["meta"],
                                           callback=self.parse,
                                           errback=self.handle_error)
                    yield req_next
            except:
                self.logger.info("Response cannot be parsed by JSON")
        else:
            self.logger.info("Response is null")

    def closed(self, reason="CorporateAZ Finished"):
        self.r.set(closed_redis_key, "1")
        self.close_status()
        self.logger.info(
            f'Closing... Setting closed signal value to {self.r.get(closed_redis_key)}')
        self.logger.info(
            f'Tickers have been pushed into {str(tickers_redis_keys)}')        

    def handle_error(self, failure):
        pass

    def close_status(self):
        """Clear running status file after closing
        """
        if os.path.exists(self.statusfilepath):
            os.remove(self.statusfilepath)
            self.logger.info(f'Deleted status file at {self.statusfilepath}')

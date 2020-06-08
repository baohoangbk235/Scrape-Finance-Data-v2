# -*- coding: utf-8 -*-
# This spider crawls a stock ticker's associated companies/subsidiaries

import json
import logging
import os
import sys
import traceback

import redis
import scrapy
from scrapy import FormRequest
from scrapy.crawler import CrawlerProcess
from scrapy.utils.log import configure_logging
from scrapy_redis import defaults
from scrapy_redis.spiders import RedisSpider
from scrapy_redis.utils import bytes_to_str
from scrapy_redis.spiders import RedisSpider

import fad_crawl.spiders.models.utilities as utilities
from fad_crawl.spiders.models.associatesdetails import data as ass
from fad_crawl.spiders.models.associatesdetails import name, settings, report_types
from fad_crawl.spiders.fadRedis import fadRedisSpider
from fad_crawl.helpers.fileDownloader import save_jsonfile


class associatesHandler(fadRedisSpider):
    name = name
    custom_settings = settings

    def __init__(self, *args, **kwargs):
        super(associatesHandler, self).__init__(*args, **kwargs)
        self.ass = ass
        self.report_types = report_types

    def next_requests(self):
        """Replaces the default method. Closes spider when tickers are crawled and queue empty.
        Customizing this method from fadRedis Spider because it has the Page param. in formdata.
        """

        use_set = self.settings.getbool('REDIS_START_URLS_AS_SET', defaults.START_URLS_AS_SET)
        fetch_one = self.server.spop if use_set else self.server.lpop
        found = 0
        while found < self.redis_batch_size:
# Fetch one ticker from Redis list, mark all reports for this ticker as unfinished
            data = fetch_one(self.redis_key)
            if not data:
                break
            self.ticker_finish = {report_type: False for report_type in report_types}
            for report_type in self.report_types:
# For each report type, begin while loop with Page number
                pg = 1
                while self.ticker_finish[report_type] is False:
                    req = self.make_request_from_data(data, report_type, page=str(pg))
                    if req:
                        yield req
                        found += 1
                        dq = self.r.incr(self.dequeued_count_key)
                        self.logger.info(f'Dequeued {dq} ticker-report-page so far')
                    else:
                        self.logger.info("Request not made from data: %r", data)
                    pg += 1
                    
# If this report type is finished, break while loop
                    if self.ticker_finish[report_type] is True:
                        break

# Log number of requests consumed from Redis feed
        if found:
            self.logger.debug("Read %s requests from '%s'", found, self.redis_key)

# Close spider if none in queue and amount crawled == amount dequeued
        if self.r.get(self.crawled_count_key) and self.r.get(self.dequeued_count_key):
            if self.r.llen(self.redis_key) == 0 and self.r.get(self.crawled_count_key) >= self.r.get(self.dequeued_count_key):
                self.r.delete(self.crawled_count_key)
                self.r.delete(self.dequeued_count_key)
                self.crawler.engine.close_spider(spider=self, reason="Queue is empty, the spider closes")

    def make_request_from_data(self, data, report_type, page):
        """
        Replaces the default method, data is a ticker.
        """
        ticker = bytes_to_str(data, self.redis_encoding)

        self.ass["formdata"]["code"] = ticker
        self.ass["meta"]["ticker"] = ticker
        self.ass["meta"]["ReportType"] = report_type
        self.ass["meta"]["Page"] = page

        return FormRequest(url=ass["url"],
                            formdata=ass["formdata"],
                            headers=ass["headers"],
                            cookies=ass["cookies"],
                            meta=ass["meta"],
                            callback=self.parse
                            )
    
    def parse(self, response):
        if response:
# If response is not an empty string, save it
            try:
                resp_json = json.loads(response.text)
                ticker = response.meta['ticker']
                report_type = response.meta['ReportType']
                page = response.meta['Page']

                save_jsonfile(resp_json,
                        filename=f'localData/{self.name}/{ticker}_Page_{page}.json')
                
                c = self.r.incr(self.crawled_count_key)
                self.logger.info(f'Crawled {c} ticker-report-page so far')

# If it is an empty string, then we've finished the report type             
            except:
                self.ticker_finish[report_type] = True
                self.logger.info("Response is an empty string")

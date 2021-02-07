# -*- coding: utf-8 -*-
import scrapy
from imgspider.items import ImgItem
import json
from pixivpy3 import *
from scrapy.utils.project import get_project_settings

def gt(hosts):
    api = ByPassSniApi()
    api.hosts = hosts
    api.set_auth("","")
    api.auth()
    return api.access_token
#scrapy crawl pixiv

class PixivSpider(scrapy.Spider):
    name = 'pixiv'
    allowed_domains = ['*']
    host = 'https://210.140.131.226'
    access_token = ''
    def start_requests(self):
        start = self.settings.get("START")
        stop = self.settings.get("STOP")
        for offset in range(start,stop):
            offset *= 30
            headers = {'App-OS':'ios',
                   'App-OS-Version':'12.2',
                   'App-Version':'7.6.2',
                   'host': 'app-api.pixiv.net',
                   'User-Agent':'PixivIOSApp/7.6.2 (iOS 12.2; iPhone9,1)',
                   'Authorization':'Bearer %s' % self.access_token}
            url = "%s/v1/illust/ranking?mode=day&filter=for_ios&offset=%s"%(self.host,offset)
            yield scrapy.Request(url=url,headers = headers,
            callback=self.dealImg,dont_filter = True)

    def dealImg(self,response):
        if response.status == 400:
            self.access_token = gt(self.host)
            headers = {'App-OS':'ios',
                   'App-OS-Version':'12.2',
                   'App-Version':'7.6.2',
                   'host': 'app-api.pixiv.net',
                   'User-Agent':'PixivIOSApp/7.6.2 (iOS 12.2; iPhone9,1)',
                   'Authorization':'Bearer %s' % self.access_token}
            yield scrapy.Request(url=response.url,headers = headers,
            callback=self.dealImg,dont_filter = True)
            
        
        jsonres = json.loads(response.text)
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.99 Safari/537.36',
            'Referer': 'https://www.pixiv.net/'
        }
        if "error" in jsonres:
            return 
        
        for ajson in jsonres["illusts"]:
            pid = ajson["id"]
            if ajson["meta_single_page"]:
                url = ajson["image_urls"]["medium"]
                yield scrapy.Request(url=url, meta={'pid': pid, 'page': 0},headers = headers,
                        callback=self.parse,dont_filter = True)
            else:
                urls = ajson["meta_pages"]
                for page, aurl in enumerate(urls):
                    url = aurl["image_urls"]["medium"]
                    yield scrapy.Request(url=url, meta={'pid': pid, 'page': page},headers = headers,
                        callback=self.parse,dont_filter = True)

    def parse(self, response):
        pid = response.meta['pid']
        item = ImgItem()
        item["pid"] = pid
        item["page"] = response.meta['page']
        item["image"] = response.body
        return item
        

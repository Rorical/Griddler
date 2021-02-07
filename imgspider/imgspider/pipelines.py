# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html

from scrapy.utils.project import get_project_settings
import sys
sys.path.append('/var/service/griddler')

import pimg

class ImgspiderPipeline(object):
    def open_spider(self, spider):
        self.settings = get_project_settings()
        self.pimg = pimg.Pimg('/var/service/griddler/config.ini')

    def close_spider(self, spider):
        del self.pimg

    def process_item(self, item, spider):
        self.pimg.insert(item["pid"], item["image"], item["page"])
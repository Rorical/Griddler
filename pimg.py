import numpy as np
import tensorflow as tf
from PIL import Image
from milvus import Milvus, IndexType, MetricType
import pymongo
from io import BytesIO
import requests
import re
import thumbnail
Image.MAX_IMAGE_PIXELS = None
from configparser import ConfigParser
import zerorpc

class Pimg():
    def __init__(self, configpath = "config.ini"):
        config = ConfigParser()
        config.read(configpath,encoding="utf-8")
        self.mcol = config["common"]["name"]
        self.dbclient = pymongo.MongoClient(config["mongodb"]["uri"])
        self.db = self.dbclient[config["mongodb"]["db"]]
        self.milvus = Milvus(uri=config["milvus"]["uri"])
        self.model = tf.keras.applications.EfficientNetB7(
            include_top=False, weights='imagenet', input_tensor=None,
            input_shape=None, pooling=None, classes = 1000,
            classifier_activation='softmax'
        )
        if not self.milvus.has_collection(self.mcol)[1]:
            self.milvus.create_collection({'collection_name':self.mcol, 'dimension':2304, 'index_file_size':2048, 'index_type': IndexType.IVF_SQ8, 'metric_type':MetricType.L2})
        self.filter = zerorpc.Client()
        self.filter.connect("tcp://127.0.0.1:" + config["cuckoo"]["port"])
        #self.filter = cfilter.cfilter(config["cuckoo"]["file"])
        
        self.topk = config["common"].getint("topk")
        self.thumbnail = thumbnail.thumbnail(
                config["minio"]["domain"], config["minio"].getboolean("encrypt"), config["minio"].getint("thumbnail_size"), config["minio"]["bucket"],
                config["minio"]["access_key"], config["minio"]["secret_key"]
                )
        self.filesurl = "%s/%s/" % (config["common"]["filesurl"], self.thumbnail.bucket)
        self.milvus_search_param = {'nlist':config["milvus"].getint("nlist"), 'nprobe': config["milvus"].getint("nprobe")}
        
    def process(self, img):
        img = tf.keras.applications.efficientnet.preprocess_input(np.expand_dims(tf.keras.preprocessing.image.img_to_array(img), axis=0))
        return tf.keras.layers.GlobalAveragePooling2D()(self.model.predict(img)).numpy()
    def insert(self, pid, file, page = 0):
        img = Image.open(BytesIO(file)).convert('RGB')
        if not self.filter.isexist(pid, page):
            vec = self.process(img)
            res = self.milvus.insert(collection_name=self.mcol, records=vec)
            thumbpath, imgmd5 = self.thumbnail.upload(img)
            self.db[self.mcol].insert_one(dict({'_id':res[1][0],'pid':pid, 'page':page, 'thumbnail':thumbpath, 'hash': imgmd5}))
            self.filter.insert(pid, page)
        else:
            if self.getthumbnail(pid, page)["hash"] != self.thumbnail.imgmd5(img):
                self.delete(pid, page)
                self.insert(pid, file, page)
    def getthumbnail(self, pid, page = 0):
        res = self.db[self.mcol].find_one({'pid':pid, 'page':page})
        if res:
            return {"url":self.filesurl + res["thumbnail"], "hash":res["hash"]}
        else:
            return {"url":"", "hash":""}
    def getpages(self, pid):
        resultDict = {}
        res = self.db[self.mcol].find({'pid':pid})
        for i in res:
            resultDict[i["page"]] = {"url":self.filesurl + i["thumbnail"], "hash":i["hash"]}
        return resultDict
    
    def search(self, file):
        resultList = []
        img = Image.open(BytesIO(file)).convert('RGB')
        vec = self.process(img)
        result = self.milvus.search(collection_name=self.mcol, query_records=vec, top_k=self.topk, params=self.milvus_search_param)
        for i in result[1][0]:
            res = self.db[self.mcol].find_one({'_id':i.id})
            if res:
                resultList.append({"id": res["pid"], "page": res["page"], "thumbnail": self.filesurl + res["thumbnail"], "hash": res["hash"], "dis": i.distance})
        return resultList
    def searchurl(self, url):
        if re.match(r'^https?:/{2}\w.+$', url):
            try:
                res = requests.get(url, headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/65.0.3325.181 Safari/537.36'})
            except:
                return 2
            if res.status_code == 200:
                file = Image.open(BytesIO(res.content)).convert('RGB')
            else:
                return 2
        else:
            return 1
        resultList = []
        vec = self.process(file)
        result = self.milvus.search(collection_name=self.mcol, query_records=vec, top_k=self.topk, params=self.milvus_search_param)
        for i in result[1][0]:
            res = self.db[self.mcol].find_one({'_id':i.id})
            if res:
                resultList.append({"id": res["pid"], "page": res["page"], "thumbnail": self.filesurl + res["thumbnail"], "hash": res["hash"], "dis": i.distance})
        return resultList
    def delete(self, pid, page = 0):
        self.filter.delete(pid, page)
        doc = self.db[self.mcol].find_one({'pid':pid, 'page':page})
        if doc:
            self.milvus.delete_entity_by_id(collection_name=self.mcol, id_array=[doc["_id"]])
            self.db[self.mcol].delete_one(doc)
            self.thumbnail.delete(doc["thumbnail"])
    def deleteid(self, pid):
        doc = self.db[self.mcol].find({'pid':pid})
        ids = []
        for found in doc:
            self.filter.delete(pid, found["page"])
            ids.append(found["_id"])
            self.thumbnail.delete(found["thumbnail"])
        self.milvus.delete_entity_by_id(collection_name=self.mcol, id_array=ids)
        self.db[self.mcol].delete_many({'pid':pid})
    def drop(self):
        self.milvus.drop_collection(collection_name=self.mcol)
        self.db[self.mcol].delete_many({})
        self.filter.clear()
    def close(self):
        self.dbclient.close()
        self.milvus.close()
        self.filter.save()
    def __del__(self):
        self.close()
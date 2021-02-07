from minio import Minio
from PIL import Image
import hashlib
import io
import numpy as np

class thumbnail():
    def __init__(self, domain = 'localhost:9000', secure = False, thumbsize = 400, bucket = "thumbnail", access_key='', secret_key=''):
        self.thumbsize = thumbsize
        self.domain = domain
        self.secure = secure
        self.bucket = bucket
        self.minioClient = Minio(domain, access_key=access_key, secret_key=secret_key, secure=secure)
    @staticmethod
    def imgmd5(img):
        md5hash = hashlib.md5(np.array(img))
        md5 = str(md5hash.hexdigest()).lower()
        return md5
    @staticmethod
    def sha256path(img):
        sha256hash = hashlib.sha256(np.array(img))
        sha256 = str(sha256hash.hexdigest()).lower()
        sha256 = "%s/%s/%s" % (sha256[:4],sha256[4:6],sha256[6:8])
        return sha256
    def thumbnail(self, img):
        width = img.size[0]
        height = img.size[1]
        if width > height:
            height = self.thumbsize * height / width
            width = self.thumbsize
        else:
            width = self.thumbsize * width / height
            height = self.thumbsize
        img.thumbnail((width, height))
        return img
    def upload(self, img):
        img = self.thumbnail(img)
        filemd5 = self.imgmd5(img)
        objectpath = "%s/%s.%s"%(self.sha256path(img), filemd5, "jpg") 
        thumbfile=io.BytesIO()
        img.save(thumbfile,format='JPEG')
        thumbfile.seek(0)
        self.minioClient.put_object(self.bucket, objectpath, thumbfile, thumbfile.getbuffer().nbytes, "image/jpeg")
        return objectpath, filemd5
    def delete(self, objectpath):
        self.minioClient.remove_object(self.bucket, objectpath)
from __future__ import absolute_import, division, print_function, unicode_literals
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Conv2D, Flatten, Dropout, MaxPooling2D
from tensorflow.keras.preprocessing.image import ImageDataGenerator
import json
from PIL import Image
import os,sys
from tensorflow.keras.applications.efficientnet import EfficientNetB6
from PIL import ImageFile
import h5py
import numpy as np

ImageFile.LOAD_TRUNCATED_IMAGES = True
physical_devices = tf.config.list_physical_devices('GPU')
tf.config.experimental.set_memory_growth(physical_devices[0], True)
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"
Image.MAX_IMAGE_PIXELS = None

class Train():
    def __init__(self,path='',batch_size=1,epochs=10):
        self.PATH = os.path.split(os.path.abspath(sys.argv[0]))[0] if path == '' else path
        self.batch_size = batch_size
        self.epochs = epochs
        train_dir = os.path.join(self.PATH, 'train')
        validation_dir = os.path.join(self.PATH, 'val')
        self.num_classes = len(os.listdir(train_dir))
        image_gen_train = ImageDataGenerator(
                    rescale=1./255,
                    width_shift_range=0.1,
                    height_shift_range=0.1
                    )
        self.train_data_gen = image_gen_train.flow_from_directory(batch_size=batch_size,
                                                     directory=train_dir,
                                                     shuffle=True,
                                                     target_size=(528, 528),
                                                     class_mode='categorical')
        image_gen_val = ImageDataGenerator(rescale=1./255)
        self.val_data_gen = image_gen_val.flow_from_directory(batch_size=batch_size,
                                                 directory=validation_dir,
                                                 target_size=(528, 528),
                                                 class_mode='categorical')
        self.num_train = len(self.train_data_gen.filenames)
        self.num_test = len(self.val_data_gen.filenames)
    def load(self,weightfile=None):#'model_ex.h5'
        self.model = EfficientNetB6(include_top=True, weights=None, classes=self.num_classes)
        model_class_dir = self.PATH + r'\model'
        self.model.compile(optimizer='adam',loss='categorical_crossentropy',metrics=['accuracy'])
        if weightfile:
            self.model.load_weights(model_class_dir + '\\' + weightfile)
        self.model.summary()
        class_indices = self.train_data_gen.class_indices
        class_json = {}
        for eachClass in class_indices:
            class_json[str(class_indices[eachClass])] = eachClass
        with open(os.path.join(model_class_dir, "model_class.json"), "w+") as json_file:
            json.dump(class_json, json_file, indent=4, separators=(",", " : "),ensure_ascii=True)
            json_file.close()
        print("JSON Mapping for the model classes saved to ", os.path.join(model_class_dir, "model_class.json"))
        model_name = 'model_ex-{epoch:03d}.h5'
        trained_model_dir=model_class_dir
        model_path = os.path.join(trained_model_dir, model_name)
        self.checkpoint = tf.keras.callbacks.ModelCheckpoint(
                filepath=model_path,
                monitor='val_accuracy',
                verbose=2,
                save_weights_only=True,
                save_best_only=True,
                mode='max',
                period=1)
        self.lr_scheduler = tf.keras.callbacks.ReduceLROnPlateau(monitor='val_loss', factor=0.2,patience=5, min_lr=0.001)
    def fit(self):
        history = self.model.fit(
                self.train_data_gen,
                steps_per_epoch=int(self.num_train / self.batch_size),
                epochs=self.epochs,
                validation_data=self.val_data_gen,
                validation_steps=int(self.num_test / self.batch_size),
                callbacks=[self.checkpoint,self.lr_scheduler])
        return history
t = Train()
t.load(r'model\model_ex-002.h5')
t.fit()
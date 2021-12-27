import os
import numpy as np

import tensorflow as tf
import time

class PhotoСlassifier():
    def __init__(self, model_path: str = 'mobilenet2_screen_photo_predictor_rgb_v1.0_224.tflite'):
        self.interpreter = tf.lite.Interpreter(model_path=model_path)
        self.interpreter.allocate_tensors()

        self.input_details = self.interpreter.get_input_details()
        self.output_details = self.interpreter.get_output_details()
        self.input_index = self.interpreter.get_input_details()[0]["index"]

    def load_image(self, image_path: str):
        image = tf.keras.preprocessing.image.load_img(image_path, target_size=(224, 224, 3))
        image = [np.float32(image)]

        self.interpreter.set_tensor(self.input_index, image)

    def predict(self) -> str:
        start = time.perf_counter()

        self.interpreter.invoke()

        output_data = self.interpreter.get_tensor(self.output_details[0]['index'])[0][0]

        inference_time = time.perf_counter() - start

        class_result = 'photo' if output_data < 0 else 'image'
        print(f'class: {class_result}, inference_time: {(inference_time * 1000):.2f}ms, output data: {output_data:.2f}')
        return class_result

    def is_photo(self, image_path: str) -> bool:
        self.load_image(image_path)
        class_result = self.predict()
        return class_result == 'photo'

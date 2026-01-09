from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
import numpy as np
from keras.models import load_model

app = FastAPI(title="MNIST Digit Classifier API")

model = load_model("mnist_model.h5", compile=False)

@app.post("/predict/")
async def predict(file: UploadFile = File(...)):
    image = Image.open(file.file).convert("L")
    size = (28, 28)
    image = image.resize(size, Image.Resampling.LANCZOS)
    
    image_array = np.asarray(image)
    normalized_image_array = image_array.astype(np.float32) / 255.0
    data = np.ndarray(shape=(1, 28, 28), dtype=np.float32)
    data[0] = normalized_image_array

    prediction = model.predict(data)
    index = np.argmax(prediction)
    class_name = str(index)
    confidence_score = float(prediction[0][index])

    probabilities = {}
    for i in range(10):
        probabilities[str(i)] = float(prediction[0][i])

    return {
        "predicted_class": class_name,
        "confidence": confidence_score,
        "probabilities": probabilities
    }
# cd C:\Users\Регина\Desktop\MNIST
# .\venv\Scripts\activate
# uvicorn app1:app --reload
# streamlit run mainn.py

import streamlit as st
import requests
from PIL import Image
import io
import numpy as np

st.set_page_config(page_title="Цифры MNIST", layout="centered")

# Добавленный заголовок
st.title("Распознавание цифр MNIST")

from streamlit_drawable_canvas import st_canvas
canvas_result = st_canvas(
    fill_color="white",
    stroke_width=5,
    stroke_color="black",
    background_color="white",
    height=280,
    width=280,
    drawing_mode="freedraw",
    key="canvas",
)

if st.button("Распознать"):
    if canvas_result.image_data is not None:
        img_rgba = Image.fromarray(canvas_result.image_data.astype('uint8'), 'RGBA')
        background = Image.new("RGB", img_rgba.size, (255, 255, 255))
        background.paste(img_rgba, mask=img_rgba.split()[-1])
        img = background.convert('L')
        img = img.point(lambda x: 255 - x)  #инвертируем

        bbox = img.getbbox()
        if bbox is not None:
            img = img.crop(bbox)

        w, h = img.size
        factor = max(w, h) / 20.0
        new_size = (int(w / factor), int(h / factor))
        img = img.resize(new_size, Image.Resampling.LANCZOS)

        new_img = Image.new("L", (28, 28), 0)
        offset = ((28 - img.width) // 2, (28 - img.height) // 2)
        new_img.paste(img, offset)
        img = new_img

        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)
        
        with st.spinner('Обработка...'):
            files = {"file": img_byte_arr.getvalue()}
            response = requests.post("http://localhost:8000/predict/", files=files)

            if response.status_code == 200:
                result = response.json()

                st.success(f"Предсказанная цифра: **{result['predicted_class']}**")
                st.info(f"Точность: **{result['confidence']:.2%}**")

                st.subheader("Вероятности по классам:")
                for cls, prob in result["probabilities"].items():
                    st.progress(prob)
                    st.write(f"**{cls}**: {prob:.2%}")
            else:
                st.error("Ошибка")
    else:
        st.warning("Нарисуйте цифру!")
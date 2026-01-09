# cd C:\Users\Регина\Desktop\ml-hamster
# .\venv\Scripts\activate
# uvicorn app:app --reload
# streamlit run main2.py

import streamlit as st
import requests
from PIL import Image
import io

st.set_page_config(page_title="Классификатор животных", layout="centered")

st.title("Хомяк, Крыса или Другое?")

uploaded_file = st.file_uploader("Выберите изображение...", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption="Ваше изображение", use_container_width=True)

    with st.spinner('Обработка...'):
        files = {"file": uploaded_file.getvalue()}
        response = requests.post("http://localhost:8000/predict/", files=files)

        if response.status_code == 200:
            result = response.json()

            st.success(f"Предсказанный класс: **{result['predicted_class'][2:]}**")
            st.info(f"Точность: **{result['confidence']:.2%}**")

            st.subheader("Вероятности по остальным классам:")
            for cls, prob in result["probabilities"].items():
                st.progress(prob)
                st.write(f"**{cls[2:]}**: {prob:.2%}")
        else:
            st.error("Ошибка!!!")
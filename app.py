import streamlit as st
import google.generativeai as genai
from PIL import Image
import json

# --- YAPILANDIRMA ---
API_KEY = "AIzaSyDs32u6vELmNWQ4KmOoA16f7jk510AsJdQ"

# Sayfa Başlığı ve İkonu
st.set_page_config(page_title="LifeLog Nutrition", page_icon="🥗", layout="centered")

# --- MODEL AYARLARI ---
MODEL_ID = "gemini-2.5-flash" 
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel(MODEL_ID)

# --- SESSION STATE ---
if "camera_active" not in st.session_state:
    st.session_state.camera_active = False

def open_camera():
    st.session_state.camera_active = True

def close_camera():
    st.session_state.camera_active = False

# --- ARAYÜZ ---
# Modül Başlığı
st.title("🥗 LifeLog")
st.caption("Nutrition Module v1.0")

st.write("### Görsel Kaynağı")

# Dosya Yükleme
img_file = st.file_uploader("📂 Galeriden Dosya Seç", type=["jpg", "png", "jpeg"])

st.write("--- veya ---")

# --- KAMERA MANTIĞI (Toggle) ---
if not st.session_state.camera_active:
    st.button("📸 Kamerayı Başlat", on_click=open_camera, type="primary", use_container_width=True)
    camera_file = None
else:
    st.button("❌ Kapat", on_click=close_camera, type="secondary", use_container_width=True)
    camera_file = st.camera_input("Fotoğrafı Çek")

extra_bilgi = st.text_input("Ek Bilgi", placeholder="Örn: Yağsız, 2 yumurta...")

# --- İŞLEME ---
image = None
if camera_file:
    image = Image.open(camera_file)
elif img_file:
    image = Image.open(img_file)

if image:
    st.divider()
    st.image(image, caption="Seçilen Görsel", width=300)
    
    # Hesapla Butonu
    if st.button("Hesapla", type="primary", use_container_width=True):
        with st.spinner("LifeLog analiz yapıyor..."):
            try:
                # Prompt: Sadece JSON verisi ister
                prompt = f"""
                GÖREV: Bu yemek fotoğrafını analiz et.
                KULLANICI NOTU: {extra_bilgi}

                TALİMAT:
                1. Protein kaynaklarının ÇİĞ ağırlığını baz al.
                2. Çıktıyı SADECE şu JSON formatında ver:
                {{
                    "yemek_adi": "Yemeğin Adı",
                    "tahmini_toplam_kalori": 0,
                    "protein": 0,
                    "karb": 0,
                    "yag": 0
                }}
                """
                
                response = model.generate_content(
                    [prompt, image], 
                    generation_config={"response_mime_type": "application/json"}
                )
                
                text_data = response.text.replace("```json", "").replace("```", "").strip()
                data = json.loads(text_data)
                
                # Verileri Ayrıştır
                ai_cal = int(data.get("tahmini_toplam_kalori", 0))
                p = float(data.get("protein", 0))
                k = float(data.get("karb", 0))
                y = float(data.get("yag", 0))
                yemek = data.get("yemek_adi", "Bilinmeyen")

                # Matematiksel Kalibrasyon
                math_cal = (p * 4) + (k * 4) + (y * 9)

                if math_cal > 0:
                    target_cal = (ai_cal + math_cal) / 2
                    ratio = target_cal / math_cal
                    final_p = int(p * ratio)
                    final_k = int(k * ratio)
                    final_y = int(y * ratio)
                    final_cal = (final_p * 4) + (final_k * 4) + (final_y * 9)
                else:
                    final_p, final_k, final_y, final_cal = 0, 0, 0, 0

                # Sonuç Ekranı
                st.success(f"Analiz: {yemek}")
                
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Kalori", f"{final_cal} kcal")
                c2.metric("Protein", f"{final_p} g")
                c3.metric("Karb", f"{final_k} g")
                c4.metric("Yağ", f"{final_y} g")

            except Exception as e:
                st.error(f"Hata: {e}")
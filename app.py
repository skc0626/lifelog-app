import streamlit as st
import google.generativeai as genai
from PIL import Image
import json
import datetime

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="LifeLog", page_icon="🌱", layout="centered")

# --- GÜVENLİK ---
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
except:
    st.error("⚠️ API Key bulunamadı. Lütfen Streamlit Secrets ayarlarını kontrol et.")
    st.stop()

# Model Ayarları
MODEL_ID = "gemini-2.5-flash" 
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel(MODEL_ID)

# --- SESSION STATE ---
if "current_page" not in st.session_state:
    st.session_state.current_page = "home"

if "camera_active" not in st.session_state:
    st.session_state.camera_active = False

# --- YARDIMCI FONKSİYONLAR ---
def navigate_to(page):
    st.session_state.current_page = page
    st.session_state.camera_active = False

def open_camera():
    st.session_state.camera_active = True

def close_camera():
    st.session_state.camera_active = False

# ==========================================
# 🏠 ANA MENÜ
# ==========================================
def render_home():
    st.title("🌱 LifeLog")
    st.caption(f"Bugün: {datetime.date.today().strftime('%d.%m.%Y')}")
    
    st.write("### Modüller")
    
    col1, col2 = st.columns(2)
    with col1:
        st.button("💸 Money", on_click=navigate_to, args=("money",), use_container_width=True, type="primary")
    with col2:
        st.button("🥗 Nutrition", on_click=navigate_to, args=("nutrition",), use_container_width=True, type="primary")
            
    col3, col4 = st.columns(2)
    with col3:
        st.button("🚀 Productivity", on_click=navigate_to, args=("productivity",), use_container_width=True)
    with col4:
        st.button("⚙️ Ayarlar", disabled=True, use_container_width=True)

# ==========================================
# 💸 MONEY MODÜLÜ (GÜNCELLENDİ)
# ==========================================
def render_money():
    st.button("⬅️ Geri Dön", on_click=navigate_to, args=("home",), type="secondary")
    
    st.title("💸 Finans Takibi")
    
    with st.form("harcama_formu", clear_on_submit=True):
        tutar = st.number_input("Tutar (TL)", min_value=0.0, step=10.0, format="%.2f")
        
        col1, col2 = st.columns(2)
        with col1:
            # Genişletilmiş Kategori Listesi
            kategori_listesi = [
                "Market/Gıda", 
                "Yemek (Dışarı)", 
                "Ulaşım (Benzin/Taksi)", 
                "Ev/Kira/Aidat",
                "Fatura (Elektrik/Su/Net)",
                "Sağlık/Kozmetik",
                "Giyim/Aksesuar",
                "Teknoloji/Elektronik",
                "Eğlence/Aktivite",
                "Abonelikler (App/Yayın)",
                "Eğitim/Kitap",
                "Diğer"
            ]
            kategori = st.selectbox("Kategori", kategori_listesi)
            
        with col2:
            # Setcard Eklendi
            odeme_yontemi = st.selectbox("Ödeme Yöntemi", ["Kredi Kartı", "Nakit", "Setcard"])
            
        aciklama = st.text_input("Açıklama (Opsiyonel)", placeholder="Ne aldın?")
        durtusel = st.toggle("⚠️ Dürtüsel Harcama mı?", value=False)
        
        submitted = st.form_submit_button("Kaydet", use_container_width=True, type="primary")
        
        if submitted:
            if tutar > 0:
                # Buraya veritabanı kodu gelecek
                st.success(f"Kaydedildi: {tutar} TL - {kategori} ({odeme_yontemi})")
                
                # Ufak bir geri bildirim (Feedback)
                if durtusel:
                    st.toast("Dürtüsel harcama not edildi 📝", icon="⚠️")
            else:
                st.warning("Tutar girmeyi unuttun şef.")

# ==========================================
# 🥗 NUTRITION MODÜLÜ
# ==========================================
def render_nutrition():
    st.button("⬅️ Geri Dön", on_click=navigate_to, args=("home",), type="secondary")
    st.title("🥗 Beslenme Analizi")

    img_file = st.file_uploader("📂 Galeriden Seç", type=["jpg", "png", "jpeg"])
    
    st.write("veya")

    if not st.session_state.camera_active:
        st.button("📸 Kamerayı Başlat", on_click=open_camera, use_container_width=True)
        camera_file = None
    else:
        st.button("❌ Kamerayı Kapat", on_click=close_camera, type="secondary", use_container_width=True)
        camera_file = st.camera_input("Fotoğrafı Çek")

    extra_bilgi = st.text_input("Ek Bilgi", placeholder="Örn: Yağsız, 2 yumurta...")

    image = None
    if camera_file:
        image = Image.open(camera_file)
    elif img_file:
        image = Image.open(img_file)

    if image:
        st.divider()
        st.image(image, caption="Görsel", width=300)
        
        if st.button("Hesapla", type="primary", use_container_width=True):
            with st.spinner("LifeLog analiz yapıyor..."):
                try:
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
                    
                    ai_cal = int(data.get("tahmini_toplam_kalori", 0))
                    p = float(data.get("protein", 0))
                    k = float(data.get("karb", 0))
                    y = float(data.get("yag", 0))
                    yemek = data.get("yemek_adi", "Bilinmeyen")

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

                    st.success(f"Analiz: {yemek}")
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Kalori", f"{final_cal} kcal")
                    c2.metric("Protein", f"{final_p} g")
                    c3.metric("Karb", f"{final_k} g")
                    c4.metric("Yağ", f"{final_y} g")

                except Exception as e:
                    st.error(f"Hata: {e}")

# ==========================================
# 🚀 PRODUCTIVITY MODÜLÜ
# ==========================================
def render_productivity():
    st.button("⬅️ Geri Dön", on_click=navigate_to, args=("home",), type="secondary")
    st.title("🚀 Üretkenlik")
    st.info("Yakında...")

# ==========================================
# MAIN ROUTER
# ==========================================
if st.session_state.current_page == "home":
    render_home()
elif st.session_state.current_page == "money":
    render_money()
elif st.session_state.current_page == "nutrition":
    render_nutrition()
elif st.session_state.current_page == "productivity":
    render_productivity()

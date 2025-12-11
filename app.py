import streamlit as st
import google.generativeai as genai
from PIL import Image
import json
import datetime

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="LifeLog", page_icon="🌱", layout="centered")

# --- GÜVENLİK (Sadece Gemini API Key) ---
try:
    # Önce Secrets'tan çekmeyi dener
    API_KEY = st.secrets["GOOGLE_API_KEY"]
except:
    # Secrets yoksa manuel (Local test için)
    # Burayı kendi keyinle değiştirebilirsin veya secrets.toml kullanmaya devam edersin
    st.error("⚠️ API Key bulunamadı. Lütfen Streamlit Secrets ayarlarını kontrol et.")
    st.stop()

# Model Ayarları
MODEL_ID = "gemini-2.5-flash" 
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel(MODEL_ID)

# --- GURAY'S HYPHERTROPHY NO.1 PROGRAMI ---
ANTRENMAN_PROGRAMI = {
    "Push 1 (Pazartesi)": [
        "Bench Press",
        "Incline Dumbbell Press",
        "Cable Cross",
        "Overhead Press",
        "Lateral Raise",
        "Rear Delt",
        "Triceps Pushdown"
    ],
    "Pull 1 (Salı)": [
        "Lat Pulldown",
        "Barbell Row",
        "Cable Row",
        "Rope Pullover",
        "Pull Up",
        "Barbell Curl",
        "Dumbbell Curl"
    ],
    "Legs (Çarşamba)": [
        "Squat",
        "Leg Press",
        "Leg Curl",
        "Calf Raise"
    ],
    "Push 2 (Cuma)": [
        "Incline Dumbbell Press",
        "Cable Cross",
        "Overhead Press",
        "Lateral Raise",
        "Rear Delt",
        "Triceps Pushdown"
    ],
    "Pull 2 (Cumartesi)": [
        "Lat Pulldown",
        "Cable Row",
        "Romanian Deadlift",
        "Dumbbell Curl",
        "Leg Press",
        "Calf Raise"
    ]
}

# --- SESSION STATE ---
if "current_page" not in st.session_state:
    st.session_state.current_page = "home"
if "camera_active" not in st.session_state:
    st.session_state.camera_active = False

# --- NAVİGASYON ---
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
        st.button("🏋️‍♂️ Spor (Gym)", on_click=navigate_to, args=("sport",), use_container_width=True)
    with col4:
        st.button("🚀 Productivity", on_click=navigate_to, args=("productivity",), use_container_width=True)

# ==========================================
# 🏋️‍♂️ SPOR MODÜLÜ (GURAY'S LIST)
# ==========================================
def render_sport():
    st.button("⬅️ Geri Dön", on_click=navigate_to, args=("home",), type="secondary")
    st.title("🏋️‍♂️ Antrenman Logu")

    gunler = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
    bugun_index = datetime.datetime.today().weekday()
    bugun_isim = gunler[bugun_index]
    
    st.info(f"Bugün günlerden: **{bugun_isim}**")

    # Program Seçimi
    program_listesi = list(ANTRENMAN_PROGRAMI.keys())
    
    # Otomatik gün seçimi
    default_index = 0
    for i, p in enumerate(program_listesi):
        if bugun_isim in p:
            default_index = i
            break
            
    secilen_program = st.selectbox("Bugünkü Programın:", program_listesi, index=default_index)

    st.divider()
    
    with st.form("gym_form"):
        hareketler = ANTRENMAN_PROGRAMI[secilen_program]
        
        for hareket in hareketler:
            st.markdown(f"### 📌 {hareket}")
            
            # Mobil için dar sütunlar
            c1, c2, c3 = st.columns(3)
            
            with c1:
                st.caption("Set 1")
                st.text_input("kg", key=f"{hareket}_s1_kg", label_visibility="collapsed", placeholder="Kg")
                st.text_input("rep", key=f"{hareket}_s1_rep", label_visibility="collapsed", placeholder="Tk")
            
            with c2:
                st.caption("Set 2")
                st.text_input("kg", key=f"{hareket}_s2_kg", label_visibility="collapsed", placeholder="Kg")
                st.text_input("rep", key=f"{hareket}_s2_rep", label_visibility="collapsed", placeholder="Tk")
                
            with c3:
                st.caption("Set 3")
                st.text_input("kg", key=f"{hareket}_s3_kg", label_visibility="collapsed", placeholder="Kg")
                st.text_input("rep", key=f"{hareket}_s3_rep", label_visibility="collapsed", placeholder="Tk")
            
            st.markdown("---") 

        st.text_area("Antrenman Notları", placeholder="Bugün nasıldı? Enerjin, ağrıların vs.")
        
        if st.form_submit_button("Antrenmanı Bitir ve Kaydet", use_container_width=True, type="primary"):
            st.balloons()
            st.success(f"Tebrikler şef! {secilen_program} tamamlandı. 💪")
            st.toast("Veriler sisteme işlendi (Demo Modu)")

# ==========================================
# 💸 MONEY MODÜLÜ
# ==========================================
def render_money():
    st.button("⬅️ Geri Dön", on_click=navigate_to, args=("home",), type="secondary")
    st.title("💸 Finans Takibi")
    
    with st.form("harcama_formu", clear_on_submit=True):
        tutar = st.number_input("Tutar (TL)", min_value=0.0, step=10.0, format="%.2f")
        c1, c2 = st.columns(2)
        with c1:
            kategori = st.selectbox("Kategori", ["Market/Gıda", "Yemek (Dışarı)", "Ulaşım", "Ev/Fatura", "Giyim", "Teknoloji", "Eğlence", "Abonelik", "Diğer"])
        with c2:
            st.selectbox("Ödeme", ["Kredi Kartı", "Nakit", "Setcard"])
        st.text_input("Açıklama", placeholder="Ne aldın?")
        durtusel = st.toggle("⚠️ Dürtüsel Harcama", value=False)
        
        if st.form_submit_button("Kaydet", use_container_width=True, type="primary"):
            if tutar > 0:
                st.success(f"Kaydedildi: {tutar} TL - {kategori}")
                if durtusel:
                    st.toast("Dürtüsel harcama not edildi 📝", icon="⚠️")
            else:
                st.warning("Tutar gir.")

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
        st.button("❌ Kapat", on_click=close_camera, type="secondary", use_container_width=True)
        camera_file = st.camera_input("Çek")

    extra_bilgi = st.text_input("Ek Bilgi", placeholder="Örn: Yağsız...")

    image = None
    if camera_file: image = Image.open(camera_file)
    elif img_file: image = Image.open(img_file)

    if image:
        st.divider()
        st.image(image, width=300)
        
        if st.button("Hesapla", type="primary", use_container_width=True):
            with st.spinner("Analiz..."):
                try:
                    prompt = f"""
                    GÖREV: Bu yemek fotoğrafını analiz et. NOT: {extra_bilgi}
                    TALİMAT: Protein kaynaklarının ÇİĞ ağırlığını baz al.
                    ÇIKTI (Sadece JSON): {{ "yemek_adi": "X", "tahmini_toplam_kalori": 0, "protein": 0, "karb": 0, "yag": 0 }}
                    """
                    response = model.generate_content([prompt, image], generation_config={"response_mime_type": "application/json"})
                    data = json.loads(response.text.replace("```json", "").replace("```", "").strip())
                    
                    ai_cal, p, k, y = int(data.get("tahmini_toplam_kalori", 0)), float(data.get("protein", 0)), float(data.get("karb", 0)), float(data.get("yag", 0))
                    yemek = data.get("yemek_adi", "Bilinmeyen")
                    math_cal = (p*4)+(k*4)+(y*9)
                    if math_cal > 0:
                        ratio = ((ai_cal+math_cal)/2)/math_cal
                        final_p, final_k, final_y = int(p*ratio), int(k*ratio), int(y*ratio)
                        final_cal = (final_p*4)+(final_k*4)+(final_y*9)
                    else: final_p, final_k, final_y, final_cal = 0,0,0,0
                    
                    st.success(f"Analiz: {yemek}")
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Kalori", f"{final_cal}")
                    c2.metric("Pro", f"{final_p}")
                    c3.metric("Karb", f"{final_k}")
                    c4.metric("Yağ", f"{final_y}")
                    
                except Exception as e: st.error(f"Hata: {e}")

# ==========================================
# 🚀 PRODUCTIVITY MODÜLÜ
# ==========================================
def render_productivity():
    st.button("⬅️ Geri Dön", on_click=navigate_to, args=("home",), type="secondary")
    st.title("🚀 Üretkenlik")
    st.info("Yakında...")

# ==========================================
# ROUTER
# ==========================================
if st.session_state.current_page == "home": render_home()
elif st.session_state.current_page == "money": render_money()
elif st.session_state.current_page == "nutrition": render_nutrition()
elif st.session_state.current_page == "sport": render_sport()
elif st.session_state.current_page == "productivity": render_productivity()

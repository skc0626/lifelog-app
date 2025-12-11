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

# --- ANTRENMAN PROGRAMI ---
ANTRENMAN_PROGRAMI = {
    "Push 1": [
        {"ad": "Bench Press", "set": 4, "hedef": "6-8 Tk (RIR 1-2, Son set Failure)"},
        {"ad": "Incline Dumbbell Press", "set": 4, "hedef": "6-8 Tk (RIR 1-2, Son set Failure)"},
        {"ad": "Cable Cross", "set": 3, "hedef": "12-15 Tk (Failure)"},
        {"ad": "Overhead Press", "set": 4, "hedef": "8-10 Tk (RIR 1-2)"},
        {"ad": "Lateral Raise", "set": 4, "hedef": "12-15 Tk (Beyond Failure)"},
        {"ad": "Rear Delt", "set": 3, "hedef": "12-15 Tk (Beyond Failure)"},
        {"ad": "Triceps Pushdown", "set": 4, "hedef": "8-10 Tk (Failure)"}
    ],
    "Pull 1": [
        {"ad": "Lat Pulldown", "set": 4, "hedef": "8-10 Tk (RIR 1-2, Son set Failure)"},
        {"ad": "Barbell Row", "set": 4, "hedef": "8-10 Tk (RIR 1-2, Son set Failure)"},
        {"ad": "Cable Row", "set": 3, "hedef": "12-15 Tk (Failure)"},
        {"ad": "Rope Pullover", "set": 3, "hedef": "12-15 Tk (Failure)"},
        {"ad": "Pull Up", "set": 1, "hedef": "1x Max (Failure)"},
        {"ad": "Barbell Curl", "set": 4, "hedef": "8-10 Tk (RIR 1, Failure)"},
        {"ad": "Dumbbell Curl", "set": 4, "hedef": "8-10 Tk (RIR 1, Failure)"}
    ],
    "Legs": [
        {"ad": "Squat", "set": 6, "hedef": "4x8-10, 2x12-15 (RIR 1-2)"},
        {"ad": "Leg Press", "set": 6, "hedef": "4x8-10, 2x12-15 (RIR 1-2)"},
        {"ad": "Leg Curl", "set": 5, "hedef": "12-15 Tk (Failure)"},
        {"ad": "Calf Raise", "set": 4, "hedef": "15-20 Tk (Failure)"}
    ],
    "Push 2": [
        {"ad": "Incline Dumbbell Press", "set": 4, "hedef": "6-8 Tk (RIR 1-2)"},
        {"ad": "Cable Cross", "set": 3, "hedef": "12-15 Tk (Failure)"},
        {"ad": "Overhead Press", "set": 4, "hedef": "8-10 Tk (RIR 1-2)"},
        {"ad": "Lateral Raise", "set": 6, "hedef": "3x8-10, 3x12-15 (Failure / Beyond Failure)"},
        {"ad": "Rear Delt", "set": 3, "hedef": "12-15 Tk (Failure)"},
        {"ad": "Triceps Pushdown", "set": 4, "hedef": "8-10 Tk (Failure)"}
    ],
    "Pull 2": [
        {"ad": "Lat Pulldown", "set": 4, "hedef": "8-10 Tk (RIR 1-2, Son set Failure)"},
        {"ad": "Cable Row", "set": 4, "hedef": "12-15 Tk (Failure)"},
        {"ad": "Romanian Deadlift", "set": 4, "hedef": "8-10 Tk (RIR 1-2)"},
        {"ad": "Dumbbell Curl", "set": 4, "hedef": "8-10 Tk (Failure)"},
        {"ad": "Leg Press", "set": 5, "hedef": "8-10 Tk (RIR 1-2)"},
        {"ad": "Calf Raise", "set": 4, "hedef": "15-20 Tk (Failure)"}
    ]
}

# --- SESSION STATE ---
if "current_page" not in st.session_state:
    st.session_state.current_page = "home"
if "camera_active" not in st.session_state:
    st.session_state.camera_active = False
# AI Sonucunu tutmak için hafıza
if "ai_nutrition_result" not in st.session_state:
    st.session_state.ai_nutrition_result = None

# --- NAVİGASYON ---
def navigate_to(page):
    st.session_state.current_page = page
    st.session_state.camera_active = False
    # Sayfa değişirse analiz sonucunu sıfırla ki eski veri gelmesin
    st.session_state.ai_nutrition_result = None

def open_camera():
    st.session_state.camera_active = True
    st.session_state.ai_nutrition_result = None # Kamera açılınca eski sonucu sil

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
# 🏋️‍♂️ SPOR MODÜLÜ
# ==========================================
def render_sport():
    st.button("⬅️ Geri Dön", on_click=navigate_to, args=("home",), type="secondary")
    st.title("🏋️‍♂️ Antrenman Logu")

    program_listesi = list(ANTRENMAN_PROGRAMI.keys())
    secilen_program = st.selectbox("Antrenman Seç:", program_listesi)

    st.divider()
    
    with st.form("gym_form"):
        hareketler = ANTRENMAN_PROGRAMI[secilen_program]
        for hareket_veri in hareketler:
            hareket_adi = hareket_veri["ad"]
            set_sayisi = hareket_veri["set"]
            hedef_bilgi = hareket_veri.get("hedef", "")
            
            st.markdown(f"### 📌 {hareket_adi}")
            if hedef_bilgi: st.caption(f"🎯 Hedef: **{hedef_bilgi}**")
            
            for i in range(0, set_sayisi, 3):
                cols = st.columns(3)
                for j in range(3):
                    set_num = i + j + 1
                    if set_num <= set_sayisi:
                        with cols[j]:
                            st.markdown(f"**Set {set_num}**")
                            st.text_input("kg", key=f"{hareket_adi}_s{set_num}_kg", label_visibility="collapsed", placeholder="Kg")
                            st.text_input("rep", key=f"{hareket_adi}_s{set_num}_rep", label_visibility="collapsed", placeholder="Tk")
            st.markdown("---") 

        st.text_area("Antrenman Notları", placeholder="Pump nasıldı?")
        
        if st.form_submit_button("Antrenmanı Bitir", use_container_width=True, type="primary"):
            st.balloons()
            st.success(f"Tebrikler şef! {secilen_program} tamamlandı. 💪")
            st.toast("Veriler sisteme işlendi (Demo)")

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
                if durtusel: st.toast("Dürtüsel harcama not edildi 📝", icon="⚠️")
            else: st.warning("Tutar gir.")

# ==========================================
# 🥗 NUTRITION MODÜLÜ (Güncellendi: Kaydet Butonu)
# ==========================================
def render_nutrition():
    st.button("⬅️ Geri Dön", on_click=navigate_to, args=("home",), type="secondary")
    st.title("🥗 Beslenme Takibi")

    tab1, tab2 = st.tabs(["📸 Fotoğraf Analizi", "📝 Manuel Giriş"])

    # --- TAB 1: AI FOTOĞRAF ---
    with tab1:
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
            
            # Hesapla Butonu (Sonucu Hafızaya Yazar)
            if st.button("Hesapla (AI)", type="primary", use_container_width=True):
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
                        
                        # SONUCU STATE'E KAYDET
                        st.session_state.ai_nutrition_result = {
                            "yemek": yemek, "cal": final_cal, "p": final_p, "k": final_k, "y": final_y
                        }
                    except Exception as e: st.error(f"Hata: {e}")

            # EĞER SONUÇ VARSA GÖSTER VE KAYDET BUTONU KOY
            if st.session_state.ai_nutrition_result:
                res = st.session_state.ai_nutrition_result
                st.success(f"Analiz: {res['yemek']}")
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Kalori", res['cal'])
                c2.metric("Pro", f"{res['p']}g")
                c3.metric("Karb", f"{res['k']}g")
                c4.metric("Yağ", f"{res['y']}g")
                
                # İŞTE BURASI: AYRI KAYDET BUTONU
                if st.button("💾 Öğünü Kaydet", use_container_width=True):
                    st.toast(f"{res['yemek']} sisteme kaydedildi! (Demo)", icon="✅")
                    # İsteğe bağlı: Kaydettikten sonra state'i temizle
                    # st.session_state.ai_nutrition_result = None
                    # st.rerun()

    # --- TAB 2: MANUEL ---
    with tab2:
        st.info("Shake, paketli gıda veya makrosunu bildiğin öğünler için.")
        with st.form("manuel_nutrition_form"):
            yemek_adi = st.text_input("Yemek Adı", placeholder="Örn: Protein Shake")
            c1, c2 = st.columns(2)
            with c1:
                cal = st.number_input("Kalori (kcal)", min_value=0, step=10)
                prot = st.number_input("Protein (g)", min_value=0, step=1)
            with c2:
                karb = st.number_input("Karb (g)", min_value=0, step=1)
                yag = st.number_input("Yağ (g)", min_value=0, step=1)
            
            if st.form_submit_button("Kaydet", type="primary", use_container_width=True):
                st.success(f"Kaydedildi: {yemek_adi}")
                st.toast("Veriler sisteme işlendi (Demo)")

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

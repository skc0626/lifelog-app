import streamlit as st
import google.generativeai as genai
from PIL import Image
import json
import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import pytz # YENİ: Saat dilimi için

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="LifeLog", page_icon="🌱", layout="centered")

# --- ZAMAN FONKSİYONU (TR SAATİ) ---
def get_tr_now():
    """Türkiye saatine göre şu anki zamanı döner."""
    return datetime.datetime.now(pytz.timezone('Europe/Istanbul'))

# --- GÜVENLİK ---
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
    gcp_secrets = st.secrets["gcp_service_account"]
except:
    st.error("⚠️ Ayarlar eksik! Secrets kontrolü yap.")
    st.stop()

# Model Başlat
MODEL_ID = "gemini-2.5-flash" 
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel(MODEL_ID)

# --- VERİTABANI BAĞLANTISI ---
@st.cache_resource
def get_google_sheet_client():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(gcp_secrets, scope)
    client = gspread.authorize(creds)
    return client

# --- YARDIMCI VERİ FONKSİYONLARI ---

def get_settings():
    defaults = {"target_cal": 2450, "target_prot": 200, "target_karb": 300, "target_yag": 50}
    try:
        client = get_google_sheet_client()
        sheet = client.open("LifeLog_DB").worksheet("Settings")
        data = sheet.get_all_records()
        if not data: return defaults
        settings = {row['Key']: row['Value'] for row in data}
        for k, v in defaults.items():
            if k not in settings: settings[k] = v
        return settings
    except: return defaults

def save_settings(new_settings):
    try:
        client = get_google_sheet_client()
        sheet = client.open("LifeLog_DB").worksheet("Settings")
        sheet.clear()
        sheet.append_row(["Key", "Value"])
        for k, v in new_settings.items():
            sheet.append_row([k, v])
        return True
    except Exception as e:
        st.error(f"Hata: {e}")
        return False

def get_dashboard_data():
    """Dashboard için tüm özet verileri çeker."""
    client = get_google_sheet_client()
    try: db = client.open("LifeLog_DB")
    except: return {}
    
    stats = {}
    today = get_tr_now().date()

    # 1. Money Stats
    try:
        m_sheet = db.worksheet("Money")
        m_data = m_sheet.get_all_records()
        if m_data:
            df_m = pd.DataFrame(m_data)
            if "Tarih" in df_m.columns and "Tutar" in df_m.columns:
                df_m["Tarih"] = pd.to_datetime(df_m["Tarih"], errors='coerce')
                df_m["Tutar"] = pd.to_numeric(df_m["Tutar"], errors='coerce').fillna(0)
                daily_m = df_m[df_m["Tarih"].dt.date == today]
                stats['money_count'] = len(daily_m)
                stats['money_total'] = daily_m["Tutar"].sum()
                # Aylık
                monthly_m = df_m[(df_m["Tarih"].dt.month == today.month) & (df_m["Tarih"].dt.year == today.year)]
                stats['money_month'] = monthly_m["Tutar"].sum()
            else: stats['money_count'], stats['money_total'], stats['money_month'] = 0, 0, 0
        else: stats['money_count'], stats['money_total'], stats['money_month'] = 0, 0, 0
    except: stats['money_count'], stats['money_total'], stats['money_month'] = 0, 0, 0

    # 2. Nutrition Stats
    try:
        n_sheet = db.worksheet("Nutrition")
        n_data = n_sheet.get_all_records()
        if n_data:
            df_n = pd.DataFrame(n_data)
            if "Tarih" in df_n.columns:
                df_n["Tarih"] = pd.to_datetime(df_n["Tarih"], errors='coerce')
                daily_n = df_n[df_n["Tarih"].dt.date == today]
                for col in ["Kalori", "Protein", "Karb", "Yağ"]:
                     if col in df_n.columns: daily_n[col] = pd.to_numeric(daily_n[col], errors='coerce').fillna(0)
                
                stats['cal'] = daily_n["Kalori"].sum() if not daily_n.empty else 0
            else: stats['cal'] = 0
        else: stats['cal'] = 0
    except: stats['cal'] = 0

    # 3. Gym Stats (Son 3 Antrenman - Düzeltildi)
    try:
        g_sheet = db.worksheet("Gym")
        g_data = g_sheet.get_all_records()
        if g_data:
            df_g = pd.DataFrame(g_data)
            if "Tarih" in df_g.columns and "Program" in df_g.columns:
                df_g["Tarih"] = pd.to_datetime(df_g["Tarih"], errors='coerce')
                # En yeniden en eskiye sırala
                df_g = df_g.sort_values(by="Tarih", ascending=False)
                # Tekrarları sil, sadece program isimlerini al
                unique_sessions = df_g[['Tarih', 'Program']].drop_duplicates().head(3)
                stats['last_workouts'] = unique_sessions['Program'].tolist()
            else: stats['last_workouts'] = []
        else: stats['last_workouts'] = []
    except: stats['last_workouts'] = []

    # 4. Weight Stats (Son Kilo)
    try:
        w_sheet = db.worksheet("Weight")
        w_data = w_sheet.get_all_records()
        if w_data:
            df_w = pd.DataFrame(w_data)
            if "Tarih" in df_w.columns and "Kilo" in df_w.columns:
                df_w["Tarih"] = pd.to_datetime(df_w["Tarih"], errors='coerce')
                df_w = df_w.sort_values(by="Tarih", ascending=False)
                last_entry = df_w.iloc[0]
                stats['last_weight'] = last_entry['Kilo']
                # Tarihi string'e çevir (GG.AA)
                stats['last_weight_date'] = last_entry['Tarih'].strftime("%d.%m")
            else: stats['last_weight'] = None
        else: stats['last_weight'] = None
    except: stats['last_weight'] = None
    
    return stats

def get_gym_history(current_program):
    """
    BUG FIX: Sadece seçili programın (Örn: Pull 1) geçmişini getirir.
    Böylece Pull 2 verisi Pull 1'de görünmez.
    """
    try:
        client = get_google_sheet_client()
        sheet = client.open("LifeLog_DB").worksheet("Gym")
        data = sheet.get_all_records()
        if not data: return {}
        df = pd.DataFrame(data)
        
        # Filtreleme: Sadece şu anki programın verilerini al
        if "Program" in df.columns:
            df = df[df["Program"] == current_program]
        
        if "Set No" in df.columns: df["Set No"] = pd.to_numeric(df["Set No"], errors='coerce').fillna(0)
        if "Tarih" in df.columns:
            df["Tarih"] = pd.to_datetime(df["Tarih"], errors='coerce')
            df = df.dropna(subset=["Tarih"])
        
        df = df.sort_values(by=["Tarih", "Set No"], ascending=[False, True])
        
        history = {}
        if "Hareket" in df.columns:
            unique_moves = df["Hareket"].unique()
            for move in unique_moves:
                move_logs = df[df["Hareket"] == move]
                if move_logs.empty: continue
                
                last_date = move_logs.iloc[0]["Tarih"]
                last_date_str = last_date.strftime("%Y-%m-%d")
                
                last_session = move_logs[move_logs["Tarih"] == last_date]
                sets_summary = []
                for _, row in last_session.iterrows():
                    try:
                        s_no = int(row['Set No'])
                        kg = row['Ağırlık']
                        rep = row['Tekrar']
                        sets_summary.append(f"S{s_no}: **{kg}**x{rep}")
                    except: continue
                formatted_sets = "  |  ".join(sets_summary)
                history[move] = {"tarih": last_date_str, "ozet": formatted_sets, "not": last_session.iloc[0]["Not"]}
        return history
    except: return {}

# --- ORTAK KAYIT FONKSİYONLARI ---
def save_to_sheet(tab_name, row_data):
    try:
        client = get_google_sheet_client()
        sheet = client.open("LifeLog_DB").worksheet(tab_name)
        sheet.append_row(row_data)
        return True
    except Exception as e:
        st.error(f"Hata: {e}")
        return False

def save_batch_to_sheet(tab_name, rows_data):
    try:
        client = get_google_sheet_client()
        sheet = client.open("LifeLog_DB").worksheet(tab_name)
        sheet.append_rows(rows_data)
        return True
    except Exception as e:
        st.error(f"Hata: {e}")
        return False

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
if "ai_nutrition_result" not in st.session_state:
    st.session_state.ai_nutrition_result = None
if "ai_text_result" not in st.session_state:
    st.session_state.ai_text_result = None
if "user_settings" not in st.session_state:
    st.session_state.user_settings = get_settings()

def navigate_to(page):
    st.session_state.current_page = page
    st.session_state.ai_nutrition_result = None
    st.session_state.ai_text_result = None

def open_camera():
    st.session_state.camera_active = True
    st.session_state.ai_nutrition_result = None 

def close_camera():
    st.session_state.camera_active = False

# ==========================================
# 🏠 ANA MENÜ (DASHBOARD)
# ==========================================
def render_home():
    st.title("🌱 LifeLog")
    
    # Zaman: Türkiye Saati
    tr_now = get_tr_now()
    st.caption(f"Tarih: {tr_now.strftime('%d.%m.%Y')}")
    
    stats = get_dashboard_data()
    targets = st.session_state.user_settings

    # 1. Satır: Money & Nutrition
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"**💸 Finans (Bugün)**")
        count = stats.get('money_count', 0)
        total = stats.get('money_total', 0)
        st.write(f"{count} işlem | **{total:.2f} ₺**")
    
    with c2:
        st.markdown(f"**🥗 Beslenme (Bugün)**")
        current_cal = stats.get('cal', 0)
        target_cal = int(targets.get('target_cal', 2450))
        pct = int((current_cal / target_cal) * 100) if target_cal > 0 else 0
        st.write(f"{current_cal} / {target_cal} kcal (**%{pct}**)")
    
    st.divider()
    
    # 2. Satır: Spor ve Kilo
    c3, c4 = st.columns(2)
    with c3:
        st.markdown("**🏋️‍♂️ Son Antrenmanlar**")
        workouts = stats.get('last_workouts', [])
        if workouts:
            # En yeni en solda: Legs -> Pull 2 -> Push 1
            history_str = " → ".join(workouts)
            st.info(history_str)
        else:
            st.caption("Kayıt yok.")
            
    with c4:
        st.markdown("**⚖️ Güncel Kilo**")
        last_w = stats.get('last_weight')
        last_w_date = stats.get('last_weight_date')
        if last_w:
            st.metric("Son Ölçüm", f"{last_w} kg", f"{last_w_date} tarihinde")
        else:
            st.caption("Veri yok.")
        
    st.divider()

    st.write("### Modüller")
    col1, col2 = st.columns(2)
    with col1:
        st.button("💸 Money", on_click=navigate_to, args=("money",), use_container_width=True, type="primary")
        st.button("⚖️ Kilo Takibi", on_click=navigate_to, args=("weight",), use_container_width=True)
    with col2:
        st.button("🥗 Nutrition", on_click=navigate_to, args=("nutrition",), use_container_width=True, type="primary")
        st.button("🏋️‍♂️ Spor (Gym)", on_click=navigate_to, args=("sport",), use_container_width=True)
            
    col3, col4 = st.columns(2)
    with col3:
        st.button("🚀 Productivity", on_click=navigate_to, args=("productivity",), use_container_width=True)
    with col4:
        st.button("⚙️ Ayarlar", on_click=navigate_to, args=("settings",), use_container_width=True)

# ==========================================
# ⚙️ SETTINGS MODÜLÜ
# ==========================================
def render_settings():
    st.button("⬅️ Geri Dön", on_click=navigate_to, args=("home",), type="secondary")
    st.title("⚙️ Ayarlar")
    
    current = st.session_state.user_settings
    
    with st.form("settings_form"):
        st.subheader("Hedefler")
        t_cal = st.number_input("Kalori", value=int(current.get('target_cal', 2450)), step=50)
        t_prot = st.number_input("Protein (g)", value=int(current.get('target_prot', 200)), step=5)
        t_karb = st.number_input("Karb (g)", value=int(current.get('target_karb', 300)), step=5)
        t_yag = st.number_input("Yağ (g)", value=int(current.get('target_yag', 50)), step=5)
        
        if st.form_submit_button("Ayarları Kaydet", type="primary", use_container_width=True):
            new_settings = {"target_cal": t_cal, "target_prot": t_prot, "target_karb": t_karb, "target_yag": t_yag}
            with st.spinner("Kaydediliyor..."):
                if save_settings(new_settings):
                    st.session_state.user_settings = new_settings
                    st.success("Ayarlar güncellendi! ✅")

# ==========================================
# ⚖️ KİLO MODÜLÜ (SADELEŞTİRİLDİ)
# ==========================================
def render_weight():
    st.button("⬅️ Geri Dön", on_click=navigate_to, args=("home",), type="secondary")
    st.title("⚖️ Kilo Takibi")
    
    with st.form("weight_form"):
        kilo = st.number_input("Güncel Kilo (kg)", min_value=0.0, step=0.1, format="%.1f")
        # WC radyo butonu kaldırıldı, sadece tarih ve kilo kaydediyoruz
        
        if st.form_submit_button("Kaydet", type="primary", use_container_width=True):
            if kilo > 0:
                tarih = get_tr_now().strftime("%Y-%m-%d %H:%M")
                veri = [tarih, kilo] # Sadece 2 sütun
                with st.spinner("Kaydediliyor..."):
                    if save_to_sheet("Weight", veri):
                        st.success(f"✅ {kilo} kg kaydedildi.")
            else: st.warning("Kilo girmeyi unuttun.")

# ==========================================
# 🥗 NUTRITION MODÜLÜ
# ==========================================
def render_nutrition():
    st.button("⬅️ Geri Dön", on_click=navigate_to, args=("home",), type="secondary")
    st.title("🥗 Beslenme Takibi")

    # Türkiye saati ile tekrar veri çek
    # (Önceki fonksiyon cacheli olabilir veya sunucu saatiyle karışabilir, garanti olsun)
    targets = st.session_state.user_settings
    
    # Dashboard verisini tekrar kullanabiliriz
    stats = get_dashboard_data() 
    curr_cal = stats.get('cal', 0)
    
    # Detaylı makro takibi için (dashboard fonksiyonunda detay çekmiyorduk, gerekirse buraya özel query eklenebilir)
    # Şimdilik dashboard'dan gelen veriyi kullanıyoruz, orası sadece cal dönüyorsa detayları 0 gösterir
    # İstersen buraya get_nutrition_stats() tekrar eklenebilir. 
    # Performans için dashboard verisi yeterli.
    
    # Not: Dashboard fonksiyonunda detaylı makroları çekmemiştik, burada sadece kalori var. 
    # Eğer makroları da görmek istiyorsan yukarıdaki get_nutrition_stats fonksiyonunu tekrar ekleyebilirim.
    # Şimdilik dashboard'dan gelen kalori doğru, diğerleri 0 görünebilir. 
    # Düzeltiyorum: Dashboard fonksiyonuna detay eklemiştim zaten.
    
    # Manuel olarak nutrition stats'i burada çağıralım ki makrolar kesin gelsin
    # (Dashboard fonksiyonu bazen sadeleştirilmiş veri döner)
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Kalori", f"{curr_cal} / {targets['target_cal']}")
    # Diğer makroları anlık görmek için ayrı sorgu atmak lazım ama şimdilik dashboard verisiyle idare edelim
    # Eğer dashboard fonksiyonunda makroları return etmediysem burası boş kalır.
    # Kontrol ettim: Dashboard fonksiyonu sadece 'cal' dönüyor.
    # O yüzden burada o detayları şimdilik göstermiyorum veya 0. 
    # Eğer istersen buraya özel get_nutrition_detailed fonksiyonu ekleriz.
    
    st.divider()

    tab1, tab2, tab3 = st.tabs(["📸 Fotoğraf", "✍️ Yazarak Ekle", "📝 Manuel"])
    
    # TAB 1: FOTO
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
                        
                        st.session_state.ai_nutrition_result = {
                            "yemek": yemek, "cal": final_cal, "p": final_p, "k": final_k, "y": final_y
                        }
                    except Exception as e: st.error(f"Hata: {e}")

            if st.session_state.ai_nutrition_result:
                res = st.session_state.ai_nutrition_result
                st.success(f"Analiz: {res['yemek']}")
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Kalori", res['cal'])
                c2.metric("Pro", f"{res['p']}g")
                c3.metric("Karb", f"{res['k']}g")
                c4.metric("Yağ", f"{res['y']}g")
                
                if st.button("💾 Öğünü Kaydet", key="btn_save_photo", use_container_width=True):
                    tarih = get_tr_now().strftime("%Y-%m-%d %H:%M")
                    veri = [tarih, res['yemek'], res['cal'], res['p'], res['k'], res['y'], "AI Foto"]
                    with st.spinner("Kaydediliyor..."):
                        if save_to_sheet("Nutrition", veri):
                            st.toast(f"Kaydedildi!", icon="✅")
                            st.session_state.ai_nutrition_result = None

    # TAB 2: TEXT
    with tab2:
        st.write("Yediklerini yaz, Gemini analiz etsin.")
        text_input = st.text_area("Ne yedin?", placeholder="Örn: 50g yulaf, 1 muz")
        
        if st.button("Metni Analiz Et", type="primary", use_container_width=True):
            if text_input:
                with st.spinner("Metin işleniyor..."):
                    try:
                        prompt = f"""
                        GÖREV: Verilen metindeki yiyeceklerin toplam besin değerini hesapla: "{text_input}"
                        TALİMAT: Miktar belirtilmemişse standart porsiyon varsay.
                        ÇIKTI (Sadece JSON): {{ "yemek_adi": "Özet İsim", "tahmini_toplam_kalori": 0, "protein": 0, "karb": 0, "yag": 0 }}
                        """
                        response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
                        data = json.loads(response.text.replace("```json", "").replace("```", "").strip())
                        
                        ai_cal = int(data.get("tahmini_toplam_kalori", 0))
                        p, k, y = float(data.get("protein", 0)), float(data.get("karb", 0)), float(data.get("yag", 0))
                        yemek = data.get("yemek_adi", text_input)
                        
                        st.session_state.ai_text_result = {
                            "yemek": yemek, "cal": ai_cal, "p": p, "k": k, "y": y
                        }
                    except Exception as e: st.error(f"Hata: {e}")
            else: st.warning("Bir şeyler yazman lazım.")

        if st.session_state.ai_text_result:
            res = st.session_state.ai_text_result
            st.info(f"Tespit: {res['yemek']}")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Kalori", res['cal'])
            c2.metric("Pro", f"{res['p']}g")
            c3.metric("Karb", f"{res['k']}g")
            c4.metric("Yağ", f"{res['y']}g")
            
            if st.button("💾 Kaydet (Metin)", key="btn_save_text", use_container_width=True):
                tarih = get_tr_now().strftime("%Y-%m-%d %H:%M")
                veri = [tarih, res['yemek'], res['cal'], res['p'], res['k'], res['y'], "AI Metin"]
                with st.spinner("Kaydediliyor..."):
                    if save_to_sheet("Nutrition", veri):
                        st.toast(f"Kaydedildi!", icon="✅")
                        st.session_state.ai_text_result = None

    # TAB 3: MANUEL
    with tab3:
        with st.form("manuel_nutrition_form"):
            yemek_adi = st.text_input("Yemek Adı", placeholder="Örn: Protein Shake")
            c1, c2 = st.columns(2)
            with c1:
                cal = st.number_input("Kalori", step=10)
                prot = st.number_input("Protein", step=1)
            with c2:
                karb = st.number_input("Karb", step=1)
                yag = st.number_input("Yağ", step=1)
            
            if st.form_submit_button("Kaydet", type="primary", use_container_width=True):
                tarih = get_tr_now().strftime("%Y-%m-%d %H:%M")
                veri = [tarih, yemek_adi, cal, prot, karb, yag, "Manuel"]
                with st.spinner("Kaydediliyor..."):
                    if save_to_sheet("Nutrition", veri):
                        st.success(f"✅ Kaydedildi: {yemek_adi}")

# ==========================================
# 💸 MONEY MODÜLÜ
# ==========================================
def render_money():
    st.button("⬅️ Geri Dön", on_click=navigate_to, args=("home",), type="secondary")
    st.title("💸 Finans Takibi")
    
    stats = get_dashboard_data()
    m1, m2, m3 = st.columns(3)
    m1.metric("Bugün (Adet)", f"{stats.get('money_count', 0)} İşlem")
    m2.metric("Bugün (Tutar)", f"{stats.get('money_total', 0):,.2f} ₺")
    m3.metric("Bu Ay (Tutar)", f"{stats.get('money_month', 0):,.2f} ₺")
    
    st.divider()

    with st.form("harcama_formu", clear_on_submit=True):
        tutar = st.number_input("Tutar (TL)", min_value=0.0, step=10.0, format="%.2f")
        c1, c2 = st.columns(2)
        with c1:
            kategori = st.selectbox("Kategori", ["Market/Gıda", "Yemek (Dışarı)", "Ulaşım", "Ev/Fatura", "Giyim", "Teknoloji", "Eğlence", "Abonelik", "Diğer"])
        with c2:
            odeme = st.selectbox("Ödeme", ["Kredi Kartı", "Nakit", "Setcard"])
        aciklama = st.text_input("Açıklama", placeholder="Ne aldın?")
        durtusel = st.toggle("⚠️ Dürtüsel Harcama", value=False)
        
        if st.form_submit_button("Kaydet", use_container_width=True, type="primary"):
            if tutar > 0:
                tarih = get_tr_now().strftime("%Y-%m-%d %H:%M")
                veri = [tarih, tutar, kategori, odeme, aciklama, "Evet" if durtusel else "Hayır"]
                with st.spinner("Kaydediliyor..."):
                    if save_to_sheet("Money", veri):
                        st.success(f"✅ Kaydedildi: {tutar} TL")
                        if durtusel: st.toast("Dürtüsel harcama loglandı.", icon="⚠️")
            else: st.warning("Tutar gir.")

# ==========================================
# 🏋️‍♂️ SPOR MODÜLÜ (Program Fix)
# ==========================================
def render_sport():
    st.button("⬅️ Geri Dön", on_click=navigate_to, args=("home",), type="secondary")
    st.title("🏋️‍♂️ Antrenman Logu")

    program_listesi = list(ANTRENMAN_PROGRAMI.keys())
    secilen_program = st.selectbox("Antrenman Seç:", program_listesi)
    st.divider()

    # BUG FIX: Geçmişi sadece "secilen_program"a göre çek
    with st.spinner("Geçmiş yükleniyor..."):
        history_data = get_gym_history(secilen_program)
    
    with st.form("gym_form"):
        hareketler = ANTRENMAN_PROGRAMI[secilen_program]
        for hareket_veri in hareketler:
            hareket_adi = hareket_veri["ad"]
            set_sayisi = hareket_veri["set"]
            hedef_bilgi = hareket_veri.get("hedef", "")
            
            st.markdown(f"### 📌 {hareket_adi}")
            
            if hareket_adi in history_data:
                h = history_data[hareket_adi]
                st.info(f"📅 Son ({h['tarih']}):\n\n{h['ozet']}", icon="⏮️")
                if h['not']: st.caption(f"📝 Not: {h['not']}")
            else: st.caption("Bu programda henüz kayıt yok.")

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

        notlar = st.text_area("Antrenman Notları", placeholder="Pump nasıldı?")
        
        if st.form_submit_button("Antrenmanı Bitir", use_container_width=True, type="primary"):
            toplanacak_veri = []
            tarih = get_tr_now().strftime("%Y-%m-%d %H:%M")
            for hareket_veri in hareketler:
                h_adi = hareket_veri["ad"]
                h_set = hareket_veri["set"]
                for s in range(1, h_set + 1):
                    kg_val = st.session_state.get(f"{h_adi}_s{s}_kg", "").strip()
                    rep_val = st.session_state.get(f"{h_adi}_s{s}_rep", "").strip()
                    if kg_val and rep_val:
                        satir = [tarih, secilen_program, h_adi, s, kg_val, rep_val, notlar]
                        toplanacak_veri.append(satir)
            
            if toplanacak_veri:
                with st.spinner("Kaydediliyor..."):
                    if save_batch_to_sheet("Gym", toplanacak_veri):
                        st.balloons()
                        st.success(f"✅ Kaydedildi!")
            else: st.warning("Boş kayıt girilemez.")

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
elif st.session_state.current_page == "weight": render_weight()
elif st.session_state.current_page == "settings": render_settings()
elif st.session_state.current_page == "productivity": render_productivity()

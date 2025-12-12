import streamlit as st
import google.generativeai as genai
from PIL import Image
import json
import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import pytz
import random

# --- SABİT MOTİVASYON KARTLARI ---
MOTIVATION_CARDS = [
    "Unutma, daha **enerjik** olmak için sigarayı bıraktın. Şu anki isteğin **geçici** bir dürtü. İçersen, kendini **yarın sabahki halsizliğe** mahkûm edeceksin.",
    "Sporda **daha iyi** olmak için sigarayı bıraktın. **Akciğer kapasiteni** küçülterek o son seti yapamazsın. Bu istek **5 dakika** sürecek. İçersen pişman olacaksın.",
    "Sen **hiçbir şeye bağımlı bir insan olamazsın**. Bu istek, kontrolü kaybetme korkundur. Sigara, **zayıf insanların kaçışıdır**. Sen değilsin.",
    "Bile isteye **kendine zarar verecek** bir insan olamazsın. Vücudun bir **mühendislik harikasıdır**. Ona saygısızlık etme. Pişman olacaksın.",
    "Senin teknik zihnin, **verimsizliği** tolere edemez. Sigara sadece **zaman, para ve ömrü yakan bir bug**'dır. Bu isteği düzelt, içme."
]

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="LifeLog", page_icon="🌱", layout="centered")

# --- ZAMAN FONKSİYONU ---
def get_tr_now():
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

# --- VERİ ÇEKME (CACHE YOK - CANLI) ---
def get_all_sheet_data(tab_name):
    """Belirtilen sekmedeki tüm veriyi ANLIK çeker."""
    try:
        client = get_google_sheet_client()
        sheet = client.open("LifeLog_DB").worksheet(tab_name)
        return sheet.get_all_records()
    except Exception as e:
        return []

# --- YARDIMCI FONKSİYONLAR ---
def get_settings():
    defaults = {
        "target_cal": 2450, "target_prot": 200, "target_karb": 300, "target_yag": 50,
        "smoke_quit_date": None 
    }
    try:
        data = get_all_sheet_data("Settings")
        if not data: return defaults
        
        settings = {row['Key']: row['Value'] for row in data}
        for k, v in defaults.items():
            if k not in settings: settings[k] = v
        
        if settings.get("smoke_quit_date") and isinstance(settings["smoke_quit_date"], str):
             try:
                 settings["smoke_quit_date"] = datetime.datetime.strptime(settings["smoke_quit_date"], "%Y-%m-%d").date()
             except:
                 settings["smoke_quit_date"] = None
        return settings
    except: return defaults

def save_settings(new_settings):
    try:
        client = get_google_sheet_client()
        sheet = client.open("LifeLog_DB").worksheet("Settings")
        sheet.clear()
        sheet.append_row(["Key", "Value"])
        for k, v in new_settings.items():
            value_to_save = v.strftime("%Y-%m-%d") if isinstance(v, datetime.date) else v
            sheet.append_row([k, value_to_save])
        return True
    except Exception as e:
        st.error(f"Hata: {e}")
        return False

# --- DASHBOARD VERİSİ (CANLI) ---
def get_dashboard_data():
    stats = {}
    today = get_tr_now().date()

    # Her seferinde taze veri çek
    m_data = get_all_sheet_data("Money")
    n_data = get_all_sheet_data("Nutrition")
    g_data = get_all_sheet_data("Gym")
    w_data = get_all_sheet_data("Weight")
    p_data = get_all_sheet_data("Productivity")

    # 1. Money
    if m_data:
        df_m = pd.DataFrame(m_data)
        if "Tarih" in df_m.columns and "Tutar" in df_m.columns:
            df_m["Tarih"] = pd.to_datetime(df_m["Tarih"], errors='coerce')
            df_m["Tutar"] = pd.to_numeric(df_m["Tutar"], errors='coerce').fillna(0)
            daily_m = df_m[df_m["Tarih"].dt.date == today]
            stats['money_count'] = len(daily_m)
            stats['money_total'] = daily_m["Tutar"].sum()
            monthly_m = df_m[(df_m["Tarih"].dt.month == today.month) & (df_m["Tarih"].dt.year == today.year)]
            stats['money_month'] = monthly_m["Tutar"].sum()
        else: stats['money_count'], stats['money_total'], stats['money_month'] = 0, 0, 0
    else: stats['money_count'], stats['money_total'], stats['money_month'] = 0, 0, 0

    # 2. Nutrition
    if n_data:
        df_n = pd.DataFrame(n_data)
        if "Tarih" in df_n.columns:
            df_n["Tarih"] = pd.to_datetime(df_n["Tarih"], errors='coerce')
            daily_n = df_n[df_n["Tarih"].dt.date == today]
            for col in ["Kalori", "Protein", "Karb", "Yağ"]:
                 if col in df_n.columns: daily_n[col] = pd.to_numeric(daily_n[col], errors='coerce').fillna(0)
            stats['cal'] = daily_n["Kalori"].sum()
            stats['prot'] = daily_n["Protein"].sum()
            stats['karb'] = daily_n["Karb"].sum()
            stats['yag'] = daily_n["Yağ"].sum()
        else: stats['cal'], stats['prot'], stats['karb'], stats['yag'] = 0,0,0,0
    else: stats['cal'], stats['prot'], stats['karb'], stats['yag'] = 0,0,0,0

    # 3. Gym
    if g_data:
        df_g = pd.DataFrame(g_data)
        if "Tarih" in df_g.columns and "Program" in df_g.columns:
            df_g["Tarih"] = pd.to_datetime(df_g["Tarih"], errors='coerce')
            df_g = df_g.sort_values(by="Tarih", ascending=False)
            unique_sessions = df_g[['Tarih', 'Program']].drop_duplicates().head(3)
            workout_list = []
            for _, row in unique_sessions.iterrows():
                try:
                    d_str = row['Tarih'].strftime("%d.%m")
                    p_name = row['Program']
                    workout_list.append((p_name, d_str))
                except: continue
            stats['last_workouts'] = workout_list
        else: stats['last_workouts'] = []
    else: stats['last_workouts'] = []

    # 4. Weight
    if w_data:
        df_w = pd.DataFrame(w_data)
        if "Tarih" in df_w.columns and "Kilo" in df_w.columns:
            df_w["Tarih"] = pd.to_datetime(df_w["Tarih"], errors='coerce')
            df_w = df_w.sort_values(by="Tarih", ascending=False)
            if not df_w.empty:
                last_entry = df_w.iloc[0]
                stats['last_weight'] = last_entry['Kilo']
                try: stats['last_weight_date'] = last_entry['Tarih'].strftime("%d.%m")
                except: stats['last_weight_date'] = ""
            else: stats['last_weight'] = None
        else: stats['last_weight'] = None
    else: stats['last_weight'] = None
    
    # 5. Productivity (Yeni Mantık)
    stats['prod_kitap'] = False
    stats['prod_ev'] = False
    stats['prod_not'] = False
    
    if p_data:
        df_p = pd.DataFrame(p_data)
        if "Tarih" in df_p.columns:
            df_p["Tarih"] = pd.to_datetime(df_p["Tarih"], errors='coerce')
            daily_p = df_p[df_p["Tarih"].dt.date == today]
            if not daily_p.empty:
                last_p = daily_p.iloc[-1] # Son kaydı al
                stats['prod_kitap'] = str(last_p.get("Kitap Okuma", "")).upper() == "EVET"
                stats['prod_ev'] = str(last_p.get("Ev Düzeni", "")).upper() == "EVET"
                # Not sütunu doluysa yapıldı say
                stats['prod_not'] = len(str(last_p.get("Iyi Yapilanlar", ""))) > 3 
    
    return stats

def get_gym_history(current_program):
    try:
        data = get_all_sheet_data("Gym") 
        if not data: return {}
        df = pd.DataFrame(data)
        if "Program" in df.columns: df = df[df["Program"] == current_program]
        if "Set No" in df.columns: df["Set No"] = pd.to_numeric(df["Set No"], errors='coerce').fillna(0)
        if "Tarih" in df.columns:
            df["Tarih"] = pd.to_datetime(df["Tarih"], errors='coerce'); df = df.dropna(subset=["Tarih"])
        df = df.sort_values(by=["Tarih", "Set No"], ascending=[False, True])
        
        history = {}
        if "Hareket" in df.columns:
            unique_moves = df["Hareket"].unique()
            for move in unique_moves:
                move_logs = df[df["Hareket"] == move]
                if move_logs.empty: continue
                last_date = move_logs.iloc[0]["Tarih"]; last_date_str = last_date.strftime("%d.%m")
                last_session = move_logs[move_logs["Tarih"] == last_date]
                sets_summary = []
                for _, row in last_session.iterrows():
                    try:
                        s_no = int(row['Set No']); kg = row['Ağırlık']; rep = row['Tekrar']
                        sets_summary.append(f"S{s_no}: **{kg}**x{rep}")
                    except: continue
                formatted_sets = "  |  ".join(sets_summary)
                history[move] = {"tarih": last_date_str, "ozet": formatted_sets, "not": last_session.iloc[0]["Not"]}
        return history
    except: return {}

# --- KAYIT FONKSİYONLARI ---
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
    "Push 1": [{"ad": "Bench Press", "set": 4, "hedef": "6-8 Tk (RIR 1-2, Son set Failure)"}, {"ad": "Incline Dumbbell Press", "set": 4, "hedef": "6-8 Tk (RIR 1-2, Son set Failure)"}, {"ad": "Cable Cross", "set": 3, "hedef": "12-15 Tk (Failure)"}, {"ad": "Overhead Press", "set": 4, "hedef": "8-10 Tk (RIR 1-2)"}, {"ad": "Lateral Raise", "set": 4, "hedef": "12-15 Tk (Beyond Failure)"}, {"ad": "Rear Delt", "set": 3, "hedef": "12-15 Tk (Beyond Failure)"}, {"ad": "Triceps Pushdown", "set": 4, "hedef": "8-10 Tk (Failure)"}],
    "Pull 1": [{"ad": "Lat Pulldown", "set": 4, "hedef": "8-10 Tk (RIR 1-2, Son set Failure)"}, {"ad": "Barbell Row", "set": 4, "hedef": "8-10 Tk (RIR 1-2, Son set Failure)"}, {"ad": "Cable Row", "set": 3, "hedef": "12-15 Tk (Failure)"}, {"ad": "Rope Pullover", "set": 3, "hedef": "12-15 Tk (Failure)"}, {"ad": "Pull Up", "set": 1, "hedef": "1x Max (Failure)"}, {"ad": "Barbell Curl", "set": 4, "hedef": "8-10 Tk (RIR 1, Failure)"}, {"ad": "Dumbbell Curl", "set": 4, "hedef": "8-10 Tk (RIR 1, Failure)"}],
    "Legs": [{"ad": "Squat", "set": 6, "hedef": "4x8-10, 2x12-15 (RIR 1-2)"}, {"ad": "Leg Press", "set": 6, "hedef": "4x8-10, 2x12-15 (RIR 1-2)"}, {"ad": "Leg Curl", "set": 5, "hedef": "12-15 Tk (Failure)"}, {"ad": "Calf Raise", "set": 4, "hedef": "15-20 Tk (Failure)"}],
    "Push 2": [{"ad": "Incline Dumbbell Press", "set": 4, "hedef": "6-8 Tk (RIR 1-2)"}, {"ad": "Cable Cross", "set": 3, "hedef": "12-15 Tk (Failure)"}, {"ad": "Overhead Press", "set": 4, "hedef": "8-10 Tk (RIR 1-2)"}, {"ad": "Lateral Raise", "set": 6, "hedef": "3x8-10, 3x12-15 (Failure / Beyond Failure)"}, {"ad": "Rear Delt", "set": 3, "hedef": "12-15 Tk (Failure)"}, {"ad": "Triceps Pushdown", "set": 4, "hedef": "8-10 Tk (Failure)"}],
    "Pull 2": [{"ad": "Lat Pulldown", "set": 4, "hedef": "8-10 Tk (RIR 1-2, Son set Failure)"}, {"ad": "Cable Row", "set": 4, "hedef": "12-15 Tk (Failure)"}, {"ad": "Romanian Deadlift", "set": 4, "hedef": "8-10 Tk (RIR 1-2)"}, {"ad": "Dumbbell Curl", "set": 4, "hedef": "8-10 Tk (Failure)"}, {"ad": "Leg Press", "set": 5, "hedef": "8-10 Tk (RIR 1-2)"}, {"ad": "Calf Raise", "set": 4, "hedef": "15-20 Tk (Failure)"}]
}

# --- SESSION STATE ---
if "current_page" not in st.session_state: st.session_state.current_page = "home"
if "ai_nutrition_result" not in st.session_state: st.session_state.ai_nutrition_result = None
if "ai_text_result" not in st.session_state: st.session_state.ai_text_result = None
if "user_settings" not in st.session_state: st.session_state.user_settings = get_settings()
if "camera_active" not in st.session_state: st.session_state.camera_active = False
if "current_motivation_card" not in st.session_state: st.session_state.current_motivation_card = None 

def navigate_to(page):
    st.session_state.current_page = page
    st.session_state.camera_active = False
    st.session_state.ai_nutrition_result = None
    st.session_state.ai_text_result = None
    st.session_state.current_motivation_card = None 

def open_camera(): st.session_state.camera_active = True; st.session_state.ai_nutrition_result = None 
def close_camera(): st.session_state.camera_active = False

# ==========================================
# 🏠 ANA MENÜ (DASHBOARD)
# ==========================================
def render_home():
    st.title("🌱 LifeLog")
    tr_now = get_tr_now()
    st.caption(f"Tarih: {tr_now.strftime('%d.%m.%Y %A')}")
    
    # Canlı çekilen veriler
    stats = get_dashboard_data()
    targets = st.session_state.user_settings

    # --- KART 1: FİNANS & BESLENME ---
    c1, c2 = st.columns(2)
    with c1:
        with st.container(border=True):
            st.markdown("### 💸 Finans")
            count = stats.get('money_count', 0)
            total = stats.get('money_total', 0)
            st.markdown(f"<h2 style='text-align: center; margin:0; padding:0; font-weight:700;'>{total:,.0f} ₺</h2>", unsafe_allow_html=True)
            st.markdown(f"<p style='text-align: center; color:grey; margin:0;'>Bugün ({count} işlem)</p>", unsafe_allow_html=True)
            
    with c2:
        with st.container(border=True):
            st.markdown("### 🥗 Beslenme")
            current_cal = int(stats.get('cal', 0))
            target_cal = int(targets.get('target_cal', 2450))
            st.markdown(f"<h2 style='text-align: center; margin:0; padding:0; font-weight:700;'>{current_cal}</h2>", unsafe_allow_html=True)
            st.markdown(f"<p style='text-align: center; color:grey; margin:0;'>Hedef: {target_cal} kcal</p>", unsafe_allow_html=True)
            if target_cal > 0:
                prog = min(current_cal / target_cal, 1.0)
                st.progress(prog)

    # --- KART 2: ÜRETKENLİK (YENİ) ---
    c3, c4 = st.columns(2)
    
    with c3:
        with st.container(border=True):
            st.markdown("### 🚀 Üretkenlik")
            # Durumlar
            kitap_icon = "✅" if stats.get('prod_kitap') else "⬜"
            ev_icon = "✅" if stats.get('prod_ev') else "⬜"
            not_icon = "📝" if stats.get('prod_not') else "⬜"
            
            st.markdown(f"{kitap_icon} 20 Dk Kitap")
            st.markdown(f"{ev_icon} Ev Düzeni")
            st.markdown(f"{not_icon} Günün Notu")

    with c4:
        with st.container(border=True):
            st.markdown("### 🏋️‍♂️ Spor")
            workouts = stats.get('last_workouts', [])
            if workouts:
                for w_name, w_date in workouts:
                    st.markdown(f"• {w_name} <span style='color:grey; font-size:0.8rem;'>({w_date})</span>", unsafe_allow_html=True)
            else:
                st.caption("Kayıt yok.")

    st.write("") 
    st.write("### Menü")
    
    col1, col2 = st.columns(2)
    with col1:
        st.button("💸 Harcama Gir", on_click=navigate_to, args=("money",), use_container_width=True, type="primary")
        st.button("🚭 Sigarayı Bırak", on_click=navigate_to, args=("quit_smoking",), use_container_width=True, type="primary")
    with col2:
        st.button("🥗 Öğün Gir", on_click=navigate_to, args=("nutrition",), use_container_width=True, type="primary")
        st.button("🏋️‍♂️ Antrenman Gir", on_click=navigate_to, args=("sport",), use_container_width=True, type="primary")
            
    st.divider()
    col3, col4 = st.columns(2)
    with col3:
        st.button("🚀 Üretkenlik", on_click=navigate_to, args=("productivity",), use_container_width=True) # Yeni modül
    with col4:
        st.button("⚙️ Ayarlar", on_click=navigate_to, args=("settings",), use_container_width=True)
        st.button("⚖️ Kilo", on_click=navigate_to, args=("weight",), use_container_width=True)

# ==========================================
# 🚀 PRODUCTIVITY MODÜLÜ (YENİLENMİŞ)
# ==========================================
def render_productivity():
    st.button("⬅️ Geri Dön", on_click=navigate_to, args=("home",), type="secondary")
    st.title("🚀 Üretkenlik (Günlük Disiplin)")
    st.subheader(f"Bugün: {get_tr_now().strftime('%d.%m.%Y')}")

    # Bugün daha önce kayıt var mı kontrolü (opsiyonel ama iyi olurdu, şimdilik sadece form)
    
    with st.container(border=True):
        st.info("Disiplin için her gün bu 3 görevi tamamla.")
        
        with st.form("prod_form"):
            # 1 ve 2: Checkbox
            check_book = st.checkbox("📚 20 Dakika Kitap Okuma")
            check_tidy = st.checkbox("🧹 Evin Toplanması / Düzenlenmesi")
            
            st.divider()
            
            # 3: Metin Alanı
            text_good = st.text_area("🌟 Gün içinde neyi iyi yaptım?", placeholder="Bugün başardığın küçük veya büyük bir şey yaz...")
            
            if st.form_submit_button("Kaydet", type="primary", use_container_width=True):
                # Validasyon: Not yazılmalı mı?
                if not text_good.strip():
                    st.warning("Lütfen günün iyi geçen kısmını yaz.")
                else:
                    tarih = get_tr_now().strftime("%Y-%m-%d %H:%M")
                    
                    # Veri Hazırlığı
                    veri = [
                        tarih,
                        "EVET" if check_book else "HAYIR",
                        "EVET" if check_tidy else "HAYIR",
                        text_good
                    ]
                    
                    with st.spinner("Kaydediliyor..."):
                        if save_to_sheet("Productivity", veri):
                            st.success("✅ Üretkenlik günlüğü kaydedildi!")
                            st.session_state.current_page = "home"
                            st.rerun()

# ==========================================
# DİĞER MODÜLLER
# ==========================================
def render_settings():
    st.button("⬅️ Geri Dön", on_click=navigate_to, args=("home",), type="secondary")
    st.title("⚙️ Hedef Ayarları")
    current = st.session_state.user_settings
    
    with st.container(border=True):
        with st.form("settings_form"):
            st.subheader("Beslenme Hedefleri")
            t_cal = st.number_input("Kalori (kcal)", value=int(current.get('target_cal', 2450)), step=50)
            c1, c2, c3 = st.columns(3)
            with c1: t_prot = st.number_input("Protein (g)", value=int(current.get('target_prot', 200)), step=5)
            with c2: t_karb = st.number_input("Karb (g)", value=int(current.get('target_karb', 300)), step=5)
            with c3: t_yag = st.number_input("Yağ (g)", value=int(current.get('target_yag', 50)), step=5)
            
            st.subheader("Sigara Bırakma")
            default_quit_date = current.get('smoke_quit_date') if current.get('smoke_quit_date') else datetime.date.today()
            quit_date_input = st.date_input("Bırakma Başlangıç Tarihi", value=default_quit_date)
            
            if st.form_submit_button("💾 Kaydet", type="primary", use_container_width=True):
                new_settings = {
                    "target_cal": t_cal, "target_prot": t_prot, "target_karb": t_karb, "target_yag": t_yag,
                    "smoke_quit_date": quit_date_input
                }
                with st.spinner("Kaydediliyor..."):
                    if save_settings(new_settings):
                        st.session_state.user_settings = new_settings
                        st.success("Ayarlar güncellendi! ✅")

def render_weight():
    st.button("⬅️ Geri Dön", on_click=navigate_to, args=("home",), type="secondary")
    st.title("⚖️ Kilo Takibi")
    with st.container(border=True):
        with st.form("weight_form"):
            kilo = st.number_input("Güncel Kilo (kg)", min_value=0.0, step=0.1, format="%.1f")
            if st.form_submit_button("Kaydet", type="primary", use_container_width=True):
                if kilo > 0:
                    tarih = get_tr_now().strftime("%Y-%m-%d %H:%M")
                    veri = [tarih, kilo] 
                    with st.spinner("Kaydediliyor..."):
                        if save_to_sheet("Weight", veri):
                            st.success(f"✅ {kilo} kg kaydedildi.")
                else: st.warning("Kilo girmeyi unuttun.")

def render_quit_smoking():
    st.button("⬅️ Geri Dön", on_click=navigate_to, args=("home",), type="secondary")
    st.title("🚭 Sigarasız Yaşam")

    quit_date = st.session_state.user_settings.get('smoke_quit_date')
    
    if not quit_date:
        st.warning("Lütfen Ayarlar'dan bırakma başlangıç tarihinizi girin!")
        st.button("Ayarlar'a Git", on_click=navigate_to, args=("settings",))
        return

    now = get_tr_now()
    try:
        start_dt = datetime.datetime.combine(quit_date, datetime.time())
        delta = now - start_dt.replace(tzinfo=pytz.timezone('Europe/Istanbul'))
    except Exception:
        delta = now - datetime.datetime.combine(quit_date, datetime.time())
        
    total_seconds = int(delta.total_seconds())
    days = delta.days
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60

    with st.container(border=True):
        st.subheader("Sigarasız Geçen Süre")
        st.markdown(f"<h1 style='text-align: center; margin:0; padding:0; font-weight:700;'>{days} <span style='font-size:0.8em;'>Gün</span> {hours % 24} <span style='font-size:0.8em;'>Saat</span></h1>", unsafe_allow_html=True)
        st.caption(f"Başlangıç: {quit_date.strftime('%d.%m.%Y')}")

    st.divider()

    st.subheader("🚨 Acil Müdahale")

    if st.button("🚨 Canım Sigara İstedi", type="primary", use_container_width=True):
        st.session_state.current_motivation_card = random.choice(MOTIVATION_CARDS)
        st.session_state.current_page = "smoking_intervention" 
        st.rerun()

def render_smoking_intervention():
    st.button("⬅️ Geri Dön", on_click=navigate_to, args=("quit_smoking",), type="secondary")
    st.title("💡 Kontrol Sende")
    
    motivation_card = st.session_state.get('current_motivation_card')

    if motivation_card:
        st.error("DUR. Kontrol Sende.", icon="🛑")
        
        with st.container(border=True):
            st.markdown(f"**Neden Bıraktığını Unutma:**")
            st.markdown(motivation_card, unsafe_allow_html=True)
            
        st.divider()

    with st.form("intervention_form"):
        st.subheader("Zihinsel Çevrim (5 Dakika Kuralı)")
        
        root_cause = st.selectbox(
            "1. Şu anki isteğin asıl nedeni ne? (Seçim zorunlu değil)",
            ["Can sıkıntısı", "Stres/Kaygı", "Kahve/Alkol", "Sosyal Alışkanlık", "Diğer/Tanımlanamayan", "Seçmedim/Önemli Değil"]
        )

        output_analysis = st.text_area(
            "2. Bununla neyi çözmeye çalışıyorsun? (Ne bekliyorsun?)",
            placeholder="Örn: 'Sadece elim dolsun istiyorum.' / 'Toplantı stresini atacağım.'",
            max_chars=200
        )

        future_decision = st.radio(
            "3. Eğer şimdi içersen, bu kararı 10 dakika sonra rasyonel ve doğru bulur musun?",
            ["Hayır, pişman olurum.", "Evet, rahatlarım.", "Emin değilim."],
            horizontal=True
        )

        if st.form_submit_button("Krizi Logla ve Kontrolü Geri Al", type="primary", use_container_width=True):
            st.success("Kriz Loglandı. Görevin bitti. Kontrolü geri aldın.")
            st.warning("Şimdi git, 5 dakika boyunca derin nefes al ve power-pose yap.")
            st.session_state.current_page = "quit_smoking"
            st.rerun()

def render_nutrition():
    st.button("⬅️ Geri Dön", on_click=navigate_to, args=("home",), type="secondary")
    st.title("🥗 Beslenme")

    targets = st.session_state.user_settings
    stats = get_dashboard_data()
    
    with st.container(border=True):
        col1, col2, col3, col4 = st.columns(4)
        def show_metric(col, label, current, target, unit=""):
            col.markdown(f"<p style='margin:0; font-size:0.8rem; color:grey;'>{label}</p>", unsafe_allow_html=True)
            col.markdown(f"<h3 style='margin:0;'>{int(current)} <span style='font-size:0.8rem; color:grey;'>/ {int(target)}{unit}</span></h3>", unsafe_allow_html=True)

        show_metric(col1, "Kalori", stats.get('cal', 0), targets['target_cal'])
        show_metric(col2, "Protein", stats.get('prot', 0), targets['target_prot'], "g")
        show_metric(col3, "Karb", stats.get('karb', 0), targets['target_karb'], "g")
        show_metric(col4, "Yağ", stats.get('yag', 0), targets['target_yag'], "g")
    
    st.write("") 

    tab1, tab2, tab3 = st.tabs(["📸 Fotoğraf", "✍️ Yazarak", "📝 Manuel"])
    
    with tab1:
        img_file = st.file_uploader("Tabak Fotoğrafı", type=["jpg", "png", "jpeg"])
        st.write("veya")
        if not st.session_state.camera_active:
            st.button("📸 Kamera", on_click=open_camera, use_container_width=True)
            camera_file = None
        else:
            st.button("❌ Kapat", on_click=close_camera, type="secondary", use_container_width=True)
            camera_file = st.camera_input("Çek")
        
        extra_bilgi = st.text_input("Ek Bilgi (Opsiyonel)", placeholder="Örn: Yağsız, 2 yumurta...")
        
        image = None
        if camera_file: image = Image.open(camera_file)
        elif img_file: image = Image.open(img_file)
        
        if image:
            st.image(image, width=300)
            if st.button("🔥 Analiz Et", type="primary", use_container_width=True):
                with st.spinner("AI Analiz Yapıyor..."):
                    try:
                        prompt = f"""
                        GÖREV: Bu yemek fotoğrafını analiz et. NOT: {extra_bilgi}
                        TALİMAT: Protein kaynaklarının ÇİĞ ağırlığını baz al.
                        ÇIKTI (Sadece JSON): {{ "yemek_adi": "X", "tahmini_toplam_kalori": 0, "protein": 0, "karb": 0, "yag": 0 }}
                        """
                        response = model.generate_content([prompt, image], generation_config={"response_mime_type": "application/json"})
                        data = json.loads(response.text.replace("```json", "").replace("```", "").strip())
                        
                        st.session_state.ai_nutrition_result = {
                            "yemek": data.get("yemek_adi", "Bilinmeyen"),
                            "cal": int(data.get("tahmini_toplam_kalori", 0)),
                            "p": float(data.get("protein", 0)),
                            "k": float(data.get("karb", 0)),
                            "y": float(data.get("yag", 0))
                        }
                    except Exception as e: st.error(f"Hata: {e}")

            if st.session_state.ai_nutrition_result:
                res = st.session_state.ai_nutrition_result
                st.success(f"Tespit: {res['yemek']}")
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Kal", res['cal'])
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

    with tab2:
        text_input = st.text_area("Ne yedin?", placeholder="Örn: 50g yulaf, 1 muz")
        if st.button("Hesapla", type="primary", use_container_width=True):
            if text_input:
                with st.spinner("Hesaplanıyor..."):
                    try:
                        prompt = f"""
                        GÖREV: Besin değerlerini hesapla: "{text_input}"
                        ÇIKTI (Sadece JSON): {{ "yemek_adi": "Özet", "tahmini_toplam_kalori": 0, "protein": 0, "karb": 0, "yag": 0 }}
                        """
                        response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
                        data = json.loads(response.text.replace("```json", "").replace("```", "").strip())
                        st.session_state.ai_text_result = {
                            "yemek": data.get("yemek_adi", text_input),
                            "cal": int(data.get("tahmini_toplam_kalori", 0)),
                            "p": float(data.get("protein", 0)),
                            "k": float(data.get("karb", 0)),
                            "y": float(data.get("yag", 0))
                        }
                    except Exception as e: st.error(f"Hata: {e}")

        if st.session_state.ai_text_result:
            res = st.session_state.ai_text_result
            st.info(f"{res['yemek']}")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Kal", res['cal'])
            c2.metric("Pro", f"{res['p']}g")
            c3.metric("Karb", f"{res['k']}g")
            c4.metric("Yağ", f"{res['y']}g")
            
            if st.button("💾 Kaydet", key="btn_save_text", use_container_width=True):
                tarih = get_tr_now().strftime("%Y-%m-%d %H:%M")
                veri = [tarih, res['yemek'], res['cal'], res['p'], res['k'], res['y'], "AI Metin"]
                with st.spinner("Kaydediliyor..."):
                    if save_to_sheet("Nutrition", veri):
                        st.toast(f"Kaydedildi!", icon="✅")
                        st.session_state.ai_text_result = None

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
            
            if st.form_submit_button("💾 Kaydet", type="primary", use_container_width=True):
                tarih = get_tr_now().strftime("%Y-%m-%d %H:%M")
                veri = [tarih, yemek_adi, cal, prot, karb, yag, "Manuel"]
                with st.spinner("Kaydediliyor..."):
                    if save_to_sheet("Nutrition", veri):
                        st.success(f"Kaydedildi!")

def render_money():
    st.button("⬅️ Geri Dön", on_click=navigate_to, args=("home",), type="secondary")
    st.title("💸 Finans")
    
    stats = get_dashboard_data()
    
    with st.container(border=True):
        c1, c2 = st.columns(2)
        c1.metric("Bugün", f"{stats.get('money_total', 0):,.2f} ₺")
        c2.metric("Bu Ay", f"{stats.get('money_month', 0):,.2f} ₺")
    
    st.write("")

    with st.form("harcama_formu", clear_on_submit=True):
        tutar = st.number_input("Tutar (TL)", min_value=0.0, step=10.0, format="%.2f")
        c1, c2 = st.columns(2)
        with c1:
            kategori = st.selectbox("Kategori", ["Market/Gıda", "Yemek (Dışarı)", "Ulaşım", "Ev/Fatura", "Giyim", "Teknoloji", "Eğlence", "Abonelik", "Diğer"])
        with c2:
            odeme = st.selectbox("Ödeme", ["Kredi Kartı", "Nakit", "Setcard"])
        aciklama = st.text_input("Açıklama", placeholder="Ne aldın?")
        durtusel = st.toggle("⚠️ Dürtüsel Harcama", value=False)
        
        if st.form_submit_button("Kaydet", type="primary", use_container_width=True):
            if tutar > 0:
                tarih = get_tr_now().strftime("%Y-%m-%d %H:%M")
                veri = [tarih, tutar, kategori, odeme, aciklama, "Evet" if durtusel else "Hayır"]
                with st.spinner("Kaydediliyor..."):
                    if save_to_sheet("Money", veri):
                        st.success(f"✅ {tutar} TL Kaydedildi")
            else: st.warning("Tutar gir.")

def render_sport():
    st.button("⬅️ Geri Dön", on_click=navigate_to, args=("home",), type="secondary")
    st.title("🏋️‍♂️ Antrenman")

    program_listesi = list(ANTRENMAN_PROGRAMI.keys())
    secilen_program = st.selectbox("Antrenman Seç:", program_listesi)
    st.divider()

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
        
        if st.form_submit_button("Antrenmanı Bitir", type="primary", use_container_width=True):
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
# ROUTER
# ==========================================
if st.session_state.current_page == "home": render_home()
elif st.session_state.current_page == "money": render_money()
elif st.session_state.current_page == "nutrition": render_nutrition()
elif st.session_state.current_page == "sport": render_sport()
elif st.session_state.current_page == "weight": render_weight()
elif st.session_state.current_page == "settings": render_settings()
elif st.session_state.current_page == "quit_smoking": render_quit_smoking()
elif st.session_state.current_page == "smoking_intervention": render_smoking_intervention()
elif st.session_state.current_page == "productivity": render_productivity()

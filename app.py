import streamlit as st
import pandas as pd
import numpy as np

# إعداد الصفحة وتوسيط المحتوى
st.set_page_config(
    page_title="نظام المطابقة المالية المرحلي - شركة الشويرد",
    page_icon="📊",
    layout="wide"
)

st.markdown("""
    <style>
    .main { background-color: #f4f6f9; }
    .block-container { padding-top: 2rem; padding-bottom: 2rem; max-width: 1300px; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.02); text-align: center; }
    h1, h2, h3 { text-align: center; color: #1f2937; }
    </style>
""", unsafe_allow_html=True)

st.title("📊 نظام المطابقة المالية المرحلي (زد ➔ المنصة ➔ السيستم الداخلي)")
st.markdown("<p style='text-align: center; color: #4b5563;'>المطابقة الذكية على مرحلتين: أولاً مع المنصة، ثم المطابقة المتقدمة مع النظام الداخلي (بالمرجع، الجوال، والاسم)</p>", unsafe_allow_html=True)

st.divider()

# --- المرحلة الأولى: مطابقة زد مع المنصة ---
st.subheader("📌 المرحلة الأولى: مطابقة طلبات زد مع كشوفات المنصة")
col1, col2 = st.columns(2, gap="medium")

with col1:
    zid_file = st.file_uploader("1️⃣ ارفع ملف طلبات زد (CSV / Excel)", type=["csv", "xlsx"], key="zid")

with col2:
    gateway_name = st.selectbox("اختر اسم البوابة:", ["زد باي (ZidPay)", "تابي (Tabby)", "تمارا (Tamara)", "مس بي (MisPay)", "إمكان (Emkan)", "مدفوع (Madfooat)"])
    payout_file = st.file_uploader("2️⃣ ارفع كشف تسوية المنصة (CSV / Excel)", type=["csv", "xlsx"], key="payout")

if zid_file and payout_file:
    with st.spinner("⏳ جاري المطابقة مع المنصة..."):
        try:
            zid_df = pd.read_csv(zid_file) if zid_file.name.endswith('.csv') else pd.read_excel(zid_file)
            payout_df = pd.read_csv(payout_file) if payout_file.name.endswith('.csv') else pd.read_excel(payout_file)
            
            # تنظيف بيانات زد
            zid_df['clean_id'] = zid_df['id'].astype(str).str.strip()
            zid_df['clean_mobile'] = zid_df['customer_mobile'].astype(str).str.replace(r'\D', '', regex=True).str.strip()
            zid_df['clean_total'] = pd.to_numeric(zid_df['total'], errors='coerce').fillna(0)
            zid_df['clean_name'] = zid_df['customer_name'].astype(str).str.strip().str.lower()
            
            # تنظيف المنصة
            p_cols = payout_df.columns
            p_id_col = next((c for c in p_cols if 'id' in c.lower() or 'order' in c.lower() or 'طلب' in c), p_cols[0])
            p_amt_col = next((c for c in p_cols if 'amount' in c.lower() or 'total' in c.lower() or 'مبلغ' in c), p_cols[1] if len(p_cols)>1 else p_cols[0])
            p_mob_col = next((c for c in p_cols if 'mobile' in c.lower() or 'phone' in c.lower() or 'جوال' in c), None)
            
            payout_df['clean_p_id'] = payout_df[p_id_col].astype(str).str.strip()
            payout_df['clean_p_amount'] = pd.to_numeric(payout_df[amount_col], errors='coerce').fillna(0)
            payout_df['clean_p_mobile'] = payout_df[p_mob_col].astype(str).str.replace(r'\D', '', regex=True).str.strip() if p_mob_col else ""

            payout_ids = set(payout_df['clean_p_id'])
            gateway_status = []
            
            for idx, row in zid_df.iterrows():
                z_id = row['clean_id']
                z_mob = row['clean_mobile']
                z_tot = row['clean_total']
                
                if z_id in payout_ids:
                    gateway_status.append("مطابق برقم الطلب ✅")
                else:
                    p_found = payout_df[(payout_df['clean_p_amount'] == z_tot) & ((payout_df['clean_p_mobile'] == z_mob) if z_mob != "" else True)]
                    if not p_found.empty:
                        gateway_status.append("مطابق ذكي (جوال+مبلغ) ⚠️")
                    else:
                        gateway_status.append("مفقود بالمنصة ❌")

            zid_df['حالة_المطابقة_مع_المنصة'] = gateway_status

            st.success("✨ تمت المرحلة الأولى بنجاح! يمكنك الآن الانتقال للمرحلة الثانية ومطابقة النظام الداخلي.")
            
        except Exception as e:
            st.error(f"خطأ في معالجة ملفات المرحلة الأولى: {e}")

    st.divider()

    # --- المرحلة الثانية: مطابقة الفواتير بالنظام الداخلي ---
    st.subheader("📌 المرحلة الثانية: المطابقة مع النظام الداخلي للشركة (فواتير النظام)")
    st.markdown("<p style='text-align: center; color: #4b5563;'>سيقوم النظام بمطابقة الطلبات بالاعتماد على: <b>(رقم المرجع + رقم الجوال + اسم العميل)</b> لضمان دقة 100%.</p>", unsafe_allow_html=True)
    
    system_file = st.file_uploader("3️⃣ ارفع ملف فواتير النظام الداخلي (Excel / CSV)", type=["csv", "xlsx"], key="system")

    if system_file:
        with st.spinner("⏳ جاري مطابقة الطلبات مع فواتير النظام الداخلي..."):
            try:
                system_df = pd.read_csv(system_file) if system_file.name.endswith('.csv') else pd.read_excel(system_file)
                
                # تنظيف ملف النظام الداخلي
                s_cols = system_df.columns
                s_ref_col = next((c for c in s_cols if 'مرجع' in c.lower() or 'ref' in c.lower() or 'order' in c.lower() or 'رقم' in c), s_cols[0])
                s_amt_col = next((c for c in s_cols if 'مبلغ' in c.lower() or 'amount' in c.lower() or 'total' in c.lower()), s_cols[3] if len(s_cols)>3 else s_cols[1])
                s_mob_col = next((c for c in s_cols if 'موبايل' in c.lower() or 'جوال' in c.lower() or 'phone' in c.lower()), None)
                s_name_col = next((c for c in s_cols if 'اسم' in c.lower() or 'name' in c.lower() or 'العميل' in c), None)
                
                system_df['clean_s_ref'] = system_df[s_ref_col].astype(str).str.strip()
                system_df['clean_s_amount'] = pd.to_numeric(system_df[s_amt_col], errors='coerce').fillna(0)
                system_df['clean_s_mobile'] = system_df[s_mob_col].astype(str).str.replace(r'\D', '', regex=True).str.strip() if s_mob_col else ""
                system_df['clean_s_name'] = system_df[s_name_col].astype(str).str.strip().str.lower() if s_name_col else ""

                system_refs = set(system_df['clean_s_ref'])
                system_status = []
                
                for idx, row in zid_df.iterrows():
                    z_id = row['clean_id']
                    z_mob = row['clean_mobile']
                    z_name = row['clean_name']
                    z_tot = row['clean_total']
                    
                    # 1. المطابقة المباشرة برقم المرجع
                    if z_id in system_refs:
                        system_status.append("مفوتر بالسيستم (برقم المرجع) ✅")
                    else:
                        # 2. المطابقة الذكية عند فقدان المرجع: (رقم الجوال + تطابق الاسم أو المبلغ)
                        match_cond = (system_df['clean_s_amount'] == z_tot)
                        if z_mob != "":
                            match_cond = match_cond & (system_df['clean_s_mobile'] == z_mob)
                        
                        s_found = system_df[match_cond]
                        if not s_found.empty:
                            system_status.append("مفوتر بالسيستم (بالجوال والمبلغ) ⚠️")
                        else:
                            system_status.append("غير مسجل بالسيستم الداخلي ❌")

                zid_df['حالة_المطابقة_مع_السيستم'] = system_status

                st.divider()
                
                # مؤشرات الأداء الشاملة
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("📦 إجمالي الطلبات", len(zid_df))
                m2.metric("✅ مطابقة المنصة", sum(1 for x in zid_df['حالة_المطابقة_مع_المنصة'] if "مفقود" not in x))
                m3.metric("🧾 مفوتر بالسيستم الداخلي", sum(1 for x in zid_df['حالة_المطابقة_مع_السيستم'] if "غير مسجل" not in x))
                m4.metric("❌ طلبات مفقودة / ناقصة", sum(1 for x in zid_df['حالة_المطابقة_مع_المنصة'] if "مفقود" in x) + sum(1 for x in zid_df['حالة_المطابقة_مع_السيستم'] if "غير مسجل" in x))

                st.divider()
                
                st.subheader("📋 التقرير المرحلي الشامل (زد ➔ المنصة ➔ السيستم)")
                display_cols = ['id', 'customer_name', 'customer_mobile', 'total', 'حالة_المطابقة_مع_المنصة', 'حالة_المطابقة_مع_السيستم', 'added_at (Asia/Riyadh)']
                available_cols = [c for c in display_cols if c in zid_df.columns]
                st.dataframe(zid_df[available_cols], use_container_width=True, height=420)

                st.markdown("<br>", unsafe_allow_html=True)
                
                # زر التحميل بصيغة Excel
                col_b1, col_b2, col_b3 = st.columns([1, 2, 1])
                with col_b2:
                    excel_data = zid_df.to_csv(index=False).encode('utf-8-sig')
                    st.download_button(
                        label="📥 تحميل التقرير النهائي الشامل بصيغة Excel",
                        data=excel_data,
                        file_name="Final_Complete_Reconciliation_Report.csv",
                        mime="text/csv",
                        use_container_width=True
                    )

            except Exception as e:
                st.error(f"حدث خطأ أثناء معالجة فواتير النظام الداخلي: {e}")
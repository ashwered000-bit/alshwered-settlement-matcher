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
st.markdown("<p style='text-align: center; color: #4b5563;'>المطابقة الذكية المتقدمة والمتوافقة مع كافة بوابات الدفع (بما فيها تمارا وزد باي)</p>", unsafe_allow_html=True)

st.divider()

# --- المرحلة الأولى: مطابقة زد مع المنصة ---
st.subheader("📌 المرحلة الأولى: مطابقة طلبات زد مع كشوفات المنصة")
col1, col2 = st.columns(2, gap="medium")

with col1:
    zid_file = st.file_uploader("1️⃣ ارفع ملف طلبات زد (CSV / Excel)", type=["csv", "xlsx"], key="zid")

with col2:
    gateway_name = st.selectbox("اختر اسم البوابة:", ["زد باي (ZidPay)", "تمارا (Tamara)", "تابي (Tabby)", "مس بي (MisPay)", "إمكان (Emkan)", "مدفوع (Madfooat)"])
    payout_file = st.file_uploader("2️⃣ ارفع كشف تسوية المنصة (CSV / Excel)", type=["csv", "xlsx"], key="payout")

if zid_file and payout_file:
    with st.spinner("⏳ جاري تحليل المطابقة مع المنصة بدقة عالية..."):
        try:
            zid_df = pd.read_csv(zid_file) if zid_file.name.endswith('.csv') else pd.read_excel(zid_file)
            
            # قراءة ملف المنصة بحسب نوعه (فحص فاصل الترميز لـ CSV إن وجد)
            try:
                payout_df = pd.read_csv(payout_file, encoding='utf-8') if payout_file.name.endswith('.csv') else pd.read_excel(payout_file)
            except:
                payout_df = pd.read_csv(payout_file, encoding='latin1') if payout_file.name.endswith('.csv') else pd.read_excel(payout_file)
            
            # تنظيف بيانات زد وتوحيدها
            zid_df['clean_id'] = pd.to_numeric(zid_df['id'], errors='coerce').fillna(0).astype('int64').astype(str).str.strip()
            zid_df['clean_mobile'] = zid_df['customer_mobile'].astype(str).str.replace(r'\D', '', regex=True).str.strip()
            zid_df['clean_total'] = pd.to_numeric(zid_df['total'], errors='coerce').fillna(0).round(2)
            zid_df['clean_name'] = zid_df['customer_name'].astype(str).str.strip().str.lower()
            
            # البحث الذكي والديناميكي عن أعمدة المنصة (وخصوصاً تمارا التي تستخدم Merchant Order ID أو Reference)
            p_cols = payout_df.columns
            p_cols_lower = [str(c).lower() for c in p_cols]
            
            # البحث عن عمود رقم الطلب في المنصة
            p_id_col = None
            for key in ['merchant order id', 'order reference', 'reference', 'order_id', 'order id', 'id', 'رقم الطلب', 'المرجع']:
                for idx, col_l in enumerate(p_cols_lower):
                    if key in col_l:
                        p_id_col = p_cols[idx]
                        break
                if p_id_col:
                    break
            if not p_id_col:
                p_id_col = p_cols[0] # افتراضي أول عمود

            # البحث عن عمود المبلغ في المنصة
            p_amt_col = None
            for key in ['amount', 'total', 'paid', 'مبلغ', 'الإجمالي']:
                for idx, col_l in enumerate(p_cols_lower):
                    if key in col_l:
                        p_amt_col = p_cols[idx]
                        break
                if p_amt_col:
                    break
            if not p_amt_col:
                p_amt_col = p_cols[1] if len(p_cols) > 1 else p_cols[0]

            # البحث عن عمود الجوال في المنصة
            p_mob_col = None
            for key in ['mobile', 'phone', 'customer_mobile', 'جوال', 'هاتف']:
                for idx, col_l in enumerate(p_cols_lower):
                    if key in col_l:
                        p_mob_col = p_cols[idx]
                        break
                if p_mob_col:
                    break

            # تجهيز وتنظيف أعمدة المنصة
            payout_df['clean_p_id'] = payout_df[p_id_col].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
            payout_df['clean_p_amount'] = pd.to_numeric(payout_df[p_amt_col], errors='coerce').fillna(0).round(2)
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
                    # مطابقة ذكية بديلة (المبلغ + الجوال)
                    p_found = payout_df[(payout_df['clean_p_amount'] == z_tot) & ((payout_df['clean_p_mobile'] == z_mob) if z_mob != "" else True)]
                    if not p_found.empty:
                        gateway_status.append("مطابق ذكي (جوال+مبلغ) ⚠️")
                    else:
                        gateway_status.append("مفقود بالمنصة ❌")

            zid_df['حالة_المطابقة_مع_المنصة'] = gateway_status

            st.success(f"✨ تمت مطابقة ملف {gateway_name} بنجاح! شاهد النتائج أو حمل التقرير أدناه:")
            
            st.dataframe(zid_df[['id', 'customer_name', 'customer_mobile', 'total', 'حالة_المطابقة_مع_المنصة', 'added_at (Asia/Riyadh)']], use_container_width=True, height=300)
            
            col_bp1, col_bp2, col_bp3 = st.columns([1, 2, 1])
            with col_bp2:
                gateway_excel_data = zid_df.to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    label=f"📥 تحميل تقرير مطابقة المنصة ({gateway_name}) فقط",
                    data=gateway_excel_data,
                    file_name=f"Gateway_Reconciliation_{gateway_name}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            
        except Exception as e:
            st.error(f"حدث خطأ أثناء معالجة ملفات المنصة: {e}")

    st.divider()

    # --- المرحلة الثانية: مطابقة الفواتير بالنظام الداخلي ---
    st.subheader("📌 المرحلة الثانية: المطابقة مع النظام الداخلي للشركة (فواتير النظام)")
    st.markdown("<p style='text-align: center; color: #4b5563;'>سيقوم النظام بالبحث عن رقم الطلب في <b>جميع أعمدة النظام الداخلي</b>، أو مطابقة (الجوال + المبلغ + الاسم) بدقة.</p>", unsafe_allow_html=True)
    
    system_file = st.file_uploader("3️⃣ ارفع ملف فواتير النظام الداخلي (Excel / CSV)", type=["csv", "xlsx"], key="system")

    if system_file:
        with st.spinner("⏳ جاري المطابقة الشاملة مع فواتير النظام الداخلي..."):
            try:
                system_df = pd.read_csv(system_file) if system_file.name.endswith('.csv') else pd.read_excel(system_file)
                
                # البحث الشامل في كافة أعمدة النظام الداخلي
                system_all_values = set()
                for col in system_df.columns:
                    cleaned_col = pd.to_numeric(system_df[col], errors='coerce').fillna(0).astype('int64').astype(str).str.strip()
                    system_all_values.update(cleaned_col[cleaned_col != '0'].tolist())
                    str_col = system_df[col].astype(str).str.strip()
                    system_all_values.update(str_col.tolist())

                s_cols = system_df.columns
                s_amt_col = next((c for c in s_cols if 'مبلغ' in str(c).lower() or 'amount' in str(c).lower() or 'total' in str(c).lower()), s_cols[3] if len(s_cols)>3 else s_cols[1])
                s_mob_col = next((c for c in s_cols if 'موبايل' in str(c).lower() or 'جوال' in str(c).lower() or 'phone' in str(c).lower()), None)
                s_name_col = next((c for c in s_cols if 'اسم' in str(c).lower() or 'name' in str(c).lower() or 'العميل' in str(c)), None)
                
                system_df['clean_s_amount'] = pd.to_numeric(system_df[s_amt_col], errors='coerce').fillna(0).round(2)
                system_df['clean_s_mobile'] = system_df[s_mob_col].astype(str).str.replace(r'\D', '', regex=True).str.strip() if s_mob_col else ""
                system_df['clean_s_name'] = system_df[s_name_col].astype(str).str.strip().str.lower() if s_name_col else ""

                system_status = []
                
                for idx, row in zid_df.iterrows():
                    z_id = row['clean_id']
                    z_mob = row['clean_mobile']
                    z_name = row['clean_name']
                    z_tot = row['clean_total']
                    
                    if z_id in system_all_values:
                        system_status.append("مفوتر بالسيستم (برقم المرجع) ✅")
                    else:
                        match_cond = (system_df['clean_s_amount'] == z_tot)
                        if z_mob != "":
                            match_cond = match_cond & (system_df['clean_s_mobile'] == z_mob)
                        
                        s_found = system_df[match_cond]
                        
                        if not s_found.empty:
                            name_matched = False
                            if z_name != "":
                                for _, s_row in s_found.iterrows():
                                    s_n = str(s_row['clean_s_name'])
                                    z_parts = [p for p in z_name.split() if len(p) > 2]
                                    if any(p in s_n for p in z_parts):
                                        name_matched = True
                                        break
                            
                            if name_matched or z_name == "":
                                system_status.append("مفوتر بالسيستم (بالجوال + المبلغ + الاسم) ⚠️")
                            else:
                                system_status.append("مفوتر (جوال + مبلغ بدون توافق اسم) ⚠️")
                        else:
                            system_status.append("غير مسجل بالسيستم الداخلي ❌")

                zid_df['حالة_المطابقة_مع_السيستم'] = system_status

                st.divider()
                
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
                
                col_b1, col_b2, col_b3 = st.columns([1, 2, 1])
                with col_b2:
                    excel_data = zid_df.to_csv(index=False).encode('utf-8-sig')
                    st.download_button(
                        label="📥 تحميل التقرير النهائي الشامل (زد + المنصة + السيستم الداخلي)",
                        data=excel_data,
                        file_name="Final_Complete_Reconciliation_Report.csv",
                        mime="text/csv",
                        use_container_width=True
                    )

            except Exception as e:
                st.error(f"حدث خطأ أثناء معالجة فواتير النظام الداخلي: {e}")
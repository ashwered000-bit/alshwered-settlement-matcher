import streamlit as st
import pandas as pd
import numpy as np

# إعداد الصفحة وتوسيط المحتوى
st.set_page_config(
    page_title="نظام المطابقة المالية - شركة الشويرد",
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

st.title("📊 نظام المطابقة المالية للمنصات والفواتير")
st.markdown("<p style='text-align: center; color: #4b5563;'>النظام الموحد لمطابقة طلبات زد مع بوابات الدفع (تابي، تمارا، زد باي، مس بي، مدفوع، إمكان) والنظام الداخلي وفحص التكرار</p>", unsafe_allow_html=True)

st.divider()

# --- قسم رفع الملفات بالكامل ---
st.subheader("📁 رفع الملفات المطلوبة للمطابقة والفحص")
col_f1, col_f2, col_f3 = st.columns(3, gap="medium")

with col_f1:
    zid_file = st.file_uploader("1️⃣ ملف طلبات زد (CSV / Excel)", type=["csv", "xlsx"], key="zid")

with col_f2:
    gateway_name = st.selectbox("اختر بوابة الدفع:", ["تابي (Tabby)", "تمارا (Tamara)", "زد باي (ZidPay)", "مس بي (MisPay)", "مدفوع (Madfooat)", "إمكان (Emkan)"])
    payout_file = st.file_uploader("2️⃣ كشف تسوية المنصة / البوابة", type=["csv", "xlsx"], key="payout")

with col_f3:
    system_file = st.file_uploader("3️⃣ فواتير النظام الداخلي (اختياري)", type=["csv", "xlsx"], key="system")

st.divider()

zid_df = None
payout_df = None
system_df = None

# معالجة ملفات زد والمنصة
if zid_file and payout_file:
    try:
        zid_df = pd.read_csv(zid_file) if zid_file.name.endswith('.csv') else pd.read_excel(zid_file)
        
        try:
            payout_df = pd.read_csv(payout_file, encoding='utf-8') if payout_file.name.endswith('.csv') else pd.read_excel(payout_file)
        except:
            payout_df = pd.read_csv(payout_file, encoding='latin1') if payout_file.name.endswith('.csv') else pd.read_excel(payout_file)
        
        # لو ملف مدفوع، السطر الأول هو الهيدر الفعلي
        if gateway_name == "مدفوع (Madfooat)":
            payout_df = pd.read_excel(payout_file, header=1)

        # تنظيف بيانات زد
        zid_df['clean_id'] = pd.to_numeric(zid_df['id'], errors='coerce').fillna(0).astype('int64').astype(str).str.strip()
        zid_df['clean_mobile'] = zid_df['customer_mobile'].astype(str).str.replace(r'\D', '', regex=True).str.strip()
        zid_df['clean_total'] = pd.to_numeric(zid_df['total'], errors='coerce').fillna(0).round(2)
        zid_df['clean_name'] = zid_df['customer_name'].astype(str).str.strip().str.lower()
        
        # البحث الذكي لأعمدة المنصات (يشمل تابي Order number، تمارا، مس بي، مدفوع، وإمكان)
        p_cols = payout_df.columns
        p_cols_lower = [str(c).lower() for c in p_cols]
        
        p_id_col = None
        for key in ['order number', 'order id', 'order_id', 'الرقم المرجعي', 'merchant order id', 'order reference', 'reference', 'id', 'رقم الطلب', 'charge id', 'application number']:
            for idx, col_l in enumerate(p_cols_lower):
                if key in col_l:
                    p_id_col = p_cols[idx]
                    break
            if p_id_col:
                break
        if not p_id_col:
            p_id_col = p_cols[0]

        p_amt_col = None
        for key in ['captured amount', 'payment amount', 'amount', 'total', 'المبلغ', 'paid', 'الإجمالي', 'total bill amount', 'captured']:
            for idx, col_l in enumerate(p_cols_lower):
                if key in col_l:
                    p_amt_col = p_cols[idx]
                    break
            if p_amt_col:
                break
        if not p_amt_col:
            p_amt_col = p_cols[1] if len(p_cols) > 1 else p_cols[0]

        p_mob_col = None
        for key in ['customer phone number', 'mobile', 'phone', 'customer_mobile', 'رقم جوال العميل', 'جوال', 'هاتف']:
            for idx, col_l in enumerate(p_cols_lower):
                if key in col_l:
                    p_mob_col = p_cols[idx]
                    break
            if p_mob_col:
                break

        payout_df['clean_p_id'] = payout_df[p_id_col].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
        payout_df['clean_p_amount'] = pd.to_numeric(payout_df[p_amt_col], errors='coerce').fillna(0).round(2)
        payout_df['clean_p_mobile'] = payout_df[p_mob_col].astype(str).str.replace(r'\D', '', regex=True).str.strip() if p_mob_col else ""

        # إنشاء مجموعة بجميع النصوص والأرقام الموجودة في كشف المنصة
        payout_all_texts = set()
        for col in payout_df.columns:
            payout_all_texts.update(payout_df[col].astype(str).str.strip().tolist())

        gateway_status = []
        for idx, row in zid_df.iterrows():
            z_id = row['clean_id']
            z_mob = row['clean_mobile']
            z_tot = row['clean_total']
            
            if z_id in payout_all_texts:
                gateway_status.append("مطابق برقم الطلب ✅")
            else:
                p_found = payout_df[(payout_df['clean_p_amount'] == z_tot) & ((payout_df['clean_p_mobile'] == z_mob) if z_mob != "" else True)]
                if not p_found.empty:
                    gateway_status.append("مطابق ذكي (جوال+مبلغ) ⚠️")
                else:
                    gateway_status.append("مفقود بالمنصة ❌")

        zid_df['حالة_المطابقة_مع_المنصة'] = gateway_status

    except Exception as e:
        st.error(f"خطأ في معالجة ملف المنصة: {e}")

# معالجة فواتير النظام الداخلي
if zid_file is not None and system_file is not None and zid_df is not None:
    try:
        system_df = pd.read_csv(system_file) if system_file.name.endswith('.csv') else pd.read_excel(system_file)
        
        s_cols = system_df.columns
        s_cols_lower = [str(c).lower() for c in s_cols]
        
        s_ref_col = next((s_cols[idx] for idx, col_l in enumerate(s_cols_lower) if any(k in col_l for k in ['مرجع', 'reference', 'ref', 'order', 'رقم الفاتورة'])), s_cols[0])
        s_amt_col = next((s_cols[idx] for idx, col_l in enumerate(s_cols_lower) if any(k in col_l for k in ['مبلغ', 'amount', 'total', 'الإجمالي'])), s_cols[3] if len(s_cols)>3 else s_cols[1])
        s_mob_col = next((s_cols[idx] for idx, col_l in enumerate(s_cols_lower) if any(k in col_l for k in ['موبايل', 'جوال', 'phone', 'mobile'])), None)

        system_df['clean_s_ref'] = pd.to_numeric(system_df[s_ref_col], errors='coerce').fillna(0).astype('int64').astype(str).str.strip()
        system_df['clean_s_amount'] = pd.to_numeric(system_df[s_amt_col], errors='coerce').fillna(0).round(2)
        system_df['clean_s_mobile'] = system_df[s_mob_col].astype(str).str.replace(r'\D', '', regex=True).str.strip() if s_mob_col else ""

        system_refs_set = set(system_df['clean_s_ref'])
        system_status = []
        
        for idx, row in zid_df.iterrows():
            z_id = row['clean_id']
            z_mob = row['clean_mobile']
            z_tot = row['clean_total']
            
            if z_id in system_refs_set:
                system_status.append("مفوتر بالسيستم (برقم المرجع) ✅")
            else:
                match_cond = (system_df['clean_s_amount'] == z_tot)
                if z_mob != "":
                    match_cond = match_cond & (system_df['clean_s_mobile'] == z_mob)
                else:
                    match_cond = False
                
                s_found = system_df[match_cond]
                if not s_found.empty and z_mob != "":
                    system_status.append("مفوتر بالسيستم (برقم الجوال + المبلغ) ⚠️")
                else:
                    system_status.append("غير مسجل بالسيستم الداخلي ❌")

        zid_df['حالة_المطابقة_مع_السيستم'] = system_status

    except Exception as e:
        st.error(f"حدث خطأ أثناء معالجة فواتير النظام الداخلي: {e}")
elif zid_file is not None and zid_df is not None:
    zid_df['حالة_المطابقة_مع_السيستم'] = "لم يتم رفع ملف السيستم"

# عرض النتائج الشاملة
if zid_file is not None and zid_df is not None:
    st.subheader("📋 تقرير النتائج الشامل")
    
    display_cols = ['id', 'customer_name', 'customer_mobile', 'total']
    if 'حالة_المطابقة_مع_المنصة' in zid_df.columns:
        display_cols.append('حالة_المطابقة_مع_المنصة')
    if 'حالة_المطابقة_مع_السيستم' in zid_df.columns:
        display_cols.append('حالة_المطابقة_مع_السيستم')
    if 'added_at (Asia/Riyadh)' in zid_df.columns:
        display_cols.append('added_at (Asia/Riyadh)')
        
    available_cols = [c for c in display_cols if c in zid_df.columns]
    st.dataframe(zid_df[available_cols], use_container_width=True, height=380)

    st.markdown("<br>", unsafe_allow_html=True)
    
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

st.divider()

# --- قسم لفحص الفواتير المكررة ---
st.subheader("🔍 فحص الفواتير المكررة في النظام الداخلي")
st.markdown("<p style='text-align: center; color: #4b5563;'>ارفع ملف فواتير النظام الداخلي لفحص وكشف الفواتير المكررة.</p>", unsafe_allow_html=True)

dup_file = st.file_uploader("📂 ملف فواتير النظام الداخلي لفحص التكرار (Excel / CSV)", type=["csv", "xlsx"], key="duplicates_checker")

if dup_file:
    with st.spinner("⏳ جاري فحص السجلات والبحث عن التكرارات..."):
        try:
            dup_df = pd.read_csv(dup_file) if dup_file.name.endswith('.csv') else pd.read_excel(dup_file)
            d_cols = dup_df.columns
            d_cols_lower = [str(c).lower() for c in d_cols]
            
            d_ref_col = next((d_cols[idx] for idx, col_l in enumerate(d_cols_lower) if any(k in col_l for k in ['مرجع', 'reference', 'ref', 'order', 'رقم الفاتورة'])), d_cols[0])
            d_mob_col = next((d_cols[idx] for idx, col_l in enumerate(d_cols_lower) if any(k in col_l for k in ['موبايل', 'جوال', 'phone', 'mobile'])), None)
            
            dup_df['clean_ref'] = pd.to_numeric(dup_df[d_ref_col], errors='coerce').fillna(0).astype('int64').astype(str).str.strip()
            if d_mob_col:
                dup_df['clean_mob'] = dup_df[d_mob_col].astype(str).str.replace(r'\D', '', regex=True).str.strip()
            else:
                dup_df['clean_mob'] = ""

            ref_counts = dup_df['clean_ref'].value_counts()
            duplicated_refs = ref_counts[ref_counts > 1].index.tolist()
            
            mob_counts = dup_df[dup_df['clean_mob'] != '']['clean_mob'].value_counts()
            duplicated_mobs = mob_counts[mob_counts > 1].index.tolist()

            dup_status = []
            for idx, row in dup_df.iterrows():
                reasons = []
                if row['clean_ref'] in duplicated_refs and row['clean_ref'] != '0':
                    reasons.append("مرجع مكرر ⚠️")
                if row['clean_mob'] in duplicated_mobs and row['clean_mob'] != '':
                    reasons.append("جوال مكرر ⚠️")
                
                if reasons:
                    dup_status.append(" | ".join(reasons))
                else:
                    dup_status.append("سليم ✅")

            dup_df['حالة_الفاتورة'] = dup_status
            suspicious_df = dup_df[dup_df['حالة_الفاتورة'] != "سليم ✅"]
            
            st.warning(f"⚠️ تم العثور على **{len(suspicious_df)} فاتورة مكررة** تتطلب المراجعة التدقيقية!")
            
            if not suspicious_df.empty:
                st.dataframe(suspicious_df, use_container_width=True, height=300)
                col_d1, col_d2, col_d3 = st.columns([1, 2, 1])
                with col_d2:
                    dup_excel = suspicious_df.to_csv(index=False).encode('utf-8-sig')
                    st.download_button(
                        label="📥 تحميل تقرير الفواتير المكررة بصيغة Excel",
                        data=dup_excel,
                        file_name="Duplicate_Invoices_Report.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
            else:
                st.success("🎉 ممتاز جداً! لا توجد أي فواتير مكررة في الملف المرفوع.")

        except Exception as e:
            st.error(f"حدث خطأ أثناء فحص التكرار: {e}")
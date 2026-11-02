import streamlit as st
import pandas as pd
import numpy as np

# إعداد الصفحة وتوسيط المحتوى
st.set_page_config(
    page_title="نظام المطابقة والفحص المالي - شركة الشويرد",
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

st.title("📊 نظام المطابقة المالية والفحص الرقابي (زد ➔ المنصة ➔ السيستم ➔ كشف التكرار)")
st.markdown("<p style='text-align: center; color: #4b5563;'>المطابقة الدقيقة الصارمة + قسم مستقل لفحص الفواتير المكررة بالمرجع أو الجوال</p>", unsafe_allow_html=True)

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
    with st.spinner("⏳ جاري المطابقة مع المنصة..."):
        try:
            zid_df = pd.read_csv(zid_file) if zid_file.name.endswith('.csv') else pd.read_excel(zid_file)
            
            try:
                payout_df = pd.read_csv(payout_file, encoding='utf-8') if payout_file.name.endswith('.csv') else pd.read_excel(payout_file)
            except:
                payout_df = pd.read_csv(payout_file, encoding='latin1') if payout_file.name.endswith('.csv') else pd.read_excel(payout_file)
            
            # تنظيف بيانات زد
            zid_df['clean_id'] = pd.to_numeric(zid_df['id'], errors='coerce').fillna(0).astype('int64').astype(str).str.strip()
            zid_df['clean_mobile'] = zid_df['customer_mobile'].astype(str).str.replace(r'\D', '', regex=True).str.strip()
            zid_df['clean_total'] = pd.to_numeric(zid_df['total'], errors='coerce').fillna(0).round(2)
            zid_df['clean_name'] = zid_df['customer_name'].astype(str).str.strip().str.lower()
            
            # تنظيف المنصة
            p_cols = payout_df.columns
            p_cols_lower = [str(c).lower() for c in p_cols]
            
            p_id_col = None
            for key in ['merchant order id', 'order reference', 'reference', 'order_id', 'order id', 'id', 'رقم الطلب', 'المرجع']:
                for idx, col_l in enumerate(p_cols_lower):
                    if key in col_l:
                        p_id_col = p_cols[idx]
                        break
                if p_id_col:
                    break
            if not p_id_col:
                p_id_col = p_cols[0]

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

            p_mob_col = None
            for key in ['mobile', 'phone', 'customer_mobile', 'جوال', 'هاتف']:
                for idx, col_l in enumerate(p_cols_lower):
                    if key in col_l:
                        p_mob_col = p_cols[idx]
                        break
                if p_mob_col:
                    break

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
                    p_found = payout_df[(payout_df['clean_p_amount'] == z_tot) & ((payout_df['clean_p_mobile'] == z_mob) if z_mob != "" else True)]
                    if not p_found.empty:
                        gateway_status.append("مطابق ذكي (جوال+مبلغ) ⚠️")
                    else:
                        gateway_status.append("مفقود بالمنصة ❌")

            zid_df['حالة_المطابقة_مع_المنصة'] = gateway_status

            st.success(f"✨ تمت مطابقة ملف {gateway_name} بنجاح!")
            st.dataframe(zid_df[['id', 'customer_name', 'customer_mobile', 'total', 'حالة_المطابقة_مع_المنصة', 'added_at (Asia/Riyadh)']], use_container_width=True, height=250)
            
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
    st.markdown("<p style='text-align: center; color: #4b5563;'>المطابقة الصارمة: المرجع حصرياً، أو التحقق الإجباري برقم (الجوال + المبلغ).</p>", unsafe_allow_html=True)
    
    system_file = st.file_uploader("3️⃣ ارفع ملف فواتير النظام الداخلي (Excel / CSV) للمطابقة", type=["csv", "xlsx"], key="system")

    if system_file:
        with st.spinner("⏳ جاري المطابقة الدقيقة مع فواتير النظام الداخلي..."):
            try:
                system_df = pd.read_csv(system_file) if system_file.name.endswith('.csv') else pd.read_excel(system_file)
                
                s_cols = system_df.columns
                s_cols_lower = [str(c).lower() for c in s_cols]
                
                s_ref_col = None
                for key in ['مرجع', 'reference', 'ref', 'order', 'رقم الطلب']:
                    for idx, col_l in enumerate(s_cols_lower):
                        if key in col_l:
                            s_ref_col = s_cols[idx]
                            break
                    if s_ref_col:
                        break
                if not s_ref_col:
                    s_ref_col = s_cols[0]

                s_amt_col = None
                for key in ['مبلغ', 'amount', 'total', 'الإجمالي']:
                    for idx, col_l in enumerate(s_cols_lower):
                        if key in col_l:
                            s_amt_col = s_cols[idx]
                            break
                    if s_amt_col:
                        break
                if not s_amt_col:
                    s_amt_col = s_cols[3] if len(s_cols) > 3 else s_cols[1]

                s_mob_col = None
                for key in ['موبايل', 'جوال', 'phone', 'mobile']:
                    for idx, col_l in enumerate(s_cols_lower):
                        if key in col_l:
                            s_mob_col = s_cols[idx]
                            break
                    if s_mob_col:
                        break

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
                st.dataframe(zid_df[available_cols], use_container_width=True, height=350)

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

    st.divider()

    # --- المرحلة الثالثة: فحص وتدقيق الفواتير المكررة (اختياري ومستقل) ---
    st.subheader("🔍 المرحلة الثالثة (اختيارية): كشف الفواتير المكررة في النظام الداخلي")
    st.markdown("<p style='text-align: center; color: #4b5563;'>ارفع ملف فواتير النظام الداخلي هنا لفحص وتدقيق أي فواتير مكررة (برقم المرجع أو برقم الجوال).</p>", unsafe_allow_html=True)
    
    dup_file = st.file_uploader("📂 ارفع ملف فواتير النظام الداخلي لفحص التكرار (Excel / CSV)", type=["csv", "xlsx"], key="duplicates_checker")

    if dup_file:
        with st.spinner("⏳ جاري فحص سجلات الفواتير والبحث عن التكرارات..."):
            try:
                dup_df = pd.read_csv(dup_file) if dup_file.name.endswith('.csv') else pd.read_excel(dup_file)
                
                # تحديد الأعمدة بذكاء
                d_cols = dup_df.columns
                d_cols_lower = [str(c).lower() for c in d_cols]
                
                d_ref_col = next((d_cols[idx] for idx, col_l in enumerate(d_cols_lower) if any(k in col_l for k in ['مرجع', 'reference', 'ref', 'order'])), d_cols[0])
                d_mob_col = next((d_cols[idx] for idx, col_l in enumerate(d_cols_lower) if any(k in col_l for k in ['موبايل', 'جوال', 'phone', 'mobile'])), None)
                
                dup_df['clean_ref'] = pd.to_numeric(dup_df[d_ref_col], errors='coerce').fillna(0).astype('int64').astype(str).str.strip()
                if d_mob_col:
                    dup_df['clean_mob'] = dup_df[d_mob_col].astype(str).str.replace(r'\D', '', regex=True).str.strip()
                else:
                    dup_df['clean_mob'] = ""

                # فلترة التكرارات
                ref_counts = dup_df['clean_ref'].value_counts()
                duplicated_refs = ref_counts[ref_counts > 1].index.tolist()
                
                mob_counts = dup_df[dup_df['clean_mob'] != '']['clean_mob'].value_counts()
                duplicated_mobs = mob_counts[mob_counts > 1].index.tolist()

                # إضافة عمود حالة التكرار للعرض
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
                
                # فصل فقط المكرر للعرض الواضح
                suspicious_df = dup_df[dup_df['حالة_الفاتورة'] != "سليم ✅"]
                
                st.warning(f"⚠️ تم العثور على **{len(suspicious_df)} فاتورة مكررة** (برقم المرجع أو الجوال) تتطلب المراجعة التدقيقية!")
                
                if not suspicious_df.empty:
                    st.dataframe(suspicious_df, use_container_width=True, height=300)
                    
                    col_d1, col_d2, col_d3 = st.columns([1, 2, 1])
                    with col_d2:
                        dup_excel = suspicious_df.to_csv(index=False).encode('utf-8-sig')
                        st.download_button(
                            label="📥 تحميل تقرير الفواتير المكررة فقط بصيغة Excel",
                            data=dup_excel,
                            file_name="Duplicate_Invoices_Report.csv",
                            mime="text/csv",
                            use_container_width=True
                        )
                else:
                    st.success("🎉 رائع جداً! لا توجد أي فواتير مكررة في الملف المرفوع.")

            except Exception as e:
                st.error(f"حدث خطأ أثناء فحص التكرار: {e}")
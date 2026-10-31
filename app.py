import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="نظام مطابقة تسويات شركة الشويرد", layout="wide")

st.title("🛡️ النظام الذكي للمطابقة الرباعية الدقيقة (زد و بوابات الدفع)")
st.markdown("قم برفع ملف طلبات متجر **زد** وملف كشف تسوية البوابة وسيقوم النظام بالمطابقة الفورية عبر (رقم الطلب ➔ رقم الجوال ➔ المبلغ).")

col1, col2 = st.columns(2)

with col1:
    st.subheader("1. ملف طلبات متجر زد")
    zid_file = st.file_uploader("ارفع ملف طلبات زد (Excel/CSV)", type=["csv", "xlsx"], key="zid")

with col2:
    st.subheader("2. كشف تسوية المنصة")
    gateway_name = st.selectbox("اختر اسم البوابة:", ["تابي (Tabby)", "تمارا (Tamara)", "مس بي (MisPay)", "إمكان (Emkan)", "مدفوع (Madfooat)", "زد باي (ZidPay)"])
    payout_file = st.file_uploader("ارفع كشف التسوية الخاص بالمنصة", type=["csv", "xlsx"], key="payout")

if zid_file and payout_file:
    try:
        # قراءة الملفات
        zid_df = pd.read_csv(zid_file) if zid_file.name.endswith('.csv') else pd.read_excel(zid_file)
        payout_df = pd.read_csv(payout_file) if payout_file.name.endswith('.csv') else pd.read_excel(payout_file)

        st.success("تم قراءة الملفات بنجاح. جاري تشغيل محرك المطابقة الرباعية...")

        # تنظيف وتوحيد بيانات زد الأساسية
        zid_df['clean_id'] = zid_df['id'].astype(str).str.strip()
        zid_df['clean_mobile'] = zid_df['customer_mobile'].astype(str).str.replace(r'\D', '', regex=True).str.strip()
        zid_df['clean_total'] = pd.to_numeric(zid_df['total'], errors='coerce').fillna(0)

        # البحث الديناميكي عن الأعمدة في ملف المنصة
        payout_cols = payout_df.columns
        id_col = next((c for c in payout_cols if 'id' in c.lower() or 'order' in c.lower() or 'طلب' in c), payout_cols[0])
        amount_col = next((c for c in payout_cols if 'amount' in c.lower() or 'total' in c.lower() or 'مبلغ' in c), payout_cols[1] if len(payout_cols)>1 else payout_cols[0])
        mobile_col = next((c for c in payout_cols if 'mobile' in c.lower() or 'phone' in c.lower() or 'جوال' in c), None)

        # تنظيف بيانات المنصة
        payout_df['clean_payout_id'] = payout_df[id_col].astype(str).str.strip()
        payout_df['clean_payout_amount'] = pd.to_numeric(payout_df[amount_col], errors='coerce').fillna(0)
        if mobile_col:
            payout_df['clean_payout_mobile'] = payout_df[mobile_col].astype(str).str.replace(r'\D', '', regex=True).str.strip()
        else:
            payout_df['clean_payout_mobile'] = ""

        matched_order_ids = set()

        # 1. المستوى الأول: المطابقة المباشرة برقم الطلب (Order ID)
        payout_ids_set = set(payout_df['clean_payout_id'])
        exact_match = zid_df[zid_df['clean_id'].isin(payout_ids_set)]
        matched_order_ids.update(exact_match['clean_id'].tolist())

        # 2. المستوى الثاني: المطابقة الذكية بالجوال والمبلغ
        remaining_zid = zid_df[~zid_df['clean_id'].isin(matched_order_ids)]

        secondary_matched_indices = []
        for idx, row in remaining_zid.iterrows():
            z_mobile = row['clean_mobile']
            z_total = row['clean_total']

            match_cond = (payout_df['clean_payout_amount'] == z_total)
            if z_mobile != "":
                match_cond = match_cond & (payout_df['clean_payout_mobile'] == z_mobile)

            found = payout_df[match_cond]
            if not found.empty:
                secondary_matched_indices.append(idx)
                matched_order_ids.add(row['clean_id'])

        secondary_match = remaining_zid.loc[secondary_matched_indices] if secondary_matched_indices else pd.DataFrame()

        # الطلبات المفقودة حقاً
        truly_missing = zid_df[~zid_df['clean_id'].isin(matched_order_ids)]

        st.divider()

        # مؤشرات الأداء
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("إجمالي طلبات زد", len(zid_df))
        m2.metric("مطابقة تامة برقم الطلب", len(exact_match))
        m3.metric("مطابقة ذكية (جوال + مبلغ)", len(secondary_match))
        m4.metric("❌ الطلبات المفقودة حقاً", len(truly_missing), delta_color="inverse")

        if len(truly_missing) > 0:
            st.error(f"⚠️ تنبيه دقيق: تبين وجود **{len(truly_missing)} طلب** لم تُسدّدها بوابة {gateway_name} حتى الآن!")

            display_cols = ['id', 'customer_name', 'customer_mobile', 'payment_method', 'total', 'added_at (Asia/Riyadh)']
            available_display_cols = [c for c in display_cols if c in truly_missing.columns]

            missing_report = truly_missing[available_display_cols]
            st.dataframe(missing_report, use_container_width=True)

            csv_data = missing_report.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label=f"📥 تحميل تقرير الطلبات المفقودة لدعم {gateway_name}",
                data=csv_data,
                file_name=f"Verified_Missing_Orders_{gateway_name}.csv",
                mime="text/csv"
            )
        else:
            st.balloons()
            st.success("🎉 ممتاز جداً! مطابقة بنسبة 100% ولا توجد أي مبالغ معلقة.")

    except Exception as e:
        st.error(f"حدث خطأ أثناء معالجة المطابقة: {e}")

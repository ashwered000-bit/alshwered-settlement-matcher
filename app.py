import streamlit as st
import pandas as pd
import numpy as np

# إعداد الصفحة وتصميمها
st.set_page_config(
    page_title="نظام المطابقة المالية الذكي - شركة الشويرد",
    page_icon="📊",
    layout="wide"
)

# تخصيص التصميم واللوان (CSS عصري وجميل)
st.markdown("""
    <style>
    .main {
        background-color: #f8f9fa;
    }
    .stMetric {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    </style>
""", unsafe_allow_html=True)

st.title("📊 نظام المطابقة المالية الذكي (زد وبوابات الدفع)")
st.markdown("مرحباً بك! نظام احترافي لفحص ومطابقة جميع طلبات المتجر مع كشوفات التسوية واستخراج تقرير شامل بصيغة Excel.")

st.divider()

# قسم رفع الملفات بتصميم منظم
col1, col2 = st.columns(2)

with col1:
    st.markdown("### 📥 1. ملف طلبات متجر زد")
    zid_file = st.file_uploader("اختر ملف طلبات زد (CSV / Excel)", type=["csv", "xlsx"], key="zid")

with col2:
    st.markdown("### 📥 2. كشف تسوية المنصة")
    gateway_name = st.selectbox("اختر اسم البوابة:", ["زد باي (ZidPay)", "تابي (Tabby)", "تمارا (Tamara)", "مس بي (MisPay)", "إمكان (Emkan)", "مدفوع (Madfooat)"])
    payout_file = st.file_uploader("اختر ملف تسوية المنصة (CSV / Excel)", type=["csv", "xlsx"], key="payout")

if zid_file and payout_file:
    with st.spinner("⏳ جاري معالجة الملفات ومطابقة البيانات بدقة..."):
        try:
            # قراءة الملفات
            zid_df = pd.read_csv(zid_file) if zid_file.name.endswith('.csv') else pd.read_excel(zid_file)
            payout_df = pd.read_csv(payout_file) if payout_file.name.endswith('.csv') else pd.read_excel(payout_file)
            
            # توحيد بيانات زد
            zid_df['clean_id'] = zid_df['id'].astype(str).str.strip()
            zid_df['clean_mobile'] = zid_df['customer_mobile'].astype(str).str.replace(r'\D', '', regex=True).str.strip()
            zid_df['clean_total'] = pd.to_numeric(zid_df['total'], errors='coerce').fillna(0)
            
            # البحث الديناميكي عن أعمدة المنصة
            payout_cols = payout_df.columns
            id_col = next((c for c in payout_cols if 'id' in c.lower() or 'order' in c.lower() or 'طلب' in c), payout_cols[0])
            amount_col = next((c for c in payout_cols if 'amount' in c.lower() or 'total' in c.lower() or 'مبلغ' in c), payout_cols[1] if len(payout_cols)>1 else payout_cols[0])
            mobile_col = next((c for c in payout_cols if 'mobile' in c.lower() or 'phone' in c.lower() or 'جوال' in c), None)
            
            payout_df['clean_payout_id'] = payout_df[id_col].astype(str).str.strip()
            payout_df['clean_payout_amount'] = pd.to_numeric(payout_df[amount_col], errors='coerce').fillna(0)
            if mobile_col:
                payout_df['clean_payout_mobile'] = payout_df[mobile_col].astype(str).str.replace(r'\D', '', regex=True).str.strip()
            else:
                payout_df['clean_payout_mobile'] = ""

            # قائمة لتحديد حالة كل طلب
            matching_status = []
            matched_order_ids = set()
            
            payout_ids_set = set(payout_df['clean_payout_id'])
            
            # تحليل كل طلب في زد
            for idx, row in zid_df.iterrows():
                z_id = row['clean_id']
                z_mobile = row['clean_mobile']
                z_total = row['clean_total']
                
                if z_id in payout_ids_set:
                    matching_status.append("مطابق برقم الطلب ✅")
                    matched_order_ids.add(z_id)
                else:
                    # فحص المطابقة الذكية (جوال + مبلغ)
                    match_cond = (payout_df['clean_payout_amount'] == z_total)
                    if z_mobile != "":
                        match_cond = match_cond & (payout_df['clean_payout_mobile'] == z_mobile)
                    found = payout_df[match_cond]
                    
                    if not found.empty:
                        matching_status.append("مطابق ذكي (جوال + مبلغ) ⚠️")
                        matched_order_ids.add(z_id)
                    else:
                        matching_status.append("مفقود (غير موجود في التسوية) ❌")

            zid_df['حالة_المطابقة'] = matching_status
            
            # حساب الإحصائيات
            total_orders = len(zid_df)
            exact_matched = matching_status.count("مطابق برقم الطلب ✅")
            smart_matched = matching_status.count("مطابق ذكي (جوال + مبلغ) ⚠️")
            missing_count = matching_status.count("مفقود (غير موجود في التسوية) ❌")
            
            st.divider()
            
            # عرض مؤشرات الأداء بشكل عصري
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("📦 إجمالي طلبات زد", total_orders)
            m2.metric("✅ مطابقة برقم الطلب", exact_matched)
            m3.metric("⚠️ مطابقة ذكية", smart_matched)
            m4.metric("❌ الطلبات المفقودة", missing_count)
            
            st.divider()
            
            # قسم النتائج والتحميل
            st.subheader("📋 تقرير المطابقة الشامل لجميع الطلبات")
            st.markdown("يتضمن الجدول أدناه حالة كل طلب في متجر زد وهل تم تسويته في المنصة أم لا:")
            
            # عرض عينة مرتبة للمحاسب
            display_cols = ['id', 'customer_name', 'customer_mobile', 'payment_method', 'total', 'حالة_المطابقة', 'added_at (Asia/Riyadh)']
            available_cols = [c for c in display_cols if c in zid_df.columns]
            st.dataframe(zid_df[available_cols], use_container_width=True, height=400)
            
            # زر تحميل الملف الكامل إكسل
            excel_data = zid_df.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label=f"📥 تحميل التقرير الشامل الكامل (Excel/CSV) لجميع الطلبات وحالاتها",
                data=excel_data,
                file_name=f"Comprehensive_Reconciliation_{gateway_name}.csv",
                mime="image/csv" # CSV compatible
            )
            
        except Exception as e:
            st.error(f"حدث خطأ أثناء معالجة الملفات، تأكد من صحة الأعمدة: {e}")
else:
    st.info("💡 **تعليمات:** يرجى رفع ملف طلبات زد وملف تسوية المنصة في الأعلى لتبدأ المطابقة الفورية واستخراج التقارير.")
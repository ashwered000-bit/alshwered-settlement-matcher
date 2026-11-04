import io
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="نظام المطابقة المالية الآلي - شركة الشويرد", layout="wide"
)

st.title("لوحة المطابقة المالية الموحدة - شركة الشويرد")
st.markdown("---")

# ---------------------------------------------------------
# واجهة المحاسب: الشريط الجانبي لرفع الملفات
# ---------------------------------------------------------
st.sidebar.header("خيارات ومطابقة المحاسب")
st.sidebar.markdown(
    "قم برفع ملفات التقارير الخاصة بمتجر زد وأونكس برو لإجراء المطابقة"
    " الفورية."
)

# رفع ملف زد
zid_file = st.sidebar.file_uploader(
    "1️⃣ رفع تقرير طلبات زد (Zid Export)", type=["xlsx", "csv"]
)

# رفع ملف أونكس برو
onyx_file = st.sidebar.file_uploader(
    "2️⃣ رفع كشف أونكس برو (Onyx Pro)", type=["xlsx", "csv"]
)

st.sidebar.markdown("---")


# دالة مساعدة لقراءة الملفات بمرونة
def load_uploaded_file(uploaded_file):
  if uploaded_file is None:
    return pd.DataFrame()
  try:
    if uploaded_file.name.endswith(".csv"):
      return pd.read_csv(uploaded_file)
    else:
      return pd.read_excel(uploaded_file)
  except Exception as e:
    st.error(f"خطأ في قراءة الملف {uploaded_file.name}: {e}")
    return pd.DataFrame()


df_zid_raw = load_uploaded_file(zid_file)
df_onyx_raw = load_uploaded_file(onyx_file)

if not df_zid_raw.empty:
  # توحيد أسماء أعمدة زد وتنقيتها
  df_zid_raw.columns = [str(c).lower().strip() for c in df_zid_raw.columns]

  # استخراج الأعمدة بمرونة حسب مسميات زد الشهيرة
  parsed = []
  for _, row in df_zid_raw.iterrows():
    # البحث عن القيم بالأعمدة المختلفة المحتملة
    order_id = str(
        row.get("id")
        or row.get("order_id")
        or row.get("رقم الطلب")
        or row.get("الرقم")
        or ""
    )
    mobile = str(
        row.get("customer_phone")
        or row.get("mobile")
        or row.get("phone")
        or row.get("الجوال")
        or row.get("رقم الجوال")
        or ""
    ).strip()
    date = str(
        row.get("created_at")
        or row.get("date")
        or row.get("التاريخ")
        or ""
    )[:10]
    payment_method = str(
        row.get("payment_method")
        or row.get("payment")
        or row.get("وسيلة الدفع")
        or "غير محدد"
    )
    total = float(
        row.get("order_total")
        or row.get("total")
        or row.get("المبلغ")
        or row.get("الاجمالي")
        or 0.0
    )
    deposit_id = str(
        row.get("settlement_id")
        or row.get("deposit_id")
        or row.get("رقم الإيداع")
        or row.get("رقم التسوية")
        or ""
    ).strip()

    parsed.append({
        "المنصة / البوابة": "متجر زد (Zid)",
        "رقم الطلب / المرجع": order_id,
        "رقم الجوال": mobile,
        "تاريخ العملية": date,
        "وسيلة الدفع": payment_method,
        "المبلغ": total,
        "رقم الإيداع / التسوية": deposit_id,
    })

  master_df = pd.DataFrame(parsed)

  # معالجة ملف أونكس برو للمطابقة
  onyx_matched_keys = set()
  if not df_onyx_raw.empty:
    df_onyx_raw.columns = [str(c).lower().strip() for c in df_onyx_raw.columns]
    o_ref = next(
        (
            c
            for c in df_onyx_raw.columns
            if "order" in c or "reference" in c or "مرجع" in c or "فاتورة" in c
        ),
        None,
    )
    o_phone = next(
        (
            c
            for c in df_onyx_raw.columns
            if "phone" in c or "mobile" in c or "جوال" in c
        ),
        None,
    )

    if o_ref:
      onyx_matched_keys.update(
          df_onyx_raw[o_ref].astype(str).str.strip().tolist()
      )
    if o_phone:
      onyx_matched_keys.update(
          df_onyx_raw[o_phone].astype(str).str.strip().tolist()
      )
    st.sidebar.success("تم قراءة ملف أونكس برو بنجاح")


  # تحديد حالة المطابقة (وجود رقم إيداع/تسوية)
  def resolve_status(row):
    dep = str(row["رقم الإيداع / التسوية"]).strip().lower()
    if dep != "" and dep != "nan" and dep != "none" and dep != "0":
      return "مطابق"
    else:
      return "معلق لم ينزل رقم إيداع"


  master_df["حالة المطابقة"] = master_df.apply(resolve_status, axis=1)

  if not df_onyx_raw.empty:

    def check_onyx(row):
      ref = str(row["رقم الطلب / المرجع"])
      phone = str(row["رقم الجوال"])
      if ref in onyx_matched_keys or phone in onyx_matched_keys:
        return "موجود في أونكس"
      return "غير مسجل في أونكس"

    master_df["حالة أونكس"] = master_df.apply(check_onyx, axis=1)

  # مؤشرات الملخص (KPIs)
  matched_df = master_df[master_df["حالة المطابقة"] == "مطابق"]
  pending_df = master_df[master_df["حالة المطابقة"] == "معلق لم ينزل رقم إيداع"]

  c1, c2, c3 = st.columns(3)
  c1.metric(label="إجمالي الحركات", value=f"{len(master_df)} حركة")
  c2.metric(
      label="مطابق (تم الإيداع)",
      value=f"{len(matched_df)} حركة",
      delta=f"{matched_df['المبلغ'].sum():,.2f} ر.س",
  )
  c3.metric(
      label="معلق (بانتظار رقم الإيداع)",
      value=f"{len(pending_df)} حركة",
      delta=f"-{pending_df['المبلغ'].sum():,.2f} ر.س",
      delta_color="inverse",
  )

  st.markdown("---")

  # أدوات الفلترة والبحث
  filter_col1, filter_col2 = st.columns([2, 2])
  with filter_col1:
    view_mode = st.radio(
        "عرض الحركات:",
        ["الكل", "مطابق فقط", "معلق لم ينزل رقم إيداع فقط"],
        horizontal=True,
    )
  with filter_col2:
    search_query = st.text_input(
        "بحث سريع (برقم الطلب، الجوال، أو رقم الإيداع):", ""
    )

  if view_mode == "مطابق فقط":
    working_df = matched_df
  elif view_mode == "معلق لم ينزل رقم إيداع فقط":
    working_df = pending_df
  else:
    working_df = master_df

  if search_query:
    working_df = working_df[
        working_df.astype(str)
        .apply(lambda x: x.str.contains(search_query, case=False).any(), axis=1)
    ]

  st.dataframe(working_df, use_container_width=True, hide_index=True)

  st.markdown("---")
  output_buffer = io.BytesIO()
  with pd.ExcelWriter(output_buffer, engine="xlsxwriter") as writer:
    master_df.to_excel(writer, sheet_name="تقرير المطابقة المالي", index=False)

  st.download_button(
      label="تحميل تقرير المطابقة الشامل (Excel للمحاسبة)",
      data=output_buffer.getvalue(),
      file_name="Shuwayred_Financial_Reconciliation.xlsx",
      mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  )

else:
  st.info("الرجاء رفع تقرير طلبات زد (Zid Export) من القائمة الجانبية للبدء.")
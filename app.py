import io
import pandas as pd
import requests
import streamlit as st

# ضبط إعدادات الصفحة لتكون واسعة ومريحة لعين المحاسب
st.set_page_config(
    page_title="نظام المطابقة المالية الآلي - شركة الشويرد", layout="wide"
)

# ---------------------------------------------------------
# إعدادات الـ APIs (ربط المنصات وبوابات الدفع)
# ---------------------------------------------------------
ZID_STORE_ID = "113480"
ZID_MANAGER_TOKEN = "eyJpdiI6Ik1aYmZFWTVvZnZQS2JDaURoZEpySEE9PSIsInZhbHVlIjoiTnNTUnNvMmp6VXFLaWg0V3dmaWZyN21WZy9xUzE3ZzNMdzZwTUxTNk95aEpPK2Rpd2pZNEJkM1VzdjB6VER5TXJmU2FhTGNCak5UVU5sYStldFEvWmtMQmpheFNXQjgvaWRQWCtlRXFqZ3FJeTZXMCsxQ1VQZXlrMytwNStZT0t0SDR1Y3lnVUdYYmJ4OUpGZUxtSlFSbVBPZW9rdlJSL1RKeVZPMEN4SktnU0xyaGdOZnErcmZTcCt0bExXWUFPajJ0ZkZ6emVDUDRBU3RCUmZ1dW9GR3BqUHN1d0tiZG02OWtYOGMraG1HKys0ZFZwcHRDdEVQYk0waHVseDR1NlNCRlVQcXlWUlNzRmR6cGgyTlZwamc9PSIsIm1hYyI6IjgwNmU5M2ZhNTYyZWZjMmU4OGI1NzlhMDEwNzQxY2E3MjhhMThlODUxYTRhNTNmNDdhZjY1MTYyMDU3NTRjOTMiLCJ0YWciOiIifQ=="


st.title("📊 لوحة المطابقة المالية الموحدة - شركة الشويرد")
st.markdown("---")


# ---------------------------------------------------------
# دالة جلب بيانات زد آلياً عبر الـ API
# ---------------------------------------------------------
@st.cache_data(ttl=300)
def fetch_zid_data():
  url = "https://api.zid.sa/v1/managers/store/orders"
  headers = {
      "X-Manager-Token": ZID_MANAGER_TOKEN,
      "Store-Id": ZID_STORE_ID,
      "Content-Type": "application/json",
      "Accept-Language": "ar",
  }
  try:
    response = requests.get(url, headers=headers, timeout=15)
    if response.status_code == 200:
      orders = response.json().get("orders", [])
      parsed = []
      for order in orders:
        payment_info = order.get("payment", {})
        customer_info = order.get("customer", {})
        deposit_id = (
            payment_info.get("settlement_id")
            or payment_info.get("deposit_id")
            or order.get("deposit_id")
            or ""
        )

        parsed.append({
            "المنصة / البوابة": "متجر زد (Zid)",
            "رقم الطلب / المرجع": str(order.get("id", "")),
            "رقم الجوال": str(customer_info.get("mobile", "")).strip(),
            "تاريخ العملية": order.get("created_at", "")[:10],
            "وسيلة الدفع": payment_info.get("payment_method", {}).get(
                "name", "غير محدد"
            ),
            "المبلغ": float(order.get("order_total", 0)),
            "رقم الإيداع / التسوية": str(deposit_id).strip(),
        })
      return pd.DataFrame(parsed)
    else:
      return pd.DataFrame()
  except Exception:
    return pd.DataFrame()


# (ملاحظة: يمكنك توسيع هذه الدوال لاحقاً لربط نقاط النهاية API الخاصة بتابي وتمارا وبقية المنصات بنفس الطريقة)
def fetch_other_gateways_api():
  # هنا يتم جلب بيانات البوابات الأخرى (Tamara, Tabby, Emkan, Ms Pay, Madfou3) عبر الـ APIs الخاصة بها
  # كمثال توضيحي نعيد قائمة فارغة لحين ربط مسارات الـ Endpoints الخاصة بها
  return pd.DataFrame()


# ---------------------------------------------------------
# واجهة المحاسب: الشريط الجانبي (Sidebar)
# ---------------------------------------------------------
st.sidebar.header("⚙️ خيارات ومطابقة المحاسب")
st.sidebar.markdown(
    "المنصات وبوابات الدفع مرتبطة **آلياً عبر الـ API** ولا تتطلب رفع ملفات."
)

# الزر اليدوي الوحيد: ملف أونكس برو
onyx_file = st.sidebar.file_uploader(
    "📥 رفع ملف أونكس برو (اختياري للمطابقة المحاسبية)", type=["xlsx", "csv"]
)

# زر لتحديث البيانات وسحبها فوراً
if st.sidebar.button("🔄 تحديث وسحب البيانات من الـ APIs"):
  st.cache_data.clear()
  st.rerun()

# ---------------------------------------------------------
# معالجة وجمع البيانات
# ---------------------------------------------------------
df_zid = fetch_zid_data()
df_others = fetch_other_gateways_api()

all_frames = []
if not df_zid.empty:
  all_frames.append(df_zid)
if not df_others.empty:
  all_frames.append(df_others)

if all_frames:
  master_df = pd.concat(all_frames, ignore_index=True)

  # معالجة ملف أونكس برو إذا تم رفعه
  onyx_matched_keys = set()
  if onyx_file:
    try:
      df_onyx = (
          pd.read_csv(onyx_file)
          if onyx_file.name.endswith(".csv")
          else pd.read_excel(onyx_file)
      )
      df_onyx.columns = [str(c).lower().strip() for c in df_onyx.columns]
      o_ref = next(
          (
              c
              for c in df_onyx.columns
              if "order" in c or "reference" in c or "مرجع" in c or "فاتورة" in c
          ),
          None,
      )
      o_phone = next(
          (
              c
              for c in df_onyx.columns
              if "phone" in c or "mobile" in c or "جوال" in c
          ),
          None,
      )

      if o_ref:
        onyx_matched_keys.update(df_onyx[o_ref].astype(str).str.strip().tolist())
      if o_phone:
        onyx_matched_keys.update(
            df_onyx[o_phone].astype(str).str.strip().tolist()
        )
      st.sidebar.success("✅ تم قراءة كشف أونكس برو ومطابقته بنجاح")
    except Exception as e:
      st.sidebar.error(f"خطأ في قراءة ملف أونكس: {e}")

  # تطبيق شرط المطابقة الرئيسي (وجود رقم إيداع / تسوية)
  def resolve_status(row):
    dep = str(row["رقم الإيداع / التسوية"]).strip().lower()
    if dep != "" and dep != "nan" and dep != "none":
      return "مطابق"
    else:
      return "معلق لم ينزل رقم إيداع"

  master_df["حالة المطابقة"] = master_df.apply(resolve_status, axis=1)

  # فحص المطابقة مع أونكس إذا وُفت الملف
  if onyx_file:

    def check_onyx(row):
      ref = str(row["رقم الطلب / المرجع"])
      phone = str(row["رقم الجوال"])
      if ref in onyx_matched_keys or phone in onyx_matched_keys:
        return "موجود في أونكس"
      return "غير مسجل في أونكس"

    master_df["حالة أونكس"] = master_df.apply(check_onyx, axis=1)

  # ---------------------------------------------------------
  # واجهة المحاسب: مؤشرات الملخص (KPI Metrics)
  # ---------------------------------------------------------
  matched_df = master_df[master_df["حالة المطابقة"] == "مطابق"]
  pending_df = master_df[master_df["حالة المطابقة"] == "معلق لم ينزل رقم إيداع"]

  c1, c2, c3 = st.columns(3)
  c1.metric("📦 إجمالي الحركات (API)", f"{len(master_df)} حركة")
  c2.metric(
      "✅ مطابق (تم الإيداع)",
      f"{len(matched_df)} حركة",
      f"{matched_df['المبلغ'].sum():,.2f} ر.س",
  )
  c3.metric(
      "⏳ معلق (بانتظار رقم الإيداع)",
      f"{len(pending_df)} حركة",
      f"-{pending_df['المبلغ'].sum():,.2f} ر.س",
      delta_color="inverse",
  )

  st.markdown("---")

  # ---------------------------------------------------------
  # فلاتر البحث والعرض السريع للمحاسب
  # ---------------------------------------------------------
  filter_col1, filter_col2 = st.columns([2, 2])

  with filter_col1:
    view_mode = st.radio(
        "عرض الحركات:",
        ["الكل", "مطابق فقط", "معلق لم ينزل رقم إيداع فقط"],
        horizontal=True,
    )

  with filter_col2:
    search_query = st.text_input(
        "🔍 بحث سريع (برقم الطلب، الجوال، أو رقم الإيداع):", ""
    )

  # تطبيق الفلاتر
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

  # ---------------------------------------------------------
  # عرض الجدول المنسق للمحاسب
  # ---------------------------------------------------------
  st.dataframe(working_df, use_container_width=True, hide_index=True)

  # ---------------------------------------------------------
  # زر تصدير التقرير النهائي
  # ---------------------------------------------------------
  st.markdown("---")
  output_buffer = io.BytesIO()
  with pd.ExcelWriter(output_buffer, engine="xlsxwriter") as writer:
    master_df.to_excel(writer, sheet_name="تقرير المطابقة المالي", index=False)

  st.download_button(
      label="📥 تحميل تقرير المطابقة الشامل (Excel للمحاسبة)",
      data=output_buffer.getvalue(),
      file_name="Shuwayred_Financial_Reconciliation.xlsx",
      mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  )

else:
  st.warning(
      "جاري سحب البيانات من المنصات عبر الـ API، أو لا توجد بيانات متاحة حالياً."
  )
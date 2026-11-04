import io
import pandas as pd
import requests
import streamlit as st

st.set_page_config(
    page_title="نظام المطابقة المالية الآلي - شركة الشويرد", layout="wide"
)

ZID_STORE_ID = "113480"
ZID_MANAGER_TOKEN = "eyJpdiI6InN1U2pZS2xTc1ZtTW1WZktUQzAyU0E9PSIsInZhbHVlIjoiVmx3MmdOSHFWT0ZhKzFLdE56M2hEcm1xSGtpUTNBUlhaTCt1N2h6OHkyQ0Zid1Jjd0RXK1BLRm1xajNYdmlRUStUMlJxdWFzSHJtbTVEWVJYb0xjZktsRjZ0TVllOWdBOVg3Z2N6YmpUTEdSMUEvZ2QxeTZFMVJ0SVhKOVBTTE83WXpTd2QxQm5aSEdCZ29tRDk3YzEyaE13cFJYVVVjUE9wQmpOYm1LeUY4bTRsNTlPcm1zQjd4QUVCeHFaTzNnR2xkZ1BJQXdBaXZ5WEJsUDcxeTlNditKZXIwWTBMTHR5elRqMWlGNlZGcXlWWDFRSlRGNVdtOXJVS3hrNW0vYS96aEMzWWJOemhONlBzZzBIcXBBMGc9PSIsIm1hYyI6ImU2YWVmMGE0ODVlNzY5YjU2YzhhMmI0MjFiYmY2ODU1MWNlZTJlMGJmOTEyYjQyZmZhNjQ4M2VhYTAyNjdlY2EiLCJ0YWciOiIifQ=="

st.title("لوحة المطابقة المالية الموحدة - شركة الشويرد")
st.markdown("---")


@st.cache_data(ttl=300)
def fetch_zid_data():
  # تجربة الرابط البديل أو إضافة معلومات الهيدر المطلوبة بدقة لـ زد
  url = "https://api.zid.sa/v1/managers/store/orders"
  headers = {
      "Authorization": f"Bearer {ZID_MANAGER_TOKEN}",
      "X-Manager-Token": ZID_MANAGER_TOKEN,
      "Store-Id": ZID_STORE_ID,
      "Content-Type": "application/json",
      "Accept": "application/json",
      "Accept-Language": "ar",
  }
  try:
    response = requests.get(url, headers=headers, timeout=15)
    st.sidebar.info(f"حالة الاتصال: {response.status_code}")

    if response.status_code == 200:
      if "html" in response.text.lower():
        st.error(
            "الخادم أرجع صفحة HTML (تسجيل دخول). تأكد من صحة صلاحيات التوكن."
        )
        return pd.DataFrame()

      data = response.json()
      orders = (
          data.get("orders", [])
          if isinstance(data, dict)
          else data.get("data", [])
      )
      if not orders and isinstance(data, list):
        orders = data

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
            "رقم الطلب / المرجع": str(
                order.get("id") or order.get("order_id", "")
            ),
            "رقم الجوال": str(
                customer_info.get("mobile") or order.get("customer_phone", "")
            ).strip(),
            "تاريخ العملية": str(
                order.get("created_at") or order.get("date", "")
            )[:10],
            "وسيلة الدفع": str(
                payment_info.get("payment_method", {}).get("name")
                or order.get("payment_method", "غير محدد")
            ),
            "المبلغ": float(
                order.get("order_total") or order.get("total", 0.0)
            ),
            "رقم الإيداع / التسوية": str(deposit_id).strip(),
        })
      return pd.DataFrame(parsed)
    else:
      st.error(f"خطأ API: {response.status_code} - {response.text}")
      return pd.DataFrame()
  except Exception as e:
    st.error(f"خطأ اتصال: {e}")
    return pd.DataFrame()


def fetch_other_gateways_api():
  return pd.DataFrame()


st.sidebar.header("خيارات ومطابقة المحاسب")
onyx_file = st.sidebar.file_uploader(
    "رفع ملف أونكس برو (اختياري للمطابقة المحاسبية)", type=["xlsx", "csv"]
)

if st.sidebar.button("تحديث وسحب البيانات من الـ APIs"):
  st.cache_data.clear()
  st.rerun()

df_zid = fetch_zid_data()
df_others = fetch_other_gateways_api()

all_frames = []
if not df_zid.empty:
  all_frames.append(df_zid)
if not df_others.empty:
  all_frames.append(df_others)

if all_frames:
  master_df = pd.concat(all_frames, ignore_index=True)

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
      st.sidebar.success("تم قراءة كشف أونكس برو بنجاح")
    except Exception as e:
      st.sidebar.error(f"خطأ في ملف أونكس: {e}")


  def resolve_status(row):
    dep = str(row["رقم الإيداع / التسوية"]).strip().lower()
    if dep != "" and dep != "nan" and dep != "none":
      return "مطابق"
    else:
      return "معلق لم ينزل رقم إيداع"


  master_df["حالة المطابقة"] = master_df.apply(resolve_status, axis=1)

  if onyx_file:

    def check_onyx(row):
      ref = str(row["رقم الطلب / المرجع"])
      phone = str(row["رقم الجوال"])
      if ref in onyx_matched_keys or phone in onyx_matched_keys:
        return "موجود في أونكس"
      return "غير مسجل في أونكس"

    master_df["حالة أونكس"] = master_df.apply(check_onyx, axis=1)

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
  view_mode = st.radio(
      "عرض الحركات:",
      ["الكل", "مطابق فقط", "معلق لم ينزل رقم إيداع فقط"],
      horizontal=True,
  )
  search_query = st.text_input("بحث سريع:", "")

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

  output_buffer = io.BytesIO()
  with pd.ExcelWriter(output_buffer, engine="xlsxwriter") as writer:
    master_df.to_excel(writer, sheet_name="تقرير المطابقة", index=False)

  st.download_button(
      label="تحميل التقرير النهائي (Excel)",
      data=output_buffer.getvalue(),
      file_name="Shuwayred_Report.xlsx",
      mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  )
else:
  st.warning("بانتظار سحب البيانات الصحيحة من المنصة...")
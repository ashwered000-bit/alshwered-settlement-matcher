import base64
import io
import pandas as pd
import requests
import streamlit as st

st.set_page_config(
    page_title="نظام مطابقة طلبات زد مع بوابات الدفع - الشويرد",
    layout="wide",
)

st.title("🛡️ نظام مطابقة طلبات زد مع بوابات الدفع")
st.markdown(
    "مطابقة دقيقة لكشف الطلبات التي تنزل في زد وليست موجودة أو معلقة في بوابات"
    " الدفع (تابي، تمارا، مس بي، إمكان، مدفوع)."
)
st.markdown("---")

# ---------------------------------------------------------
# المفاتيح المعتمدة للبوابات
# ---------------------------------------------------------
GATEWAYS_CONFIG = {
    "tabby": {
        "public_key": "pk_b21b6ca0-f279-40f0-8e3b-f0ac1ff418b7",
        "secret_key": "sk_7de08dfa-bd16-4d4e-89c1-6eca9e928da0",
        "merchant_code": "Ashweredalbadeea",
        "base_url": "https://api.tabby.ai/v1",
    },
    "tamara": {
        "public_key": "32fc9893-4657-4d05-a6bf-8e5a77944e1b",
        "notification_token": "93bb4fd5-967c-4381-80b9-b33856e49844",
        "jwt_token": (
            "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9."
            "eyJhY2NvdW50SWQiOiJmMGU3NDk5Yy1mMmJkLTQyNzctYTEyOC03ZDQ2ZDY2NDEzZDciLCJ0eXBlIjoibWVyY2hhbnQiLCJzYWx0IjoiOWUzY2VhYWM3NTMxYWI0YzhhYjMwZDZmZGE5NjM1YzUiLCJpYXQiOjE2NDQyMzUxMDAsImlzcyI6IlRhbWFyYSJ9."
            "CvU6vvI-JUmKjQJ4tWE9_TZ1hkTeBfPZrCunFoS4D3s8G6Zw82VPi-7dxbkOKOIgiUZHLQwX1WELFkSuB9xwEElzD6UbOsZYdimaAzH0h5s0tiD6SaEIqfzo2NuQbraGy1Cd8X23F29FmfeYqHdlY10Q9Ji1-k02hbG-EM4nP_fi08iSCho8ADCPcdmPCXFsUjHf6ia8gUGkdD3cjpswRGESttheC1CuoomwsQapmFojRHKhtTtpMaBGURkCa-yzVPOPlJxXVBLQGnvE-cUemMxqjybWJFDbz9pvqurY9bm1CM1SP6Tu99XjlFjUWyFyyv-ySL86OMHd4aTZRrJ27A"
        ),
        "base_url": "https://api.tamara.co",
    },
    "mispay": {
        "app_id": "0a4d0c3ff60de86fa9f4645ddbfd68b766a80269",
        "app_secret": (
            "1318d6cb64f44d6c41336eb7522b59587ad1177ec5e66e5bc52b1e32fddcfb7b"
        ),
        "merchant_id": "PY7P6-99K0-8J2FO",
        "base_url": "https://merchant.mispay.co/api/v1",
    },
    "emkan": {
        "user": "ttCe0yuxp8SLbgwL9phkLEvpCs8a",
        "pass": "mjK_Fr6MZt3NVjfkkFhsewVAlrUa",
        "base_url": "https://merchants.emkanfinance.com.sa/api",
    },
    "madfu": {
        "api_key": "YGVou1l39EJKw4XwDcOsWx3BR",
        "app_code": "2E9FRA5F4z",
        "auth": (
            "Basic"
            " TUNUTko6SklWOFNYS1Q0ZDJIVTFoeEhJS1RDY3BnS0pBdVZUdnFQaU12MnpqeXN4"
        ),
        "base_url": "https://vendor.madfu.com.sa/api",
    },
}

# ---------------------------------------------------------
# واجهة الرفع وإدارة الجلسة (Session State) لزر التحديث
# ---------------------------------------------------------
st.sidebar.header("📥 إدخال البيانات")
uploaded_file = st.sidebar.file_uploader(
    "رفع تقرير طلبات زد (Zid Export)", type=["xlsx", "csv"]
)

if uploaded_file is not None:
  st.session_state["zid_file_bytes"] = uploaded_file.getvalue()
  st.session_state["zid_file_name"] = uploaded_file.name

if "zid_file_bytes" in st.session_state:
  if st.sidebar.button("🔄 تحديث وفحص الطلبات من جديد"):
    st.rerun()

# ---------------------------------------------------------
# دوال الاستعلام من APIs بوابات الدفع
# ---------------------------------------------------------


def check_tabby_payment(order_id):
  cfg = GATEWAYS_CONFIG["tabby"]
  headers = {
      "Authorization": f"Bearer {cfg['secret_key']}",
      "Accept": "application/json",
  }
  try:
    url = f"{cfg['base_url']}/payments?merchant_code={cfg['merchant_code']}&order_reference={order_id}"
    resp = requests.get(url, headers=headers, timeout=6)
    if resp.status_code == 200:
      data = resp.json()
      payments = (
          data.get("payments", [])
          if isinstance(data, dict)
          else (data if isinstance(data, list) else [])
      )
      if payments:
        p = payments[0]
        status = str(p.get("status", "")).lower()
        if status in ["authorized", "closed", "captured"]:
          return True, "موجود وموثق في تابي", p.get("id", "")
        return False, f"موجود في تابي ولكن بحالة معلقة ({status})", p.get("id", "")
      return False, "غير موجود نهائياً في تابي", ""
    return False, f"خطأ استجابة تابي ({resp.status_code})", ""
  except Exception as e:
    return False, f"فشل اتصال تابي: {e}", ""


def check_tamara_payment(order_id):
  cfg = GATEWAYS_CONFIG["tamara"]
  headers = {
      "Authorization": f"Bearer {cfg['jwt_token']}",
      "Accept": "application/json",
  }
  try:
    url = f"{cfg['base_url']}/orders/reference-id/{order_id}"
    resp = requests.get(url, headers=headers, timeout=6)
    if resp.status_code == 200:
      data = resp.json()
      status = str(data.get("status", "")).lower()
      if status in ["approved", "fully_captured", "authorised"]:
        return True, "موجود وموثق في تمارا", data.get("order_id", "")
      return (
          False,
          f"موجود في تمارا ولكن بحالة معلقة ({status})",
          data.get("order_id", ""),
      )
    return False, "غير موجود نهائياً في تمارا", ""
  except Exception as e:
    return False, f"فشل اتصال تمارا: {e}", ""


def check_mispay_payment(order_id):
  cfg = GATEWAYS_CONFIG["mispay"]
  headers = {
      "X-App-ID": cfg["app_id"],
      "X-App-Secret": cfg["app_secret"],
      "Accept": "application/json",
  }
  try:
    url = f"{cfg['base_url']}/orders/check/{order_id}"
    resp = requests.get(url, headers=headers, timeout=6)
    if resp.status_code == 200:
      data = resp.json()
      status = str(data.get("status", "")).lower()
      if status in ["success", "paid", "completed", "1"]:
        return True, "موجود وموثق في مس بي", data.get("transaction_id", "")
      return (
          False,
          f"موجود في مس بي ولكن بحالة معلقة ({status})",
          data.get("transaction_id", ""),
      )
    return False, "غير موجود نهائياً في مس بي", ""
  except Exception as e:
    return False, f"فشل اتصال مس بي: {e}", ""


def check_emkan_payment(order_id):
  cfg = GATEWAYS_CONFIG["emkan"]
  creds = f"{cfg['user']}:{cfg['pass']}"
  encoded = base64.b64encode(creds.encode()).decode()
  headers = {
      "Authorization": f"Basic {encoded}",
      "Accept": "application/json",
  }
  try:
    url = f"{cfg['base_url']}/orders/status?order_id={order_id}"
    resp = requests.get(url, headers=headers, timeout=6)
    if resp.status_code == 200:
      data = resp.json()
      status = str(data.get("status", "")).lower()
      if status in ["approved", "disbursed", "completed", "success"]:
        return True, "موجود وموثق في إمكان", data.get("emkan_ref", "")
      return (
          False,
          f"موجود في إمكان ولكن بحالة معلقة ({status})",
          data.get("emkan_ref", ""),
      )
    return False, "غير موجود نهائياً في إمكان", ""
  except Exception as e:
    return False, f"فشل اتصال إمكان: {e}", ""


def check_madfu_payment(order_id):
  cfg = GATEWAYS_CONFIG["madfu"]
  headers = {
      "Authorization": cfg["auth"],
      "X-Api-Key": cfg["api_key"],
      "X-App-Code": cfg["app_code"],
      "Accept": "application/json",
  }
  try:
    url = f"{cfg['base_url']}/merchant/v1/orders/{order_id}"
    resp = requests.get(url, headers=headers, timeout=6)
    if resp.status_code == 200:
      data = resp.json()
      status = str(data.get("status", "")).lower()
      if status in ["paid", "captured", "success"]:
        return True, "موجود وموثق في مدفوع", data.get("madfu_id", "")
      return (
          False,
          f"موجود في مدفوع ولكن بحالة معلقة ({status})",
          data.get("madfu_id", ""),
      )
    return False, "غير موجود نهائياً في مدفوع", ""
  except Exception as e:
    return False, f"فشل اتصال مدفوع: {e}", ""


# ---------------------------------------------------------
# تنفيذ الفحص والمعالجة بناءً على الملف المحفوظ في الذاكرة
# ---------------------------------------------------------
if "zid_file_bytes" in st.session_state:
  try:
    file_bytes = io.BytesIO(st.session_state["zid_file_bytes"])
    file_name = st.session_state["zid_file_name"]

    df_raw = (
        pd.read_csv(file_bytes)
        if file_name.endswith(".csv")
        else pd.read_excel(file_bytes)
    )
    df_raw.columns = [str(c).lower().strip() for c in df_raw.columns]

    order_col = next(
        (
            c
            for c in df_raw.columns
            if c in ["id", "order_id", "رقم الطلب", "الرقم"]
        ),
        df_raw.columns[0],
    )

    initial_count = len(df_raw)
    df_zid = df_raw.drop_duplicates(subset=[order_col], keep="first").copy()
    deduped_count = len(df_zid)
    removed_count = initial_count - deduped_count

    st.success(
        f"تم تحميل الملف بنجاح. إجمالي الطلبات: ({initial_count}) | تم حذف"
        f" التكرارات: ({removed_count}) طلب | الصافي قيد الفحص: ({deduped_count})"
        " طلب فريد."
    )

    results = []
    progress_bar = st.progress(0)

    for index, (_, row) in enumerate(df_zid.iterrows()):
      order_id = str(row.get(order_col, "")).strip()
      method = (
          str(
              row.get("payment_method")
              or row.get("payment")
              or row.get("وسيلة الدفع")
              or ""
          )
          .lower()
          .strip()
      )
      amount = float(
          row.get("order_total")
          or row.get("total")
          or row.get("المبلغ")
          or row.get("الاجمالي")
          or 0.0
      )

      is_found = False
      status_msg = ""
      ref_id = ""
      gateway_label = ""

      if "tabby" in method or "تابي" in method:
        gateway_label = "تابي (Tabby)"
        is_found, status_msg, ref_id = check_tabby_payment(order_id)
      elif "tamara" in method or "تمارا" in method:
        gateway_label = "تمارا (Tamara)"
        is_found, status_msg, ref_id = check_tamara_payment(order_id)
      elif "mispay" in method or "مس بي" in method or "مسبي" in method:
        gateway_label = "مس بي (Mispay)"
        is_found, status_msg, ref_id = check_mispay_payment(order_id)
      elif "emkan" in method or "إمكان" in method or "امكان" in method:
        gateway_label = "إمكان (Emkan)"
        is_found, status_msg, ref_id = check_emkan_payment(order_id)
      elif "madfu" in method or "مدفوع" in method:
        gateway_label = "مدفوع (Madfu)"
        is_found, status_msg, ref_id = check_madfu_payment(order_id)
      else:
        gateway_label = f"وسيلة أخرى ({method if method else 'غير محددة'})"
        is_found = True
        status_msg = "خارج نطاق بوابات التقسيط BNPL المستهدفة"

      results.append({
          "رقم طلب زد": order_id,
          "وسيلة الدفع في زد": method,
          "البوابة المحددة": gateway_label,
          "المبلغ": amount,
          "حالة التحقق": (
              "✅ موجود وموثق"
              if is_found
              else (
                  "ℹ️ دفع إلكتروني عادي/أخرى"
                  if "خارج نطاق" in status_msg
                  else "❌ غير موجود / معلق (خطر)"
              )
          ),
          "تفاصيل حالة البوابة": status_msg,
          "مرجع العملية": ref_id,
      })

      progress_bar.progress((index + 1) / deduped_count)

    res_df = pd.DataFrame(results)

    st.markdown("### 📊 ملخص نتائج المطابقة وكشف الطلبات المعلقة")
    c1, c2, c3 = st.columns(3)

    found_df = res_df[res_df["حالة التحقق"].str.contains("✅")]
    danger_df = res_df[res_df["حالة التحقق"].str.contains("❌")]

    c1.metric("إجمالي الطلبات الفريدة", f"{len(res_df)} طلب")
    c2.metric(
        "الطلبات السليمة والموثقة ✅",
        f"{len(found_df)} طلب",
        delta=f"{found_df['المبلغ'].sum():,.2f} ر.س",
    )
    c3.metric(
        "الطلبات الوهمية / غير الموجودة ❌",
        f"{len(danger_df)} طلب",
        delta=f"-{danger_df['المبلغ'].sum():,.2f} ر.س",
        delta_color="inverse",
    )

    st.markdown("---")
    st.dataframe(res_df, use_container_width=True, hide_index=True)

    csv_bytes = res_df.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "📥 تحميل تقرير المطابقة والكشف النهائي (CSV)",
        data=csv_bytes,
        file_name="Zid_Gateways_Audit_Report.csv",
        mime="text/csv",
    )

  except Exception as e:
    st.error(f"حدث خطأ أثناء قراءة أو معالجة الملف: {e}")
else:
  st.info("الرجاء رفع تقرير طلبات زد من القائمة الجانبية لبدء الفحص والمطابقة.")
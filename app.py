import base64
import io
import pandas as pd
import requests
import streamlit as st

st.set_page_config(
    page_title="نظام مطابقة طلبات زد مع بوابات الدفع - الشويرد",
    layout="wide",
)

st.title("🛡️ نظام مطابقة طلبات زد مع بوابات الدفع (Zid vs Payment Gateways)")
st.markdown(
    "مطابقة آلية لطلب زد مع (تابي، تمارا، مس بي، إمكان، مدفوع) عبر الـ APIs"
    " للتحقق من وصول المبالغ."
)
st.markdown("---")

# ---------------------------------------------------------
# المفاتيح المعتمدة لبوابات الدفع (تابي، تمارا، مس بي، إمكان، مدفوع)
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
            "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJhY2NvdW50SWQiOiJmMGU3NDk5Yy1mMmJkLTQyNzctYTEyOC03ZDQ2ZDY2NDEzZDciLCJ0eXBlIjoibWVyY2hhbnQiLCJzYWx0IjoiOWUzY2VhYWM3NTMxYWI0YzhhYjMwZDZmZGE5NjM1YzUiLCJpYXQiOjE2NDQyMzUxMDAsImlzcyI6IlRhbWFyYSJ9.CvU6vvI-JUmKjQJ4tWE9_TZ1hkTeBfPZrCunFoS4D3s8G6Zw82VPi-7dxbkOKOIgiUZHLQwX1WELFkSuB9xwEElzD6UbOsZYdimaAzH0h5s0tiD6SaEIqfzo2NuQbraGy1Cd8X23F29FmfeYqHdlY10Q9Ji1-k02hbG-EM4nP_fi08iSCho8ADCPcdmPCXFsUjHf6ia8gUGkdD3cjpswRGESttheC1CuoomwsQapmFojRHKhtTtpMaBGURkCa-yzVPOPlJxXVBLQGnvE-cUemMxqjybWJFDbz9pvqurY9bm1CM1SP6Tu99XjlFjUWyFyyv-ySL86OMHd4aTZRrJ27A"
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
# الشريط الجانبي: رفع الملف وخيارات التشغيل
# ---------------------------------------------------------
st.sidebar.header("📥 مدخلات المطابقة")
zid_file = st.sidebar.file_uploader(
    "رفع تقرير طلبات زد (Zid Export)", type=["xlsx", "csv"]
)

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
    resp = requests.get(url, headers=headers, timeout=5)
    if resp.status_code == 200:
      data = resp.json()
      payments = (
          data.get("payments", [])
          if isinstance(data, dict)
          else (data if isinstance(data, list) else [])
      )
      if payments:
        p = payments[0]
        status = p.get("status", "").lower()
        if status in ["authorized", "closed", "captured"]:
          return True, "تم الدفع والتحصيل بنجاح", p.get("id", "")
        return (
            False,
            f"موجودة في تابي ولكن الحالة ({status})",
            p.get("id", ""),
        )
      return False, "غير موجود في تابي", ""
    return False, f"خطأ تابي ({resp.status_code})", ""
  except Exception as e:
    return False, f"فشل الاتصال بـ تابي: {e}", ""


def check_tamara_payment(order_id):
  cfg = GATEWAYS_CONFIG["tamara"]
  headers = {
      "Authorization": f"Bearer {cfg['jwt_token']}",
      "Accept": "application/json",
  }
  try:
    url = f"{cfg['base_url']}/orders/reference-id/{order_id}"
    resp = requests.get(url, headers=headers, timeout=5)
    if resp.status_code == 200:
      data = resp.json()
      status = data.get("status", "").lower()
      if status in ["approved", "fully_captured", "authorised"]:
        return True, "تم التحصيل والتعميد بنجاح", data.get("order_id", "")
      return (
          False,
          f"موجودة في تمارا ولكن الحالة ({status})",
          data.get("order_id", ""),
      )
    return False, "غير موجود في تمارا", ""
  except Exception as e:
    return False, f"فشل الاتصال بـ تمارا: {e}", ""


def check_mispay_payment(order_id):
  cfg = GATEWAYS_CONFIG["mispay"]
  headers = {
      "X-App-ID": cfg["app_id"],
      "X-App-Secret": cfg["app_secret"],
      "Accept": "application/json",
  }
  try:
    url = f"{cfg['base_url']}/orders/check/{order_id}"
    resp = requests.get(url, headers=headers, timeout=5)
    if resp.status_code == 200:
      data = resp.json()
      status = str(data.get("status", "")).lower()
      if status in ["success", "paid", "completed", "1"]:
        return True, "تم الدفع بنجاح في مس بي", data.get("transaction_id", "")
      return False, f"حالة مس بي: ({status})", data.get("transaction_id", "")
    return False, "غير موجود في مس بي", ""
  except Exception as e:
    return False, f"فشل الاتصال بـ مس بي: {e}", ""


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
    resp = requests.get(url, headers=headers, timeout=5)
    if resp.status_code == 200:
      data = resp.json()
      status = str(data.get("status", "")).lower()
      if status in ["approved", "disbursed", "completed"]:
        return True, "تم الاعتماد والصرف في إمكان", data.get("emkan_ref", "")
      return False, f"حالة إمكان: ({status})", data.get("emkan_ref", "")
    return False, "غير موجود في إمكان", ""
  except Exception as e:
    return False, f"فشل الاتصال بـ إمكان: {e}", ""


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
    resp = requests.get(url, headers=headers, timeout=5)
    if resp.status_code == 200:
      data = resp.json()
      status = str(data.get("status", "")).lower()
      if status in ["paid", "captured", "success"]:
        return True, "تم السداد بنجاح في مدفوع", data.get("madfu_id", "")
      return False, f"حالة مدفوع: ({status})", data.get("madfu_id", "")
    return False, "غير موجود في مدفوع", ""
  except Exception as e:
    return False, f"فشل الاتصال بـ مدفوع: {e}", ""


# ---------------------------------------------------------
# محرك المطابقة المباشر
# ---------------------------------------------------------
if zid_file is not None:
  try:
    if zid_file.name.endswith(".csv"):
      df_zid = pd.read_csv(zid_file)
    else:
      df_zid = pd.read_excel(zid_file)

    df_zid.columns = [str(c).lower().strip() for c in df_zid.columns]

    st.success(f"تم قراءة تقرير زد بنجاح ({len(df_zid)} طلب).")

    results = []
    progress_bar = st.progress(0)
    total_rows = len(df_zid)

    for index, row in df_zid.iterrows():
      order_id = str(
          row.get("id")
          or row.get("order_id")
          or row.get("رقم الطلب")
          or row.get("الرقم")
          or ""
      ).strip()
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

      is_paid = False
      status_msg = "لم يتم الفحص"
      ref_id = ""
      gateway_detected = "غير معروفة"

      # التوجيه التلقائي للـ API بناءً على وسيلة الدفع
      if "tabby" in method or "تابي" in method:
        gateway_detected = "تابي (Tabby)"
        is_paid, status_msg, ref_id = check_tabby_payment(order_id)
      elif "tamara" in method or "تمارا" in method:
        gateway_detected = "تمارا (Tamara)"
        is_paid, status_msg, ref_id = check_tamara_payment(order_id)
      elif "mispay" in method or "مس بي" in method or "مسبي" in method:
        gateway_detected = "مس بي (Mispay)"
        is_paid, status_msg, ref_id = check_mispay_payment(order_id)
      elif "emkan" in method or "إمكان" in method or "امكان" in method:
        gateway_detected = "إمكان (Emkan)"
        is_paid, status_msg, ref_id = check_emkan_payment(order_id)
      elif "madfu" in method or "مدفوع" in method:
        gateway_detected = "مدفوع (Madfu)"
        is_paid, status_msg, ref_id = check_madfu_payment(order_id)
      else:
        gateway_detected = f"وسيلة أخرى ({method})"
        is_paid = True
        status_msg = "خارج نطاق بوابات BNPL المستهدفة"

      results.append({
          "رقم طلب زد": order_id,
          "وسيلة الدفع في زد": method,
          "البوابة المحددة": gateway_detected,
          "المبلغ": amount,
          "نتيجة الدفع بالـ API": (
              "✅ مسددة ومقبوضة" if is_paid else "❌ معلقة / لم تُسدد"
          ),
          "تفاصيل الاستجابة": status_msg,
          "مرجع العملية في البوابة": ref_id,
      })

      progress_bar.progress((index + 1) / total_rows)

    res_df = pd.DataFrame(results)

    # ---------------------------------------------------------
    # عرض المؤشرات والنتائج
    # ---------------------------------------------------------
    st.markdown("### 📊 ملخص مطابقة الفلوس والتحصيل")
    c1, c2, c3 = st.columns(3)
    paid_count = len(res_df[res_df["نتيجة الدفع بالـ API"].str.contains("✅")])
    unpaid_count = len(
        res_df[res_df["نتيجة الدفع بالـ API"].str.contains("❌")]
    )

    paid_sum = res_df[res_df["نتيجة الدفع بالـ API"].str.contains("✅")][
        "المبلغ"
    ].sum()
    unpaid_sum = res_df[res_df["نتيجة الدفع بالـ API"].str.contains("❌")][
        "المبلغ"
    ].sum()

    c1.metric("إجمالي طلبات زد", f"{len(res_df)} طلب")
    c2.metric(
        "طلبات مدفوعة ومؤكدة ✅",
        f"{paid_count} طلب",
        delta=f"{paid_sum:,.2f} ر.س",
    )
    c3.metric(
        "طلبات معلقة ولم تُسدد ❌",
        f"{unpaid_count} طلب",
        delta=f"-{unpaid_sum:,.2f} ر.س",
        delta_color="inverse",
    )

    st.markdown("---")
    st.dataframe(res_df, use_container_width=True, hide_index=True)

    # تصدير التقرير
    csv_bytes = res_df.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "📥 تحميل تقرير المطابقة المالي (CSV)",
        data=csv_bytes,
        file_name="Zid_Gateways_Reconciliation.csv",
        mime="text/csv",
    )

  except Exception as e:
    st.error(f"حدث خطأ أثناء معالجة الملف: {e}")

else:
  st.info("الرجاء رفع تقرير طلبات زد (Zid Export) لبدء المطابقة المباشرة.")
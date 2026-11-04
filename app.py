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
# واجهة الرفع وإدارة الجلسة (Session State) لزر التحديث
# ---------------------------------------------------------
st.sidebar.header("📥 إدخال البيانات")
uploaded_file = st.sidebar.file_uploader(
    "رفع تقرير طلبات زد (Zid Export)", type=["xlsx", "csv"]
)

if uploaded_file is not None:
  # حفظ الملف في ذاكرة الجلسة حتى لا يضطر المستخدم لإعادة رفعه عند الضغط على زر التحديث
  st.session_state["zid_file_bytes"] = uploaded_file.getvalue()
  st.session_state["zid_file_name"] = uploaded_file.name

# زر التحديث الفوري لتجنب إعادة رفع الملف
if "zid_file_bytes
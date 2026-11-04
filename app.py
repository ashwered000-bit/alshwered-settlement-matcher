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
# دالة جلب بيانات زد آلياً عبر الـ API مع فحص الأخطاء
# ---------------------------------------------------------
@st.cache_data(ttl=300)
def fetch_zid_data():
  # التعديل هنا: التأكد من استخدام الرابط الصحيح لمدير متجر زد
  url = "https://api.zid.sa/v1/managers/store/orders"
  headers = {
      "X-Manager-Token": ZID_MANAGER_TOKEN,
      "Store-Id": ZID_STORE_ID,
      "Content-Type": "application/json",
      "Accept-Language": "ar",
  }
  try:
    response = requests.get(url, headers=headers, timeout=15)

    # طباعة كود الاستجابة للتأكد من حالة الاتصال
    st.sidebar.info(f"حالة الاتصال بـ Zid API: {response.status_code}")

    if response.status_code == 200:
      data = response.json()
      # التعامل مع احتمال أن تكون الطلبات داخل مفتاح "orders" أو "data"
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
      st.error(
          f"فشل جلب البيانات من زد. كود الخطأ: {response.status_code} - التفاصيل:"
          f" {response.text}"
      )
      return pd.DataFrame()
  except Exception as e:
    st.error(f"حدث خطأ برمج أثناء الاتصال بـ Zid API: {e}")
    return pd.DataFrame()


def fetch_other_gateways_api():
  # مخصص للبوابات الأخرى عند توفر مسارات الـ API الخاصة بها
  return pd.DataFrame()


# ---------------------------------------------------------
# واجهة المحاسب: الشريط الجانبي (Sidebar)
# ---------------------------------------------------------
st.sidebar.header("⚙️ خيارات ومطابقة المحاسب")
st.sidebar.markdown(
    "المنصات وبوابات الدفع مرتبطة **آلياً عبر الـ API** ولا تتطلب رفع ملفات."
)

onyx_file = st.sidebar.file_uploader(
    "📥 رفع ملف أونكس برو (اختياري للمطابقة المحاسبية)", type=["xlsx", "csv"]
)

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

  # مؤشرات الملخص
  matched_df = master_df[master_df["حالة المطابقة"] == "مطابق"]
  pending_df = master_df[master_df["حالة المطابقة"] == "معلق لم ينزل رقم إيداع"]

  c1, c2, c3 = st.columns(3)
  c1.metric("📦 إجمالي الحركات (API)", f"{len(
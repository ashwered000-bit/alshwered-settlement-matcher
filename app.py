import io
import re
from datetime import datetime

import pandas as pd
import streamlit as st

st.set_page_config(page_title='مطابقة المنصات | الشويرد', page_icon='📊', layout='wide', initial_sidebar_state='expanded')

st.markdown('''<style>
@import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"], [data-testid="stApp"] {font-family:'Tajawal',sans-serif!important;}
[data-testid="stAppViewContainer"] {background:#f4f7fb;}
[data-testid="stSidebar"] {background:#10243c;}
[data-testid="stSidebar"] * {color:#f5f8ff!important;}
.block-container {padding-top:1.8rem;max-width:1500px;}
.hero {direction:rtl;background:linear-gradient(115deg,#102943,#17517a);color:white;border-radius:19px;padding:27px 32px;margin-bottom:22px;box-shadow:0 10px 30px #163b5b20;}
.hero h1 {color:white!important;font-size:30px;font-weight:800;margin:0 0 8px;}
.hero p {color:#d9e9f6;margin:0;font-size:16px;}
.section-title {direction:rtl;font-size:21px;font-weight:800;color:#142e49;margin:15px 0 12px;}
[data-testid="stMetric"] {background:white;border:1px solid #e5edf5;border-radius:16px;padding:16px 18px;box-shadow:0 3px 14px #193c5c0a;direction:rtl;}
[data-testid="stMetricLabel"] {font-size:15px;}
[data-testid="stMetricValue"] {color:#143d61;font-weight:800;}
[data-testid="stFileUploader"], [data-testid="stDataFrame"], [data-testid="stVerticalBlockBorderWrapper"] {border-radius:13px;}
.stButton button[kind="primary"], .stDownloadButton button[kind="primary"] {background:#086a9b;border:0;border-radius:11px;font-weight:800;}
.small-note {direction:rtl;color:#5d7084;font-size:14px;}
</style>''', unsafe_allow_html=True)

GATEWAYS = ['زد باي (ZidPay)', 'تابي (Tabby)', 'تمارا (Tamara)', 'مس بي (MisPay)', 'إمكان (Emkan)', 'مدفوع (Madfu)']


def read_file(upload):
    raw = upload.getvalue()
    if upload.name.lower().endswith('.csv'):
        for enc in ('utf-8-sig', 'utf-8', 'cp1256', 'latin1'):
            try:
                df = pd.read_csv(io.BytesIO(raw), encoding=enc, dtype=str, sep=None, engine='python')
                break
            except (UnicodeError, pd.errors.ParserError):
                continue
        else:
            raise ValueError('تعذر قراءة CSV؛ احفظ الملف بترميز UTF-8.')
    else:
        df = pd.read_excel(io.BytesIO(raw), dtype=str)
    df.columns = [str(x).strip() for x in df.columns]
    return df.fillna('')


def norm_id(value):
    s = str(value).strip().replace('\u200f', '').replace('\u200e', '')
    return re.sub(r'\.0$', '', s) if s.lower() not in ('nan', 'none') else ''


def amount(value):
    s = str(value).strip().replace('ر.س', '').replace('SAR', '').replace(' ', '').replace('٬', '').replace('،', '')
    if ',' in s and '.' in s:
        s = s.replace(',', '')
    elif ',' in s:
        s = s.replace(',', '.') if s.count(',') == 1 and len(s.split(',')[-1]) <= 2 else s.replace(',', '')
    s = re.sub(r'[^\d.\-]', '', s)
    try:
        return round(float(s), 2)
    except (ValueError, TypeError):
        return float('nan')


def guess(cols, terms):
    for term in terms:
        for c in cols:
            if c.lower().strip() == term.lower():
                return c
    for term in terms:
        for c in cols:
            if term.lower() in c.lower():
                return c
    return None


def choose_column(label, cols, terms, key, optional=False):
    suggested = guess(cols, terms)
    choices = (['— غير موجود —'] if optional else []) + list(cols)
    index = choices.index(suggested) if suggested in choices else 0
    selected = st.selectbox(label, choices, index=index, key=key)
    return None if selected == '— غير موجود —' else selected


def classify_status(value):
    s = str(value).strip().lower()
    if any(t in s for t in ('cancel', 'ملغي', 'ملغى', 'إلغاء', 'الغاء', 'canceled', 'cancelled')):
        return 'ملغي'
    if any(t in s for t in ('refund', 'refunded', 'مسترجع', 'مرتجع', 'استرداد')):
        return 'مسترجع'
    if any(t in s for t in ('unpaid', 'pending', 'failed', 'غير مدفوع', 'لم يتم الدفع', 'بانتظار الدفع')):
        return 'غير مؤكد'
    return 'مؤكد' if s else 'غير محدد'


def export_excel(all_results, unmatched, summary, suspicious):
    out = io.BytesIO()
    with pd.ExcelWriter(out, engine='openpyxl') as writer:
        sheets = {'الملخص': summary, 'نتائج المطابقة': all_results,
                  'الفروقات والمراجعة': suspicious, 'عمليات المنصة دون زد': unmatched}
        for name, df in sheets.items():
            df.to_excel(writer, sheet_name=name, index=False)
            ws = writer.sheets[name]
            ws.sheet_view.rightToLeft = True
            ws.freeze_panes = 'A2'
            ws.auto_filter.ref = ws.dimensions
            from openpyxl.styles import Font, PatternFill, Alignment
            for cell in ws[1]:
                cell.fill = PatternFill('solid', fgColor='143C60')
                cell.font = Font(color='FFFFFF', bold=True)
                cell.alignment = Alignment(horizontal='center')
            for column in ws.columns:
                letter = column[0].column_letter
                sample = [len(str(c.value or '')) for c in list(column)[:150]]
                ws.column_dimensions[letter].width = min(max(max(sample, default=10) + 3, 15), 45)
    return out.getvalue()


st.markdown('<div class="hero"><h1>مطابقة المنصات المالية</h1><p>شركة الشويرد | مراجعة طلبات زد مقابل عمليات بوابات الدفع واكتشاف الفروقات</p></div>', unsafe_allow_html=True)

with st.sidebar:
    st.markdown('## ⚙️ إعدادات المطابقة')
    gateway = st.selectbox('منصة الدفع', GATEWAYS)
    tolerance = st.number_input('سماحية فرق المبلغ (ريال)', min_value=0.0, max_value=10.0, value=0.01, step=0.01)
    st.caption('لا تُعتمد المطابقة برقم الطلب وحده عند اختلاف المبلغ. ولا تُعتبر عمليات الجوال والمبلغ وحدها مطابقة مؤكدة.')
    st.divider()
    st.markdown('**خطوات العمل**')
    st.markdown('١. ارفع طلبات زد.\n\n٢. ارفع كشف منصة الدفع.\n\n٣. راجع تعيين الأعمدة.\n\n٤. افحص الفروقات وصدر Excel.')

st.markdown('<div class="section-title">01 / استيراد البيانات</div>', unsafe_allow_html=True)
a, b = st.columns(2, gap='large')
with a:
    st.markdown('**📦 طلبات متجر زد — مطلوب أولاً**')
    zid_upload = st.file_uploader('ملف طلبات زد', type=['xlsx', 'csv'], key='zid_upload', label_visibility='collapsed')
with b:
    st.markdown(f'**💳 كشف {gateway}**')
    payout_upload = st.file_uploader('ملف منصة الدفع', type=['xlsx', 'csv'], key='payout_upload', label_visibility='collapsed', disabled=zid_upload is None)

if zid_upload is None:
    st.info('ابدأ برفع ملف طلبات زد بصيغة Excel أو CSV.')
    st.stop()
if payout_upload is None:
    st.info('تم اختيار ملف زد. ارفع الآن كشف منصة الدفع لإجراء المطابقة.')
    st.stop()

try:
    zid = read_file(zid_upload)
    payout = read_file(payout_upload)
except Exception as exc:
    st.error(f'تعذر قراءة الملفات: {exc}')
    st.stop()

if zid.empty or payout.empty:
    st.error('أحد الملفين فارغ ولا يمكن إجراء المطابقة.')
    st.stop()

with st.expander('02 / مراجعة أعمدة الملفات (تلقائيًا مع إمكانية التعديل)', expanded=True):
    left, right = st.columns(2, gap='large')
    with left:
        st.markdown('**أعمدة زد**')
        zid_id = choose_column('رقم الطلب', zid.columns, ['id', 'order_id', 'order number', 'رقم الطلب'], 'zid_id')
        zid_amount = choose_column('إجمالي الطلب', zid.columns, ['total', 'order_total', 'grand total', 'إجمالي الطلب', 'المجموع'], 'zid_amount')
        zid_name = choose_column('اسم العميل (اختياري)', zid.columns, ['customer_name', 'اسم العميل'], 'zid_name', True)
        zid_mobile = choose_column('جوال العميل (اختياري)', zid.columns, ['customer_mobile', 'mobile', 'الجوال'], 'zid_mobile', True)
        zid_payment = choose_column('طريقة الدفع (اختياري)', zid.columns, ['payment_method', 'طريقة الدفع'], 'zid_payment', True)
        zid_status = choose_column('حالة الطلب (اختياري)', zid.columns, ['order_status', 'status', 'حالة الطلب'], 'zid_status', True)
    with right:
        st.markdown('**أعمدة منصة الدفع**')
        pay_id = choose_column('رقم الطلب أو مرجع الطلب', payout.columns, ['order_id', 'merchant_order_id', 'order reference', 'order_number', 'reference', 'رقم الطلب'], 'pay_id')
        pay_amount = choose_column('مبلغ العملية', payout.columns, ['order_amount', 'total_amount', 'amount', 'total', 'مبلغ العملية', 'المبلغ'], 'pay_amount')
        pay_mobile = choose_column('جوال العميل (اختياري)', payout.columns, ['customer_mobile', 'mobile', 'phone', 'الجوال'], 'pay_mobile', True)
        pay_status = choose_column('حالة العملية (اختياري)', payout.columns, ['payment_status', 'transaction_status', 'status', 'حالة العملية'], 'pay_status', True)
        pay_transaction = choose_column('معرف العملية (اختياري)', payout.columns, ['transaction_id', 'payment_id', 'transaction reference', 'معرف العملية'], 'pay_transaction', True)
    st.caption('مهم: اختاري مبلغ الطلب الإجمالي في كشف الدفع، وليس صافي التسوية بعد خصم العمولة. إذا لم يتوفر مرجع الطلب، لا يمكن اعتماد المطابقة تلقائيًا.')

if zid_id == zid_amount or pay_id == pay_amount:
    st.error('يجب أن يكون عمود رقم الطلب مختلفًا عن عمود المبلغ في كل ملف.')
    st.stop()

z = zid.copy()
p = payout.copy()
z['_id'] = z[zid_id].map(norm_id)
z['_amount'] = z[zid_amount].map(amount)
z['_status'] = z[zid_status].map(classify_status) if zid_status else 'غير محدد'
p['_id'] = p[pay_id].map(norm_id)
p['_amount'] = p[pay_amount].map(amount)
p['_status'] = p[pay_status].map(classify_status) if pay_status else 'غير محدد'

# Each repeated Zid order ID is an item row, not a separate order.
# When repeated rows have the same total, use it once; otherwise flag the order for review.
records = []
for oid, group in z.groupby('_id', sort=False, dropna=False):
    values = group['_amount'].dropna().tolist()
    distinct = set(values)
    repeated_conflict = len(distinct) > 1
    order_total = values[0] if values and not repeated_conflict else float('nan')
    statuses = list(group['_status'].unique())
    records.append({'رقم طلب زد': oid, 'اسم العميل': str(group[zid_name].iloc[0]) if zid_name else '',
                    'جوال العميل': str(group[zid_mobile].iloc[0]) if zid_mobile else '',
                    'طريقة الدفع': str(group[zid_payment].iloc[0]) if zid_payment else '',
                    'حالة طلب زد': statuses[0] if len(statuses) == 1 else 'تحتاج مراجعة',
                    'مبلغ زد': order_total, 'عدد صفوف زد': len(group),
                    '_conflict': repeated_conflict})
orders = pd.DataFrame(records)

# Do not silently filter Zid orders based on guessed payment-method aliases.
# Optional user-entered filter supports platform-specific reports.
st.markdown('<div class="section-title">03 / نطاق المطابقة</div>', unsafe_allow_html=True)
if zid_payment:
    methods = sorted([x for x in orders['طريقة الدفع'].unique().tolist() if str(x).strip()])
    chosen = st.multiselect('طرق الدفع في زد التي تخص المنصة المحددة (اختياري)', methods,
                            help='حددي طرق الدفع الخاصة بهذه المنصة حتى لا تظهر طلبات المنصات الأخرى على أنها مفقودة. تركه فارغًا يعني فحص جميع طلبات زد.')
    if chosen:
        orders = orders[orders['طريقة الدفع'].isin(chosen)].copy()
else:
    st.warning('لم يتم تعيين عمود طريقة الدفع في زد. قد تظهر طلبات منصات أخرى ضمن الفروقات؛ راجعي النطاق.')

pay_groups = {oid: group for oid, group in p.groupby('_id', sort=False) if oid}
results = []
matched_pay_rows = set()
for _, o in orders.iterrows():
    oid = o['رقم طلب زد']
    group = pay_groups.get(oid)
    pay_amt = float('nan')
    pay_state = ''
    tx = ''
    if not oid:
        status, reason = 'تحتاج مراجعة', 'رقم طلب زد فارغ'
    elif o['_conflict']:
        status, reason = 'تحتاج مراجعة', 'تكرار رقم الطلب بمبالغ إجمالية مختلفة في زد'
    elif pd.isna(o['مبلغ زد']):
        status, reason = 'تحتاج مراجعة', 'مبلغ زد غير قابل للقراءة'
    elif group is None:
        status, reason = 'غير موجود في المنصة', 'لا يوجد مرجع مطابق لرقم طلب زد'
    else:
        matched_pay_rows.update(group.index.tolist())
        amounts = group['_amount'].dropna().tolist()
        pay_amt = amounts[0] if len(amounts) == 1 else float('nan')
        pay_state = '، '.join(sorted(set(group['_status'].astype(str))))
        tx = '، '.join(group[pay_transaction].astype(str).unique()[:4]) if pay_transaction else ''
        if len(group) != 1:
            status, reason = 'تحتاج مراجعة', 'رقم الطلب مكرر في كشف الدفع؛ يجب مراجعة العمليات أو الدفعات'
        elif pd.isna(pay_amt):
            status, reason = 'تحتاج مراجعة', 'مبلغ العملية غير قابل للقراءة'
        elif o['حالة طلب زد'] in ('ملغي', 'مسترجع'):
            status, reason = 'تحتاج مراجعة', 'حالة زد ملغية أو مسترجعة وتحتاج تحققًا ماليًا'
        elif pay_state in ('ملغي', 'مسترجع', 'غير مؤكد'):
            status, reason = 'تحتاج مراجعة', 'عملية الدفع ليست عملية ناجحة مؤكدة'
        elif abs(o['مبلغ زد'] - pay_amt) > tolerance:
            status, reason = 'فرق مبلغ', 'قيمة العملية لا تساوي إجمالي طلب زد'
        elif not pay_status or pay_state == 'غير محدد':
            status, reason = 'تحتاج مراجعة', 'المبلغ والمرجع متوافقان لكن حالة الدفع غير متاحة للتحقق'
        else:
            status, reason = 'مطابق', 'تطابق المرجع والمبلغ وحالة العملية'
    results.append({**{k: v for k, v in o.items() if not k.startswith('_')},
                    'مبلغ المنصة': pay_amt, 'الفرق': round(o['مبلغ زد'] - pay_amt, 2) if pd.notna(o['مبلغ زد']) and pd.notna(pay_amt) else None,
                    'حالة عملية الدفع': pay_state, 'معرف العملية': tx, 'نتيجة المطابقة': status, 'التفاصيل': reason})

result = pd.DataFrame(results)
reverse = p.loc[~p.index.isin(matched_pay_rows)].copy()
reverse_report = pd.DataFrame({'رقم مرجع المنصة': reverse['_id'], 'مبلغ المنصة': reverse['_amount'],
                               'حالة عملية الدفع': reverse['_status'],
                               'معرف العملية': reverse[pay_transaction] if pay_transaction else '',
                               'سبب المراجعة': 'عملية في المنصة لا يوجد لها رقم طلب مطابق في نطاق زد'})

st.markdown('<div class="section-title">04 / لوحة نتائج المطابقة</div>', unsafe_allow_html=True)
counts = result['نتيجة المطابقة'].value_counts()
cols = st.columns(5)
for col, label, value in zip(cols, ['طلبات زد', 'مطابق', 'غير موجود في المنصة', 'فرق مبلغ', 'تحتاج مراجعة'],
                             [len(result), counts.get('مطابق', 0), counts.get('غير موجود في المنصة', 0), counts.get('فرق مبلغ', 0), counts.get('تحتاج مراجعة', 0)]):
    col.metric(label, f'{value:,}')
st.warning(f'عمليات في منصة الدفع دون رقم طلب مطابق في نطاق زد: **{len(reverse_report):,}**. قد تشمل عمليات خارج نطاق التاريخ أو طرق الدفع المختارة.') if len(reverse_report) else st.success('لا توجد عمليات إضافية غير مرتبطة بأرقام طلبات زد في نطاق المقارنة.')

st.markdown('<div class="section-title">05 / التفاصيل والتصدير</div>', unsafe_allow_html=True)
tab1, tab2, tab3 = st.tabs(['📋 جميع الطلبات', '⚠️ الفروقات والمراجعة', '💳 عمليات المنصة دون زد'])
problem = result[result['نتيجة المطابقة'] != 'مطابق'].copy()
with tab1:
    search = st.text_input('بحث برقم الطلب أو اسم العميل', placeholder='اكتب رقم الطلب أو اسم العميل...')
    statuses = st.multiselect('تصفية حسب النتيجة', result['نتيجة المطابقة'].unique().tolist())
    display = result.copy()
    if statuses:
        display = display[display['نتيجة المطابقة'].isin(statuses)]
    if search:
        display = display[display['رقم طلب زد'].astype(str).str.contains(search, case=False, regex=False) | display['اسم العميل'].astype(str).str.contains(search, case=False, regex=False)]
    st.dataframe(display, use_container_width=True, hide_index=True, height=450)
with tab2:
    st.dataframe(problem, use_container_width=True, hide_index=True, height=400)
with tab3:
    st.dataframe(reverse_report, use_container_width=True, hide_index=True, height=400)

summary = pd.DataFrame([
    {'المؤشر': 'المنصة', 'القيمة': gateway},
    {'المؤشر': 'تاريخ إنشاء التقرير', 'القيمة': datetime.now().strftime('%Y-%m-%d %H:%M')},
    {'المؤشر': 'عدد طلبات زد ضمن النطاق', 'القيمة': len(result)},
    {'المؤشر': 'مطابق', 'القيمة': counts.get('مطابق', 0)},
    {'المؤشر': 'غير موجود في المنصة', 'القيمة': counts.get('غير موجود في المنصة', 0)},
    {'المؤشر': 'فرق مبلغ', 'القيمة': counts.get('فرق مبلغ', 0)},
    {'المؤشر': 'تحتاج مراجعة', 'القيمة': counts.get('تحتاج مراجعة', 0)},
    {'المؤشر': 'عمليات المنصة دون زد', 'القيمة': len(reverse_report)},
    {'المؤشر': 'تنبيه', 'القيمة': 'المطابقة مرجعية ولا تثبت الإيداع البنكي الفعلي'},
])
try:
    excel_bytes = export_excel(result, reverse_report, summary, problem)
    st.download_button('📥 تصدير تقرير المطابقة Excel (.xlsx)', data=excel_bytes,
                       file_name=f'ashwered_reconciliation_{datetime.now():%Y%m%d_%H%M}.xlsx',
                       mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                       type='primary', use_container_width=True)
except ImportError:
    st.error('لتصدير Excel أضيفي openpyxl إلى requirements.txt.')

st.caption('ملاحظة محاسبية: يلزم التأكد من نوع المبلغ (إجمالي الطلب قبل العمولات) وحالة الدفع، ومراجعة المرتجعات والدفعات الجزئية والتسويات البنكية منفصلًا.')

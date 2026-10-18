"""Generate a fully editable Draw.io C4-style container diagram."""
from pathlib import Path
import xml.etree.ElementTree as ET

OUT = Path(__file__).resolve().parents[1] / 'Architecture_C4' / 'BionicPRO_Task2.drawio'
mxfile = ET.Element('mxfile', host='app.diagrams.net', modified='2026-10-18T12:00:00.000Z', agent='BionicPRO-Task2', version='24.7.17')
page = ET.SubElement(mxfile, 'diagram', id='bionicpro-task2', name='Task 2 - Reports ETL C4')
model = ET.SubElement(page,'mxGraphModel',dx='2400',dy='1550',grid='1',gridSize='10',guides='1',tooltips='1',connect='1',arrows='1',fold='1',page='1',pageScale='1',pageWidth='2550',pageHeight='1430',math='0',shadow='0')
root = ET.SubElement(model, 'root')
ET.SubElement(root, 'mxCell', id='0')
ET.SubElement(root, 'mxCell', id='1', parent='0')

COLORS = {'application': ('#DFF1EB','#277967'), 'store': ('#FFF2D6','#BB7C25'),
          'external': ('#F4F2FA','#846FAD'), 'user': ('#E6EFFF','#3768AB'),
          'pipeline': ('#FCE8DB','#C36A37'), 'accent': ('#E8F2FF','#2369AF')}

def cell(name,label,x,y,w,h,typ='application',desc=None):
    bg,border=COLORS[typ]
    style=f'rounded=1;arcSize=14;whiteSpace=wrap;html=1;fillColor={bg};strokeColor={border};strokeWidth=2;align=center;verticalAlign=middle;spacing=6;fontFamily=Arial;fontSize=17;fontColor=#18304B;shadow=0;'
    contents=f'<b>{label}</b>' + (f'<br/><font color="#4B6074">{desc}</font>' if desc else '')
    el=ET.SubElement(root,'mxCell',id=name,value=contents,style=style,vertex='1',parent='1')
    ET.SubElement(el,'mxGeometry',x=str(x),y=str(y),width=str(w),height=str(h),attrib={'as':'geometry'})

def text(name,label,x,y,w,h,size=20,color='#253D57',bold=False):
    style=f'text;html=1;whiteSpace=wrap;strokeColor=none;fillColor=none;align=left;verticalAlign=middle;fontFamily=Arial;fontSize={size};fontColor={color};fontStyle={1 if bold else 0};'
    el=ET.SubElement(root,'mxCell',id=name,value=label,style=style,vertex='1',parent='1')
    ET.SubElement(el,'mxGeometry',x=str(x),y=str(y),width=str(w),height=str(h),attrib={'as':'geometry'})

def container(name,label,x,y,w,h,color='#EAF3F9'):
    style=f'rounded=1;arcSize=9;whiteSpace=wrap;html=1;fillColor={color};strokeColor=#6B91AA;strokeWidth=2;dashed=1;dashPattern=8 5;align=left;verticalAlign=top;spacingTop=16;spacingLeft=17;fontSize=22;fontColor=#224E70;fontStyle=1;'
    el=ET.SubElement(root,'mxCell',id=name,value=label,style=style,vertex='1',parent='1')
    ET.SubElement(el,'mxGeometry',x=str(x),y=str(y),width=str(w),height=str(h),attrib={'as':'geometry'})

def edge(name,a,b,label,color='#64748B',dashed=False,points=None):
    style=f'edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;jettySize=auto;html=1;endArrow=block;endFill=1;strokeWidth=2;strokeColor={color};fontColor=#42536A;fontSize=14;labelBackgroundColor=#FFFFFF;'
    if dashed: style+='dashed=1;dashPattern=5 4;'
    e=ET.SubElement(root,'mxCell',id=name,value=label,style=style,edge='1',parent='1',source=a,target=b)
    g=ET.SubElement(e,'mxGeometry',relative='1',attrib={'as':'geometry'})
    if points:
        arr=ET.SubElement(g,'Array',attrib={'as':'points'})
        for x,y in points: ET.SubElement(arr,'mxPoint',x=str(x),y=str(y))

container('boundary','BionicPRO · регион РФ (хранение и обработка данных локально)',250,105,2240,1180)
text('heading','Задание 2 · Подготовка и выдача отчётов: ETL + ClickHouse + API',60,20,2210,65,25, bold=True)
text('subtitle','C4 Container (TO-BE) · DAG по расписанию + проверка принадлежности протеза + готовность периода',65,78,1900,32,16)
cell('patient','Пациент',25,265,185,105,'user','Получает отчёт')
cell('mobile','Android UI',310,190,285,116,'user','Кнопка «Скачать отчёт»')
cell('web','Web UI',310,376,285,112,'user','Локальная демонстрация')
cell('device','Бионический протез',40,1035,195,120,'external','ESP32 / 4G')
cell('reportapi','Reports API + BFF',760,268,332,162,'application','/auth/*, /reports<br/>Session cookie · AuthZ')
cell('keycloak','Keycloak RU',1200,174,330,118,'external','OIDC Code + PKCE S256')
cell('idp','Внешний региональный IdP',1670,174,320,118,'external','OIDC / LDAP / AD')
cell('session','Redis Session Store',1200,356,330,108,'store','Opaque session → user identity')
cell('crm','CRM / Patients',365,638,322,148,'application','Patient ↔ prosthesis<br/>Владение и идентичность')
cell('telemetry_ingest','Telemetry Ingest',365,1010,322,120,'application','Поток 4G → DB')
cell('telemetry_db','Telemetry DB',760,1000,300,122,'store','Сырые события')
cell('airflow','Apache Airflow',1120,745,335,152,'pipeline','DAG: extract → aggregate<br/>→ join → load')
cell('clickhouse','ClickHouse OLAP',1650,700,357,180,'store','user_prosthesis_reports<br/>+ etl_processed_days')
cell('keycloak_db','Keycloak DB (RU)',1675,355,310,111,'store','Региональные metadata')
cell('note','Контроль доступа',2050,590,344,160,'accent','(iss, sub) → patient_id<br/>Проверка ownership по CRM<br/>нет user_id из клиента')
text('legend','Отчёт доступен только после успешного ETL за каждый день запрошенного периода. Неполный период → HTTP 409.',265,1170,2100,53,17)

edge('01','patient','mobile','использует')
edge('02','patient','web','тестирует')
edge('03','mobile','reportapi','HTTPS + cookie')
edge('04','web','reportapi','HTTPS + cookie')
edge('05','reportapi','keycloak','OAuth Code + PKCE')
edge('06','keycloak','idp','federation')
edge('07','keycloak','keycloak_db','identity metadata')
edge('08','reportapi','session','server-side session')
edge('09','reportapi','crm','проверка ownership')
edge('10','device','telemetry_ingest','4G / TLS')
edge('11','telemetry_ingest','telemetry_db','запись событий')
edge('12','crm','airflow','extract users + devices',points=[(890,710)])
edge('13','telemetry_db','airflow','extract readings')
edge('14','airflow','clickhouse','витрина + watermark')
edge('15','reportapi','clickhouse','SELECT готового отчёта',points=[(1160,520),(1840,520)])
edge('16','reportapi','note','deny-by-default',dashed=True)

ET.indent(mxfile, space='  ')
OUT.write_bytes(ET.tostring(mxfile,encoding='utf-8',xml_declaration=True))
print(OUT, OUT.stat().st_size, 'bytes')

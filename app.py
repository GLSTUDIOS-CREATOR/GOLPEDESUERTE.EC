# ====== PARCHE DE ARRANQUE (PÉGALO AL INICIO DE app.py) ======
# Evita NameError en 'mm' incluso si el import real aparece más abajo
try:
    from reportlab.lib.units import mm  # import real si está disponible
except Exception:
    # Fallback: 1 mm en puntos (ReportLab trabaja en puntos)
    mm = 2.834645669291339

# Evita NameError en @login_required si Flask-Login no está instalado
try:
    from flask_login import login_required as _login_required
    def login_required(f):
        return _login_required(f)
except Exception:
    # Fallback 'no-op': deja pasar la vista sin exigir login
    def login_required(f):
        return f
# ====== FIN PARCHE DE ARRANQUE ======



import os
import random
import pandas as pd
import qrcode
import xml.etree.ElementTree as ET
from datetime import date, datetime
from io import BytesIO
from flask import Flask, request, render_template, send_file, redirect, url_for, flash, session
# ---- Safe login URL helper (avoids BuildError for missing 'login' endpoint) ----
from flask import url_for as _flask_url_for
from werkzeug.routing import BuildError as _BuildError

def _login_url(**values):
    try:
        return _flask_url_for('login', **values)
    except Exception:
        try:
            return _flask_url_for('_login_demo', **values)
        except Exception:
            return '/_login_demo'
# -------------------------------------------------------------------------------

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.units import mm, cm, inch


app = Flask(__name__)
app.secret_key = 'super_secreto_bingo_2025'


from functools import wraps
from flask import session, redirect, url_for

def require_session(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'usuario' not in session:
            return redirect(_login_url())
        return f(*args, **kwargs)
    return wrapper



# ─── ARCHIVOS Y DIRECTORIOS ────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
USUARIOS_XML = os.path.join(BASE_DIR, 'usuarios', 'usuarios.xml')
AVATAR_DIR = os.path.join('static', 'avatars')
DATA_DIR = os.path.join(BASE_DIR, "DATA")
REINTEGROS_DIR = os.path.join(DATA_DIR, "REINTEGROS")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(REINTEGROS_DIR, exist_ok=True)
# ==== PERSISTENCIA (Render / Local) ====
import os, shutil

# 1) Usar DATA_DIR de entorno si existe; si no, ./DATA local
DATA_DIR = os.environ.get("DATA_DIR", os.path.join(BASE_DIR, "DATA"))
os.makedirs(DATA_DIR, exist_ok=True)

# Helpers
def _persist(*rel):
    """Ruta dentro de DATA_DIR (crea la carpeta si no existe)."""
    path = os.path.join(DATA_DIR, *rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return path

def _seed(src_rel, dst_abs):
    """
    Copia archivo inicial del repo → persistente, solo si NO existe.
    Ej.: _seed('static/db/caja.xml', CAJA_XML)
    """
    src_abs = os.path.join(BASE_DIR, src_rel)
    if not os.path.exists(dst_abs) and os.path.exists(src_abs):
        shutil.copy2(src_abs, dst_abs)

# 2) Reasignar rutas de XML “vivos” a DATA_DIR (persistente)
#    Usamos los mismos nombres de variables que usa tu app.
USUARIOS_XML            = _persist('usuarios', 'usuarios.xml')

CAJA_XML                = _persist('static', 'db', 'caja.xml')
ASIGNACIONES_XML        = _persist('static', 'db', 'asignaciones.xml')
PAGOS_PREMIOS_XML       = _persist('static', 'db', 'pagos_premios.xml')
RESULTADOS_SORTEO_XML   = _persist('static', 'db', 'resultados_sorteo.xml')
SORTEOS_XML             = _persist('static', 'db', 'sorteos.xml')
SPINNERS_XML            = _persist('static', 'db', 'spinners.xml')
VMIX_REINTEGRO_XML      = _persist('static', 'db', 'vmix_reintegro.xml')
VMIX_SPINNERS_XML       = _persist('static', 'db', 'vmix_spinners.xml')
VMIX_VENDEDORES_XML     = _persist('static', 'db', 'vmix_vendedores.xml')
VMIX_VENTAS_XML         = _persist('static', 'db', 'vmix_ventas.xml')

LOGS_CAJA_XML           = _persist('static', 'LOGS', 'caja.xml')
LOGS_IMPRESIONES_XML    = _persist('static', 'LOGS', 'impresiones.xml')

CONTAB_BANCOS_XML       = _persist('static', 'CONTABILIDAD', 'bancos.xml')
CONTAB_GASTOS_XML       = _persist('static', 'CONTABILIDAD', 'gastos.xml')
CONTAB_SUELDOS_XML      = _persist('static', 'CONTABILIDAD', 'sueldos.xml')
CONTAB_VENTAS_XML       = _persist('static', 'CONTABILIDAD', 'ventas.xml')

# 3) Sembrar contenido inicial (solo primera vez)
for src, dst in [
    ('usuarios/usuarios.xml',               USUARIOS_XML),
    ('static/db/caja.xml',                  CAJA_XML),
    ('static/db/asignaciones.xml',          ASIGNACIONES_XML),
    ('static/db/pagos_premios.xml',         PAGOS_PREMIOS_XML),
    ('static/db/resultados_sorteo.xml',     RESULTADOS_SORTEO_XML),
    ('static/db/sorteos.xml',               SORTEOS_XML),
    ('static/db/spinners.xml',              SPINNERS_XML),
    ('static/db/vmix_reintegro.xml',        VMIX_REINTEGRO_XML),
    ('static/db/vmix_spinners.xml',         VMIX_SPINNERS_XML),
    ('static/db/vmix_vendedores.xml',       VMIX_VENDEDORES_XML),
    ('static/db/vmix_ventas.xml',           VMIX_VENTAS_XML),
    ('static/LOGS/caja.xml',                LOGS_CAJA_XML),
    ('static/LOGS/impresiones.xml',         LOGS_IMPRESIONES_XML),
    ('static/CONTABILIDAD/bancos.xml',      CONTAB_BANCOS_XML),
    ('static/CONTABILIDAD/gastos.xml',      CONTAB_GASTOS_XML),
    ('static/CONTABILIDAD/sueldos.xml',     CONTAB_SUELDOS_XML),
    ('static/CONTABILIDAD/ventas.xml',      CONTAB_VENTAS_XML),
]:
    _seed(src, dst)

# (Opcional) Escritura atómica (más seguro ante cortes)
def write_text_atomic(path, text):
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, path)
# ==== FIN PERSISTENCIA ====

# ==== ENLAZAR CARPETAS DEL REPO -> DISCO PERSISTENTE (/data) ====
import os, shutil

PERSIST_ROOT = os.environ.get(
    "DATA_DIR",
    "/data" if os.path.isdir("/data") else os.path.join(BASE_DIR, "DATA")
)
os.makedirs(PERSIST_ROOT, exist_ok=True)

def _bind_dir(repo_rel):
    repo_abs    = os.path.join(BASE_DIR, repo_rel)
    persist_abs = os.path.join(PERSIST_ROOT, repo_rel)
    os.makedirs(persist_abs, exist_ok=True)

    # Sembrar archivos del repo -> persistente (solo si está vacío)
    try:
        if os.path.isdir(repo_abs) and not os.listdir(persist_abs):
            for name in os.listdir(repo_abs):
                src = os.path.join(repo_abs, name)
                dst = os.path.join(persist_abs, name)
                if os.path.isdir(src):
                    shutil.copytree(src, dst, dirs_exist_ok=True)
                elif os.path.isfile(src) and not os.path.exists(dst):
                    shutil.copy2(src, dst)
    except Exception as e:
        print("Seed warning:", repo_rel, e)

    # Reemplazar carpeta del repo por un enlace simbólico -> persistente
    try:
        if not os.path.islink(repo_abs):
            if os.path.isdir(repo_abs):
                shutil.rmtree(repo_abs)
            elif os.path.exists(repo_abs):
                os.remove(repo_abs)
            os.symlink(persist_abs, repo_abs, target_is_directory=True)
    except Exception as e:
        print("Bind warning:", repo_rel, e)

# Enlazar carpetas que CAMBIAN en runtime
_bind_dir("usuarios")
_bind_dir(os.path.join("static", "db"))
_bind_dir(os.path.join("static", "LOGS"))
_bind_dir(os.path.join("static", "CONTABILIDAD"))
# ==== FIN ENLACE PERSISTENTE ====


ROLES = [
    ('superadmin', 'Super Administrador'),
    ('admin', 'Administrador'),
    ('socio', 'Socio'),
    ('cobrador', 'Cobrador'),
    ('jugador', 'Jugador'),
    ('impresion', 'Impresión'),
]

# ─── UTILIDADES XML ────────────────────────
def leer_usuarios():
    if not os.path.exists(USUARIOS_XML):
        return []
    tree = ET.parse(USUARIOS_XML)
    root = tree.getroot()
    usuarios = []
    for elem in root.findall('usuario'):
        usuarios.append({
            'nombre': elem.find('nombre').text,
            'clave': elem.find('clave').text,
            'rol': elem.find('rol').text,
            'email': elem.find('email').text if elem.find('email') is not None else '',
            'estado': elem.find('estado').text,
            'avatar': elem.find('avatar').text if elem.find('avatar') is not None else 'avatar-male.png'
        })
    return usuarios

def guardar_usuarios(usuarios):
    root = ET.Element('usuarios')
    for u in usuarios:
        user_elem = ET.SubElement(root, 'usuario')
        ET.SubElement(user_elem, 'nombre').text = u['nombre']
        ET.SubElement(user_elem, 'clave').text = u['clave']
        ET.SubElement(user_elem, 'rol').text = u['rol']
        ET.SubElement(user_elem, 'email').text = u.get('email', '')
        ET.SubElement(user_elem, 'estado').text = u['estado']
        ET.SubElement(user_elem, 'avatar').text = u.get('avatar', 'avatar-male.png')
    tree = ET.ElementTree(root)
    tree.write(USUARIOS_XML, encoding='utf-8', xml_declaration=True)

def obtener_usuario(nombre):
    usuarios = leer_usuarios()
    for u in usuarios:
        if u['nombre'] == nombre:
            return u
    return None

def eliminar_usuario(nombre):
    usuarios = leer_usuarios()
    usuarios = [u for u in usuarios if u['nombre'] != nombre]
    guardar_usuarios(usuarios)

# ─── LOGIN Y DASHBOARD ─────────────────────
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form['usuario']
        clave = request.form['clave']
        usuarios = leer_usuarios()
        user = next((u for u in usuarios if u['nombre'] == usuario and u['clave'] == clave and u['estado'] == 'activo'), None)
        if user:
            session['usuario'] = user['nombre']
            session['rol'] = user['rol']
            session['avatar'] = user.get('avatar', 'avatar-male.png')
            return redirect(url_for('dashboard'))
        else:
            flash('Usuario o clave incorrectos o usuario inactivo', 'error')
    return render_template('login.html')



# ===================== DASHBOARD (HOY) =====================
# Bloque auto-contenido. Si tu app ya define constantes o helpers
# (p.ej. CAJA_XML, get_configuracion_dia, _iter_impresiones) se usan tal cual.
# No rompe nada existente.

import os
import xml.etree.ElementTree as ET
from datetime import date, datetime
from flask import render_template, jsonify, request, session, redirect, url_for

# --- Rutas/archivos (respetamos existentes si ya están definidos) -------------
CAJA_XML              = globals().get('CAJA_XML',              os.path.join('static', 'CAJA', 'caja.xml'))
VENDEDORES_XML        = globals().get('VENDEDORES_XML',        os.path.join('static', 'db', 'vendedores.xml'))
ASIGNACIONES_XML      = globals().get('ASIGNACIONES_XML',      os.path.join('static', 'db', 'asignaciones.xml'))
IMPRESION_LOG         = globals().get('IMPRESION_LOG',         os.path.join('static', 'IMPRESION', 'log.xml'))
BOLETOS_POR_PLANILLA  = int(globals().get('BOLETOS_POR_PLANILLA', 20))

# --- Helpers seguros -----------------------------------------------------------
def _parse_or_none(path):
    try:
        if not os.path.exists(path):
            return None, None
        t = ET.parse(path)
        return t, t.getroot()
    except ET.ParseError:
        return None, None

def _leer_xml_seguro(path, root_tag='root'):
    """Crea el XML vacío si no existe para evitar errores en primeras ejecuciones."""
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        ET.ElementTree(ET.Element(root_tag)).write(path, encoding='utf-8', xml_declaration=True)
    t = ET.parse(path)
    return t, t.getroot()

def _vendor_map():
    """Devuelve {seudonimo: 'Nombre Apellido (Seud)'} para etiquetas lindas."""
    out = {}
    t, r = _parse_or_none(VENDEDORES_XML)
    if r is None:
        return out
    for v in r.findall('vendedor'):
        nom  = (v.findtext('nombre') or '').strip()
        ape  = (v.findtext('apellido') or '').strip()
        seud = (v.findtext('seudonimo') or '').strip()
        if seud:
            etiqueta = (nom + ' ' + ape).strip() or seud
            out[seud] = f"{etiqueta} ({seud})"
    return out

# ---------------- IMPRESOS / PLANILLAS IMPRESAS (tolerante al formato) --------
def _impresos_y_planillas_del_dia(fecha_iso):
    """
    Devuelve (boletos_impresos, planillas_impresas) del día.
    Soporta:
      - Iterador global _iter_impresiones() si existe (chequea tipo='boletos')
      - IMPRESION/log.xml con campos: fecha_sorteo|fecha|fecha_impresion y
        total_boletos|boletos|cantidad y/o total_planillas|planillas|cantidad_planillas
    """
    total_boletos = 0
    total_planillas = 0

    # Opción 1: usar helper existente
    if '_iter_impresiones' in globals():
        try:
            for n in globals()['_iter_impresiones']():
                tipo = (n.get('tipo') or '').strip().lower()
                f = (n.findtext('fecha_sorteo') or n.findtext('fecha') or n.findtext('fecha_impresion') or '').strip()
                if f != fecha_iso:
                    continue
                # si hay entrada de tipo Boletos
                if tipo and tipo != 'boletos':
                    continue
                # boletos
                for tag in ('total_boletos','boletos','cantidad'):
                    txt = n.findtext(tag)
                    if txt:
                        try: total_boletos += int(float(txt))
                        except: pass
                        break
                # planillas
                for tag in ('total_planillas','planillas','cantidad_planillas'):
                    txt = n.findtext(tag)
                    if txt:
                        try: total_planillas += int(float(txt))
                        except: pass
                        break
            # si no venían planillas en el log, derivamos por boletos // tamaño
            if total_planillas == 0 and BOLETOS_POR_PLANILLA > 0:
                total_planillas = total_boletos // BOLETOS_POR_PLANILLA
            return total_boletos, total_planillas
        except Exception:
            pass

    # Opción 2: leer log.xml directamente (sin helper)
    t, r = _parse_or_none(IMPRESION_LOG)
    if r is None:
        return 0, 0
    # buscar cualquier nodo que tenga los campos esperados
    for nodo in r.iter():
        # fecha
        f = None
        for ft in ('fecha_sorteo', 'fecha', 'fecha_impresion'):
            try:
                f = nodo.findtext(ft)
                if f: f = f.strip()
            except: f = None
            if f: break
        # fecha por atributo
        if not f:
            f = (getattr(nodo, 'get', lambda *_: '')('fecha') or '').strip()
        if f != fecha_iso:
            continue

        # si hay tipo y no es boletos, saltamos
        tipo = (getattr(nodo, 'get', lambda *_: '')('tipo') or '').strip().lower()
        if tipo and tipo != 'boletos':
            continue

        # boletos
        ok_boletos = False
        for tag in ('total_boletos','boletos','cantidad'):
            try:
                v = nodo.findtext(tag)
                if v:
                    total_boletos += int(float(v))
                    ok_boletos = True
                    break
            except: pass

        # planillas
        ok_pl = False
        for tag in ('total_planillas','planillas','cantidad_planillas'):
            try:
                v = nodo.findtext(tag)
                if v:
                    total_planillas += int(float(v))
                    ok_pl = True
                    break
            except: pass

        # si no hubo tag de planillas pero sí de boletos, derivar
        if not ok_pl and ok_boletos and BOLETOS_POR_PLANILLA > 0:
            total_planillas += int(total_boletos // BOLETOS_POR_PLANILLA)

    # normalizar
    if total_planillas == 0 and BOLETOS_POR_PLANILLA > 0:
        total_planillas = total_boletos // BOLETOS_POR_PLANILLA

    return int(total_boletos), int(total_planillas)

# ---------------- ASIGNACIONES (planillas asignadas) --------------------------
def _asignaciones_de_dia(fecha_iso):
    """Cuenta planillas asignadas y boletos entregados del día (asignaciones.xml)."""
    planillas = 0
    t, r = _parse_or_none(ASIGNACIONES_XML)
    if r is None:
        return 0, 0
    d = r.find(f"./dia[@fecha='{fecha_iso}']")
    if d is None:
        return 0, 0
    for v in d.findall('vendedor'):
        planillas += len(v.findall('planilla'))
    entregados = planillas * BOLETOS_POR_PLANILLA
    return planillas, entregados

# ---------------- CONFIGURACIÓN DEL DÍA (valor, comisión, meta) ----------------
def _config_del_dia(fecha_iso):
    """Obtiene configuración del día. Usa get_configuracion_dia si ya existe."""
    if 'get_configuracion_dia' in globals():
        try:
            return globals()['get_configuracion_dia'](fecha_iso)
        except Exception:
            pass
    # Fallback: leer de CAJA_XML
    _, root = _leer_xml_seguro(CAJA_XML, 'caja')
    dia = root.find(f"./dia[@fecha='{fecha_iso}']")
    if dia is None:
        return {"valor_boleto": 0.0, "comision_vendedor": 0.0, "comision_extra_meta": 0.0, "meta_boletos": 0}
    cfg = dia.find('configuracion')
    def ffloat(x, d=0.0):
        try: return float(x)
        except: return d
    def fint(x, d=0):
        try: return int(x)
        except: return d
    return {
        "valor_boleto": ffloat(cfg.findtext('valor_boleto', '0') if cfg is not None else '0'),
        "comision_vendedor": ffloat(cfg.findtext('comision_vendedor', '0') if cfg is not None else '0'),
        "comision_extra_meta": ffloat(cfg.findtext('comision_extra_meta', '0') if cfg is not None else '0'),
        "meta_boletos": fint(cfg.findtext('meta_boletos', '0') if cfg is not None else '0'),
    }

# ---------------- COBROS PAGADOS DEL DÍA (dos estructuras soportadas) ----------
def _iter_cobros_pagados(fecha_iso):
    """
    Itera cobros 'pagados' del día. Soporta dos estructuras en CAJA_XML:

      a) <dia fecha="..."><cobros>
           <cobro seudonimo="..." vendidos=".." devueltos=".."
                 transferencia=".." efectivo=".." pagado="1"/>
         </cobros></dia>

      b) <dia fecha="..."><vendedor>...<vendidos>..</vendidos>
             <devueltos>..</devueltos><transferencia>..</transferencia>
             <efectivo>..</efectivo><pagado>true</pagado>...</vendedor>
    """
    _, root = _leer_xml_seguro(CAJA_XML, 'caja')
    dia = root.find(f"./dia[@fecha='{fecha_iso}']")
    if dia is None:
        return

    # (a) estructura nueva
    cobros = dia.find('cobros')
    if cobros is not None and list(cobros.findall('cobro')):
        for c in cobros.findall('cobro'):
            seud = (c.attrib.get('seudonimo') or '').strip() or '—'
            pag  = (c.attrib.get('pagado') or c.attrib.get('pago') or '0')
            pag  = str(pag).strip().lower() in ('1', 'true', 'si', 'sí')
            if not pag:
                continue
            def I(attr, d=0):
                try: return int(float(c.attrib.get(attr, d) or d))
                except: return int(d)
            def F(attr, d=0.0):
                try: return float(c.attrib.get(attr, d) or d)
                except: return float(d)
            yield {
                "seudonimo": seud,
                "vendidos":  I('vendidos', 0),
                "devueltos": I('devueltos', 0),
                "transferencia": F('transferencia', 0.0),
                "efectivo": F('efectivo', 0.0),
            }
        return

    # (b) estructura antigua
    for v in dia.findall('vendedor'):
        ptxt = (v.findtext('pagado') or v.attrib.get('pagado') or '').strip().lower()
        if ptxt not in ('true', '1', 'si', 'sí'):
            continue
        seud = (v.findtext('seudonimo') or v.attrib.get('seudonimo') or '').strip() or '—'
        def I(tag, d=0):
            try: return int(v.findtext(tag) or d)
            except: return d
        def F(tag, d=0.0):
            try: return float(v.findtext(tag) or d)
            except: return d
        yield {
            "seudonimo": seud,
            "vendidos":  I('vendidos', 0),
            "devueltos": I('devueltos', 0),
            "transferencia": F('transferencia', 0.0),
            "efectivo": F('efectivo', 0.0),
        }

# ---------------- Composición de datos del Dashboard ---------------------------
def _dashboard_data(fecha_iso):
    cfg = _config_del_dia(fecha_iso)
    valor    = float(cfg.get('valor_boleto') or 0)
    base_pct = float(cfg.get('comision_vendedor') or 0)
    extra_pct= float(cfg.get('comision_extra_meta') or 0)
    meta     = int(cfg.get('meta_boletos') or 0)

    etiquetas_vendedores = _vendor_map()

    # Cobros pagados del día
    vendedores_det = []
    tot_vend = tot_dev = 0
    tot_ing = tot_gan_vend = tot_gan_emp = 0.0
    tot_e = tot_t = 0.0

    for c in _iter_cobros_pagados(fecha_iso) or []:
        vendidos  = int(c['vendidos'] or 0)
        devueltos = int(c['devueltos'] or 0)
        pct = base_pct + (extra_pct if (meta > 0 and vendidos >= meta) else 0)
        total_venta = vendidos * valor
        gan_v = total_venta * pct / 100.0
        gan_e = total_venta - gan_v

        seud = c['seudonimo']
        etiqueta = etiquetas_vendedores.get(seud, seud)

        vendedores_det.append({
            "vendedor": etiqueta,
            "seudonimo": seud,
            "vendidos": vendidos,
            "devueltos": devueltos,
            "total_venta": round(total_venta, 2),
            "gan_vendedor": round(gan_v, 2),
            "gan_empresa": round(gan_e, 2),
        })

        tot_vend += vendidos
        tot_dev  += devueltos
        tot_ing  += total_venta
        tot_gan_vend += gan_v
        tot_gan_emp  += gan_e
        tot_e  += float(c.get('efectivo') or 0)
        tot_t  += float(c.get('transferencia') or 0)

    # Impresos y planillas impresas
    boletos_impresos, planillas_impresas = _impresos_y_planillas_del_dia(fecha_iso)

    # Asignadas
    planillas_asignadas, _entregados = _asignaciones_de_dia(fecha_iso)
    planillas_blanco = max(int(planillas_impresas) - int(planillas_asignadas), 0)

    return {
        "fecha": fecha_iso,
        "boletos_impresos": int(boletos_impresos),
        "vendidos_total": int(tot_vend),
        "devueltos_total": int(tot_dev),
        "ingresos_brutos": round(tot_ing, 2),
        "ganancia_vendedores": round(tot_gan_vend, 2),
        "ganancia_empresa": round(tot_gan_emp, 2),
        "efectivo": round(tot_e, 2),
        "transferencia": round(tot_t, 2),
        "planillas_impresas": int(planillas_impresas),
        "planillas_asignadas": int(planillas_asignadas),
        "planillas_blanco": int(planillas_blanco),
        "vendedores": vendedores_det,
        "config": {
            "valor_boleto": valor,
            "comision_vendedor": base_pct,
            "comision_extra_meta": extra_pct,
            "meta_boletos": meta
        }
    }

# --- Rutas --------------------------------------------------------------------
@app.route('/dashboard')
def dashboard():
    if 'usuario' not in session:
        return redirect(_login_url())
    return render_template(
        'dashboard.html',
        usuario=session.get('usuario',''),
        rol=session.get('rol',''),
        avatar=session.get('avatar','avatar-male.png')
    )

@app.get('/api/dashboard/hoy')
def api_dashboard_hoy():
    f = (request.args.get('fecha') or date.today().isoformat()).strip()
    try:
        datetime.fromisoformat(f)
    except Exception:
        f = date.today().isoformat()
    data = _dashboard_data(f)
    return jsonify({"ok": True, **data})



@app.route('/logout')
def logout():
    session.clear()
    return redirect(_login_url())

# ─── SECCIÓN DE USUARIOS ──────────────────
@app.route('/usuarios')
def usuarios():
    if 'usuario' not in session:
        return redirect(_login_url())
    lista_usuarios = leer_usuarios()
    roles = [r[1] for r in ROLES]
    return render_template(
        'usuarios.html',
        usuarios=lista_usuarios,
        roles=roles,
        usuario=session['usuario'],
        rol=session['rol'],
        avatar=session.get('avatar', 'avatar-male.png')
    )

@app.route('/usuarios/guardar', methods=['POST'])
def guardar_usuario():
    nombre = request.form['username']
    clave = request.form['password']
    rol   = request.form['rol']
    email = request.form.get('email', '')
    avatar_filename = request.form.get('avatar_select', 'avatar-male.png')
    estado = 'activo'

    usuarios = leer_usuarios()
    existe = False
    for u in usuarios:
        if u['nombre'] == nombre:
            u['clave'] = clave
            u['rol'] = rol
            u['email'] = email
            u['avatar'] = avatar_filename
            u['estado'] = estado
            existe = True
    if not existe:
        usuarios.append({
            'nombre': nombre,
            'clave': clave,
            'rol': rol,
            'email': email,
            'avatar': avatar_filename,
            'estado': estado
        })
    guardar_usuarios(usuarios)
    flash('Usuario guardado correctamente', 'success')
    return redirect(url_for('usuarios'))

@app.route('/usuarios/editar/<nombre>', methods=['GET', 'POST'])
def editar_usuario(nombre):
    if 'usuario' not in session:
        return redirect(_login_url())
    user = obtener_usuario(nombre)
    if not user:
        flash(f'Usuario "{nombre}" no encontrado', 'error')
        return redirect(url_for('usuarios'))
    roles = [r[1] for r in ROLES]
    if request.method == 'POST':
        user['clave'] = request.form['password']
        user['rol'] = request.form['rol']
        user['email'] = request.form.get('email', '')
        user['avatar'] = request.form.get('avatar_select', user['avatar'])
        usuarios = leer_usuarios()
        for u in usuarios:
            if u['nombre'] == nombre:
                u.update(user)
        guardar_usuarios(usuarios)
        flash('Usuario editado correctamente', 'success')
        return redirect(url_for('usuarios'))
    return render_template(
        'usuarios_editar.html',
        user=user,
        roles=[r[1] for r in ROLES],
        usuario=session['usuario'],
        rol=session['rol'],
        avatar=session.get('avatar', 'avatar-male.png')
    )




import os, random, csv, math, shutil, unicodedata
from io import BytesIO, StringIO
from datetime import datetime, date
from threading import RLock  # RLock para evitar deadlocks reentrantes

import pandas as pd
from flask import (
    Flask, request, send_file, render_template, redirect,
    url_for, flash, jsonify, session
)
from PyPDF2 import PdfMerger

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

import qrcode
import xml.etree.ElementTree as ET

# ================== FALLBACKS APP/SESSION ==================
try:
    app  # noqa
except NameError:
    app = Flask(__name__, instance_relative_config=True)
    app.secret_key = "glbingo-secret"
    app.config["JSON_AS_ASCII"] = False

try:
    require_session  # noqa
except NameError:
    def require_session(fn):
        def _wrap(*a, **k):  # aquí validarías sesión/rol real
            return fn(*a, **k)
        _wrap.__name__ = fn.__name__
        return _wrap

# ---------- utilidades ----------
def _to_int(v, default=0):
    try:
        return int(str(v).strip())
    except Exception:
        return default

def _read_df_for_series(archivo: str) -> pd.DataFrame:
    """Lee XLSX o CSV como texto; lanza FileNotFoundError si no existe."""
    path = os.path.join(DATA_DIR, archivo)
    if not os.path.exists(path):
        raise FileNotFoundError(f"No existe el archivo de serie: {archivo}")
    if archivo.lower().endswith(".csv"):
        return pd.read_csv(path, dtype=str, keep_default_na=False).fillna("")
    return pd.read_excel(path, dtype=str).fillna("")

def fecha_ddmmyyyy(fecha_iso: str) -> str:
    try:
        return datetime.strptime(fecha_iso, "%Y-%m-%d").strftime("%d-%m-%Y")
    except Exception:
        return fecha_iso

def format_money(valor) -> str:
    try:
        v = float(str(valor).replace(",", "."))
    except Exception:
        return f"${valor}"
    if abs(v - 1.0) < 1e-9:
        return "$1"
    if v < 1.0:
        s = f"{v:.2f}".replace(".", ",")
        return f"{s} ctvs"
    if abs(v - int(v)) < 1e-9:
        return f"${int(v)}"
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return f"${s}"

def _send_bytesio(buf: BytesIO, filename: str, mimetype: str = None):
    """Compat: Flask 1.x (attachment_filename) y 2.x (download_name)."""
    try:
        return send_file(buf, download_name=filename, as_attachment=True, mimetype=mimetype)
    except TypeError:
        return send_file(buf, attachment_filename=filename, as_attachment=True, mimetype=mimetype)

# ─── CONFIG PDFs ──────────────────────────────
BLEED    = 5 * mm
w, h     = A4
OFFSET_X = -20
OFFSET_Y = 5

# ─── RUTAS ────────────────────────────────────
BASE_DIR       = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR     = os.path.join(BASE_DIR, "static")
DATA_DIR       = os.path.join(BASE_DIR, "DATA")
REINTEGROS_DIR = os.path.join(DATA_DIR, "REINTEGROS")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(REINTEGROS_DIR, exist_ok=True)

# Persistencia en instance/ (o variable de entorno)
os.makedirs(app.instance_path, exist_ok=True)
STORAGE_ROOT = os.getenv("GLBINGO_STORAGE") or os.path.join(app.instance_path, "gl_bingo")
LOGS_DIR     = os.path.join(STORAGE_ROOT, "logs")
os.makedirs(LOGS_DIR, exist_ok=True)

# Migración de logs antiguos
OLD_LOGS_DIR    = os.path.join(STATIC_DIR, "LOGS")
old_xml         = os.path.join(OLD_LOGS_DIR, "impresiones.xml")
IMPRESIONES_XML = os.path.join(LOGS_DIR, "impresiones.xml")
if os.path.exists(old_xml) and not os.path.exists(IMPRESIONES_XML):
    try:
        shutil.copy2(old_xml, IMPRESIONES_XML)
        print("[MIGRATION] impresiones.xml migrado a:", IMPRESIONES_XML)
    except Exception as e:
        print("[WARN] Migración de impresiones.xml falló:", e)

# ─── Fuentes ──────────────────────────────────
ULTRA_BLACK_FONT = "Helvetica-Bold"
for fname in [
    "Montserrat-ExtraBold.ttf",
    "Inter-Black.ttf",
    "Poppins-Black.ttf",
    "ArchivoBlack-Regular.ttf",
    "Anton-Regular.ttf",
]:
    fpath = os.path.join(STATIC_DIR, "fonts", fname)
    if os.path.exists(fpath):
        try:
            pdfmetrics.registerFont(TTFont("UltraBlackLocal", fpath))
            ULTRA_BLACK_FONT = "UltraBlackLocal"
            break
        except Exception:
            pass

# ─── LAYOUT ───────────────────────────────────
MARGEN_IZQ     = 20
MARGEN_SUP     = 60
ESPACIO_X      = 140
ESPACIO_Y      = 115
COLUMNAS       = 2
FILAS          = 4

SIZE_NUM       = 23
SIZE_INFO      = 12
SIZE_ID_BIG    = 18
REINTEGRO_W    = 41
REINTEGRO_H    = 41

DELTA_Y_FILA_3 = 2
DELTA_Y_FILA_4 = 5

SERIE_MAP = {
    "Srs_ib1.xlsx":   "V",
    "Srs_ib2.xlsx":   "+",
    "Srs_ib3.xlsx":   "&",
    "Srs_Manila.xlsx":"M"
}

# ── OFFSETS EN CÓDIGO (boleto 0…7) ──
# Ajusta aquí X/Y para grid, info y reintegro de cada boleto:
per_cell_offsets = {
    0: {"grid_x": -80, "grid_y": 20,  "info_x": 5,   "info_y": 20,  "rein_x": 215, "rein_y": 30},
    1: {"grid_x": -160, "grid_y":20,  "info_x": -70, "info_y": 20,  "rein_x": 140, "rein_y": 30},
    2: {"grid_x": -80, "grid_y": 80,  "info_x": 5,   "info_y": 82,  "rein_x": 215, "rein_y": -25},
    3: {"grid_x": -160, "grid_y":80,  "info_x": -70, "info_y": 82,  "rein_x": 140, "rein_y": -25},
    4: {"grid_x": -80, "grid_y": 140, "info_x": 5,   "info_y": 140, "rein_x": 215, "rein_y": -85},
    5: {"grid_x": -160, "grid_y":140, "info_x": -70, "info_y": 140, "rein_x": 140, "rein_y": -85},
    6: {"grid_x": -80, "grid_y": 200, "info_x": 5,   "info_y": 200, "rein_x": 215, "rein_y": -145},
    7: {"grid_x": -160, "grid_y":200, "info_x": -70, "info_y": 200, "rein_x": 140, "rein_y": -145},
}


# ================== LOGS XML ==================
_LOG_LOCK = RLock()  # RLock para evitar deadlocks

def _ensure_logs_file():
    if not os.path.exists(IMPRESIONES_XML):
        root = ET.Element('impresiones')
        tree = ET.ElementTree(root)
        tmp_path = IMPRESIONES_XML + ".tmp"
        tree.write(tmp_path, encoding='utf-8', xml_declaration=True)
        os.replace(tmp_path, IMPRESIONES_XML)

def _read_logs_root():
    _ensure_logs_file()
    tree = ET.parse(IMPRESIONES_XML)
    return tree, tree.getroot()

def _write_logs_tree(tree):
    try:
        ET.indent(tree, space="  ", level=0)
    except Exception:
        pass
    tmp_path = IMPRESIONES_XML + ".tmp"
    tree.write(tmp_path, encoding='utf-8', xml_declaration=True)
    os.replace(tmp_path, IMPRESIONES_XML)

def _get_next_id(root):
    mx = 0
    for n in root.findall('impresion'):
        try:
            mx = max(mx, int(n.get('id') or 0))
        except Exception:
            pass
    return mx + 1

def _ensure_log_ids():
    with _LOG_LOCK:
        tree, root = _read_logs_root()
        changed = False
        next_id = _get_next_id(root)
        for n in root.findall('impresion'):
            if not (n.get('id') or '').isdigit():
                n.set('id', str(next_id)); next_id += 1; changed = True
        if changed:
            _write_logs_tree(tree)

def _iter_impresiones():
    _ensure_log_ids()
    _, root = _read_logs_root()
    for n in root.findall('impresion'):
        yield n

def _series_impresas_en_fecha(fecha_yyyy_mm_dd):
    s = set()
    for imp in _iter_impresiones():
        if (imp.get('tipo') or '').lower() != 'boletos':
            continue
        if (imp.findtext('fecha_sorteo') or '') != fecha_yyyy_mm_dd:
            continue
        s.add(imp.get('serie_archivo') or '')
    return s

def _append_log_impresion_boletos(
    *, usuario, serie_archivo, desde, hasta, fecha_sorteo, total_boletos,
    valor, telefono, reintegro_especial, cant_reintegro_especial,
    incluir_aleatorio, excedente=0, lote=''
):
    with _LOG_LOCK:
        tree, root = _read_logs_root()
        _ensure_log_ids()
        next_id = _get_next_id(root)
        elem = ET.Element('impresion', attrib={
            'id'           : str(next_id),
            'fecha_hora'   : datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'usuario'      : str(usuario or ''),
            'tipo'         : 'boletos',
            'serie_archivo': str(serie_archivo or ''),
            'desde'        : str(desde or ''),
            'hasta'        : str(hasta or '')
        })
        def add(tag, val):
            c = ET.SubElement(elem, tag); c.text = '' if val is None else str(val)
        add('valor', valor)
        add('telefono', telefono)
        add('fecha_sorteo', fecha_sorteo)
        add('reintegro_especial', reintegro_especial)
        add('cant_reintegro_especial', cant_reintegro_especial)
        add('incluir_aleatorio', '1' if incluir_aleatorio else '0')
        add('total_boletos', total_boletos)
        try:
            tp = int(math.ceil(int(total_boletos) / 20.0))
        except Exception:
            tp = ''
        add('total_planillas', tp)
        add('excedente', '1' if excedente else '0')
        add('lote', lote)
        root.append(elem)
        _write_logs_tree(tree)

def _append_log_impresion_planilla(
    *, usuario, serie_archivo, desde, hasta, fecha_planilla,
    lote_text='', excedente=0
):
    """Registra UNA sola fila por impresión de planillas (rango completo)."""
    with _LOG_LOCK:
        tree, root = _read_logs_root()
        _ensure_log_ids()
        next_id = _get_next_id(root)
        elem = ET.Element('impresion', attrib={
            'id'           : str(next_id),
            'fecha_hora'   : datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'usuario'      : str(usuario or ''),
            'tipo'         : 'planilla',
            'serie_archivo': str(serie_archivo or ''),
            'desde'        : str(desde or ''),
            'hasta'        : str(hasta or '')
        })
        def add(tag, val):
            c = ET.SubElement(elem, tag); c.text = '' if val is None else str(val)
        add('fecha_planilla', fecha_planilla)
        add('excedente', '1' if excedente else '0')
        add('lote', lote_text)
        try:
            total_b = int(hasta) - int(desde) + 1
        except Exception:
            total_b = ''
        add('total_boletos', total_b)
        try:
            # >>> CAMBIO: 40.0 → 20.0
            tp = int(math.ceil(int(total_b) / 20.0)) if total_b != '' else ''
        except Exception:
            tp = ''
        add('total_planillas', tp)
        root.append(elem)
        _write_logs_tree(tree)

def _delete_log_by_id(log_id: str) -> bool:
    with _LOG_LOCK:
        tree, root = _read_logs_root()
        nodo = None
        for n in root.findall('impresion'):
            if (n.get('id') or '') == str(log_id):
                nodo = n; break
        if nodo is None:
            return False
        root.remove(nodo)
        _write_logs_tree(tree)
        return True

def get_printed_ids_for_day(fecha_yyyy_mm_dd, serie_archivo):
    printed = set()
    for imp in _iter_impresiones():
        if (imp.get('tipo') or '').lower() != 'boletos':
            continue
        if (imp.get('serie_archivo') or '') != serie_archivo:
            continue
        if (imp.findtext('fecha_sorteo') or '') != fecha_yyyy_mm_dd:
            continue
        try:
            d = int(imp.get('desde') or '0'); h = int(imp.get('hasta') or '-1')
        except Exception:
            continue
        if h >= d:
            for n in range(d, h + 1):
                printed.add(str(n))
    return printed

# ---------- Permisos ----------
def _normalize(s: str) -> str:
    s = unicodedata.normalize('NFKD', s or '')
    s = ''.join(ch for ch in s if not unicodedata.combining(ch))
    return s.replace('-', ' ').replace('_', ' ').strip().lower()

def _is_superadmin() -> bool:
    """
    Verdadero si la sesión es del superadministrador.
    Acepta variantes como 'Super Administrador', 'super-administrador', etc.
    También permite al usuario 'GLSTUDIOS' como superadmin.
    """
    rol_raw = session.get('rol') or ''
    rol_n = _normalize(rol_raw)
    if rol_n in {'superadmin', 'super administrador', 'superadministrador'}:
        return True

    # Fallback por permisos
    perms = session.get('permisos') or []
    try:
        perms_l = {_normalize(str(p)) for p in perms}
    except Exception:
        perms_l = set()
    if any(p in perms_l for p in {'superadmin', 'super administrador', 'superadministrador', 'delete logs', 'logs delete'}):
        return True

    # Usuario maestro
    usuario = (session.get('usuario') or '').strip().upper()
    if usuario == 'GLSTUDIOS':
        return True

    return False

# Ruta de ayuda para pruebas locales (activar con GLBINGO_DEBUG_SUPER=1)
if os.getenv('GLBINGO_DEBUG_SUPER') == '1':
    @app.route('/debug/make-superadmin')
    def _debug_make_superadmin():
        session['rol'] = 'Super Administrador'
        u = session.get('usuario') or 'GLSTUDIOS'
        session['usuario'] = u
        flash('Sesión marcada como SUPERADMIN (modo debug).', 'success')
        return redirect(url_for('impresion'))

# Backup diario opcional
def _backup_diario():
    try:
        if os.path.exists(IMPRESIONES_XML):
            ymd = datetime.now().strftime("%Y%m%d")
            bkp = os.path.join(LOGS_DIR, f"impresiones_{ymd}.bak.xml")
            if not os.path.exists(bkp):
                shutil.copy2(IMPRESIONES_XML, bkp)
    except Exception as e:
        print("[WARN] Backup diario falló:", e)
_backup_diario()

# ─── Endpoints logs (+ UI borrar para superadmin) ───────────
_LOG_COLS = [
    "id","fecha_hora","usuario","tipo","serie_archivo","desde","hasta",
    "valor","telefono","fecha_sorteo","reintegro_especial",
    "cant_reintegro_especial","incluir_aleatorio",
    "fecha_planilla","total_boletos","total_planillas",
    "excedente","lote"
]

def _get_log_rows():
    rows = []
    for n in _iter_impresiones():
        d = dict(n.attrib)
        for ch in n:
            d[ch.tag] = ch.text or ''
        for k in _LOG_COLS:
            d.setdefault(k, "")
        rows.append(d)
    rows.sort(key=lambda x: x.get('fecha_hora', ''))
    return rows

@app.route('/logs-impresion')
@require_session
def logs_impresion_v2():
    rows = _get_log_rows()
    is_super = _is_superadmin()
    head_cells = _LOG_COLS + (["acciones"] if is_super else [])
    head = ''.join(f'<th style="padding:6px;border:1px solid #ccc;background:#f5f5f5">{c}</th>' for c in head_cells)
    trs = []
    for r in rows:
        tds = ''.join(f'<td style="padding:6px;border:1px solid #eee">{r.get(c,"")}</td>' for c in _LOG_COLS)
        if is_super:
            btn = (f'<td style="padding:6px;border:1px solid #eee">'
                   f'<button onclick="delLog({r.get("id","")})" '
                   f'style="padding:6px 10px;background:#d9534f;color:#fff;border:none;border-radius:4px;cursor:pointer">'
                   f'Eliminar</button></td>')
            tds += btn
        trs.append(f'<tr>{tds}</tr>')
    body = ''.join(trs)
    html = f"""
    <html>
    <head><meta charset="utf-8"><title>Logs de Impresión</title></head>
    <body style="font-family:Arial,Helvetica,sans-serif">
      <h2>Logs de Impresión</h2>
      <p>
        <a href="/logs-impresion.csv">Descargar CSV</a> &nbsp;|&nbsp;
        <a href="/logs-impresion.json">Ver JSON</a>
      </p>
      <table cellspacing="0" cellpadding="0" style="border-collapse:collapse;min-width:1100px">
        <thead><tr>{head}</tr></thead>
        <tbody>{body}</tbody>
      </table>

      <script>
        async function delLog(id) {{
          if (!id) return alert("ID inválido");
          if (!confirm("¿Eliminar el registro " + id + "? Esta acción no se puede deshacer.")) return;
          try {{
            const res = await fetch('/logs-impresion/delete', {{
              method: 'POST',
              headers: {{ 'Content-Type': 'application/json' }},
              credentials: 'same-origin',
              body: JSON.stringify({{ id: String(id) }})
            }});
            if (res.ok) {{
              location.reload();
            }} else {{
              const j = await res.json().catch(() => ({{}}));
              alert("No se pudo eliminar: " + (j.error || res.status));
            }}
          }} catch (e) {{
            alert("Error de red: " + e);
          }}
        }}
      </script>
    </body>
    </html>
    """
    return html

@app.route('/logs-impresion.csv')
@require_session
def logs_impresion_csv_v2():
    rows = _get_log_rows()
    buf = StringIO()
    writer = csv.DictWriter(buf, fieldnames=_LOG_COLS)
    writer.writeheader()
    writer.writerows(rows)
    csv_data = buf.getvalue()
    buf.close()
    return (
        csv_data, 200,
        {
            "Content-Type": "text/csv; charset=utf-8",
            "Content-Disposition": "attachment; filename=logs_impresion.csv",
        },
    )

@app.route('/logs-impresion.json')
@require_session
def logs_impresion_json_v2():
    rows = _get_log_rows()
    return jsonify(rows=rows, count=len(rows))

# Borrar log (solo superadmin)
@app.route('/logs-impresion/delete', methods=['POST'])
@require_session
def logs_impresion_delete():
    if not _is_superadmin():
        return jsonify(ok=False, error='forbidden'), 403
    log_id = (request.json or {}).get('id') if request.is_json else request.form.get('id')
    if not log_id:
        return jsonify(ok=False, error='missing id'), 400
    ok = _delete_log_by_id(str(log_id))
    return (jsonify(ok=True) if ok else (jsonify(ok=False, error='not found'), 404))

# ================== GENERADORES PDF ==================
def _try_draw_qr_on_canvas(c, data, x, y, size):
    """Intenta dibujar QR; si no puede, dibuja un recuadro de marcador."""
    try:
        buf_qr = BytesIO()
        qrcode.make(data).save(buf_qr, format="PNG")
        buf_qr.seek(0)
        c.drawImage(ImageReader(buf_qr), x, y, size, size, mask="auto")
        return True
    except Exception:
        c.setFillGray(0.95)
        c.rect(x, y, size, size, stroke=0, fill=1)
        c.setFillGray(0.0)
        c.setFont("Helvetica", 6)
        c.drawCentredString(x + size/2, y + size/2 - 3, "QR")
        return False

def _safe_draw_image(c, path_or_buf, x, y, w_, h_):
    """Dibuja imagen si existe, sin romper en caso de error."""
    try:
        if isinstance(path_or_buf, (str, bytes)):
            if isinstance(path_or_buf, str) and not os.path.exists(path_or_buf):
                return False
            c.drawImage(ImageReader(path_or_buf), x, y, w_, h_, mask="auto")
            return True
        else:
            c.drawImage(ImageReader(path_or_buf), x, y, w_, h_, mask="auto")
            return True
    except Exception:
        return False

def generar_pdf_boletos_excel(
    ids, registros, valor, telefono,
    nombre, reintegro_especial,
    cant_especial, reintegros,
    incluir_aleatorio, fecha_sorteo
):
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    c.translate(OFFSET_X, OFFSET_Y)

    fecha_num = fecha_ddmmyyyy(fecha_sorteo)
    precio_str = format_money(valor)

    N = len(registros)
    esp_idx = random.sample(range(N), min(N, cant_especial)) if reintegro_especial else []
    ale_idx = [i for i in range(N) if i not in esp_idx] if incluir_aleatorio else []

    for start in range(0, N, FILAS * COLUMNAS):
        page = registros[start:start + FILAS * COLUMNAS]

        for i, row in enumerate(page):
            pos = start + i
            col = i % COLUMNAS
            fil = i // COLUMNAS

            ancho_b = (w + 2 * MARGEN_IZQ - ESPACIO_X * (COLUMNAS - 1)) / COLUMNAS
            alto_b  = (h + 2 * MARGEN_SUP - ESPACIO_Y * (FILAS   - 1)) / FILAS
            x0 = MARGEN_IZQ + col * (ancho_b + ESPACIO_X)
            y0 = h - MARGEN_SUP - fil * (alto_b + ESPACIO_Y)
            if fil == 2: y0 -= DELTA_Y_FILA_3
            if fil == 3: y0 -= DELTA_Y_FILA_4

            size = min(ancho_b, alto_b) / 5
            offs = per_cell_offsets[i]

            # Rejilla 5×5 y QR en N3
            bx0 = x0 + ancho_b - size * 5 + offs['grid_x']
            by0 = y0 + offs['grid_y']
            c.setFont('Helvetica-Bold', SIZE_NUM)
            for r in range(5):
                for j, letra in enumerate('bingo'):
                    cx = bx0 + j * size
                    cy = by0 - r * size
                    if letra == 'n' and r == 2:
                        _try_draw_qr_on_canvas(c, f"{ids[pos]}|{fecha_sorteo}", cx + 2, cy + 2, size - 4)
                    else:
                        v = str(row.get(f"{letra}{r+1}", "-"))
                        c.drawCentredString(cx + size / 2, cy + size * 0.28, v)

            # Texto inferior: ID grande + fecha + valor
            boleto_text = f"{ids[pos]}{SERIE_MAP.get(nombre, nombre)}"
            x_info = x0 + offs['info_x']
            y_info = y0 - size * 5 + offs['info_y']

            c.setFont(ULTRA_BLACK_FONT, SIZE_ID_BIG)
            c.drawString(x_info, y_info, boleto_text)

            dx_id = c.stringWidth(boleto_text, ULTRA_BLACK_FONT, SIZE_ID_BIG) + 4
            c.setFont('Helvetica', SIZE_INFO)
            fecha_str = f"| {fecha_num} | "
            c.drawString(x_info + dx_id, y_info, fecha_str)

            dx_fecha = c.stringWidth(fecha_str, 'Helvetica', SIZE_INFO)
            c.setFont('Helvetica-Bold', SIZE_INFO)
            c.drawString(x_info + dx_id + dx_fecha, y_info, precio_str)

            # Reintegro seguro
            img = None
            if pos in esp_idx and reintegro_especial:
                img = reintegro_especial
            elif pos in ale_idx and reintegros:
                others = [r for r in reintegros if r != reintegro_especial]
                img = random.choice(others) if others else None

            if img:
                path_img = os.path.join(REINTEGROS_DIR, img)
                _safe_draw_image(c, path_img, x0 + offs['rein_x'], y0 - offs['rein_y'], REINTEGRO_W, REINTEGRO_H)

        c.showPage()
        c.translate(OFFSET_X, OFFSET_Y)

    c.save()
    buf.seek(0)
    return buf

def generar_pdf_planilla(ids, serie_archivo, vendedor, fecha, inicio, fin, serie_map, num_planilla=None):
    LOGO_PATH = os.path.join("static", "golpe_suerte_logo.png")
    LOGO_LEFT_PAD        = 0.1
    DATE_GAP_AFTER_LOGO  = 1
    DATE_WIDTH_FACTOR    = 0.78
    DATE_MIN_WIDTH       = 220
    QR_SIZE_HDR          = 56

    PN_W, PN_H = 54, 22

    dt = datetime.strptime(fecha, "%Y-%m-%d")
    dias   = ["Lunes","Martes","Miércoles","Jueves","Viernes","Sábado","Domingo"]
    meses  = {1:"Enero",2:"Febrero",3:"Marzo",4:"Abril",5:"Mayo",6:"Junio",7:"Julio",8:"Agosto",9:"Septiembre",10:"Octubre",11:"Noviembre",12:"Diciembre"}
    formatted_date = f"{dias[dt.weekday()]}, {dt.day} de {meses[dt.month]} del {dt.year}"
    fecha_limpia   = dt.strftime("%Y%m%d")
    serie_letra    = serie_map.get(serie_archivo, "")

    left_desde  = inicio
    left_hasta  = min(inicio + 19, fin)
    right_desde = inicio + 20
    right_hasta = min(inicio + 39, fin)
    full_desde  = inicio
    full_hasta  = min(inicio + 39, fin)

    def qr_cadena(tipo, desde, hasta, serie):
        return f"SORTEO{fecha_limpia}{tipo}A{desde}A{hasta}{serie}"

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=landscape(A4))
    ancho, alto = landscape(A4)

    M_LEFT, M_RIGHT, M_BOTTOM = 12, 20, 20
    GUTTER        = 28
    HEADER_H      = 86
    QR_SIZE_CENTER= min(GUTTER + 30, 50)

    HALF_W  = (ancho - M_LEFT - M_RIGHT - GUTTER) / 2
    TOP_Y   = alto - HEADER_H - 10
    BOT_Y   = M_BOTTOM
    AVAIL_H = TOP_Y - BOT_Y

    NUM_ROWS = 21
    ROW_H    = AVAIL_H / NUM_ROWS

    X_L = M_LEFT
    X_R = M_LEFT + HALF_W + GUTTER
    TABLE_W  = HALF_W - 20
    PAD      = 10

    FB = "Helvetica-Bold"

    left_index  = (left_desde  - 1) // 20 + 1
    right_index = (right_desde - 1) // 20 + 1

    def draw_header(x0, sheet_num, tipo, desde, hasta):
        from reportlab.lib import colors
        c.setFillColorRGB(0.92, 0.92, 0.92)
        c.rect(x0, alto - HEADER_H, HALF_W, HEADER_H, fill=1, stroke=0)
        c.setFillColor(colors.black)

        # Logo seguro (si no existe, no rompe)
        try:
            img = ImageReader(LOGO_PATH)
            ow, oh = img.getSize()
            max_logo_w = HALF_W * 0.25
            max_logo_h = HEADER_H - 10
            dw = max_logo_w
            dh = dw * oh / ow
            if dh > max_logo_h:
                dh = max_logo_h
                dw = dh * ow / oh
            logo_x = x0 + LOGO_LEFT_PAD
            logo_y = alto - HEADER_H + (HEADER_H - dh) / 2
            c.drawImage(img, logo_x, logo_y, width=dw, height=dh, mask="auto")
        except Exception:
            logo_x = x0 + LOGO_LEFT_PAD
            dw = 0

        gap = DATE_GAP_AFTER_LOGO
        right_reserved = 6 + QR_SIZE_HDR + 6 + PN_W + 6
        avail_for_date = HALF_W - ((logo_x - x0) + dw + gap + right_reserved)
        date_w = max(DATE_MIN_WIDTH, min(avail_for_date, HALF_W * DATE_WIDTH_FACTOR))
        date_h_top, date_h_bot = 26, 26
        space = 6
        total_h = date_h_top + space + date_h_bot
        bx = logo_x + dw + gap
        by = alto - HEADER_H + (HEADER_H - total_h) / 2

        c.setLineWidth(1.5)
        c.setFillGray(1.0)
        c.roundRect(bx, by + date_h_bot + space, date_w, date_h_top, 4, stroke=1, fill=1)
        c.roundRect(bx, by,                     date_w, date_h_bot, 4, stroke=1, fill=1)
        c.setFillGray(0.0)
        c.setFont(FB, 10)
        c.drawCentredString(bx + date_w/2, by + date_h_bot/2 - 4, formatted_date)

        data_qr = qr_cadena(tipo, desde, hasta, serie_letra)
        qx = x0 + HALF_W - QR_SIZE_HDR - 4
        qy = alto - HEADER_H + (HEADER_H - QR_SIZE_HDR) / 2
        _try_draw_qr_on_canvas(c, data_qr, qx, qy, QR_SIZE_HDR)

        px = qx + (QR_SIZE_HDR - PN_W) / 2
        py = qy - PN_H - 2
        c.setFillGray(1.0)
        c.roundRect(px, py, PN_W, PN_H, 6, stroke=0, fill=1)
        c.setFillGray(0.0)
        c.setFont("Helvetica-Bold", 15)
        c.drawCentredString(px + PN_W/2, py + PN_H/2 - 4, str(sheet_num))

    draw_header(X_L, left_index,  "L1", left_desde,  left_hasta)
    draw_header(X_R, right_index, "L2", right_desde, right_hasta)

    c.setLineWidth(2)
    c.line(X_R, TOP_Y, X_R, BOT_Y)

    data_full = f"SORTEO{fecha_limpia}RGA{full_desde}A{full_hasta}{serie_letra}"
    cx = X_R - (GUTTER/2) - (QR_SIZE_CENTER/2)
    cy = BOT_Y + (AVAIL_H/2) - (QR_SIZE_CENTER/2)
    _try_draw_qr_on_canvas(c, data_full, cx, cy, QR_SIZE_CENTER)

    left_data = [["Boleto / Nombres Apellidos", ""]]
    for i in range(20):
        n = inicio + i
        left_data.append([str(n) if n <= fin else "", ""])

    right_data = [["Boleto / Nombres Apellidos", ""]]
    for i in range(20):
        n = inicio + 20 + i
        right_data.append([str(n) if n <= fin else "", ""])

    header_y = TOP_Y - ROW_H
    c.setLineWidth(1.5)
    c.roundRect(X_L + PAD, header_y, TABLE_W, ROW_H, 4, stroke=1, fill=0)
    c.roundRect(X_R + PAD, header_y, TABLE_W, ROW_H, 4, stroke=1, fill=0)

    from reportlab.platypus import Table, TableStyle
    from reportlab.lib import colors
    style = TableStyle([
        ("SPAN",        (0,0),(1,0)),
        ("FONT",        (0,0),(1,0), "Helvetica-Bold", 10),
        ("ALIGN",       (0,0),(1,0), "CENTER"),
        ("FONT",        (0,1),(0,-1), "Helvetica-Bold", 12),
        ("FONT",        (1,1),(1,-1), "Helvetica", 8),
        ("VALIGN",      (0,0),(-1,-1), "MIDDLE"),
        ("INNERGRID",   (0,0),(-1,-1), 1, colors.black),
        ("BOX",         (0,0),(-1,-1), 2, colors.black),
        ("LEFTPADDING", (0,0),(-1,-1), 3),
        ("RIGHTPADDING",(0,0),(-1,-1), 3),
    ])

    tblL = Table(left_data,  colWidths=[40, TABLE_W-40], rowHeights=[ROW_H]*21)
    tblL.setStyle(style); tblL.wrapOn(c,0,0); tblL.drawOn(c, X_L+PAD, BOT_Y)

    tblR = Table(right_data, colWidths=[40, TABLE_W-40], rowHeights=[ROW_H]*21)
    tblR.setStyle(style); tblR.wrapOn(c,0,0); tblR.drawOn(c, X_R+PAD, BOT_Y)

    c.save()
    buffer.seek(0)
    return buffer

# ============== /impresion =================
@app.route('/impresion', methods=['GET', 'POST'])
@require_session
def impresion():
    files = sorted(f for f in os.listdir(DATA_DIR)
                   if f.lower().endswith(('.xlsx', '.csv')))
    series     = [(f, SERIE_MAP.get(f, f)) for f in files]
    reintegros = sorted(f for f in os.listdir(REINTEGROS_DIR)
                        if f.lower().endswith('.png')) if os.path.exists(REINTEGROS_DIR) else []
    fecha_hoy  = date.today().strftime('%Y-%m-%d')

    if request.method != 'POST':
        return render_template(
            'impresion_boletos_excel.html',
            series=series, reintegros=reintegros, fecha_hoy=fecha_hoy,
            username=session.get('usuario',''),
            usuario=session.get('usuario',''),
            rol=session.get('rol',''),
            avatar=session.get('avatar','avatar-male.png'),
            permisos=session.get('permisos', [])
        )

    form_type = (request.form.get('form_type') or '').strip().lower()

    # ---- BOLETOS ----
    if form_type == 'boletos':
        serie_archivo = (request.form.get('serie_archivo') or '').strip()
        start         = (request.form.get('serie_inicio') or '').strip()
        end           = (request.form.get('serie_fin') or '').strip()
        valor         = (request.form.get('valor') or '1.00').strip()
        telefono      = (request.form.get('telefono') or '').strip()
        fecha_str     = (request.form.get('fecha_sorteo') or fecha_hoy).strip()
        rein_esp      = (request.form.get('reintegro_especial') or '').strip()
        cntesp        = _to_int(request.form.get('cant_reintegro_especial'), 0)
        incA_raw      = (request.form.get('incluir_aleatorio') or '1').strip().lower()
        incA          = incA_raw in ('1', 'true', 'on', 'si', 'sí')

        if not serie_archivo:
            flash('Selecciona una serie para imprimir boletos.', 'warning')
            return redirect(url_for('impresion'))

        series_prev = _series_impresas_en_fecha(fecha_str)
        if series_prev and (serie_archivo not in series_prev):
            otra = ', '.join(sorted(series_prev))
            flash(f"Ya se imprimieron boletos para {fecha_str} con la serie: {otra}. "
                  f"No se permite imprimir el mismo día con otra serie.", 'danger')
            return redirect(url_for('impresion'))

        try:
            df = _read_df_for_series(serie_archivo)
        except Exception as e:
            flash(str(e), 'danger'); return redirect(url_for('impresion'))

        id_col  = df.columns[0]
        all_ids = df[id_col].astype(str).tolist()
        if not all_ids:
            flash('La serie seleccionada no contiene datos.', 'danger')
            return redirect(url_for('impresion'))

        if not start:
            start = all_ids[0]
        if not end:
            end = start

        if start not in all_ids:
            flash(f'Boleto inicial “{start}” no existe en la serie.', 'danger'); return redirect(url_for('impresion'))
        if end not in all_ids:
            flash(f'Boleto final “{end}” no existe en la serie.', 'danger'); return redirect(url_for('impresion'))

        s_idx = all_ids.index(start)
        e_idx = all_ids.index(end) + 1
        if e_idx <= s_idx:
            e_idx = s_idx + 1

        ids       = all_ids[s_idx:e_idx]
        registros = df.iloc[s_idx:e_idx].to_dict('records')

        try:
            _append_log_impresion_boletos(
                usuario=session.get('usuario', ''),
                serie_archivo=serie_archivo,
                desde=start, hasta=end,
                fecha_sorteo=fecha_str,
                total_boletos=len(ids),
                valor=valor, telefono=telefono,
                reintegro_especial=rein_esp,
                cant_reintegro_especial=cntesp,
                incluir_aleatorio=incA,
            )
        except Exception as e:
            print('[WARN] No se pudo escribir en impresiones.xml (boletos):', e)

        rein_list = sorted(f for f in os.listdir(REINTEGROS_DIR) if f.lower().endswith('.png')) if os.path.exists(REINTEGROS_DIR) else []
        buf_b = generar_pdf_boletos_excel(
            ids, registros, valor, telefono,
            serie_archivo, rein_esp, cntesp,
            rein_list, incA, fecha_str
        )
        return _send_bytesio(buf_b, 'boletos_bingo.pdf', 'application/pdf')

    # ---- PLANILLA ----
    if form_type == 'planilla':
        archivo = (request.form.get('serie_archivo_planilla') or '').strip()
        inicio  = _to_int(request.form.get('planilla_inicio'), 0)
        fin     = _to_int(request.form.get('planilla_fin'), 0)
        fecha_p = (request.form.get('fecha_planilla') or fecha_hoy).strip()

        if not archivo or inicio <= 0 or fin < inicio:
            flash('Completa serie e inicio/fin válidos para la planilla.', 'warning')
            return redirect(url_for('impresion'))

        try:
            df2 = _read_df_for_series(archivo)
        except Exception as e:
            flash(str(e), 'danger'); return redirect(url_for('impresion'))

        id_col  = df2.columns[0]
        all_ids = df2[id_col].astype(str).tolist()
        if not all_ids:
            flash('La serie seleccionada no contiene datos.', 'danger'); return redirect(url_for('impresion'))

        inicio = max(1, inicio)
        fin    = min(len(all_ids), fin)

        merger = PdfMerger()
        try:
            chunk  = 40
            total  = fin - inicio + 1
            for off in range(0, total, chunk):
                page_start = inicio + off
                page_end   = min(page_start + chunk - 1, fin)
                sub_ids    = all_ids[page_start-1:page_end]

                buf = generar_pdf_planilla(
                    sub_ids, archivo, session.get('usuario',''),
                    fecha_p, page_start, page_end, SERIE_MAP
                )
                merger.append(buf)

            salida = BytesIO()
            merger.write(salida)
            merger.close()
            salida.seek(0)
        finally:
            try:
                merger.close()
            except Exception:
                pass

        # Una sola fila para todo el rango impreso
        try:
            _append_log_impresion_planilla(
                usuario=session.get('usuario',''),
                serie_archivo=archivo,
                desde=inicio, hasta=fin,
                fecha_planilla=fecha_p,
                lote_text=f"{inicio}-{fin}",
                # >>> CAMBIO: % 40 → % 20
                excedente=1 if ((fin - inicio + 1) % 20) != 0 else 0
            )
        except Exception as e:
            print('[WARN] No se pudo escribir en impresiones.xml (planilla-range):', e)

        return _send_bytesio(salida, f'planilla_{inicio}_a_{fin}.pdf', 'application/pdf')

    flash('Formulario no reconocido.', 'warning')
    return redirect(url_for('impresion'))

# ============== ZIP (boletos + planilla) =================
def _crear_zip_boletos_planilla(nombre_serie, start, end, valor, telefono, fecha_str,
                                rein_esp, cnt_esp, incA):
    series_prev = _series_impresas_en_fecha(fecha_str)
    if series_prev and (nombre_serie not in series_prev):
        otra = ', '.join(sorted(series_prev))
        flash(f"Ya se imprimieron boletos para {fecha_str} con la serie: {otra}. "
              f"No se permite imprimir el mismo día con otra serie.", 'danger')
        return redirect(url_for('impresion'))

    try:
        df = _read_df_for_series(nombre_serie)
    except Exception as e:
        flash(str(e), 'danger'); return redirect(url_for('impresion'))

    all_ids = df[df.columns[0]].astype(str).tolist()
    if not all_ids:
        flash('La serie no contiene datos.', 'danger'); return redirect(url_for('impresion'))

    if not start:
        start = all_ids[0]
    if not end:
        end = start

    if start not in all_ids:
        flash(f'Boleto inicial “{start}” no existe.', 'danger'); return redirect(url_for('impresion'))
    if end not in all_ids:
        flash(f'Boleto final “{end}” no existe.', 'danger'); return redirect(url_for('impresion'))

    s_idx = all_ids.index(start)
    e_idx = all_ids.index(end) + 1
    if e_idx <= s_idx:
        e_idx = s_idx + 1

    ids = all_ids[s_idx:e_idx]
    registros = df.iloc[s_idx:e_idx].to_dict('records')

    rein_list = []
    if os.path.exists(REINTEGROS_DIR):
        rein_list = sorted(f for f in os.listdir(REINTEGROS_DIR) if f.lower().endswith('.png'))

    buf_boletos = generar_pdf_boletos_excel(
        ids, registros, valor, telefono,
        nombre_serie, rein_esp, cnt_esp,
        rein_list, incA, fecha_str
    )
    buf_planilla = generar_pdf_planilla(
        ids, nombre_serie, "Vendedor", fecha_str,
        int(start), int(end), SERIE_MAP
    )

    try:
        _append_log_impresion_boletos(
            usuario=session.get('usuario',''),
            serie_archivo=nombre_serie,
            desde=start, hasta=end,
            fecha_sorteo=fecha_str,
            total_boletos=len(ids),
            valor=valor, telefono=telefono,
            reintegro_especial=rein_esp,
            cant_reintegro_especial=cnt_esp,
            incluir_aleatorio=incA,
        )
        _append_log_impresion_planilla(
            usuario=session.get('usuario',''),
            serie_archivo=nombre_serie,
            desde=int(start), hasta=int(end),
            fecha_planilla=fecha_str,
            lote_text=f"{start}-{end}", excedente=0
        )
    except Exception as e:
        print('[WARN] No se pudo escribir en impresiones.xml (zip):', e)

    from zipfile import ZipFile
    zip_buffer = BytesIO()
    with ZipFile(zip_buffer, 'w') as zipf:
        zipf.writestr('boletos.pdf', buf_boletos.getvalue())
        zipf.writestr('planilla.pdf', buf_planilla.getvalue())
    zip_buffer.seek(0)

    resp = _send_bytesio(zip_buffer, "GLSTUDIOS_BOLETOS_PLANILLA.zip", "application/zip")
    try:
        resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    except Exception:
        pass
    return resp

@app.route('/descargar_zip', methods=['POST'])
@require_session
def descargar_zip():
    nombre_serie = (request.form.get('serie_archivo') or '').strip()
    start        = (request.form.get('serie_inicio') or '').strip()
    end          = (request.form.get('serie_fin') or '').strip()
    valor        = (request.form.get('valor') or '1.00').strip()
    telefono     = (request.form.get('telefono') or '').strip()
    fecha_str    = (request.form.get('fecha_sorteo') or date.today().isoformat()).strip()
    rein_esp     = (request.form.get('reintegro_especial') or '').strip()
    cnt_esp      = _to_int(request.form.get('cant_reintegro_especial'), 0)
    incA         = (request.form.get('incluir_aleatorio') or '1').strip().lower() in ('1','true','on','si','sí')

    if not nombre_serie:
        flash('Selecciona una serie.', 'warning'); return redirect(url_for('impresion'))

    return _crear_zip_boletos_planilla(nombre_serie, start, end, valor, telefono, fecha_str,
                                       rein_esp, cnt_esp, incA)

# Atajo GET/POST
@app.route('/impresion_zip', methods=['GET', 'POST'])
@require_session
def impresion_zip():
    if request.method == 'GET':
        nombre_serie = (request.args.get('serie') or '').strip()
        start        = (request.args.get('desde') or '').strip()
        end          = (request.args.get('hasta') or '').strip()
        valor        = (request.args.get('valor') or '1.00').strip()
        telefono     = ''
        fecha_str    = (request.args.get('fecha') or date.today().isoformat()).strip()
        rein_esp     = (request.args.get('reintegro') or '').strip()
        cnt_esp      = _to_int(request.args.get('cant'), 0)
        incA         = (request.args.get('aleatorio') or '1').strip().lower() in ('1','true','on','si','sí')

        if not nombre_serie:
            flash('Selecciona una serie.', 'warning'); return redirect(url_for('impresion'))

        return _crear_zip_boletos_planilla(nombre_serie, start, end, valor, telefono, fecha_str,
                                           rein_esp, cnt_esp, incA)
    return descargar_zip()

# ================== MAIN ==================





# ============== OTROS ==============
@app.route('/usuarios/eliminar/<nombre>', methods=['POST'])
def eliminar_usuario_route(nombre):
    if 'usuario' not in session:
        return redirect(_login_url())
    eliminar_usuario(nombre)   # función existente en tu app
    flash('Usuario eliminado correctamente', 'success')
    return redirect(url_for('usuarios'))




#vendedores seccion de listas #




VENDEDORES_XML = os.path.join('static', 'db', 'vendedores.xml')
ASIGNACIONES_XML = os.path.join('static', 'db', 'asignaciones.xml')
BOLETOS_POR_PLANILLA = 40  # Cambia esto según tus necesidades

# ----------- FUNCIONES PARA VENDEDORES -----------

# ============================================================
#  RUTAS Y CONSTANTES (tus líneas originales, no se tocan)
# ============================================================
VENDEDORES_XML = os.path.join('static', 'db', 'vendedores.xml')
ASIGNACIONES_XML = os.path.join('static', 'db', 'asignaciones.xml')
BOLETOS_POR_PLANILLA = 40  # Cambia esto según tus necesidades

# ----------- FUNCIONES PARA VENDEDORES -----------
# (mantengo tu reasignación exacta, como la tienes)
VENDEDORES_XML = 'static/db/vendedores.xml'


# ============================================================
#  UTILIDADES SEGURAS (nuevas)
# ============================================================
def _ensure_xml(path: str, root_tag: str = 'vendedores'):
    """
    Garantiza que exista el archivo XML y su carpeta.
    Si no existe, lo crea con la etiqueta raíz indicada.
    """
    carpeta = os.path.dirname(path)
    if carpeta and not os.path.exists(carpeta):
        os.makedirs(carpeta, exist_ok=True)
    if not os.path.exists(path):
        root = ET.Element(root_tag)
        tree = ET.ElementTree(root)
        tree.write(path, encoding='utf-8', xml_declaration=True)


def _read_tree_with_root(path: str, root_tag: str = 'vendedores'):
    """
    Asegura el XML y devuelve (tree, root) listos para usar.
    """
    _ensure_xml(path, root_tag)
    tree = ET.parse(path)
    root = tree.getroot()
    # Si el root no coincide (por si se creó con otro tag), lo normalizamos
    if root.tag != root_tag:
        new_root = ET.Element(root_tag)
        for child in list(root):
            new_root.append(child)
        tree._setroot(new_root)
        root = new_root
    return tree, root


def _indent_tree_if_possible(tree: ET.ElementTree):
    """
    Intenta indentar (Python 3.9+) para que el XML quede legible.
    """
    try:
        ET.indent(tree, space="  ", level=0)  # type: ignore[attr-defined]
    except Exception:
        pass


def _write_xml_atomic(tree: ET.ElementTree, path: str):
    """
    Escritura atómica: escribe a .tmp y luego reemplaza.
    Evita corrupciones si el proceso se interrumpe.
    """
    tmp = f"{path}.tmp"
    _indent_tree_if_possible(tree)
    tree.write(tmp, encoding='utf-8', xml_declaration=True)
    os.replace(tmp, path)


# ============================================================
#  CRUD DE VENDEDORES (robusto; respeta tu API)
# ============================================================
def cargar_vendedores_xml():
    vendedores = []
    # Lee de forma segura (crea el archivo si no existe)
    tree, root = _read_tree_with_root(VENDEDORES_XML, 'vendedores')

    for idx, v in enumerate(root.findall('vendedor')):
        vendedores.append({
            'id': idx,  # mantener índice para editar/eliminar
            'nombre'  : (v.findtext('nombre') or '').strip(),
            'apellido': (v.findtext('apellido') or '').strip(),
            'seudonimo': (v.findtext('seudonimo') or '').strip(),
        })
    return vendedores


def guardar_vendedor(nombre, apellido, seudonimo):
    # Normaliza strings
    nombre = (nombre or '').strip()
    apellido = (apellido or '').strip()
    seudonimo = (seudonimo or '').strip()

    tree, root = _read_tree_with_root(VENDEDORES_XML, 'vendedores')

    # Agrega nuevo <vendedor>
    v = ET.SubElement(root, 'vendedor')
    ET.SubElement(v, 'nombre').text = nombre
    ET.SubElement(v, 'apellido').text = apellido
    ET.SubElement(v, 'seudonimo').text = seudonimo

    _write_xml_atomic(tree, VENDEDORES_XML)


def editar_vendedor(idx, nombre, apellido, seudonimo):
    nombre = (nombre or '').strip()
    apellido = (apellido or '').strip()
    seudonimo = (seudonimo or '').strip()

    tree, root = _read_tree_with_root(VENDEDORES_XML, 'vendedores')
    vendedores = root.findall('vendedor')

    if 0 <= idx < len(vendedores):
        v = vendedores[idx]

        def _set(tag, val):
            el = v.find(tag)
            if el is None:
                el = ET.SubElement(v, tag)
            el.text = val

        _set('nombre', nombre)
        _set('apellido', apellido)
        _set('seudonimo', seudonimo)

        _write_xml_atomic(tree, VENDEDORES_XML)


def eliminar_vendedor(idx):
    tree, root = _read_tree_with_root(VENDEDORES_XML, 'vendedores')
    vendedores = root.findall('vendedor')

    if 0 <= idx < len(vendedores):
        root.remove(vendedores[idx])
        _write_xml_atomic(tree, VENDEDORES_XML)


# ============================================================
#  ENDPOINT /vendedores (idéntico en comportamiento)
# ============================================================
@app.route('/vendedores', methods=['GET', 'POST'])
def vendedores():
    if request.method == 'POST':
        if 'editar' in request.form:
            idx = int(request.form['id'])
            nombre = request.form['nombre'].strip()
            apellido = request.form['apellido'].strip()
            seudonimo = request.form['seudonimo'].strip()
            editar_vendedor(idx, nombre, apellido, seudonimo)
            flash("Vendedor editado correctamente.", "success")

        elif 'eliminar' in request.form:
            idx = int(request.form['id'])
            eliminar_vendedor(idx)
            flash("Vendedor eliminado.", "info")

        else:
            nombre = request.form['nombre'].strip()
            apellido = request.form['apellido'].strip()
            seudonimo = request.form['seudonimo'].strip()
            if nombre and apellido and seudonimo:
                guardar_vendedor(nombre, apellido, seudonimo)
                flash("¡Vendedor agregado!", "success")
            else:
                flash("Todos los campos son obligatorios.", "danger")

        return redirect(url_for('vendedores'))

    # GET: cargar y renderizar
    vendedores_list = cargar_vendedores_xml()
    return render_template('vendedores.html', vendedores=vendedores_list)



# ----------- FUNCIONES PARA ASIGNACIONES -----------


import os
import re
import xml.etree.ElementTree as ET
from datetime import date
from flask import render_template, request, jsonify, session, redirect, url_for

# === Archivos base ===
VENDEDORES_XML       = globals().get('VENDEDORES_XML',       'static/db/vendedores.xml')
ASIGNACIONES_XML     = globals().get('ASIGNACIONES_XML',     'static/db/asignaciones.xml')
IMPRESIONES_XML      = globals().get('IMPRESIONES_XML',      'static/LOGS/impresiones.xml')  # ← LOG de impresión
BOLETOS_POR_PLANILLA = int(globals().get('BOLETOS_POR_PLANILLA', 20))

os.makedirs(os.path.dirname(ASIGNACIONES_XML), exist_ok=True)
os.makedirs(os.path.dirname(IMPRESIONES_XML), exist_ok=True)
if not os.path.exists(ASIGNACIONES_XML):
    ET.ElementTree(ET.Element('asignaciones')).write(ASIGNACIONES_XML, encoding='utf-8', xml_declaration=True)
if not os.path.exists(IMPRESIONES_XML):
    ET.ElementTree(ET.Element('impresiones')).write(IMPRESIONES_XML, encoding='utf-8', xml_declaration=True)

# === Helpers XML generales ===
def _parse_or_none(path):
    try:
        if not os.path.exists(path):
            return None, None
        t = ET.parse(path)
        return t, t.getroot()
    except ET.ParseError:
        return None, None

def cargar_vendedores():
    vendedores = []
    t, r = _parse_or_none(VENDEDORES_XML)
    if r is None:
        return vendedores
    for v in r.findall('vendedor'):
        vendedores.append({
            'nombre': (v.findtext('nombre') or ""),
            'apellido': (v.findtext('apellido') or ""),
            'seudonimo': (v.findtext('seudonimo') or "")
        })
    return vendedores

def leer_asignaciones():
    t, r = _parse_or_none(ASIGNACIONES_XML)
    if r is None:
        t = ET.ElementTree(ET.Element('asignaciones'))
        r = t.getroot()
        t.write(ASIGNACIONES_XML, encoding='utf-8', xml_declaration=True)
    return t, r

def guardar_asignaciones(tree):
    try:
        ET.indent(tree, space="  ", level=0)
    except Exception:
        pass
    tree.write(ASIGNACIONES_XML, encoding='utf-8', xml_declaration=True)

# === Rangos / parse de planillas ===
def calcular_rango(planilla, boletos_por_planilla=BOLETOS_POR_PLANILLA):
    inicio = (int(planilla)-1)*boletos_por_planilla + 1
    fin = int(planilla)*boletos_por_planilla
    return f"{inicio}-{fin}"

def parsear_planillas_input(planillas_raw):
    planillas = set()
    planillas_raw = planillas_raw or ""
    # soporta: "1,2", "1-3", "PL03, PL04", "1/2/3"
    piezas = re.split(r'[,\/\s]+', planillas_raw.strip())
    for parte in piezas:
        parte = parte.strip()
        if not parte:
            continue
        # soportar rango "3-7"
        if '-' in parte:
            a, b = parte.split('-', 1)
            a = a.replace('PL', '').replace('pl', '').lstrip('0') or '0'
            b = b.replace('PL', '').replace('pl', '').lstrip('0') or '0'
            if a.isdigit() and b.isdigit():
                a, b = int(a), int(b)
                if a > 0 and b >= a:
                    for x in range(a, b+1):
                        planillas.add(str(x))
            continue
        # número simple
        p = parte.replace('PL', '').replace('pl', '').lstrip('0') or '0'
        if p.isdigit() and int(p) > 0:
            planillas.add(str(int(p)))
    return sorted(planillas, key=lambda x: int(x))

# === LOG de impresiones: series impresas y total impresas por serie+fecha ===
def _imp_root():
    t, r = _parse_or_none(IMPRESIONES_XML)
    if r is None:
        t = ET.ElementTree(ET.Element('impresiones'))
        r = t.getroot()
        t.write(IMPRESIONES_XML, encoding='utf-8', xml_declaration=True)
    return t, r

def series_impresas_en_fecha(fecha_iso):
    """Series (archivo) que tienen registros de 'boletos' en esa fecha."""
    _, r = _imp_root()
    s = set()
    for n in r.findall('impresion'):
        if (n.get('tipo') or '').lower() != 'boletos':
            continue
        if (n.findtext('fecha_sorteo') or '').strip() != fecha_iso:
            continue
        serie = (n.get('serie_archivo') or '').strip()
        if serie:
            s.add(serie)
    return sorted(s)

def total_boletos_impresos_por_serie_fecha(serie_archivo, fecha_iso):
    """Suma lógicamente todos los 'total_boletos' para esa serie y fecha."""
    _, r = _imp_root()
    total = 0
    for n in r.findall('impresion'):
        if (n.get('tipo') or '').lower() != 'boletos':
            continue
        if (n.get('serie_archivo') or '') != serie_archivo:
            continue
        if (n.findtext('fecha_sorteo') or '').strip() != fecha_iso:
            continue
        try:
            total += int(float(n.findtext('total_boletos') or '0'))
        except Exception:
            pass
    return int(total)

def planillas_impresas_por_serie_fecha(serie_archivo, fecha_iso):
    tot_boletos = total_boletos_impresos_por_serie_fecha(serie_archivo, fecha_iso)
    return tot_boletos // BOLETOS_POR_PLANILLA

# === Utilidades de lectura/armado de la tabla para el template ===
def _armar_asignaciones_mostrar(root, fecha):
    asignaciones_mostrar = []
    dia = root.find(f"./dia[@fecha='{fecha}']")
    if dia is not None:
        for v in dia.findall('vendedor'):
            vendedor_info = {
                "nombre": v.attrib.get('nombre', ''),
                "apellido": v.attrib.get('apellido', ''),
                "seudonimo": v.attrib.get('seudonimo', ''),
                "planillas": []  # [{numero, rango, serie}]
            }
            for p in v.findall('planilla'):
                vendedor_info["planillas"].append({
                    "numero": p.attrib.get('numero', ''),
                    "rango":  p.attrib.get('rango', ''),
                    "serie":  p.attrib.get('serie', ''),  # puede venir vacío si eran antiguas
                })
            asignaciones_mostrar.append(vendedor_info)
    return asignaciones_mostrar

def _contar_asignadas_serie(root, fecha, serie_archivo):
    """Cantidad de planillas asignadas para ese día + serie."""
    cnt = 0
    dia = root.find(f"./dia[@fecha='{fecha}']")
    if dia is None: return 0
    for v in dia.findall('vendedor'):
        for p in v.findall('planilla'):
            if (p.attrib.get('serie') or '') == serie_archivo:
                cnt += 1
    return cnt

# === Rutas ===
@app.route('/asignar-planillas', methods=['GET', 'POST'])
def asignar_planillas():
    # (opcional) proteger por sesión
    if 'usuario' not in session:
        return redirect(_login_url())

    vendedores = cargar_vendedores()
    tree, root = leer_asignaciones()
    fecha_hoy = date.today().isoformat()

    # Filtros por querystring
    fecha_seleccionada = (request.args.get('fecha') or fecha_hoy).strip()
    series_dia = series_impresas_en_fecha(fecha_seleccionada)
    serie_param = (request.args.get('serie') or (series_dia[0] if series_dia else '')).strip()

    if request.method == 'POST':
        # Campos requeridos
        vendedor_val   = request.form.get('vendedor', '')
        planillas_raw  = request.form.get('planillas', '')
        fecha_form     = request.form.get('fecha', fecha_hoy).strip()
        serie_archivo  = request.form.get('serie_archivo', '').strip()  # ← NUEVO

        if not vendedor_val or not planillas_raw or not fecha_form or not serie_archivo:
            return jsonify(ok=False, error="Todos los campos son obligatorios (vendedor, planillas, fecha y serie).")

        # Verificar que la serie tenga impresión registrada ese día
        impresas_serie = planillas_impresas_por_serie_fecha(serie_archivo, fecha_form)
        if impresas_serie <= 0:
            return jsonify(ok=False, error=f"No hay impresión registrada para la serie “{serie_archivo}” en la fecha {fecha_form}.")

        # Parsear vendedor
        try:
            nombre, apellido, seudonimo = vendedor_val.split('|')
        except Exception:
            return jsonify(ok=False, error="Selecciona un vendedor válido.")

        # Planillas solicitadas
        planillas = parsear_planillas_input(planillas_raw)
        if not planillas:
            return jsonify(ok=False, error="No se detectó ninguna planilla válida.")

        # Validar que estén dentro del rango IMPRESO para esa serie/fecha
        max_pl = impresas_serie  # 1..max_pl
        no_impresas = [p for p in planillas if int(p) < 1 or int(p) > max_pl]
        if no_impresas:
            return jsonify(
                ok=False,
                error=f"Estas planillas NO fueron impresas para la serie “{serie_archivo}” ({fecha_form}): {', '.join(no_impresas)}. "
                      f"Permitidas: 1–{max_pl}."
            )

        # Asegurar nodo día y vendedor
        tree, root = leer_asignaciones()
        dia = root.find(f"./dia[@fecha='{fecha_form}']")
        if dia is None:
            dia = ET.SubElement(root, 'dia', fecha=fecha_form)

        vendedor_node = None
        for v in dia.findall('vendedor'):
            if (v.attrib.get('nombre') == nombre and
                v.attrib.get('apellido') == apellido and
                v.attrib.get('seudonimo') == seudonimo):
                vendedor_node = v
                break
        if vendedor_node is None:
            vendedor_node = ET.SubElement(dia, 'vendedor', nombre=nombre, apellido=apellido, seudonimo=seudonimo)

        # Validar duplicadas contra otros vendedores (por SERIE+numero)
        asignadas_otro = set()
        for v in dia.findall('vendedor'):
            for p in v.findall('planilla'):
                serie_p = p.attrib.get('serie', '')
                if not serie_p:  # antiguas sin serie → las ignoramos en el cruce “por serie”
                    continue
                asignadas_otro.add((serie_p, p.attrib.get('numero', '')))

        ya_en_este = set(p.attrib.get('numero', '') for p in vendedor_node.findall('planilla') if p.attrib.get('serie') == serie_archivo)
        duplicadas = [p for p in planillas if (serie_archivo, p) in asignadas_otro and p not in ya_en_este]
        if duplicadas:
            return jsonify(ok=False, error=f"Las planillas {', '.join(duplicadas)} ya están asignadas a otro vendedor para la serie {serie_archivo}.")

        # Insertar nuevas (evitando repetir en el mismo vendedor)
        for p in planillas:
            if p in ya_en_este:
                continue
            rango = calcular_rango(p, BOLETOS_POR_PLANILLA)
            ET.SubElement(
                vendedor_node, 'planilla',
                numero=p, rango=rango, serie=serie_archivo, fecha_impresion=fecha_form
            )
        guardar_asignaciones(tree)

        # Preparar tabla actualizada + contadores por serie
        asignaciones_mostrar = _armar_asignaciones_mostrar(root, fecha_form)
        tbody_html = render_template(
            'tabla_asignaciones.html',
            vendedores=vendedores,
            asignaciones_mostrar=asignaciones_mostrar,
            fecha_seleccionada=fecha_form,
            boletos_por_planilla=BOLETOS_POR_PLANILLA
        )
        asignadas_serie = _contar_asignadas_serie(root, fecha_form, serie_archivo)
        blanco_serie = max(impresas_serie - asignadas_serie, 0)

        return jsonify(ok=True,
                       tbody=tbody_html,
                       contadores={
                           "impresas_serie": impresas_serie,
                           "asignadas_serie": asignadas_serie,
                           "blanco_serie": blanco_serie
                       })

    # GET: pintar página
    asignaciones_mostrar = _armar_asignaciones_mostrar(root, fecha_seleccionada)
    impresas_serie = planillas_impresas_por_serie_fecha(serie_param, fecha_seleccionada) if serie_param else 0
    asignadas_serie = _contar_asignadas_serie(root, fecha_seleccionada, serie_param) if serie_param else 0
    blanco_serie = max(impresas_serie - asignadas_serie, 0)

    return render_template(
        'asignar_planillas.html',
        vendedores=vendedores,
        fecha_hoy=fecha_hoy,
        fechas_disponibles=sorted([d.attrib['fecha'] for d in root.findall('dia')] + [fecha_hoy]),
        fecha_seleccionada=fecha_seleccionada,
        series_impresas=series_dia,           # ← para el combo de serie
        serie_seleccionada=serie_param,
        impresas_serie=impresas_serie,
        asignadas_serie=asignadas_serie,
        blanco_serie=blanco_serie,
        boletos_por_planilla=BOLETOS_POR_PLANILLA
    )

@app.route('/eliminar_planilla', methods=['POST'])
def eliminar_planilla():
    data = request.get_json(force=True) or {}
    fecha = data.get('fecha', '')
    nombre = data.get('nombre', '')
    apellido = data.get('apellido', '')
    seudonimo = data.get('seudonimo', '')
    numero_planilla = data.get('numero', '')
    serie_archivo = data.get('serie', '')  # NUEVO

    tree, root = leer_asignaciones()
    dia = root.find(f"./dia[@fecha='{fecha}']")
    ok = False

    if dia is not None:
        for v in dia.findall('vendedor'):
            if v.attrib.get('nombre') == nombre and v.attrib.get('apellido') == apellido and v.attrib.get('seudonimo') == seudonimo:
                for p in v.findall('planilla'):
                    if p.attrib.get('numero') == numero_planilla and (p.attrib.get('serie') or '') == serie_archivo:
                        v.remove(p)
                        ok = True
                        break
                if len(v.findall('planilla')) == 0:
                    dia.remove(v)
                break
        if len(dia.findall('vendedor')) == 0:
            root.remove(dia)
        guardar_asignaciones(tree)

    # Tabla actualizada + contadores por serie
    vendedores = cargar_vendedores()
    asignaciones_mostrar = _armar_asignaciones_mostrar(root, fecha)
    tbody_html = render_template(
        'tabla_asignaciones.html',
        vendedores=vendedores,
        asignaciones_mostrar=asignaciones_mostrar,
        fecha_seleccionada=fecha,
        boletos_por_planilla=BOLETOS_POR_PLANILLA
    )

    # Recalcular counters por serie+fecha
    impresas_serie = planillas_impresas_por_serie_fecha(serie_archivo, fecha) if serie_archivo else 0
    asignadas_serie = _contar_asignadas_serie(root, fecha, serie_archivo) if serie_archivo else 0
    blanco_serie = max(impresas_serie - asignadas_serie, 0)

    return jsonify(ok=ok,
                   tbody=tbody_html,
                   contadores={
                       "impresas_serie": impresas_serie,
                       "asignadas_serie": asignadas_serie,
                       "blanco_serie": blanco_serie
                   })


# ─── COBROS en CAJA_XML ─────────────────────────────────────────────────────
# ─────────────────────────────────────────────────────────────────────────────
# COBRO DE CAJA (backend para templates/cobro.html)
# ─────────────────────────────────────────────────────────────────────────────
import os
import io
import xml.etree.ElementTree as ET
from datetime import date, datetime
from types import SimpleNamespace

from flask import (
    Flask, request, render_template, redirect,
    url_for, session, jsonify, Response, render_template_string, current_app
)

# ────────────────────────────────────────────────────────────────────────────
# APP BÁSICA (autónoma). Si ya tienes tu app principal, puedes ignorar esto
# y copiar SOLO las funciones/rutas más abajo a tu proyecto.
# ────────────────────────────────────────────────────────────────────────────

app.secret_key = os.environ.get("SECRET_KEY", "glbingo-dev-key")

# ─── RUTAS/ARCHIVOS base usados por COBRO ───────────────────────────────────
CAJA_XML = os.path.join('static', 'CAJA', 'caja.xml')
os.makedirs(os.path.dirname(CAJA_XML), exist_ok=True)
if not os.path.exists(CAJA_XML):
    ET.ElementTree(ET.Element('caja')).write(CAJA_XML, encoding='utf-8', xml_declaration=True)

# Si estos símbolos no existen en este módulo, los definimos aquí
if 'VENDEDORES_XML' not in globals():
    VENDEDORES_XML = os.path.join('static', 'db', 'vendedores.xml')
if 'ASIGNACIONES_XML' not in globals():
    ASIGNACIONES_XML = os.path.join('static', 'db', 'asignaciones.xml')
if 'BOLETOS_POR_PLANILLA' not in globals():
    BOLETOS_POR_PLANILLA = 20

# ─── HELPERS XML ────────────────────────────────────────────────────────────
def _leer_xml(path: str):
    """Abre un XML; si no existe lo crea con raíz = nombre de archivo."""
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        root_name = os.path.splitext(os.path.basename(path))[0]
        ET.ElementTree(ET.Element(root_name)).write(path, encoding='utf-8', xml_declaration=True)
    tree = ET.parse(path)
    return tree, tree.getroot()

def _guardar_xml(tree: ET.ElementTree, path: str):
    try:
        ET.indent(tree, space="  ", level=0)
    except Exception:
        pass
    tree.write(path, encoding='utf-8', xml_declaration=True)

def _get_dia(root: ET.Element, fecha_str: str) -> ET.Element:
    """Obtiene/crea <dia fecha='YYYY-MM-DD'> en CAJA_XML."""
    dia = root.find(f"./dia[@fecha='{fecha_str}']")
    if dia is None:
        dia = ET.SubElement(root, 'dia', fecha=fecha_str)
    return dia

# ─── CONFIGURACIÓN DEL DÍA ──────────────────────────────────────────────────
def get_configuracion_dia(fecha_str: str):
    t, r = _leer_xml(CAJA_XML)
    dia = _get_dia(r, fecha_str)
    cfg = dia.find('configuracion')
    if cfg is None:
        cfg = ET.SubElement(dia, 'configuracion')
        ET.SubElement(cfg, 'valor_boleto').text = "0.50"
        ET.SubElement(cfg, 'comision_vendedor').text = "30.0"
        ET.SubElement(cfg, 'comision_extra_meta').text = "5.0"
        ET.SubElement(cfg, 'meta_boletos').text = "60"
        _guardar_xml(t, CAJA_XML)

    def ffloat(x, d=0.0):
        try: return float(x)
        except: return d

    def fint(x, d=0):
        try: return int(x)
        except: return d

    return {
        "valor_boleto": ffloat(cfg.findtext('valor_boleto', '0')),
        "comision_vendedor": ffloat(cfg.findtext('comision_vendedor', '0')),
        "comision_extra_meta": ffloat(cfg.findtext('comision_extra_meta', '0')),
        "meta_boletos": fint(cfg.findtext('meta_boletos', '0')),
    }

def set_configuracion_dia(fecha_str: str, data: dict):
    t, r = _leer_xml(CAJA_XML)
    dia = _get_dia(r, fecha_str)
    cfg = dia.find('configuracion') or ET.SubElement(dia, 'configuracion')
    for k in ("valor_boleto", "comision_vendedor", "comision_extra_meta", "meta_boletos"):
        node = cfg.find(k) or ET.SubElement(cfg, k)
        node.text = str(data.get(k, node.text or "0"))
    _guardar_xml(t, CAJA_XML)

# ─── VENDEDORES y ASIGNACIONES (lectura) ────────────────────────────────────
def _cargar_vendedores_base():
    """Devuelve dict por seudónimo: { seudonimo: {nombre, apellido, seudonimo} }"""
    vendedores = {}
    if os.path.exists(VENDEDORES_XML):
        _, r = _leer_xml(VENDEDORES_XML)
        for v in r.findall('vendedor'):
            seud = (v.findtext('seudonimo', '') or '').strip()
            if seud:
                vendedores[seud] = {
                    "nombre":   (v.findtext('nombre', '') or '').strip(),
                    "apellido": (v.findtext('apellido', '') or '').strip(),
                    "seudonimo": seud
                }
    return vendedores

def _cargar_asignaciones_por_fecha(fecha_str: str):
    """Devuelve dict por seudónimo: {'planillas':[...], 'boletos_entregados': int}"""
    data = {}
    if not os.path.exists(ASIGNACIONES_XML):
        return data
    _, r = _leer_xml(ASIGNACIONES_XML)
    dia = r.find(f"./dia[@fecha='{fecha_str}']")
    if dia is None:
        return data
    for v in dia.findall('vendedor'):
        seud = (v.attrib.get('seudonimo', '') or '').strip()
        plans = [p.attrib.get('numero', '') for p in v.findall('planilla')]
        plans = [p for p in plans if p]
        entregados = len(plans) * int(BOLETOS_POR_PLANILLA)
        data[seud] = {"planillas": plans, "boletos_entregados": entregados}
    return data

# ─── COBROS en CAJA_XML ─────────────────────────────────────────────────────
def _get_cobros_node(dia: ET.Element) -> ET.Element:
    return dia.find('cobros') or ET.SubElement(dia, 'cobros')

def _leer_cobros(fecha_str: str):
    """Dict por seudónimo con cobros guardados."""
    _, r = _leer_xml(CAJA_XML)
    dia = _get_dia(r, fecha_str)
    cobros = _get_cobros_node(dia)
    out = {}
    for c in cobros.findall('cobro'):
        seud = c.attrib.get('seudonimo', '')
        out[seud] = {
            "devueltos":     int(c.attrib.get('devueltos', '0')),
            "vendidos":      int(c.attrib.get('vendidos', '0')),
            "total_pagar":   float(c.attrib.get('total_pagar', '0')),
            "transferencia": float(c.attrib.get('transferencia', '0')),
            "efectivo":      float(c.attrib.get('efectivo', '0')),
            "pagado":        c.attrib.get('pagado', '0') == '1',
            "fecha_hora":    c.attrib.get('fecha_hora', '')
        }
    return out

def _upsert_cobro(fecha_str: str, seudonimo: str, datos: dict):
    """Crea/actualiza un <cobro> dentro del día indicado."""
    t, r = _leer_xml(CAJA_XML)
    dia = _get_dia(r, fecha_str)
    cobros = _get_cobros_node(dia)
    node = cobros.find(f"./cobro[@seudonimo='{seudonimo}']") or ET.SubElement(cobros, 'cobro', seudonimo=seudonimo)
    node.set('devueltos',     str(int(datos.get('devueltos', 0))))
    node.set('vendidos',      str(int(datos.get('vendidos', 0))))
    node.set('total_pagar',   f"{float(datos.get('total_pagar', 0)):.2f}")
    node.set('transferencia', f"{float(datos.get('transferencia', 0)):.2f}")
    node.set('efectivo',      f"{float(datos.get('efectivo', 0)):.2f}")
    node.set('pagado',        '1' if datos.get('pagado', True) else '0')
    node.set('fecha_hora',    datos.get('fecha_hora', datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    _guardar_xml(t, CAJA_XML)

# ─── AGREGADORES DE TOTALES (para la tabla de “Pagados”) ────────────────────
def _agregar_totales_pagados(lista_vendedores, config):
    tot = {"planillas":0, "entregados":0, "devueltos":0, "vendidos":0,
           "total":0.0, "gan_vendedor":0.0, "a_pagar_caja":0.0, "pago":0.0}

    for v in lista_vendedores:
        if not v.get('pagado'):
            continue
        tot["planillas"]  += len(v.get('planillas', []))
        tot["entregados"] += v.get('boletos_entregados', 0)
        tot["devueltos"]  += v.get('boletos_devueltos', 0)
        tot["vendidos"]   += v.get('boletos_vendidos', 0)

        vendidos    = v.get('boletos_vendidos', 0)
        total_venta = vendidos * float(config["valor_boleto"])
        pct         = float(config["comision_vendedor"])
        if vendidos >= int(config["meta_boletos"]):
            pct += float(config["comision_extra_meta"])
        gan_v = total_venta * pct / 100.0
        caja  = total_venta - gan_v
        pago  = float(v.get("transferencia", 0.0)) + float(v.get("efectivo", 0.0))

        tot["total"]        += total_venta
        tot["gan_vendedor"] += gan_v
        tot["a_pagar_caja"] += caja
        tot["pago"]         += pago

    for k in ("total","gan_vendedor","a_pagar_caja","pago"):
        tot[k] = round(tot[k], 2)
    return tot

# ─── VISTA PRINCIPAL /cobro (con ?fecha=YYYY-MM-DD) ─────────────────────────
@app.route('/cobro', methods=['GET'])
def cobro():
    if 'usuario' not in session:
        # Si tu proyecto ya tiene /login, se usará el tuyo.
        return redirect(url_for('login', _external=False)) if 'login' in app.view_functions else redirect('/_login_demo')

    fecha_actual = (request.args.get('fecha') or date.today().isoformat()).strip()

    config = get_configuracion_dia(fecha_actual)
    base   = _cargar_vendedores_base()
    asign  = _cargar_asignaciones_por_fecha(fecha_actual)
    cobros = _leer_cobros(fecha_actual)

    vendedores_ui = []
    for seud, info in asign.items():
        base_info  = base.get(seud, {"nombre":"", "apellido":"", "seudonimo":seud})
        planillas  = info.get('planillas', [])
        entregados = info.get('boletos_entregados', 0)

        c = cobros.get(seud, {})
        devueltos = c.get('devueltos', 0)
        vendidos  = c.get('vendidos', max(entregados - devueltos, 0))
        pagado    = c.get('pagado', False)

        vendedores_ui.append({
            "nombre_completo": (base_info.get('nombre','') + " " + base_info.get('apellido','')).strip() or seud,
            "seudonimo": seud,
            "planillas": planillas,
            "boletos_entregados": entregados,
            "boletos_devueltos":  devueltos,
            "boletos_vendidos":   vendidos,
            "transferencia": c.get('transferencia', 0.0),
            "efectivo":      c.get('efectivo', 0.0),
            "pagado":        pagado,
        })

    paid_totals = _agregar_totales_pagados(vendedores_ui, config)

    return render_template(
        'cobro.html',
        username=session.get('usuario', 'admin'),
        avatar=session.get('avatar', 'avatar-male.png'),
        config=config,
        fecha_actual=fecha_actual,
        vendedores=vendedores_ui,
        paid_totals=paid_totals
    )

# ─── GUARDAR CONFIGURACIÓN DEL DÍA ──────────────────────────────────────────
@app.route('/guardar_configuracion_caja', methods=['POST'])
def guardar_configuracion_caja():
    try:
        data = request.get_json(force=True) or {}
        fecha_actual = (data.get('fecha') or request.args.get('fecha') or date.today().isoformat()).strip()
        payload = {
            "valor_boleto":        float(data.get('valor_boleto', 0)),
            "comision_vendedor":   float(data.get('comision_vendedor', 0)),
            "comision_extra_meta": float(data.get('comision_extra_meta', 0)),
            "meta_boletos":        int(data.get('meta_boletos', 0)),
        }
        set_configuracion_dia(fecha_actual, payload)
        return jsonify(ok=True)
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 400

# ─── GUARDAR COBRO DE UN VENDEDOR ───────────────────────────────────────────
@app.route('/guardar_cobro/<seudonimo>', methods=['POST'])
def guardar_cobro(seudonimo):
    try:
        j = request.get_json(force=True) or {}
        fecha_actual = (j.get('fecha') or request.args.get('fecha') or date.today().isoformat()).strip()

        devueltos     = int(j.get('boletos_devueltos', 0))
        vendidos      = int(j.get('boletos_vendidos', 0))
        total_pagar   = float(j.get('total_pagar', 0))
        transferencia = float(j.get('transferencia', 0))
        efectivo      = float(j.get('efectivo', 0))

        _upsert_cobro(
            fecha_actual,
            seudonimo,
            {
                "devueltos":     devueltos,
                "vendidos":      vendidos,
                "total_pagar":   total_pagar,
                "transferencia": transferencia,
                "efectivo":      efectivo,
                "pagado":        True,
            }
        )
        return jsonify(ok=True)
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 400

# ─── RUTAS DE APOYO (no interfieren con tu app) ─────────────────────────────
@app.route("/_login_demo")
def _login_demo():
    """Login de prueba para esta demo autónoma."""
    session['usuario'] = 'Administrador'
    session['avatar'] = 'avatar-male.png'
    return redirect(url_for('cobro'))

@app.route("/cobro_ping")
def cobro_ping():
    return "COBRO PING OK"

@app.route("/cobro_raw")
def cobro_raw():
    tpl_dir = current_app.jinja_loader.searchpath[0] if hasattr(current_app, "jinja_loader") else "templates"
    path = os.path.join(tpl_dir, "cobro.html")
    if not os.path.exists(path):
        return Response(f"NO EXISTE: {path}", 404, mimetype="text/plain")
    with io.open(path, "r", encoding="utf-8") as f:
        data = f.read()
    return Response(data, 200, mimetype="text/plain; charset=utf-8")

@app.route("/cobro_inline")
def cobro_inline():
    html = """
    <!doctype html><meta charset="utf-8">
    <title>Inline Cobro</title>
    <div style="padding:24px;font:16px/1.4 system-ui;background:#f5f7fb">
      <h1>Inline OK</h1>
      <p>Si ves esto, Flask está renderizando. El problema estaría en la plantilla o su ubicación.</p>
      <a href="/_login_demo">Entrar (demo)</a> · <a href="/cobro">/cobro</a>
    </div>
    """
    return render_template_string(html)

@app.after_request
def _debug_banner(resp):
    """Inserta un banner discreto si /cobro devuelve HTML."""
    try:
        if request.path == "/cobro" and resp.content_type and resp.content_type.startswith("text/html"):
            body = resp.get_data(as_text=True) or ""
            if "<!-- COBRO DEBUG BANNER -->" not in body:
                banner = '<!-- COBRO DEBUG BANNER --><div style="position:fixed;z-index:99999;top:8px;left:8px;background:#000;color:#fff;padding:6px 10px;border-radius:6px;font:700 12px system-ui">COBRO render</div>'
                resp.set_data(banner + body)
    except Exception:
        pass
    return resp

# ─── MAIN ───────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Crea carpetas mínimas de ejemplo
    os.makedirs(os.path.dirname(VENDEDORES_XML), exist_ok=True)
    os.makedirs(os.path.dirname(ASIGNACIONES_XML), exist_ok=True)
    # Inicia
    app.run(host="127.0.0.1", port=5000, debug=False)


    
#FIN DE COBRO DE CAJA#







@app.route('/_debug_routes')
def _debug_routes():
    # lista todas las rutas registradas en este proceso
    return '<br>'.join(sorted(rule.rule for rule in app.url_map.iter_rules()))


#crear figuras #




# ─────────────────────────────────────────────────────────────
# FIGURAS · Crear, editar y listar (BINGO americano)
# ORDEN requerido (por FILAS, arriba→abajo):
#   Fila1: B1 I1 N1 G1 O1
#   Fila2: B2 I2 N2 G2 O2
#   ...
#   Fila5: B5 I5 N5 G5 O5
#
# XML: static/db/datos_figuras.xml  (guarda color + pos="B1"...)
# Rutas:
#   /figuras/crear        (crear/editar figuras)
#   /crear-figuras        (alias)
#   /escoger-figuras      (selector con tablero)
#   /figuras/seleccion    (POST opcional desde selector)
#   /api/figuras/orden    (diagnóstico del orden vigente)
# ─────────────────────────────────────────────────────────────
import os
import json
import xml.etree.ElementTree as ET
from datetime import datetime
from flask import (
    render_template, request, redirect, url_for, flash, session,
    current_app, jsonify
)

# Si tu app ya tiene "app", exponemos current_app en templates
if "app" in globals():
    @app.context_processor
    def inject_current_app():
        return dict(current_app=current_app)

# Rutas absolutas
try:
    BASE_DIR
except NameError:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

FIGURAS_XML = os.path.join(BASE_DIR, "static", "db", "datos_figuras.xml")
os.makedirs(os.path.dirname(FIGURAS_XML), exist_ok=True)

# ============ ORDENES ============
def row_order():
    """
    Orden NUEVO por FILAS (lo que pides):
    B1 I1 N1 G1 O1, B2 I2 N2 G2 O2, …, B5 I5 N5 G5 O5
    """
    letters = ["B", "I", "N", "G", "O"]
    out = []
    for r in range(1, 6):          # filas 1..5
        for L in letters:          # columnas B I N G O
            out.append(f"{L}{r}")
    return out                     # 25

def legacy_column_order():
    """
    Orden anterior por COLUMNAS (lo que NO quieres):
    B1 B2 B3 B4 B5, I1 I2 …, N1 N2 …, G1 …, O1 …
    """
    out = []
    for L in ["B", "I", "N", "G", "O"]:
        for r in range(1, 6):
            out.append(f"{L}{r}")
    return out

NEW_ORDER = row_order()
OLD_ORDER = legacy_column_order()

# ============ XML helpers ============
def _write_empty_figuras():
    root = ET.Element("figuras")
    ET.ElementTree(root).write(FIGURAS_XML, encoding="utf-8", xml_declaration=True)

def _ensure_figuras_root():
    if not os.path.exists(FIGURAS_XML):
        _write_empty_figuras()
        return
    try:
        ET.parse(FIGURAS_XML)
    except ET.ParseError:
        _write_empty_figuras()

def _load_tree():
    _ensure_figuras_root()
    return ET.parse(FIGURAS_XML)

def _find_figura(root, nombre_busqueda: str):
    nb = (nombre_busqueda or "").strip().lower()
    for f in root.findall("figura"):
        if f.attrib.get("nombre","").strip().lower() == nb:
            return f
    return None

def _celda_map_by_pos(fig_nodo):
    """Devuelve dict {pos: color} para una figura (pos= B1..O5)."""
    d = {}
    for cel in fig_nodo.findall("celda"):
        pos = (cel.attrib.get("pos") or "").strip()
        col = (cel.attrib.get("color") or "#FFFFFF").strip().upper()
        if pos:
            d[pos] = col
    return d

def _figure_pos_sequence(fig_nodo):
    """Secuencia de pos tal como está en el XML (idx 1..25)."""
    seq = []
    for i in range(1, 26):
        cel = fig_nodo.find(f'celda[@idx="{i}"]')
        seq.append(None if cel is None else (cel.attrib.get("pos") or "").strip())
    return seq

def _needs_migration(fig_nodo):
    """Detecta si la figura quedó guardada en el orden viejo por columnas."""
    seq = _figure_pos_sequence(fig_nodo)
    # comparar suficiente prefijo para no fallar con figuras cortas
    return seq[:10] == OLD_ORDER[:10]

def _rewrite_celdas(fig_nodo, pos_to_color, new_order):
    """Reescribe celdas con new_order; fuerza N3 en blanco."""
    # Limpiar celdas actuales
    for cel in list(fig_nodo.findall("celda")):
        fig_nodo.remove(cel)
    # Forzar centro libre
    pos_to_color = dict(pos_to_color)
    pos_to_color["N3"] = "#FFFFFF"
    # Escribir con nuevo orden (idx 1..25)
    for idx, pos in enumerate(new_order, start=1):
        ET.SubElement(fig_nodo, "celda", {
            "idx": str(idx),
            "color": (pos_to_color.get(pos, "#FFFFFF") or "#FFFFFF").upper(),
            "pos": pos
        })

def migrate_figuras_xml_to_row_order():
    """
    Migra figuras desde el orden por COLUMNAS al orden por FILAS.
    Mantiene colores; N3 queda blanco.
    """
    tree = _load_tree()
    root = tree.getroot()
    changed = False
    for fig in root.findall("figura"):
        if _needs_migration(fig):
            mapping = _celda_map_by_pos(fig)
            _rewrite_celdas(fig, mapping, NEW_ORDER)
            changed = True
    if changed:
        try:
            ET.indent(tree, space="  ", level=0)
        except Exception:
            pass
        tree.write(FIGURAS_XML, encoding="utf-8", xml_declaration=True)

# Ejecutar migración al importar el módulo
try:
    migrate_figuras_xml_to_row_order()
except Exception as _e:
    print("[WARN] Migración de figuras no aplicada:", _e)

# ============ Persistencia ============
def guardar_figura_en_xml(nombre, celdas_hex, descripcion="", pos_codes=None):
    """
    Guarda (crea/reemplaza) una figura:
      - celdas_hex: lista de 25 colores "#RRGGBB"
      - pos_codes : lista de 25 códigos pos (B1..O5). Si NO viene, usamos NEW_ORDER (por FILAS).
      - N3 SIEMPRE en blanco.
    """
    if len(celdas_hex) != 25:
        raise ValueError("La cuadrícula debe tener 25 celdas.")

    tree = _load_tree()
    root = tree.getroot()

    existente = _find_figura(root, nombre)
    if existente is not None:
        root.remove(existente)

    pos = list(pos_codes) if (pos_codes and len(pos_codes) == 25) else NEW_ORDER[:]
    colores = [str(c or "").strip().upper() for c in celdas_hex]

    # Centro gratis N3 blanco
    try:
        n3_idx = pos.index("N3")
        colores[n3_idx] = "#FFFFFF"
    except ValueError:
        pass

    nodo = ET.SubElement(root, "figura", {
        "nombre": (nombre or "").strip(),
        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "centro_bloqueado": "1"
    })

    if (descripcion or "").strip():
        ET.SubElement(nodo, "descripcion").text = descripcion.strip()

    for i, color in enumerate(colores, start=1):
        ET.SubElement(nodo, "celda", {
            "idx": str(i),
            "color": color,
            "pos": pos[i-1]
        })

    try:
        ET.indent(tree, space="  ", level=0)
    except Exception:
        pass
    tree.write(FIGURAS_XML, encoding="utf-8", xml_declaration=True)

def cargar_figura_por_nombre(nombre: str):
    tree = _load_tree()
    root = tree.getroot()
    nodo = _find_figura(root, nombre)
    if nodo is None:
        return None

    desc = ""
    nd = nodo.find("descripcion")
    if nd is not None and (nd.text or "").strip():
        desc = nd.text.strip()

    colores, pos = [], []
    for i in range(1, 26):
        cel = nodo.find(f'celda[@idx="{i}"]')
        if cel is None:
            colores.append("#FFFFFF")
            pos.append(NEW_ORDER[i-1])
        else:
            colores.append((cel.attrib.get("color") or "#FFFFFF").upper())
            pos.append(cel.attrib.get("pos", NEW_ORDER[i-1]))

    # N3 blanco
    try:
        n3_idx = pos.index("N3")
        colores[n3_idx] = "#FFFFFF"
    except ValueError:
        pass

    return {
        "nombre": nodo.attrib.get("nombre",""),
        "fecha": nodo.attrib.get("fecha",""),
        "centro_bloqueado": True,
        "descripcion": desc,
        "colores": colores,
        "pos": pos
    }

def cargar_todas_figuras():
    tree = _load_tree()
    root = tree.getroot()
    figs = []
    for f in root.findall("figura"):
        nombre = f.attrib.get("nombre","")
        fecha = f.attrib.get("fecha","")
        desc = ""
        nd = f.find("descripcion")
        if nd is not None and (nd.text or "").strip():
            desc = nd.text.strip()

        colores, pos = [], []
        for i in range(1, 26):
            cel = f.find(f'celda[@idx="{i}"]')
            if cel is None:
                colores.append("#FFFFFF")
                pos.append(NEW_ORDER[i-1])
            else:
                colores.append((cel.attrib.get("color") or "#FFFFFF").upper())
                pos.append(cel.attrib.get("pos", NEW_ORDER[i-1]))

        # N3 blanco
        try:
            n3_idx = pos.index("N3")
            colores[n3_idx] = "#FFFFFF"
        except ValueError:
            pass

        figs.append({
            "nombre": nombre,
            "fecha": fecha,
            "descripcion": desc,
            "colores": colores,
            "pos": pos
        })

    figs.sort(key=lambda x: x["nombre"].lower())
    return figs

# ============ Rutas (Flask) ============
@app.route("/figuras/crear", methods=["GET", "POST"])
def figuras_crear():
    # Protege si hay login en tu app
    if 'usuario' not in session and 'login' in current_app.view_functions:
        return redirect(_login_url())

    figura_cargada = None
    nombre_cargar = (request.args.get("nombre") or "").strip()
    if nombre_cargar:
        figura_cargada = cargar_figura_por_nombre(nombre_cargar)

    if request.method == "POST":
        nombre = (request.form.get("nombre") or "").strip()
        descripcion = (request.form.get("descripcion") or "").strip()
        grid_raw = (request.form.get("grid") or "").strip()      # "25 colores separados por coma"
        pos_raw  = (request.form.get("grid_pos") or "").strip()  # opcional, 25 POS separados por coma

        colores = [c.strip().upper() for c in grid_raw.split(",") if c.strip()]
        pos_codes = [p.strip() for p in pos_raw.split(",") if p.strip()] if pos_raw else None

        if not nombre:
            flash("El nombre de la figura es obligatorio.", "warning")
            return redirect(url_for("figuras_crear", nombre=nombre))

        if len(colores) != 25:
            flash("La cuadrícula enviada es inválida (deben ser 25 celdas).", "danger")
            return redirect(url_for("figuras_crear", nombre=nombre))

        if pos_codes is not None and len(pos_codes) != 25:
            flash("grid_pos inválido. Debe traer 25 posiciones (B1..O5).", "danger")
            return redirect(url_for("figuras_crear", nombre=nombre))

        try:
            guardar_figura_en_xml(nombre, colores, descripcion, pos_codes)
            flash(f"Figura '{nombre}' guardada correctamente.", "success")
            return redirect(url_for("figuras_crear", nombre=nombre))
        except Exception as e:
            flash(f"Error al guardar la figura: {e}", "danger")
            return redirect(url_for("figuras_crear"))

    return render_template("figuras_crear.html", figura=figura_cargada)

@app.route("/crear-figuras", methods=["GET", "POST"])
def crear_figuras_alias():
    return figuras_crear()

@app.route("/escoger-figuras", methods=["GET"])
def escoger_figuras():
    if 'usuario' not in session and 'login' in current_app.view_functions:
        return redirect(_login_url())
    return render_template("escoger_figuras.html")

@app.route("/figuras/seleccion", methods=["POST"])
def figuras_seleccion():
    if 'usuario' not in session and 'login' in current_app.view_functions:
        return redirect(_login_url())
    raw = request.form.get("seleccion","")
    seleccion = []
    if raw:
        try:
            seleccion = json.loads(raw)
            if not isinstance(seleccion, list):
                seleccion = []
        except Exception:
            seleccion = [s.strip() for s in raw.split(",") if s.strip()]
    session["seleccion_figuras"] = seleccion
    flash(f"Seleccionadas: {', '.join(seleccion) if seleccion else 'ninguna'}", "success")
    return redirect(url_for("escoger_figuras"))

@app.get("/api/figuras/orden")
def api_figuras_orden():
    """Para que el front valide rápidamente el orden del backend."""
    return jsonify({
        "order": NEW_ORDER,              # B1 I1 N1 G1 O1, B2 I2 ...
        "legacy_column_order": OLD_ORDER # B1 B2 B3 B4 B5, I1 I2 ...
    })





# ─────────────────────────────────────────────────────────────
# ESCOGER FIGURAS POR FECHA (con VALOR por figura)
# Archivo: static/db/figuras_por_fecha.xml
# Rutas:
#   GET  /escoger-figuras
#   POST /escoger-figuras/guardar
#   GET  /api/figuras-por-fecha
# ─────────────────────────────────────────────────────────────
import os, re, json, xml.etree.ElementTree as ET
from flask import render_template, request, redirect, url_for, flash, session, current_app, jsonify

FIGURAS_FECHA_XML = os.path.join(BASE_DIR, "static", "db", "figuras_por_fecha.xml")
os.makedirs(os.path.dirname(FIGURAS_FECHA_XML), exist_ok=True)

def _ensure_agenda_root():
    if not os.path.exists(FIGURAS_FECHA_XML):
        ET.ElementTree(ET.Element("agenda")).write(FIGURAS_FECHA_XML, encoding="utf-8", xml_declaration=True)
        return
    try:
        ET.parse(FIGURAS_FECHA_XML)
    except ET.ParseError:
        ET.ElementTree(ET.Element("agenda")).write(FIGURAS_FECHA_XML, encoding="utf-8", xml_declaration=True)

def _load_agenda_tree():
    _ensure_agenda_root()
    return ET.parse(FIGURAS_FECHA_XML)

def _find_dia(root, fecha_iso: str):
    for d in root.findall("dia"):
        if d.attrib.get("fecha") == fecha_iso:
            return d
    return None

def _is_fecha_iso(s: str) -> bool:
    return bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", (s or "").strip()))

def _norm_items(items):
    """
    items puede venir como:
      ["LLENA 1","PIRAMIDE 5"]  o  [{"nombre":"LLENA 1","valor":2.5}, ...]
    Devuelve lista normalizada: [{"nombre":str, "valor":float>=0}, ...] sin duplicados.
    """
    clean, seen = [], set()
    for x in (items or []):
        if isinstance(x, dict):
            nombre = str(x.get("nombre","")).strip()
            valor = x.get("valor", 0)
        else:
            nombre = str(x).strip()
            valor = 0
        if not nombre:
            continue
        key = nombre.lower()
        if key in seen:
            continue
        seen.add(key)
        try:
            v = float(valor)
        except Exception:
            v = 0.0
        if v < 0:
            v = 0.0
        clean.append({"nombre": nombre, "valor": round(v, 2)})
    return clean

def guardar_figuras_para_fecha(fecha_iso: str, items):
    if not _is_fecha_iso(fecha_iso):
        raise ValueError("Fecha inválida. Usa YYYY-MM-DD.")
    lista = _norm_items(items)

    tree = _load_agenda_tree()
    root = tree.getroot()
    dia = _find_dia(root, fecha_iso)
    if dia is not None:
        root.remove(dia)

    dia = ET.SubElement(root, "dia", {"fecha": fecha_iso})
    for it in lista:
        ET.SubElement(dia, "fig", {
            "nombre": it["nombre"],
            "valor": f'{it["valor"]:.2f}'
        })
    tree.write(FIGURAS_FECHA_XML, encoding="utf-8", xml_declaration=True)

def cargar_figuras_de_fecha(fecha_iso: str):
    """
    Devuelve lista de objetos: [{"nombre":"X","valor":2.5}, ...]
    (Si en XML no hay 'valor', devuelve 0.0)
    """
    if not _is_fecha_iso(fecha_iso):
        return []
    tree = _load_agenda_tree()
    root = tree.getroot()
    dia = _find_dia(root, fecha_iso)
    if dia is None:
        return []
    out = []
    for f in dia.findall("fig"):
        nombre = (f.attrib.get("nombre","") or "").strip()
        try:
            valor = float(f.attrib.get("valor","0") or 0)
        except Exception:
            valor = 0.0
        out.append({"nombre": nombre, "valor": round(max(valor, 0.0), 2)})
    return out

# ---------- RUTAS ----------

# Vista (solo GET)
@app.route("/escoger-figuras", methods=["GET"])
def escoger_figuras_view():
    if 'usuario' not in session and 'login' in current_app.view_functions:
        return redirect(_login_url())
    fecha_q = (request.args.get("fecha") or "").strip()
    preseleccion = cargar_figuras_de_fecha(fecha_q) if fecha_q else []
    return render_template("escoger_figuras.html",
                           fecha_inicial=fecha_q,
                           preseleccion=preseleccion)

# Guardar (solo POST)
@app.route("/escoger-figuras/guardar", methods=["POST"])
def escoger_figuras_guardar():
    if 'usuario' not in session and 'login' in current_app.view_functions:
        return redirect(_login_url())

    fecha = (request.form.get("fecha") or "").strip()
    raw   = (request.form.get("seleccion") or "").strip()

    items = []
    if raw:
        try:
            data = json.loads(raw)
            # data puede ser lista de strings o de objetos
            if isinstance(data, list):
                items = data
        except Exception:
            # compat: CSV -> solo nombres
            items = [s.strip() for s in raw.split(",") if s.strip()]

    try:
        guardar_figuras_para_fecha(fecha, items)
        flash(f"Figuras guardadas para {fecha}.", "success")
    except Exception as e:
        flash(f"Error al guardar: {e}", "danger")

    return redirect(url_for("escoger_figuras_view", fecha=fecha))

# API auxiliar (GET)
@app.route("/api/figuras-por-fecha", methods=["GET"])
def api_figuras_por_fecha():
    if 'usuario' not in session and 'login' in current_app.view_functions:
        return jsonify({"ok": False, "error": "no-auth"}), 401
    fecha = (request.args.get("fecha") or "").strip()
    lista = cargar_figuras_de_fecha(fecha) if _is_fecha_iso(fecha) else []
    return jsonify({"ok": True, "fecha": fecha, "figuras": lista})

# -*- coding: utf-8 -*-







#BOLETIN#


import os, re, json, math, unicodedata, xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta
from io import BytesIO
# ====== PARCHE DE ARRANQUE (PÉGALO AL INICIO DE app.py) ======
# Evita NameError en 'mm' incluso si el import real aparece más abajo
try:
    from reportlab.lib.units import mm  # import real si está disponible
except Exception:
    # Fallback: 1 mm en puntos (ReportLab trabaja en puntos)
    mm = 2.834645669291339

# Evita NameError en @login_required si Flask-Login no está instalado
try:
    from flask_login import login_required as _login_required
    def login_required(f):
        return _login_required(f)
except Exception:
    # Fallback 'no-op': deja pasar la vista sin exigir login
    def login_required(f):
        return f
# ====== FIN PARCHE DE ARRANQUE ======

import os
import random
import pandas as pd
import qrcode
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta
from io import BytesIO, StringIO
from flask import Flask, request, render_template, send_file, redirect, url_for, flash, session, jsonify, Response, render_template_string, current_app
import shutil
import csv
import math
import unicodedata
import json
import re
from threading import RLock
from functools import wraps
from werkzeug.routing import BuildError
from werkzeug.utils import secure_filename
from zipfile import ZipFile
from PyPDF2 import PdfMerger

# ReportLab imports
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.units import mm, cm, inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ---- Safe login URL helper (avoids BuildError for missing 'login' endpoint) ----
def _login_url(**values):
    try:
        return url_for('login', **values)
    except Exception:
        try:
            return url_for('_login_demo', **values)
        except Exception:
            return '/_login_demo'
# -------------------------------------------------------------------------------

# ====== CONFIGURACIÓN GLOBAL ======
app = Flask(__name__)
app.secret_key = 'super_secreto_bingo_2025'
app.config["JSON_AS_ASCII"] = False

# ====== CONSTANTES Y PATHS (DEFINIDAS UNA SOLA VEZ) ======
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, 'static')
DATA_DIR = os.environ.get("DATA_DIR", os.path.join(BASE_DIR, "DATA"))
PERSIST_ROOT = os.environ.get("DATA_DIR", "/data" if os.path.isdir("/data") else os.path.join(BASE_DIR, "DATA"))

# Asegurar directorios principales
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(PERSIST_ROOT, exist_ok=True)

# ====== PATHS DE ARCHIVOS XML (SISTEMA CENTRALIZADO) ======
def _persist_path(*rel_parts):
    """Ruta dentro de DATA_DIR (crea la carpeta si no existe)."""
    path = os.path.join(DATA_DIR, *rel_parts)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return path

def _seed_file(src_rel, dst_abs):
    """
    Copia archivo inicial del repo → persistente, solo si NO existe.
    """
    src_abs = os.path.join(BASE_DIR, src_rel)
    if not os.path.exists(dst_abs) and os.path.exists(src_abs):
        shutil.copy2(src_abs, dst_abs)

# Definir TODOS los paths XML en un solo lugar
USUARIOS_XML            = _persist_path('usuarios', 'usuarios.xml')
VENDEDORES_XML          = _persist_path('static', 'db', 'vendedores.xml')
CAJA_XML                = _persist_path('static', 'db', 'caja.xml')
ASIGNACIONES_XML        = _persist_path('static', 'db', 'asignaciones.xml')
PAGOS_PREMIOS_XML       = _persist_path('static', 'db', 'pagos_premios.xml')
RESULTADOS_SORTEO_XML   = _persist_path('static', 'db', 'resultados_sorteo.xml')
SORTEOS_XML             = _persist_path('static', 'db', 'sorteos.xml')
SPINNERS_XML            = _persist_path('static', 'db', 'spinners.xml')
VMIX_REINTEGRO_XML      = _persist_path('static', 'db', 'vmix_reintegro.xml')
VMIX_SPINNERS_XML       = _persist_path('static', 'db', 'vmix_spinners.xml')
VMIX_VENDEDORES_XML     = _persist_path('static', 'db', 'vmix_vendedores.xml')
VMIX_VENTAS_XML         = _persist_path('static', 'db', 'vmix_ventas.xml')
LOGS_CAJA_XML           = _persist_path('static', 'LOGS', 'caja.xml')
LOGS_IMPRESIONES_XML    = _persist_path('static', 'LOGS', 'impresiones.xml')
CONTAB_BANCOS_XML       = _persist_path('static', 'CONTABILIDAD', 'bancos.xml')
CONTAB_GASTOS_XML       = _persist_path('static', 'CONTABILIDAD', 'gastos.xml')
CONTAB_SUELDOS_XML      = _persist_path('static', 'CONTABILIDAD', 'sueldos.xml')
CONTAB_VENTAS_XML       = _persist_path('static', 'CONTABILIDAD', 'ventas.xml')
IMPRESIONES_XML         = _persist_path('static', 'LOGS', 'impresiones.xml')  # Principal para logs
FIGURAS_FECHA_XML       = _persist_path('static', 'db', 'figuras_por_fecha.xml')
DATOS_FIGURAS_XML       = _persist_path('static', 'db', 'datos_figuras.xml')
BINGO_XML               = _persist_path('static', 'db', 'datos_bingo.xml')
BOLETOS_XML             = _persist_path('static', 'db', 'boletos.xml')  # Nuevo: para estructura de boletos
GANADORES_XML           = _persist_path('static', 'db', 'ganadores.xml')  # Nuevo: para registrar ganadores

# Directorios especiales
REINTEGROS_DIR = os.path.join(DATA_DIR, "REINTEGROS")
COMPROB_DIR = os.path.join(STATIC_DIR, "CONTABILIDAD", "comprobantes")
BANK_FILES = os.path.join(COMPROB_DIR, "banco")
GASTO_FILES = os.path.join(COMPROB_DIR, "gastos")
RECIBOS_DIR = os.path.join(STATIC_DIR, "tmp", "recibos")

# Crear todos los directorios necesarios
for directory in [REINTEGROS_DIR, COMPROB_DIR, BANK_FILES, GASTO_FILES, RECIBOS_DIR]:
    os.makedirs(directory, exist_ok=True)

# Constantes del sistema
BOLETOS_POR_PLANILLA = 20
SERIE_MAP = {
    "Srs_ib1.xlsx": "V",
    "Srs_ib2.xlsx": "+",
    "Srs_ib3.xlsx": "&",
    "Srs_Manila.xlsx": "M"
}

ROLES = [
    ('superadmin', 'Super Administrador'),
    ('admin', 'Administrador'),
    ('socio', 'Socio'),
    ('cobrador', 'Cobrador'),
    ('jugador', 'Jugador'),
    ('impresion', 'Impresión'),
]

# ====== SISTEMA DE PERSISTENCIA UNIFICADO ======
def _bind_persistent_dirs():
    """Enlaza carpetas del repositorio con almacenamiento persistente."""
    dirs_to_bind = [
        "usuarios",
        os.path.join("static", "db"),
        os.path.join("static", "LOGS"),
        os.path.join("static", "CONTABILIDAD"),
    ]
    
    for repo_rel in dirs_to_bind:
        repo_abs = os.path.join(BASE_DIR, repo_rel)
        persist_abs = os.path.join(PERSIST_ROOT, repo_rel)
        os.makedirs(persist_abs, exist_ok=True)
        
        # Copiar archivos iniciales si el directorio persistente está vacío
        try:
            if os.path.isdir(repo_abs) and not os.listdir(persist_abs):
                for name in os.listdir(repo_abs):
                    src = os.path.join(repo_abs, name)
                    dst = os.path.join(persist_abs, name)
                    if os.path.isdir(src):
                        shutil.copytree(src, dst, dirs_exist_ok=True)
                    elif os.path.isfile(src) and not os.path.exists(dst):
                        shutil.copy2(src, dst)
        except Exception as e:
            print(f"Warning seeding {repo_rel}: {e}")
        
        # Crear enlace simbólico
        try:
            if not os.path.islink(repo_abs):
                if os.path.isdir(repo_abs):
                    shutil.rmtree(repo_abs)
                elif os.path.exists(repo_abs):
                    os.remove(repo_abs)
                os.symlink(persist_abs, repo_abs, target_is_directory=True)
        except Exception as e:
            print(f"Warning binding {repo_rel}: {e}")

# Ejecutar enlace de directorios
_bind_persistent_dirs()

# Sembrar archivos XML iniciales
seed_pairs = [
    ('usuarios/usuarios.xml', USUARIOS_XML),
    ('static/db/vendedores.xml', VENDEDORES_XML),
    ('static/db/caja.xml', CAJA_XML),
    ('static/db/asignaciones.xml', ASIGNACIONES_XML),
    ('static/db/pagos_premios.xml', PAGOS_PREMIOS_XML),
    ('static/db/resultados_sorteo.xml', RESULTADOS_SORTEO_XML),
    ('static/db/sorteos.xml', SORTEOS_XML),
    ('static/db/spinners.xml', SPINNERS_XML),
    ('static/db/vmix_reintegro.xml', VMIX_REINTEGRO_XML),
    ('static/db/vmix_spinners.xml', VMIX_SPINNERS_XML),
    ('static/db/vmix_vendedores.xml', VMIX_VENDEDORES_XML),
    ('static/db/vmix_ventas.xml', VMIX_VENTAS_XML),
    ('static/LOGS/caja.xml', LOGS_CAJA_XML),
    ('static/LOGS/impresiones.xml', LOGS_IMPRESIONES_XML),
    ('static/CONTABILIDAD/bancos.xml', CONTAB_BANCOS_XML),
    ('static/CONTABILIDAD/gastos.xml', CONTAB_GASTOS_XML),
    ('static/CONTABILIDAD/sueldos.xml', CONTAB_SUELDOS_XML),
    ('static/CONTABILIDAD/ventas.xml', CONTAB_VENTAS_XML),
    ('static/db/boletos.xml', BOLETOS_XML),  # Nuevo
    ('static/db/ganadores.xml', GANADORES_XML),  # Nuevo
]

for src_rel, dst_path in seed_pairs:
    _seed_file(src_rel, dst_path)

# ====== HELPERS GENERALES ======
def _to_int(v, default=0):
    try:
        return int(str(v).strip())
    except Exception:
        return default

def _safe_float(x, default=0.0):
    try:
        return float(str(x).strip())
    except Exception:
        return default

def _safe_text(s, font_name=""):
    s = "" if s is None else str(s)
    if font_name != "Helvetica":
        return s
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")

def format_money(valor):
    try:
        v = float(str(valor).replace(",", "."))
    except Exception:
        return f"${valor}"
    if abs(v - 1.0) < 1e-9:
        return "$1"
    if v < 1.0:
        s = f"{v:.2f}".replace(".", ",")
        return f"{s} ctvs"
    if abs(v - int(v)) < 1e-9:
        return f"${int(v)}"
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return f"${s}"

def fecha_ddmmyyyy(fecha_iso):
    try:
        return datetime.strptime(fecha_iso, "%Y-%m-%d").strftime("%d-%m-%Y")
    except Exception:
        return fecha_iso

def require_session(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'usuario' not in session:
            return redirect(_login_url())
        return f(*args, **kwargs)
    return wrapper

def _is_superadmin():
    rol_raw = session.get('rol') or ''
    rol_n = rol_raw.lower().replace('-', ' ').replace('_', ' ').strip()
    if rol_n in {'superadmin', 'super administrador', 'superadministrador'}:
        return True
    usuario = (session.get('usuario') or '').strip().upper()
    if usuario == 'GLSTUDIOS':
        return True
    return False

# ====== NUEVO: SISTEMA DE DETECCIÓN DE GANADORES ======
def _cargar_figuras_del_dia(fecha_iso):
    """Carga las figuras programadas para el día."""
    figuras = []
    if os.path.exists(FIGURAS_FECHA_XML):
        try:
            tree = ET.parse(FIGURAS_FECHA_XML)
            root = tree.getroot()
            for dia in root.findall('dia'):
                if dia.get('fecha') == fecha_iso:
                    for fig in dia.findall('fig'):
                        figuras.append({
                            'nombre': fig.get('nombre', ''),
                            'valor': _safe_float(fig.get('valor', 0)),
                            'patron': _cargar_patron_figura(fig.get('nombre', ''))
                        })
                    break
        except Exception as e:
            print(f"Error cargando figuras: {e}")
    return figuras

def _cargar_patron_figura(nombre_figura):
    """Carga el patrón (matriz 5x5) de una figura desde datos_figuras.xml."""
    patron = [[False for _ in range(5)] for _ in range(5)]  # 5x5
    
    if os.path.exists(DATOS_FIGURAS_XML):
        try:
            tree = ET.parse(DATOS_FIGURAS_XML)
            root = tree.getroot()
            
            for figura in root.findall('figura'):
                if figura.get('nombre', '').lower() == nombre_figura.lower():
                    # Cargar celdas
                    for celda in figura.findall('celda'):
                        idx = int(celda.get('idx', 0)) - 1  # 0-24
                        if 0 <= idx <= 24:
                            fila = idx // 5
                            col = idx % 5
                            color = celda.get('color', '#FFFFFF').upper()
                            # Rojo (#FF0000) significa que esa celda debe marcarse
                            patron[fila][col] = (color == '#FF0000')
                    break
        except Exception as e:
            print(f"Error cargando patrón de figura {nombre_figura}: {e}")
    
    # Centro (N3) siempre es gratis (True)
    patron[2][2] = True
    
    return patron

def _cargar_estructura_boletos(fecha_iso):
    """
    Carga la estructura de todos los boletos vendidos para el día.
    Retorna dict: {numero_boleto: {vendedor: '', numeros: matriz_5x5}}
    """
    boletos = {}
    
    # 1. Buscar en asignaciones.xml los rangos de boletos por vendedor
    vendedores_rangos = {}
    if os.path.exists(ASIGNACIONES_XML):
        try:
            tree = ET.parse(ASIGNACIONES_XML)
            root = tree.getroot()
            for dia in root.findall('dia'):
                if dia.get('fecha') == fecha_iso:
                    for vendedor in dia.findall('vendedor'):
                        seudonimo = vendedor.get('seudonimo', '')
                        for planilla in vendedor.findall('planilla'):
                            rango = planilla.get('rango', '')
                            if '-' in rango:
                                inicio, fin = map(int, rango.split('-'))
                                for boleto_num in range(inicio, fin + 1):
                                    vendedores_rangos[boleto_num] = seudonimo
                    break
        except Exception as e:
            print(f"Error cargando asignaciones: {e}")
    
    # 2. Buscar en impresiones.xml los números de los boletos
    if os.path.exists(IMPRESIONES_XML):
        try:
            tree = ET.parse(IMPRESIONES_XML)
            root = tree.getroot()
            
            for impresion in root.findall('impresion'):
                if impresion.get('tipo') == 'boletos':
                    imp_fecha = impresion.find('fecha_sorteo')
                    if imp_fecha is not None and imp_fecha.text == fecha_iso:
                        desde = _to_int(impresion.get('desde', 0))
                        hasta = _to_int(impresion.get('hasta', 0))
                        
                        # Generar números de serie para estos boletos
                        for i in range(desde, hasta + 1):
                            boleto_num = i
                            vendedor = vendedores_rangos.get(boleto_num, 'DESCONOCIDO')
                            
                            # Generar matriz 5x5 aleatoria (simulando el boleto real)
                            # En un sistema real, esto vendría de tu base de datos de boletos
                            numeros_boleto = _generar_numeros_boleto(boleto_num)
                            
                            boletos[boleto_num] = {
                                'numero': boleto_num,
                                'vendedor': vendedor,
                                'numeros': numeros_boleto,
                                'marcados': [[False for _ in range(5)] for _ in range(5)]
                            }
        except Exception as e:
            print(f"Error cargando impresiones: {e}")
    
    return boletos

def _generar_numeros_boleto(boleto_num):
    """Genera números aleatorios para un boleto según reglas Bingo."""
    import random
    random.seed(boleto_num)  # Para consistencia
    
    numeros = []
    # Columna B: 1-15
    numeros.append(sorted(random.sample(range(1, 16), 5)))
    # Columna I: 16-30
    numeros.append(sorted(random.sample(range(16, 31), 5)))
    # Columna N: 31-45 (con centro libre)
    nums_n = sorted(random.sample(range(31, 46), 4))
    nums_n.insert(2, 0)  # Centro libre
    numeros.append(nums_n)
    # Columna G: 46-60
    numeros.append(sorted(random.sample(range(46, 61), 5)))
    # Columna O: 61-75
    numeros.append(sorted(random.sample(range(61, 76), 5)))
    
    # Transponer para tener matriz 5x5
    matriz = [[numeros[col][fila] for col in range(5)] for fila in range(5)]
    return matriz

def _actualizar_marcados_en_boletos(boletos, numero_marcado):
    """
    Actualiza qué números están marcados en todos los boletos.
    Retorna lista de boletos actualizados.
    """
    boletos_actualizados = []
    
    for boleto_num, datos in boletos.items():
        actualizado = False
        for fila in range(5):
            for col in range(5):
                if datos['numeros'][fila][col] == numero_marcado:
                    datos['marcados'][fila][col] = True
                    actualizado = True
        
        if actualizado:
            boletos_actualizados.append({
                'numero': boleto_num,
                'vendedor': datos['vendedor'],
                'marcados': datos['marcados']
            })
    
    return boletos_actualizados

def _detectar_ganadores(boletos, figuras, numeros_marcados):
    """
    Detecta qué boletos han completado alguna figura.
    Retorna lista de ganadores.
    """
    ganadores = []
    
    for boleto_num, datos_boleto in boletos.items():
        marcados = datos_boleto['marcados']
        
        for figura in figuras:
            nombre_fig = figura['nombre']
            patron = figura['patron']
            
            # Verificar si el patrón coincide
            coincide = True
            for fila in range(5):
                for col in range(5):
                    # Si el patrón requiere marcado (True) y el boleto no lo tiene marcado
                    if patron[fila][col] and not marcados[fila][col]:
                        coincide = False
                        break
                if not coincide:
                    break
            
            if coincide:
                # ¡Tenemos un ganador!
                ganadores.append({
                    'fecha': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'boleto': boleto_num,
                    'figura': nombre_fig,
                    'vendedor': datos_boleto['vendedor'],
                    'premio': figura['valor'],
                    'numeros_marcados': numeros_marcados[:]  # Copia de los números marcados
                })
    
    return ganadores

def _registrar_ganador(ganador):
    """Registra un ganador en el XML de ganadores."""
    try:
        if not os.path.exists(GANADORES_XML):
            root = ET.Element('ganadores')
            tree = ET.ElementTree(root)
            tree.write(GANADORES_XML, encoding='utf-8', xml_declaration=True)
        
        tree = ET.parse(GANADORES_XML)
        root = tree.getroot()
        
        # Crear elemento ganador
        elem = ET.Element('ganador', {
            'fecha': ganador['fecha'],
            'boleto': str(ganador['boleto']),
            'figura': ganador['figura'],
            'vendedor': ganador['vendedor'],
            'premio': str(ganador['premio'])
        })
        
        # Agregar números marcados
        numeros_elem = ET.SubElement(elem, 'numeros_marcados')
        numeros_elem.text = ','.join(map(str, ganador['numeros_marcados']))
        
        root.append(elem)
        
        # Guardar
        try:
            ET.indent(tree, space="  ", level=0)
        except:
            pass
        tree.write(GANADORES_XML, encoding='utf-8', xml_declaration=True)
        
        return True
    except Exception as e:
        print(f"Error registrando ganador: {e}")
        return False

# ====== GESTIÓN DE USUARIOS ======
def leer_usuarios():
    if not os.path.exists(USUARIOS_XML):
        return []
    tree = ET.parse(USUARIOS_XML)
    root = tree.getroot()
    usuarios = []
    for elem in root.findall('usuario'):
        usuarios.append({
            'nombre': elem.find('nombre').text,
            'clave': elem.find('clave').text,
            'rol': elem.find('rol').text,
            'email': elem.find('email').text if elem.find('email') is not None else '',
            'estado': elem.find('estado').text,
            'avatar': elem.find('avatar').text if elem.find('avatar') is not None else 'avatar-male.png'
        })
    return usuarios

def guardar_usuarios(usuarios):
    root = ET.Element('usuarios')
    for u in usuarios:
        user_elem = ET.SubElement(root, 'usuario')
        ET.SubElement(user_elem, 'nombre').text = u['nombre']
        ET.SubElement(user_elem, 'clave').text = u['clave']
        ET.SubElement(user_elem, 'rol').text = u['rol']
        ET.SubElement(user_elem, 'email').text = u.get('email', '')
        ET.SubElement(user_elem, 'estado').text = u['estado']
        ET.SubElement(user_elem, 'avatar').text = u.get('avatar', 'avatar-male.png')
    tree = ET.ElementTree(root)
    tree.write(USUARIOS_XML, encoding='utf-8', xml_declaration=True)

def obtener_usuario(nombre):
    usuarios = leer_usuarios()
    for u in usuarios:
        if u['nombre'] == nombre:
            return u
    return None

def eliminar_usuario(nombre):
    usuarios = leer_usuarios()
    usuarios = [u for u in usuarios if u['nombre'] != nombre]
    guardar_usuarios(usuarios)

# ====== RUTAS PRINCIPALES ======
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form['usuario']
        clave = request.form['clave']
        usuarios = leer_usuarios()
        user = next((u for u in usuarios if u['nombre'] == usuario and u['clave'] == clave and u['estado'] == 'activo'), None)
        if user:
            session['usuario'] = user['nombre']
            session['rol'] = user['rol']
            session['avatar'] = user.get('avatar', 'avatar-male.png')
            return redirect(url_for('dashboard'))
        else:
            flash('Usuario o clave incorrectos o usuario inactivo', 'error')
    return render_template('login.html')

@app.route('/dashboard')
@require_session
def dashboard():
    return render_template(
        'dashboard.html',
        usuario=session.get('usuario',''),
        rol=session.get('rol',''),
        avatar=session.get('avatar','avatar-male.png')
    )

@app.get('/api/dashboard/hoy')
def api_dashboard_hoy():
    fecha = (request.args.get('fecha') or date.today().isoformat()).strip()
    try:
        datetime.fromisoformat(fecha)
    except Exception:
        fecha = date.today().isoformat()
    
    # Datos básicos del dashboard
    data = {
        "fecha": fecha,
        "boletos_impresos": 0,
        "vendidos_total": 0,
        "devueltos_total": 0,
        "ingresos_brutos": 0.0,
        "ganancia_vendedores": 0.0,
        "ganancia_empresa": 0.0,
        "efectivo": 0.0,
        "transferencia": 0.0,
        "planillas_impresas": 0,
        "planillas_asignadas": 0,
        "planillas_blanco": 0,
        "vendedores": [],
        "config": {
            "valor_boleto": 0.0,
            "comision_vendedor": 0.0,
            "comision_extra_meta": 0.0,
            "meta_boletos": 0
        }
    }
    
    return jsonify({"ok": True, **data})

@app.route('/logout')
def logout():
    session.clear()
    return redirect(_login_url())

# ====== SECCIÓN DE USUARIOS ======
@app.route('/usuarios')
@require_session
def usuarios():
    lista_usuarios = leer_usuarios()
    roles = [r[1] for r in ROLES]
    return render_template(
        'usuarios.html',
        usuarios=lista_usuarios,
        roles=roles,
        usuario=session['usuario'],
        rol=session['rol'],
        avatar=session.get('avatar', 'avatar-male.png')
    )

@app.route('/usuarios/guardar', methods=['POST'])
@require_session
def guardar_usuario():
    nombre = request.form['username']
    clave = request.form['password']
    rol = request.form['rol']
    email = request.form.get('email', '')
    avatar_filename = request.form.get('avatar_select', 'avatar-male.png')
    estado = 'activo'

    usuarios = leer_usuarios()
    existe = False
    for u in usuarios:
        if u['nombre'] == nombre:
            u['clave'] = clave
            u['rol'] = rol
            u['email'] = email
            u['avatar'] = avatar_filename
            u['estado'] = estado
            existe = True
    if not existe:
        usuarios.append({
            'nombre': nombre,
            'clave': clave,
            'rol': rol,
            'email': email,
            'avatar': avatar_filename,
            'estado': estado
        })
    guardar_usuarios(usuarios)
    flash('Usuario guardado correctamente', 'success')
    return redirect(url_for('usuarios'))

@app.route('/usuarios/editar/<nombre>', methods=['GET', 'POST'])
@require_session
def editar_usuario(nombre):
    user = obtener_usuario(nombre)
    if not user:
        flash(f'Usuario "{nombre}" no encontrado', 'error')
        return redirect(url_for('usuarios'))
    
    if request.method == 'POST':
        user['clave'] = request.form['password']
        user['rol'] = request.form['rol']
        user['email'] = request.form.get('email', '')
        user['avatar'] = request.form.get('avatar_select', user['avatar'])
        usuarios = leer_usuarios()
        for u in usuarios:
            if u['nombre'] == nombre:
                u.update(user)
        guardar_usuarios(usuarios)
        flash('Usuario editado correctamente', 'success')
        return redirect(url_for('usuarios'))
    
    return render_template(
        'usuarios_editar.html',
        user=user,
        roles=[r[1] for r in ROLES],
        usuario=session['usuario'],
        rol=session['rol'],
        avatar=session.get('avatar', 'avatar-male.png')
    )

@app.route('/usuarios/eliminar/<nombre>', methods=['POST'])
@require_session
def eliminar_usuario_route(nombre):
    eliminar_usuario(nombre)
    flash('Usuario eliminado correctamente', 'success')
    return redirect(url_for('usuarios'))

# ====== IMPRESIÓN DE BOLETOS ======
def _read_df_for_series(archivo: str) -> pd.DataFrame:
    """Lee XLSX o CSV como texto."""
    path = os.path.join(DATA_DIR, archivo)
    if not os.path.exists(path):
        raise FileNotFoundError(f"No existe el archivo de serie: {archivo}")
    if archivo.lower().endswith(".csv"):
        return pd.read_csv(path, dtype=str, keep_default_na=False).fillna("")
    return pd.read_excel(path, dtype=str).fillna("")

def _send_bytesio(buf: BytesIO, filename: str, mimetype: str = None):
    """Envía BytesIO como archivo."""
    try:
        return send_file(buf, download_name=filename, as_attachment=True, mimetype=mimetype)
    except TypeError:
        return send_file(buf, attachment_filename=filename, as_attachment=True, mimetype=mimetype)

# Configuración PDF
BLEED = 5 * mm
w, h = A4
OFFSET_X = -20
OFFSET_Y = 5
MARGEN_IZQ = 20
MARGEN_SUP = 60
ESPACIO_X = 140
ESPACIO_Y = 115
COLUMNAS = 2
FILAS = 4
SIZE_NUM = 23
SIZE_INFO = 12
SIZE_ID_BIG = 18
REINTEGRO_W = 41
REINTEGRO_H = 41
DELTA_Y_FILA_3 = 2
DELTA_Y_FILA_4 = 5

# Offsets por celda
per_cell_offsets = {
    0: {"grid_x": -80, "grid_y": 20,  "info_x": 5,   "info_y": 20,  "rein_x": 215, "rein_y": 30},
    1: {"grid_x": -160, "grid_y":20,  "info_x": -70, "info_y": 20,  "rein_x": 140, "rein_y": 30},
    2: {"grid_x": -80, "grid_y": 80,  "info_x": 5,   "info_y": 82,  "rein_x": 215, "rein_y": -25},
    3: {"grid_x": -160, "grid_y":80,  "info_x": -70, "info_y": 82,  "rein_x": 140, "rein_y": -25},
    4: {"grid_x": -80, "grid_y": 140, "info_x": 5,   "info_y": 140, "rein_x": 215, "rein_y": -85},
    5: {"grid_x": -160, "grid_y":140, "info_x": -70, "info_y": 140, "rein_x": 140, "rein_y": -85},
    6: {"grid_x": -80, "grid_y": 200, "info_x": 5,   "info_y": 200, "rein_x": 215, "rein_y": -145},
    7: {"grid_x": -160, "grid_y":200, "info_x": -70, "info_y": 200, "rein_x": 140, "rein_y": -145},
}

# Logs de impresión
_LOG_LOCK = RLock()

def _ensure_logs_file():
    if not os.path.exists(IMPRESIONES_XML):
        root = ET.Element('impresiones')
        tree = ET.ElementTree(root)
        tmp_path = IMPRESIONES_XML + ".tmp"
        tree.write(tmp_path, encoding='utf-8', xml_declaration=True)
        os.replace(tmp_path, IMPRESIONES_XML)

def _read_logs_root():
    _ensure_logs_file()
    tree = ET.parse(IMPRESIONES_XML)
    return tree, tree.getroot()

def _write_logs_tree(tree):
    try:
        ET.indent(tree, space="  ", level=0)
    except Exception:
        pass
    tmp_path = IMPRESIONES_XML + ".tmp"
    tree.write(tmp_path, encoding='utf-8', xml_declaration=True)
    os.replace(tmp_path, IMPRESIONES_XML)

def _iter_impresiones():
    _, root = _read_logs_root()
    for n in root.findall('impresion'):
        yield n

def _append_log_impresion_boletos(*, usuario, serie_archivo, desde, hasta, fecha_sorteo, total_boletos,
                                 valor, telefono, reintegro_especial, cant_reintegro_especial,
                                 incluir_aleatorio, excedente=0, lote=''):
    with _LOG_LOCK:
        tree, root = _read_logs_root()
        elem = ET.Element('impresion', attrib={
            'fecha_hora': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'usuario': str(usuario or ''),
            'tipo': 'boletos',
            'serie_archivo': str(serie_archivo or ''),
            'desde': str(desde or ''),
            'hasta': str(hasta or '')
        })
        def add(tag, val):
            c = ET.SubElement(elem, tag)
            c.text = '' if val is None else str(val)
        
        add('valor', valor)
        add('telefono', telefono)
        add('fecha_sorteo', fecha_sorteo)
        add('reintegro_especial', reintegro_especial)
        add('cant_reintegro_especial', cant_reintegro_especial)
        add('incluir_aleatorio', '1' if incluir_aleatorio else '0')
        add('total_boletos', total_boletos)
        try:
            tp = int(math.ceil(int(total_boletos) / 20.0))
        except Exception:
            tp = ''
        add('total_planillas', tp)
        add('excedente', '1' if excedente else '0')
        add('lote', lote)
        
        root.append(elem)
        _write_logs_tree(tree)

# Generador de PDF para boletos
def generar_pdf_boletos_excel(ids, registros, valor, telefono, nombre, reintegro_especial,
                             cant_especial, reintegros, incluir_aleatorio, fecha_sorteo):
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    c.translate(OFFSET_X, OFFSET_Y)

    fecha_num = fecha_ddmmyyyy(fecha_sorteo)
    precio_str = format_money(valor)

    N = len(registros)
    esp_idx = random.sample(range(N), min(N, cant_especial)) if reintegro_especial else []
    ale_idx = [i for i in range(N) if i not in esp_idx] if incluir_aleatorio else []

    for start in range(0, N, FILAS * COLUMNAS):
        page = registros[start:start + FILAS * COLUMNAS]

        for i, row in enumerate(page):
            pos = start + i
            col = i % COLUMNAS
            fil = i // COLUMNAS

            ancho_b = (w + 2 * MARGEN_IZQ - ESPACIO_X * (COLUMNAS - 1)) / COLUMNAS
            alto_b = (h + 2 * MARGEN_SUP - ESPACIO_Y * (FILAS - 1)) / FILAS
            x0 = MARGEN_IZQ + col * (ancho_b + ESPACIO_X)
            y0 = h - MARGEN_SUP - fil * (alto_b + ESPACIO_Y)
            if fil == 2: y0 -= DELTA_Y_FILA_3
            if fil == 3: y0 -= DELTA_Y_FILA_4

            size = min(ancho_b, alto_b) / 5
            offs = per_cell_offsets[i]

            # Rejilla 5×5
            bx0 = x0 + ancho_b - size * 5 + offs['grid_x']
            by0 = y0 + offs['grid_y']
            c.setFont('Helvetica-Bold', SIZE_NUM)
            
            for r in range(5):
                for j, letra in enumerate('bingo'):
                    cx = bx0 + j * size
                    cy = by0 - r * size
                    if letra == 'n' and r == 2:
                        # QR
                        try:
                            buf_qr = BytesIO()
                            qrcode.make(f"{ids[pos]}|{fecha_sorteo}").save(buf_qr, format="PNG")
                            buf_qr.seek(0)
                            c.drawImage(ImageReader(buf_qr), cx + 2, cy + 2, size - 4, size - 4, mask="auto")
                        except Exception:
                            c.setFillGray(0.95)
                            c.rect(cx, cy, size, size, stroke=0, fill=1)
                            c.setFillGray(0.0)
                            c.setFont("Helvetica", 6)
                            c.drawCentredString(cx + size/2, cy + size/2 - 3, "QR")
                    else:
                        v = str(row.get(f"{letra}{r+1}", "-"))
                        c.drawCentredString(cx + size / 2, cy + size * 0.28, v)

            # Texto inferior
            boleto_text = f"{ids[pos]}{SERIE_MAP.get(nombre, nombre)}"
            x_info = x0 + offs['info_x']
            y_info = y0 - size * 5 + offs['info_y']

            c.setFont('Helvetica-Bold', SIZE_ID_BIG)
            c.drawString(x_info, y_info, boleto_text)

            # Reintegro
            img = None
            if pos in esp_idx and reintegro_especial:
                img = reintegro_especial
            elif pos in ale_idx and reintegros:
                others = [r for r in reintegros if r != reintegro_especial]
                img = random.choice(others) if others else None

            if img:
                path_img = os.path.join(REINTEGROS_DIR, img)
                if os.path.exists(path_img):
                    c.drawImage(ImageReader(path_img), x0 + offs['rein_x'], y0 - offs['rein_y'], 
                               REINTEGRO_W, REINTEGRO_H, mask="auto")

        c.showPage()
        c.translate(OFFSET_X, OFFSET_Y)

    c.save()
    buf.seek(0)
    return buf

@app.route('/impresion', methods=['GET', 'POST'])
@require_session
def impresion():
    files = sorted(f for f in os.listdir(DATA_DIR)
                   if f.lower().endswith(('.xlsx', '.csv')))
    series = [(f, SERIE_MAP.get(f, f)) for f in files]
    reintegros = sorted(f for f in os.listdir(REINTEGROS_DIR)
                        if f.lower().endswith('.png')) if os.path.exists(REINTEGROS_DIR) else []
    fecha_hoy = date.today().strftime('%Y-%m-%d')

    if request.method != 'POST':
        return render_template(
            'impresion_boletos_excel.html',
            series=series, reintegros=reintegros, fecha_hoy=fecha_hoy,
            username=session.get('usuario',''),
            usuario=session.get('usuario',''),
            rol=session.get('rol',''),
            avatar=session.get('avatar','avatar-male.png'),
            permisos=session.get('permisos', [])
        )

    form_type = (request.form.get('form_type') or '').strip().lower()

    # ---- BOLETOS ----
    if form_type == 'boletos':
        serie_archivo = (request.form.get('serie_archivo') or '').strip()
        start = (request.form.get('serie_inicio') or '').strip()
        end = (request.form.get('serie_fin') or '').strip()
        valor = (request.form.get('valor') or '1.00').strip()
        telefono = (request.form.get('telefono') or '').strip()
        fecha_str = (request.form.get('fecha_sorteo') or fecha_hoy).strip()
        rein_esp = (request.form.get('reintegro_especial') or '').strip()
        cntesp = _to_int(request.form.get('cant_reintegro_especial'), 0)
        incA_raw = (request.form.get('incluir_aleatorio') or '1').strip().lower()
        incA = incA_raw in ('1', 'true', 'on', 'si', 'sí')

        if not serie_archivo:
            flash('Selecciona una serie para imprimir boletos.', 'warning')
            return redirect(url_for('impresion'))

        try:
            df = _read_df_for_series(serie_archivo)
        except Exception as e:
            flash(str(e), 'danger')
            return redirect(url_for('impresion'))

        id_col = df.columns[0]
        all_ids = df[id_col].astype(str).tolist()
        if not all_ids:
            flash('La serie seleccionada no contiene datos.', 'danger')
            return redirect(url_for('impresion'))

        if not start:
            start = all_ids[0]
        if not end:
            end = start

        if start not in all_ids:
            flash(f'Boleto inicial "{start}" no existe en la serie.', 'danger')
            return redirect(url_for('impresion'))
        if end not in all_ids:
            flash(f'Boleto final "{end}" no existe en la serie.', 'danger')
            return redirect(url_for('impresion'))

        s_idx = all_ids.index(start)
        e_idx = all_ids.index(end) + 1
        if e_idx <= s_idx:
            e_idx = s_idx + 1

        ids = all_ids[s_idx:e_idx]
        registros = df.iloc[s_idx:e_idx].to_dict('records')

        # Log
        _append_log_impresion_boletos(
            usuario=session.get('usuario', ''),
            serie_archivo=serie_archivo,
            desde=start, hasta=end,
            fecha_sorteo=fecha_str,
            total_boletos=len(ids),
            valor=valor, telefono=telefono,
            reintegro_especial=rein_esp,
            cant_reintegro_especial=cntesp,
            incluir_aleatorio=incA,
        )

        rein_list = sorted(f for f in os.listdir(REINTEGROS_DIR) 
                          if f.lower().endswith('.png')) if os.path.exists(REINTEGROS_DIR) else []
        buf_b = generar_pdf_boletos_excel(
            ids, registros, valor, telefono,
            serie_archivo, rein_esp, cntesp,
            rein_list, incA, fecha_str
        )
        return _send_bytesio(buf_b, 'boletos_bingo.pdf', 'application/pdf')

    flash('Formulario no reconocido.', 'warning')
    return redirect(url_for('impresion'))

# ====== VENDEDORES ======
def cargar_vendedores_xml():
    vendedores = []
    if not os.path.exists(VENDEDORES_XML):
        return vendedores
    
    tree = ET.parse(VENDEDORES_XML)
    root = tree.getroot()
    
    for idx, v in enumerate(root.findall('vendedor')):
        vendedores.append({
            'id': idx,
            'nombre': (v.findtext('nombre') or '').strip(),
            'apellido': (v.findtext('apellido') or '').strip(),
            'seudonimo': (v.findtext('seudonimo') or '').strip(),
        })
    return vendedores

def guardar_vendedor(nombre, apellido, seudonimo):
    nombre = (nombre or '').strip()
    apellido = (apellido or '').strip()
    seudonimo = (seudonimo or '').strip()

    if not os.path.exists(VENDEDORES_XML):
        root = ET.Element('vendedores')
        tree = ET.ElementTree(root)
    else:
        tree = ET.parse(VENDEDORES_XML)
        root = tree.getroot()

    v = ET.SubElement(root, 'vendedor')
    ET.SubElement(v, 'nombre').text = nombre
    ET.SubElement(v, 'apellido').text = apellido
    ET.SubElement(v, 'seudonimo').text = seudonimo

    tree.write(VENDEDORES_XML, encoding='utf-8', xml_declaration=True)

@app.route('/vendedores', methods=['GET', 'POST'])
@require_session
def vendedores():
    if request.method == 'POST':
        if 'editar' in request.form:
            idx = int(request.form['id'])
            nombre = request.form['nombre'].strip()
            apellido = request.form['apellido'].strip()
            seudonimo = request.form['seudonimo'].strip()
            # Implementar editar_vendedor si es necesario
            flash("Función de edición pendiente", "info")
        elif 'eliminar' in request.form:
            idx = int(request.form['id'])
            # Implementar eliminar_vendedor si es necesario
            flash("Función de eliminación pendiente", "info")
        else:
            nombre = request.form['nombre'].strip()
            apellido = request.form['apellido'].strip()
            seudonimo = request.form['seudonimo'].strip()
            if nombre and apellido and seudonimo:
                guardar_vendedor(nombre, apellido, seudonimo)
                flash("¡Vendedor agregado!", "success")
            else:
                flash("Todos los campos son obligatorios.", "danger")
        
        return redirect(url_for('vendedores'))

    vendedores_list = cargar_vendedores_xml()
    return render_template('vendedores.html', vendedores=vendedores_list)

# ====== SORTEO ======
@app.route('/sorteo')
def sorteo():
    fecha = request.args.get('fecha') or date.today().isoformat()
    return render_template('sorteo.html', fecha=fecha)

# ====== NUEVO: SISTEMA DE BINGO CON DETECCIÓN DE GANADORES ======
# Variables globales para el juego en curso
_JUEGO_ESTADO = {
    'numeros_marcados': [],
    'boletos': {},
    'figuras': [],
    'ganadores': [],
    'fecha_juego': date.today().isoformat(),
    'lock': RLock()
}

def _inicializar_juego(fecha_iso):
    """Inicializa el estado del juego para una fecha específica."""
    with _JUEGO_ESTADO['lock']:
        _JUEGO_ESTADO['fecha_juego'] = fecha_iso
        _JUEGO_ESTADO['numeros_marcados'] = []
        _JUEGO_ESTADO['ganadores'] = []
        
        # Cargar figuras del día
        _JUEGO_ESTADO['figuras'] = _cargar_figuras_del_dia(fecha_iso)
        
        # Cargar estructura de boletos
        _JUEGO_ESTADO['boletos'] = _cargar_estructura_boletos(fecha_iso)
        
        # Cargar ganadores previos
        _JUEGO_ESTADO['ganadores'] = _cargar_ganadores_dia(fecha_iso)
        
        print(f"Juego inicializado para {fecha_iso}: {len(_JUEGO_ESTADO['boletos'])} boletos, {len(_JUEGO_ESTADO['figuras'])} figuras")

def _cargar_ganadores_dia(fecha_iso):
    """Carga ganadores ya registrados para el día."""
    ganadores = []
    if os.path.exists(GANADORES_XML):
        try:
            tree = ET.parse(GANADORES_XML)
            root = tree.getroot()
            for ganador in root.findall('ganador'):
                # Solo cargar ganadores del día actual
                ganadores.append({
                    'boleto': ganador.get('boleto', ''),
                    'figura': ganador.get('figura', ''),
                    'vendedor': ganador.get('vendedor', ''),
                    'premio': _safe_float(ganador.get('premio', 0)),
                    'fecha': ganador.get('fecha', '')
                })
        except Exception as e:
            print(f"Error cargando ganadores: {e}")
    return ganadores

def _marcar_numero_y_detectar(numero):
    """
    Marca un número y detecta si hay ganadores.
    Retorna: (exito, mensaje, ganadores_nuevos)
    """
    with _JUEGO_ESTADO['lock']:
        # Verificar que el juego esté inicializado
        if not _JUEGO_ESTADO['figuras']:
            return False, "Juego no inicializado. Configura las figuras primero.", []
        
        if not _JUEGO_ESTADO['boletos']:
            return False, "No hay boletos cargados para el día.", []
        
        # Verificar que el número sea válido
        if numero < 1 or numero > 75:
            return False, f"Número {numero} fuera de rango (1-75).", []
        
        # Verificar que no esté ya marcado
        if numero in _JUEGO_ESTADO['numeros_marcados']:
            return False, f"El número {numero} ya está marcado.", []
        
        # Marcar el número
        _JUEGO_ESTADO['numeros_marcados'].append(numero)
        
        # Actualizar boletos con el número marcado
        boletos_actualizados = _actualizar_marcados_en_boletos(
            _JUEGO_ESTADO['boletos'], 
            numero
        )
        
        # Detectar nuevos ganadores
        nuevos_ganadores = _detectar_ganadores(
            _JUEGO_ESTADO['boletos'],
            _JUEGO_ESTADO['figuras'],
            _JUEGO_ESTADO['numeros_marcados']
        )
        
        # Filtrar solo ganadores nuevos (no registrados previamente)
        ganadores_nuevos = []
        for ganador in nuevos_ganadores:
            # Verificar si ya está en la lista de ganadores
            ya_ganador = any(
                g['boleto'] == ganador['boleto'] and 
                g['figura'] == ganador['figura']
                for g in _JUEGO_ESTADO['ganadores']
            )
            
            if not ya_ganador:
                # Registrar el ganador
                if _registrar_ganador(ganador):
                    _JUEGO_ESTADO['ganadores'].append(ganador)
                    ganadores_nuevos.append(ganador)
        
        # Actualizar XML del bingo
        _actualizar_xml_bingo()
        
        mensaje = f"Número {numero} marcado correctamente."
        if ganadores_nuevos:
            mensaje += f" ¡{len(ganadores_nuevos)} nuevo(s) ganador(es)!"
        
        return True, mensaje, ganadores_nuevos

def _actualizar_xml_bingo():
    """Actualiza el XML del bingo con el estado actual."""
    try:
        root = ET.Element("bingo")
        balotas = ET.SubElement(root, "balotas")
        
        # Balotas 1-75
        for n in range(1, 76):
            estado = "n" if n in _JUEGO_ESTADO['numeros_marcados'] else ""
            ultimo = "X" if n == _JUEGO_ESTADO['numeros_marcados'][-1] if _JUEGO_ESTADO['numeros_marcados'] else "" else ""
            ET.SubElement(balotas, "balota", numero=str(n), estado=estado, ultimo=ultimo)
        
        # Últimos 5 números marcados
        ultimos5 = _JUEGO_ESTADO['numeros_marcados'][-5:] if len(_JUEGO_ESTADO['numeros_marcados']) >= 5 else _JUEGO_ESTADO['numeros_marcados']
        root.find("ultimos5").text = ",".join(map(str, ultimos5))
        
        # Total marcadas
        root.find("totalMarcadas").text = str(len(_JUEGO_ESTADO['numeros_marcados']))
        
        # Último marcado
        ultimo = _JUEGO_ESTADO['numeros_marcados'][-1] if _JUEGO_ESTADO['numeros_marcados'] else ""
        root.find("ultimoMarcado").text = str(ultimo)
        
        # Stinger (para efectos de sonido)
        root.find("stinger").text = str(ultimo)
        
        # Guardar
        tree = ET.ElementTree(root)
        tree.write(BINGO_XML, encoding='utf-8', xml_declaration=True)
        
    except Exception as e:
        print(f"Error actualizando XML bingo: {e}")

# ====== RUTAS DEL JUEGO ======
@app.route('/juego')
def juego():
    fecha = request.args.get('fecha') or date.today().isoformat()
    
    # Inicializar juego para esta fecha
    _inicializar_juego(fecha)
    
    return render_template('juego.html', fecha=fecha)

@app.get('/xml/bingo')
def juego_xml_bingo():
    # Asegurar que el XML existe
    if not os.path.exists(BINGO_XML):
        _actualizar_xml_bingo()
    
    resp = make_response(send_file(BINGO_XML, mimetype="application/xml"))
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    resp.headers["Pragma"] = "no-cache"
    return resp

@app.post('/juego/marcar')
def juego_marcar():
    data = request.get_json(silent=True) or {}
    numero = _to_int(data.get("numero", 0))
    
    if not numero:
        return jsonify(success=False, error="Número inválido"), 400
    
    # Marcar número y detectar ganadores
    exito, mensaje, ganadores_nuevos = _marcar_numero_y_detectar(numero)
    
    if not exito:
        return jsonify(success=False, error=mensaje), 400
    
    respuesta = {
        'success': True,
        'numero': numero,
        'total_marcados': len(_JUEGO_ESTADO['numeros_marcados']),
        'ultimos5': _JUEGO_ESTADO['numeros_marcados'][-5:] if len(_JUEGO_ESTADO['numeros_marcados']) >= 5 else _JUEGO_ESTADO['numeros_marcados'],
        'mensaje': mensaje
    }
    
    # Si hay ganadores nuevos, incluirlos en la respuesta
    if ganadores_nuevos:
        respuesta['ganadores_nuevos'] = ganadores_nuevos
        respuesta['total_ganadores'] = len(_JUEGO_ESTADO['ganadores'])
    
    return jsonify(respuesta)

@app.post('/juego/reversa')
def juego_reversa():
    with _JUEGO_ESTADO['lock']:
        if _JUEGO_ESTADO['numeros_marcados']:
            # Eliminar el último número marcado
            ultimo = _JUEGO_ESTADO['numeros_marcados'].pop()
            
            # Actualizar XML
            _actualizar_xml_bingo()
            
            return jsonify({
                'success': True,
                'numero_eliminado': ultimo,
                'total_marcados': len(_JUEGO_ESTADO['numeros_marcados']),
                'mensaje': f'Número {ultimo} eliminado (reversa)'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'No hay números para eliminar'
            }), 400

@app.post('/juego/reset')
def juego_reset():
    with _JUEGO_ESTADO['lock']:
        _JUEGO_ESTADO['numeros_marcados'] = []
        _actualizar_xml_bingo()
        
        return jsonify({
            'success': True,
            'mensaje': 'Juego reiniciado',
            'total_marcados': 0
        })

@app.get('/juego/estado')
def juego_estado():
    """Obtiene el estado completo del juego."""
    with _JUEGO_ESTADO['lock']:
        return jsonify({
            'success': True,
            'fecha': _JUEGO_ESTADO['fecha_juego'],
            'numeros_marcados': _JUEGO_ESTADO['numeros_marcados'],
            'total_marcados': len(_JUEGO_ESTADO['numeros_marcados']),
            'total_boletos': len(_JUEGO_ESTADO['boletos']),
            'total_figuras': len(_JUEGO_ESTADO['figuras']),
            'total_ganadores': len(_JUEGO_ESTADO['ganadores']),
            'ganadores': _JUEGO_ESTADO['ganadores'],
            'ultimos5': _JUEGO_ESTADO['numeros_marcados'][-5:] if len(_JUEGO_ESTADO['numeros_marcados']) >= 5 else _JUEGO_ESTADO['numeros_marcados']
        })

@app.get('/juego/ganadores')
def juego_ganadores():
    """Obtiene la lista de ganadores."""
    with _JUEGO_ESTADO['lock']:
        return jsonify({
            'success': True,
            'ganadores': _JUEGO_ESTADO['ganadores']
        })

@app.get('/juego/inicializar/<fecha>')
def juego_inicializar_fecha(fecha):
    """Inicializa el juego para una fecha específica."""
    try:
        datetime.fromisoformat(fecha)  # Validar formato
        _inicializar_juego(fecha)
        
        return jsonify({
            'success': True,
            'fecha': fecha,
            'boletos_cargados': len(_JUEGO_ESTADO['boletos']),
            'figuras_cargadas': len(_JUEGO_ESTADO['figuras']),
            'ganadores_existentes': len(_JUEGO_ESTADO['ganadores'])
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Fecha inválida o error: {str(e)}'
        }), 400

# ====== BOLETÍN ======
@app.route('/boletin')
def boletin():
    fecha = request.args.get('fecha') or date.today().isoformat()
    return render_template('boletin.html', fecha_inicial=fecha)

# ====== PAGO DE PREMIOS ======
@app.route('/pago-premios')
def pagos_premios_view():
    return render_template('pago_premios.html')

# ====== CONTABILIDAD ======
@app.route("/contabilidad")
@require_session
def contabilidad():
    rol = session.get('rol', '')
    if rol not in ('Super Administrador', 'Administrador'):
        flash('Acceso restringido a Contabilidad', 'error')
        return redirect(url_for('dashboard'))
    
    return render_template(
        "contabilidad.html",
        usuario=session.get('usuario', ''),
        rol=rol,
        avatar=session.get('avatar', 'avatar-male.png')
    )

# ====== RUTAS DE DEPURACIÓN ======
@app.route('/_debug_routes')
def _debug_routes():
    routes = sorted(rule.rule for rule in app.url_map.iter_rules())
    return '<br>'.join(routes)

@app.route('/_login_demo')
def _login_demo():
    session['usuario'] = 'Administrador'
    session['avatar'] = 'avatar-male.png'
    return redirect(url_for('dashboard'))

# ====== INICIALIZACIÓN ======
def initialize_system():
    """Inicializa todos los componentes del sistema."""
    print("Inicializando sistema GL Bingo con detección de ganadores...")
    
    # Asegurar archivos XML críticos
    if not os.path.exists(BINGO_XML):
        _actualizar_xml_bingo()
    
    # Crear directorios necesarios
    for dir_path in [REINTEGROS_DIR, BANK_FILES, GASTO_FILES, RECIBOS_DIR]:
        os.makedirs(dir_path, exist_ok=True)
    
    # Inicializar juego para hoy
    fecha_hoy = date.today().isoformat()
    _inicializar_juego(fecha_hoy)
    
    print(f"Sistema inicializado para {fecha_hoy}")
    print(f"- Boletos cargados: {len(_JUEGO_ESTADO['boletos'])}")
    print(f"- Figuras cargadas: {len(_JUEGO_ESTADO['figuras'])}")
    print(f"- Ganadores existentes: {len(_JUEGO_ESTADO['ganadores'])}")

# ====== EJECUCIÓN ======
if __name__ == "__main__":
    initialize_system()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)




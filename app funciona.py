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
from flask import Flask, request, render_template, send_file, redirect, url_for, flash, session, Response
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
DATA_DIR = os.environ.get("DATA_DIR") or ("/data" if os.path.isdir("/data") else os.path.join(BASE_DIR, "DATA"))
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
VENDEDORES_XML          = _persist('static', 'db', 'vendedores.xml')
DATOS_FIGURAS_XML         = _persist('static', 'db', 'datos_figuras.xml')
FIGURAS_FECHA_XML         = _persist('static', 'db', 'figuras_por_fecha.xml')
FIGURAS_DEL_DIA_XML       = _persist('static', 'db', 'figuras_del_dia.xml')

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
    ('static/db/vendedores.xml',           VENDEDORES_XML),
    ('static/db/datos_figuras.xml',          DATOS_FIGURAS_XML),
    ('static/db/figuras_por_fecha.xml',      FIGURAS_FECHA_XML),
    ('DATA/static/db/figuras_del_dia.xml',   FIGURAS_DEL_DIA_XML),
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

# Copiar un XML persistente a /static/db (compatibilidad con URLs antiguas y vMix)
def _mirror_db_to_public(persist_abs: str):
    try:
        if not persist_abs or not os.path.exists(persist_abs):
            return
        public_dir = os.path.join(BASE_DIR, "static", "db")
        os.makedirs(public_dir, exist_ok=True)
        shutil.copy2(persist_abs, os.path.join(public_dir, os.path.basename(persist_abs)))
    except Exception as e:
        print(f"[WARN] Mirror static/db falló para {persist_abs}: {e}")

# Asegurar que estos XML queden visibles también en /static/db al iniciar
for _p in [locals().get("CAJA_XML"), locals().get("ASIGNACIONES_XML"), locals().get("VENDEDORES_XML"), locals().get("DATOS_FIGURAS_XML"), locals().get("FIGURAS_FECHA_XML"), locals().get("FIGURAS_DEL_DIA_XML")]:
    if _p:
        _mirror_db_to_public(_p)

# ==== FIN PERSISTENCIA ====

# ==== ENLAZAR CARPETAS DEL REPO -> DISCO PERSISTENTE (/data) ====
import os, shutil

PERSIST_ROOT = DATA_DIR
os.makedirs(PERSIST_ROOT, exist_ok=True)

def _bind_dir(repo_rel):
    """
    Enlaza (opcionalmente) carpetas del repo hacia PERSIST_ROOT.

    ⚠️ Importante: **NO borra** carpetas del repo. Antes se hacía un rmtree() y,
    si el symlink fallaba (muy común en Windows), al reiniciar se perdían datos.

    - Siempre crea la carpeta persistente.
    - "Siembra" archivos del repo → persistente solo si persistente está vacío.
    - En Linux/Mac intenta reemplazar la carpeta del repo por un symlink de forma SEGURA
      (primero crea el link, luego hace swap con backup). En Windows no lo intenta.
    """
    repo_abs    = os.path.join(BASE_DIR, repo_rel)
    persist_abs = os.path.join(PERSIST_ROOT, repo_rel)
    os.makedirs(persist_abs, exist_ok=True)

    # Sembrar (solo primera vez)
    try:
        if os.path.isdir(repo_abs) and os.path.isdir(persist_abs) and not os.listdir(persist_abs):
            for name in os.listdir(repo_abs):
                src = os.path.join(repo_abs, name)
                dst = os.path.join(persist_abs, name)
                if os.path.isdir(src):
                    shutil.copytree(src, dst, dirs_exist_ok=True)
                elif os.path.isfile(src) and not os.path.exists(dst):
                    shutil.copy2(src, dst)
    except Exception as e:
        print("Seed warning:", repo_rel, e)

    # Symlink seguro (solo POSIX). Se puede desactivar con ENABLE_SYMLINK_BIND=0
    if os.name == "nt" or os.environ.get("ENABLE_SYMLINK_BIND", "1") == "0":
        return

    try:
        if os.path.islink(repo_abs):
            return

        # Crea primero un symlink temporal; si falla, no tocamos nada
        tmp_link = repo_abs + ".__linktmp__"
        if os.path.lexists(tmp_link):
            try:
                if os.path.islink(tmp_link) or os.path.isfile(tmp_link):
                    os.unlink(tmp_link)
                else:
                    shutil.rmtree(tmp_link)
            except Exception:
                pass

        os.makedirs(os.path.dirname(repo_abs), exist_ok=True)
        os.symlink(persist_abs, tmp_link, target_is_directory=True)

        # Swap seguro: mueve carpeta actual a backup y pone el symlink en su lugar
        if os.path.exists(repo_abs):
            import time
            backup = repo_abs + f".__backup__{int(time.time())}"
            os.rename(repo_abs, backup)

        os.rename(tmp_link, repo_abs)

    except Exception as e:
        # Si algo falla, intentamos limpiar el tmp_link
        try:
            if os.path.lexists(tmp_link):
                if os.path.islink(tmp_link) or os.path.isfile(tmp_link):
                    os.unlink(tmp_link)
                else:
                    shutil.rmtree(tmp_link)
        except Exception:
            pass
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
CAJA_XML              = globals().get('CAJA_XML',              _persist('static', 'db', 'caja.xml'))
VENDEDORES_XML        = globals().get('VENDEDORES_XML',        _persist('static', 'db', 'vendedores.xml'))
ASIGNACIONES_XML      = globals().get('ASIGNACIONES_XML',      _persist('static', 'db', 'asignaciones.xml'))
IMPRESION_LOG         = globals().get('IMPRESION_LOG',         _persist('static', 'IMPRESION', 'log.xml'))
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

######__________________impresiones _________________________________####
######__________________impresiones _________________________________####
######__________________impresiones _________________________________####
######__________________impresiones _________________________________####




# -*- coding: utf-8 -*-
######__________________impresiones _________________________________####

import os, random, csv, math, shutil, unicodedata, json
from io import BytesIO, StringIO
from datetime import datetime, date
from threading import RLock  # RLock para evitar deadlocks reentrantes

import pandas as pd
from flask import (
    Flask, request, send_file, render_template, redirect,
    url_for, flash, jsonify, session
)
from markupsafe import Markup
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
per_cell_offsets = {
    0: {"grid_x": -85, "grid_y": 20,  "info_x": 5,   "info_y": 20,  "rein_x": 215, "rein_y": 30},
    1: {"grid_x": -162, "grid_y":20,  "info_x": -70, "info_y": 20,  "rein_x": 140, "rein_y": 30},
    2: {"grid_x": -85, "grid_y": 85,  "info_x": 5,   "info_y": 82,  "rein_x": 215, "rein_y": -25},
    3: {"grid_x": -162, "grid_y":85,  "info_x": -70, "info_y": 82,  "rein_x": 140, "rein_y": -25},
    4: {"grid_x": -85, "grid_y": 143, "info_x": 5,   "info_y": 132, "rein_x": 215, "rein_y": -85},
    5: {"grid_x": -162, "grid_y":143, "info_x": -70, "info_y": 132, "rein_x": 140, "rein_y": -85},
    6: {"grid_x": -85, "grid_y": 205, "info_x": 5,   "info_y": 192, "rein_x": 215, "rein_y": -145},
    7: {"grid_x": -162, "grid_y":205, "info_x": -70, "info_y": 192, "rein_x": 140, "rein_y": -145},
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

# === columnas para BONUS en la tabla simple (CSV/HTML logs)===
_LOG_COLS = [
    "id","fecha_hora","usuario","tipo","serie_archivo","desde","hasta",
    "valor","telefono","fecha_sorteo","reintegro_especial",
    "cant_reintegro_especial","incluir_aleatorio",
    "fecha_planilla","total_boletos","total_planillas",
    "excedente","lote",
    # bonus:
    "bonus_enabled","bonus_code","bonus_numbers","bonus_winners"
]

def _append_log_impresion_boletos(
    *, usuario, serie_archivo, desde, hasta, fecha_sorteo, total_boletos,
    valor, telefono, reintegro_especial, cant_reintegro_especial,
    incluir_aleatorio, excedente=0, lote='',
    # paquete bonus opcional
    bonus_payload: dict | None = None
) -> int:
    """Devuelve el id (int) del log creado."""
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

        # Bloque BONUS dentro del XML (estructurado)
        if bonus_payload:
            add('bonus_enabled', '1')
            add('bonus_code', bonus_payload.get('code',''))
            add('bonus_numbers', ','.join(map(str, bonus_payload.get('numbers',[]))))
            # vista compacta:
            bw = bonus_payload.get('winners', {})
            parts = []
            for k in [5,4,3,2,1]:
                ids = bw.get(str(k), [])
                parts.append(f"{k}:[{','.join(map(str,ids))}]")
            add('bonus_winners', ';'.join(parts))

            bx = ET.SubElement(elem, 'bonus')
            bx.set('code', bonus_payload.get('code',''))
            bx.set('feasible', '1' if bonus_payload.get('feasible', True) else '0')
            ET.SubElement(bx, 'numbers').text = ','.join(map(str, bonus_payload.get('numbers',[])))
            req = bonus_payload.get('requested', {})
            ET.SubElement(bx, 'requested').text = json.dumps(req, ensure_ascii=False)
            win = bonus_payload.get('winners', {})
            for k in ['5','4','3','2','1']:
                ET.SubElement(bx, f"k{k}").text = ','.join(map(str, win.get(k, [])))
            sh = bonus_payload.get('shortages', {})
            if sh:
                ET.SubElement(bx, 'shortages').text = json.dumps(sh, ensure_ascii=False)

        root.append(elem)
        _write_logs_tree(tree)
        return next_id

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
    rol_raw = session.get('rol') or ''
    rol_n = _normalize(rol_raw)
    if rol_n in {'superadmin', 'super administrador', 'superadministrador'}:
        return True
    perms = session.get('permisos') or []
    try:
        perms_l = {_normalize(str(p)) for p in perms}
    except Exception:
        perms_l = set()
    if any(p in perms_l for p in {'superadmin', 'super administrador', 'superadministrador', 'delete logs', 'logs delete'}):
        return True
    usuario = (session.get('usuario') or '').strip().upper()
    if usuario == 'GLSTUDIOS':
        return True
    return False

if os.getenv('GLBINGO_DEBUG_SUPER') == '1':
    @app.route('/debug/make-superadmin')
    def _debug_make_superadmin():
        session['rol'] = 'Super Administrador'
        u = session.get('usuario') or 'GLSTUDIOS'
        session['usuario'] = u
        flash('Sesión marcada como SUPERADMIN (modo debug).', 'success')
        return redirect(url_for('impresion'))

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
      <table cellspacing="0" cellpadding="0" style="border-collapse:collapse;min-width:1400px">
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

# ---- Dibujo de la franja BONUS (5 cuadros bajo el reintegro)----
def _draw_bonus_franja(c: canvas.Canvas, x_left: float, y_top_rein: float, numbers: list[int]):
    """
    x_left, y_top_rein: esquina superior-izquierda del área del reintegro ya dibujado.
    Dibuja debajo 5 cuadros con los números BONUS centrados.
    """
    if not numbers:
        return
    box = 8.5  # puntos
    gap = 3.5
    total_w = 5*box + 4*gap
    x0 = x_left + (REINTEGRO_W - total_w) / 2.0
    y0 = y_top_rein - REINTEGRO_H - 10  # separación bajo el reintegro

    # Etiqueta "BONUS"
    c.setFont("Helvetica-Bold", 8.5)
    c.drawCentredString(x_left + REINTEGRO_W/2.0, y0 + box + 10, "BONUS")

    # Marcos + números
    c.setFont("Helvetica-Bold", 9)
    for idx, n in enumerate(numbers[:5]):
        xi = x0 + idx * (box + gap)
        yi = y0
        c.roundRect(xi, yi, box, box, 2, stroke=1, fill=0)
        c.drawCentredString(xi + box/2.0, yi + box/2.0 - 3, str(n))

def generar_pdf_boletos_excel(
    ids, registros, valor, telefono,
    nombre, reintegro_especial,
    cant_especial, reintegros,
    incluir_aleatorio, fecha_sorteo,
    # puedes pasar un set global o una lista por boleto
    bonus_numbers_global: list[int] | None = None,
    bonus_numbers_per_ticket: list[list[int]] | None = None,
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

            rein_x = x0 + offs['rein_x']
            rein_y_top = y0 - offs['rein_y']  # Y superior

            if img:
                path_img = os.path.join(REINTEGROS_DIR, img)
                _safe_draw_image(c, path_img, rein_x, rein_y_top, REINTEGRO_W, REINTEGRO_H)

            # ---- BONUS debajo del reintegro ----
            bn = None
            if bonus_numbers_per_ticket and pos < len(bonus_numbers_per_ticket):
                bn = bonus_numbers_per_ticket[pos]
            elif bonus_numbers_global:
                bn = bonus_numbers_global
            if bn:
                _draw_bonus_franja(c, rein_x, rein_y_top, bn)

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
    QR_SIZE_HDR          = 56
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

    fecha_limpia = dt.strftime("%Y%m%d")
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

# =============== BONUS: utilidades ===================

def _bonus_assign_by_number(ids: list[str], base_numbers: list[int], quotas: dict[int, int]):
    """
    Asigna franjas BONUS por número específico.
    base_numbers: lista de números (1..75) escogidos para el BONUS del día.
    quotas: dict {numero: cantidad_de_ganadores} -> cuántos boletos deberán incluir ese número en su franja.
    Reglas:
      - Los boletos asignados a un número b reciben 5 números que incluyen b.
      - El resto de boletos recibe 5 números que evitan todos los base_numbers.
    Devuelve: {"per_ticket": {idx:[..5..]}, "by_number": {"14":[ID,...]}, "feasible":bool, "shortages":{num:faltantes}}
    """
    import random
    rng_all = set(range(1, 76))
    base_set = set(int(n) for n in base_numbers if 1 <= int(n) <= 75)
    quotas = {int(k): max(0, int(v)) for k, v in quotas.items() if int(k) in base_set}

    libres = list(range(len(ids)))
    per_ticket = {}
    by_number = {}
    shortages = {}
    feasible = True

    def vec_con_b(b: int):
        pool = list((rng_all - base_set) - {b})
        if len(pool) < 4:
            pool = list(rng_all - {b})
        extra = set(random.sample(pool, 4))
        vec = sorted(set([b]) | extra)
        while len(vec) < 5:
            x = random.choice(list(rng_all - set(vec)))
            vec.append(x)
            vec = sorted(set(vec))
        return vec[:5]

    def vec_sin_bases():
        pool = list(rng_all - base_set)
        if len(pool) < 5:
            pool = list(rng_all)
        vec = sorted(set(random.sample(pool, 5)))
        while len(vec) < 5:
            x = random.choice(list(rng_all - set(vec)))
            vec.append(x)
            vec = sorted(set(vec))
        # reemplaza bases si se colaron
        for i,n in enumerate(list(vec)):
            if n in base_set:
                repl = list((rng_all - set(vec)) - base_set) or list(rng_all - set(vec))
                if repl:
                    vec[i] = random.choice(repl)
        return sorted(vec)

    for b in base_numbers:
        q = int(quotas.get(int(b), 0))
        if q <= 0:
            continue
        if len(libres) < q:
            feasible = False
            shortages[int(b)] = q - len(libres)
            q = len(libres)
        elegidos = random.sample(libres, q) if q > 0 else []
        by_number[str(int(b))] = [ids[i] for i in elegidos]
        for i in elegidos:
            per_ticket[i] = vec_con_b(int(b))
        libres = [i for i in libres if i not in elegidos]

    for i in libres:
        per_ticket[i] = vec_sin_bases()

    return {
        "per_ticket": per_ticket,
        "by_number": by_number,
        "feasible": feasible,
        "shortages": shortages
    }


def _row_numbers_as_set(row: dict) -> set[int]:
    """
    Toma una fila (registro) con claves b1..b5, i1..i5, n1..n5, g1..g5, o1..o5 y devuelve un set de ints válidos.
    Ignora vacíos o no-numéricos. (Incluye N3 aunque visualmente sea QR).
    """
    nums = set()
    for letra in 'bingo':
        for r in range(1,6):
            key = f"{letra}{r}"
            v = str(row.get(key,"")).strip()
            if not v:
                continue
            try:
                n = int(v)
                if 1 <= n <= 75:
                    nums.add(n)
            except Exception:
                continue
    return nums

def _bonus_try_assign(registros: list[dict], ids: list[str], requested: dict[str,int], max_iters: int = 3000):
    """
    (Modo antiguo - set global aleatorio). Se mantiene por compatibilidad.
    """
    tickets = [_row_numbers_as_set(r) for r in registros]

    best = None
    req = {int(k): max(0, int(v)) for k,v in requested.items() if str(k) in {'1','2','3','4','5'}}

    for _ in range(max_iters):
        bonus = set(random.sample(range(1,76), 5))
        matches = [len(s & bonus) for s in tickets]

        pool = {k: [i for i, m in enumerate(matches) if m == k] for k in range(6)}  # 0..5
        winners = {}
        feasible = True
        shortages = {}
        satisfied = 0
        for k in [5,4,3,2,1]:
            want = req.get(k, 0)
            candidates = pool.get(k, [])
            if want <= 0:
                winners[str(k)] = []
                continue
            if len(candidates) >= want:
                chosen = random.sample(candidates, want)
                winners[str(k)] = [ids[i] for i in chosen]
                satisfied += want
            else:
                feasible = False
                winners[str(k)] = [ids[i] for i in candidates]
                satisfied += len(candidates)
                shortages[k] = want - len(candidates)

        result = {
            "numbers": sorted(list(bonus)),
            "winners": winners,
            "feasible": feasible,
            "shortages": shortages,
            "score": satisfied
        }
        if feasible:
            return result
        if (best is None) or (result["score"] > best["score"]):
            best = result

    return best or {
        "numbers": [],
        "winners": {str(k): [] for k in [5,4,3,2,1]},
        "feasible": False,
        "shortages": {k: requested.get(str(k),0) for k in [5,4,3,2,1]},
        "score": 0
    }

# ====== NUEVO: Asignación POR BOLETO (cuando NO hay bonus global ingresado por el usuario) ======
def _bonus_assign_per_ticket(registros: list[dict], ids: list[str], requested: dict[str,int]):
    """
    Genera números BONUS distintos por boleto cumpliendo el conteo solicitado
    de ganadores por coincidencias exactas k=5..1. Si sobran boletos, se asigna k=0.
    Retorna:
      {
        "per_ticket": [[5 nums], ...]  # alineado a 'ids'
        "winners": {"5":[ids], ...},
        "feasible": True/False,
        "shortages": {k: faltantes}
      }
    """
    N = len(registros)
    rng_all = set(range(1, 76))
    ticket_sets = [_row_numbers_as_set(r) for r in registros]

    per_ticket = [None] * N
    remaining = list(range(N))
    random.shuffle(remaining)

    winners = {str(k): [] for k in [5,4,3,2,1]}
    shortages = {}
    feasible = True
    used_sets = set()  # para evitar duplicados exactos

    def build_set(S, k):
        # k de S, 5-k fuera de S
        A = set(random.sample(list(S), k)) if k > 0 else set()
        pool_out = list(rng_all - S - A)
        B = set(random.sample(pool_out, 5 - k)) if 5 - k > 0 else set()
        return tuple(sorted(A | B))

    # Asigna exactamente los requeridos por categoría
    for k in [5,4,3,2,1]:
        want = max(0, int(requested.get(str(k), 0)))
        if want == 0:
            continue
        # candidatos que todavía no se usaron y tienen al menos k números
        cands = [i for i in remaining if len(ticket_sets[i]) >= k]
        if len(cands) < want:
            feasible = False
            shortages[k] = want - len(cands)
            want = len(cands)
        chosen = random.sample(cands, want)
        for i in chosen:
            # intenta evitar repetir exactamente el mismo set
            tries = 0
            s = build_set(ticket_sets[i], k)
            while s in used_sets and tries < 10:
                s = build_set(ticket_sets[i], k)
                tries += 1
            used_sets.add(s)
            per_ticket[i] = list(s)
            winners[str(k)].append(ids[i])
        remaining = [i for i in remaining if i not in chosen]

    # El resto con k=0 (cero coincidencias), igualmente variados
    for i in remaining:
        tries = 0
        s = build_set(ticket_sets[i], 0)
        while s in used_sets and tries < 10:
            s = build_set(ticket_sets[i], 0)
            tries += 1
        used_sets.add(s)
        per_ticket[i] = list(s)

    return {
        "per_ticket": per_ticket,
        "winners": winners,
        "feasible": feasible,
        "shortages": shortages
    }

# ====== NUEVO: Asignación desde BONUS GLOBAL con EXACTO k aciertos por boleto ======
def _bonus_assign_from_global(registros: list[dict], ids: list[str], global_numbers: list[int], requested: dict[str,int]):
    """
    Usa un set BONUS GLOBAL de 5 números (p.ej., [25,44,10,8,12]) y reparte ganadores.
    Para cada categoría k=5..1:
      - Elige boletos candidatos.
      - Genera para ese boleto una franja BONUS de 5 números que contenga EXACTAMENTE k
        números del BONUS global que estén también en el boleto, y (5-k) 'distractores'
        que NO estén en el boleto (ni en el set global) para NO completar 5 aciertos.
    Devuelve:
      {
        "per_ticket": [[5 nums], ...]  # alineado a 'ids'
        "winners": {"5":[ids], ...},
        "feasible": True/False,
        "shortages": {k: faltantes}
      }
    """
    # Normaliza y valida BONUS:
    try:
        B = [int(x) for x in global_numbers]
    except Exception:
        B = []
    B = [n for n in B if 1 <= n <= 75]
    if len(set(B)) != 5:
        # BONUS inválido
        return {
            "per_ticket": [[None]*5 for _ in registros],
            "winners": {str(k): [] for k in [5,4,3,2,1]},
            "feasible": False,
            "shortages": {"bonus_numbers": "Se requieren 5 números únicos entre 1..75"}
        }

    Bset = set(B)
    N = len(registros)
    ticket_sets = [_row_numbers_as_set(r) for r in registros]

    per_ticket = [None] * N
    remaining = list(range(N))
    random.shuffle(remaining)

    winners = {str(k): [] for k in [5,4,3,2,1]}
    shortages = {}
    feasible = True
    used_vectors = set()

    rng_all = set(range(1, 76))

    def build_vector_for_ticket(i, k):
        """
        Devuelve una tupla de 5 números para el boleto i con EXACTAMENTE k aciertos:
        - k números tomados de (B ∩ ticket_i)
        - (5-k) distractores tomados de números que NO están en el boleto y NO están en B.
        Evita repetir exactamente la misma tupla en muchos boletos.
        """
        S = ticket_sets[i]
        common = list(Bset & S)
        if len(common) < k:
            return None
        # Elige k comunes
        A = set(random.sample(common, k)) if k > 0 else set()
        # Pool de distractores: fuera del boleto y fuera del BONUS global
        pool_out = list(rng_all - S - Bset - A)
        if len(pool_out) < (5 - k):
            # si faltan, relajamos: permitimos fuera del boleto aunque estén en Bset,
            # pero intentando NO sumar más aciertos (ya excluimos S)
            pool_out = list(rng_all - S - A)
        if len(pool_out) < (5 - k):
            return None
        B_extra = set(random.sample(pool_out, 5 - k))
        vec = tuple(sorted(A | B_extra))
        return vec

    # Asigna categorías 5→1
    for k in [5,4,3,2,1]:
        want = max(0, int(requested.get(str(k), 0)))
        if want == 0:
            continue
        # Candidatos: aún no asignados y con al menos k coincidencias posibles con B
        cands = [i for i in remaining if len(ticket_sets[i] & Bset) >= k]
        if len(cands) < want:
            feasible = False
            shortages[k] = want - len(cands)
            want = len(cands)
        if want <= 0:
            continue
        chosen = random.sample(cands, want)
        for i in chosen:
            tries = 0
            vec = build_vector_for_ticket(i, k)
            while (vec is None or vec in used_vectors) and tries < 20:
                vec = build_vector_for_ticket(i, k)
                tries += 1
            if vec is None:
                feasible = False
                shortages[k] = shortages.get(k, 0) + 1
                continue
            used_vectors.add(vec)
            per_ticket[i] = list(vec)
            winners[str(k)].append(ids[i])
        remaining = [i for i in remaining if i not in chosen]

    # El resto (no ganadores): si B choca con el boleto, armamos 0 aciertos
    for i in remaining:
        S = ticket_sets[i]
        if len(Bset & S) == 0:
            vec = B[:]  # puede mostrarse tal cual (0 aciertos reales)
        else:
            pool_out = list(rng_all - S - Bset)
            if len(pool_out) < 5:
                pool_out = list(rng_all - S)
            vec = random.sample(pool_out, 5)
        per_ticket[i] = list(sorted(vec))

    return {
        "per_ticket": per_ticket,
        "winners": winners,
        "feasible": feasible,
        "shortages": shortages
    }

def _save_bonus_json(log_id: int, payload: dict):
    try:
        path = os.path.join(LOGS_DIR, f"bonus_{log_id}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("[WARN] No se pudo escribir bonus json:", e)

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

        # === BONUS: lectura del formulario
        bonus_enabled = (request.form.get('bonus_enabled') or '').lower() in ('1','true','on','si','sí')
        b5 = _to_int(request.form.get('bonus_k5'), 0)
        b4 = _to_int(request.form.get('bonus_k4'), 0)
        b3 = _to_int(request.form.get('bonus_k3'), 0)
        b2 = _to_int(request.form.get('bonus_k2'), 0)
        b1 = _to_int(request.form.get('bonus_k1'), 0)
        requested_counts = {'5': b5, '4': b4, '3': b3, '2': b2, '1': b1}

        # cuotas por NÚMERO (bonus_q1..bonus_q5 alineadas a bonus_n1..bonus_n5)
        quotas_by_number = {}
        for idx in [1,2,3,4,5]:
            nv = request.form.get(f'bonus_n{idx}')
            qv = request.form.get(f'bonus_q{idx}')
            try:
                nvi = int(str(nv).strip()) if nv not in (None, '') else None
                qvi = int(str(qv).strip()) if qv not in (None, '') else 0
            except Exception:
                nvi, qvi = None, 0
            if nvi is not None and 1 <= nvi <= 75 and qvi > 0:
                quotas_by_number[nvi] = qvi

        # BONUS GLOBAL (opcional): bonus_n1..bonus_n5
        bonus_n_inputs = []
        for k in [1,2,3,4,5]:
            v = request.form.get(f'bonus_n{k}')
            if v is not None and str(v).strip() != '':
                try:
                    bonus_n_inputs.append(int(str(v).strip()))
                except Exception:
                    pass

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

        # === BONUS: cálculo y log preparado
        bonus_payload = None
        bonus_numbers_global = None
        bonus_numbers_per_ticket = None

        if bonus_enabled:
            # === MODO POR NÚMERO ===
            if quotas_by_number:
                base_nums = [n for n in bonus_n_inputs if 1 <= n <= 75]
                base_nums = list(dict.fromkeys(base_nums))[:5]
                assign_num = _bonus_assign_by_number(ids, base_nums, quotas_by_number)
                bonus_numbers_per_ticket = assign_num["per_ticket"]
                bonus_payload = {
                    "enabled": True,
                    "mode": "per_number",
                    "code": f"BNS-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{random.randint(1000,9999)}",
                    "numbers": base_nums,
                    "requested": quotas_by_number,
                    "winners_by_number": assign_num.get("by_number", {}),
                    "feasible": assign_num.get("feasible", True),
                    "shortages": assign_num.get("shortages", {})
                }
                if not assign_num.get("feasible", True):
                    flash("BONUS por número: algunas cuotas no pudieron cubrirse completamente; se asignó lo máximo posible.", "warning")
            # Si el usuario ingresó los 5 números, seguir MODO GLOBAL:
            if len(set([n for n in bonus_n_inputs if 1 <= n <= 75])) == 5:
                global_bonus = list(dict.fromkeys([n for n in bonus_n_inputs if 1 <= n <= 75]))[:5]
                assign_glob = _bonus_assign_from_global(registros, ids, global_bonus, requested_counts)
                bonus_numbers_per_ticket = assign_glob["per_ticket"]
                bonus_payload = {
                    "enabled": True,
                    "mode": "global",
                    "code": f"BNS-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{random.randint(1000,9999)}",
                    "numbers": global_bonus,  # guardamos el BONUS base
                    "requested": requested_counts,
                    "winners": assign_glob["winners"],
                    "feasible": assign_glob["feasible"],
                    "shortages": assign_glob.get("shortages", {})
                }
                if not assign_glob["feasible"]:
                    flash("BONUS: no fue posible cumplir exactamente todas las cantidades solicitadas (modo global); se asignó lo máximo posible.", "warning")
            else:
                # Si NO ingresó los 5, usar el modo per-ticket (compatible)
                assign_pt = _bonus_assign_per_ticket(registros, ids, requested_counts)
                bonus_numbers_per_ticket = assign_pt["per_ticket"]
                bonus_payload = {
                    "enabled": True,
                    "mode": "global",
                    "code": f"BNS-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{random.randint(1000,9999)}",
                    "numbers": [],  # per-ticket (no global)
                    "requested": requested_counts,
                    "winners": assign_pt["winners"],
                    "feasible": assign_pt["feasible"],
                    "shortages": assign_pt.get("shortages", {})
                }
                if not assign_pt["feasible"]:
                    flash("BONUS: no fue posible cumplir exactamente todas las cantidades solicitadas; se asignó lo máximo posible.", "warning")

        try:
            log_id = _append_log_impresion_boletos(
                usuario=session.get('usuario', ''),
                serie_archivo=serie_archivo,
                desde=start, hasta=end,
                fecha_sorteo=fecha_str,
                total_boletos=len(ids),
                valor=valor, telefono=telefono,
                reintegro_especial=rein_esp,
                cant_reintegro_especial=cntesp,
                incluir_aleatorio=incA,
                bonus_payload=bonus_payload
            )
        except Exception as e:
            print('[WARN] No se pudo escribir en impresiones.xml (boletos):', e)
            log_id = None

        # Guarda JSON del informe BONUS (si aplica)
        if bonus_payload and log_id:
            try:
                bonus_payload_out = dict(bonus_payload)
                bonus_payload_out["log_id"] = log_id
                bonus_payload_out["serie_archivo"] = serie_archivo
                bonus_payload_out["desde"] = start
                bonus_payload_out["hasta"] = end
                bonus_payload_out["fecha_sorteo"] = fecha_str
                _save_bonus_json(log_id, bonus_payload_out)
                # Link al HTML con el resultado del BONUS
                flash(Markup(
                    f"BONUS asignado | Informe ID {log_id}. "
                    f"<a href='{url_for('bonus_informe_html', log_id=log_id)}' target='_blank'>Ver BONUS</a>"
                ), "success")
            except Exception as e:
                print("[WARN] No se pudo guardar JSON BONUS:", e)

        rein_list = sorted(f for f in os.listdir(REINTEGROS_DIR) if f.lower().endswith('.png')) if os.path.exists(REINTEGROS_DIR) else []
        buf_b = generar_pdf_boletos_excel(
            ids, registros, valor, telefono,
            serie_archivo, rein_esp, cntesp,
            rein_list, incA, fecha_str,
            bonus_numbers_global=bonus_numbers_global,
            bonus_numbers_per_ticket=bonus_numbers_per_ticket
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

        try:
            _append_log_impresion_planilla(
                usuario=session.get('usuario',''),
                serie_archivo=archivo,
                desde=inicio, hasta=fin,
                fecha_planilla=fecha_p,
                lote_text=f"{inicio}-{fin}",
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

    # ZIP (sin cálculo de BONUS en este atajo; se imprimen sin franja BONUS)
    buf_boletos = generar_pdf_boletos_excel(
        ids, registros, valor, telefono,
        nombre_serie, rein_esp, cnt_esp,
        rein_list, incA, fecha_str,
        bonus_numbers_global=None,
        bonus_numbers_per_ticket=None
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

# ===== Endpoint para ver el informe BONUS de una impresión =====
@app.route('/impresion/bonus-informe/<int:log_id>.json')
@require_session
def bonus_informe(log_id: int):
    path = os.path.join(LOGS_DIR, f"bonus_{log_id}.json")
    if not os.path.exists(path):
        return jsonify(ok=False, error="informe no encontrado"), 404
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return jsonify(ok=True, informe=data)
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 500

# ===== VISTA HTML del BONUS =====
@app.route('/impresion/bonus-informe/<int:log_id>')
@require_session
def bonus_informe_html(log_id: int):
    path = os.path.join(LOGS_DIR, f"bonus_{log_id}.json")
    if not os.path.exists(path):
        return f"<h3 style='font-family:Arial'>No existe informe BONUS {log_id}</h3>", 404
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        return f"<h3 style='font-family:Arial'>Error leyendo informe: {e}</h3>", 500

    winners = data.get("winners", {})
    requested = data.get("requested", {})
    feasible = data.get("feasible", True)
    shortages = data.get("shortages", {})
    nums = data.get("numbers", [])

    rows = []
    for k in [5,4,3,2,1]:
        want = int(requested.get(str(k), 0) or 0)
        got = len(winners.get(str(k), []))
        ids_str = ", ".join(map(str, winners.get(str(k), [])))
        rows.append(f"<tr><td>{k}</td><td>{want}</td><td>{got}</td><td style='max-width:800px;white-space:normal'>{ids_str}</td></tr>")

    base = f"<p><b>Bonus Global:</b> {', '.join(map(str, nums))}</p>" if nums else "<p><b>Bonus por boleto (no global).</b></p>"

    return f"""
    <html>
      <head>
        <meta charset='utf-8'>
        <title>Informe BONUS #{log_id}</title>
        <style>
          body {{ font-family: Arial, Helvetica, sans-serif; margin: 24px; }}
          table {{ border-collapse: collapse; width: 100%; max-width: 1200px; }}
          th, td {{ border: 1px solid #ddd; padding: 8px; }}
          th {{ background: #f3f3f3; }}
          .pill {{ display:inline-block; padding:4px 10px; border-radius:999px; background:#eee; margin-left:10px; font-size:12px; }}
        </style>
      </head>
      <body>
        <h2>Informe BONUS #{log_id}
          <span class="pill">{'FACTIBLE' if feasible else 'NO FACTIBLE'}</span>
        </h2>
        {base}
        <p><b>Código:</b> {data.get('code','')}</p>
        <table>
          <tr><th>Coincidencias</th><th>Solicitados</th><th>Asignados</th><th>Boletos ganadores (IDs)</th></tr>
          {''.join(rows)}
        </table>
        { (lambda wins_by: (
            "<h3>Ganadores por número</h3><table><tr><th>Número</th><th>Boletos</th></tr>" +
            "".join(f"<tr><td>{k}</td><td>{', '.join(v)}</td></tr>" for k,v in wins_by.items()) +
            "</table>"
            ) if wins_by else ""
          )(data.get('winners_by_number', {})) }
    
        {"<p style='color:#b00'><b>Faltantes:</b> " + ", ".join(f"{k}:{v}" for k,v in shortages.items()) + "</p>" if shortages else ""}
      </body>
    </html>
    """





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




VENDEDORES_XML = _persist('static', 'db', 'vendedores.xml')
ASIGNACIONES_XML = _persist('static', 'db', 'asignaciones.xml')
BOLETOS_POR_PLANILLA = 30  # Cambia esto según tus necesidades

# ----------- FUNCIONES PARA VENDEDORES -----------

# ============================================================
#  RUTAS Y CONSTANTES (tus líneas originales, no se tocan)
# ============================================================
VENDEDORES_XML = _persist('static', 'db', 'vendedores.xml')
ASIGNACIONES_XML = _persist('static', 'db', 'asignaciones.xml')
BOLETOS_POR_PLANILLA = 30  # Cambia esto según tus necesidades

# ----------- FUNCIONES PARA VENDEDORES -----------
# (mantengo tu reasignación exacta, como la tienes)
VENDEDORES_XML = globals().get('VENDEDORES_XML', _persist('static', 'db', 'vendedores.xml'))


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
    _mirror_persist_static_to_public(path)


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
VENDEDORES_XML       = globals().get('VENDEDORES_XML',       _persist('static', 'db', 'vendedores.xml'))
ASIGNACIONES_XML     = globals().get('ASIGNACIONES_XML',     _persist('static', 'db', 'asignaciones.xml'))
IMPRESIONES_XML      = globals().get('IMPRESIONES_XML',      _persist('static', 'LOGS', 'impresiones.xml'))  # ← LOG de impresión  # ← LOG de impresión
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

def guardar_asignaciones(tree: ET.ElementTree):
    """Guarda asignaciones en forma segura (escritura atómica) y espeja a /static/db."""
    try:
        _write_xml_atomic(tree, ASIGNACIONES_XML)
    except Exception:
        # fallback: escritura directa (último recurso)
        try:
            ET.indent(tree, space="  ", level=0)  # type: ignore[attr-defined]
        except Exception:
            pass
        tree.write(ASIGNACIONES_XML, encoding='utf-8', xml_declaration=True)
    try:
        _mirror_db_to_public(ASIGNACIONES_XML)
    except Exception:
        pass

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
CAJA_XML = globals().get('CAJA_XML', _persist('static', 'db', 'caja.xml'))
os.makedirs(os.path.dirname(CAJA_XML), exist_ok=True)
if not os.path.exists(CAJA_XML):
    ET.ElementTree(ET.Element('caja')).write(CAJA_XML, encoding='utf-8', xml_declaration=True)

# Si estos símbolos no existen en este módulo, los definimos aquí
if 'VENDEDORES_XML' not in globals():
    VENDEDORES_XML = _persist('static', 'db', 'vendedores.xml')
if 'ASIGNACIONES_XML' not in globals():
    ASIGNACIONES_XML = _persist('static', 'db', 'asignaciones.xml')
if 'BOLETOS_POR_PLANILLA' not in globals():
    BOLETOS_POR_PLANILLA = 30

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
    _mirror_persist_static_to_public(path)

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
    """Crea/actualiza un <cobro> dentro del día indicado.

    Guarda también metadatos para auditoría:
      - creado_por / creado_rol / creado_ip / creado_en (solo si no existían)
      - actualizado_por / actualizado_ip / actualizado_en (siempre)
      - snapshot de configuración (si viene en datos)
    """
    t, r = _leer_xml(CAJA_XML)
    dia = _get_dia(r, fecha_str)
    cobros = _get_cobros_node(dia)
    node = cobros.find(f"./cobro[@seudonimo='{seudonimo}']") or ET.SubElement(cobros, 'cobro', seudonimo=seudonimo)

    now = datetime.now()
    # ID estable (por día+vendedor)
    if not node.get("id"):
        node.set("id", f"{fecha_str}__{seudonimo}")

    node.set('devueltos',     str(int(datos.get('devueltos', 0))))
    node.set('vendidos',      str(int(datos.get('vendidos', 0))))
    node.set('total_pagar',   f"{float(datos.get('total_pagar', 0)):.2f}")
    node.set('transferencia', f"{float(datos.get('transferencia', 0)):.2f}")
    node.set('efectivo',      f"{float(datos.get('efectivo', 0)):.2f}")
    node.set('pagado',        '1' if datos.get('pagado', True) else '0')
    node.set('fecha_hora',    datos.get('fecha_hora', now.strftime('%Y-%m-%d %H:%M:%S')))

    # Snapshot (si se envía)
    for k in ("valor_boleto", "comision_vendedor", "comision_extra_meta", "meta_boletos"):
        if k in datos and datos.get(k) is not None:
            node.set(k, str(datos.get(k)))

    # Metadatos: creador (solo una vez)
    if not node.get("creado_en"):
        node.set("creado_en", datos.get("creado_en") or now.isoformat(timespec="seconds"))
    if not node.get("creado_por"):
        node.set("creado_por", datos.get("creado_por") or (session.get("usuario") if session else "") or "")
    if not node.get("creado_rol"):
        node.set("creado_rol", datos.get("creado_rol") or (session.get("rol") if session else "") or "")
    if not node.get("creado_ip"):
        node.set("creado_ip", datos.get("creado_ip") or (request.remote_addr if request else "") or "")

    # Metadatos: actualización (siempre)
    node.set("actualizado_en", now.isoformat(timespec="seconds"))
    node.set("actualizado_por", (session.get("usuario") if session else "") or (datos.get("creado_por") or ""))
    node.set("actualizado_ip", (request.remote_addr if request else "") or "")

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
        transferencia = float(j.get('transferencia', 0))
        efectivo      = float(j.get('efectivo', 0))
        # Total pagado se calcula en servidor para evitar inconsistencias
        total_pagar   = round(transferencia + efectivo, 2)

        cfg = get_configuracion_dia(fecha_actual)

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

                # Snapshot config (contabilidad exacta aunque cambies el % después)
                "valor_boleto": cfg.get("valor_boleto"),
                "comision_vendedor": cfg.get("comision_vendedor"),
                "comision_extra_meta": cfg.get("comision_extra_meta"),
                "meta_boletos": cfg.get("meta_boletos"),

                # Auditoría
                "creado_por": session.get("usuario", ""),
                "creado_rol": session.get("rol", ""),
                "creado_ip": request.remote_addr or "",
                "creado_en": datetime.now().isoformat(timespec="seconds"),
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
if False and __name__ == "__main__":  # DESHABILITADO (evita arrancar antes de cargar rutas)
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

FIGURAS_XML = globals().get("DATOS_FIGURAS_XML") or os.path.join(globals().get("DATA_DIR", BASE_DIR), "static", "db", "datos_figuras.xml")
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
    _mirror_db_to_public(FIGURAS_XML)

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
    _mirror_db_to_public(FIGURAS_XML)

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
    _mirror_db_to_public(FIGURAS_XML)

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

FIGURAS_FECHA_XML = globals().get("FIGURAS_FECHA_XML") or os.path.join(globals().get("DATA_DIR", BASE_DIR), "static", "db", "figuras_por_fecha.xml")
os.makedirs(os.path.dirname(FIGURAS_FECHA_XML), exist_ok=True)

def _ensure_agenda_root():
    if not os.path.exists(FIGURAS_FECHA_XML):
        ET.ElementTree(ET.Element("agenda")).write(FIGURAS_FECHA_XML, encoding="utf-8", xml_declaration=True)
        _mirror_db_to_public(FIGURAS_FECHA_XML)
        return
    try:
        ET.parse(FIGURAS_FECHA_XML)
    except ET.ParseError:
        ET.ElementTree(ET.Element("agenda")).write(FIGURAS_FECHA_XML, encoding="utf-8", xml_declaration=True)
        _mirror_db_to_public(FIGURAS_FECHA_XML)

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
    _mirror_db_to_public(FIGURAS_FECHA_XML)

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

from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for

# ReportLab
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader  # tamaño real del logo

# ------------------ App ------------------
try:
    app  # noqa: F821
except NameError:

    app.secret_key = "dev"

# ------------------ Ajustes visuales ------------------
FIG_BLOCK_SCALE       = 0.99  # escala global de las figuras
FIG_FIXED_COLS        = 8     # columnas por fila para figuras (auto si None)
LOGO_SCALE_DEFAULT    = 1.30  # escala del logo (1.0 = normal)

# ------------------ Paths ------------------
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
DB_DIR     = os.path.join(STATIC_DIR, "db")
IMG_DIR    = os.path.join(STATIC_DIR, "img")
FONTS_DIR  = os.path.join(STATIC_DIR, "fonts")
LOGS_DIR   = os.path.join(STATIC_DIR, "LOGS")

for p in (DB_DIR, IMG_DIR, FONTS_DIR):
    os.makedirs(p, exist_ok=True)

# XMLs base
FIGURAS_FECHA_XML  = os.path.join(DB_DIR, "figuras_por_fecha.xml")
DATOS_FIGURAS_XML  = os.path.join(DB_DIR, "datos_figuras.xml")
RESULTADOS_XML     = os.path.join(DB_DIR, "resultados_sorteo.xml")

# Layout JSON (diseñador)
LAYOUT_JSON = os.path.join(DB_DIR, "boletin_layout.json")

# ------------------ Helpers ------------------
def _is_fecha_iso(s: str) -> bool:
    return bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", (s or "").strip()))

def _money(v):
    try:
        return f"${float(v):,.2f}"
    except Exception:
        return "$0.00"

def _money_header(v):
    try:
        return f"${int(round(float(v))):,}".replace(",", ",")
    except Exception:
        return "$0"

def _safe_text(s, font_name):
    s = "" if s is None else str(s)
    if font_name != "Helvetica":
        return s
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")

def _es_largo(fecha_iso: str) -> str:
    meses = ["enero","febrero","marzo","abril","mayo","junio","julio","agosto","septiembre","octubre","noviembre","diciembre"]
    dias  = ["lunes","martes","miércoles","jueves","viernes","sábado","domingo"]
    d = datetime.fromisoformat(fecha_iso).date()
    return f"{dias[d.weekday()].upper()}, {d.day} DE {meses[d.month-1].upper()} DE {d.year}"

def _es_corta(fecha_iso: str) -> str:
    meses = ["enero","febrero","marzo","abril","mayo","junio","julio","agosto","septiembre","octubre","noviembre","diciembre"]
    dias  = ["lunes","martes","miércoles","jueves","viernes","sábado","domingo"]
    d = datetime.fromisoformat(fecha_iso).date()
    return f"{dias[d.weekday()]}, {d.day} de {meses[d.month-1]} de {d.year}"

def _ensure_xml(path, root_name):
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        ET.ElementTree(ET.Element(root_name)).write(path, encoding="utf-8", xml_declaration=True)
        return
    try:
        ET.parse(path)
    except ET.ParseError:
        ET.ElementTree(ET.Element(root_name)).write(path, encoding="utf-8", xml_declaration=True)

# ------------------ Agenda / Figuras por fecha ------------------
def _figuras_de_fecha(fecha_iso):
    if not _is_fecha_iso(fecha_iso):
        return []
    _ensure_xml(FIGURAS_FECHA_XML, "agenda")
    root = ET.parse(FIGURAS_FECHA_XML).getroot()
    for d in root.findall("dia"):
        if d.attrib.get("fecha") == fecha_iso:
            out = []
            for f in d.findall("fig"):
                nom = (f.attrib.get("nombre") or "").strip()
                try:
                    val = float(f.attrib.get("valor") or 0.0)
                except Exception:
                    val = 0.0
                if nom:
                    out.append({"nombre": nom, "valor": val})
            return out
    return []

# ------------------ Formas 5x5 ------------------
def _load_shapes():
    shapes = {}
    if not os.path.exists(DATOS_FIGURAS_XML):
        return shapes
    try:
        root = ET.parse(DATOS_FIGURAS_XML).getroot()
    except ET.ParseError:
        return shapes
    for n in root.findall("figura"):
        nombre = (n.attrib.get("nombre", "") or "").strip()
        if not nombre:
            continue
        arr = [False] * 25
        for i in range(1, 26):
            cel = n.find(f'celda[@idx="{i}"]')
            if cel is not None:
                col = (cel.attrib.get("color", "#FFFFFF") or "").upper()
                arr[i - 1] = (col == "#FF0000")
        arr[12] = False  # centro libre
        shapes[nombre.strip().lower()] = arr
    return shapes

# ------------------ Resultados (XML) ------------------
# ===================== BOLETÍN: RUTAS ROBUSTAS (LOCAL/RENDER) =====================
# Objetivo:
#  - Guardar/leer resultados SIEMPRE desde una ruta consistente
#  - Escribir en DATA_DIR/static/db (persistente) y también "espejar" en BASE_DIR/static/db (para que lo veas en tu carpeta)
#  - Si no existe día en resultados_sorteo.xml, devolver estructura basada en figuras programadas (no deja el PDF en blanco)

def _boletin_data_dir():
    base = os.environ.get("DATA_DIR")
    if base:
        return base
    # Render suele montar /data; en local usamos ./DATA
    return "/data" if os.path.isdir("/data") else os.path.join(BASE_DIR, "DATA")

def _boletin_db_dirs():
    data_dir = _boletin_data_dir()
    db_persist = os.path.join(data_dir, "static", "db")
    db_public  = os.path.join(BASE_DIR, "static", "db")
    return db_persist, db_public

def _boletin_resultados_paths():
    db_persist, db_public = _boletin_db_dirs()
    return os.path.join(db_persist, "resultados_sorteo.xml"), os.path.join(db_public, "resultados_sorteo.xml")

def _boletin_pick_resultados_xml():
    p, pub = _boletin_resultados_paths()
    # Si existe el persistente y tiene contenido, úsalo
    try:
        if os.path.exists(p) and os.path.getsize(p) > 50:
            return p
    except Exception:
        pass
    # Si no, usa el público
    return pub

def _boletin_seed_resultados():
    p, pub = _boletin_resultados_paths()
    try:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        os.makedirs(os.path.dirname(pub), exist_ok=True)
        # si no existe persistente, copia desde public si existe
        if (not os.path.exists(p)) and os.path.exists(pub):
            shutil.copy2(pub, p)
    except Exception:
        pass

def _boletin_write_resultados_xml(xml_bytes: bytes):
    p, pub = _boletin_resultados_paths()
    for dst in (p, pub):
        try:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(dst, "wb") as f:
                f.write(xml_bytes)
        except Exception:
            pass

# Asegura que exista al menos el archivo base
try:
    _boletin_seed_resultados()
except Exception:
    pass

def _cargar_resultados(fecha_iso):
    # Siempre devolver estructura (para que el PDF no salga vacío)
    data = {"items": [], "extras": {"comodin": {}, "gran_bonus": {}}}
    if not _is_fecha_iso(fecha_iso):
        return data

    # 1) Base: figuras programadas del día (aunque no haya ganadores todavía)
    try:
        agenda_hoy = _figuras_de_fecha(fecha_iso) or []
        # Mantener orden de agenda
        for f in agenda_hoy:
            nom = (f.get("nombre") or f.get("figura") or "").strip()
            if nom:
                data["items"].append({"figura": nom, "ganadores": []})
    except Exception:
        agenda_hoy = []

    # 2) Leer resultados guardados (si existen)
    try:
        _boletin_seed_resultados()
        path = _boletin_pick_resultados_xml()
        _ensure_xml(path, "resultados")
        root = ET.parse(path).getroot()
        dia = None
        for d in root.findall("dia"):
            if d.attrib.get("fecha") == fecha_iso:
                dia = d
                break

        # Si existe el día, mezclar ganadores/extras
        if dia is not None:
            # Mapa para reemplazar ganadores en la agenda
            idx_map = { (it.get("figura") or "").strip().lower(): i for i, it in enumerate(data["items"]) }
            for f in dia.findall("fig"):
                nom = (f.attrib.get("nombre", "") or "").strip()
                if not nom:
                    continue
                gs = []
                for g in f.findall("ganador"):
                    try:
                        prem = float(g.attrib.get("premio") or 0.0)
                    except Exception:
                        prem = 0.0
                    gs.append({
                        "boleto": g.attrib.get("boleto", ""),
                        "nombre": g.attrib.get("nombre", ""),
                        "vendedor": g.attrib.get("vendedor", ""),
                        "sector": g.attrib.get("sector", ""),
                        "premio": prem
                    })
                key = nom.lower()
                if key in idx_map:
                    data["items"][idx_map[key]]["ganadores"] = gs
                else:
                    data["items"].append({"figura": nom, "ganadores": gs})

            com = dia.find("comodin")
            if com is not None:
                data["extras"]["comodin"] = {
                    "boletos": com.attrib.get("boletos", ""),
                    "texto": com.attrib.get("texto", "")
                }
            bon = dia.find("granbonus")
            if bon is not None:
                nums = [n.strip() for n in (bon.attrib.get("numeros", "")).split(",") if n.strip()]
                data["extras"]["gran_bonus"] = {
                    "numeros": nums,
                    "texto": bon.attrib.get("texto", "")
                }
    except Exception:
        pass

    # 3) Mezclar ganadores detectados del juego (ganadores.json) si existen y aún no están
    try:
        # GANADORES_JSON suele estar en DB_DIR; si existe esta variable, úsala
        gj_path = None
        try:
            gj_path = GANADORES_JSON
        except Exception:
            pass
        if gj_path and os.path.exists(gj_path):
            gj = _safe_json_read(gj_path) or {}
            stack = gj.get(str(fecha_iso)) or []
            if isinstance(stack, list) and stack:
                idx_map = { (it.get("figura") or "").strip().lower(): i for i, it in enumerate(data["items"]) }
                for w in stack:
                    fig = (w.get("figura") or w.get("nombre_figura") or "").strip()
                    if not fig:
                        continue
                    key = fig.lower()
                    if key not in idx_map:
                        data["items"].append({"figura": fig, "ganadores": []})
                        idx_map[key] = len(data["items"]) - 1
                    # Si el detector ya trae tabla/boleto/vendedor/planilla, lo dejamos como texto si no existe en XML
                    # Nota: esto NO reemplaza lo que guardaste manualmente; solo llena si está vacío
                    if not data["items"][idx_map[key]]["ganadores"]:
                        # Crear entrada mínima para que el PDF muestre algo
                        b = str(w.get("boleto") or w.get("tabla") or "").strip()
                        vend = str(w.get("vendedor") or "").strip()
                        pl = str(w.get("planilla") or w.get("rango") or w.get("sector") or "").strip()
                        data["items"][idx_map[key]]["ganadores"] = [{
                            "boleto": b,
                            "nombre": str(w.get("nota") or w.get("nombre") or "").strip(),
                            "vendedor": vend,
                            "sector": pl,
                            "premio": float(w.get("premio") or 0.0) if str(w.get("premio") or "").strip() else 0.0
                        }]
    except Exception:
        pass

    return data

    for f in dia.findall("fig"):
        nom = f.attrib.get("nombre", "")
        gs = []
        for g in f.findall("ganador"):
            try:
                prem = float(g.attrib.get("premio") or 0.0)
            except Exception:
                prem = 0.0
            gs.append({
                "boleto": g.attrib.get("boleto", ""),
                "nombre": g.attrib.get("nombre", ""),
                "vendedor": g.attrib.get("vendedor", ""),
                "sector": g.attrib.get("sector", ""),
                "premio": prem
            })
        data["items"].append({"figura": nom, "ganadores": gs})

    com = dia.find("comodin")
    if com is not None:
        data["extras"]["comodin"] = {
            "boletos": com.attrib.get("boletos", ""),
            "texto": com.attrib.get("texto", "")
        }
    bon = dia.find("granbonus")
    if bon is not None:
        nums = [n.strip() for n in (bon.attrib.get("numeros", "")).split(",") if n.strip()]
        data["extras"]["gran_bonus"] = {
            "numeros": nums,
            "texto": bon.attrib.get("texto", "")
        }
    return data

def _guardar_resultados(fecha_iso, resultados, extras=None):
    if not _is_fecha_iso(fecha_iso):
        raise ValueError("Fecha inválida")

    _boletin_seed_resultados()
    path = _boletin_pick_resultados_xml()

    _ensure_xml(path, "resultados")
    tree = ET.parse(path)
    root = tree.getroot()

    # reemplazar el día completo para esa fecha
    for d in root.findall("dia"):
        if d.attrib.get("fecha") == fecha_iso:
            root.remove(d)
            break

    dia = ET.SubElement(root, "dia", {"fecha": fecha_iso})

    for item in (resultados or []):
        nom = (item.get("figura") or "").strip()
        if not nom:
            continue
        fig = ET.SubElement(dia, "fig", {"nombre": nom})
        for g in (item.get("ganadores") or []):
            try:
                prem = float(g.get("premio") or 0.0)
            except Exception:
                prem = 0.0
            ET.SubElement(fig, "ganador", {
                "boleto": (g.get("boleto") or "").strip(),
                "nombre": (g.get("nombre") or "").strip(),
                "vendedor": (g.get("vendedor") or "").strip(),
                "sector": (g.get("sector") or "").strip(),
                "premio": f"{prem:.2f}"
            })

    if extras:
        com = extras.get("comodin") or {}
        bon = extras.get("gran_bonus") or {}
        if com:
            ET.SubElement(dia, "comodin", {
                "boletos": (com.get("boletos") or "").strip(),
                "texto": (com.get("texto") or "").strip()
            })
        if bon:
            nums = bon.get("numeros")
            if isinstance(nums, (list, tuple)):
                nums = ",".join(str(x) for x in nums)
            ET.SubElement(dia, "granbonus", {
                "numeros": (nums or "").strip(),
                "texto": (bon.get("texto") or "").strip()
            })

    # escribir y espejar en ambas rutas (persistente + static/db)
    xml_bytes = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    _boletin_write_resultados_xml(xml_bytes)

# ------------------ Reintegro desde LOGS ------------------
def _find_image_case_insensitive(dirs, filename):
    base = (filename or "").strip()
    if not base:
        return None
    cands = [base]
    if "." not in base:
        cands += [base + ext for ext in (".png",".jpg",".jpeg",".webp",".gif")]
    for d in dirs:
        if not os.path.isdir(d):
            continue
        try:
            files = os.listdir(d)
        except Exception:
            files = []
        lowers = [f.lower() for f in files]
        for cand in cands:
            if cand.lower() in lowers:
                return os.path.join(d, files[lowers.index(cand.lower())])
        bases = {os.path.splitext(f)[0].lower(): f for f in files}
        key = os.path.splitext(base)[0].lower()
        if key in bases:
            return os.path.join(d, bases[key])
    return None

def _reintegro_from_log_for_date(fecha_iso):
    log_path = os.path.join(LOGS_DIR, "impresiones.xml")
    if not os.path.exists(log_path):
        for alt in (os.path.join(DB_DIR, "impresiones.xml"), os.path.join(BASE_DIR, "impresiones.xml")):
            if os.path.exists(alt):
                log_path = alt
                break
        else:
            return {"archivo": None, "imagen": None, "cantidad": None, "fecha": None}

    try:
        root = ET.parse(log_path).getroot()
    except ET.ParseError:
        return {"archivo": None, "imagen": None, "cantidad": None, "fecha": None}

    records = []
    for imp in root.findall("impresion"):
        fs = (imp.findtext("fecha_sorteo") or imp.findtext("fecha") or "").strip()
        rein = (imp.findtext("reintegro_especial") or imp.findtext("reintegro") or "").strip()
        cant = (imp.findtext("cantidad_reintegro_especial") or imp.findtext("cant_reintegro_especial") or "").strip()
        if rein:
            records.append((fs, rein, cant))

    chosen = None
    for item in reversed(records):
        if _is_fecha_iso(fecha_iso) and item[0] == fecha_iso:
            chosen = item
            break
    if chosen is None and records:
        chosen = records[-1]

    if chosen is None:
        return {"archivo": None, "imagen": None, "cantidad": None, "fecha": None}

    nombre_archivo = chosen[1]
    dirs = [
        os.path.join(STATIC_DIR, "REINTEGROS"),
        os.path.join(STATIC_DIR, "reintegros"),
        os.path.join(IMG_DIR, "reintegros"),
    ]
    img = _find_image_case_insensitive(dirs, nombre_archivo)
    return {"archivo": nombre_archivo, "imagen": img, "cantidad": chosen[2], "fecha": chosen[0]}

# ------------------ Layout JSON ------------------
def _read_json(path, default_obj):
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(default_obj, f, ensure_ascii=False, indent=2)
        return default_obj
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default_obj

def _write_json(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)

# --- Auto-fit para que entren todas las figuras en A4 ---
def _default_layout(figs, scale=1.0, fixed_cols=None):
    W, H = A4
    n = max(1, len(figs))

    header_h = 120
    top_y = header_h + 1
    bottom_reserved = 1
    avail_h = max(120.0, H - top_y - bottom_reserved)

    margin_x = 10
    gap_x = 5
    gap_row = 5
    extra_v = 22 + 8 + 18

    best = None
    if fixed_cols:
        cols = max(1, min(int(fixed_cols), n))
        rows = math.ceil(n / cols)
        size_w = (W - 2*margin_x - (cols-1)*gap_x) / cols
        size_h = (avail_h - (rows-1)*gap_row - rows*extra_v) / rows
        size = min(size_w, size_h)
        best = (size, cols, rows)
    else:
        for cols in range(14, 3, -1):
            rows = math.ceil(n / cols)
            size_w = (W - 2 * margin_x - (cols - 1) * gap_x) / cols
            size_h = (avail_h - (rows - 1) * gap_row - rows * extra_v) / rows
            size = min(size_w, size_h)
            if size <= 28:
                continue
            if best is None or size > best[0]:
                best = (size, cols, rows)

    if best is None:
        size, cols, rows = 72, min(n, 8), math.ceil(n / min(n, 8))
    else:
        size, cols, rows = best

    size *= float(scale)

    positions = {}
    x0 = margin_x
    y0 = top_y
    for i, f in enumerate(figs):
        col = i % cols
        row = i // cols
        x = x0 + col * (size + gap_x)
        y = y0 + row * (size + gap_row + extra_v)
        positions[f["nombre"]] = {"x": float(x), "y": float(y), "size": float(size)}

    return {
        "logo":  {"x": 12, "y": 8, "w": 420, "h": 110},
        "title": {"x": 220, "y": 32, "size": 18, "align": "left"},
        "total": {"x": W - 22, "y": 24, "size": 56, "align": "right"},
        "figs": positions
    }

def _layout_for(fecha_base, figs, scale=1.0, force_autofit=False, fixed_cols=None):
    data = _read_json(LAYOUT_JSON, {"default": {}})
    if fecha_base in data and not force_autofit:
        return data[fecha_base]
    return _default_layout(figs, scale=scale, fixed_cols=fixed_cols)

# ------------------ PDF helpers (dibujo) ------------------
def _register_font():
    try:
        for p in [
            os.path.join(FONTS_DIR, "DejaVuSans.ttf"),
            "C:\\Windows\\Fonts\\arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]:
            if os.path.exists(p):
                pdfmetrics.registerFont(TTFont("GLTTF", p))
                return "GLTTF"
    except Exception:
        pass
    return "Helvetica"

def _chip(c, x, y_top, w, txt, font, bg="#1F58FF", fs=10):
    h = 18
    y = y_top - h
    c.setFillColor(colors.HexColor(bg)); c.roundRect(x, y, w, h, 6, 0, 1)
    c.setFillColor(colors.white); c.setFont(font, fs); c.drawCentredString(x + w/2, y + 4, txt)

def _bar(c, x, y_base, w, txt, font, bg="#173A9E", fs=10):
    h = 18
    y = y_base - h
    c.setFillColor(colors.HexColor(bg)); c.roundRect(x, y, w, h, 6, 0, 1)
    c.setFillColor(colors.white); c.setFont(font, fs); c.drawCentredString(x + w/2, y + 4, txt)

def _draw_star(c, cx, cy, r_outer, r_inner, color_hex="#FF0000"):
    pts = []
    for i in range(10):
        ang = math.radians(-90 + i * 36)
        r = r_outer if i % 2 == 0 else r_inner
        pts.append((cx + r * math.cos(ang), cy + r * math.sin(ang)))
    p = c.beginPath()
    p.moveTo(pts[0][0], pts[0][1])
    for (px, py) in pts[1:]:
        p.lineTo(px, py)
    p.close()
    c.setFillColor(colors.HexColor(color_hex))
    c.drawPath(p, fill=1, stroke=0)

def _grid5(c, x, y_top, size, mask):
    cell = (size - 4) / 5.0
    for r in range(5):
        for col in range(5):
            idx = r*5 + col
            on  = bool(mask[idx]) if mask else False
            px  = x + col*(cell+1)
            py  = y_top - (r+1)*(cell+1)
            c.setFillColor(colors.HexColor("#1F58FF") if on else colors.HexColor("#E8EEFF"))
            c.rect(px, py, cell, cell, stroke=0, fill=1)
    c.setStrokeColor(colors.HexColor("#27418B"))
    c.rect(x-1, y_top-(5*(cell+1))-1, 5*(cell+1)-1, 5*(cell+1)-1, stroke=1, fill=0)
    cx = x + 2*(cell+1) + cell/2.0
    cy = y_top - (3*(cell+1)) + cell/2.0
    _draw_star(c, cx, cy, r_outer=cell*0.42, r_inner=cell*0.20, color_hex="#FF0000")

def _draw_ultrablack(c, text, x, y, size, font):
    c.setFont(font, size)
    c.setFillColor(colors.black)
    for dx, dy in [(0,0),(0.25,0),(0,-0.25),(0.25,-0.25),(0.15,-0.15),(-0.15,-0.15)]:
        c.drawRightString(x+dx, y+dy, text)

# --------- Helpers de SPINNERS (Extras) ----------
def _parse_spinners(extras: dict):
    """
    Lee extras y extrae lista de spinners (hasta 20) y el valor por spinner.
    Busca en:
      - extras['spinners'] -> {'numeros': '...', 'valor'/'texto': '...'}
      - fallback: extras['comodin'] -> usa 'boletos' como numeros y 'texto' como valor
    """
    extras = extras or {}
    block = extras.get("spinners") or {}
    if not block:
        block = extras.get("comodin") or {}

    raw_nums = (block.get("numeros") or (block.get("boletos") or "")).strip()
    raw_val  = (block.get("valor") or (block.get("texto") or "")).strip()

    tokens = re.findall(r"\d{1,4}", raw_nums)
    nums = [t.zfill(4) for t in tokens][:20]

    m = re.search(r"(\d+(?:[.,]\d{1,2})?)", raw_val)
    valor = None
    if m:
        try:
            valor = float(m.group(1).replace(",", "."))
        except Exception:
            valor = None

    return {"nums": nums, "valor": valor}

def _draw_spinners_card(c, x, y, w, h, nums, valor, font):
    """
    Tarjeta SPINNERS con 'pastillas' de 4 cuadritos.
    - Las filas se **CENTRAN** horizontalmente.
    - Se ajusta tamaño para encajar sin recortar.
    """
    # Tarjeta
    c.setFillColor(colors.HexColor("#F8FAFF"))
    c.setStrokeColor(colors.HexColor("#CBD5F1"))
    c.roundRect(x, y, w, h, 10, stroke=1, fill=1)

    pad = 10
    inner_x = x + pad
    inner_y = y + pad
    inner_w = w - 2*pad
    inner_h = h - 2*pad

    # Título + valor
    c.setFillColor(colors.HexColor("#0F172A")); c.setFont(font, 10)
    c.drawString(inner_x, y + h - pad - 6, "SPINNERS")
    if valor is not None:
        c.setFillColor(colors.HexColor("#334155")); c.setFont(font, 9)
        c.drawRightString(x + w - pad, y + h - pad - 6, f"Valor c/u: {_money(valor)}")

    # Parámetros visuales
    title_h     = 18          # espacio reservado para el título
    spinner_gap = 12          # separación entre spinners
    row_gap     = 8           # separación entre filas
    box_gap     = 3           # separación entre dígitos
    pill_pad    = 6           # padding interno de la pastilla
    grid_h      = max(10, inner_h - title_h)

    n = len(nums)
    if n == 0:
        return

    # Elegimos per_row y tamaño de box maximizando el encaje
    best = None  # (box_size, per_row, rows)
    max_per_row = min(n, 8)
    for per_row in range(max_per_row, 0, -1):
        rows = math.ceil(n / per_row)

        # Ancho disponible -> box por ancho
        max_box_w = ((inner_w - (per_row - 1) * spinner_gap) / per_row - 2 * pill_pad - 3 * box_gap) / 4.0
        # Alto disponible -> box por alto
        max_box_h = ((grid_h - (rows - 1) * row_gap) / rows - 2 * pill_pad)

        box = min(max_box_w, max_box_h, 18)  # límite superior estético
        if box >= 10:  # mínimo legible
            if best is None or box > best[0]:
                best = (box, per_row, rows)

    if best is None:
        best = (8.0, min(n, 6), math.ceil(n / min(n, 6)))

    box, per_row, rows = best
    fs = max(9, min(14, box * 0.70))

    pill_h = 2 * pill_pad + box
    pill_w = 2 * pill_pad + 4 * box + 3 * box_gap

    # Dibujo centrado por fila
    c.setFont(font, fs)
    idx = 0
    for r in range(rows):
        remaining = n - idx
        count = min(per_row, remaining)
        row_w = count * pill_w + (count - 1) * spinner_gap
        start_x = inner_x + max(0, (inner_w - row_w) / 2.0)  # <-- centrado
        y_row = inner_y + grid_h - pill_h - r * (pill_h + row_gap)

        for j in range(count):
            cur_x = start_x + j * (pill_w + spinner_gap)

            # Pastilla
            c.setFillColor(colors.HexColor("#EEF2FF"))
            c.setStrokeColor(colors.HexColor("#C7D2FE"))
            c.roundRect(cur_x, y_row, pill_w, pill_h, 7, stroke=1, fill=1)

            # 4 cuadritos
            s = re.sub(r"\D", "", str(nums[idx]))[:4].rjust(4, "0")
            xx = cur_x + pill_pad
            yy = y_row + pill_pad
            for ch in s:
                c.setFillColor(colors.white)
                c.setStrokeColor(colors.HexColor("#94A3B8"))
                c.roundRect(xx, yy, box, box, 3, stroke=1, fill=1)

                c.setFillColor(colors.HexColor("#111827"))
                tx = xx + (box - pdfmetrics.stringWidth(ch, font, fs)) / 2.0
                ty = yy + (box - fs) / 2.0 - 0.5
                c.drawString(tx, ty, ch)

                xx += box + box_gap

            idx += 1
            if idx >= n:
                break

# ------------------ Rutas Flask ------------------

@app.get("/api/figuras-manana")
def api_figuras_manana():
    base = (request.args.get("fecha") or date.today().isoformat()).strip()
    if not _is_fecha_iso(base):
        base = date.today().isoformat()
    manana = (datetime.fromisoformat(base) + timedelta(days=1)).date().isoformat()
    figs = _figuras_de_fecha(manana)
    total = sum((f.get("valor") or 0.0) for f in figs)
    return jsonify({"ok": True, "fecha": manana, "figuras": figs, "total": total})

@app.get("/api/resultados")
def api_resultados():
    fecha = (request.args.get("fecha") or date.today().isoformat()).strip()
    if not _is_fecha_iso(fecha):
        fecha = date.today().isoformat()
    return jsonify({"ok": True, **_cargar_resultados(fecha)})

@app.post("/boletin/guardar")
def boletin_guardar():
    fecha = (request.form.get("fecha") or "").strip()
    raw = (request.form.get("resultados") or "").strip()
    raw_extras = (request.form.get("extras") or "").strip()
    resultados = []
    extras = None
    if raw:
        try:
            tmp = json.loads(raw)
            if isinstance(tmp, list):
                resultados = tmp
        except Exception:
            pass
    if raw_extras:
        try:
            tmp = json.loads(raw_extras)
            if isinstance(tmp, dict):
                extras = tmp
        except Exception:
            pass
    try:
        _guardar_resultados(fecha, resultados, extras)
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400

@app.get("/api/boletin-layout/get")
def api_layout_get():
    fecha = (request.args.get("fecha") or date.today().isoformat()).strip()
    if not _is_fecha_iso(fecha):
        fecha = date.today().isoformat()
    manana = (datetime.fromisoformat(fecha) + timedelta(days=1)).date().isoformat()
    figs = _figuras_de_fecha(manana)
    lay  = _layout_for(fecha, figs, scale=FIG_BLOCK_SCALE, fixed_cols=FIG_FIXED_COLS)
    return jsonify({"ok": True, "layout": lay, "figuras": figs})

@app.post("/api/boletin-layout/save")
def api_layout_save():
    payload = request.get_json(force=True, silent=True) or {}
    fecha = (payload.get("fecha") or date.today().isoformat()).strip()
    if not _is_fecha_iso(fecha):
        fecha = date.today().isoformat()
    lay = payload.get("layout") or {}
    data = _read_json(LAYOUT_JSON, {"default": {}})
    data[fecha] = lay
    _write_json(LAYOUT_JSON, data)
    return jsonify({"ok": True})

@app.get("/")
def home():
    return redirect(url_for("boletin_view"))

@app.get("/boletin")
def boletin_view():
    q = (request.args.get("fecha") or date.today().isoformat()).strip()
    if not _is_fecha_iso(q):
        q = date.today().isoformat()
    try:
        return render_template("boletin.html", fecha_inicial=q)
    except Exception:
        pdf_url = url_for("boletin_pdf", fecha=q)
        return f'''
        <html><body style="font-family:Arial, sans-serif; background:#0b1324; color:#e5e7eb;">
            <div style="max-width:920px;margin:40px auto;padding:16px;background:#111827;border-radius:12px;">
                <h2>Boletín</h2>
                <p>Fecha seleccionada: {q}</p>
                <p><a style="background:#10b981;color:#fff;padding:8px 12px;border-radius:8px;text-decoration:none"
                      href="{pdf_url}" target="_blank">Ver PDF</a></p>
            </div>
        </body></html>
        '''

# ------------------ PDF principal ------------------
@app.get("/boletin/pdf")
def boletin_pdf():
    try:
        fecha = (request.args.get("fecha") or date.today().isoformat()).strip()
        if not _is_fecha_iso(fecha):
            fecha = date.today().isoformat()

        # escala de figuras + columnas
        qscale = request.args.get("scale")
        qcols  = request.args.get("cols")
        fixed_cols = int(qcols) if qcols else (FIG_FIXED_COLS or None)
        if qscale is None:
            scale = FIG_BLOCK_SCALE
            force_autofit = False
        else:
            try:
                scale = float(qscale)
            except Exception:
                scale = FIG_BLOCK_SCALE
            scale = max(0.5, min(1.2, scale))
            force_autofit = True

        # Escalas opcionales
        def _float_arg(name, default):
            v = request.args.get(name)
            if v is None:
                return default
            try:
                return float(v)
            except Exception:
                return default

        LOGO_SCALE = max(0.5, min(2.0, _float_arg("logo_scale", LOGO_SCALE_DEFAULT)))
        REIN_SCALE = max(0.5, min(1.6, _float_arg("rein_scale", 1.05)))
        SPIN_SCALE = max(0.5, min(1.6, _float_arg("spin_scale", 1.00)))

        dt = datetime.fromisoformat(fecha).date()
        manana = (dt + timedelta(days=1)).isoformat()

        figs_manana  = _figuras_de_fecha(manana)
        total_manana = sum((f.get("valor") or 0.0) for f in figs_manana)
        resultados   = _cargar_resultados(fecha)
        shapes       = _load_shapes()
        layout       = _layout_for(fecha, figs_manana, scale=scale, force_autofit=force_autofit, fixed_cols=fixed_cols)

        # Reintegro (por fecha) desde LOGS
        rein_log = _reintegro_from_log_for_date(fecha)

        # SPINNERS (Extras)
        sp_data = _parse_spinners(resultados.get("extras") or {})

        # Backfill posiciones
        default_figs_pos = _default_layout(figs_manana, scale=scale, fixed_cols=fixed_cols)["figs"]
        layout.setdefault("figs", {})
        for f in figs_manana:
            n = f["nombre"]
            if n not in layout["figs"]:
                layout["figs"][n] = default_figs_pos.get(n, {"x": 50, "y": 148, "size": 96})

        buf = BytesIO()
        c = canvas.Canvas(buf, pagesize=A4)
        W, H = A4

        FONT = _register_font()
        T = lambda s: _safe_text(s, FONT)

        # ---------- Header ----------
        header_h = 120
        c.setFillColor(colors.HexColor("#E7B91E"))
        c.rect(0, H - header_h, W, header_h, 0, 1)

        # Logo
        logo_candidates = [
            os.path.join(BASE_DIR, "static", "golpe_suerte_logo.png"),
            os.path.join(IMG_DIR, "logo.png"),
            os.path.join(IMG_DIR, "golpe_suerte_logo.png"),
            os.path.join(BASE_DIR, "static", "img", "logo.png"),
        ]
        logo = next((p for p in logo_candidates if os.path.exists(p)), None)
        L = layout.get("logo", {"x": 12, "y": 8, "w": 420, "h": 110})
        if logo:
            img = ImageReader(logo)
            iw, ih = img.getSize()
            s = min(L["w"]/iw, L["h"]/ih) * float(LOGO_SCALE)
            draw_w = iw * s
            draw_h = ih * s
            if draw_w > L["w"] or draw_h > L["h"]:
                f = min(L["w"]/draw_w, L["h"]/draw_h, 1.0)
                draw_w *= f
                draw_h *= f
            c.drawImage(img, L["x"], H - (L["y"] + draw_h),
                        width=draw_w, height=draw_h,
                        preserveAspectRatio=True, mask="auto")

        # Título + fecha
        c.setFillColor(colors.black)
        c.setFont(FONT, 18)
        c.drawCentredString(W/2, H - 42, T("JUEGO HOY"))
        c.setFont(FONT, 11)
        c.drawCentredString(W/2, H - 58, T(_es_corta(manana).capitalize()))

        # Total a jugar
        TL = layout.get("total", {"x": W - 22, "y": 24, "size": 56, "align": "right"})
        c.setFillColor(colors.white); c.setFont(FONT, 11)
        c.drawRightString(W - 18, H - 22, T("PREMIO TOTAL"))
        amount = T(_money_header(total_manana))
        _draw_ultrablack(c, amount,
                         TL.get("x", W - 22),
                         H - (TL.get("y", 24) + TL.get("size", 56)),
                         TL.get("size", 56), FONT)

        # ---------- Figuras de mañana ----------
        fig_lay = layout.get("figs", {})
        for f in figs_manana:
            name = f["nombre"]; val = f.get("valor") or 0.0
            pos = fig_lay.get(name) or {}
            bx = float(pos.get("x", 50)); by = float(pos.get("y", header_h + 28)); bw = float(pos.get("size", 96))

            _chip(c, bx, H - by, bw, T(_money(val)), FONT, "#1F58FF", 10)
            grid_top = H - by - 22
            mask = shapes.get(name.strip().lower(), [False] * 25)
            _grid5(c, bx, grid_top, bw, mask)
            _bar(c, bx, grid_top - (bw + 8), bw, T(name.upper()), FONT, "#0E2E8E", 10)

        # ---------- Resultados ----------
        block_h_extra = 22 + 8 + 18
        max_depth = header_h
        for f in figs_manana:
            pos = fig_lay.get(f["nombre"]) or {}
            by   = float(pos.get("y", header_h + 28))
            bw   = float(pos.get("size", 96))
            depth = by + (bw + block_h_extra)
            if depth > max_depth:
                max_depth = depth

        depth = max_depth + 28
        y = H - depth
        MIN_Y_FIRST_PAGE = 120
        if y < MIN_Y_FIRST_PAGE:
            y = MIN_Y_FIRST_PAGE

        # Banda compacta
        c.setFillColor(colors.HexColor("#2B2370")); c.rect(0, y, W, 16, 0, 1)
        c.setFillColor(colors.white); c.setFont(FONT, 10)
        c.drawCentredString(W/2, y + 4, T(f"RESULTADOS SORTEO { _es_largo(fecha) }"))
        y -= 4

        agenda = _figuras_de_fecha(fecha)
        premio_map = {a["nombre"].strip().lower(): (a.get("valor") or 0.0) for a in agenda}

        def ensure_space(hmin=70, top_margin=16):
            nonlocal y
            if y - hmin < top_margin:
                c.showPage()
                y = H - top_margin

        def bloque(fig, ganadores, premio_total):
            nonlocal y
            ensure_space(120)
            y -= 16
            c.setFillColor(colors.HexColor("#EDF2FF")); c.rect(14, y, W - 28, 18, 0, 1)
            c.setFillColor(colors.HexColor("#203880")); c.setFont(FONT, 10)
            c.drawCentredString(W / 2, y + 5, T(fig.upper()))
            c.drawRightString(W - 20, y + 5, T(f"Premio total { _money(premio_total) }"))
            y -= 20

            c.setFillColor(colors.HexColor("#6B7280")); c.setFont(FONT, 9)
            c.drawString(20, y, T("Boleto"))
            c.drawString(86, y, T("Nombre"))
            c.drawString(320, y, T("Vendedor"))
            c.drawRightString(W - 20, y, T("Premio"))
            y -= 8
            c.setStrokeColor(colors.HexColor("#CBD5F1")); c.line(14, y, W - 14, y)
            y -= 8

            par = True
            for g in (ganadores or []):
                ensure_space(30)
                if par:
                    c.setFillColor(colors.HexColor("#F7F9FF")); c.rect(14, y - 12, W - 28, 14, 0, 1)
                par = not par
                c.setFillColor(colors.black); c.setFont(FONT, 9)
                nombre = g.get("nombre", "") or ""
                vendedor = (g.get("vendedor", "") or "").strip()
                planilla = (g.get("sector", "") or "").strip()
                
                # Si NO hay vendedor (planilla sin asignar), mostramos el nombre del sorteo
                sorteo_nombre = ""
                try:
                    sorteo_nombre = (layout.get("sorteo") or layout.get("nombre_sorteo") or "").strip()
                except Exception:
                    sorteo_nombre = ""
                if not vendedor:
                    vendedor = sorteo_nombre or "GOLPE DE SUERTE"
                
                vend_show = vendedor if not planilla else f"{vendedor} · {planilla}"
                
                c.drawString(20, y - 9, T(g.get("boleto", "")))
                c.drawString(86, y - 9, T(nombre))
                c.drawString(320, y - 9, T(vend_show))
                try:
                    prem = float(g.get("premio") or 0.0)
                except Exception:
                    prem = 0.0
                c.drawRightString(W - 20, y - 9, T(_money(prem)))
                y -= 14
            y -= 4

        for item in (resultados.get("items") or []):
            nom = item.get("figura", "")
            gan = item.get("ganadores") or []
            premio = premio_map.get(nom.strip().lower(), 0.0)
            if premio == 0.0:
                premio = sum((g.get("premio") or 0.0) for g in gan)
            bloque(nom, gan, premio)

        # ---------- Tarjetas inferiores ----------
        margin = 12
        espacio_disponible = (y - margin)

        # SPINNERS (izquierda)
        sp_base_h = 86
        sp_base_w = 360
        sp_h = sp_base_h * SPIN_SCALE
        sp_w = sp_base_w * SPIN_SCALE
        if espacio_disponible < (sp_h + 20):
            factor = max(0.40, (espacio_disponible - 20) / max(sp_h, 1))
            sp_h *= factor
            sp_w *= factor
        if sp_data["nums"] or (sp_data["valor"] is not None):
            _draw_spinners_card(c, margin, margin, sp_w, sp_h, sp_data["nums"], sp_data["valor"], FONT)

        # REINTEGRO (derecha)
        rein_base_h = 90
        rein_base_w = int(rein_base_h * 3.75)
        card_h = rein_base_h * REIN_SCALE
        card_w = rein_base_w * REIN_SCALE
        if espacio_disponible < (card_h + 20):
            factor = max(0.40, (espacio_disponible - 20) / max(card_h, 1))
            card_h *= factor
            card_w *= factor

        rein_x = W - margin - card_w
        base_y = margin

        if rein_log.get("imagen"):
            c.setFillColor(colors.HexColor("#D1D5DB"))
            c.roundRect(rein_x+2.5, base_y-2.5, card_w, card_h, 10, stroke=0, fill=1)
            c.setFillColor(colors.white); c.setStrokeColor(colors.HexColor("#CBD5F1"))
            c.roundRect(rein_x, base_y, card_w, card_h, 10, stroke=1, fill=1)

            gap = 25
            label_w = card_w * 0.45
            img_w   = card_w - label_w - gap - 10
            label_x = rein_x + 8
            img_x   = label_x + label_w + gap
            inner_y = base_y + 8
            inner_h = card_h - 16

            c.setFillColor(colors.HexColor("#190042"))
            c.setFont(FONT, max(12, int(16 * REIN_SCALE)))
            text_y = inner_y + (inner_h / 2) - 6
            c.drawString(label_x, text_y, "REINTEGRO")

            c.setStrokeColor(colors.HexColor("#0C8A3E"))
            c.setLineWidth(1)
            c.line(label_x, text_y - 4, label_x + (label_w * 0.60), text_y - 4)

            c.drawImage(
                rein_log["imagen"], img_x, inner_y,
                width=img_w, height=inner_h,
                preserveAspectRatio=True, anchor='sw', mask='auto'
            )

        c.showPage()
        c.save()
        buf.seek(0)
        return send_file(buf, as_attachment=True,
                         download_name=f"boletin_{fecha}.pdf",
                         mimetype="application/pdf")

    except Exception:
        import traceback
        print("[/boletin/pdf ERROR]\n", traceback.format_exc())
        return "Error generando PDF", 500


# (opcional) arrancar si se ejecuta directo






# ------------------------------------------------------------------------------
# Run
# FIN BOLETIN CERRADO ------------------------------------------------------------------------------










#PAGO DE PREMIOS

# =========================
#  PAGO DE PREMIOS (MÓDULO)
# =========================
# No toca boletín ni "figuras de mañana"

import os, re, json, xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta
from io import BytesIO

from flask import request, jsonify, send_file, render_template, session
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader, simpleSplit
from reportlab.pdfbase.pdfmetrics import stringWidth

# ---- Rutas base / compatibilidad con tu app principal ----
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
DB_DIR     = os.path.join(STATIC_DIR, "db")
IMG_DIR    = os.path.join(STATIC_DIR, "img")

RESULTADOS_XML = os.path.join(DB_DIR, "resultados_sorteo.xml")

def _pp_is_fecha_iso(s):
    try:
        datetime.fromisoformat((s or "").strip()); return True
    except Exception:
        return False

def _safe_float(x, default=0.0):
    try:
        return float(x)
    except Exception:
        return default

def _ensure_xml(path, root_name):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not os.path.exists(path):
        ET.ElementTree(ET.Element(root_name)).write(path, encoding="utf-8", xml_declaration=True)
        return
    try:
        ET.parse(path)
    except ET.ParseError:
        ET.ElementTree(ET.Element(root_name)).write(path, encoding="utf-8", xml_declaration=True)

# Intenta usar una TTF del sistema; si no, Helvetica
def _pp_register_font():
    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        for p in [
            os.path.join(STATIC_DIR, "fonts", "DejaVuSans.ttf"),
            "C:\\Windows\\Fonts\\arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]:
            if os.path.exists(p):
                pdfmetrics.registerFont(TTFont("GLTTF", p))
                return "GLTTF"
    except Exception:
        pass
    return "Helvetica"

_PPFONT     = _pp_register_font()
_PPBOLDFONT = "Helvetica-Bold"
_ppT        = lambda s: "" if s is None else str(s)

# ---- Archivos del módulo ----
PAGOS_XML   = os.path.join(DB_DIR, "pagos_premios.xml")
RECIBOS_DIR = os.path.join(STATIC_DIR, "tmp", "recibos")
CFG_JSON    = os.path.join(DB_DIR, "pagos_config.json")

os.makedirs(RECIBOS_DIR, exist_ok=True)
_ensure_xml(PAGOS_XML, "pagos")

CFG_DEFAULT = {
    "company_name": "Gran Sorteo Ventanas",
    "city_default": "Vinces",
    "letterhead": "HOJA-MEMBRETADA.png"  # en static/img/
}

def _cfg_read():
    if not os.path.exists(CFG_JSON):
        with open(CFG_JSON, "w", encoding="utf-8") as f:
            json.dump(CFG_DEFAULT, f, ensure_ascii=False, indent=2)
        return CFG_DEFAULT.copy()
    try:
        with open(CFG_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)
        for k, v in CFG_DEFAULT.items():
            data.setdefault(k, v)
        return data
    except Exception:
        return CFG_DEFAULT.copy()

def _cfg_write(obj):
    with open(CFG_JSON, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)

# ---- Utilidades de pagos ----
def _pp_premio_key(fecha_iso, figura_nombre, boleto):
    return f"{(fecha_iso or '').strip()}||{(figura_nombre or '').strip().lower()}||{(boleto or '').strip()}"

def _pp_leer_pagos_map():
    _ensure_xml(PAGOS_XML, "pagos")
    try:
        root = ET.parse(PAGOS_XML).getroot()
    except ET.ParseError:
        root = ET.Element("pagos")
    out = {}
    for p in root.findall("pago"):
        k = p.attrib.get("key") or _pp_premio_key(
            p.attrib.get("fecha_sorteo", ""),
            p.attrib.get("figura", ""),
            p.attrib.get("boleto", "")
        )
        out[k] = p.attrib
    return out

def _pp_guardar_pago_registro(pago_dict):
    _ensure_xml(PAGOS_XML, "pagos")
    tree = ET.parse(PAGOS_XML); root = tree.getroot()
    ET.SubElement(root, "pago", pago_dict)
    tree.write(PAGOS_XML, encoding="utf-8", xml_declaration=True)

def _pp_iter_ganadores_de_fecha(fecha_iso):
    if not _pp_is_fecha_iso(fecha_iso): return
    _ensure_xml(RESULTADOS_XML, "resultados")
    try:
        root = ET.parse(RESULTADOS_XML).getroot()
    except ET.ParseError:
        return
    dia = None
    for d in root.findall("dia"):
        if d.attrib.get("fecha") == fecha_iso:
            dia = d; break
    if dia is None: return
    for fig in dia.findall("fig"):
        figura = fig.attrib.get("nombre", "")
        for g in fig.findall("ganador"):
            yield {
                "fecha": fecha_iso,
                "figura": figura,
                "boleto": g.attrib.get("boleto",""),
                "nombre": g.attrib.get("nombre",""),
                "vendedor": g.attrib.get("vendedor",""),
                "sector": g.attrib.get("sector",""),
                "premio": _safe_float(g.attrib.get("premio"))
            }

def _pp_ultima_fecha_con_resultados():
    _ensure_xml(RESULTADOS_XML, "resultados")
    try:
        root = ET.parse(RESULTADOS_XML).getroot()
    except ET.ParseError:
        return date.today().isoformat()
    fechas = []
    for d in root.findall("dia"):
        f = (d.attrib.get("fecha") or "").strip()
        if _pp_is_fecha_iso(f): fechas.append(f)
    return (sorted(fechas)[-1] if fechas else date.today().isoformat())

# -------------------- Helpers de dibujo (justificado) --------------------
def _wrap_words(text, font, size, max_width):
    words = (text or "").split()
    lines, cur = [], []
    for w in words:
        trial = " ".join(cur + [w])
        if stringWidth(trial, font, size) <= max_width or not cur:
            cur.append(w)
        else:
            lines.append(cur); cur = [w]
    if cur: lines.append(cur)
    return lines

def _draw_justified_paragraph(c, text, x, y, width, font, size, leading, min_justify_ratio=0.65):
    """
    Dibuja párrafo JUSTIFICADO entre [x, x+width]. Devuelve el nuevo y.
    Las líneas demasiado cortas se dibujan alineadas a la izquierda.
    """
    lines_words = _wrap_words(text, font, size, width)
    for idx, words in enumerate(lines_words):
        line = " ".join(words)
        n_spaces = max(len(words) - 1, 0)
        line_w = stringWidth(line, font, size)

        to = c.beginText()
        to.setTextOrigin(x, y)
        to.setFont(font, size)

        # Última línea o línea corta -> izquierda normal
        if idx == len(lines_words) - 1 or n_spaces == 0 or (line_w / float(width)) < min_justify_ratio:
            to.textLine(line)
        else:
            extra = (width - line_w)
            to.setWordSpace(extra / n_spaces)
            to.textLine(line)
        c.drawText(to)
        y -= leading
    return y

# ---- Generador de ACTA PDF (título centrado, texto justificado) ----
def _pp_generate_recibo_pdf(recibo_id, payload):
    cfg = _cfg_read()
    out = os.path.join(RECIBOS_DIR, f"{recibo_id}.pdf")

    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    W, H = A4

    # Fondo membrete "cover"
    letter = (payload.get("letterhead") or cfg.get("letterhead") or "").strip()
    letter_path = os.path.join(IMG_DIR, letter)
    if os.path.exists(letter_path):
        img = ImageReader(letter_path)
        iw, ih = img.getSize()
        s = max(W/float(iw), H/float(ih))
        tw, th = iw*s, ih*s
        c.drawImage(img, (W-tw)/2.0, (H-th)/2.0, width=tw, height=th, mask="auto")

    # Márgenes
    LM, RM = 64, 64
    TOP    = 240     # bajamos todo más
    WIDTH  = W - LM - RM
    LEAD   = 16
    y = H - TOP
    T = _ppT

    # ---- TÍTULO CENTRADO ----
    c.setFont(_PPBOLDFONT, 13)
    c.drawCentredString(W/2, y, T(f"Acta {recibo_id.upper()}"))
    y -= 28

    # Ciudad y Fecha (centradas)
    c.setFont(_PPFONT, 11)
    c.drawCentredString(W/2, y, T(f"Ciudad: {payload.get('ciudad', cfg.get('city_default',''))}")); y -= 16
    c.drawCentredString(W/2, y, T(f"Fecha: {payload.get('fecha_pago','')}")); y -= 26

    # ---- PÁRRAFOS JUSTIFICADOS ----
    empresa  = payload.get("empresa") or cfg.get("company_name","")
    monto    = _safe_float(payload.get("premio"))
    cobr     = T(payload.get("cobrador_nombre",""))
    planilla = T(payload.get("ganador_nombre",""))
    figura   = T(payload.get("figura",""))
    boleto   = T(payload.get("boleto",""))
    fsort    = T(payload.get("fecha_sorteo",""))

    # Párrafo 1 (con el texto de planilla entre paréntesis)
    p1 = (f"La empresa {empresa} hace la entrega formal de un premio valorado en "
          f"$ {monto:.2f} al señor(a) {cobr} "
          + (f"({planilla}) " if planilla else "")
          + "en calidad de ganador(a).")
    c.setFont(_PPFONT, 11)
    y = _draw_justified_paragraph(c, p1, LM, y, WIDTH, _PPFONT, 11, LEAD)

    # Párrafo 2
    p2 = (f"Ganador(a) de la figura {figura} con el boleto No. {boleto} "
          f"del sorteo realizado el día {fsort}.")
    y = _draw_justified_paragraph(c, p2, LM, y, WIDTH, _PPFONT, 11, LEAD)

    # Caducidad
    try:
        f_sorteo = datetime.fromisoformat(fsort).date()
        f_caduca = f_sorteo + timedelta(days=30)
        hoy_pago = datetime.fromisoformat(T(payload.get("fecha_pago",""))).date()
        dias = (f_caduca - hoy_pago).days
        p3 = f"Caducidad del premio: {f_caduca.isoformat()} (quedaban {dias} días)."
        y = _draw_justified_paragraph(c, p3, LM, y, WIDTH, _PPFONT, 10, 14)
    except Exception:
        pass

    y -= 10
    p4 = "El ganador firma como constancia de haber recibido el premio ganado a conformidad."
    y = _draw_justified_paragraph(c, p4, LM, y, WIDTH, _PPFONT, 11, LEAD)

    # ---- FIRMA (más abajo) ----
    y = max(y - 48, 260)  # garantiza que quede bien abajo
    x1, x2 = LM + 140, W - RM - 140
    c.setLineWidth(1)
    c.line(x1, y, x2, y)
    y -= 18
    c.setFont(_PPFONT, 12)
    c.drawCentredString(W/2, y, cobr.upper()); y -= 14
    c.setFont(_PPFONT, 10)
    c.drawCentredString(W/2, y, f"C.I.: {T(payload.get('cobrador_ci',''))}    Telf: {T(payload.get('cobrador_tel','-'))}")
    y -= 18
    c.setFont(_PPFONT, 9)
    c.drawCentredString(W/2, y, "Firma de quien cobra")

    c.save()
    with open(out, "wb") as f:
        f.write(buf.getvalue())
    return out

# ------------------ Rutas del módulo ------------------

@app.get("/pago-premios")
def pagos_premios_view():
    try:
        return render_template("pago_premios.html", fecha_inicial=_pp_ultima_fecha_con_resultados())
    except Exception:
        f = _pp_ultima_fecha_con_resultados()
        return f"""
        <html><body style="font-family:Arial;background:#0b1324;color:#e5e7eb">
            <div style="max-width:920px;margin:40px auto;padding:16px;background:#111827;border-radius:12px;">
                <h2>Pago de premios</h2>
                <p>Instala <code>templates/pago_premios.html</code>. Por ahora, usa las APIs:</p>
                <ul>
                    <li><code>/api/premios/ultima-fecha</code></li>
                    <li><code>/api/premios-pendientes?fecha={f}</code></li>
                </ul>
            </div>
        </body></html>
        """

@app.get("/api/pagos/config")
def api_pagos_config_get():
    return jsonify({"ok": True, "config": _cfg_read()})

@app.post("/api/pagos/config")
def api_pagos_config_set():
    data = request.get_json(silent=True) or {}
    cfg = _cfg_read()
    for k in ("company_name","city_default","letterhead"):
        if k in data and isinstance(data[k], str):
            cfg[k] = data[k].strip()
    _cfg_write(cfg)
    return jsonify({"ok": True, "config": cfg})

@app.get("/api/premios/ultima-fecha")
def api_premios_ultima_fecha():
    return jsonify({"ok": True, "fecha": _pp_ultima_fecha_con_resultados()})

@app.get("/api/premios-pendientes")
def api_premios_pendientes():
    fecha = (request.args.get("fecha") or _pp_ultima_fecha_con_resultados()).strip()
    if not _pp_is_fecha_iso(fecha):
        fecha = _pp_ultima_fecha_con_resultados()

    pagos = _pp_leer_pagos_map()
    hoy = datetime.now().date()
    f_sorteo = datetime.fromisoformat(fecha).date()
    caduca = f_sorteo + timedelta(days=30)

    out = []
    for g in _pp_iter_ganadores_de_fecha(fecha) or []:
        k = _pp_premio_key(fecha, g["figura"], g["boleto"])
        pp = pagos.get(k)
        out.append({
            **g,
            "key": k,
            "pagado": bool(pp),
            "expirado": (hoy > caduca),
            "fecha_caduca": caduca.isoformat(),
            "recibo_id": (pp or {}).get("recibo_id"),
            "pagado_por": (pp or {}).get("pagado_por"),
            "fecha_pago": (pp or {}).get("fecha_pago")
        })
    return jsonify({"ok": True, "items": out})

@app.post("/api/premios/pagar")
def api_premio_pagar():
    fecha = (request.form.get("fecha") or "").strip()
    figura = (request.form.get("figura") or "").strip()
    boleto = (request.form.get("boleto") or "").strip()
    ganador_nombre = (request.form.get("ganador_nombre") or "").strip()
    premio = _safe_float(request.form.get("premio"))
    cobr_ci  = (request.form.get("cobrador_ci") or "").strip()
    cobr_nom = (request.form.get("cobrador_nombre") or "").strip()
    ciudad   = (request.form.get("ciudad") or "").strip() or _cfg_read().get("city_default","")
    empresa  = (request.form.get("empresa") or "").strip() or _cfg_read().get("company_name","")
    tel      = (request.form.get("telefono") or "").strip()

    if not (_pp_is_fecha_iso(fecha) and figura and boleto and cobr_ci and cobr_nom):
        return jsonify({"ok": False, "msg": "Datos incompletos."}), 400

    f_sorteo = datetime.fromisoformat(fecha).date()
    if datetime.now().date() > f_sorteo + timedelta(days=30):
        return jsonify({"ok": False, "msg": "Premio caducado (más de 30 días)."}), 400

    key = _pp_premio_key(fecha, figura, boleto)
    pagos = _pp_leer_pagos_map()
    if key in pagos:
        return jsonify({"ok": False, "msg": "Este premio ya fue pagado."}), 400

    pagado_por = session.get("usuario", "GLSTUDIOS")
    fecha_pago = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    recibo_id  = re.sub(r'[^A-Za-z0-9]', '', f"{fecha}-{figura}-{boleto}-{int(datetime.now().timestamp())}")

    payload = {
        "fecha_sorteo": fecha, "ciudad": ciudad, "empresa": empresa,
        "cobrador_ci": cobr_ci, "cobrador_nombre": cobr_nom, "cobrador_tel": tel,
        "ganador_nombre": ganador_nombre, "figura": figura, "boleto": boleto,
        "premio": premio, "fecha_pago": fecha_pago
    }
    try:
        _pp_generate_recibo_pdf(recibo_id, payload)
    except Exception as e:
        return jsonify({"ok": False, "msg": f"Error generando acta: {e}"}), 500

    _pp_guardar_pago_registro({
        "key": key,
        "fecha_sorteo": fecha,
        "figura": figura,
        "boleto": boleto,
        "ganador_nombre": ganador_nombre,
        "premio": f"{premio:.2f}",
        "cobrador_ci": cobr_ci,
        "cobrador_nombre": cobr_nom,
        "pagado_por": pagado_por,
        "fecha_pago": fecha_pago,
        "recibo_id": recibo_id
    })
    return jsonify({"ok": True, "recibo": f"/recibos/{recibo_id}.pdf", "recibo_id": recibo_id})

@app.get("/recibos/<rid>.pdf")
def pagos_descargar_recibo(rid):
    p = os.path.join(RECIBOS_DIR, f"{rid}.pdf")
    if not os.path.exists(p):
        return "No encontrado", 404
    return send_file(p, as_attachment=False, download_name=f"{rid}.pdf", mimetype="application/pdf")



#FIN PAGO DE PREOS





#SORTEOS CODIGOS GENERALES #

# -*- coding: utf-8 -*-
# GL Bingo — Sorteo + XMLs vMix (ventas, figuras, spinners, reintegro)
# Versión unificada: guarda XMLs en DATA/static/db y espejo en static/db

from flask import Flask, render_template, request, jsonify, redirect, url_for, send_from_directory
import os, re
from datetime import date, datetime
import xml.etree.ElementTree as ET


app.secret_key = "glbingo"

# -------------------- Paths base --------------------
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR  = os.path.join(BASE_DIR, "static")
DATA_DIR    = os.path.join(BASE_DIR, "DATA")                 # carpeta de datos viva
DB_STATIC   = os.path.join(STATIC_DIR, "db")                 # espejo servible por /static/db/...
DB_DATA     = os.path.join(DATA_DIR, "static", "db")         # **principal** para Juego

# asegurar directorios
for d in (STATIC_DIR, DB_STATIC, DATA_DIR, DB_DATA, os.path.join(DB_DATA, "spinners"), os.path.join(STATIC_DIR, "LOGS")):
    os.makedirs(d, exist_ok=True)

LOGS_DIR = os.path.join(STATIC_DIR, "LOGS")  # tus logs ya están bajo static

# --------------- Helpers de escritura ---------------
def _write_xml_both(tree: ET.ElementTree, relpath: str):
    """Escribe el XML tanto en DATA/static/db/<relpath> como en static/db/<relpath>."""
    # destino en DATA
    dst_data   = os.path.join(DB_DATA, relpath)
    os.makedirs(os.path.dirname(dst_data), exist_ok=True)
    tree.write(dst_data, encoding="utf-8", xml_declaration=True)
    # espejo en STATIC
    dst_static = os.path.join(DB_STATIC, relpath)
    os.makedirs(os.path.dirname(dst_static), exist_ok=True)
    tree.write(dst_static, encoding="utf-8", xml_declaration=True)
    return {"data": dst_data, "static": dst_static}

def _write_text_both(text: str, relpath: str):
    dst_data   = os.path.join(DB_DATA, relpath)
    dst_static = os.path.join(DB_STATIC, relpath)
    os.makedirs(os.path.dirname(dst_data), exist_ok=True)
    os.makedirs(os.path.dirname(dst_static), exist_ok=True)
    with open(dst_data, "w", encoding="utf-8") as f:   f.write(text)
    with open(dst_static, "w", encoding="utf-8") as f: f.write(text)
    return {"data": dst_data, "static": dst_static}

# --------------- Rutas de archivos (relativas) ---------------
# Entradas
FIGS_XML_REL        = "figuras_por_fecha.xml"
ASIG_XML_REL        = "asignaciones.xml"
IMP_XML_PATH        = os.path.join(LOGS_DIR, "impresiones.xml")  # ya estabas en static/LOGS
CATALOGO_FIGXML_REL = "datos_figuras.xml"                        # opcional

# Salidas vMix (todas en /db)
VMIX_VENTAS_REL       = "vmix_ventas.xml"
VMIX_FIG_NOMB_REL     = "vmix_figuras_nombres.xml"
VMIX_FIG_COLORES_REL  = "vmix_figuras_colores.xml"
VMIX_FIG_GRID_REL     = "vmix_figuras.xml"            # 25 celdas
VMIX_SPINNERS_REL     = "vmix_spinners.xml"           # PRIORIDAD para Juego
STD_SPINNERS_REL      = "spinners.xml"                # Fallback para Juego
VMIX_REINTEGRO_REL    = "vmix_reintegro.xml"

# Nuevos pedidos
XML_FIGURAS_LISTA_REL = "xml_figuras_lista.xml"       # presentación (25 columnas)
XML_FIGURAS_2COL_REL  = "xml_figuras.xml"             # tablero (2 columnas)
SPINNERS_HIST_DIR_REL = "spinners"                    # carpeta para YYYY-MM-DD.xml

# Para leer entradas, preferimos DATA si existe; fallback a STATIC
def _in_db_existing(relname: str) -> str:
    p_data   = os.path.join(DB_DATA, relname)
    p_static = os.path.join(DB_STATIC, relname)
    if os.path.exists(p_data):   return p_data
    if os.path.exists(p_static): return p_static
    return p_data  # por defecto apuntamos a DATA

# --------------- Constantes de tablero ---------------
COLOR_ON  = "#ff0037"
COLOR_OFF = "#E8E8E8"

POS_25_ROW = [
    "B1","I1","N1","G1","O1",
    "B2","I2","N2","G2","O2",
    "B3","I3","N3","G3","O3",
    "B4","I4","N4","G4","O4",
    "B5","I5","N5","G5","O5",
]
POS_25_COL = [
    "B1","B2","B3","B4","B5",
    "I1","I2","I3","I4","I5",
    "N1","N2","N3","N4","N5",
    "G1","G2","G3","G4","G5",
    "O1","O2","O3","O4","O5",
]

# ---------------- Utils ----------------
def _parse_float(x):
    try:
        return float(str(x).replace(",", "."))
    except:
        return 0.0

def _fmt_int(x):
    try:
        n = int(round(float(x)))
        return str(n)
    except:
        return "0"

def code_for(name: str) -> str:
    n = (name or "").strip().upper()
    if n.startswith("TABLA LLENA 1"): return "TL1"
    if n.startswith("TABLA LLENA 2"): return "TL2"
    if n.startswith("TABLA LLENA 3"): return "TL3"
    if n.startswith("TABLA LLENA 4"): return "TL4"
    return re.sub(r"[^A-Z0-9]", "", n)[:4] or "FIG"

def _san4(v: str) -> str:
    """Normaliza string a 4 dígitos (0-9). Vacío => ''."""
    if v is None: return ""
    v = re.sub(r"\D", "", str(v))[:4]
    return v.zfill(4) if v else ""

# ---------------- Lecturas ----------------
def get_figuras_del_dia(fecha):
    """TL1..TL4 + resto (nombre/valor) desde figuras_por_fecha.xml."""
    tl = [0.0, 0.0, 0.0, 0.0]
    resto = []
    FIGS_XML = _in_db_existing(FIGS_XML_REL)
    if not os.path.exists(FIGS_XML):
        return tl, resto
    root = ET.parse(FIGS_XML).getroot()
    dia = root.find(f".//dia[@fecha='{fecha}']")
    if dia is None:
        return tl, resto
    for fig in dia.findall("fig"):
        nombre = (fig.attrib.get("nombre","") or "").strip()
        val    = _parse_float(fig.attrib.get("valor","0"))
        low    = nombre.lower()
        if "llena" in low and "1" in low:   tl[0] = val
        elif "llena" in low and "2" in low: tl[1] = val
        elif "llena" in low and "3" in low: tl[2] = val
        elif "llena" in low and "4" in low: tl[3] = val
        else:
            resto.append({"nombre": nombre, "valor": _fmt_int(val)})
    return tl, resto

def get_asignaciones_del_dia(fecha):
    """
    Lee asignaciones.xml para una fecha y devuelve rangos asignados.
    Devuelve lista de dicts con:
      - desde, hasta
      - vendedor (seudónimo o nombre)
      - planilla (número/id si existe)
      - rango (texto 'a-b')
      - serie_archivo (si la planilla lo trae)
    """
    filas = []
    ASIG_XML = _in_db_existing(ASIG_XML_REL)
    if not os.path.exists(ASIG_XML):
        return filas
    root = ET.parse(ASIG_XML).getroot()
    dia = root.find(f".//dia[@fecha='{fecha}']")
    if dia is None:
        return filas

    for vend in dia.findall("vendedor"):
        nom = vend.attrib.get("seudonimo") or (
            " ".join([vend.attrib.get("nombre", ""), vend.attrib.get("apellido", "")]).strip() or "—"
        )

        for p in vend.findall("planilla"):
            r = (p.attrib.get("rango", "") or "").strip()
            if r and "-" in r:
                a, b = r.split("-", 1)
                desde, hasta = a.strip(), b.strip()
            else:
                desde = p.attrib.get("desde", "") or p.attrib.get("inicio", "") or "0"
                hasta = p.attrib.get("hasta", "") or p.attrib.get("fin", "") or "0"

            plan_num = (p.attrib.get("numero") or p.attrib.get("planilla") or p.attrib.get("id") or "").strip()
            serie_archivo = (p.attrib.get("serie_archivo") or p.attrib.get("serie") or "").strip()

            # normaliza rango para mostrar en UI/PDF
            rango_txt = r.strip() if r else (f"{desde}-{hasta}" if str(desde).strip() and str(hasta).strip() else "")

            filas.append({
                "desde": desde,
                "hasta": hasta,
                "vendedor": nom,
                "planilla": plan_num,
                "rango": rango_txt,
                "serie_archivo": serie_archivo,
            })

    return filas


def _serie_equal(a: str, b: str) -> bool:
    """Compara series ignorando carpetas (Srs_ib1.csv vs data/Srs_ib1.csv)."""
    a = (a or "").strip()
    b = (b or "").strip()
    if not a or not b:
        return True
    try:
        return os.path.basename(a) == os.path.basename(b)
    except Exception:
        return a == b


def buscar_info_por_boleto(fecha, boleto, serie_archivo: str = ""):
    """
    Devuelve dict con vendedor/planilla/rango para un boleto (tabla) dentro del rango asignado.
    Si serie_archivo se proporciona y en asignaciones viene 'serie_archivo', se filtra por serie.
    """
    try:
        num = int(str(boleto).strip())
    except Exception:
        return {}

    serie_archivo = (serie_archivo or "").strip()
    for f in get_asignaciones_del_dia(fecha):
        try:
            a = int(re.sub(r"\D", "", str(f.get("desde", ""))) or 0)
            b = int(re.sub(r"\D", "", str(f.get("hasta", ""))) or 0)
        except Exception:
            continue

        if not (a <= num <= b):
            continue

        # si tenemos serie, intentamos hacer match con la serie guardada en la planilla
        s2 = (f.get("serie_archivo") or "").strip()
        if serie_archivo and s2 and not _serie_equal(serie_archivo, s2):
            continue

        return f

    return {}


def buscar_vendedor_por_boleto(fecha, boleto):
    info = buscar_info_por_boleto(fecha, boleto)
    return (info.get("vendedor") or "").strip()


def get_impresiones_info(fecha):
    serie = "—"; primer = 0; ultimo = 0; total_b = 0; valor_b = 0; rein = "—"
    if not os.path.exists(IMP_XML_PATH):
        return dict(
            serie_detectada=serie, primer_boleto=str(primer), ultimo_boleto=str(ultimo),
            boletos_impresos=_fmt_int(total_b), valor_boleto=_fmt_int(valor_b), reintegro_dia=rein
        )
    root = ET.parse(IMP_XML_PATH).getroot()
    primera = None; ultima  = None
    for n in root.findall("impresion"):
        if n.attrib.get("tipo") != "boletos": continue
        if (n.findtext("fecha_sorteo") or "").strip() != fecha: continue
        try: total_b += int(n.findtext("total_boletos") or "0")
        except: pass
        valor_b = _parse_float(n.findtext("valor") or "0")
        if (n.findtext("reintegro_especial") or "").strip():
            rein = n.findtext("reintegro_especial").strip()
        try:
            d = int(n.attrib.get("desde","0") or 0)
            h = int(n.attrib.get("hasta","0") or 0)
            if primera is None or d < primera: primera = d
            if ultima  is None or h > ultima:  ultima  = h
        except: pass
        if n.attrib.get("serie_archivo"): serie = n.attrib.get("serie_archivo")
    primer = primera or 0
    ultimo = ultima or 0
    return dict(
        serie_detectada=serie, primer_boleto=str(primer), ultimo_boleto=str(ultimo),
        boletos_impresos=_fmt_int(total_b), valor_boleto=_fmt_int(valor_b), reintegro_dia=rein
    )

# --------- Catálogo de figuras dibujadas (opcional) ----------
def load_catalogo_figuras():
    """Índice por código con sus celdas."""
    catalogo = {}
    CATALOGO_FIGXML = _in_db_existing(CATALOGO_FIGXML_REL)
    if not os.path.exists(CATALOGO_FIGXML):
        return catalogo
    root = ET.parse(CATALOGO_FIGXML).getroot()
    for f in root.findall(".//figura"):
        nombre = (f.attrib.get("nombre","") or "").strip()
        codigo = code_for(nombre)
        cbloq  = f.attrib.get("centro_bloqueado","0")
        celdas = []
        for c in f.findall("celda"):
            idx   = int(c.attrib.get("idx","0") or 0)
            color = (c.attrib.get("color","#FFFFFF") or "#FFFFFF").upper()
            pos   = c.attrib.get("pos") or (POS_25_ROW[idx-1] if 1 <= idx <= 25 else "B1")
            celdas.append({"idx": idx, "color": color, "pos": pos})
        if len(celdas) < 25:
            ya = {x["idx"] for x in celdas}
            for i in range(1,26):
                if i not in ya:
                    celdas.append({"idx": i, "color": "#FFFFFF", "pos": POS_25_ROW[i-1]})
            celdas.sort(key=lambda x:x["idx"])
        catalogo[codigo] = {"nombre": nombre, "centro_bloqueado": cbloq, "celdas": celdas}
    return catalogo

# ======================== Escritura de XMLs ========================
def grid_colors_for(codigo, catalogo):
    """25 colores ON/OFF para una figura."""
    if codigo in ("TL1","TL2") and codigo not in catalogo:
        return [COLOR_ON] * 25
    if codigo not in catalogo:
        return [COLOR_OFF] * 25
    cols = []
    for cel in sorted(catalogo[codigo]["celdas"], key=lambda x:x["idx"]):
        raw = (cel["color"] or "#FFFFFF").upper()
        on = raw not in ("#FFFFFF", "#FFF", "#FFFFFF00", "TRANSPARENT")
        cols.append(COLOR_ON if on else COLOR_OFF)
    if len(cols) < 25:
        cols += [COLOR_OFF] * (25 - len(cols))
    return cols[:25]

def write_vmix_ventas(fecha, imp):
    root = ET.Element("ventas", {"fecha": fecha})
    ET.SubElement(root, "serie").text            = imp["serie_detectada"]
    ET.SubElement(root, "primer_boleto").text    = imp["primer_boleto"]
    ET.SubElement(root, "ultimo_boleto").text    = imp["ultimo_boleto"]
    ET.SubElement(root, "valor_boleto").text     = _fmt_int(imp["valor_boleto"])
    ET.SubElement(root, "boletos_impresos").text = _fmt_int(imp["boletos_impresos"])
    _write_xml_both(ET.ElementTree(root), VMIX_VENTAS_REL)

def write_vmix_figuras_listas(fecha, tl, resto):
    """vmix_figuras_nombres.xml y vmix_figuras_colores.xml. Retorna lista ordenada del día."""
    fig_elegidas = []
    if tl[0] > 0: fig_elegidas.append({"nombre":"Tabla Llena 1","valor":_fmt_int(tl[0])})
    if tl[1] > 0: fig_elegidas.append({"nombre":"Tabla Llena 2","valor":_fmt_int(tl[1])})
    if tl[2] > 0: fig_elegidas.append({"nombre":"Tabla Llena 3","valor":_fmt_int(tl[2])})
    if tl[3] > 0: fig_elegidas.append({"nombre":"Tabla Llena 4","valor":_fmt_int(tl[3])})
    fig_elegidas += resto

    root = ET.Element("figuras_nombres", {"fecha": fecha})
    for f in fig_elegidas:
        ET.SubElement(root, "fig", {"nombre": f["nombre"], "valor": f["valor"]})
    _write_xml_both(ET.ElementTree(root), VMIX_FIG_NOMB_REL)

    root2 = ET.Element("figuras_colores", {"fecha": fecha})
    for f in fig_elegidas:
        ET.SubElement(root2, "fig", {"nombre": f["nombre"], "valor": f["valor"], "codigo": code_for(f["nombre"]), "color": ""})
    _write_xml_both(ET.ElementTree(root2), VMIX_FIG_COLORES_REL)

    return fig_elegidas

def write_vmix_figuras_grid(fecha, figuras_dia, catalogo):
    """vmix_figuras.xml (cada figura con 25 celdas idx/pos/color)."""
    root = ET.Element("figuras")
    ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for f in figuras_dia:
        nombre = f["nombre"]; codigo = code_for(nombre)
        nodo_f = ET.SubElement(root, "figura", {
            "nombre": nombre, "fecha": ahora,
            "centro_bloqueado": "1" if (codigo in catalogo and catalogo[codigo].get("centro_bloqueado","0") == "1") else "0"
        })
        cols = grid_colors_for(codigo, catalogo)
        for i, col in enumerate(cols, start=1):
            ET.SubElement(nodo_f, "celda", {"idx": str(i), "color": col, "pos": POS_25_ROW[i-1]})
    _write_xml_both(ET.ElementTree(root), VMIX_FIG_GRID_REL)

def write_xml_figuras_lista_presentacion(fecha, figuras_dia, catalogo):
    """
    <juego><filaFiguras> ... 25 columnas en orden B1..B5,I1..I5,N1..N5,G1..G5,O1..O5 </filaFiguras></juego>
    """
    root = ET.Element("juego")
    ident = 1
    for f in figuras_dia:
        nombre = f["nombre"]; valor = f["valor"]; codigo = code_for(nombre)
        fila = ET.SubElement(root, "filaFiguras")
        ET.SubElement(fila, "figuraIDENTIFICADOR").text = str(ident)
        ET.SubElement(fila, "figuraNOMBRE").text        = nombre
        ET.SubElement(fila, "figuraVALOR").text         = valor
        ET.SubElement(fila, "figuraESTADO").text        = "inactivo"

        cols = grid_colors_for(codigo, catalogo)
        pos_to_col = {POS_25_ROW[i]: cols[i] for i in range(25)}
        for lab in POS_25_COL:  # orden columna-primero
            ET.SubElement(fila, f"figura{lab}").text = pos_to_col[lab]
        ident += 1
    _write_xml_both(ET.ElementTree(root), XML_FIGURAS_LISTA_REL)

def write_xml_figuras_tablero_2columnas(fecha, figuras_dia):
    """
    <juego fecha="..."><filaTablero><colA>Nombre|Valor|Estado</colA><colB>...</colB></filaTablero></juego>
    """
    root = ET.Element("juego", {"fecha": fecha})
    fila = ET.SubElement(root, "filaTablero")
    a = figuras_dia[0] if len(figuras_dia) >= 1 else None
    b = figuras_dia[1] if len(figuras_dia) >= 2 else None
    def pack(fig): return f"{fig['nombre']}|{fig['valor']}|inactivo" if fig else ""
    ET.SubElement(fila, "colA").text = pack(a)
    ET.SubElement(fila, "colB").text = pack(b)
    _write_xml_both(ET.ElementTree(root), XML_FIGURAS_2COL_REL)

# ================== Spinners (estándar) ==================
def make_spinners_tree(vals, fecha_iso: str):
    root = ET.Element("spinners", {"fecha": fecha_iso})
    for i in range(20):
        v = _san4(vals[i] if i < len(vals) else "")
        n = ET.SubElement(root, "n", {"i": str(i+1)})
        if v:
            n.set("v", v)
    return ET.ElementTree(root)

def save_spinners(vals, fecha_iso: str | None = None):
    """
    Guarda spinners en:
      - vmix_spinners.xml (prioridad para Juego)
      - spinners.xml      (fallback)
      - spinners/YYYY-MM-DD.xml (histórico)
    Y en **ambas ubicaciones**: DATA/static/db y static/db.
    """
    if not fecha_iso:
        fecha_iso = date.today().isoformat()
    tree = make_spinners_tree(vals, fecha_iso)

    _write_xml_both(tree, VMIX_SPINNERS_REL)
    _write_xml_both(tree, STD_SPINNERS_REL)
    # histórico por fecha
    hist_rel = os.path.join(SPINNERS_HIST_DIR_REL, f"{fecha_iso}.xml")
    _write_xml_both(tree, hist_rel)

    return {
        "vmix": os.path.join(DB_DATA, VMIX_SPINNERS_REL),
        "std":  os.path.join(DB_DATA, STD_SPINNERS_REL),
        "hist": os.path.join(DB_DATA, hist_rel),
    }

def read_spinners_current():
    """Devuelve lista de 20 (4 dígitos) desde vmix_spinners.xml o spinners.xml."""
    for rel in (VMIX_SPINNERS_REL, STD_SPINNERS_REL):
        p = _in_db_existing(rel)
        if os.path.exists(p):
            try:
                root = ET.parse(p).getroot()
                out=[]
                for n in root.findall(".//n"):
                    v = n.attrib.get("v") or (n.text or "")
                    v = _san4(v)
                    out.append(v if v else "")
                return (out + [""]*20)[:20]
            except:
                pass
    return [""]*20

def write_vmix_reintegro(fecha, reinteg_name):
    root = ET.Element("reintegro", {"fecha": fecha})
    ET.SubElement(root, "archivo").text = reinteg_name or ""
    ET.SubElement(root, "ruta").text    = "static/REINTEGROS/" + (reinteg_name or "")
    _write_xml_both(ET.ElementTree(root), VMIX_REINTEGRO_REL)

# ---------------- Rutas ----------------

from flask import render_template, request

@app.route("/juego/spinner_overlay")
def spinner_overlay():
    return render_template("spinner_overlay.html")




@app.route("/")
def root():
    return redirect(url_for("sorteo", fecha=date.today().isoformat()))

@app.route("/sorteo")
def sorteo():
    fecha = request.args.get("fecha") or date.today().isoformat()
    imp = get_impresiones_info(fecha)
    tl, resto = get_figuras_del_dia(fecha)
    asignaciones = get_asignaciones_del_dia(fecha)
    total_boletos_x_valor = int(_fmt_int(imp["boletos_impresos"])) * int(_fmt_int(imp["valor_boleto"]))
    total_premios = int(round(sum(tl) + sum(_parse_float(f["valor"]) for f in resto)))
    return render_template(
        "sorteo.html",
        fecha=fecha,
        serie_detectada=imp["serie_detectada"],
        primer_boleto=imp["primer_boleto"],
        ultimo_boleto=imp["ultimo_boleto"],
        reintegro_dia=imp["reintegro_dia"],
        valor_boleto=_fmt_int(imp["valor_boleto"]),
        boletos_impresos=_fmt_int(imp["boletos_impresos"]),
        total_a_jugar=_fmt_int(total_boletos_x_valor),
        total_premios=_fmt_int(total_premios),
        tl1=_fmt_int(tl[0]), tl2=_fmt_int(tl[1]), tl3=_fmt_int(tl[2]), tl4=_fmt_int(tl[3]),
        figs_resto=resto,
        asignaciones=asignaciones
    )

@app.route("/api/vendedor-por-boleto", methods=["GET","POST"])
def api_vend_boleto():
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        fecha  = data.get("fecha",""); boleto = data.get("boleto","")
    else:
        fecha  = request.args.get("fecha",""); boleto = request.args.get("boleto","")
    vendedor = buscar_vendedor_por_boleto(fecha, boleto)
    return jsonify(ok=True, vendedor=vendedor)

# --------- NUEVOS endpoints de spinners ---------
@app.get("/api/spinners")
def api_spinners_get():
    return jsonify(ok=True, spinners=read_spinners_current())

@app.post("/api/spinners/guardar")
def api_spinners_guardar():
    data  = request.get_json(silent=True) or {}
    fecha = data.get("fecha") or date.today().isoformat()
    vals  = data.get("spinners", [])
    files = save_spinners(vals, fecha)
    return jsonify(ok=True, files=files, fecha=fecha)

# --------- Activar sorteo (escribe TODO) ---------
@app.post("/api/activar-sorteo")
def sorteo_activar():
    data  = request.get_json(silent=True) or {}
    fecha = data.get("fecha")
    spins = data.get("spinners", [])
    if not fecha:
        return jsonify(ok=False, mensaje="Falta la fecha")

    imp = get_impresiones_info(fecha)
    tl, resto = get_figuras_del_dia(fecha)

    # 1) ventas
    write_vmix_ventas(fecha, imp)

    # 2) listas (nombres y códigos)
    figuras_dia = write_vmix_figuras_listas(fecha, tl, resto)

    # 3) grid 25 celdas
    catalogo = load_catalogo_figuras()
    write_vmix_figuras_grid(fecha, figuras_dia, catalogo)

    # 4) PRESENTACIÓN (25 columnas en el orden correcto)
    write_xml_figuras_lista_presentacion(fecha, figuras_dia, catalogo)

    # 5) TABLERO (2 columnas)
    write_xml_figuras_tablero_2columnas(fecha, figuras_dia)

    # 6) spinners y reintegro (GUARDADO ESTÁNDAR => Juego los ve)
    save_spinners(spins, fecha)
    write_vmix_reintegro(fecha, imp["reintegro_dia"])

    return jsonify(ok=True, mensaje="XMLs generados/reemplazados correctamente.")

# --------- (Opcional) servir DATA por URL para depurar ---------
@app.route("/data-db/<path:rel>")
def serve_data_db(rel):
    """Útil para ver que realmente se escribió en DATA/static/db/."""
    return send_from_directory(DB_DATA, rel, as_attachment=False)

# ----------------- MAIN -----------------
if False and __name__ == "__main__":  # DESHABILITADO (evita arrancar antes de cargar rutas)
    app.run(debug=True)




#FIN SORTEO #





# ================= CONTABILIDAD: helpers y rutas =================
# Seguridad por rol, gastos, banco, resumen, y endpoints de curvas por vendedor

import os
import xml.etree.ElementTree as ET
from datetime import datetime, date, timedelta
from flask import jsonify, render_template, request, redirect, url_for, session, flash
from werkzeug.utils import secure_filename
from io import BytesIO
try:
    from PIL import Image, ImageOps
except Exception:
    Image = None
    ImageOps = None

# === Comprobantes (subidas) ===
ALLOWED_EXTS = {"pdf", "png", "jpg", "jpeg", "webp"}

# Guardado PERSISTENTE: todo va a DATA_DIR/static/CONTABILIDAD/...
# y se "espeja" a /static/CONTABILIDAD/... para que el navegador pueda abrirlo.
import shutil

PUBLIC_STATIC_DIR   = os.path.join(BASE_DIR, "static")
PERSIST_STATIC_DIR  = os.path.join(DATA_DIR, "static")
PERSIST_CONTAB_DIR  = os.path.join(PERSIST_STATIC_DIR, "CONTABILIDAD")

COMPROB_DIR         = os.path.join(PERSIST_CONTAB_DIR, "comprobantes")
BANK_FILES          = os.path.join(COMPROB_DIR, "banco")
GASTO_FILES         = os.path.join(COMPROB_DIR, "gastos")

PUBLIC_COMPROB_DIR  = os.path.join(PUBLIC_STATIC_DIR, "CONTABILIDAD", "comprobantes")
PUBLIC_BANK_FILES   = os.path.join(PUBLIC_COMPROB_DIR, "banco")
PUBLIC_GASTO_FILES  = os.path.join(PUBLIC_COMPROB_DIR, "gastos")

os.makedirs(BANK_FILES, exist_ok=True)
os.makedirs(GASTO_FILES, exist_ok=True)
os.makedirs(PUBLIC_BANK_FILES, exist_ok=True)
os.makedirs(PUBLIC_GASTO_FILES, exist_ok=True)

def _mirror_persist_static_to_public(persist_abs: str) -> str | None:
    """Copia un archivo dentro de DATA_DIR/static/... hacia BASE_DIR/static/... y devuelve la ruta pública."""
    try:
        if not persist_abs or not os.path.exists(persist_abs):
            return None
        persist_abs_norm = os.path.abspath(persist_abs)
        persist_root = os.path.abspath(PERSIST_STATIC_DIR)
        if os.path.commonpath([persist_abs_norm, persist_root]) != persist_root:
            return None
        # persist_abs debería estar dentro de DATA_DIR/static
        rel = os.path.relpath(persist_abs, PERSIST_STATIC_DIR).replace("\\", "/")
        public_abs = os.path.join(PUBLIC_STATIC_DIR, rel.replace("/", os.sep))
        os.makedirs(os.path.dirname(public_abs), exist_ok=True)
        shutil.copy2(persist_abs, public_abs)
        return public_abs
    except Exception as e:
        print(f"[WARN] mirror static falló: {e}")
        return None

def _ext_ok(filename: str) -> bool:
    ext = os.path.splitext(filename or "")[1].lower().lstrip(".")
    return ext in ALLOWED_EXTS

def _save_upload(fs, folder: str, base: str) -> str:
    """Guarda comprobante en persistente y retorna ruta relativa desde /static.

    - Si es imagen (png/jpg/jpeg/webp): la comprime y la guarda como .jpg (ligera).
    - Si es PDF: la guarda tal cual.
    """
    fname = secure_filename(fs.filename or "")
    ext0 = os.path.splitext(fname)[1].lower().lstrip(".")
    if not ext0 or ext0 not in ALLOWED_EXTS:
        raise ValueError("extensión no permitida")

    # Límite duro de subida (evita reventar el servidor con fotos gigantes)
    try:
        if request.content_length and request.content_length > 25 * 1024 * 1024:  # 25MB
            raise ValueError("archivo-demasiado-grande")
    except Exception:
        pass

    is_img = ext0 in {"png", "jpg", "jpeg", "webp"}
    if is_img and Image is not None:
        # Siempre guardamos imágenes como JPG comprimido
        ext = ".jpg"
        persist_path = os.path.join(folder, f"{base}{ext}")
        os.makedirs(os.path.dirname(persist_path), exist_ok=True)

        try:
            raw = fs.read()
            fs.stream.seek(0)
            img = Image.open(BytesIO(raw))
            if ImageOps is not None:
                img = ImageOps.exif_transpose(img)

            if img.mode != "RGB":
                img = img.convert("RGB")

            # Redimensionar (recibos/fotos de celular suelen venir enormes)
            max_dim = 1600
            if max(img.size) > max_dim:
                img.thumbnail((max_dim, max_dim))

            # Guardado con compresión adaptativa (objetivo <= ~650KB)
            target = 650 * 1024
            for q in (80, 74, 68, 62, 56):
                tmp = BytesIO()
                img.save(tmp, format="JPEG", quality=q, optimize=True, progressive=True)
                if tmp.tell() <= target or q == 56:
                    with open(persist_path, "wb") as f:
                        f.write(tmp.getvalue())
                    break
        except Exception:
            # Fallback: si por alguna razón falla Pillow, guardamos el original sin romper el flujo
            persist_path = os.path.join(folder, f"{base}.{ext0}")
            os.makedirs(os.path.dirname(persist_path), exist_ok=True)
            fs.save(persist_path)
    else:
        # PDF (o sin Pillow): guardar tal cual
        ext = "." + ext0
        persist_path = os.path.join(folder, f"{base}{ext}")
        os.makedirs(os.path.dirname(persist_path), exist_ok=True)
        fs.save(persist_path)

    # espejo -> carpeta pública /static
    public_abs = _mirror_persist_static_to_public(persist_path)
    if public_abs and os.path.exists(public_abs):
        rel = os.path.relpath(public_abs, PUBLIC_STATIC_DIR).replace("\\", "/")
        return rel

    # fallback: si no se pudo espejar, devolvemos una ruta "segura" sin .. (solo nombre)
    return f"CONTABILIDAD/comprobantes/{os.path.basename(folder)}/{os.path.basename(persist_path)}".replace("\\", "/")

# ---- Archivo de gastos ----

GASTOS_XML = globals().get("CONTAB_GASTOS_XML", _persist('static', 'CONTABILIDAD', 'gastos.xml'))
os.makedirs(os.path.dirname(GASTOS_XML), exist_ok=True)
if not os.path.exists(GASTOS_XML):
    ET.ElementTree(ET.Element('gastos')).write(GASTOS_XML, encoding='utf-8', xml_declaration=True)
_mirror_persist_static_to_public(GASTOS_XML)

# ---- Auditoría (registro de acciones contables) ----
AUDIT_XML = _persist('static', 'CONTABILIDAD', 'auditoria.xml')
os.makedirs(os.path.dirname(AUDIT_XML), exist_ok=True)
if not os.path.exists(AUDIT_XML):
    ET.ElementTree(ET.Element('auditoria')).write(AUDIT_XML, encoding='utf-8', xml_declaration=True)
_mirror_persist_static_to_public(AUDIT_XML)

def _audit_event(modulo: str, accion: str, ref: str = "", extra: dict | None = None):
    """Guarda un evento de auditoría (quién, cuándo, IP y detalle)."""
    extra = extra or {}
    try:
        tree, root = _xml_read(AUDIT_XML)
    except Exception:
        # si por alguna razón falla la lectura, recreamos
        root = ET.Element('auditoria')
        tree = ET.ElementTree(root)

    now = datetime.now()
    eid = str(int(now.timestamp()*1000))
    e = ET.SubElement(root, "evento", {"id": eid})
    ET.SubElement(e, "fecha").text = now.date().isoformat()
    ET.SubElement(e, "hora").text = now.strftime("%H:%M:%S")
    ET.SubElement(e, "timestamp").text = now.isoformat(timespec="seconds")
    ET.SubElement(e, "usuario").text = (session.get("usuario") if session else "") or ""
    ET.SubElement(e, "rol").text = (session.get("rol") if session else "") or ""
    ET.SubElement(e, "ip").text = (request.remote_addr if request else "") or ""
    ET.SubElement(e, "modulo").text = modulo or ""
    ET.SubElement(e, "accion").text = accion or ""
    ET.SubElement(e, "ref").text = ref or ""

    det = ET.SubElement(e, "detalle")
    for k, v in (extra or {}).items():
        it = ET.SubElement(det, "d", {"k": str(k)})
        it.text = str(v)

    _xml_write(tree, AUDIT_XML)
    return eid

def _is_admin() -> bool:
    rol_n = _normalize(session.get('rol', '') or '')
    return rol_n in {'administrador', 'admin', 'super administrador', 'superadministrador', 'superadmin'}

def _require_super() -> bool:
    return _is_superadmin()

def _client_ip() -> str:
    return request.headers.get("X-Forwarded-For", request.remote_addr) if request else ""

def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")

def _now_hora() -> str:
    return datetime.now().strftime("%H:%M:%S")

def _safe_backup_copy(src: str, dst_dir: str):
    try:
        if src and os.path.exists(src):
            os.makedirs(dst_dir, exist_ok=True)
            base = os.path.basename(src)
            shutil.copy2(src, os.path.join(dst_dir, base))
    except Exception as e:
        print("[WARN] backup copy failed:", e)

def _reset_xml(path: str, root_tag: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    ET.ElementTree(ET.Element(root_tag)).write(path, encoding='utf-8', xml_declaration=True)
    _mirror_persist_static_to_public(path)



def _xml_read(path):
    tree = ET.parse(path)
    return tree, tree.getroot()

def _xml_write(tree, path):
    try:
        ET.indent(tree, space="  ", level=0)
    except Exception:
        pass
    tree.write(path, encoding='utf-8', xml_declaration=True)
    _mirror_persist_static_to_public(path)

# ---- Gastos CRUD ----
def _gasto_row(elem):
    return {
        "id": elem.get("id"),
        "fecha": elem.findtext("fecha", ""),
        "hora": elem.findtext("hora", ""),
        "categoria": elem.findtext("categoria", ""),
        "medio": elem.findtext("medio", ""),     # caja | banco
        "banco": elem.findtext("banco", ""),
        "monto": float(elem.findtext("monto", "0") or 0),
        "descripcion": elem.findtext("descripcion", ""),
        "creado_por": elem.findtext("creado_por", ""),
        "creado_rol": elem.findtext("creado_rol", ""),
        "creado_ip": elem.findtext("creado_ip", ""),
        "creado_en": elem.findtext("creado_en", ""),
        "comprobante": elem.findtext("comprobante", ""),
    }

def _gastos_list(desde_iso, hasta_iso):
    _, root = _xml_read(GASTOS_XML)
    out = []
    for g in root.findall("gasto"):
        f = g.findtext("fecha", "")
        if not f:
            continue
        if f >= desde_iso and f <= hasta_iso:
            out.append(_gasto_row(g))
    out.sort(key=lambda x: (x["fecha"], x["id"]))
    return out

def _gasto_add(data, usuario, comp_path=None, gid_forced=None, monto_comprobante=None,
              ip=None, rol=None, creado_en=None):
    tree, root = _xml_read(GASTOS_XML)
    now = datetime.now()
    gid = gid_forced or str(int(now.timestamp()*1000))
    g = ET.SubElement(root, "gasto", {"id": gid})

    fecha = (data.get("fecha") or date.today().isoformat())
    hora  = (data.get("hora")  or now.strftime("%H:%M:%S"))
    ET.SubElement(g, "fecha").text = fecha
    ET.SubElement(g, "hora").text  = hora
    ET.SubElement(g, "categoria").text = (data.get("categoria") or "Gasto")
    ET.SubElement(g, "medio").text = (data.get("medio") or "caja")
    ET.SubElement(g, "banco").text = (data.get("banco") or data.get("cuenta") or "")
    ET.SubElement(g, "monto").text = str(float(data.get("monto") or 0))
    ET.SubElement(g, "descripcion").text = (data.get("descripcion") or "")

    ET.SubElement(g, "creado_por").text = (usuario or "sistema")
    ET.SubElement(g, "creado_rol").text = (rol or session.get("rol", "") or "")
    ET.SubElement(g, "creado_ip").text  = (ip or (request.remote_addr if request else "") or "")
    ET.SubElement(g, "creado_en").text  = (creado_en or now.isoformat(timespec="seconds"))

    if comp_path:
        ET.SubElement(g, "comprobante").text = comp_path
    if monto_comprobante is not None:
        ET.SubElement(g, "monto_comprobante").text = str(float(monto_comprobante))

    _xml_write(tree, GASTOS_XML)
    return gid

def _gasto_delete(gid):
    tree, root = _xml_read(GASTOS_XML)
    for g in root.findall("gasto"):
        if g.get("id") == gid:
            root.remove(g); _xml_write(tree, GASTOS_XML); return True
    return False

# ---- Auxiliares generales ----
def _daterange(d1_iso, d2_iso):
    d1 = datetime.fromisoformat(d1_iso).date()
    d2 = datetime.fromisoformat(d2_iso).date()
    curr = d1
    while curr <= d2:
        yield curr.isoformat()
        curr += timedelta(days=1)

def _safe_int(x, d=0):
    try: return int(str(x).strip() or d)
    except Exception: return d

def _safe_float(x, d=0.0):
    try: return float(str(x).strip() or d)
    except Exception: return d

def _to_bool(x):
    s = str(x or '').strip().lower()
    return s in ('1', 'true', 't', 'yes', 'si', 'sí')

# ---- Impresos (desde LOG de impresión) ----
def _sum_impresos(desde_iso, hasta_iso):
    total = 0
    for n in _iter_impresiones():  # definido en tu app (impresión de boletos)
        if (n.get('tipo') or '').lower() != 'boletos':
            continue
        f = (n.findtext('fecha_sorteo') or '').strip()
        if f and (desde_iso <= f <= hasta_iso):
            try:
                total += int(n.findtext('total_boletos') or '0')
            except Exception:
                pass
    return total

# ---- Lectura flexible de CAJA (cobros) ----
def _caja_iter_cobros_dia(root_dia: ET.Element):
    """
    Itera cobros pagados del nodo <dia>.
    Soporta:
      A) <cobros><cobro vendidos=".." devueltos=".." efectivo=".." transferencia=".." pagado="1" .../></cobros>
      B) <vendedor><vendidos>..</vendidos><devueltos>..</devueltos>...</vendedor>
    """
    # A) Nuevo
    cobros = root_dia.find('cobros')
    if cobros is not None:
        for c in cobros.findall('cobro'):
            yield {
                "seudonimo": c.attrib.get('seudonimo', ''),
                "vendidos": _safe_int(c.attrib.get('vendidos', 0)),
                "devueltos": _safe_int(c.attrib.get('devueltos', 0)),
                "efectivo": _safe_float(c.attrib.get('efectivo', 0)),
                "transferencia": _safe_float(c.attrib.get('transferencia', 0)),
                "pagado": _to_bool(c.attrib.get('pagado', '0')),
            }
        return
    # B) Antiguo
    for v in root_dia.findall('vendedor'):
        yield {
            "seudonimo": v.attrib.get('seudonimo', ''),
            "vendidos": _safe_int(v.findtext('vendidos', 0)),
            "devueltos": _safe_int(v.findtext('devueltos', 0)),
            "efectivo": _safe_float(v.findtext('efectivo', 0)),
            "transferencia": _safe_float(v.findtext('transferencia', 0)),
            "pagado": _to_bool(v.findtext('pagado', 'false') or v.attrib.get('pagado')),
        }

# ---- Caja (vendidos/devueltos/recaudo/comisiones, efectivo/transferencia) ----
def _sum_caja(desde_iso, hasta_iso):
    vendidos = devueltos = 0
    total_recaudado = gan_vendedores = a_caja = 0.0
    tot_efectivo = tot_transfer = 0.0

    # Abrimos una sola vez el XML de caja
    _, root = _leer_xml(CAJA_XML)

    for f in _daterange(desde_iso, hasta_iso):
        dia = root.find(f"./dia[@fecha='{f}']")
        if dia is None:
            continue

        cfg = get_configuracion_dia(f)
        valor     = _safe_float(cfg.get("valor_boleto"), 0.0)
        pct_base  = _safe_float(cfg.get("comision_vendedor"), 0.0)
        pct_extra = _safe_float(cfg.get("comision_extra_meta"), 0.0)
        meta      = _safe_int(cfg.get("meta_boletos"), 0)

        for r in _caja_iter_cobros_dia(dia):
            if not r.get('pagado'):
                continue

            vend = _safe_int(r.get('vendidos', 0))
            dev  = _safe_int(r.get('devueltos', 0))

            vendidos  += vend
            devueltos += dev

            total_venta = vend * valor
            pct = pct_base + (pct_extra if vend >= meta else 0.0)

            gan_v = total_venta * pct / 100.0
            caja  = total_venta - gan_v

            total_recaudado += total_venta
            gan_vendedores  += gan_v
            a_caja          += caja

            tot_transfer += _safe_float(r.get('transferencia', 0))
            tot_efectivo += _safe_float(r.get('efectivo', 0))

    return {
        "vendidos": vendidos,
        "devueltos": devueltos,
        "total_recaudado": round(total_recaudado, 2),
        "gan_vendedores": round(gan_vendedores, 2),
        "a_pagar_caja": round(a_caja, 2),
        "efectivo": round(tot_efectivo, 2),
        "transferencia": round(tot_transfer, 2)
    }

# ---- Asignaciones: planillas / entregados ----
def _sum_asignaciones(desde_iso, hasta_iso):
    path_asig = globals().get("ASIGNACIONES_XML", _persist("static", "db", "asignaciones.xml"))
    boletos_por_planilla = int(globals().get("BOLETOS_POR_PLANILLA", 20))
    if not os.path.exists(path_asig):
        return 0, 0
    try:
        root = ET.parse(path_asig).getroot()
    except ET.ParseError:
        return 0, 0

    planillas = 0
    for d in root.findall("dia"):
        f = (d.attrib.get("fecha") or "").strip()
        if not f or f < desde_iso or f > hasta_iso:
            continue
        for _ in d.findall("vendedor"):
            planillas += len(_.findall("planilla"))
    entregados = planillas * boletos_por_planilla
    return planillas, entregados

# ---- Premios (pagados / por caducar / caducados) ----
def _sum_premios(desde_iso, hasta_iso):
    pagos_map = _pp_leer_pagos_map()  # ya definido en tu módulo de premios
    hoy = date.today()

    total_pagado = 0.0
    por_caducar = 0
    caducados   = 0

    for f in _daterange(desde_iso, hasta_iso):
        f_sorteo = datetime.fromisoformat(f).date()
        caduca = f_sorteo + timedelta(days=30)
        for g in (_pp_iter_ganadores_de_fecha(f) or []):
            k = _pp_premio_key(f, g["figura"], g["boleto"])
            pp = pagos_map.get(k)
            premio_val = _safe_float(g.get("premio", 0), 0)
            if pp:
                total_pagado += _safe_float(pp.get("premio", premio_val), premio_val)
            else:
                if hoy > caduca:
                    caducados += 1
                elif 0 <= (caduca - hoy).days <= 5:
                    por_caducar += 1

    return {
        "premios_pagados_total": round(total_pagado, 2),
        "premios_por_caducar": por_caducar,
        "premios_caducados": caducados
    }

def _premios_pagados_detalle(desde_iso, hasta_iso):
    pagos = _pp_leer_pagos_map()
    items = []
    for p in pagos.values():
        f = (p.get("fecha_sorteo") or "").strip()
        if not f or f < desde_iso or f > hasta_iso:
            continue
        try:
            items.append({
                "fecha_sorteo": f,
                "figura": p.get("figura", ""),
                "boleto": p.get("boleto", ""),
                "ganador": p.get("ganador_nombre", ""),
                "premio": _safe_float(p.get("premio", 0), 0),
                "fecha_pago": p.get("fecha_pago", ""),
                "recibo_id": p.get("recibo_id", ""),
                "pagado_por": p.get("pagado_por", "")
            })
        except Exception:
            pass
    items.sort(key=lambda x: (x["fecha_sorteo"], x["figura"], x["boleto"]))
    return items

# ---- Ruta HTML protegida ----
@app.route("/contabilidad")
def contabilidad():
    if 'usuario' not in session:
        return redirect(_login_url())
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

# ---- Gastos con foto (pantalla simple, sin depender del template contabilidad.html) ----
@app.get("/contabilidad/gastos-fotos")
def contabilidad_gastos_fotos():
    if 'usuario' not in session:
        return redirect(_login_url())
    rol = session.get('rol', '')
    if rol not in ('Super Administrador', 'Administrador'):
        flash('Acceso restringido a Contabilidad', 'error')
        return redirect(url_for('dashboard'))

    # Página mínima para registrar gastos con foto/PDF (el backend comprime imágenes automáticamente).
    return """<!doctype html>
<html lang='es'>
<head>
  <meta charset='utf-8'/>
  <meta name='viewport' content='width=device-width, initial-scale=1'/>
  <title>Gastos con Foto</title>
  <style>
    body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Ubuntu,'Helvetica Neue',Arial; background:#0b1220; color:#e6e8ef; margin:0;}
    .wrap{max-width:980px;margin:24px auto;padding:0 16px;}
    .card{background:#111a2e;border:1px solid rgba(255,255,255,.08);border-radius:16px;padding:16px;box-shadow:0 12px 30px rgba(0,0,0,.35);}
    h1{font-size:20px;margin:0 0 12px;}
    .grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;}
    label{font-size:12px;opacity:.9;display:block;margin:0 0 6px;}
    input,select,textarea{width:100%;padding:10px 12px;border-radius:12px;border:1px solid rgba(255,255,255,.12);background:#0b1220;color:#e6e8ef;outline:none;}
    textarea{min-height:80px;resize:vertical;}
    .row{display:flex;gap:10px;align-items:center;flex-wrap:wrap;}
    .btn{background:#2b6cff;color:white;border:0;border-radius:12px;padding:10px 14px;font-weight:700;cursor:pointer}
    .btn:disabled{opacity:.6;cursor:not-allowed}
    .note{font-size:12px;opacity:.8;margin-top:8px;line-height:1.35}
    table{width:100%;border-collapse:collapse;margin-top:14px;}
    th,td{text-align:left;padding:10px 8px;border-bottom:1px solid rgba(255,255,255,.08);font-size:13px;vertical-align:top;}
    th{opacity:.85}
    a{color:#9bd0ff}
    .pill{display:inline-block;padding:4px 10px;border-radius:999px;background:rgba(43,108,255,.18);border:1px solid rgba(43,108,255,.35);font-size:12px}
    @media (max-width:760px){.grid{grid-template-columns:1fr;}}
  </style>
</head>
<body>
  <div class='wrap'>
    <div class='card'>
      <div class='row' style='justify-content:space-between'>
        <h1>Registrar gasto con foto (comprimida)</h1>
        <a href='/contabilidad' class='pill'>Volver a Contabilidad</a>
      </div>

      <form id='f' class='grid' enctype='multipart/form-data'>
        <div>
          <label>Categoria</label>
          <select name='categoria' required>
            <option value='Pago de Personal'>Pago de Personal</option>
            <option value='Arriendo'>Arriendo</option>
            <option value='Internet'>Internet</option>
            <option value='Café'>Café</option>
            <option value='Servicios Básicos'>Servicios Básicos</option>
            <option value='Otros'>Otros</option>
          </select>
        </div>

        <div>
          <label>Medio</label>
          <select name='medio' required>
            <option value='caja'>Caja (Efectivo)</option>
            <option value='banco'>Banco (Transferencia)</option>
          </select>
        </div>

        <div>
          <label>Monto ($)</label>
          <input name='monto' type='number' step='0.01' min='0' required placeholder='0.00'/>
        </div>

        <div>
          <label>Fecha</label>
          <input name='fecha' id='fecha' type='date' required/>
        </div>

        <div style='grid-column:1/-1'>
          <label>Descripción</label>
          <textarea name='descripcion' placeholder='Ej: Pago internet febrero, arriendo local, etc.'></textarea>
        </div>

        <div style='grid-column:1/-1'>
          <label>Foto/PDF del comprobante (se comprimirá automáticamente si es imagen)</label>
          <input name='comprobante' type='file' accept='image/*,application/pdf' required/>
          <div class='note'>Tip: puedes subir una foto tomada con el celular. El sistema la reduce (máx. 1600px) y la guarda ligera (~650KB aprox.).</div>
        </div>

        <div class='row' style='grid-column:1/-1;justify-content:flex-end'>
          <button class='btn' id='btn'>Guardar gasto</button>
        </div>
      </form>

      <div id='msg' class='note'></div>

      <h1 style='margin-top:18px'>Últimos gastos (30 días)</h1>
      <div style='overflow:auto'>
        <table>
          <thead>
            <tr>
              <th>Fecha</th>
              <th>Categoría</th>
              <th>Medio</th>
              <th>Monto</th>
              <th>Descripción</th>
              <th>Comprobante</th>
            </tr>
          </thead>
          <tbody id='tb'></tbody>
        </table>
      </div>
    </div>
  </div>

<script>
  const $ = (s) => document.querySelector(s);
  const tb = $('#tb');
  const msg = $('#msg');
  const btn = $('#btn');

  // Fecha por defecto: hoy (la API permite solo hoy)
  const today = new Date();
  const iso = today.toISOString().slice(0,10);
  $('#fecha').value = iso;

  function money(n){ try{return Number(n).toFixed(2);}catch(e){return n;} }

  async function cargar(){
    const desde = new Date(Date.now() - 30*24*3600*1000).toISOString().slice(0,10);
    const hasta = iso;
    const r = await fetch(`/api/gastos?desde=${desde}&hasta=${hasta}`, {credentials:'same-origin'});
    const j = await r.json();
    tb.innerHTML = '';
    if(!j.ok){ tb.innerHTML = `<tr><td colspan='6'>No se pudo cargar: ${j.error||r.status}</td></tr>`; return; }
    const items = j.items || [];
    if(items.length===0){ tb.innerHTML = `<tr><td colspan='6'>Sin gastos en este rango</td></tr>`; return; }
    for(const g of items){
      const link = g.comprobante ? `<a target='_blank' href='/static/${g.comprobante}'>Ver</a>` : '';
      tb.innerHTML += `<tr>
        <td>${g.fecha||''}</td>
        <td>${g.categoria||''}</td>
        <td>${g.medio||''}</td>
        <td>$${money(g.monto||0)}</td>
        <td>${(g.descripcion||'').replace(/</g,'&lt;')}</td>
        <td>${link}</td>
      </tr>`;
    }
  }

  $('#f').addEventListener('submit', async (ev) => {
    ev.preventDefault();
    msg.textContent = '';
    btn.disabled = true;
    try{
      const fd = new FormData(ev.target);
      // Para pasar la validación del backend
      const monto = fd.get('monto') || '0';
      fd.set('monto_confirm', monto);

      const r = await fetch('/api/gastos', {method:'POST', body: fd, credentials:'same-origin'});
      const j = await r.json().catch(()=>({}));
      if(!r.ok || !j.ok){
        msg.textContent = 'No se pudo guardar: ' + (j.error || r.status);
      }else{
        msg.textContent = '✅ Gasto guardado correctamente.';
        ev.target.reset();
        $('#fecha').value = iso;
        await cargar();
      }
    }catch(e){
      msg.textContent = 'Error: ' + e;
    }finally{
      btn.disabled = false;
    }
  });

  cargar();
</script>
</body>
</html>"""



# ========================= BANCO (Empresa) =========================
BANCOS_XML = globals().get("CONTAB_BANCOS_XML", _persist('static', 'CONTABILIDAD', 'bancos.xml'))
os.makedirs(os.path.dirname(BANCOS_XML), exist_ok=True)
if not os.path.exists(BANCOS_XML):
    ET.ElementTree(ET.Element('bancos')).write(BANCOS_XML, encoding='utf-8', xml_declaration=True)
_mirror_persist_static_to_public(BANCOS_XML)

def _bank_xml():
    tree = ET.parse(BANCOS_XML)
    return tree, tree.getroot()

def _bank_write(tree):
    try:
        ET.indent(tree, space="  ", level=0)
    except Exception:
        pass
    tree.write(BANCOS_XML, encoding='utf-8', xml_declaration=True)
    _mirror_persist_static_to_public(BANCOS_XML)

def _bank_row(e: ET.Element):
    return {
        "id": e.get("id"),
        "fecha": e.findtext("fecha", ""),
        "hora": e.findtext("hora", ""),
        "cuenta": e.findtext("cuenta", "Empresa"),
        "tipo": (e.findtext("tipo", "ingreso") or "").lower(),  # ingreso|egreso|transferencia
        "monto": float(e.findtext("monto", "0") or 0),
        "referencia": e.findtext("referencia", ""),
        "creado_por": e.findtext("creado_por", ""),
        "creado_rol": e.findtext("creado_rol", ""),
        "creado_ip": e.findtext("creado_ip", ""),
        "creado_en": e.findtext("creado_en", ""),
        "comprobante": e.findtext("comprobante", ""),
        "monto_comprobante": float(e.findtext("monto_comprobante", "0") or 0) if e.find("monto_comprobante") is not None else None,
        "locked": (e.findtext("locked", "false") == "true"),
    }

def _bank_get(mid: str):
    tree, root = _bank_xml()
    for e in root.findall("mov"):
        if e.get("id") == mid:
            return tree, root, e
    return tree, root, None

def _bank_add(fecha:str, cuenta:str, tipo:str, monto:float, referencia:str, creado_por:str,
              comprobante:str=None, locked:bool=False, forced_id:str=None, monto_comprobante:float=None,
              ip:str=None, rol:str=None, creado_en:str=None, hora:str=None):
    tree, root = _bank_xml()
    now = datetime.now()
    mid = forced_id or str(int(now.timestamp()*1000))
    m = ET.SubElement(root, "mov", {"id": mid})

    ET.SubElement(m, "fecha").text = (fecha or date.today().isoformat())
    ET.SubElement(m, "hora").text  = (hora or now.strftime("%H:%M:%S"))
    ET.SubElement(m, "cuenta").text = (cuenta or "Empresa")
    ET.SubElement(m, "tipo").text = (tipo or "ingreso")  # ingreso | egreso | transferencia
    ET.SubElement(m, "monto").text = str(float(monto or 0))
    ET.SubElement(m, "referencia").text = (referencia or "")
    ET.SubElement(m, "creado_por").text = (creado_por or "sistema")
    ET.SubElement(m, "creado_rol").text = (rol or session.get("rol", "") or "")
    ET.SubElement(m, "creado_ip").text  = (ip or (request.remote_addr if request else "") or "")
    ET.SubElement(m, "creado_en").text  = (creado_en or now.isoformat(timespec="seconds"))

    if comprobante:
        ET.SubElement(m, "comprobante").text = comprobante
    ET.SubElement(m, "locked").text = "true" if locked else "false"
    if monto_comprobante is not None:
        ET.SubElement(m, "monto_comprobante").text = str(float(monto_comprobante))

    _bank_write(tree)
    return mid

def _bank_list(desde:str, hasta:str, cuenta:str=None):
    _, root = _bank_xml()
    items = []
    for e in root.findall('mov'):
        f = e.findtext('fecha') or ''
        if not f:
            continue
        if desde and f < desde:  # fuera de rango inferior
            continue
        if hasta and f > hasta:  # fuera de rango superior
            continue
        if cuenta and (e.findtext('cuenta') or 'Empresa') != cuenta:
            continue
        items.append(_bank_row(e))
    items.sort(key=lambda x: (x["fecha"], x["id"]))
    return items

def _bank_delete(mid:str):
    tree, root, e = _bank_get(mid)
    if e is None:
        return False
    if (e.findtext("locked", "false") == "true"):
        return False
    root.remove(e); _bank_write(tree); return True

def _bank_delete_force(mid:str):
    """Borra un movimiento aun si está locked. SOLO usar para Super Admin."""
    tree, root, e = _bank_get(mid)
    if e is None:
        return False
    root.remove(e)
    _bank_write(tree)
    return True

def _bank_saldo(cuenta:str="Empresa", hasta:str=None):
    _, root = _bank_xml()
    total = 0.0
    for e in root.findall('mov'):
        if (e.findtext('cuenta') or 'Empresa') != cuenta:
            continue
        f = e.findtext('fecha') or ''
        if hasta and f > hasta:
            continue
        tipo = (e.findtext('tipo') or 'ingreso').lower()
        monto = float(e.findtext('monto') or 0)
        if tipo == 'ingreso':
            total += monto
        else:
            total -= monto
    return round(total, 2)

def _require_admin():
    return session.get('rol', '') in ('Super Administrador', 'Administrador')

# -------------------- Rutas Banco (REST) --------------------
@app.get("/api/banco/saldo")
def api_banco_saldo():
    cuenta = request.args.get("cuenta") or "Empresa"
    hasta = request.args.get("hasta") or date.today().isoformat()
    return jsonify({"ok": True, "cuenta": cuenta, "hasta": hasta, "saldo": _bank_saldo(cuenta, hasta)})

@app.get("/api/banco/movimientos")
def api_banco_movimientos():
    cuenta = request.args.get("cuenta") or "Empresa"
    desde = request.args.get("desde") or (date.today() - timedelta(days=30)).isoformat()
    hasta = request.args.get("hasta") or date.today().isoformat()
    return jsonify({"ok": True, "items": _bank_list(desde, hasta, cuenta)})

@app.post("/api/banco/deposito")
def api_banco_deposito():
    if not _require_admin():
        return jsonify({"ok": False, "error": "no-autorizado"}), 403

    if request.content_type and "multipart/form-data" in request.content_type:
        form = request.form
        file = request.files.get("comprobante") or request.files.get("foto")
        if not file or not file.filename:
            return jsonify({"ok": False, "error": "comprobante-requerido"}), 400
        if not _ext_ok(file.filename):
            return jsonify({"ok": False, "error": "ext-archivo-no-valida"}), 400

        monto = float(form.get("monto") or 0)
        monto_comp = float(form.get("monto_confirm") or form.get("monto_comprobante") or 0)
        if round(monto, 2) != round(monto_comp, 2):
            return jsonify({"ok": False, "error": "monto-comprobante-difiere"}), 400

        mid = str(int(datetime.now().timestamp()*1000))
        comp_rel = _save_upload(file, BANK_FILES, f"dep_{mid}")
        _bank_add(
            fecha = form.get("fecha") or date.today().isoformat(),
            cuenta = form.get("cuenta") or "Empresa",
            tipo = "ingreso",
            monto = monto,
            referencia = form.get("referencia") or "Depósito",
            creado_por = session.get('usuario', 'sistema'),
            comprobante = comp_rel,
            locked = True,
            forced_id = mid,
            monto_comprobante = monto_comp,
            ip = request.remote_addr,
            rol = session.get('rol',''),
            creado_en = datetime.now().isoformat(timespec='seconds'),
            hora = datetime.now().strftime('%H:%M:%S')
        )
        return jsonify({"ok": True, "id": mid, "saldo": _bank_saldo(form.get('cuenta') or "Empresa")})
    else:
        return jsonify({"ok": False, "error": "usar-multipart-con-comprobante"}), 400

@app.post("/api/banco/retiro")
def api_banco_retiro():
    if not _require_admin():
        return jsonify({"ok": False, "error": "no-autorizado"}), 403
    data = request.get_json(force=True) or {}
    mid = _bank_add(
        fecha = data.get("fecha") or date.today().isoformat(),
        cuenta = data.get("cuenta") or "Empresa",
        tipo = "egreso",
        monto = float(data.get("monto") or 0),
        referencia = data.get("referencia") or "Retiro",
        creado_por = session.get('usuario', 'sistema'),
        locked = False,
        ip = request.remote_addr,
        rol = session.get('rol',''),
        creado_en = datetime.now().isoformat(timespec='seconds'),
        hora = datetime.now().strftime('%H:%M:%S')
    )
    return jsonify({"ok": True, "id": mid, "saldo": _bank_saldo(data.get("cuenta") or "Empresa")})

@app.delete("/api/banco/movimientos/<mid>")
def api_banco_borrar(mid):
    if not _require_admin() and not _is_superadmin():
        return jsonify({"ok": False, "error": "no-autorizado"}), 403

    force = (request.args.get("force") == "1")
    if force:
        # Solo SUPER ADMIN puede forzar borrado (incluye locked)
        if not _is_superadmin():
            return jsonify({"ok": False, "error": "solo-superadmin"}), 403
        ok = _bank_delete_force(mid)
    else:
        ok = _bank_delete(mid)

    if not ok:
        return jsonify({"ok": False, "error": "mov-bloqueado-o-inexistente"}), 400

    try:
        _audit_event("banco", "delete", mid, {"force": force})
    except Exception:
        pass
    return jsonify({"ok": True})

# -------------------- API: GASTOS --------------------
@app.get("/api/gastos")
def api_gastos_list():
    if 'usuario' not in session:
        return jsonify({"ok": False, "error": "no-auth"}), 401
    desde = (request.args.get("desde") or (date.today() - timedelta(days=30)).isoformat()).strip()
    hasta = (request.args.get("hasta") or date.today().isoformat()).strip()
    return jsonify({"ok": True, "items": _gastos_list(desde, hasta)})

@app.post("/api/gastos")
def api_gastos_add():
    if 'usuario' not in session:
        return jsonify({"ok": False, "error": "no-auth"}), 401

    if request.content_type and "multipart/form-data" in request.content_type:
        form = request.form
        # Regla: solo se pueden ingresar gastos del día actual
        hoy = date.today().isoformat()
        fecha_form = (form.get("fecha") or hoy).strip()
        if fecha_form != hoy:
            return jsonify({"ok": False, "error": "solo-hoy"}), 400

        file = request.files.get("comprobante") or request.files.get("foto")
        if not file or not file.filename:
            return jsonify({"ok": False, "error": "comprobante-requerido"}), 400
        if not _ext_ok(file.filename):
            return jsonify({"ok": False, "error": "ext-archivo-no-valida"}), 400

        monto = float(form.get("monto") or 0)
        monto_comp = float(form.get("monto_confirm") or form.get("monto_comprobante") or 0)
        if round(monto, 2) != round(monto_comp, 2):
            return jsonify({"ok": False, "error": "monto-comprobante-difiere"}), 400

        gid = str(int(datetime.now().timestamp()*1000))
        comp_rel = _save_upload(file, GASTO_FILES, f"gasto_{gid}")
        data = dict(form)
        data["fecha"] = fecha_form
        _gasto_add(data, session.get('usuario'), comp_rel, gid_forced=gid, monto_comprobante=monto_comp, ip=request.remote_addr, rol=session.get('rol',''), creado_en=datetime.now().isoformat(timespec='seconds'))
        return jsonify({"ok": True, "id": gid})
    else:
        return jsonify({"ok": False, "error": "usar-multipart-con-comprobante"}), 400

@app.delete("/api/gastos/<gid>")
def api_gastos_delete(gid):
    if 'usuario' not in session:
        return jsonify({"ok": False, "error": "no-auth"}), 401
    # Solo SUPER ADMIN puede borrar gastos (control estricto)
    if not _is_superadmin():
        return jsonify({"ok": False, "error": "solo-superadmin"}), 403

    ok = _gasto_delete(gid)
    try:
        _audit_event("gastos", "delete", gid, {"ok": ok})
    except Exception:
        pass
    return jsonify({"ok": ok})

# -------------------- API: RESUMEN CONTABLE --------------------
@app.get("/api/contabilidad/resumen")
def api_contabilidad_resumen():
    desde = (request.args.get("desde") or (date.today() - timedelta(days=30)).isoformat()).strip()
    hasta = (request.args.get("hasta") or date.today().isoformat()).strip()
    try:
        if datetime.fromisoformat(desde) > datetime.fromisoformat(hasta):
            desde, hasta = hasta, desde
    except Exception:
        pass

    impresos = _sum_impresos(desde, hasta)
    caja     = _sum_caja(desde, hasta)
    premios  = _sum_premios(desde, hasta)

    gastos_items = _gastos_list(desde, hasta)
    gastos_total  = round(sum(g["monto"] for g in gastos_items if (g["categoria"] or "").lower() != "sueldo"), 2)
    sueldos_total = round(sum(g["monto"] for g in gastos_items if (g["categoria"] or "").lower() == "sueldo"), 2)
    gastos_caja   = round(sum(g["monto"] for g in gastos_items if g["medio"] == "caja"), 2)
    gastos_banco  = round(sum(g["monto"] for g in gastos_items if g["medio"] == "banco"), 2)

    banco_items = _bank_list(desde, hasta, "Empresa")
    planillas_asignadas, boletos_entregados = _sum_asignaciones(desde, hasta)

    gan_empresa   = round(caja["total_recaudado"] - caja["gan_vendedores"], 2)
    utilidad_neta = round(gan_empresa - premios["premios_pagados_total"] - gastos_total - sueldos_total, 2)

    saldo_caja  = round(caja["efectivo"]      - gastos_caja, 2)
    saldo_banco = round(caja["transferencia"] - gastos_banco, 2)

    premios_detalle = _premios_pagados_detalle(desde, hasta)

    return jsonify({
        "ok": True,
        "rango": {"desde": desde, "hasta": hasta},
        "planillas_asignadas": planillas_asignadas,
        "boletos_entregados": boletos_entregados,
        "boletos_impresos": impresos,
        "boletos_vendidos": caja["vendidos"],
        "boletos_devueltos": caja["devueltos"],
        "ingresos_brutos": caja["total_recaudado"],
        "ganancia_vendedores": caja["gan_vendedores"],
        "ganancia_empresa": gan_empresa,
        "premios_pagados_total": premios["premios_pagados_total"],
        "premios_por_caducar": premios["premios_por_caducar"],
        "premios_caducados": premios["premios_caducados"],
        "gastos_total": gastos_total,
        "sueldos_total": sueldos_total,
        "utilidad_neta": utilidad_neta,
        "efectivo_cobrado": caja["efectivo"],
        "transferencias_cobradas": caja["transferencia"],
        "saldo_caja": saldo_caja,
        "saldo_banco": saldo_banco,
        "gastos": gastos_items,
        "banco": banco_items,
        "premios_detalle": premios_detalle
    })


# -------------------- API: MOVIMIENTOS UNIFICADOS + SUPER ADMIN --------------------

def _caja_list_cobros_rango(desde_iso: str, hasta_iso: str):
    _, root = _leer_xml(CAJA_XML)
    items = []
    for dia in root.findall("dia"):
        fecha = (dia.get("fecha") or "").strip()
        if not fecha:
            continue
        if desde_iso and fecha < desde_iso:
            continue
        if hasta_iso and fecha > hasta_iso:
            continue
        cobros = dia.find("cobros")
        if cobros is None:
            continue
        for c in cobros.findall("cobro"):
            seud = (c.get("seudonimo") or "").strip()
            if not seud:
                continue
            transferencia = float(c.get("transferencia", "0") or 0)
            efectivo = float(c.get("efectivo", "0") or 0)
            total_pagar = float(c.get("total_pagar", "0") or 0)
            pagado = (c.get("pagado", "0") == "1")
            fh = c.get("fecha_hora", "") or ""
            hora = fh.split(" ")[1] if (" " in fh) else (fh.split("T")[1] if "T" in fh else "")
            medio = "mixto" if (transferencia > 0 and efectivo > 0) else ("transferencia" if transferencia > 0 else "efectivo")
            cid = c.get("id") or f"{fecha}__{seud}"
            items.append({
                "id": cid,
                "fecha": fecha,
                "hora": hora,
                "tipo": "cobro",
                "naturaleza": "ingreso",
                "monto": round(total_pagar, 2),
                "medio": medio,
                "banco": "",  # si quieres, aquí puedes guardar banco de transferencia en el futuro
                "referencia": f"Cobro vendedor {seud}",
                "seudonimo": seud,
                "pagado": pagado,
                "detalle": {
                    "vendidos": int(c.get("vendidos", "0") or 0),
                    "devueltos": int(c.get("devueltos", "0") or 0),
                    "transferencia": round(transferencia, 2),
                    "efectivo": round(efectivo, 2),
                },
                "creado_por": c.get("creado_por", "") or "",
                "creado_rol": c.get("creado_rol", "") or "",
                "creado_ip": c.get("creado_ip", "") or "",
                "creado_en": c.get("creado_en", "") or "",
                "actualizado_por": c.get("actualizado_por", "") or "",
                "actualizado_ip": c.get("actualizado_ip", "") or "",
                "actualizado_en": c.get("actualizado_en", "") or "",
                "comprobante": "",  # si deseas adjuntar comprobante al cobro, lo agregamos luego
            })
    items.sort(key=lambda x: (x["fecha"], x.get("hora",""), x["id"]))
    return items

@app.get("/api/session")
def api_session_info():
    return jsonify({
        "ok": True,
        "usuario": session.get("usuario", ""),
        "rol": session.get("rol", ""),
        "is_superadmin": _is_superadmin()
    })

@app.get("/api/contabilidad/movimientos")
def api_contabilidad_movimientos():
    desde = request.args.get("desde") or (date.today() - timedelta(days=30)).isoformat()
    hasta = request.args.get("hasta") or date.today().isoformat()
    # Cobros (caja)
    cobros = _caja_list_cobros_rango(desde, hasta)
    # Gastos
    gastos = _gastos_list(desde, hasta)
    mov_gastos = []
    for g in gastos:
        mov_gastos.append({
            "id": g["id"],
            "fecha": g["fecha"],
            "hora": g.get("hora",""),
            "tipo": "gasto",
            "naturaleza": "egreso",
            "monto": round(float(g.get("monto") or 0), 2),
            "medio": g.get("medio",""),
            "banco": g.get("banco",""),
            "referencia": g.get("categoria","Gasto"),
            "detalle": {"descripcion": g.get("descripcion","")},
            "creado_por": g.get("creado_por",""),
            "creado_rol": g.get("creado_rol",""),
            "creado_ip": g.get("creado_ip",""),
            "creado_en": g.get("creado_en",""),
            "comprobante": g.get("comprobante",""),
        })
    # Banco (movimientos)
    banco = _bank_list(desde, hasta, None)
    mov_banco = []
    for b in banco:
        mov_banco.append({
            "id": b["id"],
            "fecha": b["fecha"],
            "hora": b.get("hora",""),
            "tipo": "banco",
            "naturaleza": "ingreso" if b.get("tipo") == "ingreso" else "egreso",
            "monto": round(float(b.get("monto") or 0), 2),
            "medio": "banco",
            "banco": b.get("cuenta","Empresa"),
            "referencia": b.get("referencia",""),
            "detalle": {"tipo_banco": b.get("tipo","")},
            "creado_por": b.get("creado_por",""),
            "creado_rol": b.get("creado_rol",""),
            "creado_ip": b.get("creado_ip",""),
            "creado_en": b.get("creado_en",""),
            "comprobante": b.get("comprobante",""),
            "locked": bool(b.get("locked")),
        })

    # Unificado
    items = cobros + mov_gastos + mov_banco
    items.sort(key=lambda x: (x["fecha"], x.get("hora",""), x["tipo"], x["id"]))
    return jsonify({"ok": True, "desde": desde, "hasta": hasta, "items": items})

@app.get("/api/contabilidad/export.csv")
def api_contabilidad_export_csv():
    desde = request.args.get("desde") or (date.today() - timedelta(days=30)).isoformat()
    hasta = request.args.get("hasta") or date.today().isoformat()
    data = api_contabilidad_movimientos().get_json()
    items = data.get("items", []) if isinstance(data, dict) else []
    import csv
    from io import StringIO
    buff = StringIO()
    w = csv.writer(buff)
    w.writerow(["fecha","hora","tipo","naturaleza","monto","medio","banco","referencia","usuario","rol","ip","timestamp","comprobante","id"])
    for it in items:
        w.writerow([
            it.get("fecha",""),
            it.get("hora",""),
            it.get("tipo",""),
            it.get("naturaleza",""),
            it.get("monto",""),
            it.get("medio",""),
            it.get("banco",""),
            it.get("referencia",""),
            it.get("creado_por",""),
            it.get("creado_rol",""),
            it.get("creado_ip",""),
            it.get("creado_en",""),
            it.get("comprobante",""),
            it.get("id",""),
        ])
    out = buff.getvalue()
    return Response(out, mimetype="text/csv", headers={"Content-Disposition": f"attachment; filename=contabilidad_{desde}_a_{hasta}.csv"})

# ---- SUPER ADMIN: borrar/anular cobros y reset total ----

def _caja_delete_cobro(fecha_str: str, seudonimo: str):
    t, r = _leer_xml(CAJA_XML)
    dia = _get_dia(r, fecha_str)
    cobros = dia.find("cobros")
    if cobros is None:
        return False
    node = cobros.find(f"./cobro[@seudonimo='{seudonimo}']")
    if node is None:
        return False
    cobros.remove(node)
    _guardar_xml(t, CAJA_XML)
    return True

@app.delete("/api/superadmin/cobro")
def api_superadmin_delete_cobro():
    if 'usuario' not in session:
        return jsonify({"ok": False, "error": "no-auth"}), 401
    if not _require_super():
        return jsonify({"ok": False, "error": "solo-superadmin"}), 403
    fecha = (request.args.get("fecha") or "").strip()
    seud = (request.args.get("seudonimo") or "").strip()
    if not fecha or not seud:
        return jsonify({"ok": False, "error": "faltan-parametros"}), 400
    ok = _caja_delete_cobro(fecha, seud)
    _audit_event("caja", "delete_cobro", f"{fecha}__{seud}", {"ok": ok})
    return jsonify({"ok": ok})

@app.post("/api/superadmin/cobro/anular")
def api_superadmin_anular_cobro():
    if 'usuario' not in session:
        return jsonify({"ok": False, "error": "no-auth"}), 401
    if not _require_super():
        return jsonify({"ok": False, "error": "solo-superadmin"}), 403
    data = request.get_json(silent=True) or {}
    fecha = (data.get("fecha") or "").strip()
    seud = (data.get("seudonimo") or "").strip()
    motivo = (data.get("motivo") or "").strip()
    if not fecha or not seud:
        return jsonify({"ok": False, "error": "faltan-parametros"}), 400
    # Anular: deja registro pero lo marca NO pagado y en cero
    _upsert_cobro(fecha, seud, {
        "devueltos": 0,
        "vendidos": 0,
        "total_pagar": 0,
        "transferencia": 0,
        "efectivo": 0,
        "pagado": False,
        "creado_por": session.get("usuario",""),
        "creado_rol": session.get("rol",""),
        "creado_ip": request.remote_addr or "",
        "creado_en": datetime.now().isoformat(timespec="seconds"),
    })
    _audit_event("caja", "anular_cobro", f"{fecha}__{seud}", {"motivo": motivo})
    return jsonify({"ok": True})

@app.post("/api/superadmin/reset-contabilidad")
def api_superadmin_reset_contabilidad():
    if 'usuario' not in session:
        return jsonify({"ok": False, "error": "no-auth"}), 401
    if not _require_super():
        return jsonify({"ok": False, "error": "solo-superadmin"}), 403

    data = request.get_json(silent=True) or {}
    confirm = (data.get("confirm") or "").strip().upper()
    if confirm != "BORRAR TODO":
        return jsonify({"ok": False, "error": "confirmacion-invalida", "hint": "Envíe confirm='BORRAR TODO'"}), 400

    scopes = data.get("scopes") or ["caja", "gastos", "banco", "asignaciones"]
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = os.path.join(PERSIST_CONTAB_DIR, "backups", f"reset_{ts}")
    os.makedirs(backup_dir, exist_ok=True)

    # Backup antes de borrar
    for p in [CAJA_XML, GASTOS_XML, BANCOS_XML, ASIGNACIONES_XML, AUDIT_XML]:
        _safe_backup_copy(p, backup_dir)

    # Reset según scopes
    if "caja" in scopes:
        _reset_xml(CAJA_XML, "caja")
    if "gastos" in scopes:
        _reset_xml(GASTOS_XML, "gastos")
    if "banco" in scopes:
        _reset_xml(BANCOS_XML, "banco")
    if "asignaciones" in scopes:
        _reset_xml(ASIGNACIONES_XML, "asignaciones")

    _audit_event("sistema", "reset_contabilidad", "", {"scopes": ",".join(scopes), "backup_dir": backup_dir})

    return jsonify({"ok": True, "backup_dir": backup_dir, "scopes": scopes})

@app.get("/api/superadmin/auditoria")
def api_superadmin_auditoria():
    if 'usuario' not in session:
        return jsonify({"ok": False, "error": "no-auth"}), 401
    if not _require_super():
        return jsonify({"ok": False, "error": "solo-superadmin"}), 403
    desde = request.args.get("desde") or (date.today() - timedelta(days=30)).isoformat()
    hasta = request.args.get("hasta") or date.today().isoformat()
    tree, root = _xml_read(AUDIT_XML)
    out = []
    for ev in root.findall("evento"):
        f = ev.findtext("fecha","")
        if f and f < desde: 
            continue
        if f and f > hasta:
            continue
        det = {}
        dnode = ev.find("detalle")
        if dnode is not None:
            for d in dnode.findall("d"):
                det[d.get("k","")] = d.text or ""
        out.append({
            "id": ev.get("id",""),
            "fecha": f,
            "hora": ev.findtext("hora",""),
            "timestamp": ev.findtext("timestamp",""),
            "usuario": ev.findtext("usuario",""),
            "rol": ev.findtext("rol",""),
            "ip": ev.findtext("ip",""),
            "modulo": ev.findtext("modulo",""),
            "accion": ev.findtext("accion",""),
            "ref": ev.findtext("ref",""),
            "detalle": det,
        })
    out.sort(key=lambda x: (x["fecha"], x["hora"], x["id"]))
    return jsonify({"ok": True, "items": out})

@app.route("/contabilidad/balance")
def contabilidad_balance():
    if 'usuario' not in session:
        return redirect(url_for('login', _external=False)) if 'login' in app.view_functions else redirect('/_login_demo')
    # HTML + JS (sin f-strings para evitar errores)
    return Response("""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Balance Contable - GL</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    body{font-family:system-ui,Segoe UI,Roboto,Arial; background:#0b1220; color:#e8eefc; margin:0}
    header{padding:16px 20px; background:linear-gradient(90deg,#0d1b3d,#0b1220); border-bottom:1px solid rgba(255,255,255,.08)}
    h1{margin:0; font-size:18px; letter-spacing:.3px}
    .wrap{padding:18px; display:grid; gap:14px}
    .row{display:grid; grid-template-columns: 1fr; gap:14px}
    @media(min-width:1100px){ .row{grid-template-columns: 360px 1fr} }
    .card{background:rgba(255,255,255,.06); border:1px solid rgba(255,255,255,.10); border-radius:14px; padding:14px}
    .grid4{display:grid; grid-template-columns:repeat(2,1fr); gap:10px}
    @media(min-width:900px){ .grid4{grid-template-columns:repeat(4,1fr)} }
    .k{font-size:12px; opacity:.85}
    .v{font-size:20px; font-weight:800; margin-top:6px}
    input,button,select{background:#0f1a33; color:#e8eefc; border:1px solid rgba(255,255,255,.12); border-radius:10px; padding:10px 12px}
    button{cursor:pointer}
    button.danger{background:#3a0c12; border-color:#7c1b2a}
    table{width:100%; border-collapse:collapse; font-size:13px}
    th,td{padding:10px 8px; border-bottom:1px solid rgba(255,255,255,.08); text-align:left; vertical-align:top}
    th{font-size:12px; opacity:.9}
    a{color:#9ad1ff; text-decoration:none}
    .pill{display:inline-block; padding:3px 8px; border-radius:999px; font-size:12px; border:1px solid rgba(255,255,255,.16); background:rgba(255,255,255,.06)}
    .muted{opacity:.75}
    .right{display:flex; gap:10px; flex-wrap:wrap; align-items:center}
  </style>
</head>
<body>
<header>
  <div style="display:flex;justify-content:space-between;gap:12px;align-items:center;flex-wrap:wrap">
    <h1>Balance contable (Caja + Banco + Gastos)</h1>
    <div class="right">
      <label class="muted">Desde</label><input id="desde" type="date">
      <label class="muted">Hasta</label><input id="hasta" type="date">
      <button id="btnCargar">Cargar</button>
      <a id="btnExport" class="pill" href="#" target="_blank">Exportar CSV</a>
      <a class="pill" href="/contabilidad" target="_blank">Resumen</a>
    </div>
  </div>
</header>

<div class="wrap">
  <div class="grid4">
    <div class="card"><div class="k">Ingresos (Cobros)</div><div class="v" id="kIngresos">$0.00</div></div>
    <div class="card"><div class="k">Gastos</div><div class="v" id="kGastos">$0.00</div></div>
    <div class="card"><div class="k">Banco (Saldo neto rango)</div><div class="v" id="kBanco">$0.00</div></div>
    <div class="card"><div class="k">Balance (Ingresos - Gastos)</div><div class="v" id="kBalance">$0.00</div></div>
  </div>

  <div class="row">
    <div class="card">
      <div style="display:flex;justify-content:space-between;gap:10px;align-items:center;flex-wrap:wrap">
        <div>
          <div class="k">Acciones</div>
          <div class="muted" id="who"></div>
        </div>
        <div class="right" id="superBox" style="display:none">
          <button class="danger" id="btnReset">Reset contabilidad</button>
        </div>
      </div>
      <hr style="border:0;border-top:1px solid rgba(255,255,255,.10);margin:12px 0">
      <div class="k">Auditoría (últimos 30 días)</div>
      <div style="max-height:260px; overflow:auto; margin-top:10px">
        <table id="tblAudit">
          <thead><tr><th>Fecha</th><th>Usuario</th><th>Acción</th><th>Ref</th></tr></thead>
          <tbody></tbody>
        </table>
      </div>
    </div>

    <div class="card">
      <div class="k" style="margin-bottom:8px">Curva (Ingresos vs Gastos)</div>
      <canvas id="ch1" height="120"></canvas>
      <div class="k" style="margin-top:14px;margin-bottom:8px">Detalle de movimientos</div>
      <div style="max-height:420px; overflow:auto">
        <table id="tblMov">
          <thead>
            <tr>
              <th>Fecha</th><th>Tipo</th><th>Monto</th><th>Medio/Banco</th><th>Referencia</th><th>Usuario</th><th>Comprobante</th><th id="thAcc" style="display:none">Acción</th>
            </tr>
          </thead>
          <tbody></tbody>
        </table>
      </div>
    </div>
  </div>
</div>

<script>
const money = n => {
  const x = Number(n||0);
  return x.toLocaleString('es-EC',{style:'currency',currency:'USD'});
};

let chart1 = null;
let isSuper = false;

async function sessionInfo(){
  const r = await fetch('/api/session'); const j = await r.json();
  isSuper = !!j.is_superadmin;
  document.getElementById('who').textContent = `${j.usuario || ''} • ${j.rol || ''}`;
  document.getElementById('superBox').style.display = isSuper ? '' : 'none';
  document.getElementById('thAcc').style.display = isSuper ? '' : 'none';
}

function todayISO(){
  const d = new Date();
  return d.toISOString().slice(0,10);
}
function daysAgoISO(n){
  const d = new Date(); d.setDate(d.getDate()-n);
  return d.toISOString().slice(0,10);
}

async function cargar(){
  const desde = document.getElementById('desde').value;
  const hasta = document.getElementById('hasta').value;

  document.getElementById('btnExport').href = `/api/contabilidad/export.csv?desde=${desde}&hasta=${hasta}`;

  // resumen básico
  const r1 = await fetch(`/api/contabilidad/resumen?desde=${desde}&hasta=${hasta}`);
  const j1 = await r1.json();

  const ingresos = (j1.caja && j1.caja.total_pagado) ? Number(j1.caja.total_pagado) : 0;
  const gastos   = (j1.gastos && j1.gastos.total) ? Number(j1.gastos.total) : 0;
  const bancoN   = (j1.banco && j1.banco.saldo) ? Number(j1.banco.saldo) : 0;

  document.getElementById('kIngresos').textContent = money(ingresos);
  document.getElementById('kGastos').textContent   = money(gastos);
  document.getElementById('kBanco').textContent    = money(bancoN);
  document.getElementById('kBalance').textContent  = money(ingresos - gastos);

  // movimientos
  const r2 = await fetch(`/api/contabilidad/movimientos?desde=${desde}&hasta=${hasta}`);
  const j2 = await r2.json();
  renderMov(j2.items || []);

  // curva simple por día desde resumen (si existe)
  const labels = (j1.curva && j1.curva.labels) ? j1.curva.labels : [];
  const dataIngresos = (j1.curva && j1.curva.ingresos) ? j1.curva.ingresos : [];
  const dataGastos   = (j1.curva && j1.curva.gastos) ? j1.curva.gastos : [];

  if(chart1) chart1.destroy();
  const ctx = document.getElementById('ch1').getContext('2d');
  chart1 = new Chart(ctx, {
    type: 'line',
    data: { labels, datasets: [
      { label: 'Ingresos', data: dataIngresos },
      { label: 'Gastos', data: dataGastos },
    ]},
    options: { responsive:true, plugins:{legend:{labels:{color:'#e8eefc'}}}, scales:{x:{ticks:{color:'#e8eefc'}},y:{ticks:{color:'#e8eefc'}}}}
  });
}

function renderMov(items){
  const tbody = document.querySelector('#tblMov tbody');
  tbody.innerHTML = '';
  for(const it of items){
    const tr = document.createElement('tr');
    const comp = it.comprobante ? `<a href="/static/${it.comprobante}" target="_blank">Ver</a>` : '';
    const monto = (it.naturaleza === 'egreso') ? -Number(it.monto||0) : Number(it.monto||0);
    const tipo = it.tipo === 'banco' ? `Banco (${it.detalle && it.detalle.tipo_banco ? it.detalle.tipo_banco : ''})` : it.tipo;
    const medio = it.tipo === 'banco' ? (it.banco || '') : (it.medio || '');
    const usuario = it.creado_por || '';

    let btn = '';
    if(isSuper){
      if(it.tipo === 'gasto'){
        btn = `<button class="danger" data-t="gasto" data-id="${it.id}">Eliminar</button>`;
      } else if(it.tipo === 'banco'){
        btn = `<button class="danger" data-t="banco" data-id="${it.id}">Eliminar</button>`;
      } else if(it.tipo === 'cobro'){
        btn = `<button class="danger" data-t="cobro" data-id="${it.id}" data-f="${it.fecha}" data-s="${it.seudonimo}">Eliminar</button>`;
      }
    }

    tr.innerHTML = `
      <td>${it.fecha || ''} <span class="muted">${it.hora || ''}</span></td>
      <td><span class="pill">${tipo}</span></td>
      <td>${money(monto)}</td>
      <td>${medio}</td>
      <td>${it.referencia || ''}</td>
      <td>${usuario}</td>
      <td>${comp}</td>
      <td class="acc" style="display:${isSuper?'table-cell':'none'}">${btn}</td>
    `;
    tbody.appendChild(tr);
  }

  // acciones borrar
  if(isSuper){
    tbody.querySelectorAll('button.danger').forEach(b=>{
      b.addEventListener('click', async ()=>{
        const t = b.dataset.t;
        if(!confirm('¿Seguro? Esto quedará registrado en auditoría.')) return;
        if(t === 'gasto'){
          const r = await fetch(`/api/gastos/${b.dataset.id}`, {method:'DELETE'});
          await r.json(); await cargar(); await cargarAuditoria();
        }
        if(t === 'banco'){
          const r = await fetch(`/api/banco/movimientos/${b.dataset.id}?force=1`, {method:'DELETE'});
          await r.json(); await cargar(); await cargarAuditoria();
        }
        if(t === 'cobro'){
          const f = b.dataset.f; const s = b.dataset.s;
          const r = await fetch(`/api/superadmin/cobro?fecha=${f}&seudonimo=${encodeURIComponent(s)}`, {method:'DELETE'});
          await r.json(); await cargar(); await cargarAuditoria();
        }
      })
    })
  }
}

async function cargarAuditoria(){
  if(!isSuper){
    document.querySelector('#tblAudit tbody').innerHTML = '<tr><td colspan="4" class="muted">Solo visible para Super Admin</td></tr>';
    return;
  }
  const desde = daysAgoISO(30);
  const hasta = todayISO();
  const r = await fetch(`/api/superadmin/auditoria?desde=${desde}&hasta=${hasta}`);
  const j = await r.json();
  const tbody = document.querySelector('#tblAudit tbody');
  tbody.innerHTML = '';
  (j.items || []).slice(-200).reverse().forEach(ev=>{
    const tr = document.createElement('tr');
    tr.innerHTML = `<td>${ev.fecha} <span class="muted">${ev.hora||''}</span></td><td>${ev.usuario||''}</td><td>${ev.modulo||''}:${ev.accion||''}</td><td class="muted">${ev.ref||''}</td>`;
    tbody.appendChild(tr);
  });
}

document.getElementById('btnCargar').addEventListener('click', async ()=>{ await cargar(); await cargarAuditoria(); });

document.getElementById('btnReset').addEventListener('click', async ()=>{
  if(!isSuper) return;
  const txt = prompt('Escribe BORRAR TODO para dejar contabilidad en blanco (se hace backup automático).');
  if(!txt) return;
  const r = await fetch('/api/superadmin/reset-contabilidad', {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({confirm: txt, scopes:['caja','gastos','banco','asignaciones']})
  });
  const j = await r.json();
  if(!j.ok){ alert('No se pudo: ' + (j.error||'')); return; }
  alert('Listo. Backup: ' + j.backup_dir);
  await cargar(); await cargarAuditoria();
});

// init
(async ()=>{
  document.getElementById('desde').value = daysAgoISO(30);
  document.getElementById('hasta').value = todayISO();
  await sessionInfo();
  await cargar();
  await cargarAuditoria();
})();
</script>
</body>
</html>""", mimetype="text/html")


# ---- ENDPOINTS para curvas por vendedor (ventas / devueltos / combinado) ----
def _caja_iter_cobros_rango(desde_iso, hasta_iso):
    _, root = _leer_xml(CAJA_XML)
    for f in _daterange(desde_iso, hasta_iso):
        dia = root.find(f"./dia[@fecha='{f}']")
        if dia is None:
            continue
        for r in _caja_iter_cobros_dia(dia):
            if r.get('pagado'):
                yield (f, r.get('seudonimo') or '', _safe_int(r.get('vendidos', 0)), _safe_int(r.get('devueltos', 0)))

@app.get("/api/contabilidad/ventas-vendedores")
def api_ventas_vendedores():
    desde = (request.args.get("desde") or date.today().isoformat()).strip()
    hasta = (request.args.get("hasta") or date.today().isoformat()).strip()
    agg = {}
    for _, seud, vend, _ in _caja_iter_cobros_rango(desde, hasta):
        agg[seud] = agg.get(seud, 0) + vend
    items = [{"vendedor": k or "(sin seudónimo)", "vendidos": v} for k, v in agg.items()]
    return jsonify(ok=True, items=sorted(items, key=lambda x: -x["vendidos"]))

@app.get("/api/contabilidad/devueltos-vendedores")
def api_devueltos_vendedores():
    desde = (request.args.get("desde") or date.today().isoformat()).strip()
    hasta = (request.args.get("hasta") or date.today().isoformat()).strip()
    agg = {}
    for _, seud, _, dev in _caja_iter_cobros_rango(desde, hasta):
        agg[seud] = agg.get(seud, 0) + dev
    items = [{"vendedor": k or "(sin seudónimo)", "devueltos": v} for k, v in agg.items()]
    return jsonify(ok=True, items=sorted(items, key=lambda x: -x["devueltos"]))

@app.get("/api/contabilidad/vendedores_ranking")
def api_vendedores_ranking():
    desde = (request.args.get("desde") or date.today().isoformat()).strip()
    hasta = (request.args.get("hasta") or date.today().isoformat()).strip()
    agg = {}
    for _, seud, vend, dev in _caja_iter_cobros_rango(desde, hasta):
        ref = agg.setdefault(seud or "(sin seudónimo)", {"vendedor": seud or "(sin seudónimo)", "vendidos": 0, "devueltos": 0})
        ref["vendidos"]  += vend
        ref["devueltos"] += dev
    return jsonify(ok=True, items=sorted(agg.values(), key=lambda x: (-x["vendidos"], x["devueltos"])))





#JUEGO #

# ===========================
#  JUEGO + SPINNERS + FIGURAS
#  (Blueprint: /juego/*)
# ===========================
# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
import os, json, re, xml.etree.ElementTree as ET
from datetime import datetime, date
from flask import Blueprint, jsonify, render_template, request, redirect, url_for, session, send_file, make_response

# ============================================================
#  CONFIG & RUTAS (respeta tu DATA_DIR si ya existe)
# ============================================================
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = globals().get("DATA_DIR") or os.getenv("DATA_DIR") or _BASE_DIR
# DB pública (para el navegador /static/*) y DB persistente (Render: DATA_DIR/static/db)
DB_DIR_PUBLIC = os.path.join(_BASE_DIR, "static", "db")
DB_DIR_PERSIST = os.path.join(DATA_DIR, "static", "db")
# Preferimos la pública en local si existe, si no usamos la persistente
DB_DIR = DB_DIR_PUBLIC if os.path.exists(DB_DIR_PUBLIC) else DB_DIR_PERSIST
os.makedirs(DB_DIR_PUBLIC, exist_ok=True)
os.makedirs(DB_DIR_PERSIST, exist_ok=True)
# Archivos core
BINGO_XML     = os.path.join(DB_DIR, "datos_bingo.xml")
HIST_JSON     = os.path.join(DB_DIR, "historial.json")

# Spinners (VMIX overlay + fallback XML)
VMIX_SPINNERS_XML = globals().get("VMIX_SPINNERS_XML", os.path.join(DB_DIR, "vmix_spinners.xml"))
SPINNERS_XML      = globals().get("SPINNERS_XML",      os.path.join(DB_DIR, "spinners.xml"))
SPINNERS_STATE_JSON = os.path.join(DB_DIR, "spinners_state.json")

# Sorteos / Figuras
SORTEOS_XML = globals().get("SORTEOS_XML", os.path.join(DB_DIR, "sorteos.xml"))
SORTEO_JSON_CANDIDATES = [
    os.path.join(DB_DIR, "sorteo.json"),
    os.path.join(DB_DIR, "config_sorteo.json"),
]
FIGURAS_DIR         = os.path.join(DB_DIR, "figuras")
FIGURAS_DEL_DIA_XML = os.path.join(DB_DIR, "figuras_del_dia.xml")
DATOS_FIGURAS_XML   = os.path.join(DB_DIR, "datos_figuras.xml")
os.makedirs(FIGURAS_DIR, exist_ok=True)
FIG_ESTADOS_JSON = os.path.join(DB_DIR, "figuras_estado.json")

# vMix API (HTTP) — opcional
VMIX_HOST = os.getenv("VMIX_HOST", "127.0.0.1")
VMIX_PORT = os.getenv("VMIX_PORT", "8088")
VMIX_OVERLAY_INDEX = int(os.getenv("VMIX_OVERLAY_INDEX", "3"))
VMIX_SPINNER_INPUT = os.getenv("VMIX_SPINNER_INPUT", "SpinnerOverlay")

require_session = globals().get("require_session", None)

# ============================================================
#  BLUEPRINT
# ============================================================
juego_bp = Blueprint("juego", __name__, url_prefix="/juego")


# ============================
#  GANADORES (detección real)
#  - Detecta tablas ganadoras SOLO dentro de los rangos impresos (boletos) del día
#  - Cruza FIGURAS DEL DÍA (figuras_por_fecha.xml) + patrones (datos_figuras.xml)
#  - Escribe ganadores.xml (con colores + números) para usarlo en vMix / overlays
# ============================
from collections import defaultdict

GANADORES_XML         = os.path.join(DB_DIR, "ganadores.xml")
GANADORES_JSON        = os.path.join(DB_DIR, "ganadores.json")
GANADORES_STATE_JSON  = os.path.join(DB_DIR, "ganadores_state.json")
GANADORES_XML_PUBLIC  = os.path.join(BASE_DIR, "static", "db", "ganadores.xml")  # compat (por si alguien lee static/db)

def _safe_json_read(path):
    fn = globals().get("_json_read")
    if callable(fn):
        return fn(path)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def _safe_json_write(path, data):
    fn = globals().get("_json_write")
    if callable(fn):
        return fn(path, data)
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def _agenda_paths():
    """figuras_por_fecha.xml (donde guardas las FIGURAS DEL DÍA con VALOR)."""
    paths = []
    # módulo /escoger-figuras guarda aquí:
    paths.append(os.path.join(BASE_DIR, "static", "db", "figuras_por_fecha.xml"))
    # por si existiera en DATA/static/db
    paths.append(os.path.join(DB_DIR, "figuras_por_fecha.xml"))
    # si alguien lo dejó en raíz
    paths.append(os.path.join(BASE_DIR, "figuras_por_fecha.xml"))
    return [p for p in paths if p]

def _load_figuras_por_fecha(fecha_iso: str):
    """Devuelve lista: [{"nombre":..., "valor":float}, ...]"""
    for path in _agenda_paths():
        if not os.path.exists(path):
            continue
        try:
            root = ET.parse(path).getroot()
        except Exception:
            continue
        dia = None
        for d in root.findall("dia"):
            if (d.attrib.get("fecha") or "").strip() == fecha_iso:
                dia = d
                break
        if dia is None:
            continue
        out = []
        for f in dia.findall("fig"):
            nombre = (f.attrib.get("nombre") or "").strip()
            if not nombre:
                continue
            try:
                valor = float((f.attrib.get("valor") or "0").replace(",", "."))
            except Exception:
                valor = 0.0
            out.append({"nombre": nombre, "valor": round(max(valor, 0.0), 2)})
        return out
    return []

def _catalogo_paths():
    """Posibles ubicaciones de datos_figuras.xml (patrones 5x5)."""
    paths = []
    # variable global (módulo principal)
    gx = globals().get("FIGURAS_XML")
    if gx: paths.append(gx)
    # ubicaciones comunes
    paths.append(os.path.join(BASE_DIR, "static", "db", "datos_figuras.xml"))
    paths.append(os.path.join(DB_DIR, "datos_figuras.xml"))
    # fallback: por si quedó con otro nombre
    paths.append(os.path.join(BASE_DIR, "static", "db", "datos_figuras.XML"))
    return [p for p in paths if p]

def _load_catalogo_figuras_any():
    """Intenta usar load_catalogo_figuras() si existe; si no, carga datos_figuras.xml directamente."""
    fn = globals().get("load_catalogo_figuras")
    if callable(fn):
        try:
            cat = fn()
            if isinstance(cat, dict) and cat:
                return cat
        except Exception:
            pass

    for path in _catalogo_paths():
        if not os.path.exists(path):
            continue
        try:
            root = ET.parse(path).getroot()
        except Exception:
            continue

        catalogo = {}
        # soporta <figuras><figura ...> o cualquier raíz con .//figura
        for f in root.findall(".//figura"):
            nombre = (f.attrib.get("nombre","") or "").strip()
            if not nombre:
                continue
            code = globals().get("code_for")(nombre) if callable(globals().get("code_for")) else re.sub(r"[^A-Z0-9]", "", nombre.upper())[:4] or "FIG"
            cbloq  = f.attrib.get("centro_bloqueado","0")
            celdas = []
            for c in f.findall("celda"):
                try:
                    idx = int(c.attrib.get("idx","0") or 0)
                except Exception:
                    idx = 0
                color = (c.attrib.get("color","#FFFFFF") or "#FFFFFF").upper()
                pos   = (c.attrib.get("pos") or "").upper()
                celdas.append({"idx": idx, "color": color, "pos": pos})
            # completa 25 si falta
            if len(celdas) < 25:
                pos_order = globals().get("POS_25_ROW") or []
                ya = {x.get("idx") for x in celdas}
                for i in range(1,26):
                    if i in ya:
                        continue
                    pos = pos_order[i-1] if i-1 < len(pos_order) else ""
                    celdas.append({"idx": i, "color": "#FFFFFF", "pos": pos})
            celdas.sort(key=lambda x: (x.get("idx") or 0))
            catalogo[code] = {"nombre": nombre, "centro_bloqueado": cbloq, "celdas": celdas}
        if catalogo:
            return catalogo

    return {}

def _get_rangos_en_juego(fecha_iso: str):
    """Rangos impresos (boletos) para la fecha (solo tablas EN JUEGO)."""
    paths = []
    # constantes existentes (según tu app)
    if "IMPRESIONES_XML" in globals(): paths.append(globals().get("IMPRESIONES_XML"))
    if "IMP_XML_PATH" in globals(): paths.append(globals().get("IMP_XML_PATH"))
    if "LOGS_IMPRESIONES_XML" in globals(): paths.append(globals().get("LOGS_IMPRESIONES_XML"))
    # fallback
    paths.append(os.path.join(BASE_DIR, "static", "LOGS", "impresiones.xml"))
    paths.append(os.path.join(DB_DIR, "impresiones.xml"))

    imp_path = next((p for p in paths if p and os.path.exists(p)), None)
    if not imp_path:
        return []

    try:
        root = ET.parse(imp_path).getroot()
    except Exception:
        return []

    rangos = []
    for imp in root.findall(".//impresion"):
        tipo = (imp.get("tipo") or "").strip().lower()
        if tipo != "boletos":
            continue
        f = (imp.findtext("fecha_sorteo") or imp.get("fecha_sorteo") or imp.findtext("fecha") or "").strip()
        # normaliza a ISO si viene como dd/mm/yyyy
        if f and callable(globals().get("_to_iso_date")):
            try:
                f = globals().get("_to_iso_date")(f)
            except Exception:
                pass
        if f != fecha_iso:
            continue

        serie_archivo = (imp.get("serie_archivo") or imp.findtext("serie_archivo") or "").strip()
        desde = (imp.get("desde") or imp.findtext("desde") or "").strip()
        hasta = (imp.get("hasta") or imp.findtext("hasta") or "").strip()
        if not serie_archivo or not desde or not hasta:
            continue
        rangos.append({"serie_archivo": serie_archivo, "desde": desde, "hasta": hasta})

    return rangos

def _pos_to_key(pos: str) -> str:
    """B1 -> b1 (como vienen las columnas en el CSV/XLSX)."""
    pos = (pos or "").strip().upper()
    if not pos:
        return ""
    return pos[0].lower() + pos[1:]  # B10 -> b10

def _is_free_cell(v: str) -> bool:
    vv = (str(v) if v is not None else "").strip().upper()
    return (vv == "" or vv == "0" or vv == "00" or vv == "FREE" or vv == "LIBRE")

def _build_grid_from_row(row_lower: dict):
    """Devuelve grid 5x5 y pos->valor usando b1..o5."""
    def g(col, n):
        return str(row_lower.get(f"{col}{n}", "")).strip()
    grid = [
        [g('b',1), g('i',1), g('n',1), g('g',1), g('o',1)],
        [g('b',2), g('i',2), g('n',2), g('g',2), g('o',2)],
        [g('b',3), g('i',3), g('n',3), g('g',3), g('o',3)],
        [g('b',4), g('i',4), g('n',4), g('g',4), g('o',4)],
        [g('b',5), g('i',5), g('n',5), g('g',5), g('o',5)],
    ]
    pos_map = {}
    pos_order = globals().get("POS_25_ROW") or []
    # rellena pos_map usando pos_order
    flat = []
    for r in range(5):
        for c in range(5):
            flat.append(grid[r][c])
    for i, pos in enumerate(pos_order):
        if i < len(flat):
            pos_map[pos] = flat[i]
    return grid, pos_map

def _required_positions_for_fig(code: str, catalogo: dict):
    """Devuelve (required_pos_list, color_map_pos)"""
    pos_order = globals().get("POS_25_ROW") or []
    color_off = (globals().get("COLOR_OFF") or "#E8E8E8").upper()

    # tabla llena si no está en catálogo
    if code in ("TL1","TL2","TL3","TL4") and code not in catalogo:
        color_on = (globals().get("COLOR_ON") or "#FF0000").upper()
        return list(pos_order), {p: (color_on if p else "#FFFFFF") for p in pos_order}

    f = catalogo.get(code)
    if not f:
        return [], {}

    required = []
    cmap = {}
    for cel in (f.get("celdas") or []):
        pos = (cel.get("pos") or "").upper()
        col = (cel.get("color") or "#FFFFFF").upper()
        if not pos:
            continue
        cmap[pos] = col
        if col not in ("#FFFFFF", color_off, "#E8E8E8"):
            required.append(pos)

    # completa cmap con blancos para posiciones faltantes
    for p in pos_order:
        if p and p not in cmap:
            cmap[p] = "#FFFFFF"

    return required, cmap

def _write_ganadores_xml(fecha_iso: str, ultimo_marcado: int, ganadores: list):
    """Escribe ganadores.xml con estructura + colores + números."""
    root = ET.Element("ganadores", {
        "fecha": str(fecha_iso),
        "ultimo_marcado": (str(ultimo_marcado) if ultimo_marcado else "")
    })

    for g in ganadores:
        ga = ET.SubElement(root, "ganador", {
            "figura": str(g.get("figura","")),
            "fig_code": str(g.get("fig_code","")),
            "valor": f'{float(g.get("valor",0) or 0):.2f}',
            "serie": str(g.get("serie","")),
            "tabla": str(g.get("tabla","")),
            "ultima_bola": str(g.get("ultima_bola",""))
        })

        # resumen
        ET.SubElement(ga, "numeros_figura").text = ",".join(str(x) for x in (g.get("numeros_figura") or []))
        ET.SubElement(ga, "numero_ganador").text = str(g.get("numero_ganador","") or "")

        # grilla
        carton = ET.SubElement(ga, "carton", {"id": str(g.get("tabla",""))})
        pos_order = globals().get("POS_25_ROW") or []
        grid = g.get("grid") or [[""]*5 for _ in range(5)]
        cmap = g.get("color_map_pos") or {}
        req  = set(g.get("required_pos") or [])
        marked = set(str(x) for x in (g.get("marcados_nums") or []))

        # exporta 25 celdas, en orden B1..O5
        # además exporta el número del cartón y si está marcado y si es requerido por la figura
        for i, pos in enumerate(pos_order):
            r = i // 5
            c = i % 5
            num = ""
            try:
                num = str(grid[r][c]).strip()
            except Exception:
                num = ""
            cel = ET.SubElement(carton, "celda", {
                "pos": pos,
                "numero": num,
                "figura_color": (cmap.get(pos,"#FFFFFF") or "#FFFFFF"),
                "requerido": ("1" if pos in req else "0"),
                "marcado": ("1" if (num in marked or (num and num.isdigit() and str(int(num)) in marked) or _is_free_cell(num)) else "0")
            })

    xml_bytes = ET.tostring(root, encoding="utf-8")
    # pretty simple: deja tal cual (vMix no exige "pretty")
    for path in [GANADORES_XML, GANADORES_XML_PUBLIC]:
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "wb") as f:
                f.write(b'<?xml version="1.0" encoding="utf-8"?>\n')
                f.write(xml_bytes)
        except Exception:
            pass

def _write_ganadores_json(fecha_iso: str, ganadores: list, keys: list):
    data = _safe_json_read(GANADORES_JSON) or {}
    data[str(fecha_iso)] = ganadores
    _safe_json_write(GANADORES_JSON, data)
    _safe_json_write(GANADORES_STATE_JSON, {"keys": keys})

def _recalcular_ganadores(fecha_iso: str, stack: list, ultimo_marcado: int = 0):
    """Recalcula TODO (para reversa/reset) y reescribe ganadores.xml/json."""
    ganadores, nuevos, keys = _detectar_ganadores(fecha_iso, stack, ultimo_marcado, recalc=True)
    _write_ganadores_json(fecha_iso, ganadores, keys)
    _write_ganadores_xml(fecha_iso, ultimo_marcado, ganadores)
    return ganadores, nuevos

# ============================================================
#  PERFORMANCE: caches para acelerar lectura/detección de tablas
# ============================================================
try:
    _SERIES_META_CACHE  # noqa
except NameError:
    _SERIES_META_CACHE = {}
    _SERIES_META_LOCK = RLock()
    _CARTONES_INDEX_CACHE = {}
    _CARTONES_INDEX_LOCK = RLock()

def _get_series_meta_cached(archivo: str):
    """Devuelve (df, id_col, ids, id_to_idx, mtime) con caché por mtime del archivo."""
    path = os.path.join(DATA_DIR, archivo)
    if not os.path.exists(path):
        raise FileNotFoundError(f"No existe el archivo de serie: {archivo}")
    try:
        mtime = os.path.getmtime(path)
    except Exception:
        mtime = 0.0

    with _SERIES_META_LOCK:
        c = _SERIES_META_CACHE.get(path)
        if c and c.get("mtime") == mtime:
            return c["df"], c["id_col"], c["ids"], c["id_to_idx"], mtime

    # Lee del disco (lento) solo si cambió
    df = _read_df_for_series(archivo)
    if df is None or df.empty:
        raise ValueError(f"Serie vacía: {archivo}")

    id_col = df.columns[0]
    ids = df[id_col].astype(str).tolist()
    id_to_idx = {v: i for i, v in enumerate(ids)}

    with _SERIES_META_LOCK:
        _SERIES_META_CACHE[path] = {
            "mtime": mtime,
            "df": df,
            "id_col": id_col,
            "ids": ids,
            "id_to_idx": id_to_idx
        }
        # límite simple para evitar crecimiento infinito
        if len(_SERIES_META_CACHE) > 8:
            # borra uno cualquiera (suficiente)
            _SERIES_META_CACHE.pop(next(iter(_SERIES_META_CACHE.keys())), None)

    return df, id_col, ids, id_to_idx, mtime

def _get_cartones_index_cached(fecha_iso: str, serie_archivo: str, merged, df, id_col: str, mtime: float):
    """Construye (1 sola vez) el índice por número para las tablas en juego del día."""
    merged_sig = tuple((int(s), int(e)) for s, e in merged)
    key = (str(fecha_iso), str(serie_archivo), merged_sig, float(mtime))

    with _CARTONES_INDEX_LOCK:
        c = _CARTONES_INDEX_CACHE.get(key)
        if c:
            return c["tickets"], c["by_num"]

    tickets = []
    by_num = defaultdict(list)

    for s, e in merged_sig:
        if s < 0: s = 0
        if e > len(df): e = len(df)
        if e <= s:
            continue
        sub = df.iloc[s:e]

        # Nota: esto corre SOLO cuando cambia el rango / serie (no en cada click)
        for _, row in sub.iterrows():
            rowd = row.to_dict()
            row_lower = {str(k).lower(): str(v).strip() for k, v in rowd.items()}
            carton_id = str(rowd.get(id_col, row_lower.get(str(id_col).lower(), ""))).strip()
            if not carton_id:
                carton_id = str(row_lower.get(str(id_col).lower(), "")).strip()

            grid, pos_map = _build_grid_from_row(row_lower)

            nums_in_carton = set()
            for v in pos_map.values():
                if _is_free_cell(v):
                    continue
                sv = str(v).strip()
                if sv.isdigit():
                    nums_in_carton.add(int(sv))

            tidx = len(tickets)
            tickets.append({
                "carton_id": carton_id,
                "grid": grid,
                "pos_map": pos_map,
                "nums": nums_in_carton
            })
            for n in nums_in_carton:
                by_num[n].append(tidx)

    with _CARTONES_INDEX_LOCK:
        _CARTONES_INDEX_CACHE[key] = {"tickets": tickets, "by_num": dict(by_num)}
        # límite simple para evitar crecimiento infinito
        if len(_CARTONES_INDEX_CACHE) > 20:
            _CARTONES_INDEX_CACHE.clear()

    return tickets, dict(by_num)

def _clear_juego_caches():
    """Útil si quieres limpiar manualmente la caché (por ejemplo al resetear)."""
    try:
        with _SERIES_META_LOCK:
            _SERIES_META_CACHE.clear()
    except Exception:
        pass
    try:
        with _CARTONES_INDEX_LOCK:
            _CARTONES_INDEX_CACHE.clear()
    except Exception:
        pass


def _detectar_ganadores(fecha_iso: str, stack: list, ultimo_marcado: int, recalc: bool = False):
    """
    Detecta ganadores reales (OPTIMIZADO):
      - Solo tablas dentro de rangos impresos (boletos) del día.
      - Solo figuras del día (figuras_por_fecha.xml).
      - En modo normal (recalc=False): SOLO revisa tablas que contienen el ÚLTIMO número marcado
        y SOLO figuras donde ese último número es parte de la figura (esto acelera muchísimo).
      - En modo recalc=True: recalcula todo (para reversa/reset) y revisa todas las tablas/figuras.
    """
    # normaliza marcados
    marked_nums = set()
    for x in (stack or []):
        try:
            xi = int(str(x).strip())
            if 1 <= xi <= 75:
                marked_nums.add(xi)
        except Exception:
            pass

    # estado (para no repetir)
    state = _safe_json_read(GANADORES_STATE_JSON) or {}
    known = set(state.get("keys") or [])
    if recalc:
        known = set()

    # ganadores existentes
    allj = _safe_json_read(GANADORES_JSON) or {}
    ganadores = allj.get(str(fecha_iso), []) if not recalc else []
    nuevos = []

    # figuras del día
    figuras = _load_figuras_por_fecha(fecha_iso)
    if not figuras:
        return ganadores, nuevos, sorted(known)

    # estados de figuras (INACTIVO = no se juega)
    fig_states = {}
    if "FIG_ESTADOS_JSON" in globals():
        try:
            fig_states = (_safe_json_read(globals().get("FIG_ESTADOS_JSON")) or {}).get(str(fecha_iso), {}) or {}
        except Exception:
            fig_states = {}

    # catálogo patrones
    catalogo = _load_catalogo_figuras_any()

    # precompute patrones activos
    patrones = []
    for it in figuras:
        nombre = it.get("nombre", "")
        if not nombre:
            continue
        estado = str(fig_states.get(nombre, "") or "").strip().upper()
        if estado == "INACTIVO":
            continue

        code = globals().get("code_for")(nombre) if callable(globals().get("code_for")) else re.sub(r"[^A-Z0-9]", "", nombre.upper())[:4] or "FIG"
        required_pos, cmap = _required_positions_for_fig(code, catalogo)

        if not required_pos and not (code in ("TL1", "TL2", "TL3", "TL4")):
            any_on = any(v not in ("#FFFFFF", (globals().get("COLOR_OFF") or "#E8E8E8").upper(), "#E8E8E8") for v in (cmap.values() or []))
            if not any_on:
                continue

        patrones.append({
            "nombre": nombre,
            "code": code,
            "valor": float(it.get("valor", 0) or 0),
            "required_pos": required_pos,
            "color_map_pos": cmap
        })

    if not patrones:
        return ganadores, nuevos, sorted(known)

    # rangos impresos (tablas en juego)
    rangos = _get_rangos_en_juego(fecha_iso)
    if not rangos:
        return ganadores, nuevos, sorted(known)

    by_series = defaultdict(list)
    for r in rangos:
        by_series[r["serie_archivo"]].append((r["desde"], r["hasta"]))

    # normaliza último marcado (solo en modo normal)
    try:
        ultimo = int(ultimo_marcado) if ultimo_marcado else 0
    except Exception:
        ultimo = 0

    for serie_archivo, spans in by_series.items():
        try:
            df, id_col, ids, id_to_idx, mtime = _get_series_meta_cached(serie_archivo)
        except Exception:
            continue
        if df is None or df.empty:
            continue

        # convierte spans a intervalos [s,e)
        intervals = []
        for desde, hasta in spans:
            if desde not in id_to_idx or hasta not in id_to_idx:
                continue
            s = id_to_idx[desde]
            e = id_to_idx[hasta] + 1
            if e <= s:
                e = s + 1
            intervals.append((s, e))
        if not intervals:
            continue

        # merge intervals
        intervals.sort()
        merged = []
        for s, e in intervals:
            if not merged or s > merged[-1][1]:
                merged.append([s, e])
            else:
                merged[-1][1] = max(merged[-1][1], e)

        # indexa tablas una sola vez por (fecha, serie, rango, mtime)
        tickets, by_num = _get_cartones_index_cached(str(fecha_iso), str(serie_archivo), merged, df, id_col, mtime)

        # MODO NORMAL: solo tablas que contienen el último número
        if (not recalc) and (1 <= ultimo <= 75):
            cand_idxs = by_num.get(ultimo, [])
        else:
            cand_idxs = range(len(tickets))

        if not cand_idxs:
            continue

        for tidx in cand_idxs:
            t = tickets[tidx]
            carton_id = t.get("carton_id", "")
            grid = t.get("grid")
            pos_map = t.get("pos_map") or {}

            for pat in patrones:
                fig_code = pat["code"]
                key = f"{fecha_iso}|{fig_code}|{serie_archivo}|{carton_id}"
                if key in known:
                    continue

                needed = []
                has_ultimo = False

                for pos in pat["required_pos"]:
                    v = pos_map.get(pos, "")
                    if _is_free_cell(v):
                        continue
                    sv = str(v).strip()
                    if sv.isdigit():
                        n = int(sv)
                        needed.append(n)
                        if (not recalc) and (n == ultimo):
                            has_ultimo = True

                if not needed:
                    continue

                # En modo normal: si la figura NO incluye el último número, NO puede "aparecer" en este click
                if (not recalc) and (1 <= ultimo <= 75) and (not has_ultimo):
                    continue

                ok = True
                for n in needed:
                    if n not in marked_nums:
                        ok = False
                        break

                if ok:
                    known.add(key)
                    numero_ganador = ultimo if ultimo else (needed[-1] if needed else "")

                    info_b = buscar_info_por_boleto(str(fecha_iso), carton_id, serie_archivo)
                    vendedor_b = (info_b.get("vendedor") or "").strip()
                    planilla_b = (info_b.get("planilla") or "").strip()
                    rango_b    = (info_b.get("rango") or "").strip()
                    win = {
                        "fecha": str(fecha_iso),
                        "figura": pat["nombre"],
                        "fig_code": fig_code,
                        "valor": round(float(pat["valor"]), 2),
                        "serie": serie_archivo,
                        "vendedor": vendedor_b,
                        "planilla": planilla_b,
                        "rango": rango_b,
                        "sector": (planilla_b or rango_b),
                        "tabla": carton_id,
                        "ultima_bola": int(ultimo) if ultimo else "",
                        "numero_ganador": int(numero_ganador) if str(numero_ganador).isdigit() else str(numero_ganador),
                        "numeros_figura": needed,
                        "grid": grid,
                        "required_pos": pat["required_pos"],
                        "color_map_pos": pat["color_map_pos"],
                        "marcados_nums": sorted(list(marked_nums)),
                    }
                    ganadores.append(win)
                    nuevos.append(win)

    return ganadores, nuevos, sorted(known)


@juego_bp.get("/ganadores")
def juego_ganadores_list():
    """Lista ganadores detectados (JSON)."""
    fecha = _get_sorteo_fecha()
    data = _safe_json_read(GANADORES_JSON) or {}
    return jsonify(ok=True, fecha=fecha, ganadores=data.get(str(fecha), []))

@juego_bp.get("/ganadores.xml")
def juego_ganadores_xml():
    """XML para vMix: ganadores con colores + números."""
    path = GANADORES_XML if os.path.exists(GANADORES_XML) else GANADORES_XML_PUBLIC
    if not path or not os.path.exists(path):
        # crea vacío
        _write_ganadores_xml(_get_sorteo_fecha(), 0, [])
        path = GANADORES_XML if os.path.exists(GANADORES_XML) else GANADORES_XML_PUBLIC
    return send_file(path, mimetype="application/xml", as_attachment=False, download_name="ganadores.xml")

# ============================================================
#  HELPERS JSON/XML
# ============================================================
def _json_read(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def _json_write(path, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False

def _ensure_hist():
    if not os.path.exists(HIST_JSON):
        _json_write(HIST_JSON, {"stack": [], "ts": datetime.utcnow().isoformat()})

def _read_stack():
    _ensure_hist()
    try:
        data = _json_read(HIST_JSON) or {}
        return [int(x) for x in data.get("stack", []) if 1 <= int(x) <= 75]
    except Exception:
        return []

def _write_stack(stack):
    _json_write(HIST_JSON, {"stack": [int(x) for x in stack], "ts": datetime.utcnow().isoformat()})

def _ensure_bingo_xml():
    if os.path.exists(BINGO_XML):
        return
    root = ET.Element("bingo")
    balotas = ET.SubElement(root, "balotas")
    for n in range(1, 76):
        # 'estado' y 'ultimo'
        ET.SubElement(balotas, "balota", numero=str(n), estado="", ultimo="")
    ET.SubElement(root, "ultimos5").text = ""
    ET.SubElement(root, "totalMarcadas").text = "0"
    ET.SubElement(root, "ultimoMarcado").text = ""
    ET.SubElement(root, "stinger").text = ""
    ET.ElementTree(root).write(BINGO_XML, encoding="utf-8", xml_declaration=True)

def _sync_bingo_xml_from_stack(stack):
    """
    Reglas pedidas (como tu captura):
      - estado="n" para marcadas, "" para no marcadas
      - ultimo="X" SOLO en <balota numero="1">, X = último marcado; todas las demás "", incluida la balota X
      - ultimos5: más reciente → más antiguo
      - ultimoMarcado: último marcado
    """
    _ensure_bingo_xml()
    tree = ET.parse(BINGO_XML); root = tree.getroot()
    balotas_el = root.find("balotas")

    marked = set(int(x) for x in stack)
    last = stack[-1] if stack else None

    # Limpia 'estado' y 'ultimo'
    for b in balotas_el.findall("balota"):
        b.set("estado", "")
        b.set("ultimo", "")

    # Marca presentes
    for b in balotas_el.findall("balota"):
        n = int(b.get("numero"))
        if n in marked:
            b.set("estado", str(n))

    # 👉 "ultimo" solo en la balota numero="1"
    first = balotas_el.find(".//balota[@numero='1']")
    if first is not None:
        first.set("ultimo", str(last) if last is not None else "")

    # ultimos5 (más reciente primero)
    ult5 = list(reversed(stack[-5:])) if stack else []
    root.find("ultimos5").text = ",".join(str(x) for x in ult5)

    root.find("totalMarcadas").text = str(len(marked))
    root.find("ultimoMarcado").text = (str(last) if last is not None else "")

    tree.write(BINGO_XML, encoding="utf-8", xml_declaration=True)

def _to_iso_date(s: str) -> str:
    s = (s or "").strip()
    if not s: return ""
    if "/" in s:
        try:
            d, m, y = s.split("/")
            return f"{y}-{int(m):02d}-{int(d):02d}"
        except Exception:
            pass
    try:
        return str(date.fromisoformat(s))
    except Exception:
        return ""

def _get_sorteo_fecha() -> str:
    for path in SORTEO_JSON_CANDIDATES:
        js = _json_read(path)
        if isinstance(js, dict):
            for k in ("fecha", "fecha_sorteo", "date"):
                if js.get(k):
                    iso = _to_iso_date(str(js[k]))
                    if iso: return iso
    try:
        if os.path.exists(SORTEOS_XML):
            root = ET.parse(SORTEOS_XML).getroot()
            act = root.find(".//dia[@activo='1']") or root.find(".//dia[@active='1']")
            if act is not None and (act.get("fecha") or "").strip():
                return _to_iso_date(act.get("fecha"))
    except Exception:
        pass
    return date.today().isoformat()

# ============================================================
#  SPINNERS: estado persistente + XML fallback + vMix API
# ============================================================
def _ensure_vmix_xml():
    if os.path.exists(VMIX_SPINNERS_XML):
        return
    root = ET.Element("vmix")
    ET.SubElement(root, "overlay", index=str(VMIX_OVERLAY_INDEX), state="off")
    ET.SubElement(root, "spinner", state="idle", locked="0")
    nums = ET.SubElement(root, "nums")
    for _ in range(20):
        ET.SubElement(nums, "n", v="")
    ET.ElementTree(root).write(VMIX_SPINNERS_XML, encoding="utf-8", xml_declaration=True)

def _read_spinners_list():
    for path in (VMIX_SPINNERS_XML, SPINNERS_XML):
        try:
            if not os.path.exists(path): continue
            root = ET.parse(path).getroot()
            out = []
            for n in root.findall(".//n"):
                val = (n.attrib.get("v") if hasattr(n, "attrib") else None) or (n.text or "")
                val = re.sub(r"\D", "", val)[:4]
                out.append(val.zfill(4) if val else "")
            out = (out + [""] * 20)[:20]
            return out
        except Exception:
            pass
    return [""] * 20

def _write_spinners_list(values):
    _ensure_vmix_xml()
    tree = ET.parse(VMIX_SPINNERS_XML); root = tree.getroot()
    nums = root.find("nums")
    if nums is None:
        nums = ET.SubElement(root, "nums")
    for el in list(nums):
        nums.remove(el)
    for i in range(20):
        v = ""
        if i < len(values):
            raw = str(values[i]).strip()
            v = re.sub(r"\D", "", raw)[:4]
            if v: v = v.zfill(4)
        ET.SubElement(nums, "n", v=v)
    tree.write(VMIX_SPINNERS_XML, encoding="utf-8", xml_declaration=True)

def _read_spinner_state():
    st = _json_read(SPINNERS_STATE_JSON) or {}
    return {
        "running": bool(st.get("running", False)),
        "locked":  bool(st.get("locked", False)),
        "overlay_on": bool(st.get("overlay_on", False)),
        "ts": st.get("ts") or datetime.utcnow().isoformat(),
    }

def _write_spinner_state(running=None, locked=None, overlay_on=None):
    cur = _read_spinner_state()
    if running is not None:   cur["running"] = bool(running)
    if locked is not None:    cur["locked"] = bool(locked)
    if overlay_on is not None:cur["overlay_on"] = bool(overlay_on)
    cur["ts"] = datetime.utcnow().isoformat()
    _json_write(SPINNERS_STATE_JSON, cur)

    # Espejo en XML
    _ensure_vmix_xml()
    tree = ET.parse(VMIX_SPINNERS_XML); root = tree.getroot()
    spn = root.find("spinner") or ET.SubElement(root, "spinner")
    spn.set("state", "running" if cur["running"] else "idle")
    spn.set("locked", "1" if cur["locked"] else "0")
    ov = root.find("overlay") or ET.SubElement(root, "overlay", index=str(VMIX_OVERLAY_INDEX))
    ov.set("index", str(VMIX_OVERLAY_INDEX))
    ov.set("state", "on" if cur["overlay_on"] else "off")
    tree.write(VMIX_SPINNERS_XML, encoding="utf-8", xml_declaration=True)
    return cur

def _vmix_call(function, **params):
    import socket
    try:
        import requests
    except Exception:
        return False, "requests-not-available"
    base = f"http://{VMIX_HOST}:{VMIX_PORT}/api/"
    q = {"Function": function}
    q.update({k: str(v) for k, v in params.items() if v is not None})
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.5)
        sock.connect((VMIX_HOST, int(VMIX_PORT)))
        sock.close()
    except Exception:
        return False, "vmix-offline"
    try:
        r = requests.get(base, params=q, timeout=1.5)
        if r.status_code == 200:
            return True, "ok"
        return False, f"http-{r.status_code}"
    except Exception as e:
        return False, f"err:{e}"

def _overlay_on():
    ok, msg = _vmix_call(f"OverlayInput{VMIX_OVERLAY_INDEX}On", Input=VMIX_SPINNER_INPUT)
    st = _write_spinner_state(overlay_on=True)
    return ok, msg, st

def _overlay_off():
    ok, msg = _vmix_call(f"OverlayInput{VMIX_OVERLAY_INDEX}Off", Input=VMIX_SPINNER_INPUT)
    st = _write_spinner_state(overlay_on=False)
    return ok, msg, st

# ============================================================
#  FIGURAS HELPERS
# ============================================================
def _pick_figuras_xml_for_fecha(fecha: str) -> str:
    candidates = [
        os.path.join(FIGURAS_DIR, f"{fecha}.xml"),
        FIGURAS_DEL_DIA_XML,
        DATOS_FIGURAS_XML,
    ]
    for c in candidates:
        if os.path.exists(c): return c
    root = ET.Element("figuras")
    ET.ElementTree(root).write(FIGURAS_DEL_DIA_XML, encoding="utf-8", xml_declaration=True)
    return FIGURAS_DEL_DIA_XML

def _parse_valor_int(v):
    try:
        return int(float(str(v).replace(",", ".").strip()))
    except Exception:
        return 0

def _parse_fig_item_from_text(txt: str):
    s = (txt or "").strip()
    if not s: return None
    s = s.replace("—", "-").replace("–", "-")
    m = re.match(r"^(.*?)[\s:\-]+(\d+(\.\d+)?)\s*$", s)
    if m:
        nombre = m.group(1).strip()
        valor  = _parse_valor_int(m.group(2))
        if nombre:
            return {"nombre": nombre, "valor": valor}
    return {"nombre": s, "valor": 0}

def _read_figuras_from_xml(path_xml: str):
    out = []
    try:
        root = ET.parse(path_xml).getroot()
        for f in root.findall(".//figura"):
            nombre = (f.get("nombre") or f.findtext("figuraNOMBRE") or "").strip()
            valor  = _parse_valor_int(f.get("valor") or f.findtext("figuraVALOR") or 0)
            estado = (f.get("estado") or "").strip().upper() or "INACTIVO"
            if nombre:
                out.append({"nombre": nombre, "valor": valor, "estado": estado})
    except Exception:
        pass
    return out

def _merge_estado_desde_xml(path_xml: str, base_list: list):
    try:
        current = _read_figuras_from_xml(path_xml)
        m = {c["nombre"].strip().lower(): c for c in current}
        out = []
        for f in base_list:
            key = f["nombre"].strip().lower()
            estado = (m.get(key, {}).get("estado") or f.get("estado") or "INACTIVO").upper()
            out.append({"nombre": f["nombre"], "valor": _parse_valor_int(f["valor"]), "estado": estado})
        return out
    except Exception:
        return base_list

def _load_figuras_desde_json_o_xml(fecha: str):
    for path in SORTEO_JSON_CANDIDATES:
        js = _json_read(path)
        if isinstance(js, dict):
            for k in ("figuras_del_dia", "figs_del_dia", "figuras"):
                raw = js.get(k)
                if isinstance(raw, list) and raw:
                    out = []
                    for item in raw:
                        if isinstance(item, dict):
                            nombre = (item.get("nombre") or item.get("name") or "").strip()
                            valor  = _parse_valor_int(item.get("valor") or item.get("value") or 0)
                            if nombre:
                                out.append({"nombre": nombre, "valor": valor, "estado": "INACTIVO"})
                        else:
                            p = _parse_fig_item_from_text(str(item))
                            if p:
                                out.append({"nombre": p["nombre"], "valor": p["valor"], "estado": "INACTIVO"})
                    path_xml = _pick_figuras_xml_for_fecha(fecha)
                    out = _merge_estado_desde_xml(path_xml, out)
                    return (out, path_xml)
    path_xml = _pick_figuras_xml_for_fecha(fecha)
    figs = _read_figuras_from_xml(path_xml)
    return (figs, path_xml)

def _write_figure_state_to_xml(path_xml: str, nombre: str, estado: str, valor: int | None = None):
    estado = (estado or "").strip().upper()
    if estado not in ("INACTIVO", "SE FUE", "SE QUEDO"):
        estado = "INACTIVO"
    if not os.path.exists(path_xml):
        root = ET.Element("figuras")
        ET.ElementTree(root).write(path_xml, encoding="utf-8", xml_declaration=True)
    tree = ET.parse(path_xml); root = tree.getroot()
    target = None
    for f in root.findall(".//figura"):
        n = (f.get("nombre") or f.findtext("figuraNOMBRE") or "").strip()
        if n.lower() == nombre.strip().lower():
            target = f; break
    if target is None:
        target = ET.SubElement(root, "figura", nombre=nombre)
    target.set("nombre", nombre)
    target.set("estado", estado)
    if valor is not None:
        target.set("valor", str(_parse_valor_int(valor)))
    else:
        if target.get("valor") is None:
            target.set("valor", "0")
    tree.write(path_xml, encoding="utf-8", xml_declaration=True)
    return True

# ============================================================
#  RUTAS UI
# ============================================================
@juego_bp.route("/")
def juego_ui():
    try:
        if require_session and not session.get("usuario"):
            return redirect(url_for("login"))
    except Exception:
        pass
    return render_template("juego.html")

@juego_bp.get("/spinner_overlay")
def spinner_overlay_ui():
    return render_template("spinner_overlay.html")

# ============================================================
#  RUTAS: XML públicos (no cache)
# ============================================================
def _no_cache_file(path, mime="application/xml"):
    resp = make_response(send_file(path, mimetype=mime))
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp

@juego_bp.get("/xml/bingo")
def juego_xml_bingo():
    _ensure_bingo_xml()
    return _no_cache_file(BINGO_XML)

@juego_bp.get("/xml/spinners")
def juego_xml_spinners():
    _ensure_vmix_xml()
    return _no_cache_file(VMIX_SPINNERS_XML)

# ============================================================
#  RUTAS ESTADO JUEGO / SPINNERS
# ============================================================
@juego_bp.get("/estado.json")
def juego_estado_json():
    stack = _read_stack()
    last = (stack[-1] if stack else None)
    spinners = _read_spinners_list()
    spn_state = _read_spinner_state()
    return jsonify(
        ok=True,
        stack=stack,
        last=last,
        total=len(stack),
        ultimos5=list(reversed(stack[-5:])),
        spinners=spinners,
        spinner_state=spn_state
    )

@juego_bp.get("/spinners")
def juego_spinners():
    return jsonify(ok=True, spinners=_read_spinners_list(), state=_read_spinner_state())

@juego_bp.post("/spinners/update_list")
def juego_spinners_update_list():
    data = request.get_json(silent=True) or {}
    values = data.get("values") or data.get("spinners") or []
    if not isinstance(values, list):
        return jsonify(ok=False, error="values debe ser lista"), 400
    _write_spinners_list(values)
    return jsonify(ok=True, spinners=_read_spinners_list())

@juego_bp.post("/spinners/launch")
def juego_spinners_launch():
    st = _read_spinner_state()
    if st["locked"]:
        return jsonify(ok=False, error="Spinners bloqueados. Desbloquea para lanzar."), 409
    ok, msg, _ = _overlay_on()
    st = _write_spinner_state(running=True, locked=False, overlay_on=True)
    return jsonify(ok=True, vmix_ok=ok, vmix_msg=msg, state=st)

@juego_bp.post("/spinners/lock")
def juego_spinners_lock():
    ok, msg, _ = _overlay_off()
    st = _write_spinner_state(running=False, locked=True, overlay_on=False)
    return jsonify(ok=True, vmix_ok=ok, vmix_msg=msg, state=st)

@juego_bp.post("/spinners/unlock")
def juego_spinners_unlock():
    st = _write_spinner_state(locked=False)
    return jsonify(ok=True, state=st)

@juego_bp.post("/spinners/overlay")
def juego_spinners_overlay():
    data = request.get_json(silent=True) or {}
    action = (data.get("action") or "").lower()
    if action not in ("on", "off"):
        return jsonify(ok=False, error="action debe ser 'on' o 'off'"), 400
    if action == "on":
        ok, msg, st = _overlay_on()
    else:
        ok, msg, st = _overlay_off()
    return jsonify(ok=True, vmix_ok=ok, vmix_msg=msg, state=st)

# ============================================================
#  RUTAS JUEGO
# ============================================================
@juego_bp.post("/marcar")
def juego_marcar():
    data = request.get_json(silent=True) or {}
    numero = str(data.get("numero", "")).strip()
    if not numero.isdigit():
        return jsonify(success=False, error="Número inválido"), 400

    n = int(numero)
    if n < 1 or n > 75:
        return jsonify(success=False, error="Rango 1–75"), 400

    stack = _read_stack()
    if n not in stack:
        stack.append(n)
        _write_stack(stack)
        _sync_bingo_xml_from_stack(stack)

    # escribe stinger/última bola (si lo usas en vMix)
    try:
        tree = ET.parse(BINGO_XML); root = tree.getroot()
        st = root.find("stinger") or ET.SubElement(root, "stinger")
        st.text = str(n)
        tree.write(BINGO_XML, encoding="utf-8", xml_declaration=True)
    except Exception:
        pass

    # ===== Detectar GANADORES reales (figuras del día + rangos impresos) =====
    fecha = _get_sorteo_fecha()
    ganadores_nuevos = []
    ganadores_total = []
    try:
        ganadores_total, ganadores_nuevos, keys = _detectar_ganadores(str(fecha), stack, n, recalc=False)
        if ganadores_nuevos:
            _write_ganadores_json(str(fecha), ganadores_total, keys)
            _write_ganadores_xml(str(fecha), n, ganadores_total)
    except Exception:
        pass

    return jsonify(
        success=True,
        stack=stack,
        last=n,
        total=len(stack),
        ultimos5=list(reversed(stack[-5:])),
        ganadores_nuevos=ganadores_nuevos,
        ganadores_total=len(ganadores_total),
        fecha=str(fecha)
    )


@juego_bp.post("/reversa")
def juego_reversa():
    data = request.get_json(silent=True) or {}
    stack = _read_stack()
    if str(data.get("all", "")).lower() in ("1", "true", "si", "sí", "yes"):
        stack = []
    else:
        if stack:
            stack.pop()

    _write_stack(stack)
    _sync_bingo_xml_from_stack(stack)

    last = (stack[-1] if stack else 0)

    try:
        tree = ET.parse(BINGO_XML); root = tree.getroot()
        st = root.find("stinger") or ET.SubElement(root, "stinger")
        st.text = (str(last) if last else "")
        tree.write(BINGO_XML, encoding="utf-8", xml_declaration=True)
    except Exception:
        pass

    # Recalcula ganadores (por si desmarcaste un número)
    try:
        fecha = _get_sorteo_fecha()
        ganadores_total, _ = _recalcular_ganadores(str(fecha), stack, int(last) if last else 0)
        gcount = len(ganadores_total)
    except Exception:
        gcount = 0

    return jsonify(
        success=True,
        stack=stack,
        last=(stack[-1] if stack else None),
        total=len(stack),
        ultimos5=list(reversed(stack[-5:])),
        ganadores_total=gcount
    )


@juego_bp.post("/reset")
def juego_reset():
    _write_stack([])
    _sync_bingo_xml_from_stack([])
    try:
        tree = ET.parse(BINGO_XML); root = tree.getroot()
        st = root.find("stinger") or ET.SubElement(root, "stinger"); st.text = ""
        tree.write(BINGO_XML, encoding="utf-8", xml_declaration=True)
    except Exception:
        pass

    # apaga overlay/spinner
    _overlay_off()
    _write_spinner_state(running=False, locked=False, overlay_on=False)

    # limpia ganadores
    try:
        fecha = _get_sorteo_fecha()
        # borra lista del día en ganadores.json
        data = _safe_json_read(GANADORES_JSON) or {}
        data[str(fecha)] = []
        _safe_json_write(GANADORES_JSON, data)
        _safe_json_write(GANADORES_STATE_JSON, {"keys": []})
        _write_ganadores_xml(str(fecha), 0, [])
    except Exception:
        pass

    return jsonify(success=True)


@juego_bp.post("/activar_stinger")
def juego_activar_stinger():
    data = request.get_json(silent=True) or {}
    numero = str(data.get("numero", "")).strip()
    if not numero:
        return jsonify(success=False, error="numero requerido"), 400
    _ensure_bingo_xml()
    tree = ET.parse(BINGO_XML); root = tree.getroot()
    st = root.find("stinger") or ET.SubElement(root, "stinger")
    st.text = numero
    tree.write(BINGO_XML, encoding="utf-8", xml_declaration=True)
    return jsonify(success=True)

# ============================================================
#  SORTEO / FIGURAS
# ============================================================
@juego_bp.get("/sorteo_fecha")
def juego_sorteo_fecha():
    return jsonify(ok=True, fecha=_get_sorteo_fecha())


@juego_bp.get("/tabla_ganadora_random")
def juego_tabla_ganadora_random():
    """
    Si ya hay ganadores detectados, devuelve el ÚLTIMO ganador (real).
    Si aún no hay ganadores, devuelve una tabla aleatoria SOLO dentro de los rangos impresos del día.
    """
    fecha = _get_sorteo_fecha()

    # 1) Si existen ganadores reales, devuelve el último
    try:
        data = _safe_json_read(GANADORES_JSON) or {}
        wins = data.get(str(fecha), []) or []
        if wins:
            w = wins[-1]
            return jsonify(
                ok=True,
                tipo="ganadora",
                fecha=str(fecha),
                serie_archivo=w.get("serie", ""),
                tabla_num=w.get("tabla", ""),
                figura=w.get("figura", ""),
                valor=w.get("valor", 0),
                ultima_bola=w.get("ultima_bola", ""),
                numeros_figura=w.get("numeros_figura", []),
                grid=w.get("grid", [])
            )
    except Exception:
        pass

    # 2) Fallback: tabla aleatoria dentro de rangos impresos
    rangos = _get_rangos_en_juego(str(fecha))
    if not rangos:
        return jsonify(ok=False, error="No hay rangos impresos (boletos) para esta fecha"), 404

    # elige un rango aleatorio
    r = random.choice(rangos)
    serie_archivo = r["serie_archivo"]
    try:
        df = _read_df_for_series(serie_archivo)
    except Exception:
        return jsonify(ok=False, error=f"No se pudo leer la serie {serie_archivo}"), 500

    if df is None or df.empty:
        return jsonify(ok=False, error=f"Serie vacía: {serie_archivo}"), 500

    id_col = df.columns[0]
    ids = df[id_col].astype(str).tolist()
    id_to_idx = {v: i for i, v in enumerate(ids)}
    if r["desde"] not in id_to_idx or r["hasta"] not in id_to_idx:
        return jsonify(ok=False, error="Rango no encontrado en la serie"), 404

    s = id_to_idx[r["desde"]]
    e = id_to_idx[r["hasta"]] + 1
    if e <= s:
        e = s + 1
    pick_idx = random.randrange(s, min(e, len(df)))
    row = df.iloc[pick_idx].to_dict()
    row_lower = {str(k).lower(): str(v).strip() for k, v in row.items()}

    # construye grid (misma forma que la UI espera)
    grid, _ = _build_grid_from_row(row_lower)
    tabla_num = str(row.get(id_col, row_lower.get(str(id_col).lower(), ""))).strip()

    return jsonify(
        ok=True,
        tipo="aleatoria",
        fecha=str(fecha),
        serie_archivo=serie_archivo,
        tabla_num=tabla_num,
        grid=grid
    )


@juego_bp.get("/figuras")
def juego_figuras_list():
    # Lee FIGURAS DEL DÍA desde static/db/figuras_por_fecha.xml (mismo origen de /escoger-figuras)
    fecha = _get_sorteo_fecha()
    figs = _load_figuras_por_fecha(str(fecha))
    estados = {}
    try:
        if "FIG_ESTADOS_JSON" in globals():
            estados = (_safe_json_read(FIG_ESTADOS_JSON) or {}).get(str(fecha), {}) or {}
    except Exception:
        estados = {}

    out = []
    for f in figs:
        nombre = f.get("nombre", "")
        if not nombre:
            continue
        out.append({
            "nombre": nombre,
            "valor": float(f.get("valor", 0) or 0),
            "estado": (estados.get(nombre) or "ACTIVO")
        })

    origen = next((p for p in _agenda_paths() if os.path.exists(p)), "")
    return jsonify(ok=True, fecha=fecha, origen_xml=origen, figuras=out, figuras_del_dia=out, total=len(out))


@juego_bp.post("/figuras/estado")
def juego_figuras_estado():
    data = request.get_json(silent=True) or {}
    nombre = (data.get("nombre") or "").strip()
    estado = (data.get("estado") or "").strip().upper()
    valor  = data.get("valor", None)
    if not nombre:
        return jsonify(ok=False, error="nombre requerido"), 400
    if estado not in ("INACTIVO", "SE FUE", "SE QUEDO"):
        return jsonify(ok=False, error="estado inválido"), 400
    fecha = _get_sorteo_fecha()
    path_xml = _pick_figuras_xml_for_fecha(fecha)
    ok = _write_figure_state_to_xml(path_xml, nombre, estado, valor)
    if not ok:
        return jsonify(ok=False, error="no se pudo escribir XML"), 500
    cache = _json_read(FIG_ESTADOS_JSON) or {}
    cache.setdefault(fecha, {})
    cache[fecha][nombre] = estado
    _json_write(FIG_ESTADOS_JSON, cache)
    figs = _read_figuras_from_xml(path_xml)
    return jsonify(ok=True, fecha=fecha, origen_xml=path_xml, figuras=figs)

@juego_bp.post("/figuras/sync-xml")
def juego_figuras_sync_xml():
    fecha = _get_sorteo_fecha()
    cache = _json_read(FIG_ESTADOS_JSON) or {}
    estados = cache.get(fecha, {})
    path_xml = _pick_figuras_xml_for_fecha(fecha)
    actual = {f["nombre"].strip().lower(): f for f in _read_figuras_from_xml(path_xml)}
    for nombre, estado in estados.items():
        low = nombre.strip().lower()
        valor = actual.get(low, {}).get("valor", 0)
        _write_figure_state_to_xml(path_xml, nombre, estado, valor)
    figs = _read_figuras_from_xml(path_xml)
    return jsonify(ok=True, fecha=fecha, origen_xml=path_xml, figuras=figs)

# ============================================================
#  REGISTRO BP + INICIALIZACIÓN
# ============================================================
def register_juego(app):
    app.register_blueprint(juego_bp)
    _ensure_bingo_xml()
    _ensure_hist()
    _ensure_vmix_xml()
    _write_spinner_state(running=False, locked=False, overlay_on=False)

try:
    app  # noqa
    if "juego" not in [bp.name for bp in app.blueprints.values()]:
        register_juego(app)
except Exception:
    pass



# ================== FIN JUEGO ==================

# inicio spinners #



# ===================== SPINNERS API + OVERLAY =====================

# ===========================
# ==== [ SPINNERS + VMIX OVERLAY ] ============================================
import os, xml.etree.ElementTree as ET
from datetime import datetime
from flask import request, jsonify, render_template

# ---------- Config ----------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = globals().get("DATA_DIR", os.path.join(BASE_DIR, "DATA"))
DB_DIR = os.path.join(DATA_DIR, "static", "db")
os.makedirs(DB_DIR, exist_ok=True)

VMIX_SPINNERS_XML = os.path.join(DB_DIR, "vmix_spinners.xml")
SPINNERS_XML      = os.path.join(DB_DIR, "spinners.xml")

# Cambia esto si tu vMix API está en otra IP/puerto:
# Ej: "http://127.0.0.1:8088/api"
VMIX_API_URL = os.getenv("VMIX_API_URL", "").strip()  # vacío = desactivado
VMIX_OVERLAY_INDEX = int(os.getenv("VMIX_OVERLAY_INDEX", "1"))  # Overlay 1 por defecto

# ---------- Utilidades XML ----------
def _ensure_xml_files():
    """Crea plantillas XML si no existen."""
    if not os.path.exists(SPINNERS_XML):
        root = ET.Element("spinners")
        # 20 slots inicialmente vacíos (0000) y unlocked
        for i in range(1, 21):
            ET.SubElement(root, "spinner", index=str(i), value="0000", locked="0", used="0")
        ET.indent(root, space="  ")
        ET.ElementTree(root).write(SPINNERS_XML, encoding="utf-8", xml_declaration=True)

    if not os.path.exists(VMIX_SPINNERS_XML):
        root = ET.Element("vmix")
        overlay = ET.SubElement(root, "overlay", index=str(VMIX_OVERLAY_INDEX), state="off")
        # espejo de los 20
        group = ET.SubElement(root, "spinners")
        for i in range(1, 21):
            ET.SubElement(group, "spinner", index=str(i), value="0000", locked="0", used="0")
        ET.indent(root, space="  ")
        ET.ElementTree(root).write(VMIX_SPINNERS_XML, encoding="utf-8", xml_declaration=True)

def _read_spinners():
    _ensure_xml_files()
    tree = ET.parse(SPINNERS_XML); root = tree.getroot()
    data = []
    for node in root.findall("spinner"):
        data.append({
            "index": int(node.get("index", "0")),
            "value": node.get("value", "0000"),
            "locked": node.get("locked", "0") == "1",
            "used": node.get("used", "0") == "1",
        })
    return data

def _write_spinners(spinners):
    root = ET.Element("spinners")
    for s in spinners:
        ET.SubElement(root, "spinner",
                      index=str(s["index"]),
                      value=str(s["value"]).zfill(4)[:4],
                      locked="1" if s.get("locked") else "0",
                      used="1" if s.get("used") else "0")
    ET.indent(root, space="  ")
    ET.ElementTree(root).write(SPINNERS_XML, encoding="utf-8", xml_declaration=True)

def _read_vmix():
    _ensure_xml_files()
    t = ET.parse(VMIX_SPINNERS_XML); r = t.getroot()
    return t, r

def _mirror_to_vmix(spinners, overlay_state=None):
    """Espeja lista de spinners a vmix_spinners.xml y opcionalmente cambia overlay on/off."""
    t, r = _read_vmix()
    # overlay
    overlay = r.find("overlay")
    if overlay is None:
        overlay = ET.SubElement(r, "overlay", index=str(VMIX_OVERLAY_INDEX), state="off")
    if overlay_state in ("on", "off"):
        overlay.set("state", overlay_state)

    # grupo
    group = r.find("spinners")
    if group is None:
        group = ET.SubElement(r, "spinners")
    # limpia
    for child in list(group):
        group.remove(child)
    # reescribe
    for s in spinners:
        ET.SubElement(group, "spinner",
                      index=str(s["index"]),
                      value=str(s["value"]).zfill(4)[:4],
                      locked="1" if s.get("locked") else "0",
                      used="1" if s.get("used") else "0")
    ET.indent(r, space="  ")
    t.write(VMIX_SPINNERS_XML, encoding="utf-8", xml_declaration=True)

# ---------- vMix API (opcional) ----------
def _vmix_call(function_name, **params):
    """
    Llama al API HTTP de vMix si VMIX_API_URL está definido.
    Ej: _vmix_call("OverlayInput1On")
    """
    if not VMIX_API_URL:
        return {"ok": False, "msg": "VMIX_API_URL no configurado"}
    try:
        import requests
        # Construye query tipo: ?Function=OverlayInput1On
        q = {"Function": function_name}
        # anexa params si aplica
        for k, v in params.items():
            q[k] = v
        resp = requests.get(VMIX_API_URL, params=q, timeout=3)
        return {"ok": resp.ok, "status": resp.status_code}
    except Exception as e:
        return {"ok": False, "msg": str(e)}

# ---------- Rutas JSON ----------
@app.get("/juego/spinners")
def get_spinners():
    """
    Devuelve los 20 spinners: index, value (0000-9999), locked, used
    """
    data = sorted(_read_spinners(), key=lambda x: x["index"])
    return jsonify(data)

@app.post("/juego/spinners/generar")
def post_spinner_generar():
    """
    Pone el visor del spinner (index) en 0000, no toca 'value' si ya existía
    pero deja 'used=0' y 'locked=0' si quieres relanzar.
    Body: {index:int}
    """
    payload = request.get_json(force=True, silent=True) or {}
    index = int(payload.get("index", 1))
    sp = _read_spinners()
    found = None
    for s in sp:
        if s["index"] == index:
            found = s; break
    if not found:
        return jsonify({"ok": False, "msg": "index inválido"}), 400

    # GENERAR → reset visual, desbloqueado y sin usado
    found["value"] = "0000"
    found["used"] = False
    found["locked"] = False
    _write_spinners(sp)
    _mirror_to_vmix(sp)   # espejo

    return jsonify({"ok": True, "index": index, "value": found["value"]})

@app.post("/juego/spinners/lanzar")
def post_spinner_lanzar():
    """
    Lanza el spinner al valor objetivo, marca used=1, locked=1 y enciende Overlay 1 (opcional).
    Body: {index:int, target:str|int, overlay_on:bool}
    """
    payload = request.get_json(force=True, silent=True) or {}
    index = int(payload.get("index", 1))
    target = str(payload.get("target", "0000")).zfill(4)[:4]
    overlay_on = bool(payload.get("overlay_on", True))

    sp = _read_spinners()
    found = None
    for s in sp:
        if s["index"] == index:
            found = s; break
    if not found:
        return jsonify({"ok": False, "msg": "index inválido"}), 400
    if found.get("locked"):
        return jsonify({"ok": False, "msg": "Este spinner está bloqueado"}), 403

    # asigna valor, usa y bloquea
    found["value"] = target
    found["used"] = True
    found["locked"] = True
    _write_spinners(sp)

    # overlay ON (XML) y (opcional) API vMix
    _mirror_to_vmix(sp, overlay_state="on" if overlay_on else None)
    vmix_api = None
    if overlay_on:
        # Ej.: OverlayInput1On, OverlayInput1Off  (vMix es 1-indexed)
        vmix_api = _vmix_call(f"OverlayInput{VMIX_OVERLAY_INDEX}On")

    return jsonify({"ok": True, "index": index, "value": target, "vmix_api": vmix_api})

@app.post("/juego/spinners/unlock")
def post_spinner_unlock():
    """
    Desbloquea un spinner (o todos). Body: {index:int} o {all:true}
    """
    payload = request.get_json(force=True, silent=True) or {}
    all_flag = bool(payload.get("all"))
    sp = _read_spinners()

    if all_flag:
        for s in sp:
            s["locked"] = False
        _write_spinners(sp); _mirror_to_vmix(sp)
        return jsonify({"ok": True, "msg": "Todos desbloqueados"})

    index = int(payload.get("index", 1))
    for s in sp:
        if s["index"] == index:
            s["locked"] = False
            _write_spinners(sp); _mirror_to_vmix(sp)
            return jsonify({"ok": True, "index": index, "locked": False})
    return jsonify({"ok": False, "msg": "index inválido"}), 400

@app.post("/juego/spinners/lock")
def post_spinner_lock():
    """
    Bloquea un spinner (o todos). Body: {index:int} o {all:true}
    """
    payload = request.get_json(force=True, silent=True) or {}
    all_flag = bool(payload.get("all"))
    sp = _read_spinners()

    if all_flag:
        for s in sp:
            s["locked"] = True
        _write_spinners(sp); _mirror_to_vmix(sp)
        return jsonify({"ok": True, "msg": "Todos bloqueados"})

    index = int(payload.get("index", 1))
    for s in sp:
        if s["index"] == index:
            s["locked"] = True
            _write_spinners(sp); _mirror_to_vmix(sp)
            return jsonify({"ok": True, "index": index, "locked": True})
    return jsonify({"ok": False, "msg": "index inválido"}), 400

@app.post("/juego/spinners/reset_used")
def post_spinner_reset_used():
    """
    Resetea 'used' de todos a 0 (útil al preparar un nuevo sorteo).
    """
    sp = _read_spinners()
    for s in sp:
        s["used"] = False
        s["locked"] = False
        s["value"] = "0000"
    _write_spinners(sp)
    _mirror_to_vmix(sp, overlay_state="off")
    return jsonify({"ok": True})

# ---------- Rutas Overlay (HTML) ----------
@app.get("/juego/spinner_overlay")
def spinner_overlay_page():
    """
    Overlay transparente para vMix (usa tu spinner_overlay.html)
    """
    # Si usas render_template con archivo físico:
    return render_template("spinner_overlay.html")

# (Opcional) API rápida para apagar overlay vía backend + vMix API
@app.post("/vmix/overlay/off")
def vmix_overlay_off():
    sp = _read_spinners()
    _mirror_to_vmix(sp, overlay_state="off")
    vmix_api = _vmix_call(f"OverlayInput{VMIX_OVERLAY_INDEX}Off")
    return jsonify({"ok": True, "vmix_api": vmix_api})
# ==== [ FIN SPINNERS ] ========================================================






#--------FIN DE SPINNERS------------##





# ============================================================
# HOTFIX GLBINGO: resolver rutas de DB/LOGS + guardar figuras del día
# (Evita que "Figuras del día" salga vacío por estar leyendo/escribiendo
#  en carpetas distintas: static/db vs DATA/static/db, etc.)
# ============================================================
import os as _os
import json as _json
import datetime as _dt
import xml.etree.ElementTree as _ET

def _uniq(seq):
    seen=set()
    out=[]
    for x in seq:
        if not x or x in seen:
            continue
        seen.add(x)
        out.append(x)
    return out

def _candidate_db_dirs_hotfix():
    base = _os.path.dirname(_os.path.abspath(__file__))
    parent = _os.path.dirname(base)
    env_data = _os.environ.get("DATA_DIR", "").strip()

    candidates = []
    # 1) DATA_DIR (Render / disco persistente)
    if env_data:
        candidates += [
            _os.path.join(env_data, "static", "db"),
            _os.path.join(env_data, "db"),
        ]
    # 2) Carpeta DATA dentro del proyecto
    candidates += [
        _os.path.join(base, "DATA", "static", "db"),
        _os.path.join(base, "static", "db"),
        # por si estás ejecutando desde otra copia/carpeta
        _os.path.join(parent, "DATA", "static", "db"),
        _os.path.join(parent, "static", "db"),
    ]
    # 3) Algunos nombres comunes (si existen)
    for name in ["GOLPEDESUERTE.EC", "SISTEMA GOLPE", "SISTEMA_GOLPE"]:
        candidates += [
            _os.path.join(parent, name, "DATA", "static", "db"),
            _os.path.join(parent, name, "static", "db"),
        ]

    candidates = _uniq([c for c in candidates if _os.path.isdir(c)])

    # Escoge el "mejor" directorio por contenido real
    def score(d):
        s = 0.0
        def add_file(fname, weight, min_sz):
            p = _os.path.join(d, fname)
            if _os.path.exists(p):
                try:
                    sz = _os.path.getsize(p)
                except Exception:
                    sz = 0
                s_local = weight if sz >= min_sz else weight * 0.2
                return s_local
            return 0.0

        s += add_file("datos_figuras.xml", 6, 500)
        s += add_file("figuras_por_fecha.xml", 5, 80)
        s += add_file("datos_bingo.xml", 3, 80)
        s += add_file("historial.json", 2, 10)
        # bonus por cantidad de XML
        try:
            s += len([f for f in _os.listdir(d) if f.lower().endswith(".xml")]) * 0.01
        except Exception:
            pass
        return s

    if not candidates:
        # fallback
        return [ _os.path.join(base, "static", "db") ]
    best = max(candidates, key=score)
    # prioridad: best primero, luego el resto
    ordered = [best] + [c for c in candidates if c != best]
    return ordered

def _pick_best_db_dir_hotfix():
    return _candidate_db_dirs_hotfix()[0]

def _candidate_logs_dirs_hotfix():
    base = _os.path.dirname(_os.path.abspath(__file__))
    parent = _os.path.dirname(base)
    env_data = _os.environ.get("DATA_DIR", "").strip()

    candidates = []
    if env_data:
        candidates += [
            _os.path.join(env_data, "static", "LOGS"),
            _os.path.join(env_data, "LOGS"),
        ]
    candidates += [
        _os.path.join(base, "DATA", "static", "LOGS"),
        _os.path.join(base, "static", "LOGS"),
        _os.path.join(parent, "DATA", "static", "LOGS"),
        _os.path.join(parent, "static", "LOGS"),
    ]
    candidates = _uniq([c for c in candidates if _os.path.isdir(c)])
    if not candidates:
        # crea al menos la local
        local = _os.path.join(base, "static", "LOGS")
        _os.makedirs(local, exist_ok=True)
        candidates = [local]
    return candidates

def _agenda_paths_hotfix():
    # Devuelve TODAS las rutas posibles de figuras_por_fecha.xml (mejor primero)
    paths=[]
    for d in _candidate_db_dirs_hotfix():
        paths.append(_os.path.join(d, "figuras_por_fecha.xml"))
    return _uniq(paths)

def _datos_figuras_paths_hotfix():
    paths=[]
    for d in _candidate_db_dirs_hotfix():
        paths.append(_os.path.join(d, "datos_figuras.xml"))
    return _uniq(paths)

def _impresiones_paths_hotfix():
    # admite LOGS y también db (por si alguien lo guardó allí)
    paths=[]
    for d in _candidate_logs_dirs_hotfix():
        paths.append(_os.path.join(d, "impresiones.xml"))
    for d in _candidate_db_dirs_hotfix():
        paths.append(_os.path.join(d, "impresiones.xml"))
    return _uniq(paths)

def _parse_fecha_flexible(fecha_str):
    if not fecha_str:
        raise ValueError("fecha vacía")
    s = str(fecha_str).strip()
    # yyyy-mm-dd
    try:
        return _dt.datetime.strptime(s, "%Y-%m-%d").date()
    except Exception:
        pass
    # dd/mm/yyyy
    try:
        return _dt.datetime.strptime(s, "%d/%m/%Y").date()
    except Exception:
        pass
    # dd-mm-yyyy
    try:
        return _dt.datetime.strptime(s, "%d-%m-%Y").date()
    except Exception:
        pass
    raise ValueError(f"Formato de fecha no válido: {s}")

def _ensure_agenda_file(path):
    _os.makedirs(_os.path.dirname(path), exist_ok=True)
    if _os.path.exists(path):
        # si está corrupto, lo re-crea
        try:
            _ET.parse(path)
            return
        except Exception:
            pass
    root = _ET.Element("agenda")
    _ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)

def _write_agenda_for_fecha(path, fecha_iso, figuras):
    """
    figuras: lista de dicts {nombre, valor, estado}
    """
    _ensure_agenda_file(path)
    tree = _ET.parse(path)
    root = tree.getroot()

    # Busca/crea nodo del día
    dia = None
    for d in root.findall("dia"):
        if (d.get("fecha") or "").strip() == fecha_iso:
            dia = d
            break
    if dia is None:
        dia = _ET.SubElement(root, "dia")
        dia.set("fecha", fecha_iso)

    # limpia y vuelve a escribir
    for child in list(dia):
        dia.remove(child)

    for it in figuras:
        nombre = str(it.get("nombre","")).strip()
        if not nombre:
            continue
        fig = _ET.SubElement(dia, "fig")
        fig.set("nombre", nombre)
        fig.set("valor", str(it.get("valor","")).strip())
        fig.set("estado", str(it.get("estado","en_juego")).strip() or "en_juego")

    tree.write(path, encoding="utf-8", xml_declaration=True)

def _debug_print_paths_hotfix():
    try:
        best_db = _pick_best_db_dir_hotfix()
        print("\n[GLBINGO HOTFIX] DB_DIR elegido:", best_db)
        print("[GLBINGO HOTFIX] Agenda candidates:")
        for p in _agenda_paths_hotfix():
            print(" -", p, "(existe)" if _os.path.exists(p) else "")
        print("[GLBINGO HOTFIX] Datos figuras candidates:")
        for p in _datos_figuras_paths_hotfix():
            print(" -", p, "(existe)" if _os.path.exists(p) else "")
        print("[GLBINGO HOTFIX] Impresiones candidates:")
        for p in _impresiones_paths_hotfix():
            print(" -", p, "(existe)" if _os.path.exists(p) else "")
        print("")
    except Exception as e:
        print("[GLBINGO HOTFIX] No se pudo imprimir rutas:", e)

# 1) Sobrescribimos helpers usados por el módulo de juego (si existen)
globals()["_agenda_paths"] = _agenda_paths_hotfix
globals()["_impresiones_paths"] = _impresiones_paths_hotfix

# 2) Forzamos variables globales típicas (si existen) a apuntar al mejor DB_DIR
try:
    _best_db = _pick_best_db_dir_hotfix()
    for _var, _fname in [
        ("DB_DIR", None),
        ("BINGO_XML", "datos_bingo.xml"),
        ("HIST_JSON", "historial.json"),
        ("GANADORES_XML", "ganadores_bingo.xml"),
        ("DATOS_FIGURAS_XML", "datos_figuras.xml"),
        ("FIGURAS_FECHA_XML", "figuras_por_fecha.xml"),
    ]:
        if _var in globals():
            globals()[_var] = _best_db if _fname is None else _os.path.join(_best_db, _fname)
except Exception:
    pass

# 3) PARCHAMOS la vista /escoger-figuras/guardar para guardar en TODAS las rutas candidatas
def _guardar_figuras_para_fecha_hotfix():
    from flask import request, redirect, url_for, flash
    # Acepta tanto form como JSON (por si mañana se cambia el front)
    fecha_raw = (request.form.get("fecha") or request.args.get("fecha") or
                 (request.json.get("fecha") if request.is_json else None))
    try:
        fecha = _parse_fecha_flexible(fecha_raw)
    except Exception as e:
        flash(f"Fecha inválida: {e}", "danger")
        return redirect(url_for("escoger_figuras"))

    seleccion_raw = (request.form.get("seleccion") or
                     (request.json.get("seleccion") if request.is_json else None))

    if not seleccion_raw:
        flash("No se recibió selección de figuras.", "danger")
        return redirect(url_for("escoger_figuras_view", fecha=fecha.isoformat()) if "escoger_figuras_view" in app.view_functions else url_for("escoger_figuras"))

    try:
        figuras = _json.loads(seleccion_raw)
        if not isinstance(figuras, list):
            raise ValueError("seleccion no es lista")
    except Exception as e:
        flash(f"Selección inválida: {e}", "danger")
        return redirect(url_for("escoger_figuras_view", fecha=fecha.isoformat()) if "escoger_figuras_view" in app.view_functions else url_for("escoger_figuras"))

    # Normaliza
    norm=[]
    for it in figuras:
        if not isinstance(it, dict):
            continue
        nombre = str(it.get("nombre","")).strip()
        if not nombre:
            continue
        norm.append({
            "nombre": nombre,
            "valor": str(it.get("valor","")).strip(),
            "estado": str(it.get("estado","en_juego")).strip() or "en_juego"
        })

    # Escribe en todas las rutas candidatas
    ok=0
    for path in _agenda_paths_hotfix():
        try:
            _write_agenda_for_fecha(path, fecha.isoformat(), norm)
            ok += 1
        except Exception as e:
            print("[GLBINGO HOTFIX] Error guardando agenda en", path, "->", e)

    if ok > 0:
        flash(f"Figuras del día guardadas en {ok} ruta(s).", "success")
    else:
        flash("No se pudo guardar la agenda de figuras (revisa permisos/carpetas).", "danger")

    # vuelve a la vista de escoger para esa fecha
    if "escoger_figuras_view" in app.view_functions:
        return redirect(url_for("escoger_figuras_view", fecha=fecha.isoformat()))
    return redirect(url_for("escoger_figuras"))

try:
    if "guardar_figuras_para_fecha" in app.view_functions:
        app.view_functions["guardar_figuras_para_fecha"] = _guardar_figuras_para_fecha_hotfix
except Exception as e:
    print("[GLBINGO HOTFIX] No se pudo parchear guardar_figuras_para_fecha:", e)

# 4) imprime rutas en consola al iniciar
try:
    _debug_print_paths_hotfix()
except Exception:
    pass

# ============================================================
# FIN HOTFIX
# ============================================================


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)





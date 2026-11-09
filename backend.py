"""
Backend FastAPI + Supabase
Recibe TXT, procesa y guarda histórico en Supabase
"""
import os
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
import shutil
from datetime import datetime

from procesador import procesar_tag_completo, parse_pi_txt
from supabase import create_client, Client

app = FastAPI(title="Procesador PI - Histórico Supabase")

# Configuración Supabase (usa variables de entorno en Render)
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

supabase: Client = None
if SUPABASE_URL and SUPABASE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def root():
    return FileResponse("static/index.html")


@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """Recibe TXT, procesa, guarda en Supabase y elimina el archivo"""
    if not file.filename.endswith(".txt"):
        raise HTTPException(status_code=400, detail="Solo se aceptan archivos .txt")
    
    dest = UPLOAD_DIR / file.filename
    try:
        # Guardar temporalmente
        with dest.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Procesar
        data = parse_pi_txt(dest)
        resultado = procesar_tag_completo(data)
        
        # Guardar en Supabase (si está configurado)
        if supabase:
            guardar_en_supabase(resultado)
        
        return {
            "status": "ok",
            "archivo": file.filename,
            "tag": resultado.get("tag"),
            "eliminado": True
        }
    except Exception as e:
        # Devolver el error detallado para diagnóstico
        import traceback
        error_detail = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
        raise HTTPException(status_code=500, detail=error_detail)
    finally:
        # Siempre eliminar el archivo TXT después de procesarlo
        if dest.exists():
            dest.unlink()


def guardar_en_supabase(resultado: dict):
    """Guarda el resumen horario en la tabla 'resumenes'"""
    tag = resultado.get("tag", "")
    archivo = resultado.get("archivo", "")
    ahora = datetime.utcnow().isoformat()
    
    for datos in resultado.get("registros", []):
        if not datos:
            continue
        fila = {
            "tag": tag,
            "archivo": archivo,
            "fecha": datos.get("fecha"),
            "hora": datos.get("hora"),
            "fecha_proceso": ahora,
            "n": datos.get("n"),
            "promedio": datos.get("promedio"),
            "maximo": datos.get("maximo"),
            "minimo": datos.get("minimo"),
            "final": datos.get("final"),
            "inicio": datos.get("inicio"),
            "sobre_100_sin": datos.get("sobre_100_sin", 0),
            "sobre_100_con": datos.get("sobre_100_con", 0),
            "sobre_150_sin": datos.get("sobre_150_sin", 0),
            "sobre_150_con": datos.get("sobre_150_con", 0),
            "sobre_180_sin": datos.get("sobre_180_sin", 0),
            "sobre_180_con": datos.get("sobre_180_con", 0),
            "arranques": datos.get("arranques", 0),
            "tiempo_con_carga": datos.get("tiempo_con_carga", 0),
            "tiempo_sin_carga": datos.get("tiempo_sin_carga", 0),
            "tiempo_detenido": datos.get("tiempo_detenido", 0),
        }
        supabase.table("resumenes").insert(fila).execute()


@app.get("/api/resumen")
async def resumen(fecha: str = None):
    """Devuelve resúmenes desde Supabase filtrados por fecha (opcional)"""
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase no configurado")
    
    query = supabase.table("resumenes").select("*")
    if fecha:
        query = query.eq("fecha", fecha)
    response = query.order("fecha_proceso", desc=True).limit(5000).execute()
    
    # Quedarnos solo con el más reciente por tag + fecha + hora
    latest = {}
    for r in response.data:
        key = (r.get("tag", "").upper(), r.get("fecha"), r.get("hora"))
        if key not in latest:
            latest[key] = r
    
    return JSONResponse(content={"resultados": list(latest.values())})



@app.get("/api/fechas")
async def listar_fechas():
    """Devuelve las fechas únicas disponibles en la tabla resumenes"""
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase no configurado")
    
    try:
        response = supabase.table("resumenes") \
            .select("fecha") \
            .not_.is_("fecha", "null") \
            .order("fecha", desc=True) \
            .execute()
        
        fechas = sorted(list(set(
            r["fecha"] for r in response.data if r.get("fecha")
        )), reverse=True)
        return JSONResponse(content={"fechas": fechas})
    except Exception as e:
        return JSONResponse(content={"fechas": [], "error": str(e)}, status_code=500)

@app.get("/health")
async def health():
    return {"status": "ok", "supabase": supabase is not None}

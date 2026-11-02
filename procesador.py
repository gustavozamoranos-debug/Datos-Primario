"""
Procesador de archivos TXT de PI ProcessBook
Replica el resumen horario de la hoja DATOS TA (tabla de parámetros)
"""
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import defaultdict

def parse_pi_txt(file_path: Path) -> Dict[str, Any]:
    text = file_path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    
    tag_name = ""
    data_start = 0
    for i, line in enumerate(lines[:30]):
        if line.startswith("Name"):
            parts = line.split("\t")
            if len(parts) > 1:
                tag_name = parts[1].strip()
        if line.startswith("Time\t"):
            data_start = i + 1
            break
    
    points = []
    for line in lines[data_start:]:
        line = line.strip()
        if not line:
            continue
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        
        time_str = parts[0]
        value_str = parts[1]
        is_bad = "Bad" in value_str or "bad" in value_str.lower()
        value = None
        if not is_bad:
            try:
                value = float(value_str.replace(",", "."))
            except ValueError:
                value = None
        
        m = re.match(r"(\d{2})-(\d{2})-(\d{4})\s+(\d{1,2}):(\d{2}):(\d{2})", time_str)
        dt = None
        if m:
            dt = datetime(int(m[3]), int(m[2]), int(m[1]), int(m[4]), int(m[5]), int(m[6]))
        
        points.append({
            "time": dt,
            "value": value,
            "is_bad": is_bad
        })
    
    return {"tag": tag_name, "points": points, "file": file_path.name}


def clasificar_carga(valores_recientes: List[float], valor_actual: float, umbral_bajo: float = 39) -> str:
    """
    Clasifica si un evento alto es 'con carga' o 'sin carga'.
    Simplificación de la lógica del Excel: 
    Si en las últimas 5 mediciones hubo valores <= 39 y luego hay tendencia creciente,
    se considera 'sin carga' (arranque). Si no, 'con carga'.
    """
    if not valores_recientes:
        return "con carga"
    
    # Buscar si hubo valores bajos recientemente
    bajos = [v for v in valores_recientes[-5:] if v is not None and v <= umbral_bajo]
    if not bajos:
        return "con carga"
    
    # Tendencia creciente simple
    ultimos = [v for v in valores_recientes[-4:] if v is not None]
    if len(ultimos) >= 2 and valor_actual > ultimos[-1]:
        return "sin carga"
    return "con carga"


def procesar_tag_completo(data: Dict[str, Any]) -> Dict[str, Any]:
    tag = data["tag"].upper()
    points = [p for p in data["points"] if p["time"] is not None]
    
    # Agrupar por hora
    by_hour = defaultdict(list)
    for p in points:
        if p["value"] is not None:
            by_hour[p["time"].hour].append(p["value"])
    
    horas = list(range(7, 19))  # 07 a 18
    resultado = {"tag": data["tag"], "archivo": data["file"], "horas": {}}
    
    for h in horas:
        vals = by_hour.get(h, [])
        if not vals:
            resultado["horas"][h] = {}
            continue
        
        # Valores no cero para promedio de corriente
        vals_no_cero = [v for v in vals if v != 0]
        
        hora_data = {
            "n": len(vals),
            "promedio": sum(vals_no_cero) / len(vals_no_cero) if vals_no_cero else 0,
            "maximo": max(vals) if vals else 0,
            "minimo": min(vals) if vals else 0,
            "final": vals[-1] if vals else 0,
            "inicio": vals[0] if vals else 0,
        }
        
        # Solo para Corriente: conteos sobre umbrales con/sin carga
        if "CR001" in tag and "II" in tag:
            conteos = {"sobre_100_sin": 0, "sobre_100_con": 0,
                       "sobre_150_sin": 0, "sobre_150_con": 0,
                       "sobre_180_sin": 0, "sobre_180_con": 0}
            
            # Recorrer puntos de la hora para detectar eventos
            puntos_hora = [p for p in points if p["time"] and p["time"].hour == h and p["value"] is not None]
            recientes = []
            for p in puntos_hora:
                v = p["value"]
                tipo = clasificar_carga(recientes, v)
                if v >= 100:
                    conteos[f"sobre_100_{'sin' if tipo == 'sin carga' else 'con'}"] += 1
                if v >= 150:
                    conteos[f"sobre_150_{'sin' if tipo == 'sin carga' else 'con'}"] += 1
                if v >= 180:
                    conteos[f"sobre_180_{'sin' if tipo == 'sin carga' else 'con'}"] += 1
                recientes.append(v)
                if len(recientes) > 10:
                    recientes.pop(0)
            
            hora_data.update(conteos)
        
        resultado["horas"][h] = hora_data
    
    return resultado


def procesar_carpeta(carpeta: Path) -> List[Dict[str, Any]]:
    resultados = []
    for txt in sorted(carpeta.glob("*.txt")):
        try:
            data = parse_pi_txt(txt)
            resultados.append(procesar_tag_completo(data))
        except Exception as e:
            resultados.append({"archivo": txt.name, "error": str(e)})
    return resultados

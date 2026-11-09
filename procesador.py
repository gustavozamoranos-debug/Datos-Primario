"""
Procesador de archivos TXT de PI ProcessBook
Replica el resumen horario de la hoja DATOS TURNO del Excel Primario.xlsm
Incluye fecha y cálculo de tiempos.
"""
import re
from datetime import datetime, timedelta
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
        is_bad = "Bad" in value_str or "bad" in value_str.lower() or value_str.upper() == "DETENIDO"
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


def clasificar_punto(value: Optional[float], is_bad: bool) -> str:
    if is_bad or value is None or value == 0:
        return "DETENIDO"
    if value <= 39:
        return "VACIO"
    return "CON CARGA"


def procesar_tag_completo(data: Dict[str, Any]) -> Dict[str, Any]:
    points = [p for p in data["points"] if p["time"] is not None]
    if not points:
        return {"tag": data["tag"], "archivo": data["file"], "horas": {}}
    
    points.sort(key=lambda x: x["time"])
    tag = data["tag"].upper()
    is_corriente = "CR001" in tag and ("II" in tag or "-II" in tag)
    
    # Agrupar por fecha + hora
    by_date_hour = defaultdict(list)
    for p in points:
        key = (p["time"].date().isoformat(), p["time"].hour)
        by_date_hour[key].append(p)
    
    resultado = {"tag": data["tag"], "archivo": data["file"], "registros": []}
    
    for (fecha, h), pts in sorted(by_date_hour.items()):
        if not pts:
            continue
        
        vals = [p["value"] for p in pts if p["value"] is not None]
        
        hora_data = {
            "fecha": fecha,
            "hora": h,
            "n": len(vals),
            "promedio": round(sum(vals) / len(vals), 2) if vals else 0,
            "maximo": round(max(vals), 2) if vals else 0,
            "minimo": round(min(vals), 2) if vals else 0,
            "final": round(vals[-1], 2) if vals else 0,
            "inicio": round(vals[0], 2) if vals else 0,
            "arranques": 0,
            "sobre_100_sin": 0,
            "sobre_100_con": 0,
            "sobre_150_sin": 0,
            "sobre_150_con": 0,
            "sobre_180_sin": 0,
            "sobre_180_con": 0,
            "tiempo_con_carga": 0.0,
            "tiempo_sin_carga": 0.0,
            "tiempo_detenido": 0.0,
        }
        
        if is_corriente and len(pts) >= 1:
            vals_carga = [v for v in vals if v is not None and v > 39]
            vals_sin = [v for v in vals if v is not None and v <= 42]
            if vals_carga:
                hora_data["promedio"] = round(sum(vals_carga) / len(vals_carga), 2)
            if vals_sin:
                hora_data["promedio_sin_carga"] = round(sum(vals_sin) / len(vals_sin), 2)
            else:
                hora_data["promedio_sin_carga"] = 0
            
            for v in vals:
                if v is None:
                    continue
                if v >= 100:
                    hora_data["sobre_100_con"] += 1
                if v >= 150:
                    hora_data["sobre_150_con"] += 1
                if v >= 180:
                    hora_data["sobre_180_con"] += 1
            
            tiempo_con = 0.0
            tiempo_sin = 0.0
            tiempo_det = 0.0
            arranques = 0
            prev_class = None
            
            # Límites de la hora
            hora_inicio = pts[0]["time"].replace(minute=0, second=0, microsecond=0)
            hora_fin = hora_inicio + timedelta(hours=1)
            
            # Tiempo desde inicio de hora hasta primera muestra
            if pts[0]["time"] > hora_inicio:
                delta = (pts[0]["time"] - hora_inicio).total_seconds()
                clas = clasificar_punto(pts[0]["value"], pts[0]["is_bad"])
                if clas == "CON CARGA":
                    tiempo_con += delta
                elif clas == "VACIO":
                    tiempo_sin += delta
                else:
                    tiempo_det += delta
            
            # Tiempos entre muestras consecutivas (solo dentro de la hora)
            for i in range(len(pts) - 1):
                p1 = pts[i]
                p2 = pts[i + 1]
                if p1["time"] is None or p2["time"] is None:
                    continue
                if p2["time"] >= hora_fin:
                    break
                delta_sec = (p2["time"] - p1["time"]).total_seconds()
                if delta_sec <= 0:
                    continue
                
                clas = clasificar_punto(p1["value"], p1["is_bad"])
                
                if clas == "CON CARGA":
                    tiempo_con += delta_sec
                elif clas == "VACIO":
                    tiempo_sin += delta_sec
                else:
                    tiempo_det += delta_sec
                
                if prev_class in ("DETENIDO", "VACIO") and clas == "CON CARGA":
                    arranques += 1
                prev_class = clas
            
            # Tiempo desde última muestra hasta fin de hora
            ultima = pts[-1]
            if ultima["time"] < hora_fin:
                delta = (hora_fin - ultima["time"]).total_seconds()
                clas = clasificar_punto(ultima["value"], ultima["is_bad"])
                if clas == "CON CARGA":
                    tiempo_con += delta
                elif clas == "VACIO":
                    tiempo_sin += delta
                else:
                    tiempo_det += delta
            
            # Normalizar a exactamente 3600 segundos
            total = tiempo_con + tiempo_sin + tiempo_det
            if total > 0 and abs(total - 3600) > 1:
                factor = 3600 / total
                tiempo_con *= factor
                tiempo_sin *= factor
                tiempo_det *= factor
            
            hora_data["tiempo_con_carga"] = round(tiempo_con, 1)
            hora_data["tiempo_sin_carga"] = round(tiempo_sin, 1)
            hora_data["tiempo_detenido"] = round(tiempo_det, 1)
            hora_data["arranques"] = arranques
        
        resultado["registros"].append(hora_data)
    
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

# Procesador PI + Histórico en Supabase

## 1. Configurar Supabase

1. Crea una cuenta en [https://supabase.com](https://supabase.com)
2. Crea un nuevo proyecto.
3. Ve a **SQL Editor** y ejecuta el contenido del archivo `supabase_schema.sql`.
4. Ve a **Settings → API** y copia:
   - **Project URL**
   - **anon public key** (o service_role key si prefieres)

## 2. Configurar Render

En tu servicio de Render, ve a **Environment** y agrega estas variables:

| Key | Value |
|-----|-------|
| `SUPABASE_URL` | La Project URL de Supabase |
| `SUPABASE_KEY` | La anon key de Supabase |

## 3. Desplegar

Sube los archivos a GitHub y despliega en Render (usando el Dockerfile).

## 4. Código VBA

Usa la misma URL de upload:

```vba
Private Const URL_SERVIDOR As String = "https://datos-primario.onrender.com/api/upload"
```

Cada vez que el macro suba un TXT, los datos procesados se guardarán automáticamente en Supabase.

## 5. Consultar histórico

La web (`/api/resumen`) ahora lee desde Supabase, por lo que puedes ver el histórico acumulado.

---

**Nota**: El plan gratuito de Supabase tiene 500 MB de base de datos, suficiente para meses de resúmenes horarios.

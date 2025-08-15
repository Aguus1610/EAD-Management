# 🚀 Deploy en Render - Guía Completa

## 📋 Preparación del Proyecto

### 1. Crear archivo `render.yaml`
```yaml
services:
  - type: web
    name: sistema-taller
    env: python
    buildCommand: "pip install -r requirements.txt"
    startCommand: "gunicorn app:app"
    envVars:
      - key: PYTHON_VERSION
        value: 3.8.10
      - key: SECRET_KEY
        generateValue: true
      - key: FLASK_DEBUG
        value: False
```

### 2. Actualizar `requirements.txt`
```
Flask==2.3.3
pandas==2.0.3
openpyxl==3.1.2
gunicorn==21.2.0
```

### 3. Crear `gunicorn.conf.py`
```python
bind = "0.0.0.0:10000"
workers = 2
timeout = 30
keepalive = 2
worker_class = "sync"
```

### 4. Modificar `app.py` para producción
```python
# Al final de app.py
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
```

## 🔗 Pasos en Render.com

1. **Crear cuenta** en [render.com](https://render.com)
2. **Conectar GitHub** repository
3. **New Web Service** → seleccionar tu repo
4. **Configurar**:
   - Environment: Python 3
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app`
5. **Deploy** automático

## 🔒 Variables de Entorno en Render
```
SECRET_KEY = [Auto-generada]
FLASK_DEBUG = False
DATABASE_PATH = /opt/render/project/src/taller.db
```

## ✅ URL Final
`https://sistema-taller.onrender.com`

## 💾 Base de Datos
- SQLite funciona out-of-the-box
- Para datos persistentes: usar PostgreSQL addon (gratis)

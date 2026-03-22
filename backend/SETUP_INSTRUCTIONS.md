# Backend Setup Instructions

## ⚠️ Important: Use a Clean Virtual Environment

The dependency conflicts you're seeing are from **other packages** installed globally (gradio, langchain, tensorflow, etc.) that are **NOT required** for this project.

## 🔧 Clean Setup (Recommended)

### Option 1: Fresh Virtual Environment

```bash
# 1. Delete existing virtual environment
Remove-Item -Recurse -Force venv  # PowerShell
# rm -rf venv  # Linux/Mac

# 2. Create new clean virtual environment
python -m venv venv

# 3. Activate (IMPORTANT!)
.\venv\Scripts\activate  # Windows PowerShell
# source venv/bin/activate  # Linux/Mac

# 4. Upgrade pip
python -m pip install --upgrade pip

# 5. Install ONLY our requirements
pip install -r requirements.txt

# 6. Verify installation
pip list
```

### Option 2: Use requirements-minimal.txt (Fastest)

If Option 1 still has conflicts, use the minimal requirements:

```bash
pip install -r requirements-minimal.txt
```

## ✅ What You Actually Need

This project **ONLY** requires:
- ✅ FastAPI (web framework)
- ✅ NetworkX (graph processing)
- ✅ Google Generative AI (LLM)
- ✅ Pandas (data processing)
- ✅ Uvicorn (ASGI server)
- ✅ Python-dotenv (environment variables)

## ❌ What You DON'T Need

These are causing conflicts but **NOT required**:
- ❌ gradio
- ❌ langchain
- ❌ tensorflow
- ❌ paddlepaddle
- ❌ historical
- ❌ swag-client
- ❌ dataclasses-json

## 🐛 Troubleshooting

### Issue: Dependencies still conflicting

**Solution:**
```bash
# Create completely isolated environment
python -m venv venv_clean --clear

# Activate new environment
.\venv_clean\Scripts\activate

# Install fresh
pip install --no-cache-dir -r requirements.txt
```

### Issue: "ModuleNotFoundError"

**Solution:** Make sure virtual environment is activated
```bash
# You should see (venv) in your terminal prompt
# If not, activate:
.\venv\Scripts\activate
```

### Issue: Old package versions

**Solution:**
```bash
# Upgrade all packages
pip install --upgrade -r requirements.txt
```

## 🚀 Quick Test

After installation, verify everything works:

```bash
# Activate environment
.\venv\Scripts\activate

# Run test
python -c "import fastapi, networkx, google.generativeai; print('✅ All core packages installed')"

# Start server (after setting GEMINI_API_KEY in .env)
python app.py
```

## 📦 System Requirements

- Python 3.9 or higher
- pip 21.0 or higher
- 2GB RAM minimum (4GB+ recommended)
- Windows/Linux/macOS

## 🔑 Environment Setup

```bash
# Copy example env file
copy .env.example .env  # Windows
# cp .env.example .env  # Linux/Mac

# Edit .env and add your Gemini API key
notepad .env  # Windows
# nano .env  # Linux/Mac
```

## ⚡ Production Deployment

For production, pin all dependencies (already done in requirements.txt):

```bash
# Install exact versions
pip install -r requirements.txt

# Verify no conflicts
pip check
```

## 💡 Pro Tips

1. **Always use virtual environments** - Never install to global Python
2. **Activate before work** - Run `.\venv\Scripts\activate` every time
3. **One project = One venv** - Don't share virtual environments
4. **Check activation** - Look for `(venv)` in terminal prompt
5. **Freeze dependencies** - `pip freeze > requirements-lock.txt` for exact reproduction

## 🆘 Still Having Issues?

1. **Python version**: Check with `python --version` (need 3.9+)
2. **Pip version**: Check with `pip --version` (need 21.0+)
3. **Clean slate**: Delete venv, remove pip cache, start fresh
4. **System packages**: On Linux, may need `python3-venv` package

---

**Last Updated:** March 22, 2026  
**Tested On:** Python 3.9, 3.10, 3.11, 3.12

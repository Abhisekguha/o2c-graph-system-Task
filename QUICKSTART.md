# Quick Start Guide

## Prerequisites
- Python 3.9 or higher
- Node.js 16 or higher
- Google Gemini API Key (free at https://ai.google.dev)

## Setup Steps

### 1. Get Gemini API Key
1. Go to https://ai.google.dev
2. Click "Get API Key"
3. Create a new API key
4. Copy the key

### 2. Backend Setup

Open terminal and run:

```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On Mac/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
copy .env.example .env  # Windows
# OR
cp .env.example .env    # Mac/Linux

# Edit .env and add your API key
notepad .env  # Windows
# OR
nano .env     # Mac/Linux

# Add this line:
GEMINI_API_KEY=your_actual_api_key_here

# Start backend server
python app.py
```

Backend will start on http://localhost:8000

### 3. Frontend Setup

Open a NEW terminal window:

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start frontend
npm start
```

Frontend will open automatically at http://localhost:3000

## Verification

1. Backend health check:
   - Open http://localhost:8000/api/health
   - Should see `{"status": "healthy", ...}`

2. Frontend:
   - Open http://localhost:3000
   - Graph should load and display nodes/edges
   - Chat interface should be ready

## Try It Out

**Example Queries:**
1. "How many sales orders are there?"
2. "Trace the flow of billing document 90504248"
3. "Find sales orders without deliveries"
4. "Which products are most popular?"

## Troubleshooting

**Backend not starting?**
- Check Python version: `python --version` (should be 3.9+)
- Check if port 8000 is free
- Verify GEMINI_API_KEY is set in .env

**Frontend not loading?**
- Check Node version: `node --version` (should be 16+)
- Run `npm install` again
- Check browser console (F12) for errors

**Graph not loading?**
- Verify backend is running (check http://localhost:8000/api/health)
- Check dataset files exist in parent directory
- Check browser console for CORS errors

## Next Steps

Once everything works:
1. Try the example queries in the chat
2. Click on nodes to explore properties
3. Use the "Trace" functionality with document IDs
4. Analyze broken flows

Happy exploring! 🚀

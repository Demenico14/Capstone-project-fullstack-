# Backend Setup Instructions

## Issue: PyTorch Library Loading Error on macOS

The error you're experiencing is due to PyTorch not having stable support for Python 3.13 yet, especially on macOS with Apple Silicon (M1/M2/M3).

## Solution: Use Python 3.11 or 3.12

### Step 1: Create a new virtual environment with Python 3.11 or 3.12

```bash
# First, deactivate your current environment
deactivate

# Remove the old virtual environment
rm -rf tobacco

# Create a new virtual environment with Python 3.11 (or 3.12)
# Option A: If you have Python 3.11 installed
python3.11 -m venv tobacco

# Option B: If you have Python 3.12 installed
python3.12 -m venv tobacco

# Activate the new environment
source tobacco/bin/activate
```

### Step 2: Install PyTorch for macOS

For Apple Silicon Macs (M1/M2/M3), install PyTorch with MPS (Metal Performance Shaders) support:

```bash
pip install --upgrade pip
pip install torch torchvision torchaudio
```

### Step 3: Install other requirements

```bash
pip install -r requirements.txt
```

### Step 4: Verify installation

```bash
python -c "import torch; print(f'PyTorch version: {torch.__version__}'); print(f'MPS available: {torch.backends.mps.is_available()}')"
```

### Step 5: Run the backend

```bash
# For the main API server
python api_server.py

# Or for the ML app
python app.py
```

## Alternative: Install Python 3.11 if you don't have it

If you don't have Python 3.11 installed:

```bash
# Using Homebrew
brew install python@3.11

# Then create the virtual environment
/opt/homebrew/bin/python3.11 -m venv tobacco
source tobacco/bin/activate
```

## Troubleshooting

If you still encounter issues:

1. **Clear pip cache:**
   ```bash
   pip cache purge
   ```

2. **Reinstall torch completely:**
   ```bash
   pip uninstall torch torchvision torchaudio
   pip install torch torchvision torchaudio
   ```

3. **Check your Python version:**
   ```bash
   python --version  # Should show 3.11.x or 3.12.x
   ```

## MongoDB Connection

Make sure your MongoDB server at `192.168.4.2:27017` is running and accessible before starting the backend server.

---
description: Build a portable Windows installer for FaceFusion (NVIDIA GPU)
---

This workflow automates the process of setting up a standalone environment for FaceFusion on Windows, specifically optimized for NVIDIA GPUs.

1.  **Prerequisites Check**
    Ensure Python 3.10 or higher is installed and available in the PATH.
    ```powershell
    python --version
    ```

2.  **Create Virtual Environment**
    Create a fresh virtual environment to isolate dependencies.
    ```powershell
    python -m venv venv
    ```

3.  **Activate Virtual Environment**
    Activate the virtual environment for subsequent commands.
    ```powershell
    .\venv\Scripts\activate
    ```

4.  **Install FaceFusion with CUDA Support**
    Use the provided installation script to install dependencies, selecting CUDA for NVIDIA GPU acceleration.
    // turbo
    ```powershell
    python install.py --onnxruntime cuda --skip-conda
    ```

5.  **Create Launcher Script**
    Create a `run.bat` file to easily launch FaceFusion using the virtual environment.
    ```powershell
    Set-Content -Path "run.bat" -Value "@echo off`r`ncall venv\Scripts\activate.bat`r`npython facefusion.py run`r`npause"
    ```

6.  **Verify Installation**
    Launch FaceFusion to verify it starts correctly and detects the GPU.
    ```powershell
    .\run.bat
    ```

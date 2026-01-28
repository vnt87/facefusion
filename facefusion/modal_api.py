import modal

APP_NAME = "facefusion-api"
app = modal.App(APP_NAME)

image = (
    modal.Image.debian_slim(python_version='3.12')
    .apt_install('ffmpeg', 'curl')
    .pip_install(
        'gradio-rangeslider==0.0.8',
        'gradio==5.44.1',
        'numpy==2.2.6',
        'onnx==1.19.1',
        'onnxruntime==1.23.2',
        'opencv-python==4.12.0.88',
        'psutil==7.1.3',
        'tqdm==4.67.1',
        'scipy==1.16.3',
        'fastapi>=0.115.2',
        'uvicorn>=0.34.0',
        'python-multipart>=0.0.18'
    )
    .add_local_dir('.', remote_path='/root/facefusion', ignore=lambda path: any(p in str(path) for p in ['.git', '__pycache__', 'venv', '.gradio', 'output']))
)

@app.function(
    image=image,
    allow_concurrent_inputs=100,
    timeout=3600
)
@modal.asgi_app()
def fastapi_app():
    import sys
    # FORCE /root/facefusion to the absolute front of sys.path
    if '/root/facefusion' not in sys.path:
        sys.path.insert(0, '/root/facefusion')

    # Force absolute imports to ensure we use the local code
    from facefusion.api.core import create_app
    
    # Initialize the app
    web_app = create_app()
    return web_app

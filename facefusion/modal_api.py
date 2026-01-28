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
    timeout=3600,
    network_file_systems={"/data": modal.NetworkFileSystem.from_name("facefusion-storage", create_if_missing=True)}
)
@modal.asgi_app()
def fastapi_app():
    import sys
    import os
    # FORCE /root/facefusion to the absolute front of sys.path
    if '/root/facefusion' not in sys.path:
        sys.path.insert(0, '/root/facefusion')

    # Force absolute imports
    from facefusion import state_manager
    from facefusion.api.core import create_app
    
    # Remote storage setup
    remote_storage_path = '/data'
    remote_jobs_path = f'{remote_storage_path}/jobs'
    remote_temp_path = f'{remote_storage_path}/temp'
    os.makedirs(remote_jobs_path, exist_ok=True)
    os.makedirs(remote_temp_path, exist_ok=True)
    
    # Inject paths into state manager
    state_manager.set_item('jobs_path', remote_jobs_path)
    state_manager.set_item('temp_path', remote_temp_path)
    
    # Initialize the app
    web_app = create_app()
    return web_app

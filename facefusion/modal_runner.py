import os
import shutil
import time
from typing import Any, Dict, List

import modal

from facefusion import state_manager, logger
from facefusion.filesystem import get_file_name
from facefusion.types import Args

APP_NAME = "facefusion"
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
    gpu='any',
    timeout=3600,
    network_file_systems={"/data": modal.NetworkFileSystem.from_name("facefusion-storage", create_if_missing=True)}
)
def run_remote(args: Args, file_uploads: Dict[str, bytes] = None) -> bytes:
    import os
    import sys
    # FORCE /root/facefusion to the absolute front of sys.path
    if '/root/facefusion' not in sys.path:
        sys.path.insert(0, '/root/facefusion')
    
    # Remote storage setup
    remote_storage_path = '/data'
    remote_jobs_path = f'{remote_storage_path}/jobs'
    remote_temp_path = f'{remote_storage_path}/temp'
    os.makedirs(remote_jobs_path, exist_ok=True)
    os.makedirs(remote_temp_path, exist_ok=True)

    # Handle file uploads if any
    if file_uploads:
        upload_dir = f'{remote_temp_path}/uploads'
        os.makedirs(upload_dir, exist_ok=True)
        
        if 'source_paths' in args and args['source_paths']:
            new_source_paths = []
            for i, _ in enumerate(args['source_paths']):
                key = f'source_{i}'
                if key in file_uploads:
                    # Determine extension from original path
                    ext = os.path.splitext(args['source_paths'][i])[1]
                    dest = f"{upload_dir}/{key}{ext}"
                    with open(dest, 'wb') as f:
                        f.write(file_uploads[key])
                    new_source_paths.append(dest)
            if new_source_paths:
                args['source_paths'] = new_source_paths
                
        if 'target_path' in args and args['target_path']:
             key = 'target'
             if key in file_uploads:
                 ext = os.path.splitext(args['target_path'])[1]
                 dest = f"{upload_dir}/{key}{ext}"
                 with open(dest, 'wb') as f:
                     f.write(file_uploads[key])
                 args['target_path'] = dest

    # Force absolute imports
    import facefusion.state_manager as sm
    import facefusion.core as core
    from facefusion.jobs import job_manager, job_runner
    
    # Handle output path - redirect to remote temp
    if 'output_path' in args:
        ext = os.path.splitext(args['output_path'])[1] or '.png'
        remote_output_path = f"{remote_temp_path}/output_{int(time.time())}{ext}"
        args['output_path'] = remote_output_path

    # GOD MODE STATE PATCH
    remote_state = dict(args)
    remote_state['modal'] = False
    
    def patched_get_item(key):
        return remote_state.get(key)
        
    def patched_set_item(key, value):
        if value is not None:
            remote_state[key] = value

    # Patch modules
    sm.get_item = patched_get_item
    sm.set_item = patched_set_item
    core.state_manager = sm
    
    # Force context
    import facefusion.app_context as app_context
    app_context.detect_app_context = lambda: 'cli'
    
    # Path injection
    remote_state.update({
        'jobs_path': remote_jobs_path,
        'temp_path': remote_temp_path
    })
    job_manager.init_jobs(remote_jobs_path)
    job_manager.JOBS_PATH = remote_jobs_path
    
    # Ensure models are downloaded
    if not core.common_pre_check() or not core.processors_pre_check():
        print("[MODAL_DEBUG] Pre-check failed")
        return None

    # Run processing
    job_id = f'modal_job_{int(time.time())}'
    if job_manager.create_job(job_id):
        from facefusion.core import process_step
        from facefusion.args import reduce_step_args
        step_args = reduce_step_args(args)
        
        if job_manager.add_step(job_id, step_args) and job_manager.submit_job(job_id):
            if job_runner.run_job(job_id, process_step):
                output_path = remote_state.get('output_path')
                if output_path and os.path.exists(output_path):
                    with open(output_path, 'rb') as f:
                        return f.read()
    
    return None


import threading

RUN_LOCK = threading.Lock()

def run(args: Args) -> bool:
    logger.info('Running on Modal...', __name__)
    
    # Prepare file uploads
    file_uploads = {}
    source_paths = args.get('source_paths', [])
    if source_paths:
        for i, path in enumerate(source_paths):
            if os.path.exists(path):
                with open(path, 'rb') as f:
                    file_uploads[f'source_{i}'] = f.read()
    
    target_path = args.get('target_path')
    if target_path and os.path.exists(target_path):
        with open(target_path, 'rb') as f:
            file_uploads['target'] = f.read()

    with RUN_LOCK:
        try:
            with app.run():
                output_content = run_remote.remote(args, file_uploads)
                
                if output_content:
                    output_path = args.get('output_path')
                    if output_path:
                        os.makedirs(os.path.dirname(output_path), exist_ok=True)
                        with open(output_path, 'wb') as f:
                            f.write(output_content)
                        logger.info(f'Output saved to {output_path}', __name__)
                        return True
                    else:
                        logger.error('No output path provided', __name__)
                        return False
                else:
                    logger.error('Modal execution failed or returned no output', __name__)
                    return False
        except Exception as e:
            logger.error(f'Modal execution error: {str(e)}', __name__)
            return False

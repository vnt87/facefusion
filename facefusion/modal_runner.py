import os
import shutil
from typing import Any, Dict, List

import modal

from facefusion import state_manager, logger
from facefusion.filesystem import get_file_name
from facefusion.types import Args

APP_NAME = 'facefusion'
app = modal.App(APP_NAME)

image = (
    modal.Image.debian_slim()
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
)


@app.function(
    image=image,
    gpu='any',
    timeout=3600,
    mounts=[modal.Mount.from_local_dir('.', remote_path='/root/facefusion', condition=lambda path: not any(p in path for p in ['.git', '__pycache__', 'venv', '.gradio', 'output']))]
)
def run_remote(args: Args) -> bytes:
    import sys
    sys.path.append('/root/facefusion')
    from facefusion import core, state_manager, job_manager, job_runner
    from facefusion.download import conditional_download

    # Initialize state
    for key, value in args.items():
        state_manager.set_item(key, value)

    # Ensure models are downloaded (this might need improvement to cache models in a Volume)
    conditional_download(state_manager.get_item('download_providers'), state_manager.get_item('download_scope'))

    # Run the job
    # We'll use the headless run logic but adapted
    # Since we are inside the container, we can just call the processing logic
    # But we need to make sure the input files are found.
    # The mount puts them in /root/facefusion.
    # Args should have relative paths which should work if we are in /root/facefusion
    
    os.chdir('/root/facefusion')
    
    # We need to simulate the job runner
    # Create a temporary job
    job_id = 'modal_job'
    if job_manager.create_job(job_id):
        # Add step
        # We need to reconstruct step args from state/args
        # This is a bit hacky, ideally we reuse core logic more cleanly
        # But for now, let's try to invoke the processor directly or use job_manager
        
        # Let's try to use process_headless logic from core.py
        # But we need to capture the output file
        
        # Re-import to ensure we have the functions
        from facefusion.core import process_step
        
        # We need to construct step_args. 
        # In core.process_headless, it calls reduce_step_args(args)
        from facefusion.args import reduce_step_args
        step_args = reduce_step_args(args)
        
        if job_manager.add_step(job_id, step_args) and job_manager.submit_job(job_id):
            if job_runner.run_job(job_id, process_step):
                # Success
                output_path = args.get('output_path')
                if os.path.exists(output_path):
                    with open(output_path, 'rb') as f:
                        return f.read()
    
    return None


def run(args: Args) -> bool:
    # We need to make sure the input files in args are available to the mount
    # The mount is defined globally as the current directory.
    # So as long as source/target are relative paths in the current dir, it should work.
    # If they are absolute, we might have issues.
    
    logger.info('Running on Modal...', __name__)
    
    with app.run():
        output_content = run_remote.remote(args)
        
        if output_content:
            output_path = args.get('output_path')
            with open(output_path, 'wb') as f:
                f.write(output_content)
            logger.info(f'Output saved to {output_path}', __name__)
            return True
        else:
            logger.error('Modal execution failed or returned no output', __name__)
            return False

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
    timeout=3600
)
def run_remote(args: Args) -> bytes:
    import os
    import sys
    # FORCE /root/facefusion to the absolute front of sys.path
    if '/root/facefusion' not in sys.path:
        sys.path.insert(0, '/root/facefusion')
    
    # Force absolute imports from our mounted directory
    import facefusion.state_manager as sm
    # Force absolute imports from our mounted directory
    # Force absolute imports from our mounted directory
    import facefusion.state_manager as sm
    import facefusion.core as core
    import facefusion.app_context as app_context
    from facefusion.jobs import job_manager, job_runner
    
    # GOD MODE STATE PATCH
    # Unify everything into one dictionary and override get_item/set_item
    remote_state = dict(args)
    # Ensure modal flag is FALSE in remote to avoid recursion
    remote_state['modal'] = False
    
    def patched_get_item(key):
        return remote_state.get(key)
        
    def patched_set_item(key, value):
        if value is not None:
            remote_state[key] = value
        else:
            # Protect critical keys from being wiped by apply_args(step_args)
            if key not in ['execution_queue_count', 'download_scope', 'voice_extractor_model']: # keys that are safely None
                 # Log only if needed, or silently ignore
                 pass

    # Patch EVERY module that might be state_manager
    import sys
    import facefusion.core as core
    
    # ID CHECK
    print(f"[MODAL_DEBUG] ID of local sm: {id(sm)}")
    if hasattr(core, 'state_manager'):
        print(f"[MODAL_DEBUG] ID of core.state_manager: {id(core.state_manager)}")
        print(f"[MODAL_DEBUG] core.state_manager file: {getattr(core.state_manager, '__file__', 'unknown')}")
        
        # Force patch
        core.state_manager.get_item = patched_get_item
        core.state_manager.set_item = patched_set_item
        if hasattr(core.state_manager, 'STATE_SET'):
             print(f"[MODAL_DEBUG] Injecting into core.state_manager.STATE_SET (Size: {len(core.state_manager.STATE_SET['cli'])})")
             core.state_manager.STATE_SET['cli'].update(remote_state)
             core.state_manager.STATE_SET['ui'].update(remote_state)
    else:
        print("[MODAL_DEBUG] core.state_manager NOT FOUND")

    for name, module in list(sys.modules.items()):
        if 'state_manager' in name:
            print(f"[MODAL_DEBUG] Patching {name} (ID: {id(module)})")
            module.get_item = patched_get_item
            module.set_item = patched_set_item
            if hasattr(module, 'STATE_SET'):
                module.STATE_SET['cli'].update(remote_state)
                module.STATE_SET['ui'].update(remote_state)
            print(f"[MODAL_DEBUG] Patching {name} ({getattr(module, '__file__', 'no file')})")
            module.get_item = patched_get_item
            module.set_item = patched_set_item
            if hasattr(module, 'STATE_SET'):
                module.STATE_SET['cli'].update(remote_state)
                module.STATE_SET['ui'].update(remote_state)
    
    # PATCH APP CONTEXT
    import facefusion.app_context as app_context
    app_context.detect_app_context = lambda: 'cli'
    
    # Verify injection
    print(f"[MODAL_DEBUG] Patched get_item('processors'): {patched_get_item('processors')}")

    # Force remote-friendly paths
    remote_jobs_path = '/tmp/facefusion/jobs'
    remote_temp_path = '/tmp/facefusion/temp'
    
    print(f"[MODAL_DEBUG] Setting remote jobs_path to: {remote_jobs_path}")
    
    # Inject into state
    state_manager.STATE_SET['cli'].update({
        'jobs_path': remote_jobs_path,
        'temp_path': remote_temp_path
    })
    state_manager.STATE_SET['ui'].update({
        'jobs_path': remote_jobs_path,
        'temp_path': remote_temp_path
    })

    # Initialize Job Manager with remote path
    job_manager.init_jobs(remote_jobs_path)
    job_manager.JOBS_PATH = remote_jobs_path # Force it again
    print(f"[MODAL_DEBUG] job_manager.JOBS_PATH is now: {job_manager.JOBS_PATH}")
    
    # Ensure models are downloaded
    if not core.common_pre_check() or not core.processors_pre_check():
        print("[MODAL_DEBUG] Pre-check failed")
        return False

    # Run processing
    job_id = 'modal_job'
    if job_manager.create_job(job_id):
        from facefusion.core import process_step
        from facefusion.args import reduce_step_args
        step_args = reduce_step_args(args)
        
        if job_manager.add_step(job_id, step_args) and job_manager.submit_job(job_id):
            if job_runner.run_job(job_id, process_step):
                output_path = args.get('output_path')
                if os.path.exists(output_path):
                    with open(output_path, 'rb') as f:
                        return f.read()
    
    return None


import threading

RUN_LOCK = threading.Lock()

def run(args: Args) -> bool:
    logger.info('Running on Modal...', __name__)
    
    with RUN_LOCK:
        try:
            with app.run():
                output_content = run_remote.remote(args)
                
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

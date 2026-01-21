import onnxruntime
import sys

print(f"Python version: {sys.version}")
try:
    print(f"ONNX Runtime version: {onnxruntime.__version__}")
except AttributeError:
    print("ONNX Runtime version: Not found (AttributeError)")

print(f"ONNX Runtime module: {onnxruntime}")
try:
    print(f"ONNX Runtime path: {onnxruntime.__path__}")
except AttributeError:
    print("ONNX Runtime path: Not found")
print(f"Dir(onnxruntime): {dir(onnxruntime)}")

try:
    providers = onnxruntime.get_available_providers()
    print(f"Available Providers: {providers}")

    if 'CUDAExecutionProvider' not in providers:
        print("ERROR: CUDAExecutionProvider not found in available providers!")
    else:
        print("SUCCESS: CUDAExecutionProvider is available.")
        
except Exception as e:
    print(f"CRASHED: {e}")

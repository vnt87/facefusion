from facefusion.execution import get_available_execution_providers
import onnxruntime

print("ONNX Runtime Providers:", onnxruntime.get_available_providers())
print("FaceFusion Execution Providers:", get_available_execution_providers())

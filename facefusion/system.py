import os
import platform
from datetime import datetime
from functools import lru_cache
from typing import Optional

import psutil

from facefusion.types import CpuInfo, DiskInfo, LoadAverage, NetworkInfo, OperatingSystemInfo, PythonInfo, RamInfo, SystemInfo, TemperatureInfo


@lru_cache()
def detect_static_system_info() -> SystemInfo:
	return detect_system_info()


def detect_system_info(temp_path : Optional[str] = None) -> SystemInfo:
	return\
	{
		'operating_system': get_operating_system_info(),
		'python': get_python_info(),
		'cpu': get_cpu_info(),
		'ram': get_ram_info(),
		'disk': get_disk_info(temp_path),
		'temperatures': get_temperature_info(),
		'network': get_network_info(),
		'load_average': get_load_average()
	}


def get_operating_system_info() -> OperatingSystemInfo:
	boot_timestamp = psutil.boot_time()
	boot_time = datetime.fromtimestamp(boot_timestamp)
	uptime_seconds = int((datetime.now() - boot_time).total_seconds())

	return\
	{
		'name': platform.system(),
		'architecture': platform.machine(),
		'platform': platform.platform(),
		'boot_time': boot_time.isoformat(),
		'uptime_seconds': uptime_seconds
	}


def get_python_info() -> PythonInfo:
	return\
	{
		'version': platform.python_version(),
		'implementation': platform.python_implementation()
	}


def get_cpu_info() -> CpuInfo:
	cpu_freq = psutil.cpu_freq()
	cpu_percent = psutil.cpu_percent(interval = 0)

	cpu_info : CpuInfo =\
	{
		'model': get_cpu_model(),
		'physical_cores': psutil.cpu_count(logical = False),
		'logical_cores': psutil.cpu_count(logical = True),
		'usage_percent': cpu_percent
	}

	if cpu_freq:
		cpu_info['frequency'] =\
		{
			'current': cpu_freq.current,
			'min': cpu_freq.min,
			'max': cpu_freq.max
		}

	return cpu_info


def get_cpu_model() -> Optional[str]:
	if platform.system() == 'Linux':
		try:
			with open('/proc/cpuinfo', 'r') as f:
				for line in f:
					if line.startswith('model name'):
						return line.split(':', 1)[1].strip()
		except Exception:
			pass
	if platform.system() == 'Darwin':
		try:
			import subprocess
			result = subprocess.run(['sysctl', '-n', 'machdep.cpu.brand_string'], capture_output = True, text = True)
			if result.returncode == 0:
				return result.stdout.strip()
		except Exception:
			pass
	if platform.system() == 'Windows':
		try:
			import subprocess
			result = subprocess.run(['wmic', 'cpu', 'get', 'name'], capture_output = True, text = True)
			if result.returncode == 0:
				lines = result.stdout.strip().split('\n')
				if len(lines) > 1:
					return lines[1].strip()
		except Exception:
			pass
	return None


def get_ram_info() -> RamInfo:
	virtual_memory = psutil.virtual_memory()
	swap_memory = psutil.swap_memory()

	return\
	{
		'total': virtual_memory.total,
		'available': virtual_memory.available,
		'used': virtual_memory.used,
		'free': virtual_memory.free,
		'percent': virtual_memory.percent,
		'swap_total': swap_memory.total,
		'swap_used': swap_memory.used,
		'swap_free': swap_memory.free,
		'swap_percent': swap_memory.percent
	}


def get_disk_info(temp_path : Optional[str] = None) -> Optional[DiskInfo]:
	if temp_path is None:
		temp_path = os.getcwd()

	target_mountpoint = None
	target_mountpoint_len = 0

	for partition in psutil.disk_partitions():
		if temp_path.startswith(partition.mountpoint):
			if len(partition.mountpoint) > target_mountpoint_len:
				target_mountpoint = partition.mountpoint
				target_mountpoint_len = len(partition.mountpoint)

	if target_mountpoint:
		try:
			usage = psutil.disk_usage(target_mountpoint)
			return\
			{
				'filesystem': next((p.fstype for p in psutil.disk_partitions() if p.mountpoint == target_mountpoint), 'unknown'),
				'total': usage.total,
				'used': usage.used,
				'free': usage.free,
				'percent': usage.percent
			}
		except PermissionError:
			pass

	return None


def get_temperature_info() -> Optional[TemperatureInfo]:
	if not hasattr(psutil, 'sensors_temperatures'):
		return None

	try:
		temps = psutil.sensors_temperatures()
		if not temps:
			return None

		temp_info : TemperatureInfo = {}

		for name, entries in temps.items():
			for entry in entries:
				sensor_key = f'{name}_{entry.label}' if entry.label else name
				temp_info[sensor_key] =\
				{
					'current': entry.current,
					'high': entry.high,
					'critical': entry.critical
				}

		return temp_info
	except Exception:
		return None


def get_network_info() -> NetworkInfo:
	net_io = psutil.net_io_counters()

	return\
	{
		'bytes_sent': net_io.bytes_sent,
		'bytes_recv': net_io.bytes_recv,
		'packets_sent': net_io.packets_sent,
		'packets_recv': net_io.packets_recv,
		'errin': net_io.errin,
		'errout': net_io.errout,
		'dropin': net_io.dropin,
		'dropout': net_io.dropout,
		'interfaces': {}
	}


def get_load_average() -> Optional[LoadAverage]:
	if hasattr(os, 'getloadavg'):
		load1, load5, load15 = os.getloadavg()
		return\
		{
			'load1': load1,
			'load5': load5,
			'load15': load15
		}
	return None

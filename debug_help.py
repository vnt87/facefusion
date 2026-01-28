from facefusion import program, state_manager, config

state_manager.init_item('config_path', 'facefusion.ini')
import sys
sys.argv = ['facefusion.py', 'run', '--help']
p = program.create_program()
p.parse_args()

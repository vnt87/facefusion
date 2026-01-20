import gradio

from facefusion import state_manager
from facefusion.uis.components import face_selector, instant_runner, output, preview, preview_options, source, target, terminal, trim_frame


def pre_check() -> bool:
	# Apply default settings for simple mode
	state_manager.set_item('processors', ['face_swapper', 'face_enhancer'])
	state_manager.set_item('output_video_encoder', 'hevc_nvenc')
	return True


def render() -> gradio.Blocks:
	with gradio.Blocks() as layout:
		with gradio.Row():
			with gradio.Column(scale = 1):
				with gradio.Blocks():
					source.render()
				with gradio.Blocks():
					target.render()
				with gradio.Blocks():
					instant_runner.render()
				with gradio.Blocks():
					terminal.render()
			with gradio.Column(scale = 1):
				with gradio.Blocks():
					preview.render()
					preview_options.render()
				with gradio.Blocks():
					trim_frame.render()
				with gradio.Blocks():
					face_selector.render(simple = True)
				with gradio.Blocks():
					output.render()
	return layout


def listen() -> None:
	source.listen()
	target.listen()
	output.listen()
	instant_runner.listen()
	terminal.listen()
	preview.listen()
	preview_options.listen()
	trim_frame.listen()
	face_selector.listen()


def run(ui : gradio.Blocks) -> None:
	# Launch is handled by core.py when multiple layouts are loaded
	pass

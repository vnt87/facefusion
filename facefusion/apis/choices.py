from typing import Any, Dict

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.status import HTTP_200_OK

import facefusion.choices
from facefusion.execution import get_available_execution_providers
from facefusion.ffmpeg import get_available_encoder_set
from facefusion.processors.modules.face_debugger import choices as face_debugger_choices
from facefusion.processors.modules.face_enhancer import choices as face_enhancer_choices
from facefusion.processors.modules.face_swapper import choices as face_swapper_choices
from facefusion.processors.modules.frame_enhancer import choices as frame_enhancer_choices


async def get_choices(request : Request) -> JSONResponse:
	available_execution_providers = get_available_execution_providers()
	available_encoder_set = get_available_encoder_set()

	choices_data : Dict[str, Any] =\
	{
		'face_detector_models': facefusion.choices.face_detector_models,
		'face_detector_set': facefusion.choices.face_detector_set,
		'face_landmarker_models': facefusion.choices.face_landmarker_models,
		'face_selector_modes': facefusion.choices.face_selector_modes,
		'face_selector_orders': facefusion.choices.face_selector_orders,
		'face_selector_genders': facefusion.choices.face_selector_genders,
		'face_selector_races': facefusion.choices.face_selector_races,
		'face_occluder_models': facefusion.choices.face_occluder_models,
		'face_parser_models': facefusion.choices.face_parser_models,
		'face_mask_types': facefusion.choices.face_mask_types,
		'face_mask_areas': facefusion.choices.face_mask_areas,
		'face_mask_regions': facefusion.choices.face_mask_regions,
		'voice_extractor_models': facefusion.choices.voice_extractor_models,
		'workflows': facefusion.choices.workflows,
		'audio_formats': facefusion.choices.audio_formats,
		'image_formats': facefusion.choices.image_formats,
		'video_formats': facefusion.choices.video_formats,
		'temp_frame_formats': facefusion.choices.temp_frame_formats,
		'output_audio_encoders': available_encoder_set.get('audio'),
		'output_video_encoders': available_encoder_set.get('video'),
		'output_video_presets': facefusion.choices.output_video_presets,
		'execution_providers': available_execution_providers,
		'video_memory_strategies': facefusion.choices.video_memory_strategies,
		'log_levels': facefusion.choices.log_levels,
		'face_swapper_models': face_swapper_choices.face_swapper_models,
		'face_swapper_set': face_swapper_choices.face_swapper_set,
		'face_enhancer_models': face_enhancer_choices.face_enhancer_models,
		'frame_enhancer_models': frame_enhancer_choices.frame_enhancer_models,
		'face_debugger_items': face_debugger_choices.face_debugger_items,
		'face_detector_angles': list(facefusion.choices.face_detector_angles),
		'face_detector_score_range':
		{
			'min': min(facefusion.choices.face_detector_score_range),
			'max': max(facefusion.choices.face_detector_score_range),
			'step': facefusion.choices.face_detector_score_range[1] - facefusion.choices.face_detector_score_range[0]
		},
		'face_landmarker_score_range':
		{
			'min': min(facefusion.choices.face_landmarker_score_range),
			'max': max(facefusion.choices.face_landmarker_score_range),
			'step': facefusion.choices.face_landmarker_score_range[1] - facefusion.choices.face_landmarker_score_range[0]
		},
		'face_mask_blur_range':
		{
			'min': min(facefusion.choices.face_mask_blur_range),
			'max': max(facefusion.choices.face_mask_blur_range),
			'step': facefusion.choices.face_mask_blur_range[1] - facefusion.choices.face_mask_blur_range[0]
		},
		'face_mask_padding_range':
		{
			'min': min(facefusion.choices.face_mask_padding_range),
			'max': max(facefusion.choices.face_mask_padding_range),
			'step': 1
		},
		'face_selector_age_range':
		{
			'min': min(facefusion.choices.face_selector_age_range),
			'max': max(facefusion.choices.face_selector_age_range),
			'step': 1
		},
		'reference_face_distance_range':
		{
			'min': min(facefusion.choices.reference_face_distance_range),
			'max': max(facefusion.choices.reference_face_distance_range),
			'step': facefusion.choices.reference_face_distance_range[1] - facefusion.choices.reference_face_distance_range[0]
		},
		'output_image_quality_range':
		{
			'min': min(facefusion.choices.output_image_quality_range),
			'max': max(facefusion.choices.output_image_quality_range),
			'step': 1
		},
		'output_image_scale_range':
		{
			'min': min(facefusion.choices.output_image_scale_range),
			'max': max(facefusion.choices.output_image_scale_range),
			'step': facefusion.choices.output_image_scale_range[1] - facefusion.choices.output_image_scale_range[0]
		},
		'output_audio_quality_range':
		{
			'min': min(facefusion.choices.output_audio_quality_range),
			'max': max(facefusion.choices.output_audio_quality_range),
			'step': 1
		},
		'output_audio_volume_range':
		{
			'min': min(facefusion.choices.output_audio_volume_range),
			'max': max(facefusion.choices.output_audio_volume_range),
			'step': 1
		},
		'output_video_quality_range':
		{
			'min': min(facefusion.choices.output_video_quality_range),
			'max': max(facefusion.choices.output_video_quality_range),
			'step': 1
		},
		'output_video_scale_range':
		{
			'min': min(facefusion.choices.output_video_scale_range),
			'max': max(facefusion.choices.output_video_scale_range),
			'step': facefusion.choices.output_video_scale_range[1] - facefusion.choices.output_video_scale_range[0]
		},
		'execution_thread_count_range':
		{
			'min': min(facefusion.choices.execution_thread_count_range),
			'max': max(facefusion.choices.execution_thread_count_range),
			'step': 1
		},
		'face_detector_margin_range':
		{
			'min': min(facefusion.choices.face_detector_margin_range),
			'max': max(facefusion.choices.face_detector_margin_range),
			'step': 1
		},
		'face_swapper_weight_range':
		{
			'min': min(face_swapper_choices.face_swapper_weight_range),
			'max': max(face_swapper_choices.face_swapper_weight_range),
			'step': face_swapper_choices.face_swapper_weight_range[1] - face_swapper_choices.face_swapper_weight_range[0]
		},
		'face_enhancer_blend_range':
		{
			'min': min(face_enhancer_choices.face_enhancer_blend_range),
			'max': max(face_enhancer_choices.face_enhancer_blend_range),
			'step': 1
		},
		'face_enhancer_weight_range':
		{
			'min': min(face_enhancer_choices.face_enhancer_weight_range),
			'max': max(face_enhancer_choices.face_enhancer_weight_range),
			'step': face_enhancer_choices.face_enhancer_weight_range[1] - face_enhancer_choices.face_enhancer_weight_range[0]
		},
		'frame_enhancer_blend_range':
		{
			'min': min(frame_enhancer_choices.frame_enhancer_blend_range),
			'max': max(frame_enhancer_choices.frame_enhancer_blend_range),
			'step': 1
		}
	}

	return JSONResponse(choices_data, status_code = HTTP_200_OK)

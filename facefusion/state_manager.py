from typing import Any, Union

from facefusion.app_context import detect_app_context
from facefusion.processors.types import ProcessorState, ProcessorStateKey, ProcessorStateSet
from facefusion.types import State, StateKey, StateSet

STATE_SET : Union[StateSet, ProcessorStateSet] =\
{
	'cli': {}, #type:ignore[assignment]
	'ui': {} #type:ignore[assignment]
}


def get_state() -> Union[State, ProcessorState]:
	app_context = detect_app_context()
	return STATE_SET.get(app_context)


def sync_state() -> None:
	STATE_SET['cli'] = STATE_SET.get('ui') #type:ignore[assignment]


def init_item(key : Union[StateKey, ProcessorStateKey], value : Any) -> None:
	STATE_SET['cli'][key] = value #type:ignore[literal-required]
	STATE_SET['ui'][key] = value #type:ignore[literal-required]


def get_item(key : Union[StateKey, ProcessorStateKey]) -> Any:
	value = get_state().get(key) #type:ignore[literal-required]
	if key == 'processors' and value is None:
		from facefusion.app_context import detect_app_context
		import os
		if os.environ.get('MODAL_PROJECT_NAME'):
			print(f"[MODAL_DEBUG] get_item('processors') is None! Context: {detect_app_context()}")
			print(f"[MODAL_DEBUG] STATE_SET['cli'] keys: {list(STATE_SET['cli'].keys())}")
	return value


def set_item(key : Union[StateKey, ProcessorStateKey], value : Any) -> None:
	app_context = detect_app_context()
	STATE_SET[app_context][key] = value #type:ignore[literal-required]


def sync_item(key : Union[StateKey, ProcessorStateKey]) -> None:
	STATE_SET['cli'][key] = STATE_SET.get('ui').get(key) #type:ignore[literal-required]


def clear_item(key : Union[StateKey, ProcessorStateKey]) -> None:
	set_item(key, None)

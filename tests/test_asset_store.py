import os
import tempfile
from typing import Iterator

import pytest

from facefusion import asset_store, session_manager, state_manager
from facefusion.session_context import clear_session_id, set_session_id


@pytest.fixture(scope = 'function', autouse = True)
def before_each() -> None:
	session_manager.SESSIONS.clear()
	state_manager.clear_item('asset_registry')
	clear_session_id()


@pytest.fixture(scope = 'function')
def temp_file() -> Iterator[str]:
	fd, path = tempfile.mkstemp(suffix = '.jpg')
	os.write(fd, b'test file content')
	os.close(fd)
	yield path
	if os.path.exists(path):
		os.remove(path)


@pytest.fixture(scope = 'function')
def session_id() -> str:
	test_session_id = 'test-session-123'
	set_session_id(test_session_id)
	return test_session_id


def test_register_source_asset(temp_file : str, session_id : str) -> None:
	asset_id = asset_store.register('source', temp_file, 'test.jpg')

	assert isinstance(asset_id, str)
	assert len(asset_id) == 36

	asset = asset_store.get_asset(asset_id)
	assert asset is not None
	assert asset.get('id') == asset_id
	assert asset.get('session_id') == session_id
	assert asset.get('type') == 'source'
	assert asset.get('path') == temp_file
	assert asset.get('filename') == 'test.jpg'
	assert asset.get('size') > 0
	assert asset.get('created_at')


def test_register_target_asset(temp_file : str, session_id : str) -> None:
	asset_id = asset_store.register('target', temp_file, 'video.mp4')

	asset = asset_store.get_asset(asset_id)
	assert asset.get('type') == 'target'
	assert asset.get('filename') == 'video.mp4'


def test_register_output_asset(temp_file : str, session_id : str) -> None:
	metadata = {'fps': 30, 'resolution': [1920, 1080]}
	asset_id = asset_store.register('output', temp_file, 'output.mp4', metadata)

	asset = asset_store.get_asset(asset_id)
	assert asset.get('type') == 'output'
	assert asset.get('metadata') == metadata


def test_register_invalid_type(temp_file : str, session_id : str) -> None:
	with pytest.raises(ValueError) as exc:
		asset_store.register('invalid_type', temp_file, 'test.jpg')
	assert "Invalid asset_type" in str(exc.value)


def test_register_without_session() -> None:
	fd, path = tempfile.mkstemp()
	os.close(fd)

	try:
		with pytest.raises(ValueError) as exc:
			asset_store.register('source', path, 'test.jpg')
		assert "No active session" in str(exc.value)
	finally:
		os.remove(path)


def test_register_without_filename(temp_file : str, session_id : str) -> None:
	asset_id = asset_store.register('source', temp_file)

	asset = asset_store.get_asset(asset_id)
	assert asset.get('filename') == os.path.basename(temp_file)


def test_get_asset_not_found(session_id : str) -> None:
	asset = asset_store.get_asset('non-existent-id')
	assert asset is None


def test_list_assets_empty(session_id : str) -> None:
	assets = asset_store.list_assets()
	assert assets == []


def test_list_assets_with_multiple(temp_file : str, session_id : str) -> None:
	fd1, path1 = tempfile.mkstemp(suffix = '.jpg')
	os.write(fd1, b'content 1')
	os.close(fd1)

	fd2, path2 = tempfile.mkstemp(suffix = '.mp4')
	os.write(fd2, b'content 2')
	os.close(fd2)

	try:
		asset_store.register('source', path1, 'source1.jpg')
		asset_store.register('source', path2, 'source2.jpg')
		asset_store.register('target', temp_file, 'target.mp4')

		assets = asset_store.list_assets()
		assert len(assets) == 3
	finally:
		os.remove(path1)
		os.remove(path2)


def test_list_assets_filter_by_type(temp_file : str, session_id : str) -> None:
	fd, path = tempfile.mkstemp(suffix = '.jpg')
	os.write(fd, b'content')
	os.close(fd)

	try:
		asset_store.register('source', path, 'source.jpg')
		asset_store.register('target', temp_file, 'target.mp4')

		source_assets = asset_store.list_assets('source')
		assert len(source_assets) == 1
		assert source_assets[0].get('type') == 'source'

		target_assets = asset_store.list_assets('target')
		assert len(target_assets) == 1
		assert target_assets[0].get('type') == 'target'

		output_assets = asset_store.list_assets('output')
		assert len(output_assets) == 0
	finally:
		os.remove(path)


def test_list_assets_invalid_type(session_id : str) -> None:
	with pytest.raises(ValueError) as exc:
		asset_store.list_assets('invalid_type')
	assert "Invalid asset_type" in str(exc.value)


def test_list_assets_session_scoped(temp_file : str) -> None:
	session1_id = 'session-1'
	set_session_id(session1_id)
	asset1_id = asset_store.register('source', temp_file, 'file1.jpg')

	session2_id = 'session-2'
	set_session_id(session2_id)

	fd, path2 = tempfile.mkstemp(suffix = '.jpg')
	os.write(fd, b'content 2')
	os.close(fd)

	try:
		asset2_id = asset_store.register('source', path2, 'file2.jpg')

		assets_session2 = asset_store.list_assets()
		assert len(assets_session2) == 1
		assert assets_session2[0].get('id') == asset2_id

		set_session_id(session1_id)
		assets_session1 = asset_store.list_assets()
		assert len(assets_session1) == 1
		assert assets_session1[0].get('id') == asset1_id
	finally:
		os.remove(path2)


def test_delete_asset(temp_file : str, session_id : str) -> None:
	asset_id = asset_store.register('source', temp_file, 'test.jpg')

	assert os.path.exists(temp_file)

	success = asset_store.delete_asset(asset_id)
	assert success is True

	assert not os.path.exists(temp_file)

	asset = asset_store.get_asset(asset_id)
	assert asset is None


def test_delete_asset_not_found(session_id : str) -> None:
	success = asset_store.delete_asset('non-existent-id')
	assert success is False


def test_cleanup_session_assets(session_id : str) -> None:
	fd1, path1 = tempfile.mkstemp(suffix = '.jpg')
	os.write(fd1, b'content 1')
	os.close(fd1)

	fd2, path2 = tempfile.mkstemp(suffix = '.mp4')
	os.write(fd2, b'content 2')
	os.close(fd2)

	asset_id1 = asset_store.register('source', path1, 'source.jpg')
	asset_id2 = asset_store.register('target', path2, 'target.mp4')

	assert os.path.exists(path1)
	assert os.path.exists(path2)

	asset_store.cleanup_session_assets(session_id)

	assert not os.path.exists(path1)
	assert not os.path.exists(path2)

	assert asset_store.get_asset(asset_id1) is None
	assert asset_store.get_asset(asset_id2) is None


def test_cleanup_session_assets_only_affects_target_session(temp_file : str) -> None:
	session1_id = 'session-1'
	set_session_id(session1_id)

	fd, path1 = tempfile.mkstemp(suffix = '.jpg')
	os.write(fd, b'content 1')
	os.close(fd)

	asset1_id = asset_store.register('source', path1, 'file1.jpg')

	session2_id = 'session-2'
	set_session_id(session2_id)
	asset2_id = asset_store.register('source', temp_file, 'file2.jpg')

	asset_store.cleanup_session_assets(session1_id)

	assert not os.path.exists(path1)
	assert os.path.exists(temp_file)

	set_session_id(session1_id)
	assert asset_store.get_asset(asset1_id) is None

	set_session_id(session2_id)
	assert asset_store.get_asset(asset2_id) is not None

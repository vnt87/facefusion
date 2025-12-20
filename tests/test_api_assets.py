import io
from typing import Iterator

import pytest
from starlette.testclient import TestClient

from facefusion import metadata, session_manager, state_manager
from facefusion.apis.core import create_api


@pytest.fixture(scope = 'module')
def test_client() -> Iterator[TestClient]:
	with TestClient(create_api()) as test_client:
		yield test_client


@pytest.fixture(scope = 'function', autouse = True)
def before_each() -> None:
	session_manager.SESSIONS.clear()
	state_manager.clear_item('asset_registry')


@pytest.fixture(scope = 'function')
def auth_token(test_client : TestClient) -> str:
	create_session_response = test_client.post('/session', json =
	{
		'client_version': metadata.get('version')
	})
	return create_session_response.json().get('access_token')


def test_upload_source_single(test_client : TestClient, auth_token : str) -> None:
	test_image = io.BytesIO(b'fake image data')
	test_image.name = 'test_face.jpg'

	response = test_client.post('/assets?type=source',
		files = {'file': ('test_face.jpg', test_image, 'image/jpeg')},
		headers = {'Authorization': f'Bearer {auth_token}'}
	)

	assert response.status_code == 201
	body = response.json()
	assert body.get('message') == '1 source(s) uploaded successfully'
	assert len(body.get('asset_ids')) == 1
	assert isinstance(body.get('asset_ids')[0], str)


def test_upload_source_multiple(test_client : TestClient, auth_token : str) -> None:
	test_image1 = io.BytesIO(b'fake image data 1')
	test_image1.name = 'face1.jpg'
	test_image2 = io.BytesIO(b'fake image data 2')
	test_image2.name = 'face2.jpg'

	response = test_client.post('/assets?type=source',
		files = [
			('file', ('face1.jpg', test_image1, 'image/jpeg')),
			('file', ('face2.jpg', test_image2, 'image/jpeg'))
		],
		headers = {'Authorization': f'Bearer {auth_token}'}
	)

	assert response.status_code == 201
	body = response.json()
	assert body.get('message') == '2 source(s) uploaded successfully'
	assert len(body.get('asset_ids')) == 2


def test_upload_target_image(test_client : TestClient, auth_token : str) -> None:
	test_image = io.BytesIO(b'fake image data')
	test_image.name = 'target.jpg'

	response = test_client.post('/assets?type=target',
		files = {'file': ('target.jpg', test_image, 'image/jpeg')},
		headers = {'Authorization': f'Bearer {auth_token}'}
	)

	assert response.status_code == 201
	body = response.json()
	assert body.get('message') == 'Target uploaded successfully'
	assert isinstance(body.get('asset_id'), str)


def test_upload_missing_type_param(test_client : TestClient, auth_token : str) -> None:
	test_image = io.BytesIO(b'fake image data')

	response = test_client.post('/assets',
		files = {'file': ('test.jpg', test_image, 'image/jpeg')},
		headers = {'Authorization': f'Bearer {auth_token}'}
	)

	assert response.status_code == 400
	assert response.json().get('message') == 'Missing required query parameter: type'


def test_upload_invalid_type_param(test_client : TestClient, auth_token : str) -> None:
	test_image = io.BytesIO(b'fake image data')

	response = test_client.post('/assets?type=invalid',
		files = {'file': ('test.jpg', test_image, 'image/jpeg')},
		headers = {'Authorization': f'Bearer {auth_token}'}
	)

	assert response.status_code == 400
	assert response.json().get('message') == 'Invalid type. Must be "source" or "target"'


def test_upload_no_file(test_client : TestClient, auth_token : str) -> None:
	response = test_client.post('/assets?type=source',
		headers = {'Authorization': f'Bearer {auth_token}'}
	)

	assert response.status_code == 400
	assert response.json().get('message') == 'No file provided'


def test_list_assets_empty(test_client : TestClient, auth_token : str) -> None:
	response = test_client.get('/assets',
		headers = {'Authorization': f'Bearer {auth_token}'}
	)

	assert response.status_code == 200
	body = response.json()
	assert body.get('count') == 0
	assert body.get('assets') == []


def test_list_assets_with_uploads(test_client : TestClient, auth_token : str) -> None:
	test_image = io.BytesIO(b'fake image data')
	test_client.post('/assets?type=source',
		files = {'file': ('face.jpg', test_image, 'image/jpeg')},
		headers = {'Authorization': f'Bearer {auth_token}'}
	)

	test_image2 = io.BytesIO(b'fake target data')
	test_client.post('/assets?type=target',
		files = {'file': ('target.jpg', test_image2, 'image/jpeg')},
		headers = {'Authorization': f'Bearer {auth_token}'}
	)

	response = test_client.get('/assets',
		headers = {'Authorization': f'Bearer {auth_token}'}
	)

	assert response.status_code == 200
	body = response.json()
	assert body.get('count') == 2
	assets = body.get('assets')
	assert len(assets) == 2


def test_list_assets_filter_by_type(test_client : TestClient, auth_token : str) -> None:
	test_image = io.BytesIO(b'fake image data')
	test_client.post('/assets?type=source',
		files = {'file': ('face.jpg', test_image, 'image/jpeg')},
		headers = {'Authorization': f'Bearer {auth_token}'}
	)

	test_image2 = io.BytesIO(b'fake target data')
	test_client.post('/assets?type=target',
		files = {'file': ('target.jpg', test_image2, 'image/jpeg')},
		headers = {'Authorization': f'Bearer {auth_token}'}
	)

	response = test_client.get('/assets?type=source',
		headers = {'Authorization': f'Bearer {auth_token}'}
	)

	assert response.status_code == 200
	body = response.json()
	assert body.get('count') == 1
	assets = body.get('assets')
	assert assets[0].get('type') == 'source'


def test_get_asset_metadata(test_client : TestClient, auth_token : str) -> None:
	test_image = io.BytesIO(b'fake image data')
	upload_response = test_client.post('/assets?type=source',
		files = {'file': ('face.jpg', test_image, 'image/jpeg')},
		headers = {'Authorization': f'Bearer {auth_token}'}
	)
	asset_id = upload_response.json().get('asset_ids')[0]

	response = test_client.get(f'/assets/{asset_id}',
		headers = {'Authorization': f'Bearer {auth_token}'}
	)

	assert response.status_code == 200
	body = response.json()
	assert body.get('id') == asset_id
	assert body.get('type') == 'source'
	assert body.get('filename') == 'face.jpg'
	assert body.get('size') > 0
	assert body.get('created_at')
	assert 'path' not in body


def test_get_asset_not_found(test_client : TestClient, auth_token : str) -> None:
	response = test_client.get('/assets/non-existent-id',
		headers = {'Authorization': f'Bearer {auth_token}'}
	)

	assert response.status_code == 404
	assert response.json().get('message') == 'Asset not found'


def test_download_asset(test_client : TestClient, auth_token : str) -> None:
	test_data = b'fake image data for download'
	test_image = io.BytesIO(test_data)
	upload_response = test_client.post('/assets?type=source',
		files = {'file': ('face.jpg', test_image, 'image/jpeg')},
		headers = {'Authorization': f'Bearer {auth_token}'}
	)
	asset_id = upload_response.json().get('asset_ids')[0]

	response = test_client.get(f'/assets/{asset_id}?action=download',
		headers = {'Authorization': f'Bearer {auth_token}'}
	)

	assert response.status_code == 200
	assert response.content == test_data


def test_download_asset_not_found(test_client : TestClient, auth_token : str) -> None:
	response = test_client.get('/assets/non-existent-id?action=download',
		headers = {'Authorization': f'Bearer {auth_token}'}
	)

	assert response.status_code == 404
	assert response.json().get('message') == 'Asset not found'


def test_delete_asset(test_client : TestClient, auth_token : str) -> None:
	test_image = io.BytesIO(b'fake image data')
	upload_response = test_client.post('/assets?type=source',
		files = {'file': ('face.jpg', test_image, 'image/jpeg')},
		headers = {'Authorization': f'Bearer {auth_token}'}
	)
	asset_id = upload_response.json().get('asset_ids')[0]

	response = test_client.delete(f'/assets/{asset_id}',
		headers = {'Authorization': f'Bearer {auth_token}'}
	)

	assert response.status_code == 200
	assert response.json().get('message') == 'Asset deleted successfully'

	get_response = test_client.get(f'/assets/{asset_id}',
		headers = {'Authorization': f'Bearer {auth_token}'}
	)
	assert get_response.status_code == 404


def test_delete_asset_not_found(test_client : TestClient, auth_token : str) -> None:
	response = test_client.delete('/assets/non-existent-id',
		headers = {'Authorization': f'Bearer {auth_token}'}
	)

	assert response.status_code == 404
	assert response.json().get('message') == 'Asset not found'


def test_assets_require_auth(test_client : TestClient) -> None:
	response = test_client.get('/assets')
	assert response.status_code == 401

	response = test_client.post('/assets?type=source')
	assert response.status_code == 401

	response = test_client.get('/assets/some-id')
	assert response.status_code == 401

	response = test_client.delete('/assets/some-id')
	assert response.status_code == 401


def test_assets_session_isolation(test_client : TestClient) -> None:
	session1_response = test_client.post('/session', json = {'client_version': metadata.get('version')})
	session1_token = session1_response.json().get('access_token')

	session2_response = test_client.post('/session', json = {'client_version': metadata.get('version')})
	session2_token = session2_response.json().get('access_token')

	test_image = io.BytesIO(b'session 1 data')
	upload_response = test_client.post('/assets?type=source',
		files = {'file': ('face.jpg', test_image, 'image/jpeg')},
		headers = {'Authorization': f'Bearer {session1_token}'}
	)
	asset_id = upload_response.json().get('asset_ids')[0]

	response = test_client.get('/assets',
		headers = {'Authorization': f'Bearer {session1_token}'}
	)
	assert response.json().get('count') == 1

	response = test_client.get('/assets',
		headers = {'Authorization': f'Bearer {session2_token}'}
	)
	assert response.json().get('count') == 0

	response = test_client.get(f'/assets/{asset_id}',
		headers = {'Authorization': f'Bearer {session2_token}'}
	)
	assert response.status_code == 404

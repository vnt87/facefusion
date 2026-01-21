from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from facefusion import metadata

def create_app() -> FastAPI:
	app = FastAPI(
		title = metadata.get('name'),
		version = metadata.get('version')
	)

	app.add_middleware(
		CORSMiddleware,
		allow_origins = [ '*' ],
		allow_credentials = True,
		allow_methods = [ '*' ],
		allow_headers = [ '*' ]
	)

	from .endpoints import router
	from .websocket import websocket_endpoint
	
	app.include_router(router)
	app.websocket("/ws")(websocket_endpoint)

	return app

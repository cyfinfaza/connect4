import asyncio
import re
import websockets
import time
import requests
import json
from collections import Counter

connected = set()

BOARD_CLEAR = [[0]*7 for i in range(6)]
GAME_TEMPLATE = {'players':{}, 'board':BOARD_CLEAR.copy(), 'turnName':'1', 'rxGroup':set()}
games = {'0': GAME_TEMPLATE.copy()}

async def server(websocket, path):
	global games
	print(games)
	# Register.
	connected.add(websocket)
	print("ADD INDIVIDUAL "+str(id(websocket)))
	mykey = '1'
	partnerkey = '2'
	mygame = '0'
	mycolor = 1
	myname = "Player one"
	games[mygame]['rxGroup'].add(websocket)
	playing = True
	# Board Update
	await websocket.send(json.dumps({'type': 'boardUpdate', 'board':games[mygame]['board']}))
	if len(games[mygame]['players']) < 2:
		# NO PARTNER YET
		if len(games[mygame]['players']) == 0:
			games[mygame]['board'] = BOARD_CLEAR.copy()
			print("game 0 board cleared")
			games[mygame]['players'][mykey] = {'name':myname, 'color':mycolor, 'websocket':websocket}
			await websocket.send(json.dumps({'type': 'noPartner'}))
		# PARTNER
		else:
			if '1' in games[mygame]['players']: mykey = '2'; partnerkey = '1'
			else: mykey = '1'; partnerkey = '2'
			if games[mygame]['players'][partnerkey]['color'] == 1: myname = 'Player two'; mycolor=2
			else: myname = 'Player one'; mycolor=1
			games[mygame]['players'][mykey] = {'name':myname, 'color':mycolor, 'websocket':websocket}
			await websocket.send(json.dumps({'type': 'setPartner', 'name':games[mygame]['players'][partnerkey]['name'], 'color':games[mygame]['players'][partnerkey]['color']}))
			await games[mygame]['players'][partnerkey]['websocket'].send(json.dumps({'type': 'setPartner', 'name':myname, 'color':mycolor}))
		await websocket.send(json.dumps({'type': 'setMe', 'name':myname, 'color':mycolor}))
	else:
		await websocket.send(json.dumps({'type': 'gameFull'}))
		playing = False
	for conn in games[mygame]['rxGroup']:
		await conn.send(json.dumps({'type': 'rxGroupUpdate', 'viewers':len(games[mygame]['rxGroup'])}))
	try:
		print(f'Connected users: {len(connected)}')
		async for message in websocket:
			if playing:
				result = json.loads(message)
				boardUpdate = True
				print(str(id(websocket)) +" "+ message)
				if result['type'] == "chipDrop":
					games[mygame]['board'][result['row']][result['col']] = mycolor
				elif result['type'] == "clearRequest":
					print("clearing board 0")
					print(BOARD_CLEAR)
					games[mygame]['board'] = [[0]*7 for i in range(6)]
					print(games[mygame]['board'])
					for conn in games[mygame]['rxGroup']:
						await conn.send(json.dumps({'type': 'boardClearedUpdate'}))
				if boardUpdate:
					for conn in games[mygame]['rxGroup']:
						await conn.send(json.dumps({'type': 'boardUpdate', 'board':games[mygame]['board']}))
		print("END INDIVIDUAL LOGIC LOOP "+str(id(websocket)))
	finally:
		# Unregister.
		print("DELETE INDIVIDUAL "+str(id(websocket)))
		games[mygame]['rxGroup'].remove(websocket)
		connected.remove(websocket)
		print(f'Connected users: {len(connected)}')
		print(len(games[mygame]['players']))
		if playing: games[mygame]['players'].pop(mykey)
		if playing and len(games[mygame]['players'])>0:
			await games[mygame]['players'][partnerkey]['websocket'].send(json.dumps({'type': 'lostPartner'}))
		for conn in games[mygame]['rxGroup']:
			await conn.send(json.dumps({'type': 'rxGroupUpdate', 'viewers':len(games[mygame]['rxGroup'])}))

start_server = websockets.serve(server, "0.0.0.0", 6002)
asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()
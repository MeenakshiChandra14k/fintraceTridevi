.PHONY: all kafka gateway deepbrain frontend stop

all:
	docker compose up -d
	@make kafka &
	@make gateway &
	@make deepbrain &
	@make frontend

kafka:
	cd scripts && python data_pump.py

gateway:
	cd services/gateway-api && pip install -r requirements.txt --break-system-packages -q && python main.py

deepbrain:
	cd services/pass2-deepbrain && pip install -r requirements.txt --break-system-packages -q && python nuke.py && python main.py

frontend:
	cd dashboard && npm install && npm run dev

stop:
	pkill -f "data_pump.py" || true
	pkill -f "gateway-api/main.py" || true
	pkill -f "pass2-deepbrain/main.py" || true
	pkill -f "npm run dev" || true
	docker compose down
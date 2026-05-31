.PHONY: all kafka gateway deepbrain frontend stop

VENV = source /Users/sajith/fintraceTridevi/venv/bin/activate

setup:
	curl -L "https://drive.google.com/file/d/1MF2G8UUirdx2OpS1kxx0MJB2hquYgIDF/view?usp=sharing" -o scripts/data/paysim.csv

all:
	docker compose up -d
	osascript -e 'tell app "Terminal" to activate' -e 'tell app "Terminal" to do script "cd $(PWD) && make gateway"'
	osascript -e 'tell app "Terminal" to activate' -e 'tell app "Terminal" to do script "cd $(PWD) && make deepbrain"'
	osascript -e 'tell app "Terminal" to activate' -e 'tell app "Terminal" to do script "cd $(PWD) && make kafka"'
	osascript -e 'tell app "Terminal" to activate' -e 'tell app "Terminal" to do script "cd $(PWD) && make frontend"'

gateway:
	cd services/gateway-api && $(VENV) && python3 main.py

deepbrain:
	cd services/pass2-deepbrain && $(VENV) && python3 nuke.py && python3 main.py

kafka:
	$(VENV) && python3 scripts/data_pump.py

frontend:
	cd dashboard && npm install && npm run dev

stop:
	pkill -f "data_pump.py" || true
	pkill -f "gateway-api/main.py" || true
	pkill -f "pass2-deepbrain/main.py" || true
	pkill -f "npm run dev" || true
	docker compose down
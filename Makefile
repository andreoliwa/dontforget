default:
	@echo "Must call a specific command"
	@exit 1

build:
	docker-compose build

logs:
	docker-compose logs -f --tail 100

stop:
	docker-compose stop telegram

restart: stop
	docker-compose up -d

lint:
	./manage.py lint --pylint

test:
	py.test --verbose --cov dontforget

lt: lint test

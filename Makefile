default:
	@echo "Must call a specific command"
	@exit 1

build:
	docker-compose build

logs:
	docker-compose logs -f --tail 100

stop:
	docker-compose stop flask
	docker-compose stop telegram

restart: stop
	docker-compose up -d

isort:
	isort -y

lint:
	./manage.py lint --pylint

test:
	py.test --verbose --cov dontforget

ilt: isort lint test

update:
	clear
	pre-commit autoupdate
	pre-commit gc
	poetry update

dev:
	clear
	pre-commit run --all-files
	pytest

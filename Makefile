help:
	@echo "fix-isort - fix import order with isort"
	@echo "lint - check style with isort, flake8, pep257 and pylint"
	@echo "lt - lint and test"
	@echo "test - run tests quickly with the default Python"

fix-isort:
	isort --recursive --settings-path . *.py dontforget migrations tests

lint:
	isort --recursive --settings-path . --check *.py dontforget migrations tests
	flake8 dontforget migrations tests
	pep257 dontforget migrations tests
	# pylint --rcfile=.pylintrc dontforget migrations tests

lt: lint test

test:
	./manage.py test

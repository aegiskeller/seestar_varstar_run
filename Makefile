install:
	pip install --upgrade pip
	pip install -r requirements.txt

format:
	black .

lint:
	pylint --disable=all --enable=E --max-line-length=120 --output-format=colorized --reports=n $(shell find . -maxdepth 1 -name "*.py")
## For Backend If You Do Not Install Poetry 

<!-- Run this Query On Windows Powershell to install Poetry Globally -->

(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | py -

<!-- Install Poetry in Project -->

    pip install poetry

<!-- If pyporject.toml File Already Exist In The Directory -->

    Poetry install

<!-- Now Create Your Vitual Environment By Running This Query -->

    poetry config virtualenvs.create true

<!-- After That Run This Query For env -->

    poetry env info

<!-- If You Install uvicorn Then Run This Query     -->

    poetry run uvicorn app.main:app --reload


## End For Backend

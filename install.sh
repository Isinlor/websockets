# see https://rogerbinns.github.io/apsw/download.html
pip3 install --user https://github.com/rogerbinns/apsw/releases/download/3.34.0-r1/apsw-3.34.0-r1.zip \
--global-option=fetch --global-option=--version --global-option=3.34.0 --global-option=--all \
--global-option=build --global-option=--enable-all-extensions

pip3 install -r requirements.txt
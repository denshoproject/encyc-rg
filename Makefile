PROJECT=encyc
APP=encycrg
USER=encyc
SHELL = /bin/bash

APP_VERSION := $(shell cat VERSION)
GIT_SOURCE_URL=https://github.com/densho/encyc-rg


PACKAGE_SERVER=ddr.densho.org/static/$(APP)

SRC_REPO_ASSETS=https://github.com/denshoproject/encyc-rg-assets.git

INSTALL_BASE=/opt
INSTALLDIR=$(INSTALL_BASE)/encyc-rg
DOWNLOADS_DIR=/tmp/$(APP)-install
INSTALL_RG=/opt/encyc-rg
INSTALL_ASSETS=/opt/encyc-rg-assets
REQUIREMENTS=$(INSTALLDIR)/requirements.txt
PIP_CACHE_DIR=$(INSTALL_BASE)/pip-cache

VIRTUALENV=$(INSTALLDIR)/venv/encycrg
SETTINGS=$(INSTALL_LOCAL)/encycrg/encycrg/settings.py

CONF_BASE=/etc/encyc
CONF_PRODUCTION=$(CONF_BASE)/encycrg.cfg
CONF_LOCAL=$(CONF_BASE)/encycrg-local.cfg
CONF_SECRET=$(CONF_BASE)/encycrg-secret-key.txt

SQLITE_BASE=/var/lib/$(PROJECT)
LOGS_BASE=/var/log/$(PROJECT)

MEDIA_BASE=/var/www/$(APP)
MEDIA_ROOT=$(MEDIA_BASE)/media
STATIC_ROOT=$(MEDIA_BASE)/static

# Release name e.g. jessie
DEBIAN_CODENAME := $(shell lsb_release -sc)
# Release numbers e.g. 8.10
DEBIAN_RELEASE := $(shell lsb_release -sr)
# Sortable major version tag e.g. deb8
DEBIAN_RELEASE_TAG = deb$(shell lsb_release -sr | cut -c1)

PYTHON_VERSION=
OPENJDK_PKG=
ifeq ($(DEBIAN_CODENAME), bullseye)
	PYTHON_VERSION=3.9
	OPENJDK_PKG=openjdk-17-jre-headless
endif
ifeq ($(DEBIAN_CODENAME), bookworm)
	PYTHON_VERSION=3.11.2
	OPENJDK_PKG=openjdk-17-jre-headless
endif
ifeq ($(DEBIAN_CODENAME), trixie)
	PYTHON_VERSION=3.11.6
	OPENJDK_PKG=openjdk-17-jre-headless
endif


ELASTICSEARCH=elasticsearch-2.4.6.deb

SUPERVISOR_GUNICORN_CONF=/etc/supervisor/conf.d/$(APP).conf
SUPERVISOR_CONF=/etc/supervisor/supervisord.conf
NGINX_CONF=/etc/nginx/sites-available/$(APP).conf
NGINX_CONF_LINK=/etc/nginx/sites-enabled/$(APP).conf

ASSETS=encyc-rg-assets.tgz

TGZ_BRANCH := $(shell git rev-parse --abbrev-ref HEAD | tr -d _ | tr -d -)
TGZ_FILE=$(APP)_$(APP_VERSION)
TGZ_DIR=$(INSTALL_RG)/$(TGZ_FILE)
TGZ_APP=$(TGZ_DIR)/encyc-rg
TGZ_ASSETS=$(TGZ_DIR)/encyc-rg/encyc-rg-assets

# Adding '-rcN' to VERSION will name the package "ddrlocal-release"
# instead of "ddrlocal-BRANCH"
DEB_BRANCH := $(shell python3 bin/package-branch.py)
DEB_ARCH=amd64
DEB_NAME_BULLSEYE=$(APP)-$(DEB_BRANCH)
DEB_NAME_BOOKWORM=$(APP)-$(DEB_BRANCH)
DEB_NAME_TRIXIE=$(APP)-$(DEB_BRANCH)
# Application version, separator (~), Debian release tag e.g. deb8
# Release tag used because sortable and follows Debian project usage.
DEB_VERSION_BULLSEYE=$(APP_VERSION)~deb11
DEB_VERSION_BOOKWORM=$(APP_VERSION)~deb12
DEB_VERSION_TRIXIE=$(APP_VERSION)~deb13
DEB_FILE_BULLSEYE=$(DEB_NAME_BULLSEYE)_$(DEB_VERSION_BULLSEYE)_$(DEB_ARCH).deb
DEB_FILE_BOOKWORM=$(DEB_NAME_BOOKWORM)_$(DEB_VERSION_BOOKWORM)_$(DEB_ARCH).deb
DEB_FILE_TRIXIE=$(DEB_NAME_TRIXIE)_$(DEB_VERSION_TRIXIE)_$(DEB_ARCH).deb
DEB_VENDOR=Densho.org
DEB_MAINTAINER=<geoffrey.jost@densho.org>
DEB_DESCRIPTION=Densho Encyclopedia Resource Guide site
DEB_BASE=opt/encyc-rg


.PHONY: help


help:
	@echo "encyc-rg Install Helper"
	@echo ""
	@echo "get     - Downloads source, installers, and assets files. Does not install."
	@echo ""
	@echo "install - Installs app, config files, and static assets.  Does not download."
	@echo "          IMPORTANT: Run 'adduser encyc' first to install encyc user and group."
	@echo "          Installation instructions: make howto-install"
	@echo ""
	@echo "syncdb  - Initialize or update Django app's database tables."
	@echo ""
	@echo "test    - Run unit tests"
	@echo ""
	@echo "reload  - Reloads supervisord and nginx configs"
	@echo ""
	@echo "restart - Restarts all servers"
	@echo ""
	@echo "stop    - Stops all servers"
	@echo ""
	@echo "status  - Server status"
	@echo ""
	@echo "uninstall - Deletes 'compiled' Python files. Leaves build dirs and configs."
	@echo "clean   - Deletes files created by building the program. Leaves configs."
	@echo ""
	@echo "You can append the service name to most commands (e.g. restart-app)."
	@echo "- app"
	@echo "- redis"
	@echo "- nginx"
	@echo "- supervisord"
	@echo "- elasticsearch"
	@echo ""
	@echo "branch BRANCH=[branch] - Switches encyc-rg and supporting repos to [branch]."
	@echo ""

help-all:
	@echo "install - Do a fresh install"
	@echo "install-prep    - git-config, add-user, apt-update, install-misc-tools"
	@echo "install-daemons - install-nginx install-redis install-elasticsearch"
	@echo "install-app     - install-encyc-rg"
	@echo "install-static  - "
	@echo "restart - Restart servers"
	@echo "status  - Server status"
	@echo "install-configs - "
	@echo "uninstall - "
	@echo "clean - "

howto-install:
	@echo "HOWTO INSTALL"
	@echo "- Basic Debian netinstall"
	@echo "- # vi /etc/network/interfaces"
	@echo "- # reboot"
	@echo "- # apt-get install openssh fail2ban ufw"
	@echo "- # ufw allow 22/tcp"
	@echo "- # ufw allow 80/tcp"
	@echo "- # ufw enable"
	@echo "- # apt-get install make"
	@echo "- # adduser encyc"
	@echo "- # git clone https://github.com/densho/encyc-rg.git $(INSTALLDIR)"
	@echo "- # cd $(INSTALLDIR)/encycrg"
	@echo "- # make install"
	@echo "- # make syncdb"
	@echo "- # make restart"


get: get-app apt-update

install: install-prep install-app install-static install-configs

test: test-app

uninstall: uninstall-app

clean: clean-app


install-prep: apt-upgrade install-core git-config install-misc-tools

apt-update:
	@echo ""
	@echo "Package update ---------------------------------------------------------"
	apt-get --assume-yes update

apt-upgrade:
	@echo ""
	@echo "Package upgrade --------------------------------------------------------"
	apt-get --assume-yes upgrade

install-core:
	apt-get --assume-yes install bzip2 curl gdebi-core logrotate ntp p7zip-full wget python3

git-config:
	git config --global alias.st status
	git config --global alias.co checkout
	git config --global alias.br branch
	git config --global alias.ci commit

install-misc-tools:
	@echo ""
	@echo "Installing miscellaneous tools -----------------------------------------"
	apt-get --assume-yes install ack-grep byobu elinks htop mg multitail


get-daemons: get-elasticsearch

install-daemons: install-nginx install-redis install-elasticsearch

install-nginx:
	@echo ""
	@echo "Nginx ------------------------------------------------------------------"
	apt-get --assume-yes install nginx

install-redis:
	@echo ""
	@echo "Redis ------------------------------------------------------------------"
	apt-get --assume-yes install redis-server

get-elasticsearch:
	-wget -nc -P $(DOWNLOADS_DIR) http://$(PACKAGE_SERVER)/$(ELASTICSEARCH)

install-elasticsearch: install-core
	@echo ""
	@echo "Elasticsearch ----------------------------------------------------------"
# Elasticsearch is configured/restarted here so it's online by the time script is done.
	apt-get --assume-yes install $(OPENJDK_PKG)
	-gdebi --non-interactive /tmp/downloads/$(ELASTICSEARCH)
#cp $(INSTALL_BASE)/ddr-public/conf/elasticsearch.yml /etc/elasticsearch/
#chown root.root /etc/elasticsearch/elasticsearch.yml
#chmod 644 /etc/elasticsearch/elasticsearch.yml
# 	@echo "${bldgrn}search engine (re)start${txtrst}"
	-service elasticsearch stop
	-systemctl disable elasticsearch.service

enable-elasticsearch:
	systemctl enable elasticsearch.service

disable-elasticsearch:
	systemctl disable elasticsearch.service

remove-elasticsearch:
	apt-get --assume-yes remove $(OPENJDK_PKG) elasticsearch


install-virtualenv:
	apt-get --assume-yes install python3-pip python3-venv
	python3 -m venv $(VIRTUALENV)
	source $(VIRTUALENV)/bin/activate; \
	pip3 install -U --cache-dir=$(PIP_CACHE_DIR) pip

install-setuptools: install-virtualenv
	@echo ""
	@echo "install-setuptools -----------------------------------------------------"
	apt-get --assume-yes install python-dev
	source $(VIRTUALENV)/bin/activate; \
	pip3 install -U bpython setuptools


get-app: get-encyc-rg

install-app: install-encyc-rg

test-app: test-encyc-rg

uninstall-app: uninstall-encyc-rg

clean-app: clean-encyc-rg


get-encyc-rg:
	git pull
	pip3 install -U -r $(REQUIREMENTS)

install-encyc-rg: install-virtualenv
	@echo ""
	@echo "encyc-rg --------------------------------------------------------------"
	apt-get --assume-yes install imagemagick sqlite3 supervisor
	source $(VIRTUALENV)/bin/activate; \
	pip3 install -U -r $(REQUIREMENTS)
	sudo -u encyc git config --global --add safe.directory $(INSTALL_RG)
# logs dir
	-mkdir $(LOGS_BASE)
	chown -R $(USER).root $(LOGS_BASE)
	chmod -R 755 $(LOGS_BASE)
# sqlite db dir
	-mkdir $(SQLITE_BASE)
	chown -R $(USER).root $(SQLITE_BASE)
	chmod -R 755 $(SQLITE_BASE)

syncdb:
	source $(VIRTUALENV)/bin/activate; \
	cd $(INSTALLDIR)/encycrg && python manage.py makemigrations --noinput
	source $(VIRTUALENV)/bin/activate; \
	cd $(INSTALLDIR)/encycrg && python manage.py migrate --noinput
	chown -R $(USER).root $(SQLITE_BASE)
	chmod -R 750 $(SQLITE_BASE)
	chown -R $(USER).root $(LOGS_BASE)
	chmod -R 755 $(LOGS_BASE)

test-encyc-rg:
	source $(VIRTUALENV)/bin/activate; \
	cd $(INSTALLDIR); python encycrg/manage.py test rg

shell:
	source $(VIRTUALENV)/bin/activate; \
	cd $(INSTALLDIR); python encycrg/manage.py shell

runserver:
	source $(VIRTUALENV)/bin/activate; \
	cd $(INSTALLDIR); python encycrg/manage.py runserver 0.0.0.0:8081

uninstall-encyc-rg:
	cd $(INSTALLDIR)/encycrg
	source $(VIRTUALENV)/bin/activate; \
	-pip3 uninstall -r $(REQUIREMENTS)
	-rm /usr/local/lib/python2.7/dist-packages/encycrg-*
	-rm -Rf /usr/local/lib/python2.7/dist-packages/encycrg

restart-encycrg:
	/etc/init.d/supervisor restart encycrg

stop-encycrg:
	/etc/init.d/supervisor stop encycrg

clean-encyc-rg:
	-rm -Rf $(INSTALLDIR)/encycrg/src

clean-pip:
	-rm -Rf $(PIP_CACHE_DIR)/*


branch:
	cd $(INSTALLDIR)/encycrg; python ./bin/git-checkout-branch.py $(BRANCH)


install-static: get-app-assets install-app-assets install-restframework install-swagger

clean-static: clean-app-assets clean-restframework clean-swagger

get-app-assets:
	@echo ""
	@echo "get assets -------------------------------------------------------------"
	wget -nc -P /tmp http://$(PACKAGE_SERVER)/$(ASSETS)

install-app-assets:
	@echo ""
	@echo "install assets ---------------------------------------------------------"
	-mkdir -p $(MEDIA_BASE)
	chown -R root.root $(MEDIA_BASE)
	chmod -R 755 $(MEDIA_BASE)
	tar xzvf /tmp/$(ASSETS) -C /tmp/
	-mkdir -p $(STATIC_ROOT)
	cp -R /tmp/encyc-rg-assets/* $(STATIC_ROOT)

clean-app-assets:
	-rm -Rf $(STATIC_ROOT)/

install-restframework:
	@echo ""
	@echo "rest-framework assets ---------------------------------------------------"
	cp -R $(VIRTUALENV)/lib/$(PYTHON_VERSION)/site-packages/rest_framework/static/rest_framework/ $(STATIC_ROOT)/

install-swagger:
	@echo ""
	@echo "rest-swagger assets -----------------------------------------------------"
	cp -R $(VIRTUALENV)/lib/$(PYTHON_VERSION)/site-packages/drf_yasg/static/drf-yasg/ $(STATIC_ROOT)/

clean-restframework:
	-rm -Rf $(STATIC_ROOT)/rest_framework/

clean-swagger:
	-rm -Rf $(STATIC_ROOT)/drf_yasg/


install-configs:
	@echo ""
	@echo "installing configs --------------------------------------------------"
	-mkdir /etc/encyc
	cp $(INSTALLDIR)/conf/$(APP).cfg $(CONF_PRODUCTION)
	chown root.root $(CONF_PRODUCTION)
	chmod 644 $(CONF_PRODUCTION)
	touch $(CONF_LOCAL)
	chown encyc.root $(CONF_LOCAL)
	chmod 640 $(CONF_LOCAL)
	python -c 'import random; print "".join([random.choice("abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)") for i in range(50)])' > $(CONF_SECRET)
	chown encyc.root $(CONF_SECRET)
	chmod 640 $(CONF_SECRET)
	cp $(INSTALLDIR)/conf/encycrg.conf $(NGINX_CONF)
	chown root.root $(NGINX_CONF)
	chmod 644 $(NGINX_CONF)
	-ln -s $(NGINX_CONF) $(NGINX_CONF_LINK)

uninstall-configs:
	-rm $(CONF_SECRET)

install-daemons-configs:
	@echo ""
	@echo "daemon configs ------------------------------------------------------"
# nginx settings
	cp $(INSTALLDIR)/conf/nginx-app.conf $(NGINX_CONF)
	chown root.root $(NGINX_CONF)
	chmod 644 $(NGINX_CONF)
	-ln -s $(NGINX_CONF) $(NGINX_CONF_LINK)
	cp $(INSTALLDIR)/conf/nginx-elastic.conf $(NGINX_ELASTIC_CONF)
	chown root.root $(NGINX_ELASTIC_CONF)
	chmod 644 $(NGINX_ELASTIC_CONF)
	-ln -s $(NGINX_ELASTIC_CONF) $(NGINX_ELASTIC_CONF_LINK)
	-rm /etc/nginx/sites-enabled/default
# supervisord
	cp $(INSTALLDIR)/conf/gunicorn.conf $(GUNICORN_CONF)
	chown root.root $(GUNICORN_CONF)
	chmod 644 $(GUNICORN_CONF)

uninstall-daemons-configs:
	-rm $(NGINX_APP_CONF)
	-rm $(NGINX_APP_CONF_LINK)
	-rm $(NGINX_ELASTIC_CONF)
	-rm $(NGINX_ELASTIC_CONF_LINK)
	-rm $(GUNICORN_CONF)


reload: reload-nginx reload-supervisor

reload-nginx:
	/etc/init.d/nginx reload

reload-supervisor:
	supervisorctl reload


restart: restart-elasticsearch restart-redis restart-nginx restart-supervisor

restart-elasticsearch:
	/etc/init.d/elasticsearch restart

restart-redis:
	/etc/init.d/redis-server restart

restart-nginx:
	/etc/init.d/nginx restart

restart-supervisor:
	/etc/init.d/supervisor restart


stop: stop-elasticsearch stop-redis stop-nginx stop-supervisor

stop-elasticsearch:
	/etc/init.d/elasticsearch stop

stop-redis:
	/etc/init.d/redis-server stop

stop-nginx:
	/etc/init.d/nginx stop

stop-supervisor:
	/etc/init.d/supervisor stop


status:
	-/etc/init.d/redis-server status
	-/etc/init.d/elasticsearch status
	-/etc/init.d/nginx status
	-supervisorctl status

git-status:
	@echo "------------------------------------------------------------------------"
	cd $(INSTALLDIR) && git status


tgz-local:
	rm -Rf $(TGZ_DIR)
	git clone $(INSTALL_APP) $(TGZ_APP)
	git clone $(INSTALL_ASSETS) $(TGZ_ASSETS)
	cd $(TGZ_APP); git checkout develop; git checkout master
	cd $(TGZ_ASSETS); git checkout develop; git checkout master
	tar czf $(TGZ_FILE).tgz $(TGZ_FILE)
	rm -Rf $(TGZ_DIR)

tgz:
	rm -Rf $(TGZ_DIR)
	git clone $(GIT_SOURCE_URL) $(TGZ_APP)
	git clone $(SRC_REPO_ASSETS) $(TGZ_ASSETS)
	cd $(TGZ_APP); git checkout develop; git checkout master
	cd $(TGZ_ASSETS); git checkout develop; git checkout master
	tar czf $(TGZ_FILE).tgz $(TGZ_FILE)
	rm -Rf $(TGZ_DIR)


# http://fpm.readthedocs.io/en/latest/
install-fpm:
	@echo "install-fpm ------------------------------------------------------------"
	apt-get install --assume-yes ruby ruby-dev rubygems build-essential
	gem install --no-document fpm

# https://stackoverflow.com/questions/32094205/set-a-custom-install-directory-when-making-a-deb-package-with-fpm
# https://brejoc.com/tag/fpm/
deb: deb-bullseye

deb-bullseye:
	@echo ""
	@echo "FPM packaging (bullseye) -----------------------------------------------"
	-rm -Rf $(DEB_FILE_BULLSEYE)
# Make package
	fpm   \
	--verbose   \
	--input-type dir   \
	--output-type deb   \
	--name $(DEB_NAME_BULLSEYE)   \
	--version $(DEB_VERSION_BULLSEYE)   \
	--package $(DEB_FILE_BULLSEYE)   \
	--url "$(GIT_SOURCE_URL)"   \
	--vendor "$(DEB_VENDOR)"   \
	--maintainer "$(DEB_MAINTAINER)"   \
	--description "$(DEB_DESCRIPTION)"   \
	--depends "python3"   \
	--depends "imagemagick"   \
	--depends "sqlite3"   \
	--depends "supervisor"   \
	--chdir $(INSTALLDIR)   \
	.git=$(DEB_BASE)   \
	.gitignore=$(DEB_BASE)   \
	conf=$(DEB_BASE)   \
	COPYRIGHT=$(DEB_BASE)   \
	encycrg=$(DEB_BASE)   \
	static=$(MEDIA_BASE)   \
	venv=$(DEB_BASE)   \
	INSTALL=$(DEB_BASE)   \
	LICENSE=$(DEB_BASE)   \
	Makefile=$(DEB_BASE)   \
	README.rst=$(DEB_BASE)   \
	requirements.txt=$(DEB_BASE)  \
	VERSION=$(DEB_BASE)  \
	conf/encycrg.cfg=$(CONF_BASE)/encycrg.cfg

deb-bookworm:
	@echo ""
	@echo "FPM packaging (trixie) -----------------------------------------------"
	-rm -Rf $(DEB_FILE_BOOKWORM)
# Make package
	fpm   \
	--verbose   \
	--input-type dir   \
	--output-type deb   \
	--name $(DEB_NAME_BOOKWORM)   \
	--version $(DEB_VERSION_BOOKWORM)   \
	--package $(DEB_FILE_BOOKWORM)   \
	--url "$(GIT_SOURCE_URL)"   \
	--vendor "$(DEB_VENDOR)"   \
	--maintainer "$(DEB_MAINTAINER)"   \
	--description "$(DEB_DESCRIPTION)"   \
	--depends "python3"   \
	--depends "git-core"   \
	--depends "imagemagick"   \
	--depends "sqlite3"   \
	--depends "supervisor"   \
	--chdir $(INSTALLDIR)   \
	.git=$(DEB_BASE)   \
	.gitignore=$(DEB_BASE)   \
	conf=$(DEB_BASE)   \
	COPYRIGHT=$(DEB_BASE)   \
	encycrg=$(DEB_BASE)   \
	static=$(MEDIA_BASE)   \
	venv=$(DEB_BASE)   \
	INSTALL=$(DEB_BASE)   \
	LICENSE=$(DEB_BASE)   \
	Makefile=$(DEB_BASE)   \
	README.rst=$(DEB_BASE)   \
	requirements.txt=$(DEB_BASE)  \
	VERSION=$(DEB_BASE)  \
	conf/encycrg.cfg=$(CONF_BASE)/encycrg.cfg


deb-trixie:
	@echo ""
	@echo "FPM packaging (trixie) -----------------------------------------------"
	-rm -Rf $(DEB_FILE_TRIXIE)
# Make package
	fpm   \
	--verbose   \
	--input-type dir   \
	--output-type deb   \
	--name $(DEB_NAME_TRIXIE)   \
	--version $(DEB_VERSION_TRIXIE)   \
	--package $(DEB_FILE_TRIXIE)   \
	--url "$(GIT_SOURCE_URL)"   \
	--vendor "$(DEB_VENDOR)"   \
	--maintainer "$(DEB_MAINTAINER)"   \
	--description "$(DEB_DESCRIPTION)"   \
	--depends "python3"   \
	--depends "git-core"   \
	--depends "imagemagick"   \
	--depends "sqlite3"   \
	--depends "supervisor"   \
	--chdir $(INSTALLDIR)   \
	.git=$(DEB_BASE)   \
	.gitignore=$(DEB_BASE)   \
	conf=$(DEB_BASE)   \
	COPYRIGHT=$(DEB_BASE)   \
	encycrg=$(DEB_BASE)   \
	static=$(MEDIA_BASE)   \
	venv=$(DEB_BASE)   \
	INSTALL=$(DEB_BASE)   \
	LICENSE=$(DEB_BASE)   \
	Makefile=$(DEB_BASE)   \
	README.rst=$(DEB_BASE)   \
	requirements.txt=$(DEB_BASE)  \
	VERSION=$(DEB_BASE)  \
	conf/encycrg.cfg=$(CONF_BASE)/encycrg.cfg

secret-key:
	@echo ""
	@echo "secret-key -------------------------------------------------------------"
	date +%s | sha256sum | base64 | head -c 50 > $(CONF_BASE)/encycrg-secret-key.txt

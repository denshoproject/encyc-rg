PROJECT=encyc
APP=encycrg
USER=encyc
VERSION=0.1.0

SHELL = /bin/bash
DEBIAN_CODENAME := $(shell lsb_release -sc)
DEBIAN_RELEASE := $(shell lsb_release -sr)

GIT_SOURCE_URL=https://github.com/densho/encyc-rg
PACKAGE_SERVER=ddr.densho.org/static/$(APP)

INSTALL_BASE=/usr/local/src
INSTALLDIR=$(INSTALL_BASE)/encyc-rg
DOWNLOADS_DIR=/tmp/$(APP)-install
REQUIREMENTS=$(INSTALLDIR)/requirements.txt
PIP_CACHE_DIR=$(INSTALL_BASE)/pip-cache

VIRTUALENV=$(INSTALLDIR)/env
SETTINGS=$(INSTALL_LOCAL)/encycrg/encycrg/settings.py

FPM_ARCH=amd64
FPM_FILE=encyc-rg_$(VERSION)_$(FPM_ARCH).deb
FPM_VENDOR=Densho.org
FPM_MAINTAINER=<geoffrey.jost@densho.org>
FPM_DESCRIPTION=Densho Encyclopedia Resource Guide site
FPM_BASE=usr/local/src/encyc-rg

PACKAGE_BASE=/tmp/encycrg
PACKAGE_TMP=$(PACKAGE_BASE)/encyc-rg
PACKAGE_ENV=$(PACKAGE_TMP)/env
# current branch name minus dashes or underscores
PACKAGE_BRANCH := $(shell git rev-parse --abbrev-ref HEAD | tr -d _ | tr -d -)
# current commit date minus dashes
PACKAGE_TIMESTAMP := $(shell git log -1 --pretty="%ad" --date=short | tr -d -)
# current commit hash
PACKAGE_COMMIT := $(shell git log -1 --pretty="%h")
PACKAGE_TGZ=encycrg-$(PACKAGE_BRANCH)-$(PACKAGE_TIMESTAMP)-$(PACKAGE_COMMIT).tgz
PACKAGE_RSYNC_DEST=takezo@takezo:~/packaging/encyc-rg

CONF_BASE=/etc/encyc
CONF_PRODUCTION=$(CONF_BASE)/encycrg.cfg
CONF_LOCAL=$(CONF_BASE)/encycrg-local.cfg
CONF_SECRET=$(CONF_BASE)/encycrg-secret-key.txt
CONF_DJANGO=$(INSTALLDIR)/encycrg/encycrg/settings.py

LOGS_BASE=/var/log/$(PROJECT)
SQLITE_BASE=/var/lib/$(PROJECT)

MEDIA_BASE=/var/www/$(APP)
MEDIA_ROOT=$(MEDIA_BASE)/media
STATIC_ROOT=$(MEDIA_BASE)/static

ELASTICSEARCH=elasticsearch-2.4.4.deb
ASSETS=encyc-rg-assets.tar.gz
# wget https://download.elasticsearch.org/elasticsearch/elasticsearch/elasticsearch-2.4.4.deb

SUPERVISOR_GUNICORN_CONF=/etc/supervisor/conf.d/$(APP).conf
SUPERVISOR_CONF=/etc/supervisor/supervisord.conf
NGINX_CONF=/etc/nginx/sites-available/$(APP).conf
NGINX_CONF_LINK=/etc/nginx/sites-enabled/$(APP).conf


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
	@echo "update  - Updates encyc-rg and re-copies config files."
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
	@echo "update  - Do an update"
	@echo "restart - Restart servers"
	@echo "status  - Server status"
	@echo "install-configs - "
	@echo "update-app - "
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


get: get-app get-static apt-update

install: install-prep install-app install-static install-configs

update: update-app

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
	apt-get --assume-yes install openjdk-7-jre
	-wget -nc -P $(DOWNLOADS_DIR) http://$(PACKAGE_SERVER)/$(ELASTICSEARCH)

install-elasticsearch: get-elasticsearch
	@echo ""
	@echo "Elasticsearch ----------------------------------------------------------"
# Elasticsearch is configured/restarted here so it's online by the time script is done.
	gdebi --non-interactive $(DOWNLOADS_DIR)/$(ELASTICSEARCH)
	cp $(INSTALLDIR)/debian/conf/elasticsearch.yml /etc/elasticsearch/
	chown root.root /etc/elasticsearch/elasticsearch.yml
	chmod 644 /etc/elasticsearch/elasticsearch.yml
# 	@echo "${bldgrn}search engine (re)start${txtrst}"
	/etc/init.d/elasticsearch restart
	-mkdir -p /var/backups/elasticsearch
	chown -R elasticsearch.elasticsearch /var/backups/elasticsearch
	chmod -R 755 /var/backups/elasticsearch


install-virtualenv:
	apt-get --assume-yes install python-pip python-virtualenv
	test -d $(VIRTUALENV) || virtualenv --python=python3 --distribute --setuptools $(VIRTUALENV)

install-setuptools: install-virtualenv
	@echo ""
	@echo "install-setuptools -----------------------------------------------------"
	apt-get --assume-yes install python-dev
	source $(VIRTUALENV)/bin/activate; \
	pip3 install -U bpython setuptools


get-app: get-encyc-rg get-static

install-app: install-encyc-rg

update-app: update-encyc-rg install-configs

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
	cd $(INSTALLDIR)/encycrg && python manage.py migrate --noinput
	chown -R $(USER).root $(SQLITE_BASE)
	chmod -R 750 $(SQLITE_BASE)
	chown -R $(USER).root $(LOGS_BASE)
	chmod -R 755 $(LOGS_BASE)

update-encyc-rg:
	@echo ""
	@echo "encyc-rg --------------------------------------------------------------"
	git fetch && git pull
	source $(VIRTUALENV)/bin/activate; \
	pip3 install -U -r $(REQUIREMENTS)

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


get-static: get-app-assets

install-static: install-app-assets

clean-static:


make-static-dirs:
	-mkdir $(MEDIA_BASE)
	-mkdir $(STATIC_ROOT)
	-mkdir $(STATIC_ROOT)/js
	chown -R $(USER).root $(MEDIA_BASE)
	chmod -R 755 $(MEDIA_BASE)

get-app-assets:
	-wget -nc -P $(DOWNLOADS_DIR) http://$(PACKAGE_SERVER)/$(ASSETS)

install-app-assets: make-static-dirs
	@echo ""
	@echo "get assets --------------------------------------------------------------"
	-tar xzvf $(DOWNLOADS_DIR)/$(APP)-assets.tar.gz -C $(STATIC_ROOT)/


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
	cp $(INSTALLDIR)/conf/settings.py $(CONF_DJANGO)
	chown root.root $(CONF_DJANGO)
	chmod 644 $(CONF_DJANGO)

uninstall-configs:
	-rm $(CONF_DJANGO)
	-rm $(CONF_SECRET)

install-daemons-configs:
	@echo ""
	@echo "daemon configs ------------------------------------------------------"
# nginx settings
	cp $(INSTALLDIR)/conf/nginx-app.conf $(NGINX_APP_CONF)
	chown root.root $(NGINX_APP_CONF)
	chmod 644 $(NGINX_APP_CONF)
	-ln -s $(NGINX_APP_CONF) $(NGINX_APP_CONF_LINK)
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


package:
	@echo ""
	@echo "FPM packaging ----------------------------------------------------------"
	-rm -Rf $(FPM_FILE)
	virtualenv --python=python3 --relocatable $(VIRTUALENV)  # Make venv relocatable
	fpm   \
	--verbose   \
	--input-type dir   \
	--output-type deb   \
	--name encyc-rg   \
	--version $(VERSION)   \
	--package $(FPM_FILE)   \
	--url "$(GIT_SOURCE_URL)"   \
	--vendor "$(FPM_VENDOR)"   \
	--maintainer "$(FPM_MAINTAINER)"   \
	--description "$(FPM_DESCRIPTION)"   \
	--depends "python3"   \
	--depends "imagemagick"   \
	--depends "sqlite3"   \
	--depends "supervisor"   \
	--chdir $(INSTALLDIR)   \
	conf=$(FPM_BASE)   \
	docs=$(FPM_BASE)   \
	encycrg=$(FPM_BASE)   \
	env=$(FPM_BASE)   \
	conf/settings.py=$(FPM_BASE)/encycrg/encycrg   \
	conf/encycrg.cfg=$(CONF_BASE)/encycrg.cfg   \
	conf/gunicorn.conf=$(SUPERVISOR_GUNICORN_CONF)   \
	COPYRIGHT=$(FPM_BASE)   \
	INSTALL=$(FPM_BASE)   \
	LICENSE=$(FPM_BASE)   \
	Makefile=$(FPM_BASE)   \
	README.rst=$(FPM_BASE)   \
	requirements.txt=$(FPM_BASE)

secret-key:
	@echo ""
	@echo "secret-key -------------------------------------------------------------"
	date +%s | sha256sum | base64 | head -c 50 > $(CONF_BASE)/encycrg-secret-key.txt


package-old:
	@echo ""
	@echo "packaging --------------------------------------------------------------"
	-rm -Rf $(PACKAGE_TMP)
	-rm -Rf $(PACKAGE_BASE)/*.tgz
	-mkdir -p $(PACKAGE_BASE)
	cp -R $(INSTALL_LOCAL) $(PACKAGE_TMP)
	cd $(PACKAGE_TMP)
	git clean -fd   # Remove all untracked files
	virtualenv --relocatable $(PACKAGE_ENV)  # Make venv relocatable
	-cd $(PACKAGE_BASE); tar czf $(PACKAGE_TGZ) encyc-rg

rsync-packaged:
	@echo ""
	@echo "rsync-packaged ---------------------------------------------------------"
	rsync -avz --delete $(PACKAGE_BASE)/encyc-rg $(PACKAGE_RSYNC_DEST)

install-packaged: install-prep install-dependencies install-static install-configs mkdirs syncdb install-daemon-configs
	@echo ""
	@echo "install packaged -------------------------------------------------------"

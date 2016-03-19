SHELL = /bin/bash

PROJECT=encyc
APP=encycrg
USER=encyc

PACKAGE_SERVER=ddr.densho.org/static/$(APP)

INSTALL_BASE=/usr/local/src
INSTALLDIR=$(INSTALL_BASE)/encyc-rg
DOWNLOADS_DIR=/tmp/$(APP)-install
PIP_CACHE_DIR=$(INSTALL_BASE)/pip-cache
VIRTUALENV=$(INSTALL_BASE)/env/$(APP)

LOGS_BASE=/var/log/$(PROJECT)
SQLITE_BASE=/var/lib/$(PROJECT)

MEDIA_BASE=/var/www/$(APP)
MEDIA_ROOT=$(MEDIA_BASE)/media
STATIC_ROOT=$(MEDIA_BASE)/static

DJANGO_CONF=$(INSTALLDIR)/encycrg/encycrg/settings.py
NGINX_APP_CONF=/etc/nginx/sites-available/$(APP).conf
NGINX_APP_CONF_LINK=/etc/nginx/sites-enabled/$(APP).conf
NGINX_ELASTIC_CONF=/etc/nginx/sites-available/elastic.conf
NGINX_ELASTIC_CONF_LINK=/etc/nginx/sites-enabled/elastic.conf
GUNICORN_CONF=/etc/supervisor/conf.d/gunicorn_$(APP).conf

ELASTICSEARCH=elasticsearch-1.0.1.deb
MODERNIZR=modernizr-2.6.2.js
JQUERY=jquery-1.11.0.min.js
BOOTSTRAP=bootstrap-3.1.1-dist
ASSETS=encyc-rg-assets.tar.gz
# wget https://github.com/twbs/bootstrap/releases/download/v3.1.1/bootstrap-3.1.1-dist.zip
# wget http://code.jquery.com/jquery-1.11.0.min.js
# wget https://download.elasticsearch.org/elasticsearch/elasticsearch/elasticsearch-1.0.1.deb

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
	@echo "branch BRANCH=[branch] - Switches encyc-rg and supporting repos to [branch]."
	@echo ""
	@echo "reload  - Reloads supervisord and nginx configs"
	@echo "reload-nginx"
	@echo "reload-supervisors"
	@echo ""
	@echo "restart - Restarts all servers"
	@echo "restart-elasticsearch"
	@echo "restart-redis"
	@echo "restart-nginx"
	@echo "restart-supervisord"
	@echo ""
	@echo "status  - Server status"
	@echo ""
	@echo "uninstall - Deletes 'compiled' Python files. Leaves build dirs and configs."
	@echo "clean   - Deletes files created by building the program. Leaves configs."

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
	apt-get --assume-yes install bzip2 curl gdebi-core logrotate ntp p7zip-full wget

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
	test -d $(VIRTUALENV) || virtualenv --distribute --setuptools $(VIRTUALENV)

install-setuptools: install-virtualenv
	@echo ""
	@echo "install-setuptools -----------------------------------------------------"
	apt-get --assume-yes install python-dev
	source $(VIRTUALENV)/bin/activate; \
	pip install -U --download-cache=$(PIP_CACHE_DIR) bpython setuptools


get-app: get-encyc-rg get-static

install-app: install-encyc-rg

update-app: update-encyc-rg install-configs

uninstall-app: uninstall-encyc-rg

clean-app: clean-encyc-rg


get-encyc-rg:
	git pull
	pip install --download=$(PIP_CACHE_DIR) --exists-action=i -r $(INSTALLDIR)/encycrg/requirements/production.txt

install-encyc-rg: install-virtualenv
	@echo ""
	@echo "encyc-rg --------------------------------------------------------------"
	apt-get --assume-yes install imagemagick sqlite3 supervisor
	source $(VIRTUALENV)/bin/activate; \
	pip install -U --no-index --find-links=$(PIP_CACHE_DIR) -r $(INSTALLDIR)/encycrg/requirements/production.txt
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
	cd $(INSTALLDIR)/encycrg && python manage.py syncdb --noinput
	chown -R $(USER).root $(SQLITE_BASE)
	chmod -R 750 $(SQLITE_BASE)
	chown -R $(USER).root $(LOGS_BASE)
	chmod -R 755 $(LOGS_BASE)

update-encyc-rg:
	@echo ""
	@echo "encyc-rg --------------------------------------------------------------"
	git fetch && git pull
	source $(VIRTUALENV)/bin/activate; \
	pip install -U --no-download --download-cache=$(PIP_CACHE_DIR) -r $(INSTALLDIR)/encycrg/requirements/production.txt

uninstall-encyc-rg:
	cd $(INSTALLDIR)/encycrg
	source $(VIRTUALENV)/bin/activate; \
	-pip uninstall -r $(INSTALLDIR)/encycrg/requirements/production.txt
	-rm /usr/local/lib/python2.7/dist-packages/encycrg-*
	-rm -Rf /usr/local/lib/python2.7/dist-packages/encycrg

restart-encycrg:
	/etc/init.d/supervisor restart encycrg

clean-encyc-rg:
	-rm -Rf $(INSTALLDIR)/encycrg/src

clean-pip:
	-rm -Rf $(PIP_CACHE_DIR)/*


branch:
	cd $(INSTALLDIR)/encycrg; python ./bin/git-checkout-branch.py $(BRANCH)


get-static: get-app-assets get-modernizr get-bootstrap get-jquery

install-static: install-app-assets install-modernizr install-bootstrap install-jquery

clean-static: clean-modernizr clean-bootstrap clean-jquery


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


get-modernizr:
	-wget -nc -P $(DOWNLOADS_DIR) http://$(PACKAGE_SERVER)/$(MODERNIZR)

install-modernizr: make-static-dirs
	@echo ""
	@echo "Modernizr --------------------------------------------------------------"
	-cp -R $(DOWNLOADS_DIR)/$(MODERNIZR) $(STATIC_ROOT)/js/

clean-modernizr:
	-rm $(STATIC_ROOT)/js/$(MODERNIZR)*


get-bootstrap:
	-wget -nc -P $(DOWNLOADS_DIR) http://$(PACKAGE_SERVER)/$(BOOTSTRAP).zip

install-bootstrap: make-static-dirs
	@echo ""
	@echo "Bootstrap --------------------------------------------------------------"
	7z x -y -o$(STATIC_ROOT) $(DOWNLOADS_DIR)/$(BOOTSTRAP).zip
	-ln -s $(STATIC_ROOT)/$(BOOTSTRAP) $(STATIC_ROOT)/bootstrap

clean-bootstrap:
	-rm -Rf $(STATIC_ROOT)/$(BOOTSTRAP)


get-jquery:
	-wget -nc -P $(DOWNLOADS_DIR) http://$(PACKAGE_SERVER)/$(JQUERY)

install-jquery: make-static-dirs
	@echo ""
	@echo "jQuery -----------------------------------------------------------------"
#	wget -nc -P $(STATIC_ROOT)/js http://$(PACKAGE_SERVER)/$(JQUERY)
#	-ln -s $(STATIC_ROOT)/js/$(JQUERY) $(STATIC_ROOT)/js/jquery.js
	cp -R $(DOWNLOADS_DIR)/$(JQUERY) $(STATIC_ROOT)/js/
	-ln -s $(STATIC_ROOT)/js/$(JQUERY) $(STATIC_ROOT)/js/jquery.js

clean-jquery:
	-rm -Rf $(STATIC_ROOT)/js/$(JQUERY)
	-rm $(STATIC_ROOT)/js/jquery.js


install-configs:
	@echo ""
	@echo "installing configs --------------------------------------------------"
	cp $(INSTALLDIR)/conf/settings.py $(DJANGO_CONF)
	chown root.root $(DJANGO_CONF)
	chmod 644 $(DJANGO_CONF)

uninstall-configs:
	-rm $(DJANGO_CONF)
	-rm $(CONFIG_KEY)
	-rm $(CONFIG_PROD)

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


status:
	-/etc/init.d/redis-server status
	-/etc/init.d/elasticsearch status
	-/etc/init.d/nginx status
	-supervisorctl status

git-status:
	@echo "------------------------------------------------------------------------"
	cd $(INSTALLDIR) && git status

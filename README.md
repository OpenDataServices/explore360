GrantNav - Explore Grants in the 360 data standard
==================================================

[![Build Status](https://travis-ci.com/ThreeSixtyGiving/grantnav.svg?branch=master)](https://travis-ci.com/ThreeSixtyGiving/grantnav)

We use GitHub Projects to provide a Kanban board visualisation of our workflow and issues https://github.com/ThreeSixtyGiving/grantnav/projects

Introduction
------------

This is a search tool for data in the 360 giving data format.

Live deploy at https://grantnav.threesixtygiving.org/

Requirements
------------
This application is built using Django, Elasticsearch and python 3

Installation
------------
Steps to installation:

* Install pre-requisites: Git, Python3, and lots of things for Pillow.
* Clone the repository
* Change into the cloned repository
* Create a virtual environment
* Activate the virtual environment
* Install dependencies
* Install Elastic search
* Run database migrations
* Run the development server

These instructions assume Ubuntu Xenial.

```
sudo apt-get install -y git-core
sudo apt-get install -y python3-dev

git clone git@github.com:ThreeSixtyGiving/grantnav.git
cd grantnav
python3 -m venv .ve
source .ve/bin/activate
# Make sure you have a recent version of pip, to install binary wheel packages.
pip install --upgrade pip
pip install -r requirements.txt # Use requirements_dev.txt if you're installing for development.
# Elasticsearch 7 https://www.elastic.co/guide/en/elasticsearch/reference/current/deb.html
wget -qO - https://artifacts.elastic.co/GPG-KEY-elasticsearch | sudo apt-key add -
echo "deb https://artifacts.elastic.co/packages/7.x/apt stable main" | sudo tee /etc/apt/sources.list.d/elastic-7.x.list
sudo apt-get install apt-transport-https
sudo apt-get update
sudo apt-get install elasticsearch
sudo service elasticsearch start
python manage.py migrate
# Running the tests gets some data into the elastic index
py.test
python manage.py runserver
```

Note that if you are not on Debian based system you will need to follow https://www.elastic.co/guide/en/elasticsearch/reference/current/setup.html#setup-installation to install elasticsearch.
Follow the instructions in your terminal to open the aplication in your browser.

## Database

The default django database is used in grantnav to manage user session preferences data. It must be created via the setup `manage.py migrate` for GrantNav to work correctly.

note: This is not related to elasticsearch.

Accessing GrantNav
------------------

The above command gives you a local server listening on port 8000. If you're installing inside a virtual machine, you will need to do some or all of the following:

1. Modify or disable the firewall to allow connections. (`sudo ufw disable`)
2. Set the `ALLOWED_HOSTS` environment variable to include your host IP: `export ALLOWED_HOSTS='localhost','127.0.0.1','192.168.33.10'`
3. Modify your VM settings to allow port forwarding. E.g.: `config.vm.network "private_network", ip: "192.168.33.10"` in Vagrant.
4. Start the server with the allowed host: `python manage.py runserver 192.168.33.10:8000`


Loading Data
------------

In order to load some data use the dataload/import_to_elasticsearch.py command line tool e.g:

`python dataload/import_to_elasticsearch.py --clean filename1.csv filename2.csv *.json`

The clean command is optional; it will delete the index and start again, so leave it off if you want to add just another file to an existing index.
You can specify as many file or patterns as you like at the end of the command.

The funders and recipients search requires the datastore generated `funders.jl` and `recipients.jl` files to be passed in as arguments to import_to_elasticsearch via the commands `--funders path/to/funders.jl` and `--recipients path/to/recipients.jl`.

### Getting data for loading

There is a list of 360Giving datasets at https://data.threesixtygiving.org/. There's an API for this list https://data.threesixtygiving.org/data.json and a datagetter tool to download and convert it -  https://github.com/ThreeSixtyGiving/datagetter

If your data is in a flat format (eg Excel spreadsheet, CSV), or needs validating, you can use [CoVE](https://cove.opendataservices.coop/360/) to convert and validate your data.

Alternatively contact 360Giving for the latest data dump from the datastore.
### Provenance JSON

Most parts of GrantNav work fine without provenance information. However, in order for the publisher/datasets pages to work correctly you must point the `PROVENANCE_JSON` environment variable at a local copy of [data.json](https://data.threesixtygiving.org/data.json). You must also load the data into GrantNav using filenames that correspond to the identifiers in this JSON. The [datagetter](https://github.com/ThreeSixtyGiving/datagetter) saves files with the correct name, and also makes a copy of data.json for you.

e.g.

```
cd datagetter/data/json_acceptable_license_valid
python path/to/grantnav/dataload/import_to_elasticsearch.py --clean *
cd path/to/grantnav
PROVENANCE_JSON=path/to/datagetter/data/data_acceptable_license_valid.json python manage.py runserver
```


Compile theme
-------------

In order to compile the sass theme please see the [360-ds](https://github.com/ThreeSixtyGiving/360-ds) submodule. All styles are built and imported from there.


Run tests
------------

```
ALLOWED_HOSTS=localhost py.test
```

Make sure elastic search is running.

The tests include functional tests (actually interacting with the website in selenium). These can also be run against a deployed copy of the website:

```
CUSTOM_SERVER_URL=https://dev.grantnav.opendataservices.coop py.test
```

The tests delete an elastic search index and repopulate it.  The default index name is threesixtygiving

We also use flake8 to test code quality, see https://github.com/OpenDataServices/developer-docs/blob/master/tests.md#flake8

We use ESLint to statically analyse JavaScript code.
+ Install with `npm install`
+ Run `npx eslint --ext .js --ext .html grantnav/frontend/templates/**`


Adding and updating requirements
--------------------------------

Add new requirements to ``requirements.in`` or ``requirements_dev.in`` depending on whether it is just a development requirement or not. Run `pip-compile` (from the package `pip-tools`) on the ".in" file.

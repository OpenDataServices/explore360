GrantNav - Explore Grants in the 360 data standard
==================================================


Introduction
------------

GrantNav is a search tool for data in the 360 giving data format.

You can find the tool running at [https://grantnav.threesixtygiving.org/](https://grantnav.threesixtygiving.org/)

Requirements
------------
This application is built using Django, Elasticsearch and Python 3.8

Installation
------------
Steps to installation:


1. Check out the GrantNav repository
```
git clone https://github.com/ThreeSixtyGiving/grantnav.git
cd grantnav
```

2. Create python virtual environment
```
python3.8 -m venv .ve
source .ve/bin/activate
```

3. Install dependencies

This installs Elasticsearch 7 see https://www.elastic.co/guide/en/elasticsearch/reference/current/deb.html for further information.
If you are not on Debian based system you will need to follow https://www.elastic.co/guide/en/elasticsearch/reference/current/setup.html#setup-installation to install elasticsearch.

```
pip install -r requirements.txt # Use 'requirements_dev.txt' if you're installing for development and testing.

wget -qO - https://artifacts.elastic.co/GPG-KEY-elasticsearch | sudo apt-key add -
echo "deb https://artifacts.elastic.co/packages/7.x/apt stable main" | sudo tee /etc/apt/sources.list.d/elastic-7.x.list
sudo apt-get install apt-transport-https
sudo apt-get update
sudo apt-get install elasticsearch
sudo service elasticsearch start
```

4. Run migrate to install the default django database for sessions etc (sqlite)

```
python manage.py migrate
```

5. Run the development server

```
DEBUG=true python manage.py runserver
```

## Database

The default django database is used in grantnav to manage user session preferences data. It must be created via the setup `manage.py migrate` for GrantNav to work correctly.

note: This is not related to elasticsearch.

Accessing GrantNav
------------------

The `runserver` command gives you a local server which by default listens on port 8000. If you're installing inside a virtual machine, you will need to do some or all of the following:

1. Modify or disable the firewall to allow connections. (`sudo ufw disable`)
2. Set the `ALLOWED_HOSTS` environment variable to include your host IP: `export ALLOWED_HOSTS='localhost','127.0.0.1','192.168.33.10'`
3. Modify your VM settings to allow port forwarding. E.g.: `config.vm.network "private_network", ip: "192.168.33.10"` in Vagrant.
4. Start the server with the allowed host: `python manage.py runserver 192.168.33.10:8000`


Loading Data
------------

In order to load some data use the dataload/import_to_elasticsearch.py command line tool e.g:

```
python dataload/import_to_elasticsearch.py --clean /path/to/data_package/json_all/*.json --funders /path/to/data_package/funders.jl --recipients /path/to/data_package/recipients.jl
```

The clean command is optional; it will delete the index and start again, so leave it off if you want to add just another file to an existing index.
You can specify as many file or patterns as you like at the end of the command.

The funders and recipients search requires the datastore generated `funders.jl` and `recipients.jl` files to be passed in as arguments to import_to_elasticsearch via the commands `--funders path/to/funders.jl` and `--recipients path/to/recipients.jl`.

### Getting data for loading

Either:

1. [Contact 360 Giving](https://www.threesixtygiving.org/contact/) for access to the grantnav daily data package.
or
2. Use the [datagetter](https://github.com/ThreeSixtyGiving/datagetter) to download all the [available 360 Giving data](https://registry.threesixtygiving.org) from publishers. 

### Provenance JSON

Most parts of GrantNav work fine without provenance information. However, in order for the publisher/datasets pages to work correctly you must point the `PROVENANCE_JSON` environment variable at a local copy of [data.json](https://data.threesixtygiving.org/data.json). You must also load the data into GrantNav using filenames that correspond to the identifiers in this JSON. The [datagetter](https://github.com/ThreeSixtyGiving/datagetter) saves files with the correct name, and also makes a copy of data.json for you.

e.g.

```
PROVENANCE_JSON=path/to/data_package/data_all.json python manage.py runserver
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


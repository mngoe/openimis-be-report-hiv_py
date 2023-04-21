# openIMIS Backend report reference module
This repository holds the files of the openIMIS Backend Cheque Santé reference module. 

It is dedicated to be deployed as a module of [openimis-be_py](https://github.com/openimis/openimis-be_py). 

 Start creating openimis-be-report-hiv_py module.

- from an empty repository folder

  - clone the repository or donwload the file (reporthiv)

  - checkout to the develop branch by executing the command

  - within openimis-be-report-hiv_py, create the sub repository named reporthiv

  - prepare your module to be mounted via pip: create and 
  complete the /openimis-be-report-hiv_py/ by creating or copying the setup.py, MANIFEST.in, 
  LICENSE.md and README.md (if not created), ... files (the files could be copied from product module and 
  being adpted to productpackage module needs.

  - create the file /openimis-be-report-hiv_py/reporthiv/urls.py (even empty) 
   with content: urlpatterns = []

  - from /openimis-be_py/openIMIS: register your module in the pip requirements of openIMIS,
    referencing your 'local' codebase: pip install -e ../../openimis-be-report-hiv_py/

  - register your module to openIMIS django site in /openimis-be_py/openimis.json

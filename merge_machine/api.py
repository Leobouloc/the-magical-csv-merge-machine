#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Feb  6 15:01:16 2017

@author: leo

TODO:
    - Safe file name / not unique per date
    
    - API: List of internal referentials
    - API: List of finished modules for given project / source
    - API: List of loaded sources
    
    - API: Fetch infered parameters
    - API: Fetch logs
    - API: Move implicit load out of API
    
    - API: Error codes / remove error
    
    - Change metadata to use_internal and ref_name to last used or smt. Data to
      use is specified on api call and not read from metadata (unless using last used)
    
    - Protect admin functions
    -
    - ADD LICENSE

DEV GUIDELINES:
    - By default the API will use the file with the same name in the last 
      module that was completed. Otherwise, you can specify the module to use file from
    - Suggestion methods shall be prefixed by suggest (ex: suggest_load_params, suggest_missing_values)
    - Suggestion methods shall can be plugged as input as params variable of transformation modules
    - Single file modules shall take as input: (pandas_dataframe, params)
    - Single file modules suggestion modules shall ouput (params, log)
    - Single file modules replacement modules shall ouput (pandas_dataframe, log)
    
    - Multiple file modules shall take as input: (pd_dataframe_1, pd_dataframe_2, params)
    - Multiple file modules suggestion modules shall ouput params, log
    - Multiple file modules merge module shall ouput ???
    
    - Files generated by modules should be in module directory and have names determined at the project level (not API, nor module)
    
    - Do NOT return files, instead, user can fetch file through api
    - If bad params are passed to modules, exceptions are raised, it is the APIs role to transform these exceptions in messages
    - Functions to check parameters should be named check_{variable_or_function} (ex: check_file_role)
    - All securing will be done in the API part
    - Always return {"error": ..., "project_id": ..., "response": ...}


NOTES:
    - Pay for persistant storage?

# Transform 
curl -i http://127.0.0.1:5000/transform/ -X POST -F "source=@data/tmp/test_merge.csv" -F "ref=@data/tmp/test_merge_small.csv" -F "request_json=@sample_request.json;type=application/json"

# Upload data
curl -i http://127.0.0.1:5000/download/ -X POST -F "request_json=@sample_download_request.json;type=application/json"

# Download data
curl -i http://127.0.0.1:5000/download/ -X POST -F "request_json=@sample_download_request.json;type=application/json"

# Download metadata
curl -i http://127.0.0.1:5000/metadata/ -X POST -F "request_json=@sample_download_request.json;type=application/json"
"""

import os

from flask import Flask, jsonify, render_template, request, send_file, url_for
from flask_cors import CORS, cross_origin
from werkzeug.utils import secure_filename

from admin import Admin
from user_project import UserProject
from referential import Referential


# Change current path to path of api.py
curdir = os.path.dirname(os.path.realpath(__file__))
os.chdir(curdir)

# Initiate application
app = Flask(__name__)
cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'
app.config['SERVER_NAME'] = '127.0.0.1:5000'


app.debug = True
app.secret_key = open('secret_key.txt').read()
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 # Check that files are not too big
          
          

    
def check_request():
    '''Check that input request is valid'''
    pass


def init_project(project_id=None, existing_only=False):
    '''Initialize project'''  
    
    if (project_id is None) and existing_only:
        raise Exception('Cannot pass None to project_id. \
                        Use `upload` to create a new project')
    proj = UserProject(project_id)
    return proj
    

def parse_data_params(proj, data_params, file_role=None):
    '''
    Returns identifiers for data based on project history. Uses `get_last_written`
    to retrieve the last file written given the constraints in data_params
    
    INPUT:
        - proj: a user project
        - data_params: {'file_role': ..., 'module': ..., 'file_name': ...}
        - file_role: Constrain the file role (for use in linking...)
    '''
    if data_params is None:
        module_name = None
        file_name = None
    else:
        file_role = data_params.setdefault('file_role', file_role)
        # Skip processing for internal referentials
        if data_params.setdefault('internal', False):
            raise Exception('Internal data NOT YET IMPLEMENTED')
        
        # Load data from last run (or from user specified)
        file_name = data_params.setdefault('file_name', None)
        module_name = data_params.setdefault('module', None)
        
    if any(x is None for x in [file_role, module_name, file_name]):
        (file_role, module_name, file_name) = proj.get_last_written(\
                                        file_role, module_name, file_name)
    return (file_role, module_name, file_name)


def load_from_params(proj, data_params=None):
    '''Load data to project using the parameters received in request.
    Implicit load is systematic. TODO: Define implicit load
    '''
    (file_role, module_name, file_name) = parse_data_params(proj, data_params)
    proj.load_data(file_role, module_name, file_name)



def parse_1file_request():
    # Parse json request
    data_params = None
    module_params = None
    if request.json:
        params = request.json
        assert isinstance(params, dict)
    
        if 'data' in params:
            data_params = params['data']
            
            # Make paths secure
            for key, value in data_params.items():
                data_params[key] = secure_filename(value)
            
        if 'params' in params:
            module_params = params['params']
    
    return data_params, module_params
    
def parse_linking_request():
    data_params = None
    module_params = None
    if request.json:
        params = request.json
        assert isinstance(params, dict)
    
        if 'data' in params:
            data_params = params['data']
            for file_role in ['ref', 'source']:
                # Make paths secure
                for key, value in data_params[file_role].items():
                    data_params[file_role][key] = secure_filename(value)
                
        if 'params' in params:
            module_params = params['params']
    
    return data_params, module_params    

#==============================================================================
# WEB
#==============================================================================

@app.route('/')
@app.route('/web/', methods=['GET'])
@app.route('/web/project/', methods=['GET'])
@cross_origin()
def web_index():
    return render_template('index.html', 
                           next_url=url_for('web_select_files'))


@app.route('/web/project/select/', methods=['GET'])
@app.route('/web/project/select/<project_id>/', methods=['GET', 'POST'])
@cross_origin()
def web_select_files(project_id=None):
    MAX_FILE_SIZE = 1048576
    
    proj = init_project(project_id=project_id, existing_only=True)
    all_csvs = proj.list_files(extensions=['.csv'])
    
    all_internal_refs = [] # TODO: take care of this
    return render_template('select_files.html', 
                           project_id=project_id,
                           previous_sources=all_csvs['source'],
                           previous_references=all_csvs['ref'],
                           internal_references=all_internal_refs,
                           upload_api_url=url_for('upload', project_id=project_id),
                           select_file_url=url_for('select_file', project_id=project_id),
                           next_url=url_for('web_match_columns', project_id=project_id),
                           MAX_FILE_SIZE=MAX_FILE_SIZE)

@app.route('/web/project/match_columns/<project_id>/', methods=['GET'])
@cross_origin()
def web_match_columns(project_id):
    ROWS_TO_DISPLAY = range(3)
    
    proj = init_project(project_id, existing_only=True)
    
    # Load source sample
    source_data = proj.metadata['current']['source']

    if not source_data['internal']:
        # NB: Displaying initial file
        source_sample = proj.get_sample('source', 'INIT', source_data['file_name'],
                                     row_idxs=ROWS_TO_DISPLAY)
    else:
        raise Exception('Internal source not yet implemented')
    
    # Load ref sample
    ref_data = proj.metadata['current']['ref']
    if not ref_data['internal']:
        ref_sample = proj.get_sample('ref', 'INIT', ref_data['file_name'], 
                                     row_idxs=ROWS_TO_DISPLAY)
    else:
        raise Exception('Internal source not yet implemented')
    
    print(source_sample)
    return render_template('match_columns.html',
                           source_index=list(source_sample[0].keys()),
                           ref_index=list(ref_sample[0].keys()),
                           source_sample=source_sample,
                           ref_sample=ref_sample,
                           add_column_matches_api_url=url_for('add_column_matches', project_id=project_id),
                           next_url=url_for('web_dedupe', project_id=project_id))
  
@app.route('/web/project/dedupe/<project_id>/', methods=['GET'])
@cross_origin()    
def web_dedupe(project_id):
    return 'Hi THERE. NOT YET IMPLEMENTED'
    

#==============================================================================
# API
#==============================================================================

@app.route('/api/project/new/', methods=['GET'])
def new_project():
    proj = UserProject(create_new=True)
    return jsonify(error=False, 
                   project_id=proj.project_id)


@app.route('/api/project/metadata/<project_id>/', methods=['GET', 'POST'])
@cross_origin()
def metadata(project_id):
    '''Fetch metadata for project ID'''
    proj = init_project(project_id, True)
    resp = jsonify(error=False,
                   metadata=proj.metadata, 
                   project_id=proj.project_id)
    return resp


@app.route('/api/project/download/<project_id>/', methods=['POST'])
@cross_origin()
def download(project_id):
    '''
    Download file from project.
    
    If just project_id: return last modified file
    If variables are specified, return the last file modified with specific variables
    
    '''
    try:
        proj = init_project(project_id, True)
        data_params, _ = parse_1file_request()
        
        if data_params is None:
            data_params = {}
            
        file_role = data_params.get('file_role', None)
        module = data_params.get('module', None)
        file_name = data_params.get('file_name', None)
        
        if file_role is not None:
            file_role = secure_filename(file_role)
        if module is not None:
            module = secure_filename(module)
        if file_name is not None:
            file_name = secure_filename(file_name)
            
        (file_role, module, file_name) = proj.get_last_written(file_role, module, file_name)
            
        if module == 'INIT':
            return jsonify(error=True,
                   message='No changes were made since upload. Download is not \
                           permitted. Please do not use this service for storage')
        
        file_path = proj.path_to(file_role, module, file_name)
        return send_file(file_path)
    
    except Exception as e:
        import pdb
        pdb.set_trace()
        return jsonify(error=True,
                       message=e)

@app.route('/api/project/select_file/<project_id>/', methods=['POST'])
def select_file(project_id):
    '''send {file_role: "source", file_name: "XXX", internal: False}'''
    proj = init_project(project_id, True)
    params = request.json
    proj.select_file(params['file_role'], params['file_name'], params['internal'])
    return jsonify(error=False)
 
    
    
@app.route('/api/project/exists/<project_id>/', methods=['GET', 'POST'])
@cross_origin()
def project_exists(project_id):
    '''Check if project exists'''
    try:
        _ = UserProject(project_id=secure_filename(project_id), create_new=False)
        print('YO')
        return jsonify(error=False, exists=True)
    except: 
        print('LO')
        return jsonify(error=False, exists=False)
    

@app.route('/api/project/upload/<project_id>/', methods=['POST'])
@cross_origin()
def upload(project_id=None):
    '''
    Uploads source and reference files to project either passed as variable or
    loaded from request parameters
    '''
    if  isinstance(project_id, str) and project_id.lower() == 'new_project':
        project_id = None # TODO: Dirty fix bc swagger doesnt take optional path parameters
    
    # Create or Load project
    proj = init_project(project_id) 
    
    # 
    for key in ['source', 'ref']:
        if key in request.files:
            file = request.files[key]
            if file:
                proj.add_init_data(file.stream, key, file.filename)    
    
    return jsonify(error=False,
               metadata=proj.metadata,
               project_id=proj.project_id)


@app.route('/api/project/add_column_matches/<project_id>/', methods=['POST'])
@cross_origin()
def add_column_matches(project_id):
    column_matches = request.json
    proj = init_project(project_id, existing_only=True)
    proj.add_col_matches(column_matches)
    return jsonify(error=False)
    

#==============================================================================
# MODULES
#==============================================================================

@app.route('/api/project/modules/', methods=['GET', 'POST'])
@cross_origin()
def list_modules():
    '''List available modules'''
    return jsonify(error=True,
                   message='This should list the available modules') #TODO: <--


@app.route('/api/project/modules/infer_mvs/<project_id>/', methods=['GET', 'POST'])
@cross_origin()
def infer_mvs(project_id):
    '''Runs the infer_mvs module'''
    proj = init_project(project_id, True)
    data_params, module_params = parse_1file_request()    
    
    load_from_params(proj, data_params)
    
    result = proj.infer('infer_mvs', module_params)
        
    # Write log
    proj.write_log_buffer(False)
    
    return jsonify(error=False,
                   response=result)
    
    
@app.route('/api/project/modules/replace_mvs/<project_id>/', methods=['POST'])
@cross_origin()
def replace_mvs(project_id):
    '''Runs the mvs replacement module'''
    proj = init_project(project_id, True)
    data_params, module_params = parse_1file_request()
    
    load_from_params(proj, data_params)
    proj.transform('replace_mvs', module_params)
    # Write transformations and log
    proj.write_data()    
    proj.write_log_buffer(True)
    
    return jsonify(error=False)


@app.route('/api/project/link/dedupe_linker/<project_id>/', methods=['POST'])
@cross_origin()
def linker(project_id):
    '''
    Runs deduper module. Contrary to other modules, linker modules, take
    paths as input (in addition to module parameters)
    
    {
    'data': {'source': {},  
            'ref': {}}
    'params': {'variable_definition': {...},
               'columns_to_keep': [...]}
    }
    
    '''
    proj = init_project(project_id, True)
    data_params, module_params = parse_linking_request()
    
    # Set paths
    (file_role, module_name, file_name) = parse_data_params(proj, data_params.get('source', None), file_role='source')
    source_path = proj.path_to(file_role='source', module_name=module_name, file_name=file_name)

    (file_role, module_name, file_name) = parse_data_params(proj, data_params.get('ref', None), file_role='ref')
    ref_path = proj.path_to(file_role='ref', module_name=module_name, file_name=file_name)
    
    paths = {'ref': ref_path, 'source': source_path}
    
    # Perform linking
    _ = proj.linker('dedupe_linker', paths, module_params)

    # Write transformations and log
    proj.write_data()    
    proj.write_log_buffer(True)


    return jsonify(error=False)    
    

#==============================================================================
# Admin
#==============================================================================

@app.route('/api/admin/list_projects/', methods=['GET', 'POST'])
@cross_origin()
def list_projects():
    '''Lists all project id_s'''
    admin = Admin()
    list_of_projects = admin.list_projects()
    return jsonify(error=False,
                   response=list_of_projects)

@app.route('/api/admin/list_referentials/', methods=['GET', 'POST'])
@cross_origin()
def list_referentials():
    '''Lists all internal referentials'''
    admin = Admin()
    list_of_projects = admin.list_referentials()
    return jsonify(error=False,
                   response=list_of_projects)


if __name__ == '__main__':
    app.run(debug=True)
